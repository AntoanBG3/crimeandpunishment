"""Transfers must preserve authored/generated content and actual item counts."""

import copy
import unittest
from unittest.mock import MagicMock

from game_engine.game_state import Game


class TestItemTransfers(unittest.TestCase):
    def setUp(self):
        self.game = Game(terminal_io=MagicMock())
        self.game.world_manager.load_all_characters()
        self.game.player_character = self.game.all_character_objects['Rodion Raskolnikov']
        self.game.current_location_name = self.game.player_character.current_location
        self.game.low_ai_data_mode = True
        self.game.npcs_in_current_location = []
        self.note = {'name': 'anonymous note', 'quantity': 1,
                     'generated_content': 'Someone is watching.'}
        self.game.dynamic_location_items[self.game.current_location_name] = [copy.deepcopy(self.note)]

    def test_take_read_drop_and_take_preserve_note_text(self):
        self.assertTrue(self.game._handle_take_command('anonymous note')[0])
        note = next(i for i in self.game.player_character.inventory if i['name'] == 'anonymous note')
        self.assertEqual(note['generated_content'], self.note['generated_content'])
        self.assertTrue(self.game.handle_use_item('anonymous note', interaction_type='read'))
        self.assertTrue(self.game._handle_drop_command('anonymous note')[0])
        self.assertEqual(self.game.dynamic_location_items[self.game.current_location_name], [self.note])
        self.assertTrue(self.game._handle_take_command('anonymous note')[0])

    def test_give_and_failed_give_preserve_document(self):
        player = self.game.player_character
        npc = self.game.all_character_objects['Sonya Marmeladova']
        self.game.npcs_in_current_location = [npc]
        player.inventory = [copy.deepcopy(self.note)]
        self.assertTrue(self.game.handle_use_item('anonymous note', 'Sonya', 'give'))
        received = next(i for i in npc.inventory if i['name'] == 'anonymous note')
        self.assertEqual(received['generated_content'], self.note['generated_content'])
        player.inventory = [copy.deepcopy(self.note)]
        self.assertFalse(self.game.handle_use_item('anonymous note', 'Sonya', 'give'))
        self.assertEqual(player.inventory, [self.note])

    def test_stack_without_explicit_quantity_uses_legacy_default(self):
        room = self.game.dynamic_location_items[self.game.current_location_name]
        room[:] = [{'name': 'worn coin'}]
        self.assertTrue(self.game._handle_take_command('coin')[0])
        self.assertEqual(room, [])
