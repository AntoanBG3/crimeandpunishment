# completion.py
"""Tab completion for the interactive prompt.

The completer is fed by CommandHandler._build_intent_context(), the same
context dict that powers NLP interpretation and tutorial hints: the first
word completes from COMMAND_SYNONYMS (canonical commands and aliases), and
after a recognized verb the argument completes from what is actually in the
scene (NPCs, items, inventory, exits).
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


class GameCompleter(Completer):
    def __init__(self, context_provider):
        self._context_provider = context_provider
        self._words = _command_words()

    def _argument_candidates(self, canonical):
        try:
            context = self._context_provider()
        except Exception:
            return []
        candidates = []
        for pool_key in _ARGUMENT_POOLS.get(canonical, ()):
            values = context.get(pool_key, [])
            if pool_key == "exits":
                values = [exit_info.get("name", "") for exit_info in values]
            candidates.extend(v for v in values if v)
        return candidates

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip().lower()
        # Argument position: text starts with a known command word + space.
        for word, canonical in self._words:
            if text.startswith(word + " "):
                partial = text[len(word) + 1 :]
                for candidate in self._argument_candidates(canonical):
                    if candidate.lower().startswith(partial):
                        yield Completion(candidate, start_position=-len(partial))
                return
        # Verb position: complete the command word itself.
        if " " in text:
            return
        seen = set()
        for word, _canonical in sorted(self._words):
            if word.startswith(text) and word not in seen:
                seen.add(word)
                yield Completion(word, start_position=-len(text))
