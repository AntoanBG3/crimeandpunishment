# gemini_interactions.py
import google.generativeai as genai
import os
import json

# --- Self-contained API Configuration Constants ---
API_CONFIG_FILE = "gemini_config.json"
GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
DEFAULT_GEMINI_MODEL_NAME = 'gemini-2.0-flash'

from .game_config import Colors

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
                    # Return just the key, model preference is handled separately now
                    return config.get("gemini_api_key")
        except Exception as e:
            self._log_message(f"Could not load API key from {API_CONFIG_FILE}: {e}", Colors.RED)
        return None

    def save_api_key_to_file(self, api_key):
        try:
            # When saving, also save the currently chosen model name for persistence
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
            model_instance = genai.GenerativeModel(model_to_use) # Use the passed model_to_use
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
                self.chosen_model_name = model_to_use # Confirm the successfully validated model
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
        # Using model IDs provided by the user
        models_map = {
            "1": {"name": "Gemini 1.5 Flash", "id": "gemini-1.5-flash-latest"},
            "2": {"name": "Gemini 1.5 Pro", "id": "gemini-1.5-pro-latest"},
            "3": {"name": "Gemini 2.0 Flash (Default)", "id": DEFAULT_GEMINI_MODEL_NAME},
            "4": {"name": "Gemini 2.5 Flash", "id": "gemini-2.5-flash-preview-04-17"}, # User-provided ID
            "5": {"name": "Gemini 2.5 Pro", "id": "gemini-2.5-pro-preview-05-06"},   # User-provided ID
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
        # Attempt to load preferred model from config if available with a key
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
                    # Proceed as if file didn't have a valid key or model
            else:
                self._log_message(f"Config file '{API_CONFIG_FILE}' not found.", Colors.DIM)

        if key_to_try:
            try: # Test genai.configure() first
                genai.configure(api_key=key_to_try)
                self._log_message(f"genai.configure() successful with key from {key_source}.", Colors.GREEN)
                
                # If key from env, ask for model. If key from file, use preferred_model_from_config then try setup.
                model_to_attempt_first = preferred_model_from_config if key_source == API_CONFIG_FILE else self._ask_for_model_selection()

                if self._attempt_api_setup(key_to_try, key_source, model_to_attempt_first):
                    # If the key was from file, but the model selected by user (if asked) is different from file's pref,
                    # or if user selected a non-default model with ENV key, save choice.
                    if key_source == "user input" or self.chosen_model_name != preferred_model_from_config: # This condition needs review for saving
                         # Handled by asking to save after successful manual input or if model changed.
                         pass # Saving is handled after successful manual input / validation.
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
                # Check for block reason in prompt_feedback
                if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                    block_reason_str = f" (Reason: {response.prompt_feedback.block_reason})"
                # Check for finish reason in candidates if text is empty
                elif hasattr(response, 'candidates') and len(response.candidates) > 0 and hasattr(response.candidates[0], 'finish_reason'):
                    finish_reason = response.candidates[0].finish_reason
                    # FINISH_REASON_STOP (1) is normal. Other reasons (SAFETY, RECITATION, OTHER, etc.) are issues.
                    if finish_reason != 1: # Assuming 1 is FINISH_REASON_STOP
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
            # Look for block reason in the exception response if available (some errors wrap the response)
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback') and hasattr(e.response.prompt_feedback, 'block_reason'):
                block_reason = e.response.prompt_feedback.block_reason
            
            if block_reason:
                self._log_message(f"Blocked due to: {block_reason}", Colors.YELLOW)
                return f"(OOC: My response was blocked: {block_reason})"
            
            if hasattr(e, 'grpc_status_code') and e.grpc_status_code == 7: 
                 return f"(OOC: API key error - Permission Denied. My thoughts are muddled.)"
            return f"(OOC: My thoughts are... muddled due to an error: {str(e)[:100]}...)"

    # --- Other get_... methods (get_npc_dialogue, etc.) remain unchanged ---
    # They will use self.model which is set by the updated configure method
    # with the user's chosen model name.
    # (The prompt construction inside these methods does not need to change for this request)

    def get_npc_dialogue(self, npc_character, player_character, player_dialogue,
                         current_location_name, current_time_period, relationship_status_text,
                         npc_memory_summary, player_apparent_state="normal",
                         player_notable_items_summary="nothing noteworthy",
                         recent_game_events_summary="No significant recent events.",
                         npc_objectives_summary="No specific objectives.",
                         player_objectives_summary="No specific objectives."):
        conversation_context = npc_character.get_formatted_history(player_character.name)
        situation_summary = (
            f"You, {npc_character.name} (current internal state/mood: '{npc_character.apparent_state}', pursuing: {npc_objectives_summary}), "
            f"are in {current_location_name} during the {current_time_period}. "
            f"The player, {player_character.name} (appearing '{player_apparent_state}', pursuing: {player_objectives_summary}), "
            f"{player_notable_items_summary}. "
            f"Your relationship with {player_character.name} is '{relationship_status_text}'. "
            f"You recall: {npc_memory_summary}. "
            f"Key recent events in the world: {recent_game_events_summary}."
        )

        player_state_consideration = f"""
        You should also consider the player's current apparent state: '{player_apparent_state}'.
        If this state is unusual (e.g., not 'normal', 'thoughtful', 'contemplative'), your response should subtly acknowledge or react to it, in a way that is consistent with your persona and your relationship with the player.
        For example, if the player is 'feverish', you might express concern or keep your distance. If they are 'agitated', you might be more cautious or try to calm them. If they are 'slightly drunk', you might dismiss them or find them amusing.
        This reaction should be woven into your dialogue, not necessarily a separate statement, unless a direct comment is highly in character.
        Do not overdo this; not every unusual state needs a strong reaction every time, but it should be a possibility.
        """

        player_items_consideration = f"""
        The player is also carrying these notable items: '{player_notable_items_summary}'.
        If any of these items are particularly striking, unusual for the player to carry, or relevant to your knowledge or suspicions (e.g., an axe, a bloodied item, a sacred symbol in an unexpected context), your dialogue should reflect your awareness of them.
        Your reaction could range from subtle curiosity, suspicion, concern, fear, or even a direct comment, depending on your personality, the item, and the situation.
        For instance, if the player is carrying 'Raskolnikov's axe', a character like Porfiry might make an indirect or probing remark, while Sonya might show distress if she saw a 'bloodied rag'.
        This awareness should be naturally integrated into your response. Do not simply list the items you see.
        """

        npc_objective_consideration = f"""
        Consider your own current objectives and your progress on them: '{npc_objectives_summary}'.
        Your current dialogue, tone, and focus should be influenced by how you are feeling about these objectives and your current stage in achieving them.
        For example, if you are close to completing an important objective, you might sound more confident or focused. If you are frustrated by a lack of progress on a key stage, this might color your words or make you less patient.
        Let this internal state subtly guide your responses.
        """
        sanitized_player_dialogue = player_dialogue.replace('"', '\\"')

        prompt = f"""
        **Roleplay Mandate: Embody {npc_character.name} from Dostoevsky's "Crime and Punishment" with utmost fidelity.**
        **Your Persona, {npc_character.name}:**
        {npc_character.persona}
        **Current Detailed Situation:**
        {situation_summary}
        {player_state_consideration}
        {player_items_consideration}
        {npc_objective_consideration}
        **Recent Conversation History with {player_character.name} (most recent last):**
        ---
        {conversation_context if conversation_context else "No prior conversation in this session."}
        ---
        **Player's Action:** {player_character.name} says to you: "{sanitized_player_dialogue}"
        **Your Task: Generate {npc_character.name}'s spoken response.**
        **Response Guidelines (Strict Adherence Required):**
        1.  **Authenticity.**
        2.  **Conciseness & Impact.**
        3.  **Contextual Reaction.** (This includes reacting to the player's words, the situation, and their apparent state as described above).
        4.  **Dostoevskian Tone.**
        5.  **No OOC or Meta-Commentary.**
        6.  **Dialogue Only.**
        7.  **Handling Nonsense.**
        Respond now as {npc_character.name}:
        """
        ai_text = self._generate_content_with_fallback(prompt, f"NPC dialogue for {npc_character.name}")

        # Always add player's dialogue to history
        npc_character.add_to_history(player_character.name, player_character.name, player_dialogue)
        player_character.add_to_history(npc_character.name, player_character.name, player_dialogue)

        if not ai_text.startswith("(OOC:"):
            # Clean/Normalize ai_text
            processed_ai_text = ai_text.replace('\\"', '"')

            # Strip one layer of surrounding quotes if present
            if len(processed_ai_text) >= 2 and processed_ai_text.startswith('"') and processed_ai_text.endswith('"'):
                processed_ai_text = processed_ai_text[1:-1]

            final_ai_text = processed_ai_text

            # Use cleaned text for NPC's part of history and return
            npc_character.add_to_history(player_character.name, npc_character.name, final_ai_text)
            player_character.add_to_history(npc_character.name, npc_character.name, final_ai_text)
            return final_ai_text
        else:
            # For OOC messages, still return the OOC message, player history already added
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
        prompt = f"""
        **Task: Simulate brief, ambient, Dostoevskian NPC-to-NPC interaction (1-3 lines).**
        **Setting:** {location_name}, {game_time_period}.
        **Characters:** {npc1.name} (appears {npc1.apparent_state}, persona: {npc1.persona[:150]}..., objectives: {npc1_objectives_summary}) & {npc2.name} (appears {npc2.apparent_state}, persona: {npc2.persona[:150]}..., objectives: {npc2_objectives_summary}).
        **Guidelines:**
        - Interaction should be in-character, reflecting their personas, current states, and objectives.
        - Avoid direct player involvement or addressing the player. This is an ambient exchange.
        - Maintain a Dostoevskian tone appropriate for "Crime and Punishment".
        - Format:
          {npc1.name}: [Their dialogue line 1]
          {npc2.name}: [Their dialogue line 1, responding to NPC1 or initiating]
          (Optional {npc1.name}: [Their dialogue line 2, responding to NPC2])
        - The conversation might also touch upon local gossip or a rumor. If so, make the rumor distinct or have one NPC explicitly share a piece of news or gossip they've heard.
        **Example of incorporating a rumor (do not use this specific rumor):**
        NPC1: The price of bread is scandalous, isn't it?
        NPC2: It is. And did you hear about that student, the one involved in that dreadful business with the pawnbroker? They say he's been seen lurking near the Haymarket, looking like a ghost...
        NPC1: Hush now, it's not wise to speak of such things.
        **Output:** Generate only the dialogue lines as specified.
        Generate the interaction now:
        """
        return self._generate_content_with_fallback(prompt, f"NPC-to-NPC interaction between {npc1.name} and {npc2.name}")

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
        **Guidelines:** In-character, Dostoevskian, varied content, subtle re:notoriety, plausible, concise, output only rumor.
        Generate rumor from {npc_obj.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"rumor from {npc_obj.name}")

    def get_newspaper_article_snippet(self, game_day, key_events_occurred_summary,
                                      relevant_themes_for_raskolnikov_summary, city_mood="tense and anxious"):
        prompt = f"""
        **Task: Generate short St. Petersburg newspaper snippet (2-4 sentences).**
        **Context:** Day {game_day}. Events: {key_events_occurred_summary}. Themes: {relevant_themes_for_raskolnikov_summary}. Mood: {city_mood}.
        **Guidelines:** Content (investigation, social conditions, philosophies, news, subtle allusions), 19th-C style, concise, output snippet.
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

    def get_npc_dialogue_persuasion_attempt(self, npc_character, player_character, player_persuasive_statement, 
                                            current_location_name, current_time_period, relationship_status_text, 
                                            npc_memory_summary, player_apparent_state, 
                                            player_notable_items_summary, recent_game_events_summary, 
                                            npc_objectives_summary, player_objectives_summary, 
                                            persuasion_skill_check_result_text):
        conversation_context = npc_character.get_formatted_history(player_character.name)
        situation_summary = (
            f"You, {npc_character.name} (current internal state/mood: '{npc_character.apparent_state}', pursuing: {npc_objectives_summary}), "
            f"are in {current_location_name} during the {current_time_period}. "
            f"The player, {player_character.name} (appearing '{player_apparent_state}', pursuing: {player_objectives_summary}), "
            f"{player_notable_items_summary}. "
            f"Your relationship with {player_character.name} is '{relationship_status_text}'. "
            f"You recall: {npc_memory_summary}. "
            f"Key recent events in the world: {recent_game_events_summary}."
        )

        player_state_persuasion_consideration = f"""
        Additionally, consider the player's current apparent state: '{player_apparent_state}' when forming your response to their persuasion attempt.
        An unusual state (e.g., 'agitated', 'feverish', 'paranoid', 'slightly drunk') might make you more or less receptive, or react in a specific way (e.g., wary, dismissive, concerned) to their attempt to persuade you.
        Integrate this consideration naturally into your dialogue.
        """

        player_items_persuasion_consideration = f"""
        Furthermore, consider the notable items the player is carrying: '{player_notable_items_summary}'.
        The presence of certain items (e.g., a weapon, an item of evidence, something out of place) might influence your trust, suspicion, or overall reaction to their persuasion attempt.
        Let this awareness subtly shape your response.
        """

        npc_objective_persuasion_consideration = f"""
        Your current progress on your own objectives ('{npc_objectives_summary}') should also heavily influence your response to this persuasion attempt.
        If their attempt aligns with or hinders your goals, or if your current objective stage makes you more or less receptive, reflect this in your dialogue.
        """

        prompt = f"""
        **Roleplay Mandate: Embody {npc_character.name} from Dostoevsky's "Crime and Punishment" with utmost fidelity.**
        **Your Persona, {npc_character.name}:**
        {npc_character.persona}
        **Current Detailed Situation:**
        {situation_summary}
        {player_state_persuasion_consideration}
        {player_items_persuasion_consideration}
        {npc_objective_persuasion_consideration}
        **Recent Conversation History with {player_character.name} (most recent last):**
        ---
        {conversation_context if conversation_context else "No prior conversation in this session."}
        ---
        **Player's Persuasion Attempt:**
        {player_character.name} is trying to persuade you, {npc_character.name}, about the following: "{player_persuasive_statement}"
        This persuasion attempt was a {persuasion_skill_check_result_text}.

        **Your Task (as {npc_character.name}):**
        Respond to this persuasion attempt.
        - Your reaction to the persuasion should also be influenced by the player's apparent state, as noted above.
        - If the persuasion was a SUCCESS (e.g., "SUCCESS due to their skillful argument", "CRITICAL SUCCESS, they are very convincing"): You should seem noticeably swayed, convinced, more agreeable, or willing to reveal something (if appropriate to your persona and the statement). Your dialogue should reflect this change of heart or willingness.
        - If the persuasion was a FAILURE (e.g., "FAILURE despite their efforts", "CRITICAL FAILURE, the attempt was clumsy and offensive"): You should resist the persuasion. You might become annoyed, suspicious, dismissive, reiterate your current stance more firmly, or even subtly mock the attempt, depending on your persona.
        - Your response should still be in character, concise, and in Dostoevskian tone.
        - DO NOT explicitly say "The persuasion succeeded" or "The persuasion failed." Show it through your dialogue.
        - DO NOT use parenthetical remarks like (He seems hesitant) or similar stage directions. Your response is dialogue only.

        Respond now as {npc_character.name}:
        """
        ai_text = self._generate_content_with_fallback(prompt, f"NPC persuasion response for {npc_character.name}")
        
        # Add to history (persuasion attempt is also a form of dialogue)
        if not ai_text.startswith("(OOC:"):
            npc_character.add_to_history(player_character.name, player_character.name, f"(Attempting to persuade) {player_persuasive_statement}")
            npc_character.add_to_history(player_character.name, npc_character.name, ai_text)
            player_character.add_to_history(npc_character.name, player_character.name, f"(My persuasive attempt) {player_persuasive_statement}")
            player_character.add_to_history(npc_character.name, npc_character.name, ai_text)
        return ai_text

    def get_enhanced_observation(self, character_obj, target_name, target_category, base_description, skill_check_context):
        prompt = f"""
        **Roleplay Mandate: Provide a subtle, insightful observation for {character_obj.name}, reflecting a successful Observation skill check.**
        **Character Making Observation:** {character_obj.name} (State: {character_obj.apparent_state})
        **Target of Observation:** '{target_name}' (Category: {target_category})
        **Base Information Already Known/Visible:** {base_description}
        **Specific Skill Check Context from Game:** {skill_check_context}

        **Your Task:**
        Generate a brief (1-2 sentences) additional detail that {character_obj.name} notices due to their keen observation. This detail should NOT be obvious and should provide a deeper understanding, hint, or nuance related to the target. It should feel like a reward for a successful skill check.
        - If observing a *person*, focus on subtle body language, a faint scent, an almost hidden object on them, a flicker of emotion they try to hide.
        - If observing an *item*, focus on a tiny inscription, wear patterns indicating unusual use, a faint smell, a hidden compartment, its true material or age if disguised.
        - If observing *scenery*, focus on something out of place, a sign of recent passage, a hidden vantage point, an unusual silence or sound.

        **Response Guidelines:**
        1.  **Subtlety is Key:** Avoid revealing major secrets directly. Hint, imply, suggest.
        2.  **Dostoevskian Tone:** Maintain the game's atmosphere.
        3.  **Concise:** 1-2 sentences.
        4.  **Direct Observation:** Output only the observed detail, not {character_obj.name}'s thoughts about it, unless the thought *is* the observation (e.g., "It strikes you that the stain is much fresher than the surrounding grime.").
        5.  **No OOC or Meta-Commentary.**

        Generate the enhanced observation now:
        """
        return self._generate_content_with_fallback(prompt, f"enhanced observation of {target_name}")

    def get_street_life_event_description(self, location_name, time_period, player_character_context="present in the area"):
        prompt = f"""
        **Task: Generate a brief, atmospheric 'street life' event (1-2 sentences) for St. Petersburg.**
        **Setting:** {location_name}, {time_period}.
        **Context:** The player character ({player_character_context}) is present but not directly involved.
        **Examples (do not repeat these verbatim):**
        - A ragged beggar insistently pleads with a well-dressed passerby, only to be scornfully ignored.
        - Two market vendors shout loudly at each other over the price of radishes, attracting a small crowd.
        - A stray dog, ribs showing, darts through the crowd, snatching a dropped piece of bread.
        - Children's laughter echoes briefly from a nearby alleyway before being swallowed by the city's drone.
        - A lone musician plays a mournful tune on a battered accordion, his eyes closed.
        **Guidelines:**
        - Evocative and Dostoevskian in tone.
        - Focus on sensory details or brief human interactions.
        - Should *not* require player interaction or be plot-critical. Purely atmospheric.
        - Output only the 1-2 sentence description of the event.
        Generate the street life event description now:
        """
        return self._generate_content_with_fallback(prompt, f"street life event in {location_name}")