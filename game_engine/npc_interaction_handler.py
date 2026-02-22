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
            should_print_static_greeting = True
            # Removed specific condition for Raskolnikov and Razumikhin
            if (
                should_print_static_greeting
                and hasattr(target_npc, "greeting")
                and target_npc.greeting
            ):
                initial_greeting_text = f'{target_npc.name}: "{target_npc.greeting}"'
                self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                print(f'"{target_npc.greeting}"')
                self.current_conversation_log.append(initial_greeting_text)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES:
                    self.current_conversation_log.pop(0)
            conversation_active = True
            while conversation_active:
                player_dialogue = self._input_color(
                    f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}): {self._prompt_arrow()}",
                    Colors.GREEN,
                ).strip()
                if player_dialogue.lower() in ["history", "review", "log"]:
                    self._print_color(
                        "\n--- Recent Conversation History ---",
                        Colors.CYAN + Colors.BOLD,
                    )
                    if not self.current_conversation_log:
                        self._print_color(
                            "No history recorded yet for this conversation.", Colors.DIM
                        )
                    else:
                        history_to_show = self.current_conversation_log[-10:]
                        for line in history_to_show:
                            if line.startswith("You:"):
                                self._print_color(line, Colors.GREEN)
                            elif ":" in line:
                                speaker, rest_of_line = line.split(":", 1)
                                self._print_color(f"{speaker}:", Colors.YELLOW, end="")
                                print(rest_of_line)
                            else:
                                self._print_color(line, Colors.DIM)
                    self._print_color("--- End of History ---", Colors.CYAN + Colors.BOLD)
                    continue
                logged_player_dialogue = f"You: {player_dialogue}"
                self.current_conversation_log.append(logged_player_dialogue)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES:
                    self.current_conversation_log.pop(0)
                if self.check_conversation_conclusion(player_dialogue):
                    self._print_color(
                        f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.",
                        Colors.WHITE,
                    )
                    conversation_active = False
                    break
                if not player_dialogue:
                    self._print_color("You remain silent for a moment.", Colors.DIM)
                    pass
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
                        [
                            "Yes?",
                            "Hmm.",
                            "What is it?",
                            "I am busy.",
                            f"{target_npc.greeting if hasattr(target_npc, 'greeting') else '...'}",
                        ]
                    )
                    self._print_color(
                        f"{Colors.DIM}(Using placeholder dialogue){Colors.RESET}",
                        Colors.DIM,
                    )
                ai_response = self._apply_verbosity(ai_response)
                target_npc.update_relationship(
                    player_dialogue,
                    POSITIVE_KEYWORDS,
                    NEGATIVE_KEYWORDS,
                    self.game_time,
                )
                self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                print(f'"{ai_response}"')
                logged_ai_response = f'{target_npc.name}: "{ai_response}"'
                self.current_conversation_log.append(logged_ai_response)
                if used_ai_dialogue and not (
                    isinstance(ai_response, str) and ai_response.startswith("(OOC:")
                ):
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
            ai_response = f"Hmm, '{statement_text}', you say? That's... something to consider. (Skill: {persuasion_skill_check_result_text})"
            self._print_color(
                f"{Colors.DIM}(Using placeholder dialogue for persuasion){Colors.RESET}",
                Colors.DIM,
            )
        ai_response = self._apply_verbosity(ai_response)
        self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
        print(f'"{ai_response}"')
        if used_ai_dialogue and not (
            isinstance(ai_response, str) and ai_response.startswith("(OOC:")
        ):
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
        self.world_manager.advance_time(TIME_UNITS_PER_PLAYER_ACTION)
        return True, True
