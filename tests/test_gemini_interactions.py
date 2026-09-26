import json
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import tempfile
from types import SimpleNamespace

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.gemini_interactions import GeminiAPI  # noqa: E402
from game_engine.character_module import Character  # noqa: E402
from tests.test_command_handler import _Model  # noqa: E402


class TestGeminiInteractions(unittest.TestCase):
    def setUp(self):
        self.api = GeminiAPI()
        self.api.model = MagicMock()
        self.player = Character(
            "Test Player",
            "A brave adventurer.",
            "Hello!",
            "start_location",
            ["start_location"],
        )

    def test_get_atmospheric_details(self):
        self.api.model.generate_content.return_value.text = "The air is thick with mystery."
        details = self.api.get_atmospheric_details(
            self.player, "a dark room", "night", "a strange noise", "find the key"
        )
        self.assertEqual(details, "The air is thick with mystery.")

    def test_get_rumor_or_gossip(self):
        npc = Character("Test NPC", "A gossip.", "Psst!", "market", ["market"])
        self.api.model.generate_content.return_value.text = "I heard the king is a frog."
        rumor = self.api.get_rumor_or_gossip(
            npc,
            "market",
            "day",
            "The king is missing.",
            2,
            "neutral",
            "get the latest scoop",
        )
        self.assertEqual(rumor, "I heard the king is a frog.")

    def test_get_dream_sequence(self):
        self.api.model.generate_content.return_value.text = "You dream of electric sheep."
        dream = self.api.get_dream_sequence(
            self.player,
            "You saw a unicorn.",
            "Find the unicorn.",
            "You are friends with the unicorn.",
        )
        self.assertEqual(dream, "You dream of electric sheep.")


class TestSavedKeyRetention(unittest.TestCase):
    """gemini_config.json is moved aside only when the service rejects the key."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        self.config_path = os.path.join(self.directory, "gemini_config.json")
        self.write_config({"gemini_api_key": "saved-key", "chosen_model_name": "gemini-3.8-flash"})
        for patcher in (
            patch("game_engine.gemini_interactions.API_CONFIG_FILE", self.config_path),
            patch.dict(os.environ, {"GEMINI_API_KEY": ""}),
            # A terminal, so an unwanted fall-through to the manual key prompt shows up.
            patch("sys.stdin.isatty", return_value=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.printed = MagicMock()
        self.replies = MagicMock(return_value="skip")

    def write_config(self, config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def configure(self, models):
        api = GeminiAPI(
            sdk=SimpleNamespace(),
            client_factory=lambda **_kwargs: SimpleNamespace(models=models),
        )
        return api, api.configure(self.printed, self.replies)

    def printed_text(self):
        return "\n".join(str(call.args[0]) for call in self.printed.call_args_list)

    def test_offline_start_keeps_saved_key_and_uses_placeholders(self):
        api, result = self.configure(_Model(error=ConnectionError("network unreachable")))
        self.assertEqual(result, {"api_configured": False, "low_ai_preference": False})
        self.assertIsNone(api.model)
        self.assertEqual(os.listdir(self.directory), ["gemini_config.json"])
        self.replies.assert_not_called()
        self.assertIn("The file was kept", self.printed_text())

    def test_rejected_key_is_moved_aside_before_the_key_prompt(self):
        error = RuntimeError("400 INVALID_ARGUMENT. API key not valid. Please pass a valid API key.")
        api, result = self.configure(_Model(error=error))
        self.assertEqual(result, {"api_configured": False, "low_ai_preference": False})
        self.assertIsNone(api.model)
        self.assertEqual(
            os.listdir(self.directory), ["gemini_config.json.failed_setup_with_gemini-3.8-flash"]
        )
        self.replies.assert_called_once()
        self.assertIn("Gemini API key", self.replies.call_args.args[0])

    def test_mistyped_values_count_as_a_malformed_file(self):
        rejected = _Model(error=RuntimeError("API key not valid."))
        for config in (
            {"gemini_api_key": "saved-key", "chosen_model_name": None},
            {"gemini_api_key": 123},
        ):
            with self.subTest(config=config):
                self.write_config(config)
                self.configure(rejected)
                self.assertEqual(
                    os.listdir(self.directory), ["gemini_config.json.initial_config_error"]
                )
                os.remove(self.config_path + ".initial_config_error")

    def test_eof_after_verification_keeps_saved_key(self):
        self.replies.side_effect = EOFError
        with self.assertRaises(EOFError):
            self.configure(_Model())
        self.assertEqual(os.listdir(self.directory), ["gemini_config.json"])
        self.assertNotIn("Error processing config file", self.printed_text())


if __name__ == "__main__":
    unittest.main()
