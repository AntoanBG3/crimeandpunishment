# gemini_interactions.py
import google.generativeai as genai
import os
import json
from game_config import API_CONFIG_FILE, GEMINI_MODEL_NAME, Colors, GEMINI_API_KEY_ENV_VAR

class GeminiAPI:
    def __init__(self):
        self.model = None
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
            self._log_message(f"Could not load API key from {API_CONFIG_FILE}: {e}", Colors.RED if hasattr(Colors, 'RED') else "")
        return None

    def save_api_key_to_file(self, api_key):
        try:
            with open(API_CONFIG_FILE, 'w') as f:
                json.dump({"gemini_api_key": api_key}, f)
            self._log_message(f"API key saved to {API_CONFIG_FILE} for future use (less secure).", Colors.MAGENTA if hasattr(Colors, 'MAGENTA') else "")
        except Exception as e:
            self._log_message(f"Could not save API key to {API_CONFIG_FILE}: {e}", Colors.RED if hasattr(Colors, 'RED') else "")

    def configure(self, print_func, input_func):
        self._print_color_func = print_func
        self._input_color_func = input_func
        self._print_color_func("\n--- Gemini API Key Configuration ---", Colors.MAGENTA)
        api_key = os.getenv(GEMINI_API_KEY_ENV_VAR)
        source = f"environment variable '{GEMINI_API_KEY_ENV_VAR}'"
        if not api_key:
            self._log_message(f"API key not found in {source}. Trying {API_CONFIG_FILE}...", Colors.YELLOW)
            api_key = self.load_api_key_from_file()
            source = API_CONFIG_FILE
            if api_key: self._log_message(f"Loaded API key from {API_CONFIG_FILE}.", Colors.GREEN)
        if not api_key:
            self._log_message(f"API key not found in {API_CONFIG_FILE} either.", Colors.YELLOW)
            api_key_input = self._input_color_func(f"Please enter your Gemini API key (or set the '{GEMINI_API_KEY_ENV_VAR}' environment variable, or place in {API_CONFIG_FILE}): ", Colors.MAGENTA)
            api_key = api_key_input.strip() if api_key_input else None
            source = "user input"
        if not api_key:
            self._print_color_func("\nNo API key provided. Game will run with placeholder responses.", Colors.RED)
            self.model = None; return
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            self._print_color_func(f"\nGemini API configured successfully using key from {source} with model '{GEMINI_MODEL_NAME}'.", Colors.GREEN)
            if source == "user input":
                save_choice = self._input_color_func(f"Save key to {API_CONFIG_FILE}? (y/n) (Not recommended if sharing project): ", Colors.YELLOW).strip().lower()
                if save_choice == 'y': self.save_api_key_to_file(api_key)
                else: self._print_color_func(f"API key not saved. Set '{GEMINI_API_KEY_ENV_VAR}' for better security.", Colors.YELLOW)
        except Exception as e:
            self._print_color_func(f"Error configuring Gemini API with model '{GEMINI_MODEL_NAME}': {e}", Colors.RED)
            self._print_color_func(f"Please ensure key (from {source}) is correct and model is valid. Placeholder responses will be used.", Colors.YELLOW)
            self.model = None
            if source == API_CONFIG_FILE and os.path.exists(API_CONFIG_FILE):
                try:
                    invalid_file_name = API_CONFIG_FILE + ".invalid_key"
                    os.rename(API_CONFIG_FILE, invalid_file_name)
                    self._print_color_func(f"Renamed potentially invalid {API_CONFIG_FILE} to {invalid_file_name}.", Colors.YELLOW)
                except OSError as ose:
                    self._print_color_func(f"Could not rename {API_CONFIG_FILE}: {ose}", Colors.YELLOW)

    def _generate_content_with_fallback(self, prompt, error_message_context="generating content"):
        if not self.model:
            return f"(OOC: Gemini API not configured. Cannot fulfill request for {error_message_context}.)"
        try:
            response = self.model.generate_content(prompt)
            # Add basic check for empty or refusal-like responses
            if not response.text or "cannot fulfill" in response.text.lower() or "unable to provide" in response.text.lower():
                self._log_message(f"Warning: Gemini returned an empty or refusal-like response for {error_message_context}.", Colors.YELLOW)
                return f"(OOC: My thoughts on this are unclear or restricted at the moment.)"
            return response.text.strip()
        except Exception as e:
            self._log_message(f"Error calling Gemini API for {error_message_context}: {e}", Colors.RED)
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback') and e.response.prompt_feedback.block_reason:
                block_reason = e.response.prompt_feedback.block_reason
                self._log_message(f"Blocked due to: {block_reason}", Colors.YELLOW)
                return f"(OOC: My response was blocked: {block_reason})"
            return f"(OOC: My thoughts are... muddled due to an error.)"

    def get_npc_dialogue(self, npc_character, player_character, player_dialogue,
                         current_location_name, relationship_status, npc_memory_summary,
                         player_apparent_state="normal", player_notable_items_summary="nothing noteworthy"):
        conversation_context = npc_character.get_formatted_history(player_character.name)
        situation_summary = (
            f"You, {npc_character.name} (currently feeling/appearing {npc_character.apparent_state}), "
            f"are in {current_location_name}. "
            f"The player, {player_character.name}, appears to be in a '{player_apparent_state}' state "
            f"and {player_notable_items_summary}. "
            f"Your relationship with {player_character.name} is {relationship_status}. "
            f"{npc_memory_summary}"
        )
        prompt = f"""
        You are {npc_character.name}, a character from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {npc_character.persona}
        Current situation: {situation_summary}
        Recent conversation history with {player_character.name} (most recent last):
        ---
        {conversation_context}
        ---
        Now, {player_character.name} says to you: "{player_dialogue}"

        Respond concisely (1-3 sentences typically) and strictly in character as {npc_character.name}.
        Your response MUST reflect:
        1. Your core persona and psychological traits from the novel.
        2. The immediate situation: your location, your own state ('{npc_character.apparent_state}'), the player's apparent state ('{player_apparent_state}'), and what they are carrying ('{player_notable_items_summary}'). If these details are striking (e.g., player looks feverish, carries an axe), your reaction should be more pronounced but still in character (e.g., Porfiry might be probing, Sonya concerned, Svidrigailov cynically amused).
        3. Your existing relationship with and memories of the player.
        4. The ongoing conversation flow.
        Maintain the serious, introspective, and psychologically complex tone of Dostoevsky's "Crime and Punishment".
        Avoid modern colloquialisms. Your speech should be somewhat formal or characteristic of the 19th century.
        Do NOT break character. Do NOT use out-of-character remarks like (OOC) or explain your reasoning.
        Your response should be only the dialogue spoken by {npc_character.name}.
        If the player's input is nonsensical or very out of character for the setting, you may express confusion or dismissiveness appropriate to your persona.
        """
        ai_text = self._generate_content_with_fallback(prompt, f"NPC dialogue for {npc_character.name}")
        if not ai_text.startswith("(OOC:"): # Only add to history if it's not an error/OOC message
            npc_character.add_to_history(player_character.name, player_character.name, player_dialogue)
            npc_character.add_to_history(player_character.name, npc_character.name, ai_text)
            player_character.add_to_history(npc_character.name, player_character.name, player_dialogue)
            player_character.add_to_history(npc_character.name, npc_character.name, ai_text)
        return ai_text

    def get_player_reflection(self, player_character, current_location_name, context_text, time_period):
        prompt = f"""
        You are roleplaying as {player_character.name} from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {player_character.persona}
        You are currently in {current_location_name} during the {time_period}.
        Your apparent state is: {player_character.apparent_state}.
        Current context or preoccupation: {context_text}
        Consider your current situation, your surroundings, your emotional state ({player_character.apparent_state}), and your objectives or recent thoughts.

        Generate a brief, introspective inner thought or reflection (1-3 sentences) that {player_character.name} might have right now.
        This reflection should be deeply personal and psychological, consistent with Dostoevsky's style.
        It might touch upon guilt, paranoia, philosophical ponderings, observations about the city's oppressive atmosphere, or fleeting memories triggered by current context.
        Maintain the serious, introspective, and psychologically complex tone.
        The reflection should be from the first-person perspective of {player_character.name} (e.g., "I feel...", "This place...").
        Do NOT break character. Output only the thought.
        """
        return self._generate_content_with_fallback(prompt, f"player reflection for {player_character.name}")

    def get_atmospheric_details(self, player_character, location_name, time_period, recent_event_summary=None):
        context = f"{player_character.name} (current state: {player_character.apparent_state}) is in {location_name} during the {time_period}. "
        if recent_event_summary: context += f"Recently, {recent_event_summary}. "
        prompt = f"""
        Evoke the atmosphere of Dostoevsky's St. Petersburg, tailored to the character's perception.
        Context: {context}
        Describe a subtle, psychologically resonant atmospheric detail or a fleeting observation {player_character.name} might notice.
        This should be 1-2 concise sentences, enhancing the mood and aligning with the novel's oppressive, feverish, or introspective tone.
        Focus on sensory details (a sound, a smell, a visual detail, a feeling) or a brief, almost subconscious thought related to the environment.
        The detail should reflect {player_character.name}'s internal state ({player_character.apparent_state}) or the underlying tension of their situation.
        Do NOT make it a major plot point or an action. It's about mood and psychological texture.
        Output only the atmospheric description. Do not use quotation marks unless it's a direct thought like "This city..."
        Examples reflecting character state:
        - If Raskolnikov is feverish: "The oppressive heat of the afternoon seemed to leach the very will to act, each distant shout grating on raw nerves."
        - If Sonya is sorrowful: "A distant church bell tolled, each chime a somber echo of the city's endless grief."
        - If player is contemplative: "The way the gaslight caught the slick cobblestones made them seem like tears on the city's face."
        """
        return self._generate_content_with_fallback(prompt, "atmospheric details")


    def get_npc_to_npc_interaction(self, npc1, npc2, location_name, game_time_period):
        prompt = f"""
        Simulate a brief, ambient interaction (1-2 lines total) between two characters from Dostoevsky's "Crime and Punishment" who are in the same location.
        Location: {location_name}
        Time of day: {game_time_period}
        Character 1: {npc1.name} (appears {npc1.apparent_state})
        Persona 1: {npc1.persona}
        Recent history with Character 2 (if any): {npc1.get_formatted_history(npc2.name, limit=1)}
        Character 2: {npc2.name} (appears {npc2.apparent_state})
        Persona 2: {npc2.persona}
        Recent history with Character 1 (if any): {npc2.get_formatted_history(npc1.name, limit=1)}

        Generate a short, in-character exchange. It could be about the location, the time, a general observation, or a brief, almost unspoken acknowledgment.
        Their dialogue should reflect their personas and current apparent states.
        Do NOT have them discuss the player character unless it's extremely vague and natural.
        Maintain the serious, introspective, and psychologically complex tone.
        Format strictly as:
        {npc1.name}: [dialogue]
        {npc2.name}: [dialogue]
        OR if one is just observing the other, or a very brief non-verbal exchange:
        ({npc1.name} [e.g., glances at/avoids eye contact with/etc.] {npc2.name}, who [e.g., nods curtly/ignores them/etc.].)
        Keep it very brief and atmospheric.
        """
        return self._generate_content_with_fallback(prompt, f"NPC-to-NPC interaction between {npc1.name} and {npc2.name}")

    def get_item_interaction_description(self, character, item_name, item_details, action_type="examine"):
        prompt = f"""
        You are roleplaying as {character.name} (current state: {character.apparent_state}) from Dostoevsky's "Crime and Punishment".
        Your persona: {character.persona}
        You are interacting with an item: '{item_name}'.
        Item's base description: {item_details.get('description', 'No specific details.')}
        The action is: {action_type} (e.g., examine closely, take, drop, use on self, show to someone).

        Describe {character.name}'s brief, evocative thought, observation, or sensory detail related to this action and item, in 1-2 sentences from their first-person perspective.
        This should be deeply psychological and in line with Dostoevsky's style, reflecting the character's current mental state ({character.apparent_state}) and the item's potential significance or symbolism *to them*.
        Output only the character's thought/observation. Do not use quotation marks unless it's a very direct, short internal quote.
        """
        return self._generate_content_with_fallback(prompt, f"item interaction with {item_name} by {character.name}")

    # --- New AI Functions ---

    def get_dream_sequence(self, character_obj, recent_events_summary, current_objectives_summary):
        prompt = f"""
        You are describing a dream experienced by Rodion Raskolnikov, a character from Dostoevsky's "Crime and Punishment".
        He is currently feeling: {character_obj.apparent_state}.
        Some recent events or preoccupations might include: {recent_events_summary}.
        His current objectives or deep-seated concerns are: {current_objectives_summary}.

        Generate a short (3-5 sentences) description of a symbolic, surreal, and unsettling dream sequence.
        The dream should reflect his guilt, his philosophical theories about 'extraordinary men,' his poverty, his relationships (e.g., with Sonya, Dunya, Porfiry), or his fear and paranoia.
        Use vivid, fragmented imagery and maintain a Dostoevskian tone, heavy with psychological weight.
        The dream should feel like a product of a troubled, feverish mind.
        Focus on symbolism and emotional impact rather than a literal narrative.
        Output only the dream description.
        """
        return self._generate_content_with_fallback(prompt, "Raskolnikov's dream sequence")

    def get_rumor_or_gossip(self, npc_obj, location_name, known_facts_about_crime_summary, player_notoriety_level):
        prompt = f"""
        You are {npc_obj.name} ({npc_obj.apparent_state}), a character in 19th-century St. Petersburg, currently in {location_name}.
        Your persona: {npc_obj.persona}
        There has been a recent murder of an old pawnbroker and her sister. Publicly known details: {known_facts_about_crime_summary}.
        A young man, Raskolnikov (the player), has a notoriety level of {player_notoriety_level} (0=unknown, 1=seen acting oddly, 2=arouses suspicion, 3=definitely suspicious).

        Generate a brief, in-character snippet of gossip or a rumor (1-2 sentences) that you might share or have overheard.
        It could be about the crime itself, the general fear in the city, other daily struggles, a strange person you've seen, or something related to the atmosphere of St. Petersburg.
        Your rumor can be vague, slightly inaccurate, insightful, or even self-serving, fitting your personality.
        If Raskolnikov's notoriety is low (0-1), do NOT mention him directly or anything that clearly points to him.
        If his notoriety is higher (2-3), you might make a more pointed, though still perhaps deniable, observation if it fits your character (e.g., a suspicious student, strange comings and goings).
        Maintain a Dostoevskian tone.
        Output only the rumor/gossip.
        """
        return self._generate_content_with_fallback(prompt, f"rumor from {npc_obj.name}")

    def get_newspaper_article_snippet(self, game_day, key_events_occurred_summary, relevant_themes_for_raskolnikov_summary):
        prompt = f"""
        Generate a short St. Petersburg newspaper article snippet (2-4 sentences) for a publication like the 'St. Petersburg Chronicle'.
        It is currently Day {game_day} in the narrative timeline of "Crime and Punishment".
        Key public events that have occurred so far include: {key_events_occurred_summary}.
        Themes potentially being discussed or on people's minds (especially relevant to Raskolnikov's thoughts) include: {relevant_themes_for_raskolnikov_summary}.

        The article could be about:
        - The ongoing investigation into the pawnbroker's murder (progress, theories, police activity).
        - Social conditions in St. Petersburg (poverty, disease, alcoholism).
        - Philosophical debates on crime, morality, or new 'radical' ideas.
        - General city news or anxieties.

        Maintain a formal, somewhat dry, 19th-century journalistic style.
        The tone should be appropriate for a public newspaper of the era.
        Output only the article snippet.
        """
        return self._generate_content_with_fallback(prompt, "newspaper article snippet")

    def get_scenery_observation(self, character_obj, scenery_noun_phrase, location_name, time_period):
        prompt = f"""
        You are roleplaying as {character_obj.name} ({character_obj.apparent_state}) from Dostoevsky's "Crime and Punishment".
        You are in {location_name} during the {time_period}.
        You are looking more closely at: '{scenery_noun_phrase}'.

        Generate a brief, introspective, and Dostoevskian observation (1-2 sentences) about this specific piece of scenery from your first-person perspective.
        It should reflect your current mood ({character_obj.apparent_state}), your personality, and the general atmosphere of the novel (oppressive, symbolic, grimy, etc.).
        What deeper meaning or feeling does this mundane detail evoke in you?
        Output only the observation.
        """
        return self._generate_content_with_fallback(prompt, f"scenery observation of {scenery_noun_phrase}")

    def get_generated_text_document(self, document_type, author_persona_hint="an unknown person",
                                    recipient_persona_hint="the recipient", subject_matter="an important matter",
                                    desired_tone="neutral", key_info_to_include="some key details",
                                    length_sentences=3):
        prompt = f"""
        Generate the text for a '{document_type}'.
        Authored by: {author_persona_hint}.
        Intended for: {recipient_persona_hint}.
        Regarding: {subject_matter}.
        The desired tone is: {desired_tone}.
        It should subtly convey or include: {key_info_to_include}.
        The document should be approximately {length_sentences} sentences long and written in a style appropriate for 19th-century St. Petersburg.
        Output only the text content of the document.
        """
        return self._generate_content_with_fallback(prompt, f"generated text for {document_type}")