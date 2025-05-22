# gemini_interactions.py
import google.generativeai as genai
import os
import json
from game_config import API_CONFIG_FILE, GEMINI_MODEL_NAME as DEFAULT_GEMINI_MODEL_NAME, Colors, GEMINI_API_KEY_ENV_VAR

class GeminiAPI:
    def __init__(self):
        self.model = None
        self.chosen_model_name = DEFAULT_GEMINI_MODEL_NAME # Initialize with default
        self._print_color_func = lambda text, color, end="\n": print(f"{color}{text}{Colors.RESET}", end=end)
        self._input_color_func = lambda prompt, color: input(f"{color}{prompt}{Colors.RESET}")

    def _log_message(self, text, color, end="\n"):
        if hasattr(self, '_print_color_func') and callable(self._print_color_func):
            self._print_color_func(text, color, end=end)
        else:
            print(f"{text}")

    def load_api_key_from_file(self):
        try:
            if os.path.exists(API_CONFIG_FILE):
                with open(API_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get("gemini_api_key")
        except Exception as e:
            self._log_message(f"Could not load API key from {API_CONFIG_FILE}: {e}", Colors.RED)
        return None

    def save_api_key_to_file(self, api_key):
        try:
            with open(API_CONFIG_FILE, 'w') as f:
                json.dump({"gemini_api_key": api_key, "chosen_model_name": self.chosen_model_name}, f)
            self._log_message(f"API key and chosen model ({self.chosen_model_name}) saved to {API_CONFIG_FILE}.", Colors.MAGENTA)
        except Exception as e:
            self._log_message(f"Could not save API key/model to {API_CONFIG_FILE}: {e}", Colors.RED)

    def _rename_invalid_config_file(self, config_file_path, suffix="invalid_key"):
        if os.path.exists(config_file_path):
            try:
                invalid_file_name = config_file_path + f".{suffix}"
                os.rename(config_file_path, invalid_file_name)
                self._print_color_func(f"Renamed potentially problematic {config_file_path} to {invalid_file_name}.", Colors.YELLOW)
            except OSError as ose:
                self._print_color_func(f"Could not rename {config_file_path}: {ose}", Colors.YELLOW)

    def _attempt_api_setup(self, api_key, source, model_to_use):
        if not api_key:
            self._log_message(f"Internal: _attempt_api_setup called with no API key from {source}.", Colors.RED)
            self.model = None
            return False
            
        try:
            genai.configure(api_key=api_key)
        except Exception as e_config:
            self._print_color_func(f"Error configuring Gemini API (genai.configure using key from {source}): {e_config}", Colors.RED)
            self.model = None
            return False

        try:
            model_instance = genai.GenerativeModel(model_to_use) 
        except Exception as model_e:
            self._print_color_func(f"Error instantiating Gemini model '{model_to_use}' (key from {source}): {model_e}", Colors.RED)
            self._print_color_func(f"The API key might be valid, but there's an issue with model '{model_to_use}' (e.g., name, access permissions).", Colors.YELLOW)
            self.model = None
            return False

        self._print_color_func(f"Verifying API key from {source} with model '{model_to_use}'...", Colors.MAGENTA)
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            test_response = model_instance.generate_content(
                "Respond with only the word 'test' if this works.",
                generation_config=genai.types.GenerationConfig(candidate_count=1, max_output_tokens=5),
                safety_settings=safety_settings
            )

            if hasattr(test_response, 'text') and 'test' in test_response.text.lower():
                self._print_color_func(f"API key from {source} verified successfully for model '{model_to_use}'.", Colors.GREEN)
                self.model = model_instance
                self.chosen_model_name = model_to_use 
                return True
            else:
                feedback_text = "Unknown issue during verification."
                if hasattr(test_response, 'prompt_feedback') and hasattr(test_response.prompt_feedback, 'block_reason') and test_response.prompt_feedback.block_reason:
                    feedback_text = f"Blocked due to: {test_response.prompt_feedback.block_reason}."
                elif not hasattr(test_response, 'text') or not test_response.text:
                    feedback_text = "API key test call returned an empty or non-text response."
                else:
                    feedback_text = f"API key test call returned unexpected text: '{test_response.text[:50]}...'"
                self._print_color_func(f"API key verification with model '{model_to_use}' (key from {source}) failed: {feedback_text}", Colors.RED)
                self.model = None
                return False
        except Exception as e_test:
            self._print_color_func(f"Error during API key verification call (from {source}, model '{model_to_use}'): {e_test}", Colors.RED)
            error_str = str(e_test).lower()
            auth_keywords = [
                "api key not valid", "permission_denied", "authentication_failed", 
                "invalid api key", "credential is invalid", "unauthenticated", 
                "api_key_invalid", "user_location_invalid" 
            ]
            grpc_permission_denied = hasattr(e_test, 'grpc_status_code') and e_test.grpc_status_code == 7
            is_auth_error = grpc_permission_denied or any(keyword in error_str for keyword in auth_keywords)
            if is_auth_error:
                self._print_color_func(f"The API key from '{source}' appears invalid or lacks permissions for model '{model_to_use}'/region.", Colors.RED)
            else:
                self._print_color_func(f"Unexpected error during verification with model '{model_to_use}'.", Colors.YELLOW)
            self.model = None
            return False

    def _ask_for_model_selection(self):
        self._print_color_func("\nPlease select which Gemini model to use:", Colors.CYAN)
        models_map = {
            "1": {"name": "Gemini 1.5 Flash", "id": "gemini-1.5-flash-latest"},
            "2": {"name": "Gemini 1.5 Pro", "id": "gemini-1.5-pro-latest"},
            "3": {"name": "Gemini 2.0 Flash (Default)", "id": DEFAULT_GEMINI_MODEL_NAME},
            "4": {"name": "Gemini 2.5 Flash", "id": "gemini-2.5-flash-preview-04-17"}, 
            "5": {"name": "Gemini 2.5 Pro", "id": "gemini-2.5-pro-preview-05-06"},   
        }
        for key, model_info in models_map.items():
            self._print_color_func(f"{key}. {model_info['name']} (ID: {model_info['id']})", Colors.WHITE)
        
        while True:
            choice = self._input_color_func("Enter your choice (1-5, or press Enter for default): ", Colors.MAGENTA).strip()
            if not choice: 
                default_model_info = next(item for item in models_map.values() if item["id"] == DEFAULT_GEMINI_MODEL_NAME)
                self._print_color_func(f"Using default model: {default_model_info['name']}", Colors.YELLOW)
                return DEFAULT_GEMINI_MODEL_NAME
            if choice in models_map:
                self._print_color_func(f"You selected: {models_map[choice]['name']}", Colors.GREEN)
                return models_map[choice]['id']
            else:
                self._print_color_func("Invalid choice. Please enter a number from the list.", Colors.RED)


    def configure(self, print_func, input_func):
        self._print_color_func = print_func
        self._input_color_func = input_func
        self._print_color_func("\n--- Gemini API Key Configuration ---", Colors.MAGENTA)

        key_to_try = None
        key_source = None
        preferred_model_from_config = DEFAULT_GEMINI_MODEL_NAME 

        env_key = os.getenv(GEMINI_API_KEY_ENV_VAR)
        if env_key:
            self._log_message(f"Found API key in environment variable '{GEMINI_API_KEY_ENV_VAR}'.", Colors.YELLOW)
            key_to_try = env_key
            key_source = f"environment variable '{GEMINI_API_KEY_ENV_VAR}'"
        
        if not key_to_try:
            if os.path.exists(API_CONFIG_FILE):
                try:
                    with open(API_CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                        file_key_data = config.get("gemini_api_key")
                        if file_key_data:
                            self._log_message(f"Found API key in config file '{API_CONFIG_FILE}'.", Colors.YELLOW)
                            key_to_try = file_key_data
                            key_source = API_CONFIG_FILE
                            preferred_model_from_config = config.get("chosen_model_name", DEFAULT_GEMINI_MODEL_NAME)
                            if preferred_model_from_config != DEFAULT_GEMINI_MODEL_NAME:
                                 self._log_message(f"Loaded preferred model '{preferred_model_from_config}' from config.", Colors.YELLOW)
                except Exception as e:
                    self._log_message(f"Error reading config file {API_CONFIG_FILE}: {e}", Colors.YELLOW)
            else:
                self._log_message(f"Config file '{API_CONFIG_FILE}' not found.", Colors.DIM)

        if key_to_try:
            try: 
                genai.configure(api_key=key_to_try)
                self._log_message(f"genai.configure() successful with key from {key_source}.", Colors.GREEN)
                
                model_to_attempt_first = preferred_model_from_config if key_source == API_CONFIG_FILE else self._ask_for_model_selection()

                if self._attempt_api_setup(key_to_try, key_source, model_to_attempt_first):
                    if key_source == "user input" or self.chosen_model_name != preferred_model_from_config: 
                         pass 
                    return 
                elif key_source == API_CONFIG_FILE:
                    self._rename_invalid_config_file(API_CONFIG_FILE, f"failed_setup_with_{model_to_attempt_first.replace('/','_')}")
            
            except Exception as e_initial_config:
                self._print_color_func(f"Error initially configuring Gemini API with key from {key_source}: {e_initial_config}", Colors.RED)
                if key_source == API_CONFIG_FILE:
                     self._rename_invalid_config_file(API_CONFIG_FILE, "initial_config_error")
            
            self._print_color_func(f"API key from {key_source} (with model '{preferred_model_from_config if key_source == API_CONFIG_FILE else 'user choice'}') failed validation or setup.", Colors.YELLOW)

        while True:
            manual_api_key_input = self._input_color_func(
                f"Please enter your Gemini API key (or type 'skip' to use placeholder responses): ",
                Colors.MAGENTA
            ).strip()

            if not manual_api_key_input:
                self._print_color_func("No API key entered. Please provide a key or type 'skip'.", Colors.YELLOW)
                continue 

            if manual_api_key_input.lower() == 'skip':
                self._print_color_func("\nSkipping API key entry. Game will run with placeholder responses.", Colors.RED)
                self.model = None 
                return 
            
            try:
                genai.configure(api_key=manual_api_key_input)
                self._log_message(f"genai.configure() successful with manually entered key.", Colors.GREEN)
            except Exception as e_manual_initial_config:
                 self._print_color_func(f"Error initially configuring Gemini API with manually entered key: {e_manual_initial_config}", Colors.RED)
                 retry_choice = self._input_color_func("Invalid API key format or initial error. Try again? (y/n): ", Colors.YELLOW).strip().lower()
                 if retry_choice != 'y':
                     self._print_color_func("\nProceeding with placeholder responses.", Colors.RED)
                     self.model = None 
                     return
                 continue

            selected_model_id_manual = self._ask_for_model_selection()

            if self._attempt_api_setup(manual_api_key_input, "user input", selected_model_id_manual):
                save_choice = self._input_color_func(
                    f"Save this valid key and model ('{self.chosen_model_name}') to {API_CONFIG_FILE}? (y/n) (Not recommended if sharing project): ",
                    Colors.YELLOW
                ).strip().lower()
                if save_choice == 'y':
                    self.save_api_key_to_file(manual_api_key_input) 
                else:
                    self._print_color_func(f"API key and model choice not saved for future sessions.", Colors.YELLOW)
                return 

            self._print_color_func(f"The manually entered API key with model '{selected_model_id_manual}' failed validation.", Colors.RED)
            retry_choice = self._input_color_func("Try entering a different API key? (y/n): ", Colors.YELLOW).strip().lower()
            if retry_choice != 'y':
                self._print_color_func("\nProceeding with placeholder responses.", Colors.RED)
                self.model = None 
                return
    
    def _generate_content_with_fallback(self, prompt, error_message_context="generating content"):
        if not self.model:
            return f"(OOC: Gemini API not configured or key invalid. Cannot fulfill request for {error_message_context}.)"
        try:
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            response = self.model.generate_content(prompt, safety_settings=safety_settings)
            
            if not hasattr(response, 'text') or not response.text: 
                block_reason_str = ""
                if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                    block_reason_str = f" (Reason: {response.prompt_feedback.block_reason})"
                elif hasattr(response, 'candidates') and len(response.candidates) > 0 and hasattr(response.candidates[0], 'finish_reason'):
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason != 1: 
                         block_reason_str = f" (Finish Reason: {finish_reason})"
                
                refusal_phrases = ["cannot fulfill", "unable to provide", "cannot generate", "not able to create", "i am unable to"]
                if hasattr(response, 'text') and response.text and any(phrase in response.text.lower() for phrase in refusal_phrases):
                     self._log_message(f"Warning: Gemini returned a refusal-like response for {error_message_context}.{block_reason_str} Prompt: {prompt[:200]}...", Colors.YELLOW)
                     return f"(OOC: My thoughts on this are restricted at the moment.{block_reason_str})"

                self._log_message(f"Warning: Gemini returned an empty or non-text response for {error_message_context}.{block_reason_str} Model: {self.chosen_model_name}. Prompt: {prompt[:200]}...", Colors.YELLOW)
                return f"(OOC: My thoughts on this are unclear or restricted at the moment.{block_reason_str})"
            return response.text.strip()
        except Exception as e:
            self._log_message(f"Error calling Gemini API for {error_message_context} using model {self.chosen_model_name}: {e}", Colors.RED)
            block_reason = None
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback') and hasattr(e.response.prompt_feedback, 'block_reason'):
                block_reason = e.response.prompt_feedback.block_reason
            
            if block_reason:
                self._log_message(f"Blocked due to: {block_reason}", Colors.YELLOW)
                return f"(OOC: My response was blocked: {block_reason})"
            
            if hasattr(e, 'grpc_status_code') and e.grpc_status_code == 7: 
                 return f"(OOC: API key error - Permission Denied. My thoughts are muddled.)"
            return f"(OOC: My thoughts are... muddled due to an error: {str(e)[:100]}...)"


    def get_npc_dialogue(self, npc_character, player_character, player_dialogue,
                         current_location_name, current_time_period, relationship_status_text,
                         npc_memory_summary, player_apparent_state="normal",
                         player_notable_items_summary="nothing noteworthy",
                         recent_game_events_summary="No significant recent events.",
                         npc_objectives_summary="No specific objectives.",
                         player_objectives_summary="No specific objectives.",
                         all_npcs_in_location=None): 
        from character_module import get_relationship_description 
        conversation_context = npc_character.get_formatted_history(player_character.name)
        
        player_skills_text = f"Player Skills: Observation ({player_character.skills.get('Observation',0)}), Persuasion ({player_character.skills.get('Persuasion',0)})"

        present_npcs_info = []
        if all_npcs_in_location:
            for other_npc in all_npcs_in_location:
                if other_npc.name != npc_character.name and other_npc.name != player_character.name: 
                    relationship_score = npc_character.npc_relationships.get(other_npc.name)
                    if relationship_score is not None: 
                        relationship_desc = get_relationship_description(relationship_score)
                        present_npcs_info.append(f"{other_npc.name} (towards whom you feel {relationship_desc})")
        
        situation_summary = (
            f"You, {npc_character.name} (current internal state/mood: '{npc_character.apparent_state}', pursuing: {npc_objectives_summary}), "
            f"are in {current_location_name} during the {current_time_period}. "
            f"The player, {player_character.name} (appearing '{player_apparent_state}', pursuing: {player_objectives_summary}), "
            f"{player_notable_items_summary}. {player_skills_text}. " 
            f"Your relationship with {player_character.name} is '{relationship_status_text}'. "
            f"You recall: {npc_memory_summary}. "
            f"Key recent events in the world: {recent_game_events_summary}."
        )
        if present_npcs_info:
            situation_summary += f" Also present: {'; '.join(present_npcs_info)}."

        prompt = f"""
        **Roleplay Mandate: Embody {npc_character.name} from Dostoevsky's "Crime and Punishment" with utmost fidelity.**
        **Your Persona, {npc_character.name}:**
        {npc_character.persona}
        **Current Detailed Situation:**
        {situation_summary}
        **Recent Conversation History with {player_character.name} (most recent last):**
        ---
        {conversation_context if conversation_context else "No prior conversation in this session."}
        ---
        **Player's Action:** {player_character.name} says to you: "{player_dialogue}"
        **Your Task: Generate {npc_character.name}'s spoken response.**
        **Response Guidelines (Strict Adherence Required):**
        1.  **Authenticity & Conciseness:** Respond in character, keeping dialogue impactful and brief.
        2.  **Contextual Reaction:** Consider your feelings towards the player AND OTHERS PRESENT. If you dislike someone present, you might be more reserved or curt.
        3.  **Skill Influence (Occasional):**
            *   If the player's Persuasion skill is notably high (e.g., > 1) and the player's dialogue is an attempt to persuade or influence, you might *occasionally* make your response show this influence. Preface such a response with `[SKILL: Persuasion] `. Example: `[SKILL: Persuasion] Perhaps you have a point...`
            *   If the player's Observation skill is high (e.g., > 1), you might *occasionally* react as if they've made a keen observation you didn't expect. Preface such a response with `[SKILL: Observation] `. Example: `[SKILL: Observation] You notice that, do you? Astute.`
            *   Do NOT use these tags for every response. Use them sparingly and only when a skill logically applies to the player's dialogue and your reaction. Most responses should be normal dialogue.
        4.  **Dostoevskian Tone.**
        5.  **No OOC or Meta-Commentary.** Dialogue Only.
        Respond now as {npc_character.name}:
        """
        ai_text = self._generate_content_with_fallback(prompt, f"NPC dialogue for {npc_character.name}")
        if not ai_text.startswith("(OOC:"):
            npc_character.add_to_history(player_character.name, player_character.name, player_dialogue)
            npc_character.add_to_history(player_character.name, npc_character.name, ai_text)
            player_character.add_to_history(npc_character.name, player_character.name, player_dialogue)
            player_character.add_to_history(npc_character.name, npc_character.name, ai_text)
        return ai_text

    def get_player_reflection(self, player_character, current_location_name, current_time_period,
                              context_text, recent_interactions_summary="Nothing specific recently.",
                              inventory_highlights="You carry your usual burdens.",
                              active_objectives_summary="Your goals weigh on you."):
        prompt = f"""
        **Roleplay Mandate: Embody the internal thoughts of {player_character.name} from Dostoevsky's "Crime and Punishment".**
        **Your Persona, {player_character.name}:**
        {player_character.persona}
        **Current Situation:**
        * Location: {current_location_name}, Time: {current_time_period}, State: {player_character.apparent_state}
        * Carrying: {inventory_highlights}, Objectives: {active_objectives_summary}
        * Recent Interactions: {recent_interactions_summary}, Context: {context_text}
        **Your Task: Generate a brief, introspective inner thought (1-3 sentences).**
        **Reflection Guidelines (Strict Adherence Required):** Deeply Personal, Dostoevskian Style, First-Person, Contextual, Concise, No OOC, Output Only Thought.
        Generate {player_character.name}'s inner thought now:
        """
        return self._generate_content_with_fallback(prompt, f"player reflection for {player_character.name}")

    def get_atmospheric_details(self, player_character, location_name, time_period,
                                recent_event_summary=None, player_objective_focus=None):
        context = (f"{player_character.name} (state: {player_character.apparent_state}, preoccupied with: {player_objective_focus if player_objective_focus else 'usual thoughts'}) "
                   f"is in {location_name} during {time_period}. ")
        if recent_event_summary: context += f"Recently, {recent_event_summary}. "
        prompt = f"""
        **Task: Evoke Dostoevsky's St. Petersburg atmosphere via {player_character.name}'s perception.**
        **Context:** {context}
        **Instructions:** Describe subtle, psychologically resonant detail (1-2 sentences). Enhance mood, Dostoevskian tone. Sensory/Symbolic. Reflect internal state. Not a plot point. Output only description.
        Generate the atmospheric detail now:
        """
        return self._generate_content_with_fallback(prompt, "atmospheric details")

    def get_npc_to_npc_interaction(self, npc1, npc2, location_name, game_time_period,
                                   npc1_objectives_summary="their usual concerns",
                                   npc2_objectives_summary="their usual concerns"):
        from character_module import get_relationship_description 
        
        relationship_npc1_to_npc2_score = npc1.npc_relationships.get(npc2.name, 0)
        relationship_npc1_to_npc2_text = get_relationship_description(relationship_npc1_to_npc2_score)
        
        relationship_npc2_to_npc1_score = npc2.npc_relationships.get(npc1.name, 0)
        relationship_npc2_to_npc1_text = get_relationship_description(relationship_npc2_to_npc1_score)

        character_details = (
            f"{npc1.name} (appears '{npc1.apparent_state}', objectives: {npc1_objectives_summary}, "
            f"feels '{relationship_npc1_to_npc2_text}' towards {npc2.name}).\n"
            f"{npc2.name} (appears '{npc2.apparent_state}', objectives: {npc2_objectives_summary}, "
            f"feels '{relationship_npc2_to_npc1_text}' towards {npc1.name})."
        )

        prompt = f"""
        **Task: Simulate brief, ambient, Dostoevskian NPC-to-NPC interaction (1-3 lines).**
        **Setting:** {location_name}, {game_time_period}.
        **Characters & Their Feelings Towards Each Other:**
        {character_details}
        **Personas (for reference):**
        {npc1.name}: {npc1.persona}
        {npc2.name}: {npc2.persona}
        **Guidelines:** Interaction should be between {npc1.name} and {npc2.name}. Reflect their personas, states, and mutual feelings. Avoid player focus. Dostoevskian tone. Output only the dialogue/action.
        Generate the interaction now:
        """
        return self._generate_content_with_fallback(prompt, f"NPC-to-NPC interaction between {npc1.name} and {npc2.name}")

    def get_character_observation_detail(self, player_character, observed_npc, location_name, time_period, player_objectives_summary):
        """Generates a detailed observation of an NPC, influenced by player's Observation skill."""
        player_skills_summary = f"Player Skills: Observation ({player_character.skills.get('Observation', 0)})"
        
        prompt = f"""
        **Task: Describe {player_character.name}'s detailed observation of {observed_npc.name}.**
        **Context:**
        *   Player: {player_character.name} ({player_character.apparent_state}, Objectives: {player_objectives_summary})
        *   Observed NPC: {observed_npc.name} (appears '{observed_npc.apparent_state}')
        *   Location: {location_name}, Time: {time_period}
        *   {player_skills_summary}
        **Instructions:**
        1.  Generate a 1-2 sentence observation from {player_character.name}'s perspective.
        2.  If Player's Observation skill is high (e.g., > 1), the observation should be more insightful, revealing subtle details about {observed_npc.name}'s demeanor, appearance, or unspoken intentions.
        3.  If Observation skill is low (0 or 1), provide a more general, surface-level observation.
        4.  Maintain a Dostoevskian tone. Focus on psychological nuance.
        5.  Output only the observation. Do not include OOC or skill tags in the observation itself.
        Generate {player_character.name}'s observation of {observed_npc.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"detailed observation of {observed_npc.name} by {player_character.name}")

    def get_item_interaction_description(self, character, item_name, item_details, action_type="examine",
                                         location_name="an undisclosed location", time_period="an unknown time",
                                         target_details=None):
        prompt = f"""
        **Roleplay Mandate: Generate {character.name}'s internal, first-person Dostoevskian thought for item interaction.**
        **Context:** {character.name} ({character.apparent_state}) in {location_name} at {time_period}.
        **Item:** '{item_name}' ({item_details.get('description', 'No details')}). Action: {action_type}.
        Target: {target_details if target_details else "N/A"}.
        **Task: Describe {character.name}'s brief, evocative thought (1-2 sentences).**
        **Guidelines:** Psychologically resonant, first-person, sensory, concise, no OOC.
        Generate {character.name}'s thought/observation now:
        """
        return self._generate_content_with_fallback(prompt, f"item interaction with {item_name} by {character.name}")

    def get_dream_sequence(self, character_obj, recent_events_summary, current_objectives_summary, key_relationships_summary="No specific key relationships."):
        prompt = f"""
        **Task: Describe a symbolic, surreal, Dostoevskian dream for {character_obj.name}.**
        **Dreamer Profile:** {character_obj.name} ({character_obj.apparent_state}). Recent: {recent_events_summary}. Concerns: {current_objectives_summary}. Relationships: {key_relationships_summary}.
        **Guidelines:** Symbolic/surreal, Dostoevskian tone, vivid/fragmented imagery, emotional impact, concise (3-5 sentences), output only dream.
        Generate dream for {character_obj.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"{character_obj.name}'s dream sequence")

    def get_rumor_or_gossip(self, npc_obj, location_name, game_time_period, known_facts_about_crime_summary, player_notoriety_level, npc_relationship_with_player_text="neutral", npc_current_concerns="their usual worries"):
        prompt = f"""
        **Task: Generate brief, in-character Dostoevskian gossip/rumor (1-2 sentences) from {npc_obj.name}.**
        **Context:** {npc_obj.name} in {location_name} ({game_time_period}). Player relationship: {npc_relationship_with_player_text}. Concerns: {npc_current_concerns}.
        **Background:** Crime: {known_facts_about_crime_summary}. Player Notoriety: {player_notoriety_level}.
        **Guidelines:**
        1.  In-character ({npc_obj.name}), Dostoevskian tone.
        2.  Varied content: local happenings, character observations, philosophical musings, social commentary.
        3.  Subtle regarding player notoriety.
        4.  **Occasionally (approx. 20% chance), embed an actionable clue within the rumor.**
            *   The clue must be wrapped in tags like: `<CLUE>machine_friendly_clue_id</CLUE>`.
            *   The `machine_friendly_clue_id` should be a short, snake_case string (e.g., `mysterious_note_tavern`, `luzhin_secret_meeting`).
            *   The surrounding text should make the clue contextually understandable. Example: "Heard tell that Pyotr Petrovich has been seen conferring with unsavory types at the old docks. <CLUE>luzhin_dock_meeting</CLUE> What could a man of his standing be doing there?"
        5.  Plausible for the setting. Concise (1-3 sentences). Output only the rumor.
        Generate rumor from {npc_obj.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"rumor from {npc_obj.name}")

    def get_newspaper_article_snippet(self, game_day, key_events_occurred_summary,
                                      relevant_themes_for_raskolnikov_summary, city_mood="tense and anxious"):
        prompt = f"""
        **Task: Generate short St. Petersburg newspaper snippet (2-4 sentences) for Day {game_day}.**
        **Context:** Recent Events: {key_events_occurred_summary}. Player-Relevant Themes: {relevant_themes_for_raskolnikov_summary}. City Mood: {city_mood}.
        **Guidelines:**
        1.  Content: Reflect ongoing investigations, social conditions, philosophical debates, general city news, or subtle allusions to player/NPC actions.
        2.  Style: 19th-Century St. Petersburg journalistic tone (somewhat formal, possibly florid or moralizing).
        3.  **Occasionally (approx. 20% chance), embed an actionable clue within the article.**
            *   The clue must be wrapped in tags like: `<CLUE>machine_friendly_clue_id</CLUE>`.
            *   The `machine_friendly_clue_id` should be short and snake_case (e.g., `pawnbroker_missing_item`, `student_political_group_meeting`).
            *   The surrounding text should make the clue contextually understandable. Example: "...further inquiries into the Lizaveta Ivanovna murder have revealed a small, overlooked detail at the scene. <CLUE>pawnbroker_scene_detail</CLUE> Authorities are urging citizens with any information to come forward."
        4.  Concise. Output only the newspaper snippet.
        Generate newspaper snippet now:
        """
        return self._generate_content_with_fallback(prompt, "newspaper article snippet")

    def get_scenery_observation(self, character_obj, scenery_noun_phrase, location_name, time_period,
                                character_active_objectives_summary="their current thoughts"):
        prompt = f"""
        **Roleplay Mandate: Generate {character_obj.name}'s Dostoevskian observation of scenery.**
        **Context:** {character_obj.name} ({character_obj.apparent_state}) in {location_name} ({time_period}). Focus: '{scenery_noun_phrase}'. Preoccupations: {character_active_objectives_summary}.
        **Task: Generate brief, introspective observation (1-2 sentences).**
        **Guidelines:** Psychologically resonant, deeper meaning, first-person, concise, no OOC, output observation.
        Generate {character_obj.name}'s scenery observation now:
        """
        return self._generate_content_with_fallback(prompt, f"scenery observation of {scenery_noun_phrase}")

    def get_generated_text_document(self, document_type, author_persona_hint="an unknown person",
                                    recipient_persona_hint="the recipient", subject_matter="an important matter",
                                    desired_tone="neutral", key_info_to_include="some key details",
                                    length_sentences=3, purpose_of_document_in_game="To convey information."):
        prompt = f"""
        **Task: Generate text for a '{document_type}' in Dostoevsky's world.**
        **Specs:** Author: {author_persona_hint}. Recipient: {recipient_persona_hint}. Subject: {subject_matter}. Tone: {desired_tone}. Key Info: {key_info_to_include}. Length: {length_sentences} sentences. Style: 19th-C St. Petersburg. Purpose: {purpose_of_document_in_game}.
        **Guidelines:** Authentic voice, Dostoevskian flavor, convey info subtly, output only document text.
        Generate text for '{document_type}' now:
        """
        return self._generate_content_with_fallback(prompt, f"generated text for {document_type}")