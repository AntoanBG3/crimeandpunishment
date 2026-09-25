"""Exercise the actual installed SDK and serialization with an offline transport."""

import unittest
from unittest.mock import MagicMock

import httpx
from google import genai

from game_engine.gemini_interactions import GeminiAPI, is_usable_ai_text


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

    def test_http_failures_fall_back_without_retries(self):
        for status in (401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                handler = MagicMock(return_value=httpx.Response(status, json={
                    'error': {'code': status, 'message': 'private-response', 'status': 'UNKNOWN'}}))
                api = self.make_api(handler)
                self.assertFalse(api._attempt_api_setup('offline-key', 'test', 'test-model'))
                self.assertEqual(handler.call_count, 1)
                self.assertIsNone(api.client)

    def test_transport_timeout_falls_back(self):
        api = self.make_api(MagicMock(side_effect=httpx.ReadTimeout('private-response')))
        self.assertFalse(api._attempt_api_setup('offline-key', 'test', 'test-model'))
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
