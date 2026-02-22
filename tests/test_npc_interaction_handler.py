import unittest
from unittest.mock import patch, MagicMock
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game
from game_engine.character_module import Character
from game_engine.game_config import Colors

class TestNPCInteractionHandler(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = Character(
            name="Rodion Raskolnikov",
            persona="A poor student",
            greeting="...",
            default_location="Room",
            accessible_locations=["Room"]
        )
        self.game.player_character.inventory = []
        self.game.player_character.apparent_state = "normal"
        self.game.player_character.get_notable_carried_items_summary = MagicMock(return_value="nothing")
        self.game.player_character.get_objectives_summary = MagicMock(return_value="none")
        self.game.player_notoriety_level = 0.0
        
        self.npc = Character(
            name="Porfiry Petrovich",
            persona="Detective",
            greeting="Ah, my dear fellow!",
            default_location="Room",
            accessible_locations=["Room"]
        )
        self.npc.relationship_with_player = 0
        self.npc.conversation_histories = {}
        self.npcmock_get_objective = MagicMock()
        self.npc.get_objective_by_id = self.npcmock_get_objective
        self.npcmock_get_stage = MagicMock()
        self.npc.get_current_stage_for_objective = self.npcmock_get_stage
        
        self.game.npcs_in_current_location = [self.npc]
        self.game.all_character_objects = {"Porfiry Petrovich": self.npc}
        self.game.current_location_name = "Room"

        # Mocking systems
        self.game.gemini_api.model = MagicMock()
        self.game.gemini_api.get_npc_dialogue = MagicMock(return_value="Interesting.")
        self.game.gemini_api.get_npc_dialogue_persuasion_attempt = MagicMock(return_value="You don't say!")
        self.game.world_manager.advance_time = MagicMock()
        self.game.world_manager.get_current_time_period = MagicMock(return_value="Day")
        self.game.event_manager.check_and_trigger_events = MagicMock(return_value=False)
        self.game.get_relationship_text = MagicMock(return_value="neutral")
        self.game._get_recent_events_summary = MagicMock(return_value="nothing")
        self.game._get_objectives_summary = MagicMock(return_value="none")

        self.mock_print_color = patch.object(self.game, "_print_color").start()
        self.mock_input_color = patch.object(self.game, "_input_color").start()
        self.mock_print = patch("builtins.print").start()

    def tearDown(self):
        patch.stopall()

    def test_talk_to_no_argument(self):
        action, atmo = self.game._handle_talk_to_command(None)
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("Who do you want to talk to?", Colors.RED)

    def test_talk_to_nobody_here(self):
        self.game.npcs_in_current_location = []
        action, atmo = self.game._handle_talk_to_command("Porfiry")
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("There's no one here to talk to.", Colors.DIM)

    def test_talk_to_no_player(self):
        self.game.player_character = None
        action, atmo = self.game._handle_talk_to_command("Porfiry")
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("Cannot talk: Player character not available.", Colors.RED)

    def test_talk_to_not_found(self):
        action, atmo = self.game._handle_talk_to_command("Ghost")
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("You don't see anyone named 'ghost' here.", Colors.RED)

    def test_talk_to_porfiry_special_state(self):
        self.npcmock_get_objective.return_value = {"active": True}
        self.npcmock_get_stage.return_value = {"stage_id": "encourage_confession"}
        self.mock_input_color.side_effect = ["Farewell"] # Exit immediately
        
        self.game._handle_talk_to_command("Porfiry")
        self.assertEqual(self.npc.apparent_state, "intensely persuasive")
        
    def test_talk_to_history_command(self):
        self.mock_input_color.side_effect = ["history", "Farewell"]
        self.game._handle_talk_to_command("Porfiry")
        self.mock_print_color.assert_any_call("\n--- Recent Conversation History ---", Colors.CYAN + Colors.BOLD)

    def test_talk_to_empty_dialogue(self):
        self.mock_input_color.side_effect = ["", "Farewell"]
        self.game._handle_talk_to_command("Porfiry")
        self.mock_print_color.assert_any_call("You remain silent for a moment.", Colors.DIM)

    def test_talk_to_no_gemini_model(self):
        self.game.gemini_api.model = None
        self.mock_input_color.side_effect = ["Hello", "Farewell"]
        self.game._handle_talk_to_command("Porfiry")
        self.mock_print_color.assert_any_call(f"{Colors.DIM}(Using placeholder dialogue){Colors.RESET}", Colors.DIM)

    def test_record_memories_unusual_state(self):
        self.game.player_character.apparent_state = "dangerously agitated"
        self.npc.add_player_memory = MagicMock()
        self.game._record_npc_post_interaction_memories(self.npc, "test context")
        self.npc.add_player_memory.assert_any_call(
            memory_type="observed_player_state",
            turn=self.game.game_time,
            content={"state": "dangerously agitated", "context": "test context"},
            sentiment_impact=-1
        )

    def test_record_memories_unusual_inventory(self):
        self.game.player_character.inventory = [{"name": "raskolnikov's axe"}]
        self.npc.add_player_memory = MagicMock()
        self.game._record_npc_post_interaction_memories(self.npc, "test context")
        self.npc.add_player_memory.assert_any_call(
            memory_type="observed_player_inventory",
            turn=self.game.game_time,
            content={"item_name": "raskolnikov's axe", "context": "player was carrying test context"},
            sentiment_impact=-1
        )

    def test_persuade_invalid_args(self):
        action, atmo = self.game._handle_persuade_command(None)
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("How do you want to persuade them? Use: persuade [person] that/to [your argument]", Colors.RED)

    def test_persuade_no_player(self):
        self.game.player_character = None
        action, atmo = self.game._handle_persuade_command(("Porfiry", "I am innocent"))
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("Cannot persuade: Player character not available.", Colors.RED)

    def test_persuade_not_found(self):
        action, atmo = self.game._handle_persuade_command(("Ghost", "I am innocent"))
        self.assertFalse(action)
        self.mock_print_color.assert_any_call("You don't see anyone named 'Ghost' here to persuade.", Colors.RED)

    def test_persuade_success_with_gemini(self):
        self.game.player_character.check_skill = MagicMock(return_value=True)
        self.npc.add_player_memory = MagicMock()
        action, atmo = self.game._handle_persuade_command(("Porfiry", "I am innocent"))
        self.assertTrue(action)
        self.mock_print_color.assert_any_call("Your argument seems to have had an effect!", Colors.GREEN)
        self.game.gemini_api.get_npc_dialogue_persuasion_attempt.assert_called_once()
        self.npc.add_player_memory.assert_called()

    def test_persuade_failure_no_gemini(self):
        self.game.gemini_api.model = None
        self.game.player_character.check_skill = MagicMock(return_value=False)
        self.npc.add_player_memory = MagicMock()
        action, atmo = self.game._handle_persuade_command(("Porfiry", "I am innocent"))
        self.assertTrue(action)
        self.mock_print_color.assert_any_call(f"Your words don't seem to convince {self.npc.name}.", Colors.RED)
        self.mock_print_color.assert_any_call(f"{Colors.DIM}(Using placeholder dialogue for persuasion){Colors.RESET}", Colors.DIM)
        self.npc.add_player_memory.assert_called()

if __name__ == "__main__":
    unittest.main()
