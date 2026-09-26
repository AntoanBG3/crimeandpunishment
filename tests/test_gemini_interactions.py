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


if __name__ == "__main__":
    unittest.main()


class _Models:
    """Client stand-in: the verification call returns ``reply`` or raises ``error``."""

    def __init__(self, reply="test", error=None):
        self.reply = reply
        self.error = error

    def generate_content(self, **_kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.reply)


class TestSavedKeyRetention(unittest.TestCase):
    """gemini_config.json is moved aside only when the service rejects the key."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        config_path = os.path.join(self.directory, "gemini_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": "saved-key", "chosen_model_name": "gemini-3.5-flash"}, f)
        for patcher in (
            patch("game_engine.gemini_interactions.API_CONFIG_FILE", config_path),
            patch.dict(os.environ),
            # A terminal, so an unwanted fall-through to the manual key prompt shows up.
            patch("sys.stdin.isatty", return_value=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop("GEMINI_API_KEY", None)
        self.printed = MagicMock()
        self.replies = MagicMock(return_value="skip")

    def configure(self, models):
        api = GeminiAPI(
            sdk=SimpleNamespace(),
            client_factory=lambda **_kwargs: SimpleNamespace(models=models),
        )
        return api, api.configure(self.printed, self.replies)

    def printed_text(self):
        return "\n".join(str(call.args[0]) for call in self.printed.call_args_list)

    def test_offline_start_keeps_saved_key_and_uses_placeholders(self):
        for error in (ConnectionError("network unreachable"), TimeoutError("read timed out")):
            with self.subTest(error=type(error).__name__):
                api, result = self.configure(_Models(error=error))
                self.assertEqual(result, {"api_configured": False, "low_ai_preference": False})
                self.assertIsNone(api.model)
                self.assertEqual(os.listdir(self.directory), ["gemini_config.json"])
                self.replies.assert_not_called()
                self.assertIn("The file was kept", self.printed_text())

    def test_rejected_key_is_moved_aside_before_the_key_prompt(self):
        error = RuntimeError("400 INVALID_ARGUMENT. API key not valid. Please pass a valid API key.")
        api, result = self.configure(_Models(error=error))
        self.assertEqual(result, {"api_configured": False, "low_ai_preference": False})
        self.assertIsNone(api.model)
        self.assertEqual(
            os.listdir(self.directory), ["gemini_config.json.failed_setup_with_gemini-3.5-flash"]
        )
        self.replies.assert_called_once()
        self.assertIn("Gemini API key", self.replies.call_args.args[0])

    def test_mistyped_values_count_as_a_malformed_file(self):
        config_path = os.path.join(self.directory, "gemini_config.json")
        rejected = _Models(error=RuntimeError("API key not valid."))
        for config in (
            {"gemini_api_key": "saved-key", "chosen_model_name": None},
            {"gemini_api_key": 123},
        ):
            with self.subTest(config=config):
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f)
                self.configure(rejected)
                self.assertEqual(
                    os.listdir(self.directory), ["gemini_config.json.initial_config_error"]
                )
                os.remove(config_path + ".initial_config_error")

    def test_eof_after_verification_keeps_saved_key(self):
        self.replies.side_effect = EOFError
        with self.assertRaises(EOFError):
            self.configure(_Models())
        self.assertEqual(os.listdir(self.directory), ["gemini_config.json"])
        self.assertNotIn("Error processing config file", self.printed_text())
