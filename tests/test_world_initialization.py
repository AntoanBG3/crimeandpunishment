"""Fresh games must use the same authored mechanics as restored games."""

import unittest

from game_engine.character_module import CHARACTERS_DATA
from game_engine.game_state import Game


class TestWorldInitialization(unittest.TestCase):
    def test_authored_skills_and_relationships_survive_initialization(self):
        game = Game()
        game.world_manager.load_all_characters()
        for name, character in game.all_character_objects.items():
            with self.subTest(character=name):
                data = CHARACTERS_DATA[name]
                self.assertEqual(character.skills, data.get('skills', {}))
                self.assertEqual(character.npc_relationships, data.get('npc_relationships', {}))
                for stat, value in data.get('psychology', {}).items():
                    self.assertEqual(character.psychology[stat], value)


if __name__ == '__main__':
    unittest.main()
