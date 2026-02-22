import unittest
from unittest.mock import MagicMock
import os
import sys

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
