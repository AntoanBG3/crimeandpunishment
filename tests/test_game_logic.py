import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add project root to sys.path to allow imports from game_engine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.character_module import Character
from game_engine.gemini_interactions import GeminiAPI
from game_engine.game_state import Game # New Import
from game_engine.event_manager import EventManager # New Import
from game_engine.game_config import Colors # New Import for TestGameStateCommands

# Test data for DEFAULT_ITEMS
DEFAULT_ITEMS_TEST_DATA = {
    "apple": {"description": "A simple apple.", "stackable": True},
    "sword": {"description": "A sharp sword."},
    "coin": {"description": "A gold coin.", "value": 1},
    "potion": {"description": "A healing potion.", "stackable": True},
    "scroll": {"description": "An old scroll."}
}

TEST_ITEMS_FOR_LOOK = {
    "test_apple": {"description": "A juicy apple.", "stackable": True, "takeable": True},
    "test_sword": {"description": "A sharp sword.", "takeable": True}
}

class TestInventoryDescription(unittest.TestCase):
    def setUp(self):
        self.char = Character(
            name="TestPlayer",
            persona="A test persona",
            greeting="Hello",
            default_location="TestLocation",
            accessible_locations=["TestLocation"]
        )
        self.char.inventory = []

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_empty_inventory(self):
        self.assertEqual(self.char.get_inventory_description(), "You are carrying nothing.")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_single_non_stackable_item(self):
        self.char.inventory = [{"name": "sword"}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: sword.")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_single_stackable_item_quantity_one(self):
        self.char.inventory = [{"name": "apple", "quantity": 1}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: apple.")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_single_stackable_item_quantity_many(self):
        self.char.inventory = [{"name": "apple", "quantity": 3}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: apple (x3).")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_multiple_items(self):
        self.char.inventory = [
            {"name": "sword"},
            {"name": "apple", "quantity": 2},
            {"name": "coin", "quantity": 10}
        ]
        desc = self.char.get_inventory_description()
        self.assertTrue(desc.startswith("You are carrying: "))
        # Use sorted lists of items for comparison to handle potential order differences
        expected_items = sorted(["sword", "apple (x2)", "coin (x10)"])
        actual_items_str = desc.replace("You are carrying: ", "").split(", ")
        actual_items = sorted([item.strip('.') for item in actual_items_str])
        self.assertEqual(actual_items, expected_items)

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_item_with_command_suffix_displayed_cleanly(self):
        self.char.inventory = [{"name": "potion use_effect_player:drink"}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: potion.")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_item_with_command_suffix_stackable(self):
        self.char.inventory = [{"name": "potion use_effect_player:drink", "quantity": 3}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: potion (x3).")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_item_with_value_and_suffix_stackable(self):
        self.char.inventory = [{"name": "coin use_effect_player:spend", "quantity": 5}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: coin (x5).")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_mangled_name_not_in_default_items_but_base_is(self):
        self.char.inventory = [{"name": "scroll use_effect_player:read", "quantity": 1}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: scroll.")

    @patch('game_engine.game_config.DEFAULT_ITEMS', DEFAULT_ITEMS_TEST_DATA)
    def test_mangled_name_where_base_not_in_default_items(self):
        self.char.inventory = [{"name": "ghost_item use_effect_player:vanish"}]
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: ghost_item.")

class TestGeminiDialogueQuotes(unittest.TestCase):
    def setUp(self):
        self.mock_genai_configure = patch('google.generativeai.configure').start()
        self.mock_generative_model_cls = patch('google.generativeai.GenerativeModel').start()

        self.api = GeminiAPI()
        self.api.model = MagicMock()

        self.player = Character(name="Player", persona="P", greeting="G", default_location="L", accessible_locations=["L"])
        self.npc = Character(name="NPC", persona="N", greeting="G", default_location="L", accessible_locations=["L"])

        self.player.conversation_histories = {}
        self.npc.conversation_histories = {}

    def tearDown(self):
        patch.stopall()

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_player_dialogue_quotes_escaped_in_prompt(self, mock_generate_content):
        mock_generate_content.return_value = "AI response"
        player_dialogue = 'He said "Hello!" to me.'

        self.api.get_npc_dialogue(self.npc, self.player, player_dialogue, "Loc", "Time", "Rel", "Mem", "State", "Items", "Events", "Obj", "PlayerObj")

        self.assertTrue(mock_generate_content.called)
        prompt_arg = mock_generate_content.call_args[0][0]
        self.assertIn('He said \\"Hello!\\" to me.', prompt_arg)

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ai_response_with_escaped_quotes_normalized(self, mock_generate_content):
        mock_generate_content.return_value = 'NPC says: \\"Greetings!\\"'
        response = self.api.get_npc_dialogue(self.npc, self.player, "Hi", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, 'NPC says: "Greetings!"')
        self.assertIn(f"{self.npc.name}: NPC says: \"Greetings!\"", self.npc.conversation_histories[self.player.name])

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ai_response_with_surrounding_quotes_stripped(self, mock_generate_content):
        mock_generate_content.return_value = '"This is the actual response."'
        response = self.api.get_npc_dialogue(self.npc, self.player, "Hello", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, 'This is the actual response.')
        self.assertIn(f"{self.npc.name}: This is the actual response.", self.npc.conversation_histories[self.player.name])

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ai_response_with_both_escaped_and_surrounding_quotes(self, mock_generate_content):
        # This mock value represents an AI returning a string that contains literal backslashes
        # before quotes that it intends to be part of the string content.
        # String value: '"NPC says: \"Okay!\""' (where \" is a literal backslash then a quote)
        mock_generate_content.return_value = '"NPC says: \\"Okay!\\""'

        response = self.api.get_npc_dialogue(self.npc, self.player, "Tell me.", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, 'NPC says: "Okay!"') # Expect fully cleaned version

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ooc_message_passthrough_and_history(self, mock_generate_content):
        mock_generate_content.return_value = '(OOC: Cannot respond.)'

        self.npc.conversation_histories[self.player.name] = []
        initial_npc_history_len = len(self.npc.conversation_histories[self.player.name])

        response = self.api.get_npc_dialogue(self.npc, self.player, "What?", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, '(OOC: Cannot respond.)')

        npc_hist_for_player = self.npc.conversation_histories[self.player.name]
        self.assertEqual(len(npc_hist_for_player), initial_npc_history_len + 1)
        self.assertEqual(npc_hist_for_player[-1], f"{self.player.name}: What?")

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_history_player_dialogue_is_original(self, mock_generate_content):
        mock_generate_content.return_value = 'AI response'
        player_dialogue_with_quotes = 'My input has "quotes".'
        self.api.get_npc_dialogue(self.npc, self.player, player_dialogue_with_quotes, "L", "T", "R", "M", "S", "I", "E", "O", "PO")

        npc_history_for_player = self.npc.conversation_histories[self.player.name]
        expected_player_entry = f"{self.player.name}: {player_dialogue_with_quotes}"
        self.assertIn(expected_player_entry, npc_history_for_player)

class TestGameStateCommands(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        # Mock essential attributes/methods of the Game instance
        self.game.player_character = MagicMock(spec=Character)
        self.game.current_location_name = "Test Chamber"
        self.game.dynamic_location_items = {"Test Chamber": [{"name": "test_apple", "quantity": 1}, {"name": "test_sword"}]}
        self.game.all_character_objects = {}
        self.game.npcs_in_current_location = []
        self.game.numbered_actions_context = []

        # Patch external data
        self.mock_locations_data = patch('game_engine.game_state.LOCATIONS_DATA', {'Test Chamber': {'description': 'A room.', 'exits': {'north': 'Corridor'}}}).start()
        self.mock_default_items = patch('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_LOOK).start()

        # Patch print functions
        self.mock_print = patch('builtins.print').start()
        self.mock_print_color = patch.object(self.game, '_print_color').start()

    def tearDown(self):
        patch.stopall()

    def test_handle_look_command_item_display(self):
        self.game._handle_look_command(None) # General look

        # Collect printed output
        printed_lines = []
        for call_args in self.mock_print_color.call_args_list:
            printed_lines.append(str(call_args[0][0])) # First positional argument
        # Also check builtins.print if it was used for snippets (it shouldn't be for "Look at" now)
        for call_args in self.mock_print.call_args_list:
            printed_lines.append(str(call_args[0][0]))

        # --- Items Here ---
        # 1. Look at test_apple  (no snippet)
        # 2. Take test_apple
        # 3. Look at test_sword (no snippet)
        # 4. Take test_sword

        # Assertions for "Look at test_apple"
        expected_look_apple_line = next((i for i, line in enumerate(printed_lines) if "Look at test_apple" in line), -1)
        self.assertGreaterEqual(expected_look_apple_line, 0, "Look at test_apple action not found in output")
        self.assertFalse("juicy apple" in printed_lines[expected_look_apple_line], "Description snippet found for 'Look at test_apple'")

        # Assertions for "Take test_apple"
        self.assertTrue(any("Take test_apple" in line for line in printed_lines), "Take test_apple action not found")

        # Assertions for "Look at test_sword"
        expected_look_sword_line = next((i for i, line in enumerate(printed_lines) if "Look at test_sword" in line), -1)
        self.assertGreaterEqual(expected_look_sword_line, 0, "Look at test_sword action not found in output")
        self.assertFalse("sharp sword" in printed_lines[expected_look_sword_line], "Description snippet found for 'Look at test_sword'")

        # Assertions for "Take test_sword"
        self.assertTrue(any("Take test_sword" in line for line in printed_lines), "Take test_sword action not found")

        # Check numbered_actions_context
        # Expected actions (order might vary based on implementation, so check for presence)
        expected_context_actions = [
            {'type': 'look_at_item', 'target': 'test_apple', 'display': 'Look at test_apple'},
            {'type': 'take', 'target': 'test_apple', 'display': 'Take test_apple'}, # apple is stackable but qty 1, so no (x1)
            {'type': 'look_at_item', 'target': 'test_sword', 'display': 'Look at test_sword'},
            {'type': 'take', 'target': 'test_sword', 'display': 'Take test_sword'}
        ]
        for expected_action in expected_context_actions:
            self.assertIn(expected_action, self.game.numbered_actions_context)

class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_game = MagicMock(spec=Game) # Use spec=Game
        self.mock_game.gemini_api = MagicMock(spec=GeminiAPI) # Use spec for gemini_api
        self.mock_game.gemini_api.get_player_reflection = MagicMock(return_value="A deep thought.")

        self.mock_game.player_character = MagicMock(spec=Character)
        self.mock_game.player_character.name = "Rodion Raskolnikov"
        self.mock_game.player_character.apparent_state = "thoughtful"
        self.mock_game.player_character.add_player_memory = MagicMock()
        self.mock_game.player_character.get_objective_by_id = MagicMock(return_value=None)
        self.mock_game.player_character.activate_objective = MagicMock()
        self.mock_game.player_character.has_item = MagicMock(return_value=False)
        self.mock_game.player_character.add_to_inventory = MagicMock()

        self.mock_game.current_location_name = "Raskolnikov's Garret"
        self.mock_game.get_current_time_period = MagicMock(return_value="Morning")
        self.mock_game._get_objectives_summary = MagicMock(return_value="Some objectives.")
        self.mock_game._print_color = MagicMock()
        self.mock_game.last_significant_event_summary = ""
        self.mock_game.key_events_occurred = []
        self.mock_game.game_time = 0 # Added missing attribute

        self.event_manager = EventManager(self.mock_game)

    def test_action_letter_from_mother_calls_reflection_correctly(self):
        self.event_manager.action_letter_from_mother()

        self.mock_game.gemini_api.get_player_reflection.assert_called_once()
        args, kwargs = self.mock_game.gemini_api.get_player_reflection.call_args

        self.assertEqual(kwargs.get('player_character'), self.mock_game.player_character)
        self.assertEqual(kwargs.get('current_location_name'), self.mock_game.current_location_name)
        self.assertEqual(kwargs.get('current_time_period'), self.mock_game.get_current_time_period.return_value)
        self.assertIn('context_text', kwargs) # Check presence, content checked by other tests
        self.assertEqual(kwargs.get('active_objectives_summary'), self.mock_game._get_objectives_summary.return_value)

        # Ensure old incorrect kwargs are not present
        self.assertNotIn('player_char_obj', kwargs)
        self.assertNotIn('context_string', kwargs)
        self.assertNotIn('objectives_summary', kwargs)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
