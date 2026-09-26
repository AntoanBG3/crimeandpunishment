"""Authored data and seeded malformed inputs exercise cross-module boundaries."""

import copy
import random
import unittest
from unittest.mock import MagicMock

from game_engine.character_module import CHARACTERS_DATA
from game_engine.game_config import DEFAULT_ITEMS
from game_engine.game_state import Game
from game_engine.location_module import LOCATIONS_DATA


class TestAuditInvariants(unittest.TestCase):
    def test_authored_references_and_world_reachability(self):
        for name, character in CHARACTERS_DATA.items():
            with self.subTest(character=name):
                for location in [character['default_location'], *character.get('accessible_locations', []),
                                 *character.get('schedule', {}).values()]:
                    self.assertIn(location, LOCATIONS_DATA)
                for item in character.get('inventory_items', []):
                    self.assertIn(item['name'], DEFAULT_ITEMS)
                if not character.get('non_playable', False):
                    visited, pending = set(), [character['default_location']]
                    while pending:
                        location = pending.pop()
                        if location not in visited:
                            visited.add(location)
                            pending.extend(LOCATIONS_DATA[location].get('exits', {}))
                    self.assertEqual(visited, set(LOCATIONS_DATA))
        for name, location in LOCATIONS_DATA.items():
            with self.subTest(location=name):
                for target in location.get('exits', {}):
                    self.assertIn(target, LOCATIONS_DATA)
                for item in location.get('items_present', []):
                    self.assertIn(item['name'], DEFAULT_ITEMS)
        for item in DEFAULT_ITEMS.values():
            if 'hidden_in_location' in item:
                self.assertIn(item['hidden_in_location'], LOCATIONS_DATA)

    def test_seeded_malformed_commands_do_not_mutate_the_world(self):
        terminal = MagicMock()
        game = Game(rng=random.Random(1729), terminal_io=terminal)
        game.world_manager.load_all_characters()
        game.player_character = game.all_character_objects['Rodion Raskolnikov']
        game.current_location_name = game.player_character.current_location
        game.gemini_api.model = None
        game.low_ai_data_mode = True
        before = copy.deepcopy(game.player_character.to_dict())
        rng = random.Random(1729)
        inputs = ['', '   ', '999999999', '???', '謎' * 100_000]
        inputs += ['§' + ''.join(rng.choices('ab Ё謎!?.\t🙂', k=rng.randrange(1, 512)))
                   for _ in range(200)]
        for text in inputs:
            terminal.read_line.return_value = text
            with self.subTest(input_preview=text[:20]):
                self.assertEqual(game.command_handler._get_player_input(), (None, None))
                self.assertEqual(game.player_character.to_dict(), before)
        for command in ('take', 'move to', 'talk to'):
            result = game.command_handler._process_command(command, 'unavailable target')
            self.assertFalse(result.action_taken)
            self.assertEqual(game.player_character.to_dict(), before)
