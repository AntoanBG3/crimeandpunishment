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
            print(f"{text}") # Fallback if color functions not set

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
            self.model = None
            return

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
            # Safety settings can be adjusted here if needed, e.g.,
            # safety_settings = {'HARASSMENT': 'BLOCK_NONE'} # Example, use with caution
            response = self.model.generate_content(prompt) #, safety_settings=safety_settings)
            
            # Check for empty or refusal-like responses more robustly
            if not hasattr(response, 'text') or not response.text or \
               any(phrase in response.text.lower() for phrase in ["cannot fulfill", "unable to provide", "cannot generate", "not able to create", "i am unable to"]):
                self._log_message(f"Warning: Gemini returned an empty or refusal-like response for {error_message_context}. Prompt: {prompt[:200]}...", Colors.YELLOW)
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
        1.  **Authenticity:** Your response MUST be deeply rooted in {npc_character.name}'s established personality, psychological traits, intellectual capacity, and typical speech patterns from the novel.
        2.  **Conciseness & Impact:** Aim for 1-3 sentences typically. However, if the emotional weight or complexity of the moment demands more, a slightly longer response is permissible if it remains impactful and avoids verbosity. Every word must serve the character and the Dostoevskian tone.
        3.  **Contextual Reaction:** Your response MUST intricately weave in reactions to:
            * **Your Own State & Goals:** How does your current mood ('{npc_character.apparent_state}') and your active objectives ({npc_objectives_summary}) color your perception and reply?
            * **Player's Presentation:** The player's apparent state ('{player_apparent_state}'), what they are carrying ('{player_notable_items_summary}'), and their current objectives ({player_objectives_summary}). If these details are striking (e.g., player looks feverish and carries an axe while you are Porfiry), your reaction must be pronounced yet characteristic (Porfiry: probing, cynical amusement; Sonya: gentle concern, fear; Svidrigailov: detached curiosity, potential manipulation).
            * **Relationship & Memory:** Your established relationship ('{relationship_status_text}') and specific memories ({npc_memory_summary}) concerning {player_character.name}.
            * **Environment & Events:** The current location ({current_location_name}), time ({current_time_period}), and significant recent game events ({recent_game_events_summary}).
            * **Dialogue Flow:** The immediate player input ("{player_dialogue}") and the preceding conversation context.
        4.  **Dostoevskian Tone:** Maintain the novel's serious, introspective, psychologically complex, and often oppressive or feverish atmosphere. Your language should be somewhat formal or characteristic of 19th-century Russia. AVOID modern colloquialisms, slang, or anachronistic phrasing.
        5.  **No OOC or Meta-Commentary:** STRICTLY FORBIDDEN to break character, use out-of-character (OOC) remarks, explain your reasoning, or use meta-game language.
        6.  **Dialogue Only:** Output ONLY the words spoken by {npc_character.name}. Do not include stage directions or descriptions unless they are part of an internal, almost spoken thought that fits the character (e.g. a sigh followed by words).
        7.  **Handling Nonsense:** If the player's input is utterly nonsensical or anachronistic for the setting, express confusion, dismissiveness, or suspicion in a way that is appropriate to {npc_character.name}'s persona and intelligence. Do not simply state it's nonsensical.

        **Example of nuanced reaction:** If player is Raskolnikov, appears 'feverish', carries 'an axe', and you are Porfiry, you might say: "My dear Rodion Romanovich, you appear... overwrought. Such a burden you carry, and in this heat too. Come, sit. Tell me what troubles that keen mind of yours." (Subtly alluding to both physical and metaphorical burdens).

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
        * Location: {current_location_name}
        * Time: {current_time_period}
        * Your Apparent State: {player_character.apparent_state}
        * Carrying: {inventory_highlights}
        * Active Objectives: {active_objectives_summary}
        * Recent Interactions/Observations: {recent_interactions_summary}
        * Immediate Context/Preoccupation: {context_text}

        **Your Task: Generate a brief, introspective inner thought or reflection (typically 1-3 sentences) that {player_character.name} would have in this exact moment.**

        **Reflection Guidelines (Strict Adherence Required):**
        1.  **Deeply Personal & Psychological:** The reflection must stem from {player_character.name}'s core conflicts, anxieties, theories, guilt, paranoia, or philosophical ponderings. It should feel like a genuine glimpse into their tormented or contemplative mind.
        2.  **Dostoevskian Style:** Maintain a serious, introspective, and psychologically complex tone. The language should be rich and evocative of the novel.
        3.  **First-Person Perspective:** The reflection MUST be from {player_character.name}'s first-person perspective (e.g., "I feel...", "This place...", "Am I truly...?").
        4.  **Contextual Relevance:** The thought should be directly triggered by or relevant to:
            * The current location and its atmosphere.
            * The time of day.
            * Your character's current emotional/physical state ({player_character.apparent_state}).
            * Items you are carrying, especially if they are significant (e.g., the axe, Sonya's cross, the letter).
            * Your active objectives and their current stage/progress.
            * Recent interactions, events, or the `context_text` provided.
            * Internal conflicts related to your theories or actions.
        5.  **Concise & Poignant:** While deep, the thought should be brief and impactful.
        6.  **No OOC or Meta-Commentary:** STRICTLY FORBIDDEN to break character or explain the thought process.
        7.  **Output Only the Thought:** Generate only the reflective text itself.

        Example for Raskolnikov, if feverish, in his garret, after seeing Marmeladov:
        "This coffin of a room... it suffocates. Like that old drunkard's life, reeking of cheap vodka and despair. Are we all just insects, waiting to be crushed? Or is there... something more?"

        Generate {player_character.name}'s inner thought now:
        """
        return self._generate_content_with_fallback(prompt, f"player reflection for {player_character.name}")

    def get_atmospheric_details(self, player_character, location_name, time_period,
                                recent_event_summary=None, player_objective_focus=None):
        context = (f"{player_character.name} (current state: {player_character.apparent_state}, "
                   f"preoccupied with: {player_objective_focus if player_objective_focus else 'their usual thoughts'}) "
                   f"is in {location_name} during the {time_period}. ")
        if recent_event_summary:
            context += f"Recently, {recent_event_summary}. "

        prompt = f"""
        **Task: Evoke the atmosphere of Dostoevsky's St. Petersburg, filtered through {player_character.name}'s perception.**

        **Context:**
        {context}

        **Instructions:**
        1.  **Describe a subtle, psychologically resonant atmospheric detail or a fleeting observation {player_character.name} might notice.** This should be 1-2 concise, impactful sentences.
        2.  **Enhance Mood & Align with Tone:** The detail must align with the novel's oppressive, feverish, introspective, or grimy Dostoevskian tone. It should deepen the current mood.
        3.  **Sensory & Symbolic:** Focus on sensory details (a specific sound, a peculiar smell, a visual detail, a tactile feeling) or a brief, almost subconscious thought related to the environment that carries symbolic weight or psychological resonance for {player_character.name}.
        4.  **Reflect Internal State/Situation:** The detail should subtly reflect {player_character.name}'s internal state ({player_character.apparent_state}), their current preoccupations ({player_objective_focus}), or the underlying tension of their situation.
        5.  **Not a Plot Point:** This is NOT a major plot event or an action. It's about mood, psychological texture, and deepening immersion.
        6.  **Output Only Description:** Do not use quotation marks unless it's a very direct, short internal thought like "This city..." or "That sound..." followed by the character's interpretation.

        **Examples reflecting character state/focus:**
        * If Raskolnikov is feverish and paranoid: "The oppressive afternoon heat seemed to press down, each distant shout from the Haymarket grating on raw nerves like an accusation."
        * If Sonya is sorrowful in her room: "A lone fly buzzed against the grimy windowpane, its frantic struggle a tiny echo of the city's vast, unheeded grief."
        * If player is contemplative on Voznesensky Bridge: "The canal's murky water flowed beneath, indifferent, its surface reflecting the grey, weeping sky like a distorted mirror of the soul."
        * If Raskolnikov is focused on his 'extraordinary man' theory: "Even the peeling yellow wallpaper in this cramped stairwell seemed to mock him with its faded, meaningless patterns, a testament to the ordinary lives he sought to transcend."

        Generate the atmospheric detail now:
        """
        return self._generate_content_with_fallback(prompt, "atmospheric details")

    def get_npc_to_npc_interaction(self, npc1, npc2, location_name, game_time_period,
                                   npc1_objectives_summary="their usual concerns",
                                   npc2_objectives_summary="their usual concerns"):
        prompt = f"""
        **Task: Simulate a brief, ambient, and Dostoevskian interaction (1-3 lines total) between two NPCs.**

        **Setting:**
        * Location: {location_name}
        * Time of day: {game_time_period}

        **Characters Involved:**
        * Character 1: {npc1.name}
            * Apparent State: {npc1.apparent_state}
            * Persona: {npc1.persona}
            * Current Concerns/Objectives: {npc1_objectives_summary}
            * Recent History with Character 2 (if any): {npc1.get_formatted_history(npc2.name, limit=1) if hasattr(npc1, 'get_formatted_history') else "No specific recent interaction."}
        * Character 2: {npc2.name}
            * Apparent State: {npc2.apparent_state}
            * Persona: {npc2.persona}
            * Current Concerns/Objectives: {npc2_objectives_summary}
            * Recent History with Character 1 (if any): {npc2.get_formatted_history(npc1.name, limit=1) if hasattr(npc2, 'get_formatted_history') else "No specific recent interaction."}

        **Interaction Guidelines:**
        1.  **In-Character & Brief:** Generate a short, in-character exchange or observation. It could be about the location, the time, a general Dostoevskian observation, a brief, almost unspoken acknowledgment, or a subtle reflection of their current states/concerns.
        2.  **Reflect Personas & States:** Their dialogue or action MUST reflect their established personas and current apparent states. For instance, two desperate characters might exchange a look of shared misery, while Porfiry might make a seemingly innocuous but probing comment to another official.
        3.  **Avoid Player Focus:** Do NOT have them discuss the player character unless it's extremely vague, natural, and indirect (e.g., "Strange types about these days..."). The focus is on *their* world.
        4.  **Dostoevskian Tone:** Maintain the serious, introspective, and psychologically complex tone of the novel.
        5.  **Format (Strict):**
            * For dialogue:
                {npc1.name}: [dialogue]
                {npc2.name}: [dialogue]
            * For non-verbal or very brief interaction:
                ({npc1.name} [e.g., glances sharply at / avoids eye contact with / mutters something towards] {npc2.name}, who [e.g., nods curtly / ignores them / sighs heavily / etc.].)
            * One character might speak, and the other react non-verbally.
        6.  **Atmospheric & Subtle:** Keep it very brief and primarily for atmospheric color. This is not a major plot event.

        Generate the interaction now:
        """
        return self._generate_content_with_fallback(prompt, f"NPC-to-NPC interaction between {npc1.name} and {npc2.name}")

    def get_item_interaction_description(self, character, item_name, item_details, action_type="examine",
                                         location_name="an undisclosed location", time_period="an unknown time",
                                         target_details=None): # target_details = {"name": "X", "state": "Y"}
        prompt = f"""
        **Roleplay Mandate: Generate {character.name}'s internal, first-person Dostoevskian thought/observation upon interacting with an item.**

        **Character & Context:**
        * Character: {character.name} (Current State: {character.apparent_state})
        * Persona: {character.persona}
        * Location: {location_name}
        * Time: {time_period}
        * Interacting with Item: '{item_name}' (Base description: {item_details.get('description', 'No specific details.')})
        * Action Performed: {action_type}
        {f"* Target of Action: {target_details['name']} (appears {target_details['state']})" if target_details else ""}

        **Task: Describe {character.name}'s brief, evocative thought, observation, or sensory detail (1-2 sentences) related to this action and item.**

        **Guidelines (Strict Adherence):**
        1.  **Psychologically Resonant:** The thought must be deeply psychological, in line with Dostoevsky's style, reflecting:
            * {character.name}'s current mental/emotional state ({character.apparent_state}).
            * The item's potential significance, symbolism, or triggered memories *for them*.
            * How the item relates to their current objectives or internal conflicts.
        2.  **First-Person Internal Monologue:** Strictly from {character.name}'s perspective (e.g., "This feels...", "I recall...", "Does this mean...?").
        3.  **Sensory & Evocative:** Emphasize sensory details (how it looks, feels, smells, sounds, or tastes if applicable) and the emotional or intellectual response it provokes.
        4.  **Concise & Impactful:** The thought should be brief but carry weight.
        5.  **No OOC:** Do not break character or explain the thought.
        6.  **Output Only the Thought:** Generate only the character's internal reflection. Do not use quotation marks unless it's a very direct, short internal quote that fits the character's voice.

        **Example (Raskolnikov examining the 'bloodied rag' he hid):**
        "The stain... darker now, almost black. It seems to pulse in this wretched light. Proof. Or madness. Is there a difference anymore?"

        Generate {character.name}'s thought/observation now:
        """
        return self._generate_content_with_fallback(prompt, f"item interaction with {item_name} by {character.name}")

    def get_dream_sequence(self, character_obj, recent_events_summary, current_objectives_summary, key_relationships_summary):
        prompt = f"""
        **Task: Describe a symbolic, surreal, and unsettling Dostoevskian dream experienced by {character_obj.name}.**

        **Dreamer Profile:**
        * Character: {character_obj.name}
        * Current Emotional/Psychological State: {character_obj.apparent_state}
        * Recent Events/Preoccupations: {recent_events_summary}
        * Deep-seated Concerns/Objectives: {current_objectives_summary}
        * Key Relationships & Their Current Nature: {key_relationships_summary}

        **Dream Guidelines (Strict Adherence):**
        1.  **Symbolic & Surreal:** The dream must be rich in symbolism, reflecting {character_obj.name}'s guilt, fears, theories (e.g., Raskolnikov's 'extraordinary men'), poverty, relationships, or paranoia. Avoid literal narratives; focus on fragmented, illogical, and emotionally charged imagery.
        2.  **Dostoevskian Tone:** Maintain a heavy, psychologically weighty, and often oppressive or feverish atmosphere. The dream should feel like the product of a troubled mind.
        3.  **Vivid, Fragmented Imagery:** Use sharp, memorable, and perhaps disturbing images. Think of recurring motifs from the novel (e.g., for Raskolnikov: an axe, blood, yellow colors, cramped spaces, water, laughter, whispers, the old pawnbroker, Lizaveta, Sonya as a beacon or accuser, Porfiry as a spider).
        4.  **Emotional Impact:** The dream's primary purpose is to convey an emotional state or a psychological truth about the character.
        5.  **Concise Description:** Aim for 3-5 evocative sentences.
        6.  **Output Only Dream Description:** Do not explain the dream or its symbols.

        **Example for Raskolnikov (if feeling guilty and paranoid):**
        "He was climbing endless, narrow, yellow stairs, each step slick with something warm and dark. Laughter, thin and sharp like breaking glass, echoed from above. He tried to call out Sonya's name, but only a horse's whinny tore from his throat. The old woman's eyes, pitiless and ancient, watched from every peeling patch of wallpaper."

        Generate the dream description for {character_obj.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"{character_obj.name}'s dream sequence")

    def get_rumor_or_gossip(self, npc_obj, location_name, game_time_period, known_facts_about_crime_summary, player_notoriety_level, npc_relationship_with_player_text, npc_current_concerns):
        prompt = f"""
        **Task: Generate a brief, in-character snippet of Dostoevskian gossip or rumor (1-2 sentences) that {npc_obj.name} might share or have overheard.**

        **Context for {npc_obj.name}:**
        * Persona: {npc_obj.persona}
        * Current State: {npc_obj.apparent_state}
        * Location: {location_name} (Time: {game_time_period})
        * Relationship with Player (Raskolnikov): {npc_relationship_with_player_text}
        * Own Current Concerns/Objectives: {npc_current_concerns}

        **Background Information:**
        * The Crime: An old pawnbroker and her sister were murdered. Publicly known details: {known_facts_about_crime_summary}.
        * Player (Raskolnikov) Notoriety: Level {player_notoriety_level} (0=unknown, 1=seen acting oddly, 2=arouses some suspicion, 3=definitely suspicious and talked about).

        **Rumor/Gossip Guidelines:**
        1.  **In-Character & Dostoevskian:** The snippet must fit {npc_obj.name}'s personality, biases, and way of speaking. It should reflect the anxieties, social commentary, or grim realities of 19th-century St. Petersburg.
        2.  **Content:** Could be about:
            * The crime itself (new "details," theories, police incompetence).
            * General fear, poverty, disease, or social decay.
            * A strange person or event recently witnessed (could subtly allude to the player if notoriety is high).
            * A piece of moralizing or a cynical observation.
        3.  **Subtlety with Player Notoriety:**
            * Low Notoriety (0-1): Do NOT mention Raskolnikov directly or provide details that clearly point to him. The rumor should be general.
            * Medium Notoriety (2): Might make a vague, deniable observation about "students these days," or "strange comings and goings" if it fits the NPC's character and they are in a relevant location.
            * High Notoriety (3): Could be a more pointed, though still perhaps speculative or misinformed, comment about "that Raskolnikov fellow" or "the student involved in that dreadful business," IF it aligns with the NPC's likelihood to gossip directly and their relationship with the player.
        4.  **Plausibility:** The rumor can be vague, slightly inaccurate, insightful, self-serving, or even a complete fabrication, as long as it's something that character *might* say or believe.
        5.  **Concise:** 1-2 sentences.
        6.  **Output Only the Rumor/Gossip:** No OOC.

        **Example (Tavern keeper, player notoriety 1, relationship neutral):**
        "They say the police are running in circles over that pawnbroker... another unsolved horror to add to this cursed city's tally. More vodka, sir?"

        **Example (Nosy Landlady, player notoriety 3, relationship negative, NPC concerned about reputation):**
        "That student in the garret... Raskolnikov... always lurking, pale as a ghost. Mark my words, no good will come of him, and he'll bring trouble to this house yet!"

        Generate the rumor/gossip from {npc_obj.name} now:
        """
        return self._generate_content_with_fallback(prompt, f"rumor from {npc_obj.name}")

    def get_newspaper_article_snippet(self, game_day, key_events_occurred_summary,
                                      relevant_themes_for_raskolnikov_summary, city_mood="tense and anxious"):
        prompt = f"""
        **Task: Generate a short St. Petersburg newspaper article snippet (2-4 sentences) for a publication like the 'St. Petersburg Chronicle' or 'Police Gazette'.**

        **Context:**
        * Narrative Timeline: Day {game_day} in "Crime and Punishment."
        * Key Public Events So Far: {key_events_occurred_summary}.
        * Relevant Themes (especially for Raskolnikov's internal state): {relevant_themes_for_raskolnikov_summary}.
        * General City Mood: {city_mood}.

        **Article Guidelines:**
        1.  **Content Focus:** The article could touch upon:
            * The ongoing investigation into the pawnbroker's murder (police activity, public speculation, lack of progress, false leads).
            * Social conditions in St. Petersburg (poverty, disease, alcoholism, housing issues, public morality debates).
            * Philosophical or 'new radical' ideas being discussed, perhaps with a critical or alarmed tone.
            * General city news reflecting current anxieties or events (e.g., fires, minor crimes, public disturbances).
            * Subtly allude to Raskolnikov's anxieties or theories without naming him (e.g., "the dangerous new philosophies corrupting youth," "the psychology of the modern criminal").
        2.  **19th-Century Journalistic Style:** Maintain a formal, somewhat dry, and objective (or pseudo-objective) tone appropriate for a public newspaper of the era. Use vocabulary and sentence structures fitting the period.
        3.  **Concise:** 2-4 sentences.
        4.  **Output Only Article Snippet:** No OOC.

        **Example (focusing on social conditions and subtle allusion to Raskolnikov's thinking):**
        "The recent brutal slaying in our capital continues to perplex authorities, while the broader societal maladies of indigence and despair fester. Concerns are also being voiced in learned circles regarding the alarming rise of nihilistic philosophies amongst the student population, questioning the very foundations of moral order."

        Generate the newspaper article snippet now:
        """
        return self._generate_content_with_fallback(prompt, "newspaper article snippet")

    def get_scenery_observation(self, character_obj, scenery_noun_phrase, location_name, time_period,
                                character_active_objectives_summary):
        prompt = f"""
        **Roleplay Mandate: Generate {character_obj.name}'s internal, first-person Dostoevskian observation about a specific piece of scenery.**

        **Character & Context:**
        * Character: {character_obj.name} (Current State: {character_obj.apparent_state})
        * Persona: {character_obj.persona}
        * Location: {location_name}
        * Time: {time_period}
        * Focus of Observation: '{scenery_noun_phrase}' (a specific part of the location's description)
        * Current Preoccupations/Objectives: {character_active_objectives_summary}

        **Task: Generate a brief, introspective, and Dostoevskian observation (1-2 sentences) about this specific piece of scenery from {character_obj.name}'s perspective.**

        **Guidelines (Strict Adherence):**
        1.  **Psychologically Resonant:** The observation must reflect:
            * {character_obj.name}'s current mood ({character_obj.apparent_state}) and personality.
            * How the scenery detail might connect, even tangentially, to their active objectives, internal conflicts, or philosophical ponderings.
            * The general Dostoevskian atmosphere (oppressive, symbolic, grimy, beautiful in decay, spiritually desolate).
        2.  **Deeper Meaning/Feeling:** What deeper meaning, feeling, memory, or philosophical thought does this mundane detail evoke in {character_obj.name}?
        3.  **First-Person Internal Monologue:** Strictly from {character_obj.name}'s perspective (e.g., "This wall...", "I see in that window...").
        4.  **Concise & Impactful:** 1-2 sentences.
        5.  **No OOC:** Do not break character.
        6.  **Output Only the Observation.**

        **Example (Raskolnikov looking at 'peeling wallpaper' in his garret, thinking about his theory):**
        "This faded yellow wallpaper, peeling like dead skin... It clings to the wall with such pathetic tenacity. Is this the 'ordinary' I despise, this clinging to a wretched existence?"

        Generate {character_obj.name}'s scenery observation now:
        """
        return self._generate_content_with_fallback(prompt, f"scenery observation of {scenery_noun_phrase}")

    def get_generated_text_document(self, document_type, author_persona_hint="an unknown person",
                                    recipient_persona_hint="the recipient", subject_matter="an important matter",
                                    desired_tone="neutral", key_info_to_include="some key details",
                                    length_sentences=3, purpose_of_document_in_game="To convey information."):
        prompt = f"""
        **Task: Generate the text content for a '{document_type}' within the world of Dostoevsky's "Crime and Punishment".**

        **Document Specifications:**
        * Type: {document_type} (e.g., Anonymous Warning Note, Official Summons, Begging Letter, Svidrigailov's Diary Entry)
        * Authored by (Persona): {author_persona_hint}
        * Intended for (Persona): {recipient_persona_hint}
        * Subject Matter: {subject_matter}
        * Desired Tone: {desired_tone} (e.g., ominous, bureaucratic, desperate, cynical, falsely congenial)
        * Key Information/Subtext to Convey: {key_info_to_include}
        * Approximate Length: {length_sentences} sentences.
        * Style: Appropriate for 19th-century St. Petersburg and the specified personas/tone. Emulate Dostoevskian psychological undertones where fitting.
        * Purpose within the game (for your guidance): {purpose_of_document_in_game}

        **Guidelines:**
        1.  **Authentic Voice:** The text must convincingly sound like it was written by the `author_persona_hint` with the `desired_tone`.
        2.  **Dostoevskian Flavor:** Infuse with the novel's characteristic vocabulary, sentence structure, and psychological depth where appropriate.
        3.  **Convey Key Info Subtly:** The `key_info_to_include` should be woven naturally into the text, not just listed. Subtext and implication are powerful.
        4.  **Output Only Document Text:** Generate only the content of the document itself. No OOC.

        **Example ('Anonymous Warning Note' to Raskolnikov):**
        * Author: "Someone observant from the shadows, perhaps a minor official or a street dweller"
        * Recipient: "Rodion Raskolnikov"
        * Subject: "A warning about being watched"
        * Tone: "Ominous, slightly uneducated, hurried"
        * Key Info: "Hints that Raskolnikov's recent unusual behavior or presence near certain places has been noticed. Does not directly name the crime."
        * Purpose: "To increase Raskolnikov's paranoia."
        * Generated Text: "Some folk see too much, Mr. Student. Best be minding your steps and your dark looks. Walls have ears, and so do the rats in 'em."

        Generate the text for the '{document_type}' now:
        """
        return self._generate_content_with_fallback(prompt, f"generated text for {document_type}")

