import random
from typing import Any
from .game_config import (
    Colors,
    DEFAULT_ITEMS,
    GENERIC_SCENERY_KEYWORDS,
    STATIC_ENHANCED_OBSERVATIONS,
    STATIC_PLAYER_REFLECTIONS,
    HIGHLY_NOTABLE_ITEMS_FOR_MEMORY,
    STATIC_NEWSPAPER_SNIPPETS,
    generate_static_item_interaction_description,
    generate_static_scenery_observation,
)
from .location_module import LOCATIONS_DATA


class ItemInteractionHandler:
    """Handle item and scenery inspection interactions for the active game session."""

    # Attributes provided by the composing Game class.
    player_character: Any = None
    current_location_name: str | None = None
    gemini_api: Any = None
    low_ai_data_mode: bool = False
    command_handler: Any = None
    npcs_in_current_location: list[Any] = []
    game_time: int = 0

    def _inspect_item(
        self,
        item_name,
        item_default,
        action_context,
        observation_context,
        allow_npc_memory,
    ):
        if not self.player_character:
            self._print_color(
                "Cannot inspect item: Player character not available.", Colors.RED
            )
            return
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        self._print_color(f"You examine the {item_name}:", Colors.GREEN)
        gen_desc = None
        base_desc_for_skill_check = item_default.get("description", "An ordinary item.")

        if not self.low_ai_data_mode and self.gemini_api.model:
            gen_desc = self.gemini_api.get_item_interaction_description(
                player_character,
                item_name,
                item_default,
                action_context,
                current_location_name,
                self.get_current_time_period(),
            )

        if (
            gen_desc is not None
            and not (isinstance(gen_desc, str) and gen_desc.startswith("(OOC:"))
            and not self.low_ai_data_mode
        ):
            gen_desc = self._apply_verbosity(gen_desc)
            self._print_color(f'"{gen_desc}"', Colors.GREEN)
            base_desc_for_skill_check = gen_desc
            self._remember_ai_output(gen_desc, "item_inspection")
        else:
            if (
                self.low_ai_data_mode
                or gen_desc is None
                or (isinstance(gen_desc, str) and gen_desc.startswith("(OOC:"))
            ):
                gen_desc = generate_static_item_interaction_description(
                    item_name, "examine"
                )
                self._print_color(f'"{self._apply_verbosity(gen_desc)}"', Colors.CYAN)
            else:
                self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

        self._display_item_properties(item_default)

        if player_character.check_skill("Observation", 1):
            self._print_color(
                "(Your keen eye picks up on finer details...)", Colors.CYAN + Colors.DIM
            )
            detailed_observation = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                detailed_observation = self.gemini_api.get_enhanced_observation(
                    player_character,
                    target_name=item_name,
                    target_category="item",
                    base_description=base_desc_for_skill_check,
                    skill_check_context=observation_context,
                )

            if (
                detailed_observation is None
                or (
                    isinstance(detailed_observation, str)
                    and detailed_observation.startswith("(OOC:")
                )
                or self.low_ai_data_mode
            ):
                if STATIC_ENHANCED_OBSERVATIONS:
                    detailed_observation = random.choice(STATIC_ENHANCED_OBSERVATIONS)
                else:
                    detailed_observation = (
                        "You notice a few more mundane details, but nothing striking."
                    )
                if detailed_observation:
                    self._print_color(
                        f'Detail: "{self._apply_verbosity(detailed_observation)}"',
                        Colors.CYAN,
                    )
            elif detailed_observation:
                final_detail = self._apply_verbosity(detailed_observation)
                self._print_color(f'Detail: "{final_detail}"', Colors.GREEN)
                self._remember_ai_output(final_detail, "item_detail")

        if allow_npc_memory and item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
            for npc_observer in self.npcs_in_current_location:
                if npc_observer.name != player_character.name:
                    sentiment_impact = (
                        -2 if item_name in ["raskolnikov's axe", "bloodied rag"] else -1
                    )
                    npc_observer.add_player_memory(
                        memory_type="player_action_observed",
                        turn=self.game_time,
                        content={
                            "action": "examined_item",
                            "item_name": item_name,
                            "location": current_location_name,
                        },
                        sentiment_impact=sentiment_impact,
                    )

    def _handle_look_at_location_item(self, target_to_look_at):
        if not self.player_character:
            self._print_color(
                "Cannot inspect location items: Player character not available.",
                Colors.RED,
            )
            return True
        player_character = self.player_character
        item_info, ambiguous = self.command_handler._get_matching_location_item(
            target_to_look_at
        )
        if ambiguous:
            return True
        if item_info:
            item_default = DEFAULT_ITEMS.get(item_info["name"])
            if item_default:
                observation_context = (
                    f"Player ({player_character.name}) succeeded an Observation skill check examining the "
                    f"{item_info['name']} in {self.current_location_name}. What subtle detail, past use, hidden "
                    f"inscription, or unusual characteristic do they notice that isn't immediately obvious?"
                )
                self._inspect_item(
                    item_info["name"],
                    item_default,
                    "examine closely in environment",
                    observation_context,
                    allow_npc_memory=True,
                )
                return True
        return False

    def _handle_look_at_inventory_item(self, target_to_look_at):
        if self.player_character:
            inv_item_info, ambiguous = (
                self.command_handler._get_matching_inventory_item(target_to_look_at)
            )
            if ambiguous:
                return True
            if inv_item_info:
                item_default = DEFAULT_ITEMS.get(inv_item_info["name"])
                if item_default:
                    observation_context = (
                        f"Player ({self.player_character.name}) succeeded an Observation skill check examining their "
                        f"{inv_item_info['name']}. What subtle detail, past use, hidden inscription, or unusual "
                        f"characteristic do they notice that isn't immediately obvious?"
                    )
                    self._inspect_item(
                        inv_item_info["name"],
                        item_default,
                        "examine closely from inventory",
                        observation_context,
                        allow_npc_memory=True,
                    )
                    return True
        return False

    def _handle_look_at_npc(self, target_to_look_at):
        if not self.player_character:
            self._print_color(
                "Cannot inspect people: Player character not available.", Colors.RED
            )
            return True
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        npc, ambiguous = self.command_handler._get_matching_npc(target_to_look_at)
        if ambiguous:
            return True
        if npc:
            self._print_color(
                f"You look closely at {Colors.YELLOW}{npc.name}{Colors.RESET} (appears {npc.apparent_state}):",
                Colors.WHITE,
            )
            base_desc_for_skill_check = (
                npc.persona[:100] if npc.persona else f"{npc.name} is present."
            )  # Initialize base_desc
            observation = None

            if not self.low_ai_data_mode and self.gemini_api.model:
                observation_prompt = f"observing {npc.name} in {current_location_name}. They appear to be '{npc.apparent_state}'. You recall: {npc.get_player_memory_summary(self.game_time)}"
                observation = self.gemini_api.get_player_reflection(
                    player_character,
                    current_location_name,
                    self.get_current_time_period(),
                    observation_prompt,
                    player_character.get_inventory_description(),
                    self._get_objectives_summary(player_character),
                )

            if (
                observation is not None
                and not (
                    isinstance(observation, str) and observation.startswith("(OOC:")
                )
                and not self.low_ai_data_mode
            ):
                final_observation = self._apply_verbosity(observation)
                self._print_color(f'"{final_observation}"', Colors.GREEN)
                base_desc_for_skill_check = final_observation
                self._remember_ai_output(final_observation, "look_npc")
            else:
                if (
                    self.low_ai_data_mode
                    or observation is None
                    or (
                        isinstance(observation, str) and observation.startswith("(OOC:")
                    )
                ):
                    if STATIC_PLAYER_REFLECTIONS:
                        observation = f"{npc.name} is here. {random.choice(STATIC_PLAYER_REFLECTIONS)}"
                    else:
                        observation = f"You observe {npc.name}. They seem to be going about their business."
                    self._print_color(
                        f'"{self._apply_verbosity(observation)}"', Colors.CYAN
                    )
                else:
                    self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

            if player_character.check_skill("Observation", 1):
                self._print_color(
                    "(Your keen observation notices something more...)",
                    Colors.CYAN + Colors.DIM,
                )
                observation_context = (
                    f"Player ({player_character.name}) succeeded an Observation skill check while looking at "
                    f"{npc.name} (appears {npc.apparent_state}). What subtle, non-obvious detail does "
                    f"{player_character.name} notice about {npc.name}'s demeanor, clothing, a hidden object, "
                    f"or a subtle emotional cue? This should be something beyond the obvious, a deeper insight."
                )
                detailed_observation = None
                if not self.low_ai_data_mode and self.gemini_api.model:
                    detailed_observation = self.gemini_api.get_enhanced_observation(
                        player_character,
                        target_name=npc.name,
                        target_category="person",
                        base_description=base_desc_for_skill_check,
                        skill_check_context=observation_context,
                    )

                if (
                    detailed_observation is None
                    or (
                        isinstance(detailed_observation, str)
                        and detailed_observation.startswith("(OOC:")
                    )
                    or self.low_ai_data_mode
                ):
                    if STATIC_ENHANCED_OBSERVATIONS:
                        detailed_observation = random.choice(
                            STATIC_ENHANCED_OBSERVATIONS
                        )
                    else:
                        detailed_observation = "You notice some subtle cues, but their full meaning eludes you."
                    if detailed_observation:
                        self._print_color(
                            f'Insight: "{self._apply_verbosity(detailed_observation)}"',
                            Colors.CYAN,
                        )
                elif detailed_observation:
                    final_detail = self._apply_verbosity(detailed_observation)
                    self._print_color(f'Insight: "{final_detail}"', Colors.GREEN)
                    self._remember_ai_output(final_detail, "look_npc_detail")
            return True
        return False

    def _handle_look_at_scenery(self, target_to_look_at):
        if not self.player_character:
            self._print_color(
                "Cannot inspect scenery: Player character not available.", Colors.RED
            )
            return True
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        loc_data = LOCATIONS_DATA.get(self.current_location_name, {})
        loc_desc_lower = loc_data.get("description", "").lower()
        is_scenery = (
            any(keyword in target_to_look_at for keyword in GENERIC_SCENERY_KEYWORDS)
            or target_to_look_at in loc_desc_lower
        )
        if is_scenery:
            self._print_color(f"You focus on the {target_to_look_at}...", Colors.WHITE)
            base_desc_for_skill_check = f"The general scenery of {current_location_name}, focusing on {target_to_look_at}."  # Initial base
            observation = None

            if not self.low_ai_data_mode and self.gemini_api.model:
                observation = self.gemini_api.get_scenery_observation(
                    player_character,
                    target_to_look_at,
                    current_location_name,
                    self.get_current_time_period(),
                    self._get_objectives_summary(player_character),
                )

            if (
                observation is not None
                and not (
                    isinstance(observation, str) and observation.startswith("(OOC:")
                )
                and not self.low_ai_data_mode
            ):
                # AI success
                final_observation = self._apply_verbosity(observation)
                self._print_color(f'"{final_observation}"', Colors.CYAN)
                base_desc_for_skill_check = final_observation  # Update for skill check
                self._remember_ai_output(final_observation, "look_scenery")
            else:
                # Fallback or AI failed/OOC or low_ai_mode
                if (
                    self.low_ai_data_mode
                    or observation is None
                    or (
                        isinstance(observation, str) and observation.startswith("(OOC:")
                    )
                ):
                    observation = generate_static_scenery_observation(target_to_look_at)
                    # base_desc_for_skill_check remains the initial general one
                    self._print_color(
                        f'"{self._apply_verbosity(observation)}"', Colors.DIM
                    )  # Static in DIM
                else:  # Should not be reached
                    self._print_color(
                        f"The {target_to_look_at} is just as it seems.", Colors.DIM
                    )

            if player_character.check_skill("Observation", 0):
                self._print_color(
                    "(You scan the area more intently...)", Colors.CYAN + Colors.DIM
                )
                observation_context = f"Player ({player_character.name}) passed an Observation check while looking at '{target_to_look_at}' in {current_location_name}. What specific, easily missed detail about '{target_to_look_at}' or its immediate surroundings catches their eye, perhaps hinting at a past event, a hidden element, or the general atmosphere in a more profound way?"
                detailed_observation = None
                if not self.low_ai_data_mode and self.gemini_api.model:
                    detailed_observation = self.gemini_api.get_enhanced_observation(
                        player_character,
                        target_name=target_to_look_at,
                        target_category="scenery",
                        base_description=base_desc_for_skill_check,
                        skill_check_context=observation_context,
                    )

                if (
                    detailed_observation is None
                    or (
                        isinstance(detailed_observation, str)
                        and detailed_observation.startswith("(OOC:")
                    )
                    or self.low_ai_data_mode
                ):
                    if STATIC_ENHANCED_OBSERVATIONS:
                        detailed_observation = random.choice(
                            STATIC_ENHANCED_OBSERVATIONS
                        )
                    else:
                        detailed_observation = "The scene offers no further secrets to your gaze."  # Ultimate fallback
                    if detailed_observation:  # Check if not None
                        self._print_color(
                            f'You also notice: "{self._apply_verbosity(detailed_observation)}"',
                            Colors.CYAN,
                        )  # Static in Cyan
                elif detailed_observation:  # AI success
                    final_detail = self._apply_verbosity(detailed_observation)
                    self._print_color(
                        f'You also notice: "{final_detail}"', Colors.GREEN
                    )
                    self._remember_ai_output(final_detail, "look_scenery_detail")
                # If still None, nothing printed.
            return True
        return False

    def _handle_look_command(self, argument, show_full_look_details=False):
        self.numbered_actions_context.clear()
        action_number = 1
        current_location_data = LOCATIONS_DATA.get(self.current_location_name)
        is_general_look = argument is None or argument.lower() in ["around", ""]
        self.world_manager.update_current_location_details(
            from_explicit_look_cmd=is_general_look
        )

        if argument and not is_general_look:
            target_to_look_at = argument.lower()
            if self._handle_look_at_location_item(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_inventory_item(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_npc(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_scenery(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            else:
                self._print_color(
                    f"You don't see '{argument}' here to look at specifically.",
                    Colors.RED,
                )
                self._print_color(self._separator_line(), Colors.DIM)

        if show_full_look_details:
            self._print_color("", Colors.RESET)
            self._print_color("--- People Here ---", Colors.YELLOW + Colors.BOLD)
            npcs_present_for_hint = False
            if self.npcs_in_current_location:
                for npc in self.npcs_in_current_location:
                    look_at_npc_display = f"Look at {npc.name}"
                    self.numbered_actions_context.append(
                        {
                            "type": "look_at_npc",
                            "target": npc.name,
                            "display": look_at_npc_display,
                        }
                    )
                    self._print_color(
                        f"{action_number}. {look_at_npc_display}", Colors.YELLOW, end=""
                    )
                    print(
                        f" (Appears: {npc.apparent_state}, Relationship: {self.get_relationship_text(npc.relationship_with_player)})"
                    )
                    action_number += 1
                    npcs_present_for_hint = True
                    talk_to_npc_display = f"Talk to {npc.name}"
                    self.numbered_actions_context.append(
                        {
                            "type": "talk",
                            "target": npc.name,
                            "display": talk_to_npc_display,
                        }
                    )
                    self._print_color(
                        f"{action_number}. {talk_to_npc_display}", Colors.YELLOW
                    )
                    action_number += 1
            else:
                self._print_color("You see no one else of note here.", Colors.DIM)
            self._print_color("", Colors.RESET)
            self._print_color("--- Items Here ---", Colors.YELLOW + Colors.BOLD)
            current_loc_items = self.dynamic_location_items.get(
                self.current_location_name, []
            )
            items_present_for_hint = False
            if current_loc_items:
                for item_info in current_loc_items:
                    item_name = item_info["name"]
                    item_qty = item_info.get("quantity", 1)
                    item_default_info = DEFAULT_ITEMS.get(item_name, {})

                    full_description = item_default_info.get(
                        "description", "An undescribed item."
                    )

                    qty_str = ""
                    if (
                        item_default_info.get("stackable")
                        or item_default_info.get("value") is not None
                    ) and item_qty > 1:
                        qty_str = f" (x{item_qty})"

                    item_display_line = f"{item_name}{qty_str} - {full_description}"
                    self._print_color(
                        f"{action_number}. {item_display_line}", Colors.GREEN
                    )

                    self.numbered_actions_context.append(
                        {
                            "type": "select_item",  # Changed from 'item_reference'
                            "target": item_name,
                            "display": item_name,
                        }
                    )
                    action_number += 1
                    items_present_for_hint = True
            else:
                self._print_color("No loose items of interest here.", Colors.DIM)
            self._print_color("", Colors.RESET)
            self._print_color("--- Exits ---", Colors.BLUE + Colors.BOLD)
            has_accessible_exits = False
            if current_location_data and current_location_data.get("exits"):
                for exit_target_loc, exit_desc in current_location_data[
                    "exits"
                ].items():
                    display_text = f"{exit_desc} (to {exit_target_loc})"
                    self.numbered_actions_context.append(
                        {
                            "type": "move",
                            "target": exit_target_loc,
                            "description": exit_desc,
                            "display": display_text,
                        }
                    )
                    self._print_color(f"{action_number}. {display_text}", Colors.BLUE)
                    action_number += 1
                    has_accessible_exits = True
            if not has_accessible_exits:
                self._print_color("There are no obvious exits from here.", Colors.DIM)
            self._print_color("", Colors.RESET)
            if items_present_for_hint:
                self._print_color(
                    "(Hint: You can 'take [item name]', 'look at [item name]', or use a number to interact with items.)",
                    Colors.DIM,
                )
            if npcs_present_for_hint:
                self._print_color(
                    "(Hint: You can 'talk to [npc name]', 'look at [npc name]', or use a number to interact with people.)",
                    Colors.DIM,
                )

    def _handle_take_command(self, argument):
        if not argument:
            self._print_color("What do you want to take?", Colors.RED)
            return False, False
        if not self.player_character:
            self._print_color(
                "Cannot take items: Player character not available.", Colors.RED
            )
            return False, False
        item_to_take_name = argument.lower()
        location_items = self.dynamic_location_items.get(self.current_location_name, [])
        item_found_in_loc, ambiguous = self.command_handler._get_matching_location_item(
            item_to_take_name
        )
        item_idx_in_loc = -1
        if item_found_in_loc:
            item_idx_in_loc = location_items.index(item_found_in_loc)
        elif ambiguous:
            return False, False
        if item_found_in_loc:
            item_default_props = DEFAULT_ITEMS.get(item_found_in_loc["name"], {})
            if item_default_props.get("takeable", False):
                take_quantity = 1
                actual_taken_qty = 0
                if (
                    item_default_props.get("stackable")
                    or item_default_props.get("value") is not None
                ):
                    current_qty_in_loc = item_found_in_loc.get("quantity", 1)
                    actual_taken_qty = min(take_quantity, current_qty_in_loc)
                    item_found_in_loc["quantity"] -= actual_taken_qty
                    if item_found_in_loc["quantity"] <= 0:
                        location_items.pop(item_idx_in_loc)
                else:
                    actual_taken_qty = 1
                    location_items.pop(item_idx_in_loc)
                if self.player_character.add_to_inventory(
                    item_found_in_loc["name"], actual_taken_qty
                ):
                    self._print_color(
                        f"You take the {item_found_in_loc['name']}"
                        + (
                            f" (x{actual_taken_qty})"
                            if actual_taken_qty > 1
                            and (
                                item_default_props.get("stackable")
                                or item_default_props.get("value") is not None
                            )
                            else ""
                        )
                        + ".",
                        Colors.GREEN,
                    )
                    self.last_significant_event_summary = (
                        f"took the {item_found_in_loc['name']}."
                    )
                    if item_default_props.get("is_notable"):
                        self.player_character.apparent_state = random.choice(
                            ["thoughtful", "burdened"]
                        )
                    if (
                        self.player_character.name == "Rodion Raskolnikov"
                        and item_found_in_loc["name"] == "raskolnikov's axe"
                    ):
                        self.player_notoriety_level = min(
                            3, max(0, self.player_notoriety_level + 0.5)
                        )
                        self._print_color(
                            "(Reclaiming the axe sends a shiver down your spine, a feeling of being marked.)",
                            Colors.RED + Colors.DIM,
                        )
                    for npc in self.npcs_in_current_location:
                        if npc.name != self.player_character.name:
                            npc.add_player_memory(
                                memory_type="player_action_observed",
                                turn=self.game_time,
                                content={
                                    "action": "took_item",
                                    "item_name": item_found_in_loc["name"],
                                    "quantity": actual_taken_qty,
                                    "location": self.current_location_name,
                                },
                                sentiment_impact=(
                                    -1 if item_default_props.get("is_notable") else 0
                                ),
                            )
                    taken_item_name = item_found_in_loc["name"]
                    taken_item_props = DEFAULT_ITEMS.get(
                        taken_item_name, {}
                    )  # Changed: self.game_config
                    if taken_item_props.get("readable"):
                        self._print_color(
                            f"(Hint: You can now 'read {taken_item_name}'.)", Colors.DIM
                        )
                    elif (
                        taken_item_props.get("use_effect_player")
                        and taken_item_name != "worn coin"
                    ):
                        self._print_color(
                            f"(Hint: You can try to 'use {taken_item_name}'.)",
                            Colors.DIM,
                        )
                    return True, False
                else:
                    # Check if the failure was due to trying to take a non-stackable item already possessed
                    item_name_failed_to_add = item_found_in_loc["name"]
                    item_props_failed = DEFAULT_ITEMS.get(item_name_failed_to_add, {})
                    is_non_stackable_unique = (
                        not item_props_failed.get("stackable", False)
                        and item_props_failed.get("value") is None
                    )

                    if is_non_stackable_unique and self.player_character.has_item(
                        item_name_failed_to_add
                    ):
                        self._print_color(
                            f"You cannot carry another '{item_name_failed_to_add}'.",
                            Colors.YELLOW,
                        )
                    else:
                        # Generic failure message if not the specific non-stackable case
                        self._print_color(
                            f"Failed to add {item_name_failed_to_add} to inventory.",
                            Colors.RED,
                        )
                    return (
                        False,
                        False,
                    )  # Action was attempted (hence True for show_atmospherics) but failed
            else:
                self._print_color(
                    f"You can't take the {item_found_in_loc['name']}.", Colors.YELLOW
                )
                return False, False
        else:
            self._print_color(
                f"You don't see any '{item_to_take_name}' here to take.", Colors.RED
            )
            return False, False

    def _handle_drop_command(self, argument):
        if not argument:
            self._print_color("What do you want to drop?", Colors.RED)
            return False, False
        if not self.player_character:
            self._print_color(
                "Cannot drop items: Player character not available.", Colors.RED
            )
            return False, False
        item_to_drop_name_input = argument.lower()
        item_in_inventory_obj, ambiguous = (
            self.command_handler._get_matching_inventory_item(item_to_drop_name_input)
        )
        if ambiguous:
            return False, False
        if item_in_inventory_obj:
            item_name_to_drop = item_in_inventory_obj["name"]
            item_default_props = DEFAULT_ITEMS.get(item_name_to_drop, {})
            drop_quantity = 1
            if self.player_character.remove_from_inventory(
                item_name_to_drop, drop_quantity
            ):
                location_items = self.dynamic_location_items.setdefault(
                    self.current_location_name, []
                )
                existing_loc_item = None
                for loc_item in location_items:
                    if loc_item["name"] == item_name_to_drop:
                        existing_loc_item = loc_item
                        break
                if existing_loc_item and (
                    item_default_props.get("stackable")
                    or item_default_props.get("value") is not None
                ):
                    existing_loc_item["quantity"] = (
                        existing_loc_item.get("quantity", 0) + drop_quantity
                    )
                else:
                    location_items.append(
                        {"name": item_name_to_drop, "quantity": drop_quantity}
                    )
                self._print_color(f"You drop the {item_name_to_drop}.", Colors.GREEN)
                self.last_significant_event_summary = (
                    f"dropped the {item_name_to_drop}."
                )
                for npc in self.npcs_in_current_location:
                    if npc.name != self.player_character.name:
                        npc.add_player_memory(
                            memory_type="player_action_observed",
                            turn=self.game_time,
                            content={
                                "action": "dropped_item",
                                "item_name": item_name_to_drop,
                                "quantity": drop_quantity,
                                "location": self.current_location_name,
                            },
                            sentiment_impact=0,
                        )
                return True, False
            else:
                self._print_color(
                    f"You try to drop {item_name_to_drop}, but something is wrong.",
                    Colors.RED,
                )
                return False, False
        else:
            self._print_color(
                f"You don't have '{item_to_drop_name_input}' to drop.", Colors.RED
            )
            return False, False

    def _handle_use_command(self, argument):
        if not self.player_character:
            self._print_color(
                "Cannot use items: Player character not available.", Colors.RED
            )
            return False
        if isinstance(argument, tuple):
            item_name_input, target_name_input, interaction_mode = argument
            return self.handle_use_item(
                item_name_input, target_name_input, interaction_mode
            )
        elif argument:
            return self.handle_use_item(argument, None, "use_self_implicit")
        else:
            self._print_color("What do you want to use or read?", Colors.RED)
            return False

    def _handle_read_item(self, item_to_use_name, item_props, item_obj_in_inventory):
        if not self.player_character:
            self._print_color(
                "Cannot read items: Player character not available.", Colors.RED
            )
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        if not item_props.get("readable"):
            self._print_color(f"You can't read the {item_to_use_name}.", Colors.YELLOW)
            return False
        if item_to_use_name == "old newspaper" or item_to_use_name == "fresh newspaper":
            self._print_color(
                f"You smooth out the creases of the {item_to_use_name} and scan the faded print.",
                Colors.WHITE,
            )
            article_snippet = None
            ai_generated = False
            if not self.low_ai_data_mode and self.gemini_api.model:
                article_snippet = self.gemini_api.get_newspaper_article_snippet(
                    self.current_day,
                    self._get_recent_events_summary(),
                    self._get_objectives_summary(player_character),
                    player_character.apparent_state,
                )

            if (
                article_snippet is None
                or (
                    isinstance(article_snippet, str)
                    and article_snippet.startswith("(OOC:")
                )
                or self.low_ai_data_mode
            ):
                if STATIC_NEWSPAPER_SNIPPETS:
                    article_snippet = random.choice(STATIC_NEWSPAPER_SNIPPETS)
                else:
                    article_snippet = "The newsprint is smudged and uninteresting."  # Ultimate fallback

                if article_snippet:  # Make sure we have something to print/log
                    article_snippet = self._apply_verbosity(article_snippet)
                    self._print_color(
                        f'An article catches your eye: "{article_snippet}"', Colors.CYAN
                    )  # Static in Cyan
                    player_character.add_journal_entry(
                        "News (Static)",
                        article_snippet,
                        self._get_current_game_time_period_str(),
                    )  # Optionally log differently
            elif article_snippet:  # AI success and not OOC
                article_snippet = self._apply_verbosity(article_snippet)
                self._print_color(
                    f'An article catches your eye: "{article_snippet}"', Colors.YELLOW
                )
                player_character.add_journal_entry(
                    "News (AI)",
                    article_snippet,
                    self._get_current_game_time_period_str(),
                )  # Optionally log differently
                ai_generated = True

            if not article_snippet:  # Final fallback if all else fails
                self._print_color(
                    "The print is too faded or the news too mundane to hold your interest.",
                    Colors.DIM,
                )

            # Common logic for both AI and static snippets if they are valid
            if article_snippet:
                if (
                    "crime" in article_snippet.lower()
                    or "investigation" in article_snippet.lower()
                    or "murder" in article_snippet.lower()
                ):
                    player_character.apparent_state = "thoughtful"
                    if player_character.name == "Rodion Raskolnikov":
                        player_character.add_player_memory(
                            memory_type="read_news_crime",
                            turn=self.game_time,
                            content={
                                "summary": "Read unsettling news about the recent crime."
                            },
                            sentiment_impact=0,
                        )
                        self.player_notoriety_level = min(
                            self.player_notoriety_level + 0.1, 3
                        )
                self.last_significant_event_summary = f"read an {item_to_use_name}."
                if ai_generated:
                    self._remember_ai_output(article_snippet, "news_article")
            return True
        elif item_to_use_name == "mother's letter":
            self._print_color(
                "You re-read your mother's letter. Her words of love and anxiety, Dunya's predicament... it all weighs heavily on you.",
                Colors.YELLOW,
            )
            reflection = None
            prompt_context = "re-reading mother's letter about Dunya and Luzhin, feeling guilt and responsibility"
            if not self.low_ai_data_mode and self.gemini_api.model:
                reflection = self.gemini_api.get_player_reflection(
                    player_character,
                    current_location_name,
                    self.world_manager.get_current_time_period(),
                    prompt_context,
                )

            if (
                reflection is None
                or (isinstance(reflection, str) and reflection.startswith("(OOC:"))
                or self.low_ai_data_mode
            ):
                if STATIC_PLAYER_REFLECTIONS:
                    reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
                else:
                    reflection = "The letter stirs a whirlwind of emotions and responsibilities."  # Ultimate fallback
                self._print_color(
                    f'"{self._apply_verbosity(reflection)}"', Colors.DIM
                )  # Static reflection in DIM
            else:  # AI success
                reflection = self._apply_verbosity(reflection)
                self._print_color(f'"{reflection}"', Colors.CYAN)
                self._remember_ai_output(reflection, "read_letter")

            player_character.apparent_state = random.choice(
                ["burdened", "agitated", "resolved"]
            )
            if player_character.name == "Rodion Raskolnikov":
                player_character.add_player_memory(
                    memory_type="reread_mother_letter",
                    turn=self.game_time,
                    content={
                        "summary": "Re-reading mother's letter intensified feelings of duty and distress."
                    },
                    sentiment_impact=-1,
                )
            self.last_significant_event_summary = f"re-read the {item_to_use_name}."
            return True
        elif item_to_use_name == "sonya's new testament":
            self._print_color(
                f"You open {item_to_use_name}. The familiar words of the Gospels seem to both accuse and offer a sliver of hope.",
                Colors.GREEN,
            )
            reflection = None
            prompt_context = f"reading from {item_to_use_name}, pondering Lazarus, guilt, and salvation"
            if not self.low_ai_data_mode and self.gemini_api.model:
                reflection = self.gemini_api.get_player_reflection(
                    player_character,
                    current_location_name,
                    self.get_current_time_period(),
                    prompt_context,
                )

            if (
                reflection is None
                or (isinstance(reflection, str) and reflection.startswith("(OOC:"))
                or self.low_ai_data_mode
            ):
                if STATIC_PLAYER_REFLECTIONS:
                    reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
                else:
                    reflection = "The words offer a strange mix of judgment and hope."  # Ultimate fallback
                self._print_color(
                    f'"{self._apply_verbosity(reflection)}"', Colors.DIM
                )  # Static reflection in DIM
            else:  # AI success
                reflection = self._apply_verbosity(reflection)
                self._print_color(f'"{reflection}"', Colors.CYAN)
                self._remember_ai_output(reflection, "read_testament")

            if player_character.name == "Rodion Raskolnikov":
                player_character.apparent_state = random.choice(
                    ["contemplative", "remorseful", "thoughtful", "hopeful"]
                )
                player_character.add_player_memory(
                    memory_type="read_testament_sonya",
                    turn=self.game_time,
                    content={
                        "summary": "Read from the New Testament, stirring deep thoughts of salvation and suffering."
                    },
                    sentiment_impact=0,
                )
            self.last_significant_event_summary = f"read from {item_to_use_name}."
            return True
        elif item_to_use_name == "anonymous note":
            if item_obj_in_inventory and "generated_content" in item_obj_in_inventory:
                self._print_color(f"You read the {item_to_use_name}:", Colors.WHITE)
                self._print_color(
                    f"\"{item_obj_in_inventory['generated_content']}\"", Colors.CYAN
                )
                player_character.add_journal_entry(
                    "Note",
                    item_obj_in_inventory["generated_content"],
                    self._get_current_game_time_period_str(),
                )
                self.last_significant_event_summary = f"read an {item_to_use_name}."
                if (
                    "watch" in item_obj_in_inventory["generated_content"].lower()
                    or "know" in item_obj_in_inventory["generated_content"].lower()
                ):
                    player_character.apparent_state = "paranoid"
                return True
            else:
                self._print_color(
                    f"The {item_to_use_name} seems to be blank or unreadable.",
                    Colors.RED,
                )
                return False
        elif item_to_use_name == "IOU Slip":
            if item_obj_in_inventory and item_obj_in_inventory.get("content"):
                self._print_color(
                    f"You examine the {item_to_use_name}: \"{item_obj_in_inventory['content']}\"",
                    Colors.YELLOW,
                )
            else:
                self._print_color(
                    f"You look at the {item_to_use_name}. It's a formal-looking slip of paper.",
                    Colors.YELLOW,
                )
            self.last_significant_event_summary = f"read an {item_to_use_name}."
            return True
        elif item_to_use_name == "Student's Dog-eared Book":
            book_reflection = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                book_reflection = self.gemini_api.get_item_interaction_description(
                    player_character,
                    item_to_use_name,
                    item_props,
                    "read",
                    current_location_name,
                    self.get_current_time_period(),
                )

            if (
                book_reflection is None
                or (
                    isinstance(book_reflection, str)
                    and book_reflection.startswith("(OOC:")
                )
                or self.low_ai_data_mode
            ):
                book_reflection = generate_static_item_interaction_description(
                    item_to_use_name, "read"
                )
                self._print_color(
                    f"You open the {item_to_use_name}. {book_reflection}", Colors.CYAN
                )  # Static in Cyan
            else:  # AI success
                self._print_color(
                    f"You open the {item_to_use_name}. {book_reflection}", Colors.YELLOW
                )

            self.last_significant_event_summary = f"read from a {item_to_use_name}."
            return True

        read_reflection = None
        if not self.low_ai_data_mode and self.gemini_api.model:
            read_reflection = self.gemini_api.get_item_interaction_description(
                player_character,
                item_to_use_name,
                item_props,
                "read",
                current_location_name,
                self.get_current_time_period(),
            )

        if (
            read_reflection is None
            or (
                isinstance(read_reflection, str) and read_reflection.startswith("(OOC:")
            )
            or self.low_ai_data_mode
        ):
            read_reflection = generate_static_item_interaction_description(
                item_to_use_name, "read"
            )
            self._print_color(
                f"You read the {item_to_use_name}. {read_reflection}", Colors.CYAN
            )  # Static in Cyan
        else:  # AI success
            self._print_color(
                f"You read the {item_to_use_name}. {read_reflection}", Colors.YELLOW
            )

        self.last_significant_event_summary = f"read the {item_to_use_name}."
        return True

    def _handle_self_use_item(self, item_to_use_name, item_props, effect_key):
        if not self.player_character:
            self._print_color(
                "Cannot use items: Player character not available.", Colors.RED
            )
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        used_successfully = False
        if (
            effect_key == "comfort_self_if_ill"
            and item_to_use_name == "tattered handkerchief"
        ):
            if player_character.apparent_state in [
                "feverish",
                "coughing",
                "ill",
                "haunted by dreams",
            ]:
                self._print_color(
                    f"You press the {item_to_use_name} to your brow. It offers little physical comfort, but it's something to cling to.",
                    Colors.YELLOW,
                )
                if (
                    player_character.apparent_state == "feverish"
                    and random.random() < 0.2
                ):
                    player_character.apparent_state = "less feverish"
                    self._print_color(
                        "The coolness, imagined or real, seems to lessen the fever's grip for a moment.",
                        Colors.CYAN,
                    )
                self.last_significant_event_summary = (
                    f"used a {item_to_use_name} while feeling unwell."
                )
                used_successfully = True
            else:
                self._print_color(
                    f"You look at the {item_to_use_name}. It seems rather pointless to use it now.",
                    Colors.YELLOW,
                )
        elif (
            effect_key == "examine_bottle_for_residue"
            and item_to_use_name == "dusty bottle"
        ):
            self._print_color(
                f"You peer into the {item_to_use_name}. A faint, stale smell of cheap spirits lingers. It's long empty.",
                Colors.YELLOW,
            )
            self.last_significant_event_summary = f"examined a {item_to_use_name}."
            used_successfully = True
        elif (
            effect_key == "grip_axe_and_reminisce_horror"
            and item_to_use_name == "raskolnikov's axe"
        ):
            if player_character.name == "Rodion Raskolnikov":
                self._print_color(
                    f"You grip the {item_to_use_name}. Its cold weight is a familiar dread. The memories, sharp and bloody, flood your mind. You feel a wave of nausea, then a chilling resolve, then utter despair.",
                    Colors.RED + Colors.BOLD,
                )
                player_character.apparent_state = random.choice(
                    ["dangerously agitated", "remorseful", "paranoid"]
                )
                self.last_significant_event_summary = (
                    "held the axe, tormented by memories."
                )
                used_successfully = True
            else:
                self._print_color(
                    f"You look at the {item_to_use_name}. It's a grim object, heavy and unsettling. Best left alone.",
                    Colors.YELLOW,
                )
                used_successfully = True
        elif (
            effect_key == "reflect_on_faith_and_redemption"
            and item_to_use_name == "sonya's cypress cross"
        ):
            if player_character.name == "Rodion Raskolnikov":
                self._print_color(
                    "You clutch the small cypress cross. It feels strangely significant in your hand, a stark contrast to the turmoil within you.",
                    Colors.GREEN,
                )
                player_character.apparent_state = random.choice(
                    ["remorseful", "contemplative", "hopeful"]
                )
                self.last_significant_event_summary = (
                    "held Sonya's cross, feeling its weight and Sonya's sacrifice."
                )
                reflection = None
                if not self.low_ai_data_mode and self.gemini_api.model:
                    reflection = self.gemini_api.get_player_reflection(
                        player_character,
                        current_location_name,
                        self.get_current_time_period(),
                        "Holding Sonya's cross, new thoughts about suffering and sacrifice surface.",
                    )
                if (
                    reflection is None
                    or (isinstance(reflection, str) and reflection.startswith("(OOC:"))
                    or self.low_ai_data_mode
                ):
                    if STATIC_PLAYER_REFLECTIONS:
                        reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
                    else:
                        reflection = (
                            "The cross feels warm in your hand, a quiet comfort."
                        )
                    self._print_color(f'"{reflection}"', Colors.CYAN)
                    used_successfully = True
            else:
                self._print_color(
                    f"You examine {item_to_use_name}. It seems to be a simple wooden cross, yet it emanates a certain potent feeling.",
                    Colors.YELLOW,
                )
                used_successfully = True
        elif (
            effect_key == "examine_rag_and_spiral_into_paranoia"
            and item_to_use_name == "bloodied rag"
        ):
            self._print_color(
                f"You stare at the {item_to_use_name}. The dark stains seem to shift and spread before your eyes. Every sound, every shadow, feels like an accusation.",
                Colors.RED,
            )
            player_character.apparent_state = "paranoid"
            if player_character.name == "Rodion Raskolnikov":
                player_character.add_player_memory(
                    memory_type="observed_bloodied_rag",
                    turn=self.game_time,
                    content={
                        "summary": "The sight of the bloodied rag brought a fresh wave of paranoia."
                    },
                    sentiment_impact=-1,
                )
                self.player_notoriety_level = min(self.player_notoriety_level + 0.5, 3)
            self.last_significant_event_summary = (
                f"was deeply disturbed by a {item_to_use_name}."
            )
            used_successfully = True
        elif (
            effect_key == "drink_vodka_for_oblivion"
            and item_to_use_name == "cheap vodka"
        ):
            original_state_feverish = player_character.apparent_state == "feverish"
            self._print_color(
                "You take a long swig of the harsh vodka. It burns on the way down, offering a brief, false warmth and a dulling of the senses.",
                Colors.MAGENTA,
            )

            # Default effect of vodka
            player_character.apparent_state = "slightly drunk"

            if player_character.has_item("cheap vodka"):
                player_character.remove_from_inventory("cheap vodka", 1)
            else:
                self._print_color(
                    "Odd, the bottle seems to have vanished before you could drink it all.",
                    Colors.DIM,
                )
            self.last_significant_event_summary = (
                "drank some cheap vodka to numb the thoughts."
            )

            # Override if originally feverish
            if original_state_feverish:
                player_character.apparent_state = "agitated"
                self._print_color(
                    "The vodka clashes terribly with your fever, making you feel worse.",
                    Colors.RED,
                )
            used_successfully = True
        elif (
            effect_key == "examine_bundle_and_face_guilt_for_Lizaveta"
            and item_to_use_name == "lizaveta's bundle"
        ):
            self._print_color(
                f"You hesitantly open {item_to_use_name}. Inside are a few pitiful belongings: a worn shawl, a child's small wooden toy, a copper coin... The sight is a fresh stab of guilt for the gentle Lizaveta.",
                Colors.YELLOW,
            )
            if player_character.name == "Rodion Raskolnikov":
                player_character.apparent_state = "remorseful"
                player_character.add_player_memory(
                    memory_type="examined_lizavetas_bundle",
                    turn=self.game_time,
                    content={
                        "summary": "Examined lizaveta's bundle; the innocence of the items was a heavy burden."
                    },
                    sentiment_impact=-1,
                )
            self.last_significant_event_summary = (
                "examined lizaveta's bundle, increasing the weight of guilt."
            )
            used_successfully = True
        elif (
            effect_key == "eat_bread_for_sustenance"
            and item_to_use_name == "Loaf of Black Bread"
        ):
            self._print_color(
                f"You tear off a piece of the dense {item_to_use_name}. It's coarse, but fills your stomach somewhat.",
                Colors.YELLOW,
            )
            if player_character.apparent_state in [
                "burdened",
                "feverish",
                "despondent",
            ]:
                player_character.apparent_state = "normal"
                self._print_color(
                    "The bread provides a moment of simple relief.", Colors.CYAN
                )
            self.last_significant_event_summary = f"ate some {item_to_use_name}."
            used_successfully = True
        elif (
            effect_key == "contemplate_icon"
            and item_to_use_name == "Small, Tarnished Icon"
        ):
            icon_reflection = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                icon_reflection = self.gemini_api.get_item_interaction_description(
                    player_character,
                    item_to_use_name,
                    item_props,
                    "contemplate",
                    current_location_name,
                    self.get_current_time_period(),
                )

            if (
                icon_reflection is None
                or (
                    isinstance(icon_reflection, str)
                    and icon_reflection.startswith("(OOC:")
                )
                or self.low_ai_data_mode
            ):
                icon_reflection = generate_static_item_interaction_description(
                    item_to_use_name, "contemplate"
                )
                self._print_color(
                    f"You gaze at the {item_to_use_name}. {icon_reflection}",
                    Colors.CYAN,
                )  # Static in Cyan
            else:  # AI success
                self._print_color(
                    f"You gaze at the {item_to_use_name}. {icon_reflection}",
                    Colors.YELLOW,
                )
            self.last_significant_event_summary = f"contemplated a {item_to_use_name}."
            used_successfully = True
        if not used_successfully:
            self._print_color(
                f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.",
                Colors.YELLOW,
            )
            return False
        return used_successfully

    def _handle_give_item(self, item_to_use_name, item_props, target_name_input):
        if not self.player_character:
            self._print_color(
                "Cannot give items: Player character not available.", Colors.RED
            )
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        target_npc = next(
            (
                npc
                for npc in self.npcs_in_current_location
                if npc.name.lower().startswith(target_name_input.lower())
            ),
            None,
        )

        if not target_npc:
            self._print_color(
                f"You don't see '{target_name_input}' here to give anything to.",
                Colors.RED,
            )
            return False

        # Check if player has the item (using a generic quantity of 1 for now)
        # More sophisticated quantity handling could be added if items become stackable in a way that 'give' needs to respect.
        if not player_character.has_item(item_to_use_name, quantity=1):
            self._print_color(f"You don't have {item_to_use_name} to give.", Colors.RED)
            return False

        # Attempt to remove the item from player's inventory
        if player_character.remove_from_inventory(item_to_use_name, 1):
            # Add item to NPC's inventory
            target_npc.add_to_inventory(
                item_to_use_name, 1
            )  # Assuming quantity 1 for now

            self._print_color(
                f"You give the {item_to_use_name} to {target_npc.name}.", Colors.WHITE
            )

            # Generate NPC reaction using Gemini API
            relationship_text = self.get_relationship_text(
                target_npc.relationship_with_player
            )
            dialogue_prompt = (
                f"(Player gives {item_to_use_name} to NPC. Player expects a reaction.)"
            )

            reaction = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                reaction = self.gemini_api.get_npc_dialogue(
                    target_npc,
                    player_character,
                    dialogue_prompt,
                    current_location_name,
                    self.get_current_time_period(),
                    relationship_text,
                    target_npc.get_player_memory_summary(self.game_time),
                    player_character.apparent_state,
                    player_character.get_notable_carried_items_summary(),
                    self._get_recent_events_summary(),
                    self._get_objectives_summary(target_npc),
                    self._get_objectives_summary(player_character),
                )

            if (
                reaction is None
                or (isinstance(reaction, str) and reaction.startswith("(OOC:"))
                or self.low_ai_data_mode
            ):
                # Fallback static reaction if AI fails or low_ai_mode
                static_reactions = [
                    f"Oh, for me? Thank you for the {item_to_use_name}.",
                    f"A {item_to_use_name}? How thoughtful of you.",
                    f"I appreciate you giving me this {item_to_use_name}.",
                    f"Thank you, this {item_to_use_name} is noted.",
                ]
                reaction = random.choice(static_reactions)
                self._print_color(
                    f'{target_npc.name}: "{reaction}" {Colors.DIM}(Static reaction){Colors.RESET}',
                    Colors.YELLOW,
                )
            else:  # AI Success
                self._print_color(f'{target_npc.name}: "{reaction}"', Colors.YELLOW)

            # Update NPC's relationship with the player (e.g., a slight increase)
            target_npc.relationship_with_player += (
                1  # Simple increment, can be more nuanced
            )

            # Add a memory to the NPC about receiving the item
            target_npc.add_player_memory(
                memory_type="received_item",
                turn=self.game_time,
                content={
                    "item_name": item_to_use_name,
                    "quantity": 1,
                    "from_player": True,
                    "context": "player_gave_item",
                },
                sentiment_impact=1,  # Generally positive for receiving an item
            )

            self.last_significant_event_summary = (
                f"gave {item_to_use_name} to {target_npc.name}."
            )
            return True
        else:
            # This case should ideally be caught by has_item, but as a fallback
            self._print_color(
                f"You find you don't actually have {item_to_use_name} to give after all.",
                Colors.RED,
            )
            return False

    def handle_use_item(
        self,
        item_name_input,
        target_name_input=None,
        interaction_type="use_self_implicit",
    ):
        # This wrapper supports "give" and "use_on" routing too
        if not self.player_character:
            self._print_color("Cannot use items: Player character not set.", Colors.RED)
            return False
        item_to_use_name = None
        item_obj_in_inventory = None
        if item_name_input:
            for inv_item_obj_loop in self.player_character.inventory:
                if (
                    inv_item_obj_loop["name"]
                    .lower()
                    .startswith(item_name_input.lower())
                ):
                    item_to_use_name = inv_item_obj_loop["name"]
                    item_obj_in_inventory = inv_item_obj_loop
                    break
            if not item_to_use_name:
                if self.player_character.has_item(item_name_input):
                    item_to_use_name = item_name_input
                    item_obj_in_inventory = next(
                        (
                            item
                            for item in self.player_character.inventory
                            if item["name"] == item_to_use_name
                        ),
                        None,
                    )
                else:
                    self._print_color(
                        f"You don't have '{item_name_input}' to {interaction_type.replace('_', ' ')}.",
                        Colors.RED,
                    )
                    return False
        elif interaction_type != "use_self_implicit":
            self._print_color(
                f"What do you want to {interaction_type.replace('_', ' ')}{(' on ' + target_name_input) if target_name_input else ''}?",
                Colors.RED,
            )
            return False
        if not item_to_use_name:
            self._print_color("You need to specify an item to use or read.", Colors.RED)
            return False
        item_props = DEFAULT_ITEMS.get(item_to_use_name, {})
        used_successfully = False
        if interaction_type == "read":
            used_successfully = self._handle_read_item(
                item_to_use_name, item_props, item_obj_in_inventory
            )
        elif interaction_type == "give" and target_name_input:
            used_successfully = self._handle_give_item(
                item_to_use_name, item_props, target_name_input
            )
        elif interaction_type == "use_on" and target_name_input:
            self._print_color(
                f"You try to use the {item_to_use_name} on {target_name_input}, but nothing specific happens.",
                Colors.YELLOW,
            )
            used_successfully = False
        else:
            effect_key = item_props.get("use_effect_player")
            if effect_key:
                used_successfully = self._handle_self_use_item(
                    item_to_use_name, item_props, effect_key
                )
            else:
                self._print_color(
                    f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.",
                    Colors.YELLOW,
                )
                used_successfully = False
        if (
            used_successfully
            and item_props.get("consumable", False)
            and item_to_use_name != "cheap vodka"
        ):
            if self.player_character.remove_from_inventory(item_to_use_name, 1):
                self._print_color(f"The {item_to_use_name} is used up.", Colors.MAGENTA)
        return used_successfully
