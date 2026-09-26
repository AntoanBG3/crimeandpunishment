"""Subprocess acceptance paths exercise real commands, with isolated runtime files."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_scenarios


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

    def test_frozen_smoke_accepts_windows_locale_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'main.py').write_text(
                "import sys\n"
                "sys.stdout.buffer.write(b\"Choose Your Character\\nRaskolnikov's Garret\\n"
                "Exiting game. Goodbye.\\nCrime and Punishment 1.2.0\\n\\xb7\\n\")\n",
                encoding='utf-8',
            )
            with patch.object(audit_scenarios, 'ROOT', root):
                self.assertEqual(audit_scenarios.console()['exit_code'], 0)
