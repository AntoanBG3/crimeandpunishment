# character_module.py
import random
import copy
import logging
import json
from typing import Any, Dict, List, Optional
from .game_config import DEBUG_LOGS

def load_characters_data(data_path=None):
    from .game_config import get_data_path
    if data_path is None:
        data_path = get_data_path('data/characters.json')
    """Loads character data from a JSON file."""
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The characters data file was not found at {data_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error: The characters data file at {data_path} is not a valid JSON.")
        return {}

CHARACTERS_DATA = load_characters_data()

class Character:
    def __init__(self, name, persona, greeting, default_location, accessible_locations,
                 objectives=None, inventory_items=None, schedule=None, npc_relationships=None, skills_data=None,
                 psychology=None, is_player=False):
        self.name = name
        self.persona = persona
        self.greeting = greeting
        self.default_location = default_location
        self.current_location = default_location
        self.accessible_locations = accessible_locations if accessible_locations is not None else [default_location]
        self.is_player = is_player
        self.conversation_histories = {}
        self.memory_about_player = []  # List of dictionaries
        self.journal_entries = [] 
        self.relationship_with_player = 0
        self.npc_relationships = copy.deepcopy(npc_relationships) if npc_relationships is not None else {}
        self.skills = copy.deepcopy(skills_data) if skills_data is not None else {}
        default_psychology = {"suspicion": 0, "fear": 0, "respect": 50}
        if psychology is None:
            self.psychology = copy.deepcopy(default_psychology)
        else:
            merged_psychology = copy.deepcopy(default_psychology)
            merged_psychology.update(psychology)
            self.psychology = merged_psychology
        
        self.objectives = []
        if objectives:
            for obj_template in objectives:
                obj = copy.deepcopy(obj_template)
                obj["completed"] = obj.get("completed", False)
                obj["active"] = obj.get("active", True) 
                if "stages" not in obj or not obj["stages"]:
                    obj["stages"] = [{"stage_id": "default", "description": "Initial state of objective.", "is_current_stage": True}]
                
                current_stage_id_present = "current_stage_id" in obj
                current_stage_is_valid = False
                if current_stage_id_present:
                    for stage in obj["stages"]:
                        if stage.get("stage_id") == obj["current_stage_id"]:
                            stage["is_current_stage"] = True
                            current_stage_is_valid = True
                        else:
                            stage["is_current_stage"] = False
                
                if not current_stage_id_present or not current_stage_is_valid:
                    if obj["stages"]: 
                        obj["current_stage_id"] = obj["stages"][0].get("stage_id")
                        obj["stages"][0]["is_current_stage"] = True
                    else: 
                        obj["current_stage_id"] = "default"

                self.objectives.append(obj)


        self.inventory = [copy.deepcopy(item) for item in inventory_items] if inventory_items else []
        self.schedule = schedule if schedule else {}
        self.apparent_state = CHARACTERS_DATA.get(name, {}).get("apparent_state", "normal")


    def add_journal_entry(self, entry_type, text_content, game_day_time_period_str):
        MAX_JOURNAL_ENTRIES = 20 
        if len(self.journal_entries) >= MAX_JOURNAL_ENTRIES:
            self.journal_entries.pop(0) 
        
        entry = f"({game_day_time_period_str}) [{entry_type.upper()}]: {text_content}"
        self.journal_entries.append(entry)

    def get_journal_summary(self, count=5):
        if not self.journal_entries:
            return "Journal is empty."
        return "\nRecent Journal Entries:\n" + "\n".join(self.journal_entries[-count:])


    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "current_location": self.current_location,
            "is_player": self.is_player,
            "conversation_histories": self.conversation_histories,
            "memory_about_player": self.memory_about_player,
            "journal_entries": self.journal_entries, 
            "relationship_with_player": self.relationship_with_player,
            "npc_relationships": self.npc_relationships,
            "skills": self.skills,
            "objectives": self.objectives,
            "inventory": self.inventory,
            "apparent_state": self.apparent_state,
            "psychology": self.psychology,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], static_char_data: Optional[Dict[str, Any]]) -> 'Character':
        static_char_data_safe = static_char_data if static_char_data is not None else {}
        
        char = cls(
            name=data["name"], 
            persona=static_char_data_safe.get("persona", "A mysterious figure."),
            greeting=static_char_data_safe.get("greeting", "Hello."),
            default_location=static_char_data_safe.get("default_location", "Unknown Location"),
            accessible_locations=static_char_data_safe.get("accessible_locations", []),
            objectives=[], 
            inventory_items=data.get("inventory", []), 
            schedule=static_char_data_safe.get("schedule", {}),
            npc_relationships=static_char_data_safe.get("npc_relationships", {}), 
            skills_data=static_char_data_safe.get("skills", {}),
            psychology=static_char_data_safe.get("psychology"),
            is_player=data.get("is_player", False) 
        )
        
        char.current_location = data.get("current_location", char.default_location)
        char.conversation_histories = data.get("conversation_histories", {})
        char.memory_about_player = data.get("memory_about_player", []) # Ensures backward compatibility
        char.journal_entries = data.get("journal_entries", []) 
        char.relationship_with_player = data.get("relationship_with_player", 0)
        char.apparent_state = data.get("apparent_state", static_char_data_safe.get("apparent_state", "normal"))
        saved_psychology = data.get("psychology")
        if saved_psychology is not None:
            merged_psychology = copy.deepcopy(char.psychology)
            merged_psychology.update(saved_psychology)
            char.psychology = merged_psychology

        saved_npc_relationships = data.get("npc_relationships")
        if saved_npc_relationships is not None:
            char.npc_relationships = saved_npc_relationships
        
        saved_skills = data.get("skills")
        if saved_skills is not None:
            char.skills = saved_skills

        loaded_objectives_map = {obj['id']: obj for obj in data.get("objectives", []) if 'id' in obj}
        static_objectives_template = static_char_data_safe.get("objectives", [])
        
        final_objectives_list = []
        if static_objectives_template:
            for static_obj_template_item in static_objectives_template:
                obj_id = static_obj_template_item.get("id")
                if not obj_id: continue

                final_obj = copy.deepcopy(static_obj_template_item) 

                if obj_id in loaded_objectives_map: 
                    loaded_obj_data = loaded_objectives_map[obj_id]
                    final_obj["completed"] = loaded_obj_data.get("completed", final_obj.get("completed", False))
                    final_obj["active"] = loaded_obj_data.get("active", final_obj.get("active", True))
                    final_obj["current_stage_id"] = loaded_obj_data.get("current_stage_id", final_obj.get("current_stage_id"))

                if "stages" in final_obj and final_obj["stages"]:
                    current_stage_id_found_in_stages = False
                    for stage_in_final_obj in final_obj["stages"]:
                        is_current = (stage_in_final_obj.get("stage_id") == final_obj.get("current_stage_id"))
                        stage_in_final_obj["is_current_stage"] = is_current
                        if is_current:
                            current_stage_id_found_in_stages = True
                    if not current_stage_id_found_in_stages and final_obj["stages"]:
                        saved_stage_id = final_obj.get("current_stage_id") # Get the saved stage ID before defaulting
                        objective_id = final_obj.get("id", "Unknown Objective")
                        logging.warning(
                            f"Warning: Saved objective stage ID '{saved_stage_id}' for objective '{objective_id}' "
                            f"not found in current game data. Defaulting to first stage."
                        )
                        final_obj["current_stage_id"] = final_obj["stages"][0].get("stage_id")
                        final_obj["stages"][0]["is_current_stage"] = True
                elif "stages" not in final_obj or not final_obj.get("stages"):
                     final_obj["stages"] = [{"stage_id": "default", "description": "Objective state.", "is_current_stage": True}]
                     final_obj["current_stage_id"] = "default"

                final_objectives_list.append(final_obj)
        
        for loaded_id, loaded_obj_val in loaded_objectives_map.items():
            if not any(fo.get('id') == loaded_id for fo in final_objectives_list):
                loaded_obj_val["stages"] = loaded_obj_val.get("stages", [{"stage_id": "default", "description": "Legacy objective state.", "is_current_stage": True}])
                if "current_stage_id" not in loaded_obj_val and loaded_obj_val.get("stages"):
                    loaded_obj_val["current_stage_id"] = loaded_obj_val["stages"][0].get("stage_id")
                if loaded_obj_val.get("stages"): 
                    for stage in loaded_obj_val["stages"]:
                        stage["is_current_stage"] = (stage.get("stage_id") == loaded_obj_val.get("current_stage_id"))
                loaded_obj_val["active"] = loaded_obj_val.get("active", True)
                loaded_obj_val["completed"] = loaded_obj_val.get("completed", False)
                final_objectives_list.append(loaded_obj_val)
        
        char.objectives = final_objectives_list
        return char

    def apply_psychology_changes(self, stat_changes):
        if not isinstance(stat_changes, dict):
            return
        for stat_name, delta in stat_changes.items():
            if stat_name not in self.psychology:
                continue
            try:
                delta_value = int(delta)
            except (TypeError, ValueError):
                continue
            current_value = self.psychology.get(stat_name, 0)
            updated_value = max(0, min(100, current_value + delta_value))
            self.psychology[stat_name] = updated_value
            if DEBUG_LOGS:
                print(f"[DEBUG] {self.name} psychology '{stat_name}' changed by {delta_value} -> {updated_value}")

    def add_to_inventory(self, item_name, quantity=1):
        from .game_config import DEFAULT_ITEMS
        if item_name not in DEFAULT_ITEMS:
            return False

        item_props = DEFAULT_ITEMS[item_name]
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for item in self.inventory:
            if item["name"] == item_name:
                if is_stackable:
                    item["quantity"] = item.get("quantity", 1) + quantity
                    return True
                else: 
                    return False 

        new_item_entry = {"name": item_name}
        if is_stackable:
            new_item_entry["quantity"] = quantity
        elif quantity > 1: 
            pass 

        self.inventory.append(new_item_entry) 
        return True


    def remove_from_inventory(self, item_name, quantity=1):
        from .game_config import DEFAULT_ITEMS
        item_props = DEFAULT_ITEMS.get(item_name, {})
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for i, item in enumerate(self.inventory):
            if item["name"] == item_name:
                if is_stackable:
                    current_quantity = item.get("quantity", 1)
                    if current_quantity > quantity:
                        item["quantity"] -= quantity
                        return True
                    elif current_quantity == quantity:
                        self.inventory.pop(i)
                        return True
                    else: 
                        return False
                else: 
                    if quantity == 1: 
                        self.inventory.pop(i)
                        return True
                    else: 
                        return False
        return False 

    def has_item(self, item_name, quantity=1):
        from .game_config import DEFAULT_ITEMS
        item_props = DEFAULT_ITEMS.get(item_name, {})
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for item in self.inventory:
            if item["name"] == item_name:
                if is_stackable:
                    return item.get("quantity", 1) >= quantity
                else: 
                    return quantity == 1 
        return False

    def get_notable_carried_items_summary(self):
        from .game_config import DEFAULT_ITEMS
        if not self.inventory:
            return "is not carrying anything of note."
        notable_items_list = []
        for item_data in self.inventory:
            item_name = item_data["name"]
            item_props = DEFAULT_ITEMS.get(item_name, {})
            qty = item_data.get("quantity", 1) if item_props.get("stackable") or item_props.get("value") is not None else 1

            if item_props.get("is_notable", False):
                item_str = item_name
                if (item_props.get("stackable") or item_props.get("value") is not None) and qty > 1:
                    item_str += f" (x{qty})"
                notable_items_list.append(item_str)
            elif item_name == "worn coin" and qty >= item_props.get("notable_threshold", 20): 
                 notable_items_list.append(f"a sum of money ({qty} coins)")
        if not notable_items_list:
            return "is not carrying anything of note." # Made consistent
        if len(notable_items_list) == 1:
            return f"is carrying {notable_items_list[0]}."
        elif len(notable_items_list) == 2:
            return f"is carrying {notable_items_list[0]} and {notable_items_list[1]}."
        else: 
            return f"is carrying {', '.join(notable_items_list[:-1])}, and {notable_items_list[-1]}."

    def get_inventory_description(self):
        if not self.inventory:
            return "You are carrying nothing."
        descriptions = []
        from .game_config import DEFAULT_ITEMS
        for item_data in self.inventory:
            original_item_name = item_data["name"]
            clean_item_name = original_item_name

            command_suffix_marker = " use_effect_player:"

            if command_suffix_marker in original_item_name:
                parts = original_item_name.split(command_suffix_marker, 1)
                potential_clean_name = parts[0]
                if potential_clean_name in DEFAULT_ITEMS:
                    clean_item_name = potential_clean_name

            item_props = DEFAULT_ITEMS.get(clean_item_name, {})
            is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

            quantity = 1
            if is_stackable:
                quantity = item_data.get("quantity", 1)

            if is_stackable and quantity > 1:
                descriptions.append(f"{clean_item_name} (x{quantity})")
            else:
                descriptions.append(clean_item_name)
        return "You are carrying: " + ", ".join(descriptions) + "."

    def add_to_history(self, other_char_name, speaker_name, text):
        if other_char_name not in self.conversation_histories:
            self.conversation_histories[other_char_name] = []
        max_history = 10 
        self.conversation_histories[other_char_name].append(f"{speaker_name}: {text}")
        if len(self.conversation_histories[other_char_name]) > max_history:
            self.conversation_histories[other_char_name].pop(0) 

    def get_formatted_history(self, other_char_name, limit=6):
        history = self.conversation_histories.get(other_char_name, [])
        return "\n".join(history[-limit:])

    def add_player_memory(self, memory_type: str, turn: int, content: dict, sentiment_impact: int = 0):
        """
        Adds a structured memory about the player.
        memory_type: e.g., "received_item", "dialogue_exchange", "player_action_observed"
        turn: The game turn number.
        content: Dictionary with details specific to the type.
        sentiment_impact: Optional integer indicating sentiment impact.
        """
        # Basic validation to ensure content is a dictionary
        if not isinstance(content, dict):
            print(f"Error: Memory content for type '{memory_type}' must be a dictionary. Received: {content}")
            # Potentially add a default error memory or skip adding this memory
            return

        memory_entry = {
            "type": memory_type,
            "turn": turn,
            "content": content,
            "sentiment_impact": sentiment_impact
        }
        
        # Avoid duplicate exact memories if necessary, though turn makes most unique
        # For now, allow all memories to be added.
        self.memory_about_player.append(memory_entry)
        
        MAX_MEMORIES = 30  # Increased slightly
        if len(self.memory_about_player) > MAX_MEMORIES:
            self.memory_about_player.pop(0)

    def get_player_memory_summary(self, current_turn: int, count: int = 7):
        if not self.memory_about_player:
            return "You don't recall any specific interactions or observations about them yet."

        # Sort memories by turn, most recent first, then by sentiment impact
        # Lambda takes a memory dict and returns a tuple for sorting.
        # Sort primarily by recency (descending), then by absolute sentiment impact (descending)
        sorted_memories = sorted(
            self.memory_about_player,
            key=lambda m: (m.get("turn", 0), abs(m.get("sentiment_impact", 0))),
            reverse=True
        )

        summary_parts = []
        for mem in sorted_memories[:count]:
            turn_ago = current_turn - mem.get("turn", current_turn)
            recency_prefix = ""
            if turn_ago == 0:
                recency_prefix = "Just now, "
            elif turn_ago == 1:
                recency_prefix = "A moment ago, "
            elif turn_ago < 5:
                recency_prefix = "Recently, "
            else:
                recency_prefix = "Some time ago, "

            content_str = "details unclear"
            mem_type = mem.get("type")
            content = mem.get("content", {})

            if mem_type == "received_item":
                item_name = content.get("item_name", "an item")
                qty = content.get("quantity", 1)
                content_str = f"player gave me {item_name}{f' (x{qty})' if qty > 1 else ''}"
            elif mem_type == "gave_item_to_player":
                item_name = content.get("item_name", "an item")
                qty = content.get("quantity", 1)
                content_str = f"I gave {item_name}{f' (x{qty})' if qty > 1 else ''} to the player"
            elif mem_type == "dialogue_exchange":
                player_stmt = content.get("player_statement", "something")
                topic = content.get("topic_hint", "")
                sentiment = mem.get("sentiment_impact", 0)
                if topic:
                    content_str = f"we talked about {topic}"
                    if player_stmt and player_stmt != "...":
                         content_str += f", and they said '{player_stmt[:50]}...'"
                else:
                    content_str = f"player said '{player_stmt[:50]}...'"
                if sentiment > 0:
                    content_str += " (it was a positive exchange)"
                elif sentiment < 0:
                    content_str += " (it was a negative exchange)"
            elif mem_type == "player_action_observed":
                action = content.get("action", "did something")
                location = content.get("location")
                target = content.get("target_item")
                if target:
                    action_desc = f"player {action} {target}"
                else:
                    action_desc = f"player {action}"
                if location:
                    content_str = f"{action_desc} in {location}"
                else:
                    content_str = action_desc
            elif mem_type == "relationship_change": # For direct relationship updates
                direction = "positively" if content.get("change", 0) > 0 else "negatively"
                reason = content.get("reason", "something they did or said")
                content_str = f"my view of them changed {direction} because of {reason}"
            else: # Fallback for old string memories or unknown types
                if isinstance(mem, str): # Handle old format
                    content_str = mem 
                elif isinstance(content, dict) and "summary" in content: # If new type has a summary
                    content_str = content["summary"]
                elif isinstance(content, str): # If content is just a string
                    content_str = content
            
            summary_parts.append(recency_prefix + content_str)

        if not summary_parts:
            return "You have some fleeting recollections, but nothing stands out clearly."
        
        return "Key things you recall about them: " + "; ".join(summary_parts) + "."

    def update_relationship(self, player_dialogue: str, positive_keywords: list[str], negative_keywords: list[str], game_turn: int):
        change = 0
        player_dialogue_lower = player_dialogue.lower()
        for keyword in positive_keywords:
            if keyword in player_dialogue_lower:
                change += 1
        for keyword in negative_keywords:
            if keyword in player_dialogue_lower:
                change -= 1
        
        if change != 0: 
            self.relationship_with_player += change
            self.relationship_with_player = max(-10, min(10, self.relationship_with_player))
            self.add_player_memory(
                memory_type="relationship_change",
                turn=game_turn,
                content={
                    "reason": f"their statement ('{player_dialogue[:30]}...')",
                    "change": change
                },
                sentiment_impact=change
            )

    def get_objective_by_id(self, objective_id):
        if not objective_id: return None
        for obj in self.objectives:
            if obj.get("id") == objective_id:
                return obj
        return None

    def get_current_stage_for_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and obj.get("current_stage_id") and obj.get("stages"):
            for stage in obj["stages"]:
                if stage.get("stage_id") == obj["current_stage_id"]:
                    return stage
        return None

    def advance_objective_stage(self, objective_id, next_stage_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and obj.get("stages"):
            current_stage_found_in_obj = False
            next_stage_obj_from_template = None 
            
            for s_val_in_obj_stages in obj["stages"]:
                if s_val_in_obj_stages.get("stage_id") == next_stage_id:
                    next_stage_obj_from_template = s_val_in_obj_stages
                    break
            
            if not next_stage_obj_from_template:
                return False

            for stage_in_obj in obj["stages"]: 
                stage_in_obj["is_current_stage"] = (stage_in_obj.get("stage_id") == next_stage_id)
                if stage_in_obj["is_current_stage"]: 
                    current_stage_found_in_obj = True 

            if current_stage_found_in_obj: 
                obj["current_stage_id"] = next_stage_id
                new_stage_desc = next_stage_obj_from_template.get('description', 'unnamed stage')
                
                if self.is_player:
                    self.add_player_memory(memory_type="objective_progress", turn=0, content={"summary": f"Made progress on '{obj.get('description','Unnamed Objective')}': now at '{new_stage_desc}'."}, sentiment_impact=0)
                
                if next_stage_obj_from_template.get("is_ending_stage", False):
                    self.complete_objective(objective_id, by_stage=True)
                return True
        return False

    def complete_objective(self, objective_id, by_stage=False):
        obj = self.get_objective_by_id(objective_id)
        if obj and not obj.get("completed", False):
            obj["completed"] = True
            obj["active"] = False  
            obj_desc = obj.get('description', 'Unnamed Objective')
            if self.is_player:
                current_stage_for_memory = self.get_current_stage_for_objective(objective_id)
                stage_desc_for_memory = current_stage_for_memory.get('description', 'final stage') if current_stage_for_memory else 'final stage'
                
                if not by_stage:
                    self.add_player_memory(memory_type="objective_completed", turn=0, content={"summary": f"Objective '{obj_desc}' was completed."}, sentiment_impact=0)
                else:
                    self.add_player_memory(memory_type="objective_completed", turn=0, content={"summary": f"Objective '{obj_desc}' concluded with stage '{stage_desc_for_memory}'."}, sentiment_impact=0)
                    if DEBUG_LOGS:
                        print(f"[DEBUG] Player {self.name} completed objective: {obj_desc} (Stage: {stage_desc_for_memory if by_stage else 'N/A'})")

            link_info = None
            current_stage = self.get_current_stage_for_objective(objective_id)
            if current_stage and "linked_to_objective_completion" in current_stage:
                link_info = current_stage["linked_to_objective_completion"]
            elif "linked_to_objective_completion" in obj:
                link_info = obj["linked_to_objective_completion"]

            if link_info:
                target_objective_id = None
                specific_next_stage_id = None

                if isinstance(link_info, str): 
                    target_objective_id = link_info
                elif isinstance(link_info, dict): 
                    target_objective_id = link_info.get("id")
                    specific_next_stage_id = link_info.get("stage_to_advance_to")

                if target_objective_id:
                    target_objective = self.get_objective_by_id(target_objective_id)
                    if target_objective:
                        target_obj_desc = target_objective.get('description', 'Unnamed Linked Objective')
                        if not target_objective.get("active", False) and not target_objective.get("completed", False) :
                            if DEBUG_LOGS:
                                print(f"[DEBUG] Linking: Activating objective '{target_obj_desc}' due to completion of '{obj_desc}'.")
                            self.activate_objective(target_objective_id) 
                            if specific_next_stage_id and target_objective.get("current_stage_id") != specific_next_stage_id :
                                if DEBUG_LOGS:
                                    print(f"[DEBUG] Linking: Advancing newly activated objective '{target_obj_desc}' to specific stage '{specific_next_stage_id}'.")
                                self.advance_objective_stage(target_objective_id, specific_next_stage_id)
                            if self.is_player:
                                self.add_player_memory(memory_type="objective_linked", turn=0, content={"summary": f"Completing '{obj_desc}' has opened up new paths regarding '{target_obj_desc}'."}, sentiment_impact=0)
                        
                        elif target_objective.get("active", False) and not target_objective.get("completed", False):
                            if specific_next_stage_id:
                                if DEBUG_LOGS:
                                    print(f"[DEBUG] Linking: Advancing active objective '{target_obj_desc}' to specific stage '{specific_next_stage_id}' due to '{obj_desc}'.")
                                if self.advance_objective_stage(target_objective_id, specific_next_stage_id):
                                     if self.is_player:
                                        self.add_player_memory(memory_type="objective_linked", turn=0, content={"summary": f"Progress on '{obj_desc}' has further developed your understanding of '{target_obj_desc}'."}, sentiment_impact=0)
                                elif DEBUG_LOGS:
                                    print(f"[DEBUG] Linking: Failed to advance '{target_obj_desc}' to stage '{specific_next_stage_id}'.")
                            else:
                                current_target_stage = self.get_current_stage_for_objective(target_objective_id)
                                if current_target_stage and current_target_stage.get("next_stages"):
                                    potential_next_ids = current_target_stage["next_stages"]
                                    if isinstance(potential_next_ids, dict) and potential_next_ids:
                                        auto_next_stage_id = next(iter(potential_next_ids.values()))
                                        if DEBUG_LOGS:
                                            print(f"[DEBUG] Linking: Attempting generic advance for active objective '{target_obj_desc}' to its next stage '{auto_next_stage_id}' due to '{obj_desc}'.")
                                        if self.advance_objective_stage(target_objective_id, auto_next_stage_id):
                                            if self.is_player:
                                                self.add_player_memory(memory_type="objective_linked", turn=0, content={"summary": f"Progress on '{obj_desc}' has influenced your approach to '{target_obj_desc}'."}, sentiment_impact=0)
                                    elif isinstance(potential_next_ids, list) and potential_next_ids:
                                         auto_next_stage_id = potential_next_ids[0]
                                         if DEBUG_LOGS:
                                             print(f"[DEBUG] Linking: Attempting generic advance for active objective '{target_obj_desc}' to its next stage '{auto_next_stage_id}' due to '{obj_desc}'.")
                                         if self.advance_objective_stage(target_objective_id, auto_next_stage_id):
                                            if self.is_player:
                                                self.add_player_memory(memory_type="objective_linked", turn=0, content={"summary": f"Progress on '{obj_desc}' has influenced your approach to '{target_obj_desc}'."}, sentiment_impact=0)
                                    else:
                                        if DEBUG_LOGS:
                                            print(f"[DEBUG] Linking: Objective '{target_obj_desc}' is active, but current stage has no defined 'next_stages' for generic advance.")
                                else:
                                    if DEBUG_LOGS:
                                        print(f"[DEBUG] Linking: Objective '{target_obj_desc}' is active, but current stage or its 'next_stages' are not clearly defined for generic advance.")
            return True
        return False

    def activate_objective(self, objective_id, set_stage_id=None):
        obj = self.get_objective_by_id(objective_id)
        if obj:
            obj["active"] = True
            obj["completed"] = False  

            initial_stage_id_to_set = None
            if set_stage_id: 
                if any(s.get("stage_id") == set_stage_id for s in obj.get("stages", [])):
                    initial_stage_id_to_set = set_stage_id
                else:
                    if DEBUG_LOGS:
                        print(f"[DEBUG] Warning: Requested stage_id '{set_stage_id}' for activating objective '{objective_id}' not found. Defaulting to first stage.")

            if not initial_stage_id_to_set: 
                if obj.get("stages") and obj["stages"][0].get("stage_id"):
                    initial_stage_id_to_set = obj["stages"][0].get("stage_id")
                else: 
                    obj["stages"] = [{"stage_id": "default", "description": "Objective activated.", "is_current_stage": True}]
                    initial_stage_id_to_set = "default"
            
            obj["current_stage_id"] = initial_stage_id_to_set
            for stage in obj.get("stages", []):
                stage["is_current_stage"] = (stage.get("stage_id") == initial_stage_id_to_set)
            
            current_stage_desc = self.get_current_stage_for_objective(objective_id).get('description', 'initial stage')
            if self.is_player:
                self.add_player_memory(memory_type="objective_activated", turn=0, content={"summary": f"New objective active or re-activated: '{obj.get('description', 'Unnamed Objective')}' (Current stage: '{current_stage_desc}')."}, sentiment_impact=0)
            if DEBUG_LOGS:
                print(f"[DEBUG] Player {self.name} activated objective: {obj.get('description')} - now at stage '{current_stage_desc}'")
            return True
        return False

    def check_skill(self, skill_name: str, difficulty_threshold: int = 1) -> bool:
        """
        Checks if the character succeeds at a skill check.
        Rolls a d6, adds skill value, compares to (difficulty_threshold + 3).
        """
        skill_value = self.skills.get(skill_name, 0)
        d6_roll = random.randint(1, 6)
        
        # Formula from prompt: (skill + roll) >= (threshold + 3)
        target_number = difficulty_threshold + 3
        success = (skill_value + d6_roll) >= target_number
        
        # Debug message as specified in prompt
        if DEBUG_LOGS:
            print(f"[Skill Check] {self.name} attempting {skill_name} (Value: {skill_value}, Roll: {d6_roll}, Threshold: {difficulty_threshold}): {'Success' if success else 'Failure'}")
        return success
