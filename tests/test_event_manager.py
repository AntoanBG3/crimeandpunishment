import random
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.event_manager import EventManager  # noqa: E402
from game_engine.game_state import Game  # noqa: E402
from game_engine.static_fallbacks import STATIC_NPC_NPC_INTERACTIONS  # noqa: E402


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
            "one_time": True,
        }
        self.event_manager.story_events.append(test_event)

        result = self.event_manager.check_and_trigger_events()

        self.assertTrue(result)
        mock_action.assert_called_once_with()  # The action is called with no arguments
        self.assertIn("test_event_1", self.event_manager.triggered_events)

    def test_event_not_triggered_if_condition_false(self):
        mock_action = MagicMock()
        test_event = {
            "id": "test_event_2",
            "trigger": lambda: False,
            "action": mock_action,
            "one_time": True,
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
            "one_time": True,
        }
        self.event_manager.story_events.append(test_event)
        self.event_manager.triggered_events.add("one_time_event")  # Pretend it has already run

        result = self.event_manager.check_and_trigger_events()

        self.assertFalse(result)  # Should return False as no new event was triggered
        mock_action.assert_not_called()

    def test_repeatable_event_can_trigger_again(self):
        mock_action = MagicMock()
        test_event = {
            "id": "repeatable_event",
            "trigger": lambda: True,
            "action": mock_action,
            "one_time": False,
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
            "one_time": False,
        }
        self.event_manager.story_events.append(test_event)
        self.event_manager.triggered_events.add(
            "repeatable_event_recent_recent"
        )  # Set the recent flag

        result = self.event_manager.check_and_trigger_events()

        self.assertFalse(result)
        mock_action.assert_not_called()


class TestStoryEventsWithAuthoredData(unittest.TestCase):
    def setUp(self):
        self.game = Game(rng=random.Random(0))
        self.game.world_manager.load_all_characters()
        self.game.player_character = self.game.all_character_objects["Sonya Marmeladova"]
        self.game.player_character.is_player = True
        self.game.low_ai_data_mode = True
        for wrapper in ("_print_color", "_print_narrative", "_print_dialogue"):
            patch.object(self.game, wrapper).start()

    def tearDown(self):
        patch.stopall()

    def test_katerina_schedule_brings_her_public_lament_within_reach(self):
        # Only schedules move NPCs, and the lament needs her in the Haymarket in
        # the Afternoon or Evening.
        katerina = self.game.all_character_objects["Katerina Ivanovna Marmeladova"]
        self.game.current_location_name = "Haymarket Square"
        self.game.game_time = 130  # Evening
        with patch.object(self.game.rng, "random", return_value=0.0):
            self.game.world_manager.update_npc_locations_by_schedule()
            self.assertEqual(katerina.current_location, "Haymarket Square")
            self.assertTrue(self.game.event_manager.check_and_trigger_events())
        self.assertIn(
            "katerina_ivanovna_public_lament_recent", self.game.event_manager.triggered_events
        )
        self.assertIn("Katerina Ivanovna caused a public scene.", self.game.key_events_occurred)

    def test_static_npc_exchanges_name_the_real_speakers(self):
        # The static lines serve a configured key in LOW-AI mode and unusable AI text.
        razumikhin = self.game.all_character_objects["Dmitri Razumikhin"]
        nastasya = self.game.all_character_objects["Nastasya"]
        self.game.npcs_in_current_location = [razumikhin, nastasya]
        names = {razumikhin.name, nastasya.name}
        api = self.game.gemini_api
        for low_ai, ai_text in ((True, "Unused API text"), (False, "(OOC: blocked)")):
            for template in STATIC_NPC_NPC_INTERACTIONS:
                self.game.low_ai_data_mode = low_ai
                with self.subTest(low_ai=low_ai, template=template), \
                        patch.object(api, "model", object()), \
                        patch.object(api, "get_npc_to_npc_interaction",
                                     return_value=ai_text) as generate, \
                        patch.object(self.game.rng, "choice", return_value=template), \
                        patch.object(self.game, "_print_color") as print_color, \
                        patch.object(self.game, "_print_dialogue") as print_dialogue:
                    self.assertTrue(self.game.event_manager.attempt_npc_npc_interaction())
                    self.assertEqual(generate.called, not low_ai)
                    speakers = {call.args[0] for call in print_dialogue.call_args_list}
                    self.assertLessEqual(speakers, names)
                    printed = [str(call.args[0]) for call in print_color.call_args_list]
                    printed += [str(call.args[1]) for call in print_dialogue.call_args_list]
                    self.assertFalse([line for line in printed if "NPC" in line])
                    self.assertTrue(speakers or any(name in " ".join(printed) for name in names))


if __name__ == "__main__":
    unittest.main()
