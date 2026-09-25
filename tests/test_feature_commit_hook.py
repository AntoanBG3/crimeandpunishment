"""Exercise lifecycle feedback against real disposable Git repositories."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[1] / "scripts" / "feature_commit_hook.py"


class TestFeatureCommitHook(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.empty_hooks = self.root / 'empty-hooks'
        self.empty_hooks.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Hook Test")
        self.git("config", "user.email", "hook@example.invalid")
        (self.root / "feature.txt").write_text("original\n", encoding="utf-8")
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        self.git("add", "feature.txt", ".gitignore")
        self.git("-c", f"core.hooksPath={self.empty_hooks}", "commit", "--quiet", "-m", "Initial")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True,
        ).stdout

    def invoke(self, **fields):
        event = {"hook_event_name": "Stop", "cwd": str(self.root), **fields}
        result = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(event),
            text=True, capture_output=True, check=True,
        )
        return json.loads(result.stdout)

    def test_clean_and_ignored_files_allow_stop(self):
        self.assertEqual(self.invoke(), {})
        (self.root / "ignored.txt").write_text("local", encoding="utf-8")
        self.assertEqual(self.invoke(), {})

    def test_modified_staged_and_untracked_changes_request_review_without_mutation(self):
        for state in ("modified", "staged", "untracked"):
            with self.subTest(state=state):
                if state == "modified":
                    (self.root / "feature.txt").write_text("changed\n", encoding="utf-8")
                elif state == "staged":
                    self.git("add", "feature.txt")
                else:
                    self.git("-c", f"core.hooksPath={self.empty_hooks}", "commit", "--quiet", "-m", "Feature")
                    (self.root / "new file.txt").write_text("new\n", encoding="utf-8")
                before = (self.git("status", "--porcelain"), self.git("rev-parse", "HEAD"))
                self.assertEqual(self.invoke()["decision"], "block")
                after = (self.git("status", "--porcelain"), self.git("rev-parse", "HEAD"))
                self.assertEqual(before, after)

    def test_repeat_stop_and_plan_mode_do_not_block(self):
        (self.root / "new.txt").write_text("pending", encoding="utf-8")
        self.assertEqual(self.invoke(stop_hook_active=True), {})
        self.assertEqual(self.invoke(permission_mode="plan"), {})

    def test_session_start_provides_commit_policy(self):
        result = self.invoke(hook_event_name="SessionStart")
        self.assertIn("before starting the next feature", result["hookSpecificOutput"]["additionalContext"])

    def test_subdirectory_works_and_non_repository_warns(self):
        child = self.root / "subdirectory"
        child.mkdir()
        (self.root / "new.txt").write_text("pending", encoding="utf-8")
        self.assertEqual(self.invoke(cwd=str(child))["decision"], "block")
        with tempfile.TemporaryDirectory() as outside:
            result = self.invoke(cwd=outside)
        self.assertIn("systemMessage", result)
        self.assertNotIn("decision", result)

    def test_invalid_payload_returns_json_warning(self):
        result = subprocess.run(
            [sys.executable, str(HOOK)], input="not json", text=True,
            capture_output=True, check=True,
        )
        self.assertIn("systemMessage", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
