import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to sys.path to allow imports from game_engine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.event_manager import EventManager
from game_engine.game_state import Game
from game_engine.character_module import Character

class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_game = MagicMock(spec=Game)
        self.mock_game.gemini_api = MagicMock()
        self.mock_game.player_character = MagicMock(spec=Character)
        self.mock_game.player_character.name = "Test Player"
        self.mock_game.player_character.apparent_state = "normal"
        self.mock_game.all_character_objects = {}
        self.mock_game.current_location_name = "Test Location"
        self.mock_game.game_time = 0
        self.mock_game.player_notoriety_level = 0
        self.mock_game.triggered_events = set()
        self.mock_game.known_facts_about_crime = []
        self.mock_game.key_events_occurred = []
        self.mock_game.last_significant_event_summary = ""
        self.mock_game.low_ai_data_mode = False
        self.mock_game._print_color = MagicMock()
        self.mock_game.get_current_time_period = MagicMock(return_value="Morning")

        self.event_manager = EventManager(self.mock_game)
        self.event_manager.triggered_events = self.mock_game.triggered_events

    def test_initialization(self):
        self.assertEqual(self.event_manager.game, self.mock_game)
        self.assertIsInstance(self.event_manager.story_events, list)

    def test_trigger_marmeladov_encounter(self):
        self.mock_game.player_character.name = "Rodion Raskolnikov"
        self.mock_game.current_location_name = "Tavern"
        self.mock_game.game_time = 30
        self.event_manager.triggered_events.clear()
        self.assertTrue(self.event_manager.trigger_marmeladov_encounter())

    def test_trigger_letter_from_mother(self):
        self.mock_game.player_character.name = "Rodion Raskolnikov"
        self.mock_game.current_location_name = "Raskolnikov's Garret"
        self.mock_game.game_time = 20
        self.event_manager.triggered_events.clear()
        self.assertTrue(self.event_manager.trigger_letter_from_mother())

    def test_trigger_katerina_public_lament(self):
        katerina_mock = MagicMock(spec=Character)
        katerina_mock.current_location = "Haymarket Square"
        self.mock_game.all_character_objects = {"Katerina Ivanovna Marmeladova": katerina_mock}
        self.mock_game.current_location_name = "Haymarket Square"
        self.mock_game.get_current_time_period.return_value = "Afternoon"
        with patch('random.random', return_value=0.05):
            self.assertTrue(self.event_manager.trigger_katerina_public_lament())

    def test_trigger_find_anonymous_note(self):
        self.mock_game.player_character.name = "Rodion Raskolnikov"
        self.mock_game.player_notoriety_level = 2.0
        self.mock_game.current_location_name = "Raskolnikov's Garret"
        with patch('random.random', return_value=0.1):
            self.assertTrue(self.event_manager.trigger_find_anonymous_note())

    def test_trigger_street_life_haymarket(self):
        self.mock_game.current_location_name = "Haymarket Square"
        with patch('random.random', return_value=0.05):
            self.assertTrue(self.event_manager.trigger_street_life_haymarket())

    def test_action_marmeladov_encounter(self):
        self.event_manager.action_marmeladov_encounter()
        self.mock_game.player_character.add_player_memory.assert_called()
        self.assertIn("encountered Marmeladov in the tavern.", self.mock_game.last_significant_event_summary)

    def test_action_letter_from_mother(self):
        self.mock_game.player_character.has_item.return_value = False
        self.event_manager.action_letter_from_mother()
        self.mock_game.player_character.add_to_inventory.assert_called_with("mother's letter")
        self.assertIn("received a letter from his mother", self.mock_game.last_significant_event_summary)

    def test_action_katerina_public_lament(self):
        katerina_mock = MagicMock(spec=Character)
        self.mock_game.all_character_objects = {"Katerina Ivanovna Marmeladova": katerina_mock}
        self.event_manager.action_katerina_public_lament()
        self.assertEqual(katerina_mock.apparent_state, "highly agitated and feverish")
        self.assertIn("witnessed Katerina Ivanovna's public outburst", self.mock_game.last_significant_event_summary)

    def test_action_find_anonymous_note(self):
        with patch('game_engine.event_manager.DEFAULT_ITEMS', {"Anonymous Note": {"readable": True}}):
            self.mock_game.dynamic_location_items = {"Raskolnikov's Garret": []}
            self.mock_game.current_location_name = "Raskolnikov's Garret"
            self.event_manager.action_find_anonymous_note()
            self.assertIn("Anonymous Note", [item["name"] for item in self.mock_game.dynamic_location_items["Raskolnikov's Garret"]])
            self.assertEqual(self.mock_game.player_character.apparent_state, "paranoid")

    def test_action_street_life_haymarket(self):
        with patch('game_engine.event_manager.STATIC_STREET_LIFE_EVENTS', ["A street event happened."]):
            with patch('random.choice', return_value="A street event happened."):
                self.mock_game.gemini_api.get_street_life_event_description = MagicMock(return_value="A street event happened.")
                self.event_manager.action_street_life_haymarket()
                self.mock_game._print_color.assert_any_call("\n\x1b[2m(Nearby, A street event happened.)\x1b[0m", '\x1b[2m')

if __name__ == '__main__':
    unittest.main()