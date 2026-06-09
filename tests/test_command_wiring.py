"""Guards against command layers drifting apart.

The 'look at' and 'journal' bugs both came from command knowledge living in
several places (COMMAND_SYNONYMS, the _process_command dispatch, help text)
with nothing enforcing agreement. This test parses the dispatch with ast and
asserts the sets match, so a command can't be added to one layer and not the
other.
"""

import ast
import inspect
import unittest

from game_engine import command_handler
from game_engine.game_config import COMMAND_SYNONYMS

# Commands that are dispatched but intentionally not typeable words.
INTERNAL_COMMANDS = {"select_item"}


def _dispatched_command_literals():
    source = inspect.getsource(command_handler.CommandHandler._process_command)
    tree = ast.parse("class _W:\n" + source.replace("\n", "\n    "))
    literals = set()

    class Visitor(ast.NodeVisitor):
        def visit_Compare(self, node):
            is_command_compare = (
                isinstance(node.left, ast.Name) and node.left.id == "command"
            )
            if is_command_compare:
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(
                        comparator.value, str
                    ):
                        literals.add(comparator.value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return literals


class TestCommandWiring(unittest.TestCase):
    def test_every_synonym_key_is_dispatched(self):
        dispatched = _dispatched_command_literals()
        missing = set(COMMAND_SYNONYMS) - dispatched
        self.assertFalse(
            missing,
            f"COMMAND_SYNONYMS entries with no _process_command branch: {sorted(missing)}",
        )

    def test_every_dispatch_branch_has_a_synonym_entry(self):
        dispatched = _dispatched_command_literals()
        unknown = dispatched - set(COMMAND_SYNONYMS) - INTERNAL_COMMANDS
        self.assertFalse(
            unknown,
            f"_process_command branches unreachable by typing (no COMMAND_SYNONYMS entry): {sorted(unknown)}",
        )

    def test_known_command_check_matches_synonyms(self):
        from types import SimpleNamespace

        handler = command_handler.CommandHandler(SimpleNamespace())
        for command in COMMAND_SYNONYMS:
            self.assertTrue(handler._is_known_command(command), command)


if __name__ == "__main__":
    unittest.main()
