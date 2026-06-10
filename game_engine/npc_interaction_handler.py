# pylint: disable=no-member
import random
import re
from typing import Any
from .game_config import (
    Colors,
    CONCLUDING_PHRASES,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    TIME_UNITS_PER_PLAYER_ACTION,
    HIGHLY_NOTABLE_ITEMS_FOR_MEMORY,
)
from .gemini_interactions import is_usable_ai_text
from .objective_progression import evaluate_player_progression
from .static_fallbacks import STATIC_NPC_PARTING_BEATS

# Neutral filler lines used when the AI is unavailable or returns an unusable
# (empty / OOC) response, so an NPC never "speaks" an out-of-character marker.
_NPC_FALLBACK_LINES = ["Yes?", "Hmm.", "What is it?", "I am busy.", "..."]


class NPCInteractionHandler:
    # Attributes provided by the composing Game class.
    player_character: Any = None
    npcs_in_current_location: list[Any] = []
    game_time: int = 0
    gemini_api: Any = None
    command_handler: Any = None
    event_manager: Any = None
    world_manager: Any = None
    current_location_name: str | None = None
    last_significant_event_summary: str | None = None
    player_notoriety_level: float = 0.0
    current_conversation_log: list[str] = []

    def check_conversation_conclusion(self, text):
        for phrase_regex in CONCLUDING_PHRASES:
            if re.search(phrase_regex, text, re.IGNORECASE):
                return True
        return False

    def _print_parting_beat(self, target_npc):
        beat = random.choice(STATIC_NPC_PARTING_BEATS).format(name=target_npc.name)
        self._print_color(beat, Colors.DIM)

    def _record_npc_post_interaction_memories(self, target_npc, context_str):
        """Records NPC memories of the player's unusual state and notable inventory items after an interaction."""
        unusual_states = [
            "feverish",
            "slightly drunk",
            "paranoid",
            "agitated",
            "dangerously agitated",
            "remorseful",
            "haunted by dreams",
            "injured",
        ]
        current_player_state = self.player_character.apparent_state
        if current_player_state in unusual_states:
            sentiment = -1 if current_player_state in ["dangerously agitated", "paranoid"] else 0
            target_npc.add_player_memory(
                memory_type="observed_player_state",
                turn=self.game_time,
                content={"state": current_player_state, "context": context_str},
                sentiment_impact=sentiment,
            )
        for item_in_inventory in self.player_character.inventory:
            item_name = item_in_inventory.get("name")
            if item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
                sentiment = 0
                if item_name in ["raskolnikov's axe", "bloodied rag"]:
                    sentiment = -1
                elif (
                    item_name == "sonya's cypress cross" and target_npc.name != "Sonya Marmeladova"
                ):
                    if (
                        target_npc.name == "Porfiry Petrovich"
                        and self.player_character.name == "Rodion Raskolnikov"
                    ):
                        sentiment = -1
                target_npc.add_player_memory(
                    memory_type="observed_player_inventory",
                    turn=self.game_time,
                    content={
                        "item_name": item_name,
                        "context": f"player was carrying {context_str}",
                    },
                    sentiment_impact=sentiment,
                )

    def _handle_talk_to_command(self, argument):
        """Handles the 'talk to [npc]' command."""
        if not argument:
            self._print_color("Who do you want to talk to?", Colors.RED)
            return False, False
        if not self.npcs_in_current_location:
            self._print_color("There's no one here to talk to.", Colors.DIM)
            return False, False
        if not self.player_character:
            self._print_color("Cannot talk: Player character not available.", Colors.RED)
            return False, False
        target_name_input = argument.lower()
        target_npc, ambiguous = self.command_handler._get_matching_npc(target_name_input)
        if ambiguous:
            return False, False
        if target_npc:
            if target_npc.name == "Porfiry Petrovich":
                solve_murders_obj = target_npc.get_objective_by_id("solve_murders")
                if solve_murders_obj and solve_murders_obj.get("active"):
                    current_stage_obj = target_npc.get_current_stage_for_objective("solve_murders")
                    if (
                        current_stage_obj
                        and current_stage_obj.get("stage_id") == "encourage_confession"
                    ):
                        new_state = "intensely persuasive"
                        if target_npc.apparent_state != new_state:
                            target_npc.apparent_state = new_state
                            self._print_color(
                                f"({target_npc.name} seems to adopt a new demeanor, his gaze sharpening. He now appears {target_npc.apparent_state}.)",
                                Colors.MAGENTA + Colors.DIM,
                            )
            self.current_conversation_log = []
            MAX_CONVERSATION_LOG_LINES = 20
            self._print_color(
                f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET} (appears {target_npc.apparent_state}).",
                Colors.WHITE,
            )
            if not getattr(self, "_conversation_hint_shown", False):
                self._conversation_hint_shown = True
                self._print_color(
                    "(Speak freely. Say 'goodbye' or 'leave' to end the conversation, "
                    "'history' to review it.)",
                    Colors.DIM,
                )
            greeting = (
                target_npc.get_greeting(self.current_location_name)
                if hasattr(target_npc, "get_greeting")
                else getattr(target_npc, "greeting", None)
            )
            if greeting:
                initial_greeting_text = f'{target_npc.name}: "{greeting}"'
                self._print_dialogue(target_npc.name, f'"{greeting}"')
                self.current_conversation_log.append(initial_greeting_text)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES:
                    self.current_conversation_log.pop(0)
            conversation_active = True
            consecutive_silences = 0
            while conversation_active:
                try:
                    player_dialogue = self._input_color(
                        f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}): {self._prompt_arrow()}",
                        Colors.GREEN,
                        completion=False,  # free-form dialogue, not commands
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    # Ctrl+C/Ctrl+D leaves the conversation, not the game.
                    self._print_color(
                        f"\nYou break off the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.",
                        Colors.WHITE,
                    )
                    self._print_parting_beat(target_npc)
                    break
                if player_dialogue.lower() in ["history", "review", "log"]:
                    from rich.console import Group as RichGroup
                    from rich.panel import Panel
                    from rich.text import Text as RichText

                    if not self.current_conversation_log:
                        lines = [
                            RichText("No history recorded yet for this conversation.", style="dim")
                        ]
                    else:
                        lines = []
                        for line in self.current_conversation_log[-10:]:
                            if line.startswith("You:"):
                                lines.append(RichText(line, style="green"))
                            elif ":" in line:
                                speaker, rest_of_line = line.split(":", 1)
                                styled = RichText(f"{speaker}:", style="yellow")
                                styled.append(rest_of_line)
                                lines.append(styled)
                            else:
                                lines.append(RichText(line, style="dim"))
                    self._print_renderable(
                        Panel(
                            RichGroup(*lines),
                            title="Recent Conversation",
                            border_style="dim",
                            expand=False,
                        )
                    )
                    continue
                if not player_dialogue:
                    # Empty input costs no turn and produces no NPC reply; a
                    # second consecutive silence ends the conversation.
                    consecutive_silences += 1
                    if consecutive_silences >= 2:
                        self._print_color(
                            f"Having nothing more to say, you take your leave of {Colors.YELLOW}{target_npc.name}{Colors.RESET}.",
                            Colors.WHITE,
                        )
                        self._print_parting_beat(target_npc)
                        break
                    self._print_color(
                        "You remain silent for a moment. (Press Enter again to take your leave.)",
                        Colors.DIM,
                    )
                    continue
                consecutive_silences = 0
                logged_player_dialogue = f"You: {player_dialogue}"
                self.current_conversation_log.append(logged_player_dialogue)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES:
                    self.current_conversation_log.pop(0)
                if self.check_conversation_conclusion(player_dialogue):
                    self._print_color(
                        f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.",
                        Colors.WHITE,
                    )
                    self._print_parting_beat(target_npc)
                    conversation_active = False
                    break
                used_ai_dialogue = False
                if self.gemini_api.model:
                    ai_response = self.gemini_api.get_npc_dialogue(
                        target_npc,
                        self.player_character,
                        player_dialogue,
                        self.current_location_name,
                        self.world_manager.get_current_time_period(),
                        self.get_relationship_text(target_npc.relationship_with_player),
                        target_npc.get_player_memory_summary(self.game_time),
                        self.player_character.apparent_state,
                        self.player_character.get_notable_carried_items_summary(),
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(target_npc),
                        self._get_objectives_summary(self.player_character),
                    )
                    used_ai_dialogue = True
                else:
                    ai_response = random.choice(
                        _NPC_FALLBACK_LINES[:-1]
                        + [getattr(target_npc, "greeting", "...")]
                    )
                    self._print_color(
                        f"{Colors.DIM}(Using placeholder dialogue){Colors.RESET}",
                        Colors.DIM,
                    )
                if used_ai_dialogue and not is_usable_ai_text(ai_response):
                    # AI returned nothing usable or an OOC marker; substitute a neutral
                    # static line so the NPC never speaks OOC text verbatim.
                    ai_response = random.choice(_NPC_FALLBACK_LINES)
                    used_ai_dialogue = False
                # NPC dialogue is never hard-trimmed: verbosity steers the AI's
                # length instruction instead (response_length_pref), so a long
                # reply prints whole rather than cut off with [...more].
                target_npc.update_relationship(
                    player_dialogue,
                    POSITIVE_KEYWORDS,
                    NEGATIVE_KEYWORDS,
                    self.game_time,
                )
                self._print_dialogue(target_npc.name, f'"{ai_response}"')
                logged_ai_response = f'{target_npc.name}: "{ai_response}"'
                self.current_conversation_log.append(logged_ai_response)
                if used_ai_dialogue:
                    self._remember_ai_output(ai_response, "npc_dialogue")
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES:
                    self.current_conversation_log.pop(0)
                self.last_significant_event_summary = (
                    f'spoke with {target_npc.name} who said: "{ai_response[:50]}..."'
                )
                if self.check_conversation_conclusion(ai_response):
                    self._print_color(
                        f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.",
                        Colors.MAGENTA,
                    )
                    conversation_active = False
                self.world_manager.advance_time(TIME_UNITS_PER_PLAYER_ACTION)
                if self.event_manager.check_and_trigger_events():
                    self.last_significant_event_summary = "an event occurred during conversation."
                # Each exchange advances time, so the NPC's schedule may move
                # them away mid-conversation; don't keep talking to the absent.
                if conversation_active and target_npc not in self.npcs_in_current_location:
                    self._print_color(
                        f"\n{Colors.YELLOW}{target_npc.name}{Colors.RESET} has gone on their way; the conversation is over.",
                        Colors.MAGENTA,
                    )
                    conversation_active = False
            self._record_npc_post_interaction_memories(target_npc, "during conversation")
            if (
                self.player_character.name == "Rodion Raskolnikov"
                and target_npc
                and target_npc.name == "Porfiry Petrovich"
            ):
                self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.15))
                self._print_color(
                    "(Your conversation with Porfiry seems to have drawn some attention...)",
                    Colors.YELLOW + Colors.DIM,
                )
            evaluate_player_progression(self, "talk_to", target_npc.name)
            return True, True
        self._print_color(f"You don't see anyone named '{target_name_input}' here.", Colors.RED)
        return False, False

    def _handle_persuade_command(self, argument):
        if not argument or not isinstance(argument, tuple) or len(argument) != 2:
            self._print_color(
                "How do you want to persuade them? Use: persuade [person] that/to [your argument]",
                Colors.RED,
            )
            return False, False
        target_npc_name, statement_text = argument
        if not self.player_character:
            self._print_color("Cannot persuade: Player character not available.", Colors.RED)
            return False, False
        target_npc = next(
            (
                npc
                for npc in self.npcs_in_current_location
                if npc.name.lower().startswith(target_npc_name.lower())
            ),
            None,
        )
        if not target_npc:
            self._print_color(
                f"You don't see anyone named '{target_npc_name}' here to persuade.",
                Colors.RED,
            )
            return False, False
        self._print_color(
            f'\nYou attempt to persuade {Colors.YELLOW}{target_npc.name}{Colors.RESET} that "{statement_text}"...',
            Colors.WHITE,
        )
        difficulty = 2
        success = self.player_character.check_skill("Persuasion", difficulty)
        persuasion_skill_check_result_text = (
            "SUCCESS due to their skillful argument" if success else "FAILURE despite their efforts"
        )
        _persuade_fallback = (
            f"Hmm, '{statement_text}', you say? That's... something to consider. "
            f"(Skill: {persuasion_skill_check_result_text})"
        )
        used_ai_dialogue = False
        if self.gemini_api.model:
            ai_response = self.gemini_api.get_npc_dialogue_persuasion_attempt(
                target_npc,
                self.player_character,
                player_persuasive_statement=statement_text,
                current_location_name=self.current_location_name,
                current_time_period=self.world_manager.get_current_time_period(),
                relationship_status_text=self.get_relationship_text(
                    target_npc.relationship_with_player
                ),
                npc_memory_summary=target_npc.get_player_memory_summary(self.game_time),
                player_apparent_state=self.player_character.apparent_state,
                player_notable_items_summary=self.player_character.get_notable_carried_items_summary(),
                recent_game_events_summary=self._get_recent_events_summary(),
                npc_objectives_summary=self._get_objectives_summary(target_npc),
                player_objectives_summary=self._get_objectives_summary(self.player_character),
                persuasion_skill_check_result_text=persuasion_skill_check_result_text,
            )
            used_ai_dialogue = True
        else:
            ai_response = _persuade_fallback
            self._print_color(
                f"{Colors.DIM}(Using placeholder dialogue for persuasion){Colors.RESET}",
                Colors.DIM,
            )
        if used_ai_dialogue and not is_usable_ai_text(ai_response):
            # AI returned nothing usable or an OOC marker; fall back to the same
            # static line the no-model path uses rather than speaking OOC text.
            ai_response = _persuade_fallback
            used_ai_dialogue = False
        # Dialogue is steered by the AI length instruction, never hard-trimmed.
        self._print_dialogue(target_npc.name, f'"{ai_response}"')
        if used_ai_dialogue:
            self._remember_ai_output(ai_response, "persuasion_dialogue")
        sentiment_impact_base = 0
        if success:
            self._print_color("Your argument seems to have had an effect!", Colors.GREEN)
            sentiment_impact_base = 1
            target_npc.relationship_with_player += 1
        else:
            self._print_color(f"Your words don't seem to convince {target_npc.name}.", Colors.RED)
            sentiment_impact_base = -1
            target_npc.relationship_with_player -= 1
        target_npc.add_player_memory(
            memory_type="persuasion_attempt",
            turn=self.game_time,
            content={
                "statement": statement_text[:100],
                "outcome": "success" if success else "failure",
                "npc_response_snippet": ai_response[:70],
            },
            sentiment_impact=sentiment_impact_base,
        )
        self.last_significant_event_summary = (
            f"attempted to persuade {target_npc.name} regarding '{statement_text[:30]}...'."
        )
        self._record_npc_post_interaction_memories(target_npc, "during persuasion attempt")
        evaluate_player_progression(self, "persuade", target_npc.name)
        self.world_manager.advance_time(TIME_UNITS_PER_PLAYER_ACTION)
        return True, True

    def _handle_confess_command(self, argument=None):
        """The deliberate capstone act that drives a protagonist's story to its ending.

        Context-sensitive: for Raskolnikov it is a confession, for Sonya the resolve
        to follow him, for Porfiry the moment he secures the confession. The specific
        narration and which ending is reached are decided by the progression rules.
        """
        if not self.player_character:
            self._print_color("Cannot do that: no character.", Colors.RED)
            return False, False
        if evaluate_player_progression(self, "confess"):
            return True, True
        self._print_color(
            "You steel yourself, but this is not the moment, nor the place, for it.",
            Colors.YELLOW,
        )
        return False, False
