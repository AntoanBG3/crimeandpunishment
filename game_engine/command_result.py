"""Named turn outcomes with a tuple-compatible migration boundary."""

from enum import Enum
from typing import NamedTuple


class TurnOutcome(Enum):
    CONTINUE = "continue"
    LOADED = "loaded"
    QUIT = "quit"


class CommandResult(NamedTuple):
    """Keep legacy unpacking while the main loop consumes explicit outcomes."""

    action_taken: bool
    show_atmospherics: bool
    time_to_advance: int
    special_flag: bool | str = False

    @property
    def outcome(self):
        if self.special_flag == "load_triggered":
            return TurnOutcome.LOADED
        if self.special_flag:
            return TurnOutcome.QUIT
        return TurnOutcome.CONTINUE
