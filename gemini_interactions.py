# gemini_interactions.py
import google.generativeai as genai
import os
import json
from game_config import API_CONFIG_FILE, GEMINI_MODEL_NAME, Colors # Assuming Colors is also in game_config

class GeminiAPI:
    def __init__(self):
        self.model = None
        self.api_key_configured = False
        self._print_color_func = lambda text, color, end="\n": print(f"{color}{text}{Colors.RESET}", end=end)


    def _print_color(self, text, color, end="\n"):
        # A simple internal print or pass to a game logger if available
        print(f"{color}{text}{Colors.RESET}", end=end)


    def load_api_key(self):
        try:
            if os.path.exists(API_CONFIG_FILE):
                with open(API_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get("gemini_api_key")
        except Exception as e:
            self._print_color(f"Could not load API key from {API_CONFIG_FILE}: {e}", Colors.RED)
        return None

    def save_api_key(self, api_key):
        try:
            with open(API_CONFIG_FILE, 'w') as f:
                json.dump({"gemini_api_key": api_key}, f)
            self._print_color(f"API key saved to {API_CONFIG_FILE}", Colors.MAGENTA)
        except Exception as e:
            self._print_color(f"Could not save API key to {API_CONFIG_FILE}: {e}", Colors.RED)

    def configure(self, print_func, input_func):
        self._print_color_func = print_func # Use game's print function
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
            self.model = genai.GenerativeModel(GEMINI_MODEL_NAME) 
            self.api_key_configured = True
            self._print_color_func(f"\nGemini API configured successfully with model '{GEMINI_MODEL_NAME}'.", Colors.GREEN)
            self.save_api_key(api_key)
        except Exception as e:
            self._print_color_func(f"Error configuring Gemini API with model '{GEMINI_MODEL_NAME}': {e}", Colors.RED)
            self._print_color_func("Please ensure your API key is correct and the model name is valid.", Colors.YELLOW)
            self._print_color_func("The game will run with placeholder NPC responses.", Colors.YELLOW)
            self.api_key_configured = False
            if os.path.exists(API_CONFIG_FILE): # Remove invalid key
                try: os.remove(API_CONFIG_FILE)
                except OSError: pass


    def get_npc_dialogue(self, npc_character, player_character, player_dialogue, current_location_name, relationship_status, npc_memory_summary):
        if not self.api_key_configured or not self.model:
            return f"(OOC: Gemini API not configured. I'd normally respond to '{player_dialogue}' with deep insight.)"
        
        conversation_context = npc_character.get_formatted_history(player_character.name)
        
        prompt = f"""
        You are {npc_character.name}, a character from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {npc_character.persona}
        You are currently in {current_location_name}.
        The player is roleplaying as {player_character.name}.
        Your current relationship with {player_character.name} is {relationship_status}.
        {npc_memory_summary}

        Recent conversation history with {player_character.name}:
        ---
        {conversation_context}
        ---
        Now, {player_character.name} says to you: "{player_dialogue}"

        Respond concisely and strictly in character as {npc_character.name}, reflecting your persona, the current location, your relationship with the player, your memories of them, and the ongoing conversation.
        Maintain the serious, introspective, and psychologically complex tone of Dostoevsky's "Crime and Punishment".
        Do NOT break character. Do NOT use out-of-character remarks like (OOC) or explain your reasoning.
        Your response should be only the dialogue spoken by {npc_character.name}.
        """
        try:
            response = self.model.generate_content(prompt)
            ai_text = response.text.strip()
            return ai_text
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for NPC dialogue: {e}", Colors.RED)
            return "(OOC: My thoughts are... muddled. I cannot seem to respond right now.)"

    def get_player_reflection(self, player_character, current_location_name, objectives_text):
        if not self.api_key_configured or not self.model:
            return "(OOC: Gemini API not configured. Cannot reflect right now.)"

        prompt = f"""
        You are roleplaying as {player_character.name} from Dostoevsky's "Crime and Punishment".
        Your detailed persona: {player_character.persona}
        You are currently in {current_location_name}.
        {objectives_text}
        Consider your current situation, your surroundings, and your objectives.

        Generate a brief, introspective inner thought or reflection (1-2 sentences) that {player_character.name} might have right now.
        Maintain the serious, introspective, and psychologically complex tone of Dostoevsky's "Crime and Punishment".
        The reflection should be from the first-person perspective of {player_character.name}.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for reflection: {e}", Colors.RED)
            return "(OOC: My thoughts are a blur.)"

    def get_npc_to_npc_interaction(self, npc1, npc2, location_name, game_time_period):
        if not self.api_key_configured or not self.model:
            return None 
        
        prompt = f"""
        Simulate a brief, ambient interaction between two characters from Dostoevsky's "Crime and Punishment" who are in the same location.
        Location: {location_name}
        Time of day: {game_time_period}

        Character 1: {npc1.name}
        Persona 1: {npc1.persona}

        Character 2: {npc2.name}
        Persona 2: {npc2.persona}

        Generate a short, in-character exchange (1 line of dialogue for each character, or a brief observation one makes of the other).
        The interaction should be subtle and fit the atmosphere of the novel and their personalities. It could be about the location, the time of day, a general observation, or a brief, almost unspoken acknowledgment.
        Do NOT have them discuss the player character unless it's extremely vague and natural.
        Maintain the serious, introspective, and psychologically complex tone.
        Format as:
        {npc1.name}: [dialogue]
        {npc2.name}: [dialogue]
        OR
        {npc1.name} [observes/glances at/etc.] {npc2.name} [reaction/thought].

        Example of subtle interaction:
        Razumikhin: "Another dreary day, eh Svidrigailov?"
        Svidrigailov: "Dreary? Perhaps for some. I find St. Petersburg always offers... diversions."
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for NPC-NPC interaction: {e}", Colors.RED)
            return None

    def get_character_ascii_art(self, character_name, character_persona):
        if not self.api_key_configured or not self.model:
            return "(OOC: Gemini API not configured. Cannot visualize the character.)"

        # Extract key visual descriptions from persona if possible, or use the whole persona.
        # This is a simple approach; more advanced NLP could be used to pick out visual traits.
        # For now, we'll provide a good chunk of the persona.
        persona_summary_for_art = character_persona[:500] # Limit length for prompt

        prompt = f"""
        Generate a text-based ASCII art portrait of the character {character_name} from Dostoevsky's "Crime and Punishment".
        Character description: {persona_summary_for_art}
        
        The ASCII art should:
        - Be a recognizable portrait or bust of the character.
        - Capture their essence or a key expression based on their persona.
        - Use standard ASCII characters.
        - Be suitable for display in a terminal (roughly 40-60 characters wide, and not excessively tall).
        - Be creative and artistic within the ASCII medium.
        - Focus on the character's face and perhaps shoulders.
        - Do NOT include any explanatory text, just the ASCII art itself.
        """
        try:
            # It's good practice to set safety_settings for content generation
            # to avoid overly restrictive filtering for artistic content,
            # but use with caution and understanding of the implications.
            # For ASCII art, default safety might be fine.
            # Example:
            # safety_settings = [
            #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            # ]
            # response = self.model.generate_content(prompt, safety_settings=safety_settings)
            
            response = self.model.generate_content(prompt)
            
            # The response might sometimes include backticks around the art or other text.
            # Try to clean it up.
            ai_text = response.text.strip()
            if ai_text.startswith("```") and ai_text.endswith("```"):
                ai_text = ai_text[3:-3].strip()
            # Remove common "Here's the ASCII art:" type prefixes if the model adds them.
            lines = ai_text.split('\n')
            if lines and ("art:" in lines[0].lower() or "ascii:" in lines[0].lower()):
                ai_text = "\n".join(lines[1:])
            
            return ai_text.strip()
        except Exception as e:
            self._print_color_func(f"Error calling Gemini API for ASCII art: {e}", Colors.RED)
            return "(OOC: Could not conjure a visual representation.)"

