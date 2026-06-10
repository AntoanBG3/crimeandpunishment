# completion.py
"""Tab completion for the interactive prompt.

The completer is fed by CommandHandler._build_intent_context(), the same
context dict that powers NLP interpretation and tutorial hints: the first
word completes from COMMAND_SYNONYMS (canonical commands and aliases), and
after a recognized verb the argument completes from what is actually in the
scene (NPCs, items, inventory, exits).

The core logic is the pure completion_candidates() function, shared by the
prompt_toolkit GameCompleter (console) and the Textual Input's Tab cycling
(TUI, via terminal.completion_candidates).
"""

from prompt_toolkit.completion import Completer, Completion

from .game_config import COMMAND_SYNONYMS

# Which context pools feed each canonical command's argument.
_ARGUMENT_POOLS = {
    "talk to": ("npcs",),
    "persuade": ("npcs",),
    "give": ("inventory",),
    "take": ("items",),
    "drop": ("inventory",),
    "read": ("inventory", "items"),
    "use": ("inventory",),
    "look": ("items", "npcs"),
    "move to": ("exits",),
}


def _command_words():
    """(word, canonical) pairs, longest word first so prefixes match greedily."""
    pairs = []
    for canonical, aliases in COMMAND_SYNONYMS.items():
        pairs.append((canonical, canonical))
        for alias in aliases:
            if alias and not alias.startswith("/"):
                pairs.append((alias, canonical))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return pairs


def _argument_candidates(context, canonical):
    candidates = []
    for pool_key in _ARGUMENT_POOLS.get(canonical, ()):
        values = context.get(pool_key, [])
        if pool_key == "exits":
            values = [exit_info.get("name", "") for exit_info in values]
        candidates.extend(v for v in values if v)
    return candidates


def completion_candidates(text_before_cursor, context):
    """Completions for the given input as (candidate, start_position) pairs.

    start_position is non-positive, with prompt_toolkit semantics: the
    candidate replaces the last -start_position characters of the input.
    """
    text = text_before_cursor.lstrip().lower()
    words = _command_words()
    # Argument position: text starts with a known command word + space.
    for word, canonical in words:
        if text.startswith(word + " "):
            partial = text[len(word) + 1:]
            return [
                (candidate, -len(partial))
                for candidate in _argument_candidates(context, canonical)
                if candidate.lower().startswith(partial)
            ]
    # Verb position: complete the command word itself.
    if " " in text:
        return []
    results = []
    seen = set()
    for word, _canonical in sorted(words):
        if word.startswith(text) and word not in seen:
            seen.add(word)
            results.append((word, -len(text)))
    return results


class GameCompleter(Completer):
    def __init__(self, context_provider):
        self._context_provider = context_provider

    def _context(self):
        try:
            return self._context_provider()
        except Exception:
            return {}

    def candidates(self, text_before_cursor):
        """(candidate, start_position) pairs; the TUI's Tab cycling uses this."""
        return completion_candidates(text_before_cursor, self._context())

    def get_completions(self, document, complete_event):
        for candidate, start in self.candidates(document.text_before_cursor):
            yield Completion(candidate, start_position=start)
