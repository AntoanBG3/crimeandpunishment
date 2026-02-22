import unittest
from unittest.mock import patch
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.character_module import Character  # noqa: E402


class TestCharacterModule(unittest.TestCase):
    def setUp(self):
        self.character = Character(
            name="Test Character",
            persona="A character for testing.",
            greeting="Hello, tester!",
            default_location="test_room",
            accessible_locations=["test_room", "another_room"],
            objectives=[],
            inventory_items=[],
            schedule={},
        )
        self.character.skills = {"Observation": 2}

    def test_to_dict(self):
        char_dict = self.character.to_dict()
        expected_dict = {
            "name": "Test Character",
            "current_location": "test_room",
            "is_player": False,
            "conversation_histories": {},
            "memory_about_player": [],
            "journal_entries": [],
            "relationship_with_player": 0,
            "npc_relationships": {},
            "skills": {"Observation": 2},
            "objectives": [],
            "inventory": [],
            "apparent_state": "normal",
            "psychology": {"suspicion": 0, "fear": 0, "respect": 50},
        }
        self.assertEqual(char_dict, expected_dict)

    def test_to_dict_includes_custom_psychology(self):
        self.character.psychology = {"suspicion": 35, "fear": 10, "respect": 65}

        char_dict = self.character.to_dict()

        self.assertEqual(char_dict["psychology"], {"suspicion": 35, "fear": 10, "respect": 65})

    def test_from_dict(self):
        char_data = {
            "name": "Loaded Character",
            "persona": "Loaded persona.",
            "greeting": "Loaded greeting.",
            "default_location": "loaded_location",
            "accessible_locations": ["loaded_location"],
            "objectives": [],
            "inventory": [],
            "schedule": {},
            "skills": {"Persuasion": 3},
            "is_player": True,
            "current_location": "loaded_location",
            "apparent_state": "happy",
            "relationship_with_player": 5,
            "conversation_histories": {},
            "memory_about_player": [],
            "journal_entries": [],
        }
        static_data = {
            "persona": "Original persona.",
            "greeting": "Original greeting.",
            "default_location": "original_location",
            "accessible_locations": ["original_location"],
        }
        loaded_char = Character.from_dict(char_data, static_data)
        self.assertEqual(loaded_char.name, "Loaded Character")
        self.assertEqual(loaded_char.skills["Persuasion"], 3)
        self.assertTrue(loaded_char.is_player)

    def test_check_skill_success(self):
        with patch("game_engine.character_module.random.randint", return_value=4):
            self.assertTrue(self.character.check_skill("Observation", 2))

    def test_check_skill_failure(self):
        with patch("game_engine.character_module.random.randint", return_value=1):
            self.assertFalse(self.character.check_skill("Observation", 2))


if __name__ == "__main__":
    unittest.main()
