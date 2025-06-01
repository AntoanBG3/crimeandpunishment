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
from game_engine.gemini_interactions import GeminiAPI
from game_engine.game_state import Game
from game_engine.event_manager import EventManager
from game_engine.game_config import Colors, TIME_UNITS_PER_PLAYER_ACTION

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
    "Raskolnikov's axe": {"description": "A weighty axe.", "use_effect_player": "grip_axe_and_reminisce_horror"},
    "cheap vodka": {"description": "A bottle of cheap spirits.", "use_effect_player": "drink_vodka_for_oblivion", "consumable": True, "stackable": True},
    "Fresh Newspaper": {"description": "Today's news.", "readable": True, "use_effect_player": "read_evolving_news_article"},
    "mother's letter": {"description": "A letter from Pulcheria.", "readable": True, "use_effect_player": "reread_letter_and_feel_familial_pressure"},
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
        self.game.player_character.inventory = []
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
        self.game._handle_look_command(None)
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
        action_taken, show_atmospherics, time_units, _ = self.game._process_command('select_item', item_name)
        mock_specific_look.assert_called_once_with(item_name)
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

class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_game = MagicMock(spec=Game)
        self.mock_game.gemini_api = MagicMock(spec=GeminiAPI)
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
        self.player.inventory.append({"name": "Raskolnikov's axe", "quantity": 1})
        self.game.handle_use_item("Raskolnikov's axe", None, "use_self_implicit")
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
        self.player.inventory.append({"name": "Fresh Newspaper", "quantity": 1})
        self.player.add_journal_entry = MagicMock()
        self.game.gemini_api.get_newspaper_article_snippet = MagicMock(return_value="A terrible crime was reported...")
        self.game.handle_use_item("Fresh Newspaper", None, "read")
        self.game.gemini_api.get_newspaper_article_snippet.assert_called_once()
        self.player.add_journal_entry.assert_called_once_with("News", "A terrible crime was reported...", "Day 1, Morning")
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


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
