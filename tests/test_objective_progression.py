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

    def test_only_successful_persuasion_advances(self):
        # A failed Persuasion check is narrated as a failure and leaves the stage
        # for a retry; only a success tightens the net.
        self._set("Porfiry Petrovich", [self._npc("Rodion Raskolnikov")], "Raskolnikov's Garret")
        self.game.gemini_api.model = None  # use placeholder dialogue, no network
        pc = self.game.player_character
        with patch.object(self.game, "_print_narrative") as narrative, \
                patch.object(self.game, "_print_dialogue"):
            evaluate_player_progression(self.game, "talk_to", "Rodion Raskolnikov")
            self.assertEqual(self._stage("solve_murders"), "psychological_probes")
            narrative.reset_mock()
            with patch.object(pc, "check_skill", return_value=False):
                result = self.game._handle_persuade_command(("Rodion", "confession will help"))
            self.assertEqual(result, (True, True))
            self.assertEqual(self._stage("solve_murders"), "psychological_probes")
            narrative.assert_not_called()
            printed = " ".join(str(call.args[0]) for call in self.mock_print.call_args_list)
            self.assertIn("Your words don't seem to convince Rodion Raskolnikov", printed)
            with patch.object(pc, "check_skill", return_value=True):
                self.game._handle_persuade_command(("Rodion", "confession will help"))
        self.assertEqual(self._stage("solve_murders"), "closing_the_net")
        self.assertIn("The net draws tighter", narrative.call_args.args[0])


class TestSonyaCrossBeat(unittest.TestCase):
    """Sonya's arc turns on giving her cross, and NPCs never hand items back."""

    CROSS = "sonya's cypress cross"

    def setUp(self):
        self.game = Game()
        self.game.low_ai_data_mode = True
        self.game.gemini_api.model = None
        self.mock_print = patch.object(self.game, "_print_color").start()
        self.mock_narrative = patch.object(self.game, "_print_narrative").start()
        self.sonya = build_player("Sonya Marmeladova")
        self.rodion = Character("Rodion Raskolnikov", "", "", "Sonya's Room", ["Sonya's Room"])
        self.katerina = Character(
            "Katerina Ivanovna Marmeladova", "", "", "Sonya's Room", ["Sonya's Room"]
        )
        self.game.player_character = self.sonya
        self.game.current_location_name = "Sonya's Room"
        self.game.npcs_in_current_location = [self.rodion, self.katerina]

    def tearDown(self):
        patch.stopall()

    def _stage(self):
        return self.sonya.get_current_stage_for_objective("guide_raskolnikov")["stage_id"]

    def _give_cross(self, target):
        handler = self.game.command_handler
        command, argument = handler.parse_action(f"give {self.CROSS} to {target}")
        return handler._process_command(command, argument)

    def _printed(self):
        return " ".join(str(call.args[0]) for call in self.mock_print.call_args_list)

    def _talk_to_rodion(self):
        evaluate_player_progression(self.game, "talk_to", "Rodion Raskolnikov")

    def test_early_gift_is_refused_and_costs_no_turn(self):
        for expected_stage in ("initial_encounter", "lazarus_reading"):
            self.assertEqual(self._stage(), expected_stage)
            result = self._give_cross("Rodion")
            self.assertFalse(result.action_taken)
            self.assertTrue(self.sonya.has_item(self.CROSS))
            self.assertFalse(self.rodion.has_item(self.CROSS))
            self.assertIn("not ready to receive it", self._printed())
            self._talk_to_rodion()
        self.assertEqual(self._stage(), "offer_cross")
        self.assertTrue(self._give_cross("Rodion").action_taken)
        self.assertEqual(self._stage(), "receive_confession")
        self.assertFalse(self.sonya.has_item(self.CROSS))
        self.assertTrue(self.rodion.has_item(self.CROSS))

    def test_cross_is_refused_to_anyone_but_rodion(self):
        self._talk_to_rodion()
        self._talk_to_rodion()
        self.assertEqual(self._stage(), "offer_cross")
        self.assertFalse(self._give_cross("Katerina").action_taken)
        self.assertTrue(self.sonya.has_item(self.CROSS))
        self.assertFalse(self.katerina.has_item(self.CROSS))
        self.assertIn("meant for one who must bear a heavier cross", self._printed())
        self.assertEqual(self._stage(), "offer_cross")

    def test_talk_at_offer_cross_still_needs_the_gift(self):
        self._talk_to_rodion()
        self._talk_to_rodion()
        self._talk_to_rodion()
        self.assertEqual(self._stage(), "offer_cross")

    def test_cross_already_with_rodion_no_longer_strands_her(self):
        # State left by the pre-fix early gift (e.g. in an old save): Rodion holds
        # the cross, and two talks bring Sonya to offer_cross with nothing to give.
        self.sonya.remove_from_inventory(self.CROSS)
        self.rodion.add_to_inventory(self.CROSS)
        self._talk_to_rodion()
        self._talk_to_rodion()
        self.assertEqual(self._stage(), "offer_cross")
        self._talk_to_rodion()
        self.assertEqual(self._stage(), "receive_confession")
        narration = " ".join(str(call.args[0]) for call in self.mock_narrative.call_args_list)
        self.assertIn("He still carries the cypress cross", narration)
        self.assertTrue(evaluate_player_progression(self.game, "confess"))
        self.assertEqual(self._stage(), "follow_to_siberia")
        self.assertTrue(self.game.world_manager._check_game_ending_conditions())


if __name__ == "__main__":
    unittest.main()
