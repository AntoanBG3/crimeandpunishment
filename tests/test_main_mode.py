import unittest
from unittest.mock import patch
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import main  # noqa: E402


def _choose(argv=(), env=None, tty=True, textual=True, default="console"):
    with patch.object(main, "DEFAULT_MODE", default), patch.object(
        sys.stdin, "isatty", return_value=tty
    ), patch.object(sys.stdout, "isatty", return_value=tty), patch(
        "main.importlib.util.find_spec", return_value=object() if textual else None
    ):
        return main.choose_mode(argv=["main.py", *argv], environ=env or {})


class TestChooseMode(unittest.TestCase):
    def test_default_is_console_everywhere(self):
        self.assertEqual(_choose(), "console")
        self.assertEqual(_choose(tty=False), "console")
        self.assertEqual(_choose(textual=False), "console")

    def test_explicit_opt_in(self):
        self.assertEqual(_choose(argv=["--tui"]), "tui")
        self.assertEqual(_choose(env={"CRIME_TUI": "1"}), "tui")

    def test_opt_out_wins_over_opt_in(self):
        self.assertEqual(_choose(argv=["--tui", "--no-tui"]), "console")
        self.assertEqual(_choose(argv=["--tui"], env={"CRIME_TUI": "0"}), "console")
        self.assertEqual(_choose(argv=["--no-tui"], env={"CRIME_TUI": "1"}), "console")

    def test_non_tty_always_forces_console(self):
        self.assertEqual(_choose(argv=["--tui"], tty=False), "console")
        self.assertEqual(_choose(env={"CRIME_TUI": "1"}, tty=False), "console")
        self.assertEqual(_choose(argv=["--tui"], tty=False, default="tui"), "console")

    def test_missing_textual_falls_back(self):
        self.assertEqual(_choose(argv=["--tui"], textual=False), "console")

    def test_flipped_default(self):
        # The future one-line flip: TUI when interactive, console otherwise.
        self.assertEqual(_choose(default="tui"), "tui")
        self.assertEqual(_choose(default="tui", tty=False), "console")
        self.assertEqual(_choose(default="tui", textual=False), "console")
        self.assertEqual(_choose(argv=["--no-tui"], default="tui"), "console")


class TestAutoStartFlag(unittest.TestCase):
    """Only --auto-start skips the load prompt and character picker."""

    def launch(self, *argv, mode="console"):
        with patch.object(sys, "argv", ["main.py", *argv]), patch.object(
            main, "choose_mode", return_value=mode
        ), patch("game_engine.game_state.Game") as game_class, patch(
            "game_engine.tui_app.run_tui", return_value=0
        ) as run_tui:
            self.assertEqual(main.main(), 0)
        return game_class, run_tui

    def test_console_keeps_start_menu_by_default(self):
        game_class, _run_tui = self.launch()
        game_class.assert_called_once_with(auto_start=False)
        game_class.return_value.run.assert_called_once_with()

    def test_flag_reaches_console_game(self):
        game_class, _run_tui = self.launch("--auto-start")
        game_class.assert_called_once_with(auto_start=True)

    def test_flag_reaches_tui(self):
        game_class, run_tui = self.launch("--auto-start", mode="tui")
        run_tui.assert_called_once_with(auto_start=True)
        game_class.assert_not_called()


class TestVersionFlag(unittest.TestCase):
    def test_version_prints_and_exits_without_starting_the_game(self):
        import subprocess

        from game_engine.game_config import GAME_VERSION

        result = subprocess.run(
            [sys.executable, os.path.join(project_root, "main.py"), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"Crime and Punishment {GAME_VERSION}", result.stdout)


if __name__ == "__main__":
    unittest.main()
