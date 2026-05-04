from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from game_engine.character_module import Character, load_characters_data
from game_engine.command_handler import CommandHandler
from game_engine.event_manager import EventManager
from game_engine.game_config import Colors
from game_engine.game_state import Game
from game_engine.gemini_interactions import GeminiAPI, NaturalLanguageParser
from game_engine.location_module import load_locations_data
from game_engine.static_fallbacks import (
    generate_static_item_interaction_description,
    generate_static_scenery_observation,
)
from game_engine.world_manager import WorldManager
from tests.test_coverage_core_modules import _make_state
from tests.unittest_function_loader import load_pytest_style_functions


def test_load_characters_data_error_paths(tmp_path):
    assert load_characters_data(str(tmp_path / "missing.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json")
    assert load_characters_data(str(bad)) == {}


def test_location_data_error_paths_and_static_fallbacks(tmp_path):
    assert load_locations_data(str(tmp_path / "missing_locations.json")) == {}
    bad = tmp_path / "bad_locations.json"
    bad.write_text("{not-json")
    assert load_locations_data(str(bad)) == {}

    with patch("game_engine.static_fallbacks.random.choice", side_effect=lambda options: options[0]):
        assert generate_static_scenery_observation("window").startswith("You observe")
        assert "letter" in generate_static_item_interaction_description("letter", "read")


@patch.dict("game_engine.game_config.DEFAULT_ITEMS", {"rock": {}, "coin": {"value": 1}}, clear=True)
def test_character_edge_paths_inventory_psychology_and_memory_formats():
    c = Character("C", "p", "g", "L", ["L"], objectives=[], psychology={"fear": 5}, is_player=False)
    assert c.psychology["fear"] == 5
    assert c.get_journal_summary() == "Journal is empty."
    for idx in range(21):
        c.add_journal_entry("note", str(idx), "Day")
    assert len(c.journal_entries) == 20

    c.apply_psychology_changes(None)
    c.apply_psychology_changes({"suspicion": "2", "fear": -999, "respect": "bad", "unknown": 4})
    assert 0 <= c.psychology["fear"] <= 100

    assert c.add_to_inventory("rock", 3) is True
    assert c.add_to_inventory("rock", 1) is False
    assert c.remove_from_inventory("rock", 2) is False
    assert c.add_to_inventory("coin", 2) is True
    assert c.add_to_inventory("coin", 3) is True
    assert c.remove_from_inventory("coin", 6) is False
    assert c.has_item("rock", 2) is False
    assert c.has_item("missing") is False
    assert c.remove_from_inventory("missing") is False

    with patch.dict(
        "game_engine.game_config.DEFAULT_ITEMS",
        {
            "book": {"is_notable": True},
            "coin": {"value": 1},
            "worn coin": {"value": 1, "notable_threshold": 20},
            "icon": {"is_notable": True},
        },
        clear=True,
    ):
        c.inventory = []
        assert c.get_notable_carried_items_summary() == "is not carrying anything of note."
        c.inventory = [{"name": "book"}]
        assert c.get_notable_carried_items_summary() == "is carrying book."
        c.inventory = [{"name": "book"}, {"name": "icon"}]
        assert c.get_notable_carried_items_summary() == "is carrying book and icon."
        c.inventory = [
            {"name": "book"},
            {"name": "icon"},
            {"name": "worn coin", "quantity": 25},
        ]
        assert "and a sum of money" in c.get_notable_carried_items_summary()

    for idx in range(12):
        c.add_to_history("Other", "C", str(idx))
    assert len(c.conversation_histories["Other"]) == 10
    with patch("builtins.print") as mock_print:
        c.add_player_memory("bad", 1, "not a dict")
    assert mock_print.called
    for idx in range(31):
        c.add_player_memory("other", idx, {"summary": str(idx)})
    assert len(c.memory_about_player) == 30

    empty = Character("Empty", "p", "g", "L", ["L"])
    assert "don't recall" in empty.get_player_memory_summary(current_turn=1)
    c.memory_about_player = [
        "legacy memory",
        {"type": "received_item", "turn": 1, "content": {"item_name": "coin", "quantity": 2}},
        {"type": "gave_item_to_player", "turn": 2, "content": {"item_name": "book", "quantity": 1}},
        {"type": "dialogue_exchange", "turn": 3, "content": {"player_statement": "...", "topic_hint": ""}, "sentiment_impact": -1},
        {"type": "player_action_observed", "turn": 4, "content": {"action": "dropped", "location": "L"}},
        {"type": "other", "turn": 5, "content": {"summary": "custom"}},
        {"type": "other2", "turn": 6, "content": "string content"},
    ]
    summary = c.get_player_memory_summary(current_turn=7)
    assert "Key things you recall" in summary
    c.update_relationship("nothing relevant", ["kind"], ["rude"], game_turn=8)
    assert c.relationship_with_player == 0


def test_character_complete_objective_linking_paths():
    objectives = [
        {
            "id": "a",
            "description": "A",
            "active": True,
            "completed": False,
            "current_stage_id": "s1",
            "stages": [
                {
                    "stage_id": "s1",
                    "description": "S1",
                    "linked_to_objective_completion": {"id": "b", "stage_to_advance_to": "b2"},
                }
            ],
        },
        {
            "id": "b",
            "description": "B",
            "active": False,
            "completed": False,
            "current_stage_id": "b1",
            "stages": [
                {"stage_id": "b1", "description": "B1", "next_stages": ["b2"]},
                {"stage_id": "b2", "description": "B2"},
            ],
        },
    ]
    c = Character("C", "p", "g", "L", ["L"], objectives=objectives, is_player=True)
    assert c.complete_objective("a", by_stage=True) is True
    b = c.get_objective_by_id("b")
    assert b["active"] is True


def test_character_objective_defaults_and_legacy_roundtrip_paths():
    c = Character(
        "C",
        "p",
        "g",
        "L",
        ["L"],
        objectives=[
            {"id": "defaulted", "description": "Defaulted", "stages": []},
            {"id": "plain", "description": "Plain"},
        ],
        is_player=True,
    )
    assert c.get_current_stage_for_objective("defaulted")["stage_id"] == "default"
    assert c.get_objective_by_id(None) is None
    assert c.get_objective_by_id("missing") is None
    assert c.get_current_stage_for_objective("missing") is None
    assert c.advance_objective_stage("plain", "missing") is False
    assert c.complete_objective("missing") is False
    assert c.activate_objective("missing") is False

    static = {
        "persona": "p",
        "greeting": "g",
        "default_location": "L",
        "accessible_locations": ["L"],
        "objectives": [
            {"description": "No id"},
            {"id": "nostages", "description": "No stages", "stages": []},
        ],
    }
    data = {
        "name": "C",
        "inventory": [],
        "objectives": [
            {"id": "legacy", "description": "Legacy"},
            {
                "id": "legacy2",
                "description": "Legacy 2",
                "stages": [{"stage_id": "l2", "description": "Legacy stage"}],
            },
        ],
    }
    restored = Character.from_dict(data, static)
    assert restored.get_current_stage_for_objective("nostages")["stage_id"] == "default"
    assert restored.get_current_stage_for_objective("legacy")["stage_id"] == "default"
    assert restored.get_current_stage_for_objective("legacy2")["stage_id"] == "l2"


def test_character_objective_linking_generic_next_stage_paths():
    objectives = [
        {
            "id": "done",
            "description": "Done",
            "active": True,
            "completed": False,
            "linked_to_objective_completion": "target_dict",
            "stages": [{"stage_id": "s", "description": "S"}],
            "current_stage_id": "s",
        },
        {
            "id": "target_dict",
            "description": "Target Dict",
            "active": True,
            "completed": False,
            "stages": [
                {"stage_id": "a", "description": "A", "next_stages": {"next": "b"}},
                {"stage_id": "b", "description": "B"},
            ],
            "current_stage_id": "a",
        },
        {
            "id": "done2",
            "description": "Done 2",
            "active": True,
            "completed": False,
            "linked_to_objective_completion": "target_list",
            "stages": [{"stage_id": "s", "description": "S"}],
            "current_stage_id": "s",
        },
        {
            "id": "target_list",
            "description": "Target List",
            "active": True,
            "completed": False,
            "stages": [
                {"stage_id": "a", "description": "A", "next_stages": ["b"]},
                {"stage_id": "b", "description": "B"},
            ],
            "current_stage_id": "a",
        },
    ]
    c = Character("C", "p", "g", "L", ["L"], objectives=objectives, is_player=True)
    assert c.complete_objective("done") is True
    assert c.get_objective_by_id("target_dict")["current_stage_id"] == "b"
    assert c.complete_objective("done2") is True
    assert c.get_objective_by_id("target_list")["current_stage_id"] == "b"


def test_game_state_summary_helpers_and_guard_paths():
    game = Game()
    game._print_color = MagicMock()
    assert game._get_save_file_path("!!!") is None
    assert game._get_recent_events_summary() == "Key recent events: Game started."
    game.key_events_occurred = []
    assert game._get_recent_events_summary() == "Nothing much has happened yet."
    game.known_facts_about_crime = []
    assert "No specific details" in game._get_known_facts_summary()

    game._remember_ai_output(None, "none")
    game._remember_ai_output("(OOC: blocked)", "blocked")
    assert game.last_ai_generated_text is None
    game._remember_ai_output("  remembered text  ", "source")
    assert game.last_ai_generated_text == "remembered text"
    assert game.last_ai_generation_source == "source"

    assert game.get_relationship_text(6) == "very positive"
    assert game.get_relationship_text(3) == "positive"
    assert game.get_relationship_text(-6) == "very negative"
    assert game.get_relationship_text(-3) == "negative"

    objective = {
        "id": "o",
        "description": "Do the thing",
        "active": True,
        "completed": False,
        "stages": [{"stage_id": "s", "description": "Stage"}],
        "current_stage_id": "s",
    }
    player = Character("P", "p", "g", "L", ["L"], objectives=[objective], is_player=True)
    npc = Character("N", "p", "g", "L", ["L"], objectives=[objective], is_player=False)
    assert game._get_objectives_summary(player).startswith("Your current objectives")
    assert game._get_objectives_summary(npc).startswith("N's current objectives")

    game.save_game()
    game._print_color.assert_any_call("Cannot save: Game not fully initialized.", Colors.RED)
    assert game.load_game("!!!") is False
    with patch("game_engine.game_state.os.path.exists", return_value=False):
        assert game.load_game("missing") is False


def test_game_state_save_load_and_initialize_edge_paths(tmp_path):
    game = Game()
    game._print_color = MagicMock()

    objective = {
        "id": "inactive",
        "description": "Inactive",
        "active": False,
        "completed": False,
    }
    character = Character("P", "p", "g", "Room", ["Room"], objectives=[objective], is_player=True)
    assert game._get_objectives_summary(character) == "Currently pursuing no specific objectives."
    assert game._get_known_facts_summary().startswith("Known facts")

    game.player_character = character
    game.current_location_name = "Room"
    save_file = tmp_path / "savegame.json"
    with patch("game_engine.game_state.SAVE_GAME_FILE", str(save_file)):
        game.save_game(is_autosave=True)
        assert save_file.exists()

    with patch("game_engine.game_state.SAVE_GAME_FILE", str(save_file)), patch(
        "game_engine.game_state.open",
        side_effect=OSError("disk full"),
    ):
        game.save_game()
    assert any("Error saving game" in call.args[0] for call in game._print_color.call_args_list)

    bad_save = tmp_path / "bad_save.json"
    bad_save.write_text("{bad-json")
    with patch("game_engine.game_state.SAVE_GAME_FILE", str(bad_save)):
        assert game.load_game() is False
    assert game.player_character is None

    game = Game()
    game._print_color = MagicMock()
    game._input_color = MagicMock(return_value="")
    game.display_atmospheric_details = MagicMock()
    game.display_help = MagicMock()
    game.gemini_api.configure = MagicMock(return_value={"low_ai_preference": True})
    game.world_manager._validate_item_data = MagicMock()
    game.world_manager.load_all_characters = MagicMock()
    game.world_manager.select_player_character = MagicMock(return_value=True)
    game.world_manager.update_current_location_details = MagicMock()
    game.player_character = Character("P", "p", "g", "Room", ["Room"], is_player=True)
    game.current_location_name = "Room"
    with patch("game_engine.game_state.os.getenv", return_value="key"):
        assert game._initialize_game() is True
    assert game.low_ai_data_mode is True

    game = Game()
    game._print_color = MagicMock()
    game._input_color = MagicMock(return_value="load")
    game.display_atmospheric_details = MagicMock()
    game.display_help = MagicMock()
    game.load_game = MagicMock(return_value=False)
    game.gemini_api.configure = MagicMock(return_value={"low_ai_preference": False})
    game.world_manager._validate_item_data = MagicMock()
    game.world_manager.load_all_characters = MagicMock()
    game.world_manager.select_player_character = MagicMock(return_value=False)
    with patch("game_engine.game_state.os.getenv", return_value=None):
        assert game._initialize_game() is False


def test_game_state_run_loop_and_think_paths():
    game = Game()
    game._print_color = MagicMock()
    game._initialize_game = MagicMock(return_value=True)
    game._print_turn_header = MagicMock()
    game._display_tutorial_hint = MagicMock()
    game._display_turn_feedback = MagicMock()
    game.world_manager._handle_ambient_rumors = MagicMock()
    game.world_manager._update_world_state_after_action = MagicMock()
    game.world_manager._check_game_ending_conditions = MagicMock(return_value=False)
    game.command_handler._record_command_history = MagicMock()
    game.current_location_name = "Room"

    game.command_handler._get_player_input = MagicMock(
        side_effect=[
            (None, None),
            ("look", None),
            ("status", None),
            ("dance", None),
            ("load", None),
            ("quit", None),
        ]
    )
    game.command_handler._process_command = MagicMock(
        side_effect=[
            (True, False, 1, False),
            (False, False, 0, False),
            (False, False, 0, False),
            (False, False, 0, "load_triggered"),
            (False, False, 0, True),
        ]
    )
    with patch("game_engine.game_state.LOCATIONS_DATA", {"Room": {"description": "Room"}}):
        game.run()
    assert game.last_turn_result_icon == "QUIT"

    missing_game = Game()
    missing_game._print_color = MagicMock()
    missing_game._initialize_game = MagicMock(return_value=True)
    missing_game.current_location_name = "Missing"
    with patch("game_engine.game_state.LOCATIONS_DATA", {}):
        missing_game.run()
    assert any("Critical Error" in call.args[0] for call in missing_game._print_color.call_args_list)

    no_init_game = Game()
    no_init_game._initialize_game = MagicMock(return_value=False)
    no_init_game.run()
    no_init_game._initialize_game.assert_called_once()

    think_game = Game()
    think_game._print_color = MagicMock()
    think_game._apply_verbosity = MagicMock(side_effect=lambda text: text)
    think_game._remember_ai_output = MagicMock()
    think_game._handle_think_command()
    think_game._print_color.assert_any_call(
        "Cannot think: Player character not available.",
        Colors.RED,
    )

    objective = {
        "id": "understand_theory",
        "description": "Theory",
        "active": True,
        "completed": False,
        "current_stage_id": "stage",
        "stages": [{"stage_id": "stage", "description": "Testing theory"}],
    }
    player = Character(
        "Rodion Raskolnikov",
        "p",
        "g",
        "Room",
        ["Room"],
        objectives=[objective],
        is_player=True,
    )
    think_game.player_character = player
    think_game.current_location_name = "Room"
    think_game.low_ai_data_mode = False
    think_game.gemini_api.model = object()
    think_game.gemini_api.get_player_reflection = MagicMock(return_value="A sharp thought.")
    think_game.world_manager.get_current_time_period = MagicMock(return_value="Morning")
    think_game._handle_think_command()
    think_game._remember_ai_output.assert_called_with("A sharp thought.", "think")

    think_game.low_ai_data_mode = True
    with patch("game_engine.game_state.STATIC_PLAYER_REFLECTIONS", []):
        think_game._handle_think_command()
    assert think_game.last_significant_event_summary == "was lost in thought."


def test_display_guard_and_branch_paths():
    game = Game()
    game._print_color = MagicMock()
    game._separator_line = MagicMock(return_value="---")
    game._apply_verbosity = MagicMock(side_effect=lambda text: text)
    game._remember_ai_output = MagicMock()
    game._get_current_game_time_period_str = MagicMock(return_value="Day 1, Morning")
    game._get_objectives_summary = MagicMock(return_value="objectives")

    game.command_handler = SimpleNamespace()
    game.player_action_count = 1
    game._display_tutorial_hint()
    assert any("someone nearby" in call.args[0] for call in game._print_color.call_args_list)

    game.player_character = Character("P", "p", "g", "Room", ["Room"], is_player=True)
    game.current_location_name = "Room"
    game.low_ai_data_mode = True
    game.gemini_api.model = None
    game.last_significant_event_summary = "recent"
    game.world_manager.get_current_time_period = MagicMock(return_value="Morning")
    with patch("game_engine.display_mixin.STATIC_ATMOSPHERIC_DETAILS", []):
        game.display_atmospheric_details()
    assert game.last_significant_event_summary is None

    game.player_character = None
    game.display_objectives()
    game._display_load_recap()
    game._handle_status_command()
    game._handle_inventory_command()

    completed_player = Character(
        "P",
        "p",
        "g",
        "Room",
        ["Room"],
        objectives=[{"id": "done", "description": "Done", "completed": True}],
        is_player=True,
    )
    game.player_character = completed_player
    game.display_objectives()
    game.display_help("unknown")

    objective = {
        "id": "active",
        "description": "Active",
        "active": True,
        "completed": False,
        "current_stage_id": "s",
        "stages": [{"stage_id": "s", "description": "Stage"}],
    }
    player = Character(
        "P",
        "p",
        "g",
        "Room",
        ["Room"],
        objectives=[objective],
        skills_data={"Observation": 3},
        is_player=True,
    )
    player.inventory = [{"name": "coin", "quantity": 3}]
    npc = Character("NPC", "p", "g", "Room", ["Room"])
    npc.relationship_with_player = 6
    game.player_character = player
    game.all_character_objects = {"P": player, "NPC": npc}
    game.current_location_name = "Room"
    game.low_ai_data_mode = False
    game.color_theme = "default"
    game.verbosity_level = "standard"
    game.turn_headers_enabled = True
    with patch.dict("game_engine.display_mixin.DEFAULT_ITEMS", {"coin": {"value": 1}}, clear=True):
        for notoriety in [0, 0.25, 2, 3]:
            game.player_notoriety_level = notoriety
            game._handle_status_command()

    game.player_character = SimpleNamespace(
        get_inventory_description=MagicMock(return_value="A strange custom inventory.")
    )
    with patch("builtins.print") as mock_print:
        game._handle_inventory_command()
    mock_print.assert_called_with("A strange custom inventory.")


def test_event_manager_error_cooldown_and_gossip_paths():
    game = SimpleNamespace(game_time=50, _print_color=MagicMock())
    manager = EventManager(game)
    action = MagicMock(side_effect=RuntimeError("bad action"))
    manager.triggered_events = {"recent_event_recent"}
    manager.story_events = [
        {
            "id": "bad_trigger",
            "trigger": MagicMock(side_effect=RuntimeError("bad trigger")),
            "action": MagicMock(),
            "one_time": True,
        },
        {"id": "bad_action", "trigger": lambda: True, "action": action, "one_time": True},
    ]
    assert manager.check_and_trigger_events() is False
    assert "recent_event_recent" not in manager.triggered_events
    assert "bad_action" in manager.triggered_events
    assert game._print_color.call_count >= 2

    npc1 = SimpleNamespace(name="NPC1")
    npc2 = SimpleNamespace(name="NPC2")
    player = SimpleNamespace(add_journal_entry=MagicMock())
    game = SimpleNamespace(
        npcs_in_current_location=[npc1, npc2],
        low_ai_data_mode=False,
        gemini_api=SimpleNamespace(
            model=object(),
            get_npc_to_npc_interaction=MagicMock(
                return_value="NPC1: Did you hear the pawnbroker case is stirring again?\nNPC2: Hush."
            ),
        ),
        current_location_name="Room",
        get_current_time_period=lambda: "Morning",
        _get_objectives_summary=lambda _npc: "objectives",
        _get_current_game_time_period_str=lambda: "Day 1, Morning",
        _print_color=MagicMock(),
        player_character=player,
        overheard_rumors=[],
    )
    manager = EventManager(game)
    with patch("game_engine.event_manager.random.sample", return_value=[npc1, npc2]), patch(
        "builtins.print"
    ):
        assert manager.attempt_npc_npc_interaction() is True
    assert game.overheard_rumors
    assert player.add_journal_entry.called

    game.npcs_in_current_location = [npc1]
    assert manager.attempt_npc_npc_interaction() is False


def test_event_manager_triggers_and_story_actions():
    player = Character(
        "Rodion Raskolnikov",
        "p",
        "g",
        "Raskolnikov's Garret",
        ["Raskolnikov's Garret", "Tavern", "Haymarket Square"],
        objectives=[
            {"id": "understand_theory", "description": "Theory", "active": True},
            {"id": "help_family", "description": "Family", "active": False},
        ],
        is_player=True,
    )
    player.add_player_memory = MagicMock()
    player.add_journal_entry = MagicMock()
    katerina = SimpleNamespace(
        name="Katerina Ivanovna Marmeladova",
        current_location="Haymarket Square",
        apparent_state="agitated",
    )
    game = SimpleNamespace(
        player_character=player,
        current_location_name="Tavern",
        game_time=30,
        all_character_objects={"Katerina Ivanovna Marmeladova": katerina},
        get_current_time_period=MagicMock(return_value="Afternoon"),
        player_notoriety_level=2,
        known_facts_about_crime=[],
        key_events_occurred=[],
        last_significant_event_summary=None,
        low_ai_data_mode=True,
        gemini_api=SimpleNamespace(
            model=None,
            get_generated_text_document=MagicMock(return_value="AI note"),
            get_street_life_event_description=MagicMock(return_value="A vivid crowd scene."),
        ),
        dynamic_location_items={},
        _print_color=MagicMock(),
        _get_current_game_time_period_str=MagicMock(return_value="Day 1, Afternoon"),
        _get_objectives_summary=MagicMock(return_value="objectives"),
    )
    manager = EventManager(game)

    assert manager.trigger_marmeladov_encounter() is True
    manager.action_marmeladov_encounter()
    assert "Encountered Marmeladov." in game.key_events_occurred
    assert any("Sonya" in fact for fact in game.known_facts_about_crime)

    game.current_location_name = "Raskolnikov's Garret"
    assert manager.trigger_letter_from_mother() is True
    with patch("game_engine.event_manager.random.choice", side_effect=lambda options: options[0]), patch(
        "game_engine.event_manager.STATIC_PLAYER_REFLECTIONS",
        [],
    ):
        manager.action_letter_from_mother()
    assert player.get_objective_by_id("help_family")["active"] is True
    assert player.has_item("mother's letter") is True

    game.current_location_name = "Haymarket Square"
    with patch("game_engine.event_manager.random.random", return_value=0.0):
        assert manager.trigger_katerina_public_lament() is True
    manager.action_katerina_public_lament()
    assert katerina.apparent_state == "highly agitated and feverish"

    game.current_location_name = "Raskolnikov's Garret"
    with patch("game_engine.event_manager.random.random", return_value=0.0):
        assert manager.trigger_find_anonymous_note() is True
    with patch.dict(
        "game_engine.event_manager.DEFAULT_ITEMS",
        {"anonymous note": {"readable": True}},
        clear=True,
    ):
        manager.action_find_anonymous_note()
    assert game.dynamic_location_items["Raskolnikov's Garret"][0]["name"] == "anonymous note"
    assert player.apparent_state == "paranoid"

    game.current_location_name = "Haymarket Square"
    game.low_ai_data_mode = False
    game.gemini_api.model = object()
    with patch("game_engine.event_manager.random.random", return_value=0.0):
        assert manager.trigger_street_life_haymarket() is True
    manager.action_street_life_haymarket()
    assert "street_life_haymarket_recent" in manager.triggered_events
    assert player.add_journal_entry.called


def test_event_manager_fallback_edge_paths():
    player = SimpleNamespace(
        name="Rodion Raskolnikov",
        apparent_state="uneasy",
        add_player_memory=MagicMock(),
        add_journal_entry=MagicMock(),
    )
    game = SimpleNamespace(
        player_character=player,
        current_location_name="Raskolnikov's Garret",
        game_time=50,
        all_character_objects={},
        get_current_time_period=MagicMock(return_value="Night"),
        player_notoriety_level=2,
        known_facts_about_crime=["Sonya is already known."],
        key_events_occurred=[],
        last_significant_event_summary=None,
        low_ai_data_mode=False,
        gemini_api=SimpleNamespace(
            model=object(),
            get_generated_text_document=MagicMock(return_value=""),
            get_street_life_event_description=MagicMock(return_value="(OOC: blocked)"),
            get_npc_to_npc_interaction=MagicMock(return_value=""),
        ),
        dynamic_location_items={},
        _print_color=MagicMock(),
        _get_current_game_time_period_str=MagicMock(return_value="Day 1, Night"),
        _get_objectives_summary=MagicMock(return_value="objectives"),
        npcs_in_current_location=[SimpleNamespace(name="A"), SimpleNamespace(name="B")],
        overheard_rumors=[str(idx) for idx in range(10)],
    )
    manager = EventManager(game)
    manager.action_find_anonymous_note()
    assert "found an anonymous warning note." not in str(game.last_significant_event_summary)

    game.current_location_name = "Haymarket Square"
    with patch("game_engine.event_manager.STATIC_STREET_LIFE_EVENTS", []):
        manager.action_street_life_haymarket()
    assert "street_life_haymarket_recent" in manager.triggered_events

    with patch("game_engine.event_manager.random.sample", side_effect=ValueError):
        assert manager.attempt_npc_npc_interaction() is False
    game.gemini_api.get_npc_to_npc_interaction.return_value = (
        "A: Did you hear " + "x" * 30 + "\nB: quietly"
    )
    with patch("game_engine.event_manager.random.sample", return_value=game.npcs_in_current_location), patch(
        "builtins.print"
    ):
        assert manager.attempt_npc_npc_interaction() is True
    assert len(game.overheard_rumors) == 10


@patch.dict(
    "game_engine.item_interaction_handler.DEFAULT_ITEMS",
    {
        "anonymous note": {"readable": True},
        "IOU Slip": {"readable": True},
        "Student's Dog-eared Book": {"readable": True},
        "dusty bottle": {"use_effect_player": "examine_bottle_for_residue"},
        "bloodied rag": {"use_effect_player": "examine_rag_and_spiral_into_paranoia"},
        "Loaf of Black Bread": {
            "use_effect_player": "eat_bread_for_sustenance",
            "consumable": True,
        },
        "Small, Tarnished Icon": {"use_effect_player": "contemplate_icon"},
    },
    clear=True,
)
def test_item_read_and_self_use_additional_branches():
    game = Game()
    game._print_color = MagicMock()
    game.gemini_api.model = None
    game.low_ai_data_mode = True
    game.current_location_name = "Room"
    game.game_time = 5
    game.player_notoriety_level = 0
    player = Character("Rodion Raskolnikov", "p", "g", "Room", ["Room"])
    player.apparent_state = "burdened"
    game.player_character = player
    game.player_character.inventory = [
        {"name": "anonymous note", "generated_content": "They watch and know."},
        {"name": "IOU Slip", "content": "Debt acknowledged."},
        {"name": "Student's Dog-eared Book"},
        {"name": "dusty bottle"},
        {"name": "bloodied rag"},
        {"name": "Loaf of Black Bread"},
        {"name": "Small, Tarnished Icon"},
    ]

    assert game.handle_use_item("anonymous", None, "read") is True
    assert player.apparent_state == "paranoid"
    assert game.handle_use_item("IOU", None, "read") is True
    assert game.handle_use_item("Student", None, "read") is True
    assert game.handle_use_item("dusty", None, "use_self_implicit") is True
    assert game.handle_use_item("bloodied", None, "use_self_implicit") is True
    assert game.handle_use_item("Loaf", None, "use_self_implicit") is True
    assert not any(item["name"] == "Loaf of Black Bread" for item in player.inventory)
    assert game.handle_use_item("Small", None, "use_self_implicit") is True

    player.inventory = [{"name": "anonymous note"}]
    assert game.handle_use_item("anonymous", None, "read") is False
    assert game._handle_use_command(None) is False
    game.player_character = None
    assert game._handle_use_command("dusty") is False
    assert game.handle_use_item("dusty") is False


@patch.dict(
    "game_engine.item_interaction_handler.DEFAULT_ITEMS",
    {
        "old newspaper": {"readable": True},
        "generic pamphlet": {"readable": True},
        "raskolnikov's axe": {"use_effect_player": "grip_axe_and_reminisce_horror"},
        "sonya's cypress cross": {"use_effect_player": "reflect_on_faith_and_redemption"},
        "cheap vodka": {"use_effect_player": "drink_vodka_for_oblivion"},
        "lizaveta's bundle": {"use_effect_player": "examine_bundle_and_face_guilt_for_Lizaveta"},
        "gift": {},
    },
    clear=True,
)
def test_item_read_use_and_give_edge_branches():
    game = Game()
    game._print_color = MagicMock()
    game.gemini_api.model = None
    game.low_ai_data_mode = True
    game.current_location_name = "Room"
    game.game_time = 8
    game.player_notoriety_level = 0

    assert game._handle_read_item("old newspaper", {"readable": True}, None) is False
    assert game._handle_give_item("gift", {}, "npc") is False

    player = Character("Dmitri Razumikhin", "p", "g", "Room", ["Room"])
    player.inventory = [
        {"name": "old newspaper"},
        {"name": "generic pamphlet"},
        {"name": "raskolnikov's axe"},
        {"name": "sonya's cypress cross"},
    ]
    game.player_character = player

    with patch("game_engine.item_interaction_handler.random.choice", return_value=None), patch(
        "game_engine.item_interaction_handler.STATIC_NEWSPAPER_SNIPPETS",
        ["placeholder"],
    ):
        assert game.handle_use_item("old", None, "read") is True
    assert game.handle_use_item("generic", None, "read") is True
    assert game.handle_use_item("raskolnikov", None, "use_self_implicit") is True
    assert game.handle_use_item("sonya", None, "use_self_implicit") is True
    assert game.handle_use_item(None, "door", "use_on") is False
    assert game.handle_use_item("missing", None, "read") is False
    assert game.handle_use_item("generic", "door", "use_on") is False

    player.name = "Rodion Raskolnikov"
    player.inventory = [
        {"name": "sonya's cypress cross"},
        {"name": "cheap vodka"},
        {"name": "lizaveta's bundle"},
        {"name": "gift"},
    ]
    player.has_item = MagicMock(return_value=False)
    player.remove_from_inventory = MagicMock(return_value=False)
    assert game.handle_use_item("sonya", None, "use_self_implicit") is True
    assert game.handle_use_item("cheap", None, "use_self_implicit") is True
    assert game.handle_use_item("lizaveta", None, "use_self_implicit") is True

    target = Character("NPC", "p", "g", "Room", ["Room"])
    game.npcs_in_current_location = [target]
    player.has_item = MagicMock(return_value=True)
    player.remove_from_inventory = MagicMock(return_value=False)
    assert game._handle_give_item("gift", {}, "NPC") is False


@patch.dict(
    "game_engine.item_interaction_handler.DEFAULT_ITEMS",
    {
        "raskolnikov's axe": {
            "description": "A heavy axe.",
            "takeable": True,
            "use_effect_player": "grip_axe_and_reminisce_horror",
            "is_notable": True,
        },
        "coin": {"description": "A coin.", "takeable": True, "value": 1},
        "fixed statue": {"description": "Bolted down.", "takeable": False},
    },
    clear=True,
)
@patch("game_engine.item_interaction_handler.HIGHLY_NOTABLE_ITEMS_FOR_MEMORY", ["raskolnikov's axe"])
def test_item_look_take_and_drop_more_paths():
    game = Game()
    game._print_color = MagicMock()
    game._separator_line = MagicMock(return_value="---")
    game._apply_verbosity = lambda text: text
    game._remember_ai_output = MagicMock()
    game.gemini_api.model = None
    game.low_ai_data_mode = True
    game.current_location_name = "Room"
    game.game_time = 4
    player = Character("Rodion Raskolnikov", "p", "g", "Room", ["Room"], skills_data={"Observation": 6})
    npc = Character("Witness", "watchful", "g", "Room", ["Room"])
    npc.add_player_memory = MagicMock()
    game.player_character = player
    game.npcs_in_current_location = [npc]
    game.dynamic_location_items = {
        "Room": [
            {"name": "raskolnikov's axe"},
            {"name": "coin", "quantity": 2},
            {"name": "fixed statue"},
        ]
    }

    with patch(
        "game_engine.item_interaction_handler.LOCATIONS_DATA",
        {"Room": {"description": "A room with a window.", "exits": {"Street": "north"}}},
    ), patch("builtins.print"):
        game._handle_look_command(None, show_full_look_details=True)
        assert any(action["type"] == "move" for action in game.numbered_actions_context)
        game._handle_look_command("window")
        game._handle_look_command("unknown")

    assert game._handle_take_command(None) == (False, False)
    saved_player = game.player_character
    game.player_character = None
    assert game._handle_take_command("coin") == (False, False)
    game.player_character = saved_player
    assert game._handle_take_command("fixed") == (False, False)
    assert game._handle_take_command("coin") == (True, False)
    assert game._handle_take_command("raskolnikov") == (True, False)
    assert game.player_notoriety_level > 0
    assert npc.add_player_memory.called
    assert game._handle_take_command("missing") == (False, False)

    assert game._handle_drop_command(None) == (False, False)
    game.player_character = None
    assert game._handle_drop_command("coin") == (False, False)
    game.player_character = saved_player
    assert game._handle_drop_command("coin") == (True, False)


@patch("game_engine.command_handler.apply_color_theme", return_value=None)
def test_command_handler_more_branches(_theme):
    state = _make_state()
    state.player_character.get_journal_summary = MagicMock(return_value="J")
    state.gemini_api = SimpleNamespace(model=object(), _generate_content_with_fallback=MagicMock(return_value="alt"))
    state.last_ai_generated_text = "orig"
    handler = CommandHandler(state)

    handler._handle_theme_command(None)
    handler._handle_theme_command("bad")
    handler._handle_verbosity_command(None)
    handler._handle_verbosity_command("bad")
    handler._handle_turnheaders_command(None)
    handler._handle_turnheaders_command("maybe")

    for cmd, arg in [
        ("help", "movement"),
        ("journal", None),
        ("look", "x"),
        ("inventory", None),
        ("drop", "x"),
        ("use", ("x", None, "read")),
        ("objectives", None),
        ("think", None),
        ("wait", None),
        ("talk to", "Sonia"),
        ("persuade", ("Sonia", "please")),
        ("status", None),
        ("history", None),
        ("theme", "default"),
        ("verbosity", "brief"),
        ("turnheaders", "on"),
        ("retry", None),
        ("rephrase", None),
        ("quit", None),
    ]:
        handler._process_command(cmd, arg)


def test_command_handler_input_value_error_and_no_repeat():
    state = _make_state()
    handler = CommandHandler(state)
    state.command_history = []
    state._input_color.return_value = "!!"
    assert handler._get_player_input() == (None, None)
    state._input_color.return_value = "notanumber"
    state.gemini_api.model = None
    assert handler._get_player_input() == (None, None)


class _RespModel:
    def __init__(self, text):
        self.text = text

    def generate_content(self, *_a, **_k):
        return SimpleNamespace(text=self.text)


def test_nlp_parser_branches_and_unsafe():
    api = GeminiAPI()
    parser = NaturalLanguageParser(api)
    assert parser.parse_player_intent("kill myself", {})["intent"] == "unknown"
    api.model = _RespModel('{"intent":"talk","target":123,"confidence":"bad"}')
    out = parser.parse_player_intent("talk to sonia", {"npcs": ["sonia"]})
    assert out["intent"] == "talk" and out["target"] == ""


@patch("game_engine.gemini_interactions.os.path.exists", return_value=True)
def test_gemini_interactive_helpers_and_fallback_error_paths(_exists):
    api = GeminiAPI()
    api._print_color_func = MagicMock()

    # model selection and low-ai prompt
    inputs = iter(["9", "", "y"])
    api._input_color_func = lambda *a, **k: next(inputs)
    selected = api._ask_for_model_selection()
    assert "gemini" in selected
    assert api._prompt_for_low_ai_mode() is True

    # invalid config rename path
    with patch("game_engine.gemini_interactions.os.rename", side_effect=OSError("x")):
        api._rename_invalid_config_file("dummy")

    # _generate_content_with_fallback exception branches
    class E(Exception):
        grpc_status_code = 7

    api.model = SimpleNamespace(generate_content=MagicMock(side_effect=E("denied")))
    txt = api._generate_content_with_fallback("p", "ctx")
    assert "Permission Denied" in txt


def test_world_manager_cover_validate_item_happy_and_update_npcs():
    npc = SimpleNamespace(name="N", is_player=False, current_location="L")
    state = SimpleNamespace(
        current_location_name="L",
        npcs_in_current_location=[],
        all_character_objects={"N": npc},
        _print_color=MagicMock(),
    )
    wm = WorldManager(state)
    wm.update_npcs_in_current_location()
    assert state.npcs_in_current_location and state.npcs_in_current_location[0].name == "N"

    with patch("game_engine.world_manager.LOCATIONS_DATA", {"L": {"items_present": []}}), patch(
        "game_engine.world_manager.CHARACTERS_DATA", {"N": {"inventory_items": []}}
    ), patch("game_engine.world_manager.DEFAULT_ITEMS", {}), patch(
        "game_engine.world_manager.HIGHLY_NOTABLE_ITEMS_FOR_MEMORY", []
    ):
        wm._validate_item_data()


def test_world_manager_interaction_timer_and_move_guard_branches():
    player = SimpleNamespace(name="P", current_location="L")
    state = SimpleNamespace(
        player_character=player,
        _print_color=MagicMock(),
        current_location_name="L",
        _get_matching_exit=MagicMock(return_value=(None, True)),
        gemini_api=SimpleNamespace(model=object()),
        time_since_last_npc_interaction=999,
        npcs_in_current_location=[SimpleNamespace(), SimpleNamespace()],
        event_manager=SimpleNamespace(check_and_trigger_events=MagicMock(return_value=False), attempt_npc_npc_interaction=MagicMock(return_value=True)),
        player_action_count=0,
        actions_since_last_autosave=0,
        autosave_interval_actions=999,
        save_game=MagicMock(),
        key_events_occurred=[],
        last_significant_event_summary=None,
    )
    wm = WorldManager(state)
    wm.advance_time = MagicMock()
    with patch("game_engine.world_manager.random.random", return_value=0.0):
        wm._update_world_state_after_action("look", True, 1)
    assert state.time_since_last_npc_interaction == 0

    assert wm._handle_move_to_command(None) == (False, False)
    state.player_character = None
    assert wm._handle_move_to_command("north") == (False, False)

    state.player_character = player
    with patch("game_engine.world_manager.LOCATIONS_DATA", {}):
        assert wm._handle_move_to_command("north") == (False, False)


@patch("game_engine.gemini_interactions.os.path.exists", return_value=True)
def test_gemini_manual_and_config_exception_branches(_exists, tmp_path):
    api = GeminiAPI()
    api._print_color_func = MagicMock()
    api._log_message = MagicMock()

    # manual flow: empty then skip
    inputs = iter(["", "skip"])
    api._input_color_func = lambda *a, **k: next(inputs)
    out = api._handle_manual_key_input()
    assert out["api_configured"] is False

    # config exception branch
    cfg = tmp_path / "gemini_config.json"
    cfg.write_text("{bad-json")
    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)), patch.object(api, "_rename_invalid_config_file") as r:
        out2 = api._handle_config_file_key()
        assert out2 is None
        assert r.called


def test_gemini_parser_config_and_generation_edge_paths(tmp_path):
    api = GeminiAPI()
    api._log_message = MagicMock()
    api._print_color_func = MagicMock()

    parser = NaturalLanguageParser(api)
    api.model = SimpleNamespace(generate_content=MagicMock(side_effect=RuntimeError("model down")))
    assert parser.parse_player_intent("go north", {"exits": [{"name": "North", "description": "north"}]})[
        "intent"
    ] == "unknown"

    api.model = SimpleNamespace(
        generate_content=MagicMock(
            return_value=SimpleNamespace(
                text='{"intent":"dance","target":123,"confidence":"2.5"}'
            )
        )
    )
    out = parser.parse_player_intent("dance", {"exits": [], "items": [], "npcs": [], "inventory": []})
    assert out == {"intent": "unknown", "target": "", "confidence": 1.0}

    class BadAdapter:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("adapter")

    api.client = object()
    api._load_genai = MagicMock(return_value=True)
    with patch.object(api, "_GeminiModelAdapter", BadAdapter):
        assert parser._select_intent_model() is api.model

    cfg = tmp_path / "gemini_config.json"
    cfg.write_text('{"gemini_api_key":"abc"}')
    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)), patch(
        "game_engine.gemini_interactions.open", side_effect=OSError("cannot open")
    ):
        assert api.load_api_key_from_file() is None

    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)), patch(
        "game_engine.gemini_interactions.open", side_effect=OSError("cannot write")
    ):
        api.save_api_key_to_file("key")

    with patch("game_engine.gemini_interactions.os.path.exists", return_value=True), patch(
        "game_engine.gemini_interactions.os.rename"
    ) as rename:
        api._rename_invalid_config_file("bad_config.json")
        assert rename.called

    assert api._attempt_api_setup("", "test", "model") is False
    api._load_genai = MagicMock(return_value=False)
    assert api._attempt_api_setup("key", "test", "model") is False
    api._load_genai = MagicMock(return_value=True)
    api.genai = None
    assert api._attempt_api_setup("key", "test", "model") is False
    api.genai = SimpleNamespace(Client=MagicMock(side_effect=RuntimeError("client bad")))
    assert api._attempt_api_setup("key", "test", "model") is False

    class EmptyModel:
        def generate_content(self, *_args, **_kwargs):
            return SimpleNamespace(prompt_feedback=SimpleNamespace(block_reason="SAFETY"))

    api.genai = SimpleNamespace(Client=lambda **_kwargs: SimpleNamespace())
    with patch.object(api, "_GeminiModelAdapter", return_value=EmptyModel()):
        assert api._attempt_api_setup("key", "test", "model") is False

    class CandidateModel:
        def generate_content(self, *_args, **_kwargs):
            return SimpleNamespace(candidates=[SimpleNamespace(finish_reason=2)])

    with patch.object(api, "_GeminiModelAdapter", return_value=CandidateModel()):
        assert api._attempt_api_setup("key", "test", "model") is False

    api.model = SimpleNamespace(generate_content=MagicMock(return_value=SimpleNamespace(text=None)))
    assert "unclear or restricted" in api._generate_content_with_fallback("prompt")
    api.model = SimpleNamespace(
        generate_content=MagicMock(return_value=SimpleNamespace(candidates=[SimpleNamespace(finish_reason=2)]))
    )
    assert "Finish Reason: 2" in api._generate_content_with_fallback("prompt")
    api.model = SimpleNamespace(
        generate_content=MagicMock(return_value=SimpleNamespace(text="I cannot fulfill that."))
    )
    assert api._generate_content_with_fallback("prompt") == "I cannot fulfill that."
    api.model = SimpleNamespace(generate_content=MagicMock(side_effect=RuntimeError("plain")))
    assert "muddled due to an error" in api._generate_content_with_fallback("prompt")

    assert api._extract_json_payload("prefix {bad json}") is None
    assert api.generate_npc_response(None, "hello", {})["response_text"].startswith("The character")
    api._generate_content_with_fallback = MagicMock(return_value="")
    assert api.generate_npc_response({"name": "N"}, "hello", {})["response_text"].startswith(
        "The character"
    )
    api._generate_content_with_fallback = MagicMock(return_value='{"response_text":"","stat_changes":[]}')
    assert api.generate_npc_response({"name": "N"}, "hello", {})["response_text"].startswith(
        "The character"
    )
    api._generate_content_with_fallback = MagicMock(
        return_value='{"response_text":"Hi","stat_changes":{"fear":1,"bad":99}}'
    )
    assert api.generate_npc_response({"name": "N"}, 'say "hello"', {}) == {
        "response_text": "Hi",
        "stat_changes": {"fear": 1},
    }


def test_gemini_generate_fallback_block_reason_exception_path():
    api = GeminiAPI()
    api._log_message = MagicMock()

    class Ex(Exception):
        def __init__(self):
            self.response = SimpleNamespace(prompt_feedback=SimpleNamespace(block_reason="SAFETY"))

    api.model = SimpleNamespace(generate_content=MagicMock(side_effect=Ex()))
    txt = api._generate_content_with_fallback("prompt", "ctx")
    assert "blocked" in txt.lower()


def test_gemini_env_failure_and_config_success_save_branch(tmp_path):
    api = GeminiAPI()
    api._log_message = MagicMock()
    api._print_color_func = MagicMock()
    api._input_color_func = MagicMock(return_value="n")

    with patch("game_engine.gemini_interactions.os.getenv", return_value="env-key"), patch.object(
        api, "_attempt_api_setup", return_value=False
    ):
        out = api._handle_env_key()
        assert out["api_configured"] is False

    cfg = tmp_path / "gemini_config.json"
    cfg.write_text('{"gemini_api_key":"abc","chosen_model_name":"gemini-3-pro-preview"}')
    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)), patch("game_engine.gemini_interactions.os.path.exists", return_value=True), patch.object(
        api, "_load_genai", return_value=True
    ), patch.object(api, "_attempt_api_setup", return_value=True), patch.object(
        api, "_prompt_for_low_ai_mode", return_value=True
    ), patch.object(api, "save_api_key_to_file") as save:
        api.chosen_model_name = "gemini-3-flash-preview"
        out2 = api._handle_config_file_key()
        assert out2["api_configured"] is True
        assert save.called


def load_tests(_loader, _tests, _pattern):
    return load_pytest_style_functions(globals())
