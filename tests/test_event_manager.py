import unittest
from unittest.mock import MagicMock, patch
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.event_manager import EventManager

class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_game = MagicMock()
        self.mock_game.game_time = 10
        self.mock_game.current_location_name = "Test Location"
        self.mock_game.player_character = MagicMock()
        self.mock_game.player_character.name = "Test Player"

        self.event_manager = EventManager(self.mock_game)

        # The EventManager uses a list of dicts called story_events, not a dict called EVENTS
        self.event_manager.story_events = []
        self.event_manager.triggered_events = set()
        # event_last_triggered is not used by the check_and_trigger_events method, but it is good practice
        # to be aware of it if testing other parts of the event system in the future.

    def test_event_triggered_when_condition_met(self):
        mock_action = MagicMock()
        test_event = {
            "id": "test_event_1",
            "trigger": lambda: True,
            "action": mock_action,
            "one_time": True
        }
        self.event_manager.story_events.append(test_event)

        result = self.event_manager.check_and_trigger_events()

        self.assertTrue(result)
        mock_action.assert_called_once_with() # The action is called with no arguments
        self.assertIn("test_event_1", self.event_manager.triggered_events)

    def test_event_not_triggered_if_condition_false(self):
        mock_action = MagicMock()
        test_event = {
            "id": "test_event_2",
            "trigger": lambda: False,
            "action": mock_action,
            "one_time": True
        }
        self.event_manager.story_events.append(test_event)

        result = self.event_manager.check_and_trigger_events()

        self.assertFalse(result)
        mock_action.assert_not_called()

    def test_one_time_event_not_triggered_twice(self):
        mock_action = MagicMock()
        test_event = {
            "id": "one_time_event",
            "trigger": lambda: True,
            "action": mock_action,
            "one_time": True
        }
        self.event_manager.story_events.append(test_event)
        self.event_manager.triggered_events.add("one_time_event") # Pretend it has already run

        result = self.event_manager.check_and_trigger_events()

        self.assertFalse(result) # Should return False as no new event was triggered
        mock_action.assert_not_called()

    def test_repeatable_event_can_trigger_again(self):
        mock_action = MagicMock()
        test_event = {
            "id": "repeatable_event",
            "trigger": lambda: True,
            "action": mock_action,
            "one_time": False
        }
        self.event_manager.story_events.append(test_event)
        # Even if it was "triggered" before, as long as the "_recent" flag is not set, it should run.
        # The action itself is responsible for setting the recent flag.
        self.event_manager.triggered_events.add("repeatable_event")

        result = self.event_manager.check_and_trigger_events()

        self.assertTrue(result)
        mock_action.assert_called_once_with()

    def test_repeatable_event_not_triggered_if_recent_flag_set(self):
        mock_action = MagicMock()
        test_event = {
            "id": "repeatable_event_recent",
            "trigger": lambda: True,
            "action": mock_action,
            "one_time": False
        }
        self.event_manager.story_events.append(test_event)
        self.event_manager.triggered_events.add("repeatable_event_recent_recent") # Set the recent flag

        result = self.event_manager.check_and_trigger_events()

        self.assertFalse(result)
        mock_action.assert_not_called()

if __name__ == '__main__':
    unittest.main()
