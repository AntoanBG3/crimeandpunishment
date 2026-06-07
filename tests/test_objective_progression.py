"""End-to-end reachability tests for the objective progression arc (finding #1).

These are the proof that each playable protagonist's story can actually reach an
ending through real gameplay events, not merely that ending stages exist in data.
"""
import unittest
from unittest.mock import patch
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game
from game_engine.character_module import Character, CHARACTERS_DATA
from game_engine.objective_progression import evaluate_player_progression


def build_player(name):
    data = CHARACTERS_DATA[name]
    return Character(
        name,
        data.get("persona", ""),
        data.get("greeting", ""),
        data.get("default_location", "Haymarket Square"),
        data.get("accessible_locations", []),
        data.get("objectives", []),
        data.get("inventory_items", []),
        data.get("schedule", {}),
        is_player=True,
    )


class TestObjectiveReachability(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.mock_print = patch.object(self.game, "_print_color").start()

    def tearDown(self):
        patch.stopall()

    def _npc(self, name):
        return Character(name, "", "", "Haymarket Square", ["Haymarket Square"])

    def _set(self, player_name, npcs=None, location=None):
        self.game.player_character = build_player(player_name)
        self.game.npcs_in_current_location = npcs or []
        self.game.current_location_name = location

    def _stage(self, obj_id):
        st = self.game.player_character.get_current_stage_for_objective(obj_id)
        return st.get("stage_id") if st else None

    def _assert_ending_reached(self, obj_id, expected_stage):
        pc = self.game.player_character
        obj = pc.get_objective_by_id(obj_id)
        self.assertTrue(obj.get("completed"), f"{obj_id} should be completed")
        st = pc.get_current_stage_for_objective(obj_id)
        self.assertTrue(st.get("is_ending_stage"), f"{obj_id} should be at an ending stage")
        self.assertEqual(self._stage(obj_id), expected_stage)
        self.assertTrue(
            self.game.world_manager._check_game_ending_conditions(),
            "game ending condition should fire",
        )

    # --- Raskolnikov: three distinct endings ---
    def test_rodion_siberia_path(self):
        self._set("Rodion Raskolnikov")
        evaluate_player_progression(self.game, "talk_to", "Sonya Marmeladova")
        self.assertEqual(self._stage("grapple_with_crime"), "seek_sonya")
        evaluate_player_progression(self.game, "talk_to", "Sonya Marmeladova")
        self.assertEqual(self._stage("grapple_with_crime"), "received_cross_from_sonya")
        self.assertTrue(self.game.player_character.has_item("sonya's cypress cross"))
        self.game.npcs_in_current_location = [self._npc("Sonya Marmeladova")]
        evaluate_player_progression(self.game, "confess")
        self.assertEqual(self._stage("grapple_with_crime"), "confessed_to_sonya")
        self.game.npcs_in_current_location = []
        self.game.current_location_name = "Police Station (General Area)"
        evaluate_player_progression(self.game, "confess")
        self._assert_ending_reached("grapple_with_crime", "siberia")

    def test_rodion_public_confession_path(self):
        self._set("Rodion Raskolnikov")
        evaluate_player_progression(self.game, "talk_to", "Sonya Marmeladova")
        evaluate_player_progression(self.game, "talk_to", "Sonya Marmeladova")
        self.game.npcs_in_current_location = [self._npc("Sonya Marmeladova")]
        evaluate_player_progression(self.game, "confess")
        self.game.npcs_in_current_location = []
        self.game.current_location_name = "Haymarket Square"
        evaluate_player_progression(self.game, "confess")
        self._assert_ending_reached("grapple_with_crime", "public_confession")

    def test_rodion_unrepentant_path(self):
        self._set("Rodion Raskolnikov")
        evaluate_player_progression(self.game, "talk_to", "Arkady Svidrigailov")
        self.assertEqual(self._stage("grapple_with_crime"), "isolate_further")
        self.game.current_location_name = "Haymarket Square"
        evaluate_player_progression(self.game, "confess")
        self._assert_ending_reached("grapple_with_crime", "unrepentant_end")

    # --- Sonya ---
    def test_sonya_follow_to_siberia(self):
        self._set("Sonya Marmeladova", location="Sonya's Room")
        self.assertTrue(self.game.player_character.has_item("sonya's cypress cross"))
        evaluate_player_progression(self.game, "talk_to", "Rodion Raskolnikov")
        self.assertEqual(self._stage("guide_raskolnikov"), "lazarus_reading")
        evaluate_player_progression(self.game, "talk_to", "Rodion Raskolnikov")
        self.assertEqual(self._stage("guide_raskolnikov"), "offer_cross")
        evaluate_player_progression(
            self.game, "give_item", "sonya's cypress cross", "Rodion Raskolnikov"
        )
        self.assertEqual(self._stage("guide_raskolnikov"), "receive_confession")
        self.game.npcs_in_current_location = [self._npc("Rodion Raskolnikov")]
        evaluate_player_progression(self.game, "confess")
        self._assert_ending_reached("guide_raskolnikov", "follow_to_siberia")

    # --- Porfiry ---
    def test_porfiry_case_solved(self):
        self._set("Porfiry Petrovich")
        evaluate_player_progression(self.game, "talk_to", "Rodion Raskolnikov")
        self.assertEqual(self._stage("solve_murders"), "psychological_probes")
        evaluate_player_progression(self.game, "persuade", "Rodion Raskolnikov")
        self.assertEqual(self._stage("solve_murders"), "closing_the_net")
        evaluate_player_progression(self.game, "persuade", "Rodion Raskolnikov")
        self.assertEqual(self._stage("solve_murders"), "encourage_confession")
        self.game.npcs_in_current_location = [self._npc("Rodion Raskolnikov")]
        evaluate_player_progression(self.game, "confess")
        self._assert_ending_reached("solve_murders", "case_solved")

    # --- Guards ---
    def test_secondary_objective_does_not_end_game(self):
        # help_family reaching its family_secure ending stage must NOT end Rodion's story.
        self._set("Rodion Raskolnikov")
        evaluate_player_progression(self.game, "talk_to", "Pyotr Petrovich Luzhin")
        evaluate_player_progression(self.game, "talk_to", "Arkady Svidrigailov")
        evaluate_player_progression(self.game, "talk_to", "Dunya Raskolnikova")
        hf = self.game.player_character.get_objective_by_id("help_family")
        self.assertEqual(self._stage("help_family"), "family_secure")
        self.assertTrue(hf.get("completed"))
        self.assertFalse(self.game.world_manager._check_game_ending_conditions())

    def test_confess_is_no_op_without_precursor(self):
        # Confessing with nothing set up advances nothing and reports no ending.
        self._set("Rodion Raskolnikov")
        advanced = evaluate_player_progression(self.game, "confess")
        self.assertFalse(advanced)
        self.assertFalse(self.game.world_manager._check_game_ending_conditions())

    def test_progression_null_safe_without_player(self):
        self.game.player_character = None
        self.assertFalse(evaluate_player_progression(self.game, "talk_to", "Anyone"))

    def test_talk_handler_drives_progression(self):
        # Proves the handler hook (not just the engine) advances objectives: talking
        # to Sonya as Rodion via the real talk command advances grapple_with_crime.
        self._set("Rodion Raskolnikov", location="Sonya's Room")
        sonya = self._npc("Sonya Marmeladova")
        self.game.npcs_in_current_location = [sonya]
        self.game.all_character_objects = {"Sonya Marmeladova": sonya}
        self.game.gemini_api.model = None  # use placeholder dialogue, no network
        with patch.object(self.game, "_input_color", return_value="Farewell"), \
                patch.object(self.game.world_manager, "advance_time"), \
                patch.object(self.game.event_manager, "check_and_trigger_events",
                             return_value=False), \
                patch("builtins.print"):
            action, _ = self.game._handle_talk_to_command("Sonya")
        self.assertTrue(action)
        self.assertEqual(self._stage("grapple_with_crime"), "seek_sonya")


if __name__ == "__main__":
    unittest.main()
