"""Subprocess acceptance paths exercise real commands, with isolated runtime files."""

import json
from pathlib import Path
import subprocess
import sys
import unittest


SCENARIOS = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_scenarios.py'


class TestAuditScenarios(unittest.TestCase):
    def run_scenario(self, name, actions=100):
        result = subprocess.run([sys.executable, str(SCENARIOS), '--scenario', name,
                                 '--actions', str(actions)], capture_output=True,
                                text=True, timeout=60, check=True)
        return json.loads(result.stdout)

    def test_three_protagonists_reach_endings_through_commands(self):
        self.assertEqual(self.run_scenario('endings')['endings'], {
            'Rodion Raskolnikov': 'siberia', 'Sonya Marmeladova': 'follow_to_siberia',
            'Porfiry Petrovich': 'case_solved'})

    def test_console_start_play_quit_and_eof(self):
        self.assertEqual(self.run_scenario('console')['exit_code'], 0)

    def test_seeded_engine_with_real_save_roundtrips(self):
        self.assertEqual(self.run_scenario('engine')['actions'], 100)
