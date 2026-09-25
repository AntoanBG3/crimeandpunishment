"""Real-file save failures must not destroy the current playable session."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from game_engine.game_state import Game


class TestPersistenceBoundary(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.world_manager.load_all_characters()
        self.game.player_character = self.game.all_character_objects['Rodion Raskolnikov']
        self.game.player_character.is_player = True
        self.game.current_location_name = self.game.player_character.current_location
        self.game.world_manager.initialize_dynamic_location_items()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'savegame.json'
        self.patch = patch.object(self.game, '_get_save_file_path', return_value=str(self.path))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        for method in ('_print_color', '_print_renderable', '_display_load_recap'):
            p = patch.object(self.game, method)
            p.start()
            self.addCleanup(p.stop)
        self.game.save_game()
        self.saved = json.loads(self.path.read_text())

    def test_rejected_save_leaves_live_state_intact(self):
        variants = [None, [], {}, {'game_time': 999}, {**self.saved, 'game_time': 'tomorrow'},
                    {**self.saved, 'current_location_name': 'missing location'},
                    {**self.saved, 'all_character_objects_state': []},
                    {**self.saved, 'triggered_events': [None]}]
        bad_character = copy.deepcopy(self.saved)
        bad_character['all_character_objects_state']['Rodion Raskolnikov']['inventory'] = 42
        variants.append(bad_character)
        bad_content = copy.deepcopy(self.saved)
        bad_content['all_character_objects_state']['Rodion Raskolnikov']['inventory'][0]['generated_content'] = 123
        variants.append(bad_content)
        player = self.game.player_character
        characters = self.game.all_character_objects
        for payload in variants:
            with self.subTest(payload=type(payload).__name__):
                before = (self.game.game_time, self.game.current_location_name, player.to_dict())
                self.path.write_text(json.dumps(payload))
                self.assertFalse(self.game.load_game())
                self.assertIs(self.game.player_character, player)
                self.assertIs(self.game.all_character_objects, characters)
                self.assertEqual(before, (self.game.game_time, self.game.current_location_name,
                                          player.to_dict()))

    def test_valid_round_trip_clears_transient_scene_selection(self):
        self.game.numbered_actions_context = [{'type': 'exit', 'target': 'stale'}]
        with patch.object(self.game.world_manager, 'update_current_location_details'):
            self.assertTrue(self.game.load_game())
        self.assertEqual(self.game.numbered_actions_context, [])
        self.assertEqual(self.game.player_character.name, 'Rodion Raskolnikov')

    def test_replace_failure_preserves_previous_file(self):
        original = self.path.read_bytes()
        with patch('os.replace', side_effect=PermissionError('read only')):
            self.game.save_game()
        self.assertEqual(self.path.read_bytes(), original)

    def test_legacy_text_memories_load_and_remain_readable(self):
        player = self.saved['all_character_objects_state']['Rodion Raskolnikov']
        player['memory_about_player'] = ['An old recollection.']
        self.path.write_text(json.dumps(self.saved))
        self.assertTrue(self.game.load_game())
        self.assertIn('An old recollection.', self.game.player_character.get_player_memory_summary(1))

    def test_malformed_nested_memory_and_overflow_numbers_are_rejected(self):
        variants = [{**self.saved, 'player_notoriety_level': 10 ** 400}]
        for content in ({'summary': 42}, {'player_statement': []}, {'quantity': 'two'},
                        {'change': {}}, {'topic_hint': ['crime']}):
            payload = copy.deepcopy(self.saved)
            player = payload['all_character_objects_state']['Rodion Raskolnikov']
            player['memory_about_player'] = [{'content': content, 'type': 'dialogue_exchange'}]
            variants.append(payload)
        active = self.game.player_character
        for payload in variants:
            with self.subTest(payload=payload['player_notoriety_level']):
                self.path.write_text(json.dumps(payload))
                self.assertFalse(self.game.load_game())
                self.assertIs(self.game.player_character, active)


if __name__ == '__main__':
    unittest.main()
