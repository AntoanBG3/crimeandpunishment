"""Malformed generated text must never become blank narration or diagnostic content."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from game_engine.game_state import Game
from game_engine.gemini_interactions import GeminiAPI, NaturalLanguageParser


class TestAIFallbackBoundary(unittest.TestCase):
    def test_malformed_intent_text_and_confidence_fail_closed(self):
        responses = [42, [], None]
        for confidence in (float('nan'), float('inf'), 10 ** 400):
            responses.append(json.dumps({'intent': 'take', 'target': 'coin',
                                         'confidence': confidence}))
        for response in responses:
            with self.subTest(response=str(response)[:60]):
                api = GeminiAPI()
                api.model = SimpleNamespace(generate_content=lambda *a, **k: SimpleNamespace(text=response))
                api._load_genai = MagicMock(return_value=False)
                parsed = NaturalLanguageParser(api).parse_player_intent('pick it up', {'items': ['coin']})
                self.assertEqual(parsed['confidence'], 0)

    def test_empty_text_returns_failure_marker_without_logging_the_prompt(self):
        for text in ('', '  \n', None, 42):
            with self.subTest(text=text):
                api = GeminiAPI()
                api.model = SimpleNamespace(generate_content=lambda *a, **k: SimpleNamespace(text=text))
                api._log_message = MagicMock()
                result = api._generate_content_with_fallback('private-player-conversation')
                self.assertTrue(result.startswith('(OOC:'))
                self.assertNotIn('private-player-conversation', str(api._log_message.call_args_list))

    def test_unusable_newspaper_response_uses_static_content(self):
        for text in ('', '  ', False, 42, '  (OOC: failed)'):
            with self.subTest(text=text):
                api = MagicMock()
                api.get_newspaper_article_snippet.return_value = text
                game = Game(gemini_api=api, terminal_io=MagicMock())
                game.world_manager.load_all_characters()
                game.player_character = game.all_character_objects['Rodion Raskolnikov']
                self.assertTrue(game._handle_read_item('old newspaper', {'readable': True}, None))
                self.assertIn('NEWS (STATIC)', game.player_character.journal_entries[-1])
