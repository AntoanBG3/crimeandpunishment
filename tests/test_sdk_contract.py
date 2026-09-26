"""Exercise the actual installed SDK and serialization with an offline transport."""

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from google import genai

from game_engine.gemini_interactions import (
    DEFAULT_GEMINI_MODEL_NAME, INTENT_GEMINI_MODEL_NAME, GeminiAPI, NaturalLanguageParser,
    SetupResult, is_usable_ai_text,
)

RETIRED_MODEL = 'gemini-3.1-pro-preview'
TAVERN_SCENE = {'exits': [{'name': 'Tavern', 'description': 'a noisy tavern'}],
                'items': [], 'npcs': [], 'inventory': []}
MOVE_TO_TAVERN = {'intent': 'move', 'target': 'Tavern', 'confidence': 0.9}


def not_found(model):
    """The service's reply for a model it does not serve, such as a retired preview."""
    return httpx.Response(404, json={'error': {'code': 404, 'status': 'NOT_FOUND', 'message': (
        f'models/{model} is not found for API version v1beta, '
        'or is not supported for generateContent.')}})


def api_error(code, status, message):
    return httpx.Response(code, json={'error': {
        'code': code, 'status': status, 'message': message}})


def reply(text):
    return httpx.Response(200, json={'candidates': [{'content': {
        'role': 'model', 'parts': [{'text': text}]}, 'finishReason': 'STOP'}]})


def requested_model(request):
    return request.url.path.split('/models/')[1].split(':')[0]


def generation_config(request):
    return json.loads(request.content).get('generationConfig', {})


def serve_all_but_retired(request):
    if requested_model(request) == RETIRED_MODEL:
        return not_found(RETIRED_MODEL)
    return httpx.Response(200, json={'candidates': [{'content': {
        'role': 'model', 'parts': [{'text': 'test'}]}, 'finishReason': 'STOP'}]})


class TestSDKContract(unittest.TestCase):
    def test_test_runner_does_not_replace_sdk(self):
        api = GeminiAPI()
        self.assertTrue(api._load_genai())
        self.assertIs(api.genai, genai)

    def make_api(self, handler):
        transport = httpx.MockTransport(handler)
        http_client = httpx.Client(transport=transport)
        self.addCleanup(http_client.close)

        def factory(**kwargs):
            kwargs['http_options']['httpx_client'] = http_client
            return genai.Client(**kwargs)

        api = GeminiAPI(client_factory=factory)
        api._print_color_func = MagicMock()
        self.addCleanup(api.close)
        return api

    def test_verification_generation_and_deadline_use_real_sdk(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'candidates': [{'content': {
                'role': 'model', 'parts': [{'text': 'test'}]}, 'finishReason': 'STOP'}]})

        api = self.make_api(respond)
        self.assertTrue(api._attempt_api_setup('offline-key', 'test', 'test-model'))
        self.assertEqual(api._generate_content_with_fallback('hello'), 'test')
        self.assertEqual(len(requests), 2)
        self.assertLessEqual(requests[0].extensions['timeout']['read'], 10)
        api.close()
        self.assertIsNone(api.client)
        self.assertIsNone(api.model)

    def test_any_generation_reply_verifies_the_key(self):
        # Thinking models count thoughts against max_output_tokens, so the small
        # verification cap can end the reply before any text.
        replies = {
            'cut off while thinking': {
                'candidates': [{'content': {}, 'finishReason': 'MAX_TOKENS'}],
                'usageMetadata': {'promptTokenCount': 15, 'thoughtsTokenCount': 5,
                                  'totalTokenCount': 20}},
            'other wording': {'candidates': [{'content': {
                'role': 'model', 'parts': [{'text': 'Confirmed.'}]}, 'finishReason': 'STOP'}]},
            'blocked prompt': {'promptFeedback': {'blockReason': 'SAFETY'}},
        }
        for name, body in replies.items():
            with self.subTest(name):
                handler = MagicMock(return_value=httpx.Response(200, json=body))
                api = self.make_api(handler)
                result = api._attempt_api_setup('offline-key', 'test', 'test-model')
                self.assertIs(result, SetupResult.VERIFIED)
                self.assertEqual(handler.call_count, 1)
                self.assertEqual(api.model.model_name, 'test-model')

    def test_http_failures_fall_back_without_retries(self):
        for status in (401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                handler = MagicMock(return_value=httpx.Response(status, json={
                    'error': {'code': status, 'message': 'private-response', 'status': 'UNKNOWN'}}))
                api = self.make_api(handler)
                self.assertFalse(api._attempt_api_setup('offline-key', 'test', 'test-model'))
                self.assertEqual(handler.call_count, 1)
                self.assertIsNone(api.client)

    def test_only_rejected_keys_are_auth_failures(self):
        def error(code, status, message, **extra):
            return httpx.Response(code, json={'error': {
                'code': code, 'status': status, 'message': message, **extra}})

        invalid_key = error(400, 'INVALID_ARGUMENT', 'API key not valid. Please pass a valid API key.',
                            details=[{'@type': 'type.googleapis.com/google.rpc.ErrorInfo',
                                      'reason': 'API_KEY_INVALID'}])
        cases = {
            'invalid key': (invalid_key, SetupResult.AUTH_FAILED),
            'permission denied': (error(403, 'PERMISSION_DENIED', 'Permission denied.'),
                                  SetupResult.AUTH_FAILED),
            'offline': (httpx.ConnectError('offline'), SetupResult.FAILED),
            'quota': (error(429, 'RESOURCE_EXHAUSTED', 'Quota exceeded.'), SetupResult.FAILED),
            'outage': (error(503, 'UNAVAILABLE', 'The model is overloaded.'), SetupResult.FAILED),
            'retired model': (not_found(RETIRED_MODEL), SetupResult.MODEL_UNAVAILABLE),
        }
        for name, (outcome, expected) in cases.items():
            with self.subTest(name):
                # A mock raises exception items and returns the rest.
                handler = MagicMock(side_effect=[outcome])
                api = self.make_api(handler)
                self.assertIs(api._attempt_api_setup('offline-key', 'test', 'test-model'), expected)
                self.assertEqual(handler.call_count, 1)
                self.assertIsNone(api.client)

    def test_verification_failure_shows_api_status_and_message(self):
        handler = MagicMock(return_value=httpx.Response(404, json={'error': {
            'code': 404, 'status': 'NOT_FOUND',
            'message': 'models/test-model is not found for API version v1beta.'}}))
        api = self.make_api(handler)
        self.assertIs(api._attempt_api_setup('offline-key', 'test', 'test-model'),
                      SetupResult.MODEL_UNAVAILABLE)
        printed = [call.args[0] for call in api._print_color_func.call_args_list]
        self.assertIn('Gemini API response: 404 NOT_FOUND: models/test-model is not found '
                      'for API version v1beta.', printed)
        self.assertFalse(any('offline-key' in line for line in printed))

    def test_non_api_errors_do_not_show_exception_text(self):
        api = self.make_api(MagicMock(side_effect=httpx.ConnectError('private-response')))
        api._attempt_api_setup('offline-key', 'test', 'test-model')
        self.assertNotIn('private-response', str(api._print_color_func.call_args_list))

    def configure_saved_model(self, model, handler, *, tty, answers=()):
        """Run configure() with a gemini_config.json that names ``model``."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config_path = os.path.join(directory.name, 'gemini_config.json')
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump({'gemini_api_key': 'offline-key', 'chosen_model_name': model}, f)
        api = self.make_api(handler)
        read_line = MagicMock(side_effect=list(answers))
        with patch('game_engine.gemini_interactions.API_CONFIG_FILE', self.config_path), \
                patch.dict(os.environ, {'GEMINI_API_KEY': ''}), \
                patch('sys.stdin.isatty', return_value=tty):
            result = api.configure(api._print_color_func, read_line)
        with open(self.config_path, encoding='utf-8') as f:
            saved = json.load(f)
        return SimpleNamespace(
            api=api, result=result, saved=saved, answers=read_line,
            files=os.listdir(directory.name),
            requested=[requested_model(call.args[0]) for call in handler.call_args_list])

    def test_unavailable_saved_model_falls_back_to_the_default(self):
        handler = MagicMock(side_effect=serve_all_but_retired)
        run = self.configure_saved_model(RETIRED_MODEL, handler, tty=False, answers=['n'])
        self.assertEqual(run.result, {'api_configured': True, 'low_ai_preference': False})
        self.assertEqual(run.requested, [RETIRED_MODEL, DEFAULT_GEMINI_MODEL_NAME])
        self.assertEqual(run.api.model.model_name, DEFAULT_GEMINI_MODEL_NAME)
        # The key stays, and the model that works replaces the retired one.
        self.assertEqual(run.files, ['gemini_config.json'])
        self.assertEqual(run.saved, {'gemini_api_key': 'offline-key',
                                     'chosen_model_name': DEFAULT_GEMINI_MODEL_NAME})
        run.answers.assert_called_once()  # Only the Low AI prompt.

    def test_unavailable_saved_model_offers_the_model_menu_on_a_terminal(self):
        handler = MagicMock(side_effect=serve_all_but_retired)
        run = self.configure_saved_model(RETIRED_MODEL, handler, tty=True, answers=['3', 'n'])
        self.assertEqual(run.result, {'api_configured': True, 'low_ai_preference': False})
        self.assertIn('Enter your choice', run.answers.call_args_list[0].args[0])
        self.assertEqual(run.requested, [RETIRED_MODEL, 'gemini-3.5-flash-lite'])
        self.assertEqual(run.saved['chosen_model_name'], 'gemini-3.5-flash-lite')

    def test_replacement_model_is_saved_before_the_low_ai_prompt(self):
        handler = MagicMock(side_effect=serve_all_but_retired)
        with self.assertRaises(EOFError):
            self.configure_saved_model(RETIRED_MODEL, handler, tty=False, answers=[EOFError])
        with open(self.config_path, encoding='utf-8') as f:
            self.assertEqual(json.load(f)['chosen_model_name'], DEFAULT_GEMINI_MODEL_NAME)

    def test_saved_key_is_kept_when_no_model_is_available(self):
        # Without a terminal, the default is the only other model to try.
        for saved_model, requested in (
            (RETIRED_MODEL, [RETIRED_MODEL, DEFAULT_GEMINI_MODEL_NAME]),
            (DEFAULT_GEMINI_MODEL_NAME, [DEFAULT_GEMINI_MODEL_NAME]),
        ):
            with self.subTest(saved_model=saved_model):
                handler = MagicMock(side_effect=lambda request: not_found(requested_model(request)))
                run = self.configure_saved_model(saved_model, handler, tty=False)
                self.assertEqual(run.result, {'api_configured': False, 'low_ai_preference': False})
                self.assertEqual(run.requested, requested)
                self.assertIsNone(run.api.model)
                self.assertEqual(run.files, ['gemini_config.json'])
                self.assertEqual(run.saved['chosen_model_name'], saved_model)
                run.answers.assert_not_called()

    def verified_parser(self, handler, model=DEFAULT_GEMINI_MODEL_NAME):
        """A parser for a key verified with ``model``, and the requests made after that."""
        requests = []

        def record(request):
            requests.append(request)
            return handler(request)

        api = self.make_api(record)
        self.assertIs(api._attempt_api_setup('offline-key', 'test', model), SetupResult.VERIFIED)
        requests.clear()
        return NaturalLanguageParser(api), requests

    def test_intent_parser_asks_flash_lite_for_minimal_thinking(self):
        parser, requests = self.verified_parser(lambda request: reply(json.dumps(MOVE_TO_TAVERN)))
        self.assertEqual(parser.parse_player_intent('walk over to the tavern', TAVERN_SCENE),
                         MOVE_TO_TAVERN)
        self.assertEqual([requested_model(r) for r in requests], [INTENT_GEMINI_MODEL_NAME])
        config = generation_config(requests[0])
        self.assertEqual(config['maxOutputTokens'], NaturalLanguageParser.INTENT_MAX_OUTPUT_TOKENS)
        self.assertEqual(list(config['thinkingConfig'].values()), ['MINIMAL'])

    def test_intent_parser_falls_back_to_the_verified_model(self):
        failures = {
            'not served': not_found(INTENT_GEMINI_MODEL_NAME),
            'no permission': api_error(403, 'PERMISSION_DENIED', 'Permission denied.'),
            'settings rejected': api_error(400, 'INVALID_ARGUMENT', 'Thinking not supported.'),
            'cut off while thinking': httpx.Response(200, json={
                'candidates': [{'content': {}, 'finishReason': 'MAX_TOKENS'}],
                'usageMetadata': {'thoughtsTokenCount': 1024}}),
            'offline': httpx.ConnectError('offline'),
        }
        for name, failure in failures.items():
            with self.subTest(name):
                def respond(request, failure=failure):
                    if requested_model(request) != INTENT_GEMINI_MODEL_NAME:
                        return reply(json.dumps(MOVE_TO_TAVERN))
                    if isinstance(failure, Exception):
                        raise failure
                    return failure

                parser, requests = self.verified_parser(respond)
                for words in ('walk over to the tavern', 'head for the tavern'):
                    parsed = parser.parse_player_intent(words, TAVERN_SCENE)
                    self.assertEqual(parsed, MOVE_TO_TAVERN)
                # Flash-Lite fails once; later inputs go straight to the verified model.
                self.assertEqual([requested_model(r) for r in requests], [
                    INTENT_GEMINI_MODEL_NAME, DEFAULT_GEMINI_MODEL_NAME, DEFAULT_GEMINI_MODEL_NAME])
                fallback = generation_config(requests[1])
                self.assertNotIn('thinkingConfig', fallback)
                self.assertEqual(fallback['maxOutputTokens'],
                                 NaturalLanguageParser.INTENT_MAX_OUTPUT_TOKENS)

    def test_rejected_thinking_setting_retries_flash_lite_without_it(self):
        # A key verified with Flash-Lite falls back to that same model, left on its defaults.
        def respond(request):
            if 'thinkingConfig' in generation_config(request):
                return api_error(400, 'INVALID_ARGUMENT', 'Thinking level not supported.')
            return reply(json.dumps(MOVE_TO_TAVERN))

        parser, requests = self.verified_parser(respond, model=INTENT_GEMINI_MODEL_NAME)
        self.assertEqual(parser.parse_player_intent('walk over to the tavern', TAVERN_SCENE),
                         MOVE_TO_TAVERN)
        self.assertEqual([requested_model(r) for r in requests], [INTENT_GEMINI_MODEL_NAME] * 2)

    def test_intent_parser_gives_up_when_both_models_fail(self):
        calls = []

        def respond(request):
            # Only the verification call succeeds.
            calls.append(request)
            return reply('test') if len(calls) == 1 else not_found(requested_model(request))

        parser, requests = self.verified_parser(respond)
        self.assertEqual(parser.parse_player_intent('walk over to the tavern', TAVERN_SCENE),
                         {'intent': 'unknown', 'target': '', 'confidence': 0.0})
        self.assertEqual([requested_model(r) for r in requests],
                         [INTENT_GEMINI_MODEL_NAME, DEFAULT_GEMINI_MODEL_NAME])

    def test_transport_timeout_falls_back(self):
        api = self.make_api(MagicMock(side_effect=httpx.ReadTimeout('private-response')))
        result = api._attempt_api_setup('offline-key', 'test', 'test-model')
        self.assertIs(result, SetupResult.FAILED)
        self.assertIsNone(api.client)

    def test_empty_blocked_and_invalid_generation_results(self):
        for body in ({}, {'candidates': []}, {'promptFeedback': {'blockReason': 'SAFETY'}}):
            with self.subTest(body=body):
                handler = MagicMock(return_value=httpx.Response(200, json=body))
                api = self.make_api(handler)
                # Set up the real client without making the verification request.
                api.client = api.client_factory(api_key='offline-key', http_options={
                    'timeout': 10_000, 'retry_options': {'attempts': 1}})
                api.model = api._GeminiModelAdapter(api.client, 'test-model')
                self.assertFalse(is_usable_ai_text(api._generate_content_with_fallback('hello')))
                self.assertEqual(handler.call_count, 1)

    def test_only_nonempty_narrative_strings_are_usable(self):
        for value in (None, '', '   ', False, 42, {}, ['text'], '  (OOC: failed)'):
            self.assertFalse(is_usable_ai_text(value), repr(value))
        self.assertTrue(is_usable_ai_text('A cold wind.'))
