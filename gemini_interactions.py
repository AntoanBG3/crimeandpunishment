# gemini_interactions.py
import google.generativeai as genai
import os
import json
from game_config import API_CONFIG_FILE, GEMINI_MODEL_NAME, Colors 

class GeminiAPI:
    def __init__(self):
        self.model = None
        self.api_key_configured = False
        self._print_color_func = lambda text, color, end="\n": print(f"{color}{text}{Colors.RESET}", end=end)
        self._input_color_func = lambda prompt, color: input(f"{color}{prompt}{Colors.RESET}")

    def _log_message(self, text, color, end="\n"):
        if hasattr(self, '_print_color_func') and self._print_color_func:
            self._print_color_func(text, color, end=end)
        else: 
            print(f"{color}{text}{Colors.RESET}", end=end)

    def load_api_key(self):
        try:
            if os.path.exists(API_CONFIG_FILE):
                with open(API_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get("gemini_api_key")
        except Exception as e:
            self._log_message(f"Could not load API key from {API_CONFIG_FILE}: {e}", Colors.RED)
        return None

    def save_api_key(self, api_key):
        try:
            with open(API_CONFIG_FILE, 'w') as f:
                json.dump({"gemini_api_key": api_key}, f)
            self._log_message(f"API key saved to {API_CONFIG_FILE}", Colors.MAGENTA)
        except Exception as e:
            self._log_message(f"Could not save API key to {API_CONFIG_FILE}: {e}", Colors.RED)

    def configure(self, print_func, input_func):
        self._print_color_func = print_func 
        self._input_color_func = input_func

        self._print_color_func("\n--- Gemini API Key Configuration ---", Colors.MAGENTA)
        api_key = self.load_api_key()
        
        if not api_key:
            api_key = self._input_color_func("Please enter your Gemini API key: ", Colors.MAGENTA).strip()
                                           
        if not api_key:
            self._print_color_func("\nNo API key provided.", Colors.RED)
            self._print_color_func("The game will run with placeholder NPC responses.", Colors.YELLOW)
            self.api_key_configured = False
            return

        try:
            genai.configure(api_key=api_key)
            # Ensure the model name from game_config is used
            current_model_name = GEMINI_MODEL_NAME 
            self.model = genai.GenerativeModel(current_model_name) 
            self.api_key_configured = True
            self._print_color_func(f"\nGemini API configured successfully with model '{current_model_name}'.", Colors.GREEN)
            self.save_api_key(api_key) 
        except Exception as e:
            self._print_color_func(f"Error configuring Gemini API with model '{GEMINI_MODEL_NAME}': {e}", Colors.RED)
            self._print_color_func("Please ensure your API key is correct and the model name is valid.", Colors.YELLOW)
            self._print_color_func("The game will run with placeholder NPC responses.", Colors.YELLOW)
            self.api_key_configured = False
            if os.path.exists(API_CONFIG_FILE): 
                try: 
                    os.remove(API_CONFIG_FILE)
                    self._print_color_func(f"Removed potentially invalid API key from {API_CONFIG_FILE}.", Colors.YELLOW)
                except OSError as ose:
                    self._print_color_func(f"Could not remove {API_CONFIG_FILE}: {ose}", Colors.YELLOW)

    def get_npc_dialogue(self, npc_character, player_character, player_dialogue, 
                         current_location_name, relationship_status, npc_memory_summary, 
                         player_apparent_state="normal", player_notable_items_summary="nothing noteworthy"):
        if not self.api_key_configured or not self.model:
            return f"(OOC: Gemini API not configured. I'd normally respond to '{player_dialogue}' with deep insight.)"
        
        conversation_context = npc_character.get_formatted_history(player_character.name)
        
        # Constructing the current situation for the NPC
        situation_summary = f"You, {npc_character.name}, are in {current_location_name}. "
        situation_summary += f"The player, {player_character.name}, currently appears to be in a '{player_apparent_state}' state and {player_notable_items_summary} "
        situation_summary += f"Your relationship with {player_character.name} is {relationship_status}. "
        situation_summary += f"{npc_memory_summary}"


        prompt = f"""
        You are {npc_character.name}, a character from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {npc_character.persona}
        
        Current situation: {situation_summary}

        Recent conversation history with {player_character.name}:
        ---
        {conversation_context}
        ---
        Now, {player_character.name} says to you: "{player_dialogue}"

        Respond concisely and strictly in character as {npc_character.name}.
        Your response MUST reflect:
        1. Your core persona and psychological traits from the novel.
        2. The immediate situation: your location, the player's apparent state ('{player_apparent_state}'), and what they are carrying ('{player_notable_items_summary}'). For example, if they are carrying something suspicious or look agitated, your dialogue should subtly or directly acknowledge this in a way that is true to your character (e.g., Porfiry might be probing, Sonya concerned, Svidrigailov cynically amused).
        3. Your existing relationship with and memories of the player.
        4. The ongoing conversation flow.
        
        Maintain the serious, introspective, and psychologically complex tone of Dostoevsky's "Crime and Punishment".
        Avoid modern colloquialisms. Your speech should be somewhat formal or characteristic of the 19th century.
        Do NOT break character. Do NOT use out-of-character remarks like (OOC) or explain your reasoning.
        Your response should be only the dialogue spoken by {npc_character.name}.
        If the player's state or items are particularly striking (e.g., carrying an axe, looking feverish), your reaction should be more pronounced but still in character.
        """
        try:
            response = self.model.generate_content(prompt)
            ai_text = response.text.strip()
            
            npc_character.add_to_history(player_character.name, player_character.name, player_dialogue)
            npc_character.add_to_history(player_character.name, npc_character.name, ai_text)
            player_character.add_to_history(npc_character.name, player_character.name, player_dialogue)
            player_character.add_to_history(npc_character.name, npc_character.name, ai_text)
            return ai_text
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for NPC dialogue: {e}", Colors.RED)
            return "(OOC: My thoughts are... muddled. I cannot seem to respond right now.)"

    def get_player_reflection(self, player_character, current_location_name, objectives_text, time_period):
        if not self.api_key_configured or not self.model:
            return "(OOC: Gemini API not configured. Cannot reflect right now.)"

        prompt = f"""
        You are roleplaying as {player_character.name} from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {player_character.persona}
        You are currently in {current_location_name} during the {time_period}.
        Your apparent state is: {player_character.apparent_state}.
        {objectives_text}
        Consider your current situation, your surroundings, your emotional state, and your objectives.

        Generate a brief, introspective inner thought or reflection (1-3 sentences) that {player_character.name} might have right now.
        This reflection should be deeply personal and psychological, consistent with Dostoevsky's style.
        It might touch upon guilt, paranoia, philosophical ponderings, observations about the city's oppressive atmosphere, or fleeting memories.
        Maintain the serious, introspective, and psychologically complex tone.
        The reflection should be from the first-person perspective of {player_character.name}.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for reflection: {e}", Colors.RED)
            return "(OOC: My thoughts are a blur.)"

    def get_atmospheric_details(self, player_character, location_name, time_period, recent_event_summary=None):
        if not self.api_key_configured or not self.model:
            return None # Return None if API not configured, so game can skip printing it

        # Build a context string
        context = f"{player_character.name} ({player_character.apparent_state}) is in {location_name} during the {time_period}. "
        if recent_event_summary:
            context += f"Recently, {recent_event_summary}. "

        prompt = f"""
        Evoke the atmosphere of Dostoevsky's St. Petersburg.
        Context: {context}

        Describe a subtle, psychologically resonant atmospheric detail or a fleeting observation {player_character.name} might notice.
        This should be 1-2 sentences, enhancing the mood and aligning with the novel's oppressive, feverish, or introspective tone.
        Focus on sensory details (a sound, a smell, a visual detail, a feeling) or a brief, almost subconscious thought related to the environment.
        The detail should reflect the character's internal state or the underlying tension of their situation.
        Do NOT make it a major plot point or an action. It's about mood and psychological texture.

        Examples:
        - "A distant church bell tolled, each chime seeming to hammer another nail into the coffin of the day."
        - "The greasy steam from a nearby pie-seller's stall felt cloying, a physical manifestation of the city's decay."
        - "For a moment, the scuff mark on the floor looked like a dark accusation."
        - "The oppressive heat of the afternoon seemed to leach the very will to act."
        
        Output only the atmospheric description.
        """
        try:
            response = self.model.generate_content(prompt)
            description = response.text.strip()
            # Ensure it's not an empty string or a refusal.
            if description and len(description) > 10 and "cannot" not in description.lower() and "unable" not in description.lower():
                return description
            return None # Return None if the response is too short or seems like a refusal
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for atmospheric details: {e}", Colors.RED)
            return None


    def get_npc_to_npc_interaction(self, npc1, npc2, location_name, game_time_period):
        if not self.api_key_configured or not self.model:
            return None 
        
        prompt = f"""
        Simulate a brief, ambient interaction between two characters from Dostoevsky's "Crime and Punishment" who are in the same location.
        Location: {location_name}
        Time of day: {game_time_period}

        Character 1: {npc1.name} (appears {npc1.apparent_state})
        Persona 1: {npc1.persona}
        Recent history with Character 2 (if any): {npc1.get_formatted_history(npc2.name, limit=2)}

        Character 2: {npc2.name} (appears {npc2.apparent_state})
        Persona 2: {npc2.persona}
        Recent history with Character 1 (if any): {npc2.get_formatted_history(npc1.name, limit=2)}

        Generate a short, in-character exchange (1 line of dialogue for each character, or a brief observation one makes of the other).
        The interaction should be subtle and fit the atmosphere of the novel and their personalities. It could be about the location, the time of day, a general observation, or a brief, almost unspoken acknowledgment.
        Their dialogue should reflect their personas and current apparent states.
        Do NOT have them discuss the player character unless it's extremely vague and natural.
        Maintain the serious, introspective, and psychologically complex tone.
        Format strictly as:
        {npc1.name}: [dialogue]
        {npc2.name}: [dialogue]
        
        OR if one is just observing:
        {npc1.name} [observes/glances at/etc.] {npc2.name} [reaction/thought of NPC1 about NPC2, or NPC2's subtle reaction].
        """
        try:
            response = self.model.generate_content(prompt)
            interaction_text = response.text.strip()
            npc1.add_to_history(npc2.name, "Ambient", interaction_text)
            npc2.add_to_history(npc1.name, "Ambient", interaction_text)
            return interaction_text
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for NPC-NPC interaction: {e}", Colors.RED)
            return None

    def get_item_interaction_description(self, character, item_name, item_details, action_type="examine"):
        if not self.api_key_configured or not self.model:
            return f"(OOC: Gemini API not configured. You {action_type} the {item_name}.)"

        prompt = f"""
        You are roleplaying as {character.name} (current state: {character.apparent_state}) from Dostoevsky's "Crime and Punishment".
        Your persona: {character.persona}
        You are about to interact with an item: '{item_name}'.
        Item details: {item_details.get('description', 'No specific details.')}
        The action is: {action_type} (e.g., examine, take, drop, use).

        Describe {character.name}'s brief thought or observation related to this action and item, in 1-2 sentences.
        This thought should be deeply psychological and in line with Dostoevsky's style, reflecting the character's current mental state and the item's potential significance or symbolism.
        If examining, provide a more evocative description than the basic item detail, from the character's perspective.
        If taking, perhaps a thought about its necessity, a moral qualm, or a fleeting memory.
        If dropping, a thought about why it's being discarded, its insignificance, or a desire to be rid of it.
        If using, a brief flicker of intent or apprehension.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for item interaction: {e}", Colors.RED)
            return f"(OOC: Your thoughts on the {item_name} are unclear.)"

