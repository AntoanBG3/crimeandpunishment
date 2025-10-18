import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to sys.path to allow imports from game_engine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game
from game_engine.character_module import Character
from game_engine.game_config import DEFAULT_ITEMS, Colors

class TestGameStateHandlers(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = MagicMock(spec=Character)
        self.game.player_character.name = "Test Player"
        self.game.player_character.apparent_state = "normal"
        self.game.player_character.inventory = []
        self.game.all_character_objects = {}
        self.game.current_location_name = "Test Location"
        self.game.dynamic_location_items = {}
        self.game.npcs_in_current_location = []
        self.game.gemini_api = MagicMock()
        self.game._print_color = MagicMock()
        self.game.get_current_time_period = MagicMock(return_value="Morning")
        self.game._get_objectives_summary = MagicMock(return_value="No objectives.")

    def test_initialization(self):
        self.assertIsInstance(self.game, Game)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"test_item": {"description": "A test item."}})
    def test_handle_look_at_location_item_found(self):
        self.game.dynamic_location_items = {"Test Location": [{"name": "test_item", "quantity": 1}]}
        self.assertTrue(self.game._handle_look_at_location_item("test_item"))
        self.game._print_color.assert_any_call("You examine the test_item:", Colors.GREEN)

    def test_handle_look_at_location_item_not_found(self):
        self.game.dynamic_location_items = {"Test Location": []}
        self.assertFalse(self.game._handle_look_at_location_item("test_item"))

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"test_item": {"description": "A test item."}})
    def test_handle_look_at_inventory_item_found(self):
        self.game.player_character.inventory = [{"name": "test_item", "quantity": 1}]
        self.assertTrue(self.game._handle_look_at_inventory_item("test_item"))
        self.game._print_color.assert_any_call("You examine your test_item:", Colors.GREEN)

    def test_handle_look_at_inventory_item_not_found(self):
        self.game.player_character.inventory = []
        self.assertFalse(self.game._handle_look_at_inventory_item("test_item"))

    def test_handle_look_at_npc_found(self):
        npc_mock = MagicMock(spec=Character)
        npc_mock.name = "Test NPC"
        npc_mock.apparent_state = "calm"
        npc_mock.persona = "A test NPC."
        npc_mock.get_player_memory_summary = MagicMock(return_value="No memories.")
        npc_mock.relationship_with_player = 0
        self.game.npcs_in_current_location = [npc_mock]
        self.game.gemini_api.get_player_reflection.return_value = "A reflection."
        self.assertTrue(self.game._handle_look_at_npc("test npc"))
        self.game._print_color.assert_any_call(f"You look closely at {Colors.YELLOW}Test NPC{Colors.RESET} (appears calm):", Colors.WHITE)

    def test_handle_look_at_npc_not_found(self):
        self.game.npcs_in_current_location = []
        self.assertFalse(self.game._handle_look_at_npc("Test NPC"))

    @patch('game_engine.game_state.LOCATIONS_DATA', {"Test Location": {"description": "A room with a window."}})
    def test_handle_look_at_scenery_found(self):
        self.assertTrue(self.game._handle_look_at_scenery("window"))
        self.game._print_color.assert_any_call("You focus on the window...", Colors.WHITE)

    @patch('game_engine.game_state.LOCATIONS_DATA', {"Test Location": {"description": "A room with a window."}})
    def test_handle_look_at_scenery_not_found(self):
        self.assertFalse(self.game._handle_look_at_scenery("dragon"))

    def test_handle_look_at_npc_found(self):
        npc_mock = MagicMock(spec=Character)
        npc_mock.name = "Test NPC"
        npc_mock.apparent_state = "calm"
        npc_mock.persona = "A test NPC."
        npc_mock.get_player_memory_summary = MagicMock(return_value="No memories.")
        npc_mock.relationship_with_player = 0
        self.game.npcs_in_current_location = [npc_mock]
        self.assertTrue(self.game._handle_look_at_npc("test npc"))
        self.game._print_color.assert_any_call(f"You look closely at {Colors.YELLOW}Test NPC{Colors.RESET} (appears calm):", Colors.WHITE)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"readable_item": {"description": "A readable item.", "readable": True}})
    def test_handle_read_item_readable(self):
        item_props = DEFAULT_ITEMS.get("readable_item")
        self.game.gemini_api.get_item_interaction_description = MagicMock(return_value="You read the item.")
        self.assertTrue(self.game._handle_read_item("readable_item", item_props, {}))
        self.game._print_color.assert_any_call("You read the readable_item. You read the item.", Colors.YELLOW)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"unreadable_item": {"description": "An unreadable item.", "readable": False}})
    def test_handle_read_item_unreadable(self):
        item_props = DEFAULT_ITEMS.get("unreadable_item")
        self.assertFalse(self.game._handle_read_item("unreadable_item", item_props, {}))
        self.game._print_color.assert_any_call("You can't read the unreadable_item.", Colors.YELLOW)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"test_item": {"description": "A test item."}})
    def test_handle_give_item_success(self):
        self.game.player_character.has_item.return_value = True
        self.game.player_character.remove_from_inventory.return_value = True
        npc_mock = MagicMock(spec=Character)
        npc_mock.name = "Test NPC"
        npc_mock.relationship_with_player = 0
        self.game.npcs_in_current_location = [npc_mock]
        self.game.gemini_api.get_npc_dialogue.return_value = "Thank you."
        self.assertTrue(self.game._handle_give_item("test_item", {}, "Test NPC"))
        self.game.player_character.remove_from_inventory.assert_called_with("test_item", 1)
        npc_mock.add_to_inventory.assert_called_with("test_item", 1)

    def test_handle_give_item_npc_not_found(self):
        self.game.player_character.has_item.return_value = True
        self.assertFalse(self.game._handle_give_item("test_item", {}, "Test NPC"))
        self.game._print_color.assert_any_call("You don't see 'Test NPC' here to give anything to.", Colors.RED)

    def test_handle_give_item_player_does_not_have_item(self):
        self.game.player_character.has_item.return_value = False
        npc_mock = MagicMock(spec=Character)
        npc_mock.name = "Test NPC"
        self.game.npcs_in_current_location = [npc_mock]
        self.assertFalse(self.game._handle_give_item("test_item", {}, "Test NPC"))
        self.game._print_color.assert_any_call("You don't have test_item to give.", Colors.RED)

    @patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"test_item": {"description": "A test item.", "use_effect_player": "test_effect"}})
    def test_handle_self_use_item_success(self):
        self.game.player_character.inventory = [{"name": "test_item"}]
        item_props = DEFAULT_ITEMS.get("test_item")
        self.game._handle_self_use_item = MagicMock(return_value=True)
        self.game.handle_use_item("test_item", None, "use_self_implicit")
        self.game._handle_self_use_item.assert_called_with("test_item", item_props, "test_effect")

    def test_handle_self_use_item_no_effect(self):
        with patch.dict('game_engine.game_state.DEFAULT_ITEMS', {"test_item": {"description": "A test item."}}):
            self.game.player_character.inventory = [{"name": "test_item"}]
            self.assertFalse(self.game.handle_use_item("test_item", None, "use_self_implicit"))
            self.game._print_color.assert_any_call("You contemplate the test_item, but don't find a specific use for it right now.", Colors.YELLOW)

if __name__ == '__main__':
    unittest.main()