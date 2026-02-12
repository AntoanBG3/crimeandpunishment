import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import random # For TestItemEffects
import copy # For TestCharacterObjectives

# Add project root to sys.path to allow imports from game_engine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.character_module import Character
from game_engine.gemini_interactions import GeminiAPI, DEFAULT_GEMINI_MODEL_NAME
from game_engine.game_state import Game
from game_engine.event_manager import EventManager
from game_engine.game_config import Colors, TIME_UNITS_PER_PLAYER_ACTION, TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE, MAX_TIME_UNITS_PER_DAY, NPC_MOVE_CHANCE, TIME_PERIODS

# Test data for DEFAULT_ITEMS
DEFAULT_ITEMS_TEST_DATA = {
    "apple": {"description": "A simple apple.", "stackable": True},
    "sword": {"description": "A sharp sword."},
    "coin": {"description": "A gold coin.", "value": 1},
    "potion": {"description": "A healing potion.", "stackable": True},
    "scroll": {"description": "An old scroll."}
}

TEST_ITEMS_FOR_LOOK = {
    "test_apple": {"description": "A juicy red apple, looking crisp.", "stackable": True, "takeable": True},
    "test_sword": {"description": "A long, sharp sword, gleaming slightly.", "takeable": True},
    "test_coin": {"description": "A single gold coin.", "value": 1, "takeable": True},
    "test_scroll": {"description": "An ancient scroll.", "readable": True, "takeable": True},
    "test_potion": {"description": "A bubbling potion.", "use_effect_player": "drink_potion", "takeable": True}
}

TEST_GAME_ITEMS = { # For TestItemEffects
    "tattered handkerchief": {"description": "A worn piece of cloth.", "use_effect_player": "comfort_self_if_ill"},
    "raskolnikov's axe": {"description": "A weighty axe.", "use_effect_player": "grip_axe_and_reminisce_horror"},
    "cheap vodka": {"description": "A bottle of cheap spirits.", "use_effect_player": "drink_vodka_for_oblivion", "consumable": True, "stackable": True},
    "fresh newspaper": {"description": "Today's news.", "readable": True, "use_effect_player": "read_evolving_news_article"},
    "mother's letter": {"description": "A letter from Pulcheria.", "readable": True, "use_effect_player": "reread_letter_and_feel_familial_pressure"},
}

TEST_SCHEDULE_LOCATIONS_DATA = {
    "LocationA": {"description": "A quiet place.", "exits": {}},
    "LocationB": {"description": "A busy place.", "exits": {}},
    "LocationC": {"description": "An inaccessible place.", "exits": {}}
}
TEST_SCHEDULED_NPC_DATA = {
    "ScheduledNPC": {
        "persona": "An NPC with a schedule", "greeting": "Hmph.",
        "default_location": "LocationA",
        "accessible_locations": ["LocationA", "LocationB"],
        "schedule": {
            "Morning": "LocationA",
            "Afternoon": "LocationB",
            "Evening": "LocationA"
        }
    },
    "StaticNPC": {
        "persona": "Stays put.", "greeting": "...",
        "default_location": "LocationA",
        "accessible_locations": ["LocationA"],
        "schedule": {}
    }
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
        # This test reflects that if the "cleaned" base name is not in DEFAULT_ITEMS,
        # the original (mangled) name is displayed.
        self.assertEqual(self.char.get_inventory_description(), "You are carrying: ghost_item use_effect_player:vanish.")

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

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ai_response_with_surrounding_quotes_stripped(self, mock_generate_content):
        mock_generate_content.return_value = '"This is the actual response."'
        response = self.api.get_npc_dialogue(self.npc, self.player, "Hello", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, 'This is the actual response.')

    @patch.object(GeminiAPI, '_generate_content_with_fallback')
    def test_ai_response_with_both_escaped_and_surrounding_quotes(self, mock_generate_content):
        mock_generate_content.return_value = '"NPC says: \\"Okay!\\""'
        response = self.api.get_npc_dialogue(self.npc, self.player, "Tell me.", "L", "T", "R", "M", "S", "I", "E", "O", "PO")
        self.assertEqual(response, 'NPC says: "Okay!"')

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

@patch('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_LOOK)
class TestGameStateCommands(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = MagicMock(spec=Character)
        self.game.player_character.name = "TestPlayer" # Fix for AttributeError
        self.game.player_character.inventory = []
        # Add defaults for attributes/methods needed in get_npc_dialogue context
        self.game.player_character.apparent_state = "normal"
        self.game.player_character.get_notable_carried_items_summary = MagicMock(return_value="nothing notable.")
        self.game.player_character.get_objectives_summary = MagicMock(return_value="No specific objectives.")
        self.game.player_character.conversation_histories = {} # Ensure this exists

        self.game.current_location_name = "Test Chamber"
        self.game.dynamic_location_items = {
            "Test Chamber": [
                {"name": "test_apple", "quantity": 3},
                {"name": "test_sword"},
                {"name": "test_coin"},
                {"name": "test_scroll"},
                {"name": "test_potion"}
            ]
        }
        self.game.all_character_objects = {}
        self.game.npcs_in_current_location = []
        self.game.numbered_actions_context = []
        self.game.TIME_UNITS_PER_PLAYER_ACTION = TIME_UNITS_PER_PLAYER_ACTION

        self.mock_locations_data_patch = patch('game_engine.game_state.LOCATIONS_DATA', {'Test Chamber': {'description': 'A room.', 'exits': {'north': 'Corridor'}}})
        self.mock_locations_data = self.mock_locations_data_patch.start()

        self.mock_print = patch('builtins.print').start()
        self.mock_print_color = patch.object(self.game, '_print_color').start()
        self.mock_input_color = patch.object(self.game, '_input_color').start()

    def tearDown(self):
        patch.stopall()

    def test_handle_look_command_item_display(self):
        self.game._handle_look_command(None, show_full_look_details=True)
        printed_content = " ".join([str(call_obj[0][0]) for call_obj in self.mock_print_color.call_args_list if call_obj[0]])

        self.assertIn("test_apple (x3) - A juicy red apple, looking crisp.", printed_content)
        self.assertIn("test_sword - A long, sharp sword, gleaming slightly.", printed_content)
        self.assertIn("test_coin - A single gold coin.", printed_content)

        expected_context_actions = [
            {'type': 'select_item', 'target': 'test_apple', 'display': 'test_apple'},
            {'type': 'select_item', 'target': 'test_sword', 'display': 'test_sword'},
            {'type': 'select_item', 'target': 'test_coin', 'display': 'test_coin'}
        ]
        for expected_action in expected_context_actions:
            found = any(e_a['type'] == expected_action['type'] and e_a['target'] == expected_action['target'] for e_a in self.game.numbered_actions_context)
            self.assertTrue(found, f"Expected action {expected_action} not found in numbered_actions_context: {self.game.numbered_actions_context}")


    @patch.object(Game, '_handle_look_command')
    def test_process_command_select_item_then_look_at(self, mock_specific_look):
        item_name = "test_apple"
        self.mock_input_color.return_value = "look at"
        # When _process_command handles 'select_item', show_full_look_details is False
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        # So, _handle_look_command (mocked as mock_specific_look here) should be called with False
        mock_specific_look.assert_called_once_with(item_name, False)
        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.assertEqual(time_units, self.game.TIME_UNITS_PER_PLAYER_ACTION)

    @patch.object(Game, '_handle_take_command')
    def test_process_command_select_item_then_take(self, mock_handle_take):
        item_name = "test_apple"
        mock_handle_take.return_value = (True, True)
        self.mock_input_color.return_value = "take"
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        mock_handle_take.assert_called_once_with(item_name)
        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.assertEqual(time_units, self.game.TIME_UNITS_PER_PLAYER_ACTION)

    @patch.object(Game, 'handle_use_item')
    def test_process_command_select_item_then_read(self, mock_handle_use_item):
        self.game.player_character.inventory = [{"name": "test_scroll"}]
        item_name = "test_scroll"
        mock_handle_use_item.return_value = True
        self.mock_input_color.return_value = "read"
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        mock_handle_use_item.assert_called_once_with(item_name, None, "read")
        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.assertEqual(time_units, self.game.TIME_UNITS_PER_PLAYER_ACTION)

    @patch.object(Game, 'handle_use_item')
    def test_process_command_select_item_then_use_self(self, mock_handle_use_item):
        self.game.player_character.inventory = [{"name": "test_potion"}]
        item_name = "test_potion"
        mock_handle_use_item.return_value = True
        self.mock_input_color.return_value = "use"
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        mock_handle_use_item.assert_called_once_with(item_name, None, "use_self_implicit")
        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.assertEqual(time_units, self.game.TIME_UNITS_PER_PLAYER_ACTION)

    @patch.object(Game, 'handle_use_item')
    def test_process_command_select_item_then_give_to(self, mock_handle_use_item):
        self.game.player_character.inventory = [{"name": "test_apple"}]
        item_name = "test_apple"
        mock_npc = MagicMock(spec=Character); mock_npc.name = "TestNPC"
        self.game.npcs_in_current_location = [mock_npc]
        mock_handle_use_item.return_value = True
        self.mock_input_color.return_value = "give to TestNPC"
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        mock_handle_use_item.assert_called_once_with(item_name, "testnpc", "give")
        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.assertEqual(time_units, self.game.TIME_UNITS_PER_PLAYER_ACTION)

    def test_process_command_select_item_invalid_secondary_action(self):
        item_name = "test_apple"
        self.mock_input_color.return_value = "fly"
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        self.mock_print_color.assert_any_call(f"Invalid action 'fly' for {item_name}.", Colors.RED)
        self.assertFalse(action_taken)
        self.assertFalse(show_atmospherics)
        self.assertEqual(time_units, 0)

    # --- Tests for _handle_take_command ---
    TEST_ITEMS_FOR_TAKE = {
        "unique_sword": {"description": "A unique blade.", "takeable": True, "stackable": False},
        "apple": {"description": "A simple fruit.", "takeable": True, "stackable": True},
        "coin": {"description": "A gold piece.", "takeable": True, "value": 1}
    }

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_TAKE, clear=True)
    def test_take_non_stackable_already_has(self):
        self.game.player_character.inventory = [{"name": "unique_sword"}]
        self.game.dynamic_location_items[self.game.current_location_name] = [{"name": "unique_sword"}]
        self.game.player_character.add_to_inventory = MagicMock(return_value=False)
        self.game.player_character.has_item = MagicMock(return_value=True) # Player already has it

        action_taken, show_atmospherics = self.game._handle_take_command("unique_sword")

        self.assertFalse(action_taken)
        self.assertTrue(show_atmospherics)
        self.mock_print_color.assert_any_call("You cannot carry another 'unique_sword'.", Colors.YELLOW)
        self.game.player_character.add_to_inventory.assert_called_once_with("unique_sword", 1)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_TAKE, clear=True)
    def test_take_non_stackable_does_not_have(self):
        self.game.player_character.inventory = []
        self.game.dynamic_location_items[self.game.current_location_name] = [{"name": "unique_sword"}]
        self.game.player_character.add_to_inventory = MagicMock(return_value=True)
        self.game.player_character.has_item = MagicMock(return_value=False) # Player does not have it initially

        action_taken, show_atmospherics = self.game._handle_take_command("unique_sword")

        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.mock_print_color.assert_any_call("You take the unique_sword.", Colors.GREEN)
        # Ensure the specific "cannot carry" message was NOT printed
        for call_args in self.mock_print_color.call_args_list:
            self.assertNotEqual(call_args[0][0], "You cannot carry another 'unique_sword'.")
        self.game.player_character.add_to_inventory.assert_called_once_with("unique_sword", 1)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_TAKE, clear=True)
    def test_take_stackable_item(self):
        self.game.player_character.inventory = [{"name": "apple", "quantity": 1}]
        self.game.dynamic_location_items[self.game.current_location_name] = [{"name": "apple", "quantity": 1}]
        self.game.player_character.add_to_inventory = MagicMock(return_value=True)
        self.game.player_character.has_item = MagicMock(return_value=True) # Player has some apples

        action_taken, show_atmospherics = self.game._handle_take_command("apple")

        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.mock_print_color.assert_any_call("You take the apple.", Colors.GREEN)
        for call_args in self.mock_print_color.call_args_list:
            self.assertNotEqual(call_args[0][0], "You cannot carry another 'apple'.")
        self.game.player_character.add_to_inventory.assert_called_once_with("apple", 1)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_TAKE, clear=True)
    def test_take_item_with_value_behaves_stackable(self):
        self.game.player_character.inventory = [{"name": "coin", "quantity": 1}]
        self.game.dynamic_location_items[self.game.current_location_name] = [{"name": "coin", "quantity": 1}]
        self.game.player_character.add_to_inventory = MagicMock(return_value=True)
        # has_item mock isn't strictly necessary here as the logic branches on add_to_inventory's return primarily

        action_taken, show_atmospherics = self.game._handle_take_command("coin")

        self.assertTrue(action_taken)
        self.assertTrue(show_atmospherics)
        self.mock_print_color.assert_any_call("You take the coin.", Colors.GREEN) # Corrected assertion
        for call_args in self.mock_print_color.call_args_list:
            self.assertNotEqual(call_args[0][0], "You cannot carry another 'coin'.")
        self.game.player_character.add_to_inventory.assert_called_once_with("coin", 1)


    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_ITEMS_FOR_TAKE, clear=True)
    def test_take_add_to_inventory_fails_generic(self):
        self.game.player_character.inventory = []
        self.game.dynamic_location_items[self.game.current_location_name] = [{"name": "apple", "quantity": 1}]
        self.game.player_character.add_to_inventory = MagicMock(return_value=False)
        self.game.player_character.has_item = MagicMock(return_value=False) # Does not have the item

        action_taken, show_atmospherics = self.game._handle_take_command("apple")

        self.assertFalse(action_taken)
        self.assertTrue(show_atmospherics)
        self.mock_print_color.assert_any_call("Failed to add apple to inventory.", Colors.RED)
        for call_args in self.mock_print_color.call_args_list:
            self.assertNotEqual(call_args[0][0], "You cannot carry another 'apple'.")
        self.game.player_character.add_to_inventory.assert_called_once_with("apple", 1)

    def test_razumikhin_standard_greeting_for_raskolnikov(self):
        # Setup Player
        self.game.player_character.name = "Rodion Raskolnikov"
        # Mock player attributes needed for get_npc_dialogue context
        self.game.player_character.apparent_state = "brooding"
        self.game.player_character.get_notable_carried_items_summary = MagicMock(return_value="nothing notable.")
        self.game.player_character.get_inventory_description = MagicMock(return_value="carrying a few kopeks.")


        # Setup NPC Dmitri Razumikhin
        mock_razumikhin = MagicMock(spec=Character)
        mock_razumikhin.name = "Dmitri Razumikhin"
        mock_razumikhin.greeting = "Ah, Rodya, old friend! What brings you here?"
        mock_razumikhin.apparent_state = "cheerful"
        mock_razumikhin.relationship_with_player = 5 # Positive relationship
        mock_razumikhin.conversation_histories = {} # Initialize conversation histories
        mock_razumikhin.update_relationship = MagicMock()
        mock_razumikhin.add_player_memory = MagicMock()
        mock_razumikhin.get_player_memory_summary = MagicMock(return_value="Fond memories.")
        mock_razumikhin.get_objective_by_id = MagicMock(return_value=None)
        # Mock methods needed for get_npc_dialogue context for NPC
        mock_razumikhin.get_objectives_summary = MagicMock(return_value="Just trying to help friends.")


        self.game.npcs_in_current_location = [mock_razumikhin]
        self.game.all_character_objects["Dmitri Razumikhin"] = mock_razumikhin

        # Mock Gemini API for subsequent dialogue
        self.game.gemini_api.model = MagicMock() # Ensure API model is considered available
        self.game.gemini_api.get_npc_dialogue = MagicMock(return_value="Just thinking, Razumikhin. Just thinking.")
        # Mock game methods that provide context to get_npc_dialogue
        self.game.get_relationship_text = MagicMock(return_value="positive")
        self.game._get_recent_events_summary = MagicMock(return_value="The usual St. Petersburg gloom.")
        self.game._get_objectives_summary = MagicMock(return_value="Survive.") # For player
        self.game.get_current_time_period = MagicMock(return_value="Evening")
        self.game.player_character.current_location = self.game.current_location_name # Ensure player has a location


        # Mock input to end conversation immediately
        self.mock_input_color.side_effect = ["Hello there!", "Farewell"] # Allow one exchange

        # Action
        self.game._handle_talk_to_command("Dmitri Razumikhin")

        # Assertions
        # Check that the NPC's name was printed with _print_color(..., end="")
        self.mock_print_color.assert_any_call(f"{mock_razumikhin.name}: ", Colors.YELLOW, end="")
        # Check that the NPC's greeting was printed with print()
        self.mock_print.assert_any_call(f"\"{mock_razumikhin.greeting}\"")

        # Assert that Gemini API was called for the conversation part
        self.game.gemini_api.get_npc_dialogue.assert_called_once()
        # Verify some key context arguments passed to get_npc_dialogue
        dialogue_args, dialogue_kwargs = self.game.gemini_api.get_npc_dialogue.call_args
        self.assertEqual(dialogue_args[0], mock_razumikhin) # target_npc is the first positional arg
        self.assertEqual(dialogue_args[1], self.game.player_character) # player_character is the second
        self.assertEqual(dialogue_args[2], "Hello there!") # player_dialogue_input is the third


    # --- Tests for _handle_give_item ---
    @patch('game_engine.game_state.DEFAULT_ITEMS', {
        "test_apple": {"description": "A simple apple.", "stackable": True, "takeable": True, "value": 5}, # value makes it stackable
        "test_book": {"description": "An old book.", "takeable": True} # Non-stackable by default if no value
    })
    def test_give_item_successfully(self):
        # Setup player inventory
        self.game.player_character.inventory = [{"name": "test_apple", "quantity": 1}]
        # Mock remove_from_inventory to check it's called and simulate success
        self.game.player_character.remove_from_inventory = MagicMock(return_value=True)
        self.game.player_character.has_item = MagicMock(return_value=True) # Player has the item
        # Ensure player_character has attributes needed for dialogue context
        self.game.player_character.name = "TestPlayerGive" # Specific name for clarity if needed
        self.game.player_character.apparent_state = "generous"
        self.game.player_character.get_notable_carried_items_summary = MagicMock(return_value="an apple")
        self.game.player_character.get_objectives_summary = MagicMock(return_value="To give an apple.")


        # Setup NPC
        mock_npc = MagicMock(spec=Character)
        mock_npc.name = "TestNPC"
        mock_npc.inventory = []
        mock_npc.relationship_with_player = 0
        mock_npc.add_to_inventory = MagicMock(return_value=True) # Simulate successful add to NPC inv
        mock_npc.add_player_memory = MagicMock()
        mock_npc.get_player_memory_summary = MagicMock(return_value="No memories.")
        mock_npc.get_objectives_summary = MagicMock(return_value="To receive an apple.") # Corrected: get_objectives_summary
        self.game.npcs_in_current_location = [mock_npc]

        # Mock Gemini API & Game context methods
        self.game.gemini_api.get_npc_dialogue = MagicMock(return_value="Oh, thank you for the apple!")
        self.game.gemini_api.model = MagicMock() # Ensure model is truthy
        self.game.low_ai_data_mode = False
        self.game.get_current_time_period = MagicMock(return_value="Afternoon")
        self.game._get_recent_events_summary = MagicMock(return_value="Nothing much.")
        # Mock _get_objectives_summary on game instance for the player if not using player.get_objectives_summary directly
        # For this test, player_character.get_objectives_summary is mocked above.
        # If self.game._get_objectives_summary(self.player_character) is used, that needs mocking on game.
        # Assuming get_npc_dialogue calls self.game._get_objectives_summary(character)
        self.game._get_objectives_summary = MagicMock(side_effect=lambda char: char.get_objectives_summary())


        # Action: Player gives "test_apple" to "TestNPC"
        success = self.game.handle_use_item("test_apple", "TestNPC", "give")

        # Assertions
        self.assertTrue(success)
        self.game.player_character.remove_from_inventory.assert_called_once_with("test_apple", 1)
        mock_npc.add_to_inventory.assert_called_once_with("test_apple", 1)
        self.game.gemini_api.get_npc_dialogue.assert_called_once()
        dialogue_args, dialogue_kwargs = self.game.gemini_api.get_npc_dialogue.call_args
        # player_dialogue_input is the 3rd positional arg (index 2)
        self.assertEqual(dialogue_args[2], "(Player gives test_apple to NPC. Player expects a reaction.)")

        self.mock_print_color.assert_any_call(f"You give the test_apple to {mock_npc.name}.", Colors.WHITE)
        self.mock_print_color.assert_any_call(f"{mock_npc.name}: \"Oh, thank you for the apple!\"", Colors.YELLOW)
        self.assertEqual(mock_npc.relationship_with_player, 1)
        mock_npc.add_player_memory.assert_called_once()
        args, kwargs = mock_npc.add_player_memory.call_args
        self.assertEqual(kwargs.get('memory_type'), "received_item")
        self.assertEqual(kwargs.get('content', {}).get('item_name'), "test_apple")
        self.assertEqual(kwargs.get('content', {}).get('quantity'), 1)
        self.assertTrue(kwargs.get('content', {}).get('from_player'))
        self.assertEqual(self.game.last_significant_event_summary, f"gave test_apple to {mock_npc.name}.")

    @patch('game_engine.game_state.DEFAULT_ITEMS', {"test_banana": {"description": "A ripe banana."}})
    def test_give_item_player_does_not_have(self):
        self.game.player_character.inventory = [] # Player has nothing
        self.game.player_character.has_item = MagicMock(return_value=False) # Explicitly mock has_item

        mock_npc = MagicMock(spec=Character); mock_npc.name = "TestNPC"
        mock_npc.inventory = []; mock_npc.add_player_memory = MagicMock()
        self.game.npcs_in_current_location = [mock_npc]
        self.game.gemini_api.get_npc_dialogue = MagicMock()

        success = self.game.handle_use_item("test_banana", "TestNPC", "give")

        self.assertFalse(success)
        self.mock_print_color.assert_any_call("You don't have 'test_banana' to give.", Colors.RED)
        self.assertEqual(len(mock_npc.inventory), 0) # NPC inventory unchanged
        self.game.gemini_api.get_npc_dialogue.assert_not_called()
        mock_npc.add_player_memory.assert_not_called()

    @patch('game_engine.game_state.DEFAULT_ITEMS', {"test_orange": {"description": "A juicy orange."}})
    def test_give_item_npc_not_found(self):
        self.game.player_character.inventory = [{"name": "test_orange", "quantity": 1}]
        self.game.player_character.has_item = MagicMock(return_value=True)
        self.game.npcs_in_current_location = [] # NPC not here

        self.game.gemini_api.get_npc_dialogue = MagicMock()

        success = self.game.handle_use_item("test_orange", "MissingNPC", "give")

        self.assertFalse(success)
        self.mock_print_color.assert_any_call("You don't see 'MissingNPC' here to give anything to.", Colors.RED)
        self.assertEqual(len(self.game.player_character.inventory), 1) # Player inventory unchanged
        self.game.gemini_api.get_npc_dialogue.assert_not_called()

    @patch('game_engine.game_state.DEFAULT_ITEMS', {
        "test_pear": {"description": "A green pear.", "stackable": True, "takeable": True, "value": 3}
    })
    @patch('random.choice') # To make static fallback predictable
    def test_give_item_static_fallback_low_ai_mode(self, mock_random_choice):
        self.game.player_character.inventory = [{"name": "test_pear", "quantity": 1}]
        self.game.player_character.remove_from_inventory = MagicMock(return_value=True)
        self.game.player_character.has_item = MagicMock(return_value=True)

        mock_npc = MagicMock(spec=Character); mock_npc.name = "TestNPC"
        mock_npc.inventory = []; mock_npc.relationship_with_player = 0
        mock_npc.add_to_inventory = MagicMock(return_value=True)
        mock_npc.add_player_memory = MagicMock()
        mock_npc.get_player_memory_summary = MagicMock(return_value="No memories.")
        mock_npc.get_objective_summary = MagicMock(return_value="No objectives.")
        self.game.npcs_in_current_location = [mock_npc]

        self.game.low_ai_data_mode = True # Enable Low AI mode
        self.game.gemini_api.get_npc_dialogue = MagicMock() # This should not be called

        static_reaction_choice = "Oh, for me? Thank you for the test_pear."
        mock_random_choice.return_value = static_reaction_choice

        success = self.game.handle_use_item("test_pear", "TestNPC", "give")

        self.assertTrue(success)
        self.game.player_character.remove_from_inventory.assert_called_once_with("test_pear", 1)
        mock_npc.add_to_inventory.assert_called_once_with("test_pear", 1)
        self.game.gemini_api.get_npc_dialogue.assert_not_called() # Gemini API should not be called in low AI mode
        self.mock_print_color.assert_any_call(f"{mock_npc.name}: \"{static_reaction_choice}\" {Colors.DIM}(Static reaction){Colors.RESET}", Colors.YELLOW)
        self.assertEqual(mock_npc.relationship_with_player, 1)
        mock_npc.add_player_memory.assert_called_once()


class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_game = MagicMock(spec=Game)
        self.mock_game.gemini_api = MagicMock(spec=GeminiAPI)
        self.mock_game.gemini_api.model = MagicMock() # Add model attribute here
        self.mock_game.gemini_api.get_player_reflection = MagicMock(return_value="A deep thought.")
        self.mock_game.player_character = MagicMock(spec=Character)
        self.mock_game.player_character.name = "Rodion Raskolnikov"
        self.mock_game.player_character.apparent_state = "thoughtful"
        self.mock_game.player_character.add_player_memory = MagicMock()
        self.mock_game.player_character.get_objective_by_id = MagicMock(return_value=None)
        self.mock_game.player_character.activate_objective = MagicMock()
        self.mock_game.player_character.has_item = MagicMock(return_value=False)
        self.mock_game.player_character.add_to_inventory = MagicMock()
        self.mock_game.low_ai_data_mode = False # Add the attribute
        self.mock_game.current_location_name = "Raskolnikov's Garret"
        self.mock_game.get_current_time_period = MagicMock(return_value="Morning")
        self.mock_game._get_objectives_summary = MagicMock(return_value="Some objectives.")
        self.mock_game._print_color = MagicMock()
        self.mock_game.last_significant_event_summary = ""
        self.mock_game.key_events_occurred = []
        self.mock_game.game_time = 0
        self.event_manager = EventManager(self.mock_game)

    def test_action_letter_from_mother_calls_reflection_correctly(self):
        self.event_manager.action_letter_from_mother()
        self.mock_game.gemini_api.get_player_reflection.assert_called_once()
        args, kwargs = self.mock_game.gemini_api.get_player_reflection.call_args
        self.assertEqual(kwargs.get('player_character'), self.mock_game.player_character)
        self.assertEqual(kwargs.get('current_location_name'), self.mock_game.current_location_name)
        self.assertEqual(kwargs.get('current_time_period'), self.mock_game.get_current_time_period.return_value)
        self.assertIn('context_text', kwargs)
        self.assertEqual(kwargs.get('active_objectives_summary'), self.mock_game._get_objectives_summary.return_value)
        self.assertNotIn('player_char_obj', kwargs)
        self.assertNotIn('context_string', kwargs)
        self.assertNotIn('objectives_summary', kwargs)

@patch.dict('game_engine.game_state.DEFAULT_ITEMS', TEST_GAME_ITEMS, clear=True)
class TestItemEffects(unittest.TestCase):
    def setUp(self):
        self.mock_gemini_configure = patch.object(GeminiAPI, 'configure').start()
        self.game = Game()
        self.game.gemini_api = MagicMock(spec=GeminiAPI)
        self.game.gemini_api.model = MagicMock() # Add the model attribute
        self.player = Character(name="TestPlayer", persona="P", greeting="G", default_location="TestLocation", accessible_locations=["TestLocation"])
        self.player.inventory = []
        self.player.apparent_state = "normal"
        self.player.journal_entries = []
        self.player.memory_about_player = []
        self.game.player_character = self.player
        self.game.current_day = 1
        self.game.game_time = 100
        self.game.current_location_name = "TestLocation"
        self.game._print_color = MagicMock()
        self.game._get_current_game_time_period_str = MagicMock(return_value="Day 1, Morning")

    def tearDown(self):
        patch.stopall()

    def test_use_tattered_handkerchief_when_ill(self):
        self.player.apparent_state = "feverish"
        self.player.inventory.append({"name": "tattered handkerchief", "quantity": 1})
        with patch('random.random', return_value=0.1):
            self.game.handle_use_item("tattered handkerchief", None, "use_self_implicit")
        self.assertIn(self.player.apparent_state, ["less feverish", "feverish"])
        if self.player.apparent_state == "less feverish":
            self.game._print_color.assert_any_call("The coolness, imagined or real, seems to lessen the fever's grip for a moment.", Colors.CYAN)
        self.assertEqual(self.game.last_significant_event_summary, "used a tattered handkerchief while feeling unwell.")

    def test_use_tattered_handkerchief_when_normal(self):
        self.player.apparent_state = "normal"
        self.player.inventory.append({"name": "tattered handkerchief", "quantity": 1})
        self.game.handle_use_item("tattered handkerchief", None, "use_self_implicit")
        self.assertEqual(self.player.apparent_state, "normal")
        self.game._print_color.assert_any_call(f"You look at the tattered handkerchief. It seems rather pointless to use it now.", Colors.YELLOW)

    def test_use_raskolnikovs_axe_as_raskolnikov(self):
        self.player.name = "Rodion Raskolnikov"
        self.player.inventory.append({"name": "raskolnikov's axe", "quantity": 1})
        self.game.handle_use_item("raskolnikov's axe", None, "use_self_implicit")
        self.assertIn(self.player.apparent_state, ["dangerously agitated", "remorseful", "paranoid"])

    def test_use_cheap_vodka(self):
        self.player.inventory.append({"name": "cheap vodka", "quantity": 1})
        self.game.handle_use_item("cheap vodka", None, "use_self_implicit")
        self.assertEqual(self.player.apparent_state, "slightly drunk")
        self.assertFalse(any(item["name"] == "cheap vodka" for item in self.player.inventory), "Vodka should be consumed")
        self.assertEqual(self.game.last_significant_event_summary, "drank some cheap vodka to numb the thoughts.")

    def test_use_cheap_vodka_when_feverish(self):
        self.player.apparent_state = "feverish"
        self.player.inventory.append({"name": "cheap vodka", "quantity": 1})
        self.game.handle_use_item("cheap vodka", None, "use_self_implicit")
        self.assertEqual(self.player.apparent_state, "agitated")
        self.game._print_color.assert_any_call("The vodka clashes terribly with your fever, making you feel worse.", Colors.RED)

    def test_read_newspaper(self):
        self.player.inventory.append({"name": "fresh newspaper", "quantity": 1})
        self.player.add_journal_entry = MagicMock()
        self.game.gemini_api.get_newspaper_article_snippet = MagicMock(return_value="A terrible crime was reported...")
        self.game.handle_use_item("fresh newspaper", None, "read")
        self.game.gemini_api.get_newspaper_article_snippet.assert_called_once()
        self.player.add_journal_entry.assert_called_once_with("News (AI)", "A terrible crime was reported...", "Day 1, Morning") # Updated "News" to "News (AI)"
        self.assertEqual(self.player.apparent_state, "thoughtful")

    def test_read_mothers_letter_as_raskolnikov(self):
        self.player.name = "Rodion Raskolnikov"
        self.player.inventory.append({"name": "mother's letter", "quantity": 1})
        self.player.add_player_memory = MagicMock()
        self.game.gemini_api.get_player_reflection = MagicMock(return_value="A reflection about family.")
        self.game.handle_use_item("mother's letter", None, "read")
        self.game.gemini_api.get_player_reflection.assert_called_once()
        self.player.add_player_memory.assert_called_once_with(memory_type="reread_mother_letter", turn=self.game.game_time, content={"summary": "Re-reading mother's letter intensified feelings of duty and distress."}, sentiment_impact=-1)
        self.assertIn(self.player.apparent_state, ["burdened", "agitated", "resolved"])

class TestCharacterObjectives(unittest.TestCase):
    def setUp(self):
        self.char = Character(
            name="TestCharObj",
            persona="Objective Tester",
            greeting="Hi",
            default_location="TestRoom",
            accessible_locations=["TestRoom"]
        )
        self.obj_template_1 = {
            "id": "quest1", "description": "Main Quest", "active": False, "completed": False,
            "stages": [
                {"stage_id": "s1", "description": "Start", "is_current_stage": False},
                {"stage_id": "s2", "description": "Middle", "is_current_stage": False},
                {"stage_id": "s3", "description": "End", "is_current_stage": False, "is_ending_stage": True}
            ],
            "current_stage_id": None
        }
        self.obj_template_2 = {
            "id": "quest2", "description": "Side Quest", "active": False, "completed": False,
            "stages": [{"stage_id": "start_q2", "description": "Q2 Start", "is_current_stage": False}],
            "current_stage_id": None
        }
        self.char.objectives = []

    def test_activate_objective(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)

        self.char.activate_objective("quest1")
        obj = self.char.get_objective_by_id("quest1")
        self.assertTrue(obj['active'])
        self.assertFalse(obj['completed'])
        self.assertEqual(obj['current_stage_id'], "s1")
        self.assertTrue(obj['stages'][0]['is_current_stage'])

        # Test activating with a specific stage
        obj1_copy_2 = copy.deepcopy(self.obj_template_1)
        self.char.objectives = [obj1_copy_2] # Reset objectives
        self.char.activate_objective("quest1", set_stage_id="s2")
        obj_2 = self.char.get_objective_by_id("quest1")
        self.assertTrue(obj_2['active'])
        self.assertEqual(obj_2['current_stage_id'], "s2")
        self.assertTrue(obj_2['stages'][1]['is_current_stage'])

    def test_get_objective_by_id(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)
        self.assertIsNotNone(self.char.get_objective_by_id("quest1"))
        self.assertIsNone(self.char.get_objective_by_id("non_existent_quest"))

    def test_get_current_stage_for_objective(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)
        self.char.activate_objective("quest1")
        current_stage = self.char.get_current_stage_for_objective("quest1")
        self.assertIsNotNone(current_stage)
        self.assertEqual(current_stage['stage_id'], "s1")

    def test_advance_objective_stage(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)
        self.char.activate_objective("quest1")

        self.assertTrue(self.char.advance_objective_stage("quest1", "s2"))
        obj = self.char.get_objective_by_id("quest1")
        self.assertEqual(obj['current_stage_id'], "s2")
        self.assertTrue(obj['stages'][1]['is_current_stage'])
        self.assertFalse(obj['stages'][0]['is_current_stage'])
        self.assertTrue(obj['active'])
        self.assertFalse(obj['completed'])

        self.assertFalse(self.char.advance_objective_stage("quest1", "non_existent_stage"))

    def test_advance_to_ending_stage_completes_objective(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)
        self.char.activate_objective("quest1")

        self.assertTrue(self.char.advance_objective_stage("quest1", "s3")) # s3 is an ending stage
        obj = self.char.get_objective_by_id("quest1")
        self.assertEqual(obj['current_stage_id'], "s3")
        self.assertTrue(obj['completed'])
        self.assertFalse(obj['active'])

    def test_complete_objective_directly(self):
        obj1_copy = copy.deepcopy(self.obj_template_1)
        self.char.objectives.append(obj1_copy)
        self.char.activate_objective("quest1")

        self.assertTrue(self.char.complete_objective("quest1"))
        obj = self.char.get_objective_by_id("quest1")
        self.assertTrue(obj['completed'])
        self.assertFalse(obj['active'])

    def test_objective_linking_on_completion_activates_inactive_linked_objective(self):
        obj1_linked = copy.deepcopy(self.obj_template_1)
        obj1_linked['stages'][-1]['linked_to_objective_completion'] = "quest2"

        obj2_for_linking = copy.deepcopy(self.obj_template_2)
        obj2_for_linking['active'] = False

        self.char.objectives = [obj1_linked, obj2_for_linking]
        self.char.activate_objective("quest1")

        # Advance to the linking/ending stage of quest1
        self.char.advance_objective_stage("quest1", obj1_linked['stages'][-1]['stage_id'])

        linked_obj = self.char.get_objective_by_id("quest2")
        self.assertIsNotNone(linked_obj)
        self.assertTrue(linked_obj['active'])
        self.assertEqual(linked_obj['current_stage_id'], linked_obj['stages'][0]['stage_id'])

    def test_objective_linking_on_completion_advances_active_linked_objective_to_specific_stage(self):
        obj1_linked = copy.deepcopy(self.obj_template_1)
        obj1_linked['stages'][-1]['linked_to_objective_completion'] = {"id": "quest2", "stage_to_advance_to": "q2_middle"}

        obj2_for_linking = copy.deepcopy(self.obj_template_2)
        obj2_for_linking['stages'].append({"stage_id": "q2_middle", "description": "Q2 Middle", "is_current_stage": False})

        self.char.objectives = [obj1_linked, obj2_for_linking]
        self.char.activate_objective("quest1")
        self.char.activate_objective("quest2") # Quest2 is already active, at "start_q2"

        self.char.advance_objective_stage("quest1", obj1_linked['stages'][-1]['stage_id'])

        linked_obj = self.char.get_objective_by_id("quest2")
        self.assertIsNotNone(linked_obj)
        self.assertTrue(linked_obj['active'])
        self.assertEqual(linked_obj['current_stage_id'], "q2_middle")


# --- Tests for Low AI Data Mode ---
import io # For mocking open
from game_engine.game_config import (
    STATIC_ATMOSPHERIC_DETAILS, STATIC_PLAYER_REFLECTIONS,
    generate_static_scenery_observation, STATIC_NEWSPAPER_SNIPPETS,
    STATIC_ANONYMOUS_NOTE_CONTENT, STATIC_STREET_LIFE_EVENTS,
    STATIC_NPC_NPC_INTERACTIONS
)
# Import constant for TestGeminiAPIConfiguration
from game_engine.gemini_interactions import GEMINI_API_KEY_ENV_VAR


# Mock CHARACTERS_DATA for TestLowAIMode setup
TEST_CHAR_DATA_FOR_LOW_AI = {
    "TestPlayer": {
        "persona": "A test character",
        "greeting": "Hello.",
        "default_location": "Test Chamber",
        "accessible_locations": ["Test Chamber"],
        "non_playable": False, # Ensure it's playable
        "objectives": [],
        "inventory_items": [],
        "schedule": {}
    },
    "TestNPC1": {
        "persona": "NPC one", "greeting": "Hi NPC1",
        "default_location": "Test Chamber", "accessible_locations": ["Test Chamber"]
    },
    "TestNPC2": {
        "persona": "NPC two", "greeting": "Hi NPC2",
        "default_location": "Test Chamber", "accessible_locations": ["Test Chamber"]
    }
}
# Mock LOCATIONS_DATA for TestLowAIMode setup
TEST_LOC_DATA_FOR_LOW_AI = {
    "Test Chamber": {
        "description": "A plain room for testing.",
        "exits": {"north": "Another Room"},
        "items_present": []
    },
     "Raskolnikov's Garret": { # For letter event
        "description": "A tiny garret.", "exits": {}
    },
    "Haymarket Square": { # For street life event
        "description": "A bustling square.", "exits": {}
    }
}
# Mock DEFAULT_ITEMS for TestLowAIMode (especially for anonymous note)
TEST_DEFAULT_ITEMS_LOW_AI = {
    "anonymous note": {"description": "A mysterious note.", "readable": True, "takeable": True}
}


@patch('game_engine.game_state.CHARACTERS_DATA', TEST_CHAR_DATA_FOR_LOW_AI)
@patch('game_engine.game_state.LOCATIONS_DATA', TEST_LOC_DATA_FOR_LOW_AI)
@patch('game_engine.event_manager.DEFAULT_ITEMS', TEST_DEFAULT_ITEMS_LOW_AI) # For event manager item creation
@patch('game_engine.character_module.CHARACTERS_DATA', TEST_CHAR_DATA_FOR_LOW_AI) # For character module loading
class TestLowAIMode(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        # Simplified setup: directly initialize player without selection process
        self.game.all_character_objects = {
            name: Character.from_dict({"name": name, "is_player": (name == "TestPlayer")}, data)
            for name, data in TEST_CHAR_DATA_FOR_LOW_AI.items()
        }
        self.game.player_character = self.game.all_character_objects["TestPlayer"]
        self.game.player_character.is_player = True
        self.game.current_location_name = self.game.player_character.default_location
        self.game.initialize_dynamic_location_items() # Ensure items are initialized
        self.game.update_npcs_in_current_location()

        self.game.gemini_api = MagicMock(spec=GeminiAPI)
        self.game.gemini_api.model = MagicMock() # Simulate that a model is available by default
        self.game.gemini_api.chosen_model_name = "test_low_ai_model" # Add for save/load
        self.game.event_manager = EventManager(self.game) # Re-init with mocked game

        # Common mocks
        self.mock_print_color = patch.object(self.game, '_print_color').start()
        self.mock_input_color = patch.object(self.game, '_input_color').start() # Added this
        self.mock_random_choice = patch('random.choice').start()

    def tearDown(self):
        patch.stopall()

    def test_toggle_low_ai_data_mode(self):
        self.assertFalse(self.game.low_ai_data_mode, "Low AI mode should be False initially.")

        # First toggle: ON
        self.game._process_command("toggle_lowai", None)
        self.assertTrue(self.game.low_ai_data_mode)
        self.mock_print_color.assert_called_with("Low AI Data Mode is now ON.", Colors.MAGENTA)

        # Second toggle: OFF
        self.game._process_command("toggle_lowai", None)
        self.assertFalse(self.game.low_ai_data_mode)
        self.mock_print_color.assert_called_with("Low AI Data Mode is now OFF.", Colors.MAGENTA)

    @patch('game_engine.game_state.SAVE_GAME_FILE', "test_savegame_low_ai.json")
    def test_low_ai_data_mode_save_and_load(self):
        # Ensure file does not exist from previous failed run
        if os.path.exists("test_savegame_low_ai.json"):
            os.remove("test_savegame_low_ai.json")

        self.game.low_ai_data_mode = True
        self.game.save_game()

        # Reset game state for loading
        self.game.low_ai_data_mode = False

        # Create a new game instance to simulate loading from scratch
        new_game = Game()
        # Minimal setup for load_game to run without crashing
        new_game.gemini_api = MagicMock(spec=GeminiAPI) # Mock API for new instance too
        new_game.gemini_api.chosen_model_name = None # It would be None before load typically
        new_game._print_color = MagicMock() # Mock print for new instance

        loaded_successfully = new_game.load_game()
        self.assertTrue(loaded_successfully, "Game should load successfully.")
        self.assertTrue(new_game.low_ai_data_mode, "Low AI mode should be True after loading.")

        # Clean up the test save file
        if os.path.exists("test_savegame_low_ai.json"):
            os.remove("test_savegame_low_ai.json")

    def test_display_atmospheric_details_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_atmospheric_details = MagicMock()

        expected_detail = "The air is still and quiet."
        self.mock_random_choice.return_value = expected_detail

        # Ensure STATIC_ATMOSPHERIC_DETAILS is not empty for random.choice
        with patch('game_engine.game_state.STATIC_ATMOSPHERIC_DETAILS', [expected_detail, "Another detail"]):
            self.game.display_atmospheric_details()

        self.mock_print_color.assert_any_call(f"\n{expected_detail}", Colors.CYAN)
        self.game.gemini_api.get_atmospheric_details.assert_not_called()

    def test_handle_think_command_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_player_reflection = MagicMock()

        expected_reflection = "You ponder your next move."
        self.mock_random_choice.return_value = expected_reflection

        with patch('game_engine.game_state.STATIC_PLAYER_REFLECTIONS', [expected_reflection, "Another thought"]):
            self.game._handle_think_command()

        self.mock_print_color.assert_any_call(f"Inner thought: \"{expected_reflection}\"", Colors.GREEN)
        self.game.gemini_api.get_player_reflection.assert_not_called()

    def test_look_at_scenery_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_scenery_observation = MagicMock()
        self.game.gemini_api.get_enhanced_observation = MagicMock() # Also mock this as it's in the same path

        scenery_target = "window"
        # generate_static_scenery_observation returns one of a few options
        # We don't need to mock random.choice here if we check for partial static output.
        # However, to be precise, we can mock the function itself.
        expected_scenery_obs = f"You observe the {scenery_target}. It is as it seems."
        with patch('game_engine.game_state.generate_static_scenery_observation', return_value=expected_scenery_obs):
            self.game._handle_look_command(scenery_target)

        # Check if the static observation was printed (color might vary based on implementation)
        # The current implementation prints static scenery observation in DIM
        printed_texts = " ".join(c[0][0] for c in self.mock_print_color.call_args_list)
        self.assertIn(expected_scenery_obs, printed_texts)
        self.game.gemini_api.get_scenery_observation.assert_not_called()
        # Also check that enhanced observation for scenery wasn't called if the main one was static
        # (This depends on how base_desc_for_skill_check is handled for static scenery)
        # For now, we just ensure the primary AI call is skipped. A more robust test would check base_desc.

    @patch('game_engine.game_state.DEFAULT_ITEMS', {
        "fresh newspaper": {"description": "Today's news.", "readable": True}
    })
    def test_read_newspaper_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.player_character.inventory = [{"name": "fresh newspaper", "quantity": 1}]
        self.game.gemini_api.get_newspaper_article_snippet = MagicMock()

        expected_snippet = "The headlines are dull today."
        self.mock_random_choice.return_value = expected_snippet

        # Ensure the item exists in player's inventory for _handle_read_item
        # The _handle_read_item is called from handle_use_item
        with patch('game_engine.game_state.STATIC_NEWSPAPER_SNIPPETS', [expected_snippet, "Other news."]):
             self.game.handle_use_item("fresh newspaper", None, "read") # Correct way to trigger _handle_read_item

        # Static newspaper snippets are printed with YELLOW in the current implementation if AI was not attempted
        # but if low_ai_data_mode is true, it's CYAN.
        self.mock_print_color.assert_any_call(f"An article catches your eye: \"{expected_snippet}\"", Colors.CYAN)
        self.game.gemini_api.get_newspaper_article_snippet.assert_not_called()

    # --- Tests for EventManager with Low AI Mode ---
    def test_event_action_letter_from_mother_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_player_reflection = MagicMock()
        # Specific setup for this event if needed, e.g., player location
        self.game.player_character.name = "Rodion Raskolnikov" # Event is specific to him
        self.game.current_location_name = "Raskolnikov's Garret"

        expected_reflection = "The letter brings a wave of despair."
        self.mock_random_choice.return_value = expected_reflection

        with patch('game_engine.event_manager.STATIC_PLAYER_REFLECTIONS', [expected_reflection, "Other thoughts."]):
            self.game.event_manager.action_letter_from_mother()

        printed_text = " ".join(c[0][0] for c in self.mock_print_color.call_args_list)
        self.assertIn(f"Your thoughts race: \"{expected_reflection}\"", printed_text)
        self.game.gemini_api.get_player_reflection.assert_not_called()

    def test_event_action_find_anonymous_note_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_generated_text_document = MagicMock()

        # This event adds the note to dynamic_location_items
        self.game.dynamic_location_items[self.game.current_location_name] = []

        self.game.event_manager.action_find_anonymous_note()

        # Check that the static content was used to create the note
        found_note = False
        for item_data in self.game.dynamic_location_items.get(self.game.current_location_name, []):
            if item_data["name"] == "anonymous note":
                self.assertEqual(item_data.get("generated_content"), STATIC_ANONYMOUS_NOTE_CONTENT)
                found_note = True
                break
        self.assertTrue(found_note, "anonymous note with static content should be created.")
        self.game.gemini_api.get_generated_text_document.assert_not_called()

    def test_event_attempt_npc_npc_interaction_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_npc_to_npc_interaction = MagicMock()

        # Setup NPCs in the current location
        npc1 = self.game.all_character_objects["TestNPC1"]
        npc2 = self.game.all_character_objects["TestNPC2"]
        self.game.npcs_in_current_location = [npc1, npc2]

        expected_interaction = "NPC1 and NPC2 nod at each other."
        self.mock_random_choice.return_value = expected_interaction

        with patch('game_engine.event_manager.STATIC_NPC_NPC_INTERACTIONS', [expected_interaction, "Other interaction."]):
            self.game.event_manager.attempt_npc_npc_interaction()

        printed_text = " ".join(c[0][0] for c in self.mock_print_color.call_args_list if isinstance(c[0][0], str))
        # The static interactions might have newlines or specific formatting
        # We'll check if the core text is present.
        self.assertIn(expected_interaction.split(":")[0], printed_text) # Check for at least part of it
        self.game.gemini_api.get_npc_to_npc_interaction.assert_not_called()

    def test_event_action_street_life_haymarket_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.get_street_life_event_description = MagicMock()
        self.game.current_location_name = "Haymarket Square" # Event specific location

        expected_description = "A vendor shouts his wares."
        self.mock_random_choice.return_value = expected_description

        with patch('game_engine.event_manager.STATIC_STREET_LIFE_EVENTS', [expected_description, "Something else happens."]):
            self.game.event_manager.action_street_life_haymarket()

        printed_text = " ".join(c[0][0] for c in self.mock_print_color.call_args_list)
        self.assertIn(f"(Nearby, {expected_description})", printed_text)
        self.game.gemini_api.get_street_life_event_description.assert_not_called()

    # --- Test for AI usage when Low AI Mode is OFF ---
    def test_display_atmospheric_details_low_ai_mode_off(self):
        self.game.low_ai_data_mode = False

        ai_generated_detail = "A truly unique atmospheric detail from AI."
        self.game.gemini_api.get_atmospheric_details = MagicMock(return_value=ai_generated_detail)

        self.game.display_atmospheric_details()

        self.game.gemini_api.get_atmospheric_details.assert_called_once()
        self.mock_print_color.assert_any_call(f"\n{ai_generated_detail}", Colors.CYAN)

    # --- Tests for Game._initialize_game() ---
    @patch.object(Game, 'load_all_characters') # Mock to prevent full character setup
    @patch.object(Game, 'select_player_character') # Mock to prevent interactive player selection
    @patch.object(Game, 'update_current_location_details')
    @patch.object(Game, 'display_atmospheric_details')
    @patch.object(Game, 'display_help')
    def test_initialize_game_sets_low_ai_mode_from_configure_yes(self, mock_disp_help, mock_disp_atm, mock_upd_loc, mock_sel_player, mock_load_chars):
        # Mock configure to return Low AI Mode = True
        self.game.gemini_api.configure = MagicMock(return_value={"api_configured": True, "low_ai_preference": True})
        # Mock input for "load or new game" prompt to select new game
        self.mock_input_color.return_value = ""
        mock_sel_player.return_value = True # Ensure select_player_character indicates success

        self.game._initialize_game()
        self.assertTrue(self.game.low_ai_data_mode)

    @patch.object(Game, 'load_all_characters')
    @patch.object(Game, 'select_player_character')
    @patch.object(Game, 'update_current_location_details')
    @patch.object(Game, 'display_atmospheric_details')
    @patch.object(Game, 'display_help')
    def test_initialize_game_sets_low_ai_mode_from_configure_no(self, mock_disp_help, mock_disp_atm, mock_upd_loc, mock_sel_player, mock_load_chars):
        self.game.gemini_api.configure = MagicMock(return_value={"api_configured": True, "low_ai_preference": False})
        self.mock_input_color.return_value = ""
        mock_sel_player.return_value = True

        self.game._initialize_game()
        self.assertFalse(self.game.low_ai_data_mode)

    @patch.object(Game, 'load_all_characters')
    @patch.object(Game, 'select_player_character')
    @patch.object(Game, 'update_current_location_details')
    @patch.object(Game, 'display_atmospheric_details')
    @patch.object(Game, 'display_help')
    def test_initialize_game_low_ai_mode_defaults_false_if_api_skipped(self, mock_disp_help, mock_disp_atm, mock_upd_loc, mock_sel_player, mock_load_chars):
        self.game.gemini_api.configure = MagicMock(return_value={"api_configured": False, "low_ai_preference": False})
        self.mock_input_color.return_value = ""
        mock_sel_player.return_value = True

        self.game._initialize_game()
        self.assertFalse(self.game.low_ai_data_mode)

    @patch('game_engine.game_state.os.getenv')
    @patch.object(Game, 'load_game')
    @patch.object(Game, 'select_player_character') # Still need to mock this if load_game fails or is bypassed
    @patch.object(Game, 'load_all_characters')
    @patch.object(Game, 'update_current_location_details')
    @patch.object(Game, 'display_atmospheric_details')
    @patch.object(Game, 'display_help')
    def test_initialize_game_load_game_overrides_configure_low_ai_pref(self, mock_disp_help, mock_disp_atm, mock_upd_loc, mock_load_chars_init, mock_sel_player, mock_load_game_method, mock_os_getenv):
        # Ensure interactive path by mocking getenv
        mock_os_getenv.return_value = None
        # Simulate that configure() suggests Low AI Mode = False
        self.game.gemini_api.configure = MagicMock(return_value={"api_configured": True, "low_ai_preference": False})

        # Simulate user typing "load"
        self.mock_input_color.return_value = "load"

        # Configure mock for self.game.load_game()
        def side_effect_load_game():
            self.game.low_ai_data_mode = True # Simulate that loaded game had True for low_ai
            # Simulate other necessary attributes being set by load_game for _initialize_game to proceed
            self.game.player_character = self.game.all_character_objects["TestPlayer"] # Use player from setUp
            self.game.player_character.is_player = True
            self.game.current_location_name = "Test Chamber"
            return True # Indicate load was successful

        mock_load_game_method.side_effect = side_effect_load_game

        initialization_successful = self.game._initialize_game()
        self.assertTrue(initialization_successful, "_initialize_game should return True on successful load.")
        self.assertTrue(self.game.low_ai_data_mode, "low_ai_data_mode should be True (from loaded game).")
        mock_load_game_method.assert_called_once()


class TestGeminiAPIConfiguration(unittest.TestCase):
    def setUp(self):
        self.api = GeminiAPI()
        self.mock_print_func = MagicMock()
        self.mock_input_func = MagicMock()

        # Assign directly to the internal attributes used by configure
        self.api._print_color_func = self.mock_print_func
        self.api._input_color_func = self.mock_input_func

        # Patch methods within the GeminiAPI instance or its module
        self.patch_attempt_api_setup = patch.object(self.api, '_attempt_api_setup')
        self.mock_attempt_api_setup = self.patch_attempt_api_setup.start()

        self.patch_os_path_exists = patch('game_engine.gemini_interactions.os.path.exists')
        self.mock_os_path_exists = self.patch_os_path_exists.start()

        self.patch_open = patch('game_engine.gemini_interactions.open', new_callable=unittest.mock.mock_open)
        self.mock_open_file = self.patch_open.start()

        self.patch_os_getenv = patch('game_engine.gemini_interactions.os.getenv')
        self.mock_os_getenv = self.patch_os_getenv.start()

        # Default mock behaviors
        self.mock_os_getenv.return_value = None # No ENV key by default
        self.mock_os_path_exists.return_value = False # No config file by default
        # self.mock_attempt_api_setup.return_value = False # API setup fails by default - will set per test

    def tearDown(self):
        patch.stopall()

    def _configure_mock_attempt_api_setup_success(self):
        def mock_setup(api_key, source, model_id):
            self.api.chosen_model_name = model_id
            self.api.model = MagicMock() # Simulate model instance being set
            return True
        self.mock_attempt_api_setup.side_effect = mock_setup

    def test_ask_for_model_selection_updated_options_and_default(self):
        # This test focuses on the behavior of _ask_for_model_selection,
        # which is called by configure. We'll trigger it via configure.
        self.mock_os_getenv.return_value = None # No ENV key
        self._configure_mock_attempt_api_setup_success()

        # User provides key, presses Enter for default model, then 'n' for Low AI mode, then 'n' for saving ENV key combo
        self.mock_input_func.side_effect = ["dummy_manual_key", "", "n", "n"]

        self.api.configure(self.mock_print_func, self.mock_input_func)

        # Check that the correct model options were printed
        model_prompt_calls = [args[0] for args, _ in self.mock_print_func.call_args_list if args and isinstance(args[0], str)]

        self.assertTrue(any("Gemini 3 Pro Preview (Default) (ID: gemini-3-pro-preview)" in call for call in model_prompt_calls))
        self.assertTrue(any("Gemini 3 Flash Preview (ID: gemini-3-flash-preview)" in call for call in model_prompt_calls))

        # Check that the input prompt was for choices 1-2
        input_prompt_found = False
        for call_args in self.mock_input_func.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], str) and "(1-2), or press Enter for default): " in args[0]:
                input_prompt_found = True
                break
        self.assertTrue(input_prompt_found, "Input prompt for 1-2 choices not found.")

        self.assertEqual(self.api.chosen_model_name, DEFAULT_GEMINI_MODEL_NAME)

    def test_configure_select_first_model_successfully(self):
        self.mock_os_getenv.return_value = None # No ENV key
        self._configure_mock_attempt_api_setup_success()
        # Input: "dummy_manual_key", "1" for model, "n" for Low AI, "n" for saving ENV key combo
        self.mock_input_func.side_effect = ["dummy_manual_key", "1", "n", "n"]

        self.api.configure(self.mock_print_func, self.mock_input_func)
        self.assertEqual(self.api.chosen_model_name, 'gemini-3-pro-preview')
        self.mock_attempt_api_setup.assert_called_with("dummy_manual_key", "user input", 'gemini-3-pro-preview')

    def test_configure_successful_api_setup_prompts_low_ai_mode_yes(self):
        # Simulate manual API key input path
        self.mock_os_getenv.return_value = None
        self.mock_os_path_exists.return_value = False # No config file

        # Inputs: "dummy_api_key", "" (for default model), "y" (for low AI), "n" (for save key)
        self.mock_input_func.side_effect = ["dummy_api_key", "", "y", "n"]
        self._configure_mock_attempt_api_setup_success()

        config_result = self.api.configure(self.mock_print_func, self.mock_input_func)

        low_ai_prompt_found = False
        low_ai_enabled_msg_found = False
        for call_args in self.mock_input_func.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], str) and "Enable Low AI Data Mode?" in args[0]:
                low_ai_prompt_found = True
                break
        for call_args in self.mock_print_func.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], str) and "Low AI Data Mode will be ENABLED." in args[0]:
                low_ai_enabled_msg_found = True
                break

        self.assertTrue(low_ai_prompt_found, "Low AI mode prompt not found.")
        self.assertTrue(low_ai_enabled_msg_found, "Low AI Mode ENABLED message not found.")
        self.assertEqual(config_result, {"api_configured": True, "low_ai_preference": True})
        self.assertIsNotNone(self.api.model)

    def test_configure_successful_api_setup_prompts_low_ai_mode_no(self):
        self.mock_os_getenv.return_value = None
        self.mock_os_path_exists.return_value = False
        # Inputs: "dummy_api_key", "" (default model), "n" (low AI), "n" (save key)
        self.mock_input_func.side_effect = ["dummy_api_key", "", "n", "n"]
        self._configure_mock_attempt_api_setup_success()

        config_result = self.api.configure(self.mock_print_func, self.mock_input_func)

        disabled_msg_found = False
        for call_args in self.mock_print_func.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], str) and "Low AI Data Mode will be DISABLED (default)." in args[0]:
                disabled_msg_found = True
                break
        self.assertTrue(disabled_msg_found, "Low AI Mode DISABLED message not found.")
        self.assertEqual(config_result, {"api_configured": True, "low_ai_preference": False})

    def test_configure_skip_api_returns_low_ai_false(self):
        self.mock_os_getenv.return_value = None
        self.mock_os_path_exists.return_value = False
        self.mock_input_func.return_value = "skip" # User types 'skip' for API key

        config_result = self.api.configure(self.mock_print_func, self.mock_input_func)
        self.assertEqual(config_result, {"api_configured": False, "low_ai_preference": False})
        self.assertIsNone(self.api.model)


# This is the end of TestGeminiAPIConfiguration, the next tests will be pasted into TestLowAIMode.

# --- Tests for Game._initialize_game() within TestLowAIMode ---
# The following methods are moved to TestLowAIMode class below

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
