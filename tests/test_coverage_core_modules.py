import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from game_engine.command_handler import CommandHandler
from game_engine.gemini_interactions import GeminiAPI, NaturalLanguageParser
from game_engine.world_manager import WorldManager


class DummyNPC:
    def __init__(self, name):
        self.name = name


def _make_state():
    state = SimpleNamespace()
    state.command_history = []
    state.max_command_history = 3
    state.current_location_name = "room"
    state.dynamic_location_items = {
        "room": [{"name": "apple"}, {"name": "apricot"}, {"name": "book"}]
    }
    state.player_character = SimpleNamespace(inventory=[{"name": "coin"}, {"name": "cloak"}], apparent_state="calm")
    state.npcs_in_current_location = [DummyNPC("Sonia"), DummyNPC("Svidrigailov")]
    state.numbered_actions_context = []
    state.gemini_api = SimpleNamespace(model=None)
    state.nl_parser = MagicMock()
    state._print_color = MagicMock()
    state._describe_item_brief = lambda name: f"desc-{name}"
    state._describe_npc_brief = lambda name: f"npc-{name}"
    state._get_current_game_time_period_str = lambda: "Day 1, Morning"
    state._get_mode_label = lambda: "mode"
    state._prompt_arrow = lambda: ">"
    state._input_color = MagicMock(return_value="look")
    state.turn_headers_enabled = True
    state.color_theme = "default"
    state.verbosity_level = "standard"
    state.low_ai_data_mode = False
    state.last_ai_generated_text = None
    state._apply_verbosity = lambda text: text
    state._remember_ai_output = MagicMock()
    # command hooks used by _process_command
    state._handle_look_command = MagicMock()
    state._handle_take_command = MagicMock(return_value=(True, True))
    state._handle_drop_command = MagicMock(return_value=(True, False))
    state._handle_use_command = MagicMock(return_value=True)
    state._handle_talk_to_command = MagicMock(return_value=(True, True))
    state._handle_persuade_command = MagicMock(return_value=(False, False))
    state._handle_wait_command = MagicMock(return_value=10)
    state._handle_think_command = MagicMock()
    state._handle_inventory_command = MagicMock()
    state._handle_status_command = MagicMock()
    state._display_command_history = MagicMock()
    state.display_help = MagicMock()
    state.display_objectives = MagicMock()
    state.save_game = MagicMock()
    state.load_game = MagicMock(return_value=True)
    state.handle_use_item = MagicMock(return_value=True)
    state.world_manager = SimpleNamespace(_handle_move_to_command=MagicMock(return_value=(True, True)))
    return state


def test_parse_action_patterns_and_synonyms():
    handler = CommandHandler(_make_state())
    assert handler.parse_action("give apple to sonia") == ("use", ("apple", "sonia", "give"))
    assert handler.parse_action("read letter") == ("use", ("letter", None, "read"))
    assert handler.parse_action("use axe on door") == ("use", ("axe", "door", "use_on"))
    assert handler.parse_action("argue with sonia that repent") == (
        "persuade",
        ("sonia", "repent"),
    )


def test_record_command_history_and_canonical_formats():
    state = _make_state()
    handler = CommandHandler(state)
    handler._record_command_history("use", ("book", "Sonia", "give"))
    handler._record_command_history("use", ("letter", None, "read"))
    handler._record_command_history("use", ("key", "door", "use_on"))
    handler._record_command_history("look", None)
    assert state.command_history == [
        "read letter",
        "use key on door",
        "look",
    ]


def test_prefix_resolution_and_matching_helpers():
    state = _make_state()
    handler = CommandHandler(state)
    match, ambiguous = handler._get_matching_location_item("boo")
    assert not ambiguous and match["name"] == "book"
    match, ambiguous = handler._get_matching_location_item("ap")
    assert match is None and ambiguous
    npc, ambiguous = handler._get_matching_npc("son")
    assert npc.name == "Sonia" and not ambiguous
    inv, ambiguous = handler._get_matching_inventory_item("cl")
    assert inv["name"] == "cloak" and not ambiguous


def test_get_player_input_fast_map_and_nlp_fallback():
    state = _make_state()
    handler = CommandHandler(state)
    state._input_color.return_value = "n"
    assert handler._get_player_input() == ("move to", "north")

    state._input_color.return_value = "unknown action"
    state.gemini_api.model = object()
    handler._interpret_with_nlp = MagicMock(return_value=("take", "apple"))
    assert handler._get_player_input() == ("take", "apple")


def test_intent_handling_and_examples():
    state = _make_state()
    handler = CommandHandler(state)
    state.nl_parser.parse_player_intent.return_value = {
        "intent": "move",
        "target": "Street",
        "confidence": 0.8,
    }
    assert handler._interpret_with_nlp("go") == ("move to", "Street")

    state.nl_parser.parse_player_intent.return_value = {
        "intent": "unknown",
        "target": "",
        "confidence": 0.2,
    }
    assert handler._interpret_with_nlp("???") == (None, None)
    assert handler._get_contextual_command_examples()[0] == "look"


def test_process_command_for_control_and_ui_commands():
    state = _make_state()
    handler = CommandHandler(state)

    assert handler._process_command("save", "slot")[0] is False
    assert handler._process_command("load", "slot")[3] == "load_triggered"
    assert handler._process_command("toggle_lowai", None) == (False, False, 0, False)
    assert handler._process_command("move to", "street")[0] is True
    assert handler._process_command("take", "apple")[0] is True


def test_theme_verbosity_turnheaders_and_retry_paths():
    state = _make_state()
    handler = CommandHandler(state)

    with patch("game_engine.command_handler.apply_color_theme", return_value="default"):
        handler._handle_theme_command("default")
    handler._handle_verbosity_command("brief")
    assert state.verbosity_level == "brief"
    handler._handle_turnheaders_command("off")
    assert state.turn_headers_enabled is False

    state.last_ai_generated_text = "Original text"
    state.gemini_api = SimpleNamespace(model=object(), _generate_content_with_fallback=MagicMock(return_value="New text"))
    assert handler._handle_retry_or_rephrase("retry") is True


class _Model:
    def __init__(self, text):
        self._text = text

    def generate_content(self, *_args, **_kwargs):
        return SimpleNamespace(text=self._text)


def test_natural_language_parser_defaults_and_success():
    api = GeminiAPI()
    api.model = _Model('{"intent":"take","target":"apple","confidence":0.9}')
    parser = NaturalLanguageParser(api)
    assert parser.parse_player_intent("", {})["intent"] == "unknown"
    out = parser.parse_player_intent("take apple", {"items": ["apple"]})
    assert out["intent"] == "take"


def test_gemini_api_json_and_config_helpers(tmp_path):
    api = GeminiAPI()
    assert api._extract_json_payload("```json\n{\"a\":1}\n```") == {"a": 1}
    assert api._extract_json_payload("not json") is None

    cfg = tmp_path / "gemini_config.json"
    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)):
        api.save_api_key_to_file("k-123")
        assert api.load_api_key_from_file() == "k-123"


def test_world_manager_time_period_and_item_initialization():
    state = SimpleNamespace(
        game_time=0,
        current_day=1,
        _print_color=MagicMock(),
        key_events_occurred=[],
        last_significant_event_summary=None,
        player_character=None,
        time_since_last_npc_interaction=0,
        time_since_last_npc_schedule_update=0,
        dynamic_location_items={},
    )
    wm = WorldManager(state)
    period = wm.get_current_time_period()
    assert isinstance(period, str)

    with patch("game_engine.world_manager.LOCATIONS_DATA", {"A": {"items_present": [{"name": "x"}]}}), patch(
        "game_engine.world_manager.DEFAULT_ITEMS", {"secret": {"hidden_in_location": "A", "stackable": True, "quantity": 2}}
    ):
        wm.initialize_dynamic_location_items()
    assert any(i["name"] == "secret" for i in state.dynamic_location_items["A"])


def test_world_manager_select_player_character_non_interactive():
    state = SimpleNamespace(_print_color=MagicMock(), _input_color=MagicMock())
    wm = WorldManager(state)
    with patch(
        "game_engine.world_manager.CHARACTERS_DATA",
        {
            "Rodya": {"default_location": "A", "accessible_locations": ["A"]},
            "NPC": {"default_location": "A", "non_playable": True},
        },
    ), patch.object(wm, "initialize_dynamic_location_items"), patch.object(wm, "update_npcs_in_current_location"), patch("game_engine.world_manager.Character") as ccls:
        ccls.return_value = SimpleNamespace(name="Rodya", apparent_state="calm", inventory=[], default_location="A", current_location="A")
        assert wm.load_all_characters(from_save=False) is None
        assert wm.select_player_character(non_interactive=True) is True


def test_get_player_input_numbered_actions_and_repeat_shortcuts():
    state = _make_state()
    state.numbered_actions_context = [
        {"type": "move", "target": "north"},
        {"type": "talk", "target": "Sonia"},
        {"type": "take", "target": "book"},
        {"type": "look_at_item", "target": "book"},
        {"type": "look_at_npc", "target": "Sonia"},
        {"type": "select_item", "target": "book"},
    ]
    handler = CommandHandler(state)
    for idx, expected in [
        ("1", ("move to", "north")),
        ("2", ("talk to", "Sonia")),
        ("3", ("take", "book")),
        ("4", ("look", "book")),
        ("5", ("look", "Sonia")),
        ("6", ("select_item", "book")),
    ]:
        state._input_color.return_value = idx
        assert handler._get_player_input() == expected

    state.command_history = ["look"]
    state._input_color.return_value = "!!"
    assert handler._get_player_input() == ("look", None)


def test_process_command_select_item_subactions_and_unknown():
    state = _make_state()
    handler = CommandHandler(state)
    state._input_color.return_value = "give to sonia"
    assert handler._process_command("select_item", "book")[0] is True
    state._input_color.return_value = "use on door"
    assert handler._process_command("select_item", "book")[0] is True
    state._input_color.return_value = "invalid"
    assert handler._process_command("select_item", "book")[0] is False
    assert handler._process_command("unknowncmd", None)[0] is False


def test_world_manager_validate_items_and_ambient_rumors_and_unknown_time():
    state = SimpleNamespace(
        game_time=-999,
        _print_color=MagicMock(),
        current_location_name="Haymarket Square",
        npcs_in_current_location=[],
        low_ai_data_mode=True,
        gemini_api=SimpleNamespace(model=None),
        player_character=SimpleNamespace(
            name="Rodion Raskolnikov",
            apparent_state="normal",
            add_journal_entry=MagicMock(),
        ),
        _get_current_game_time_period_str=lambda: "Day 1, Morning",
        _apply_verbosity=lambda t: t,
        _remember_ai_output=MagicMock(),
        _get_known_facts_summary=lambda: "facts",
        get_relationship_text=lambda _: "neutral",
        _get_objectives_summary=lambda _: "obj",
        player_notoriety_level=0,
    )
    wm = WorldManager(state)
    with patch("game_engine.world_manager.TIME_PERIODS", {"Morning": (0, 1)}):
        assert wm.get_current_time_period() == "Unknown"

    with patch("game_engine.world_manager.LOCATIONS_DATA", {"A": {"items_present": [{"name": "ghost"}]}}), patch(
        "game_engine.world_manager.CHARACTERS_DATA", {"N": {"inventory_items": [{"name": "ghost2"}]}}
    ), patch("game_engine.world_manager.DEFAULT_ITEMS", {"x": {"hidden_in_location": "Missing"}}), patch(
        "game_engine.world_manager.HIGHLY_NOTABLE_ITEMS_FOR_MEMORY", ["missing"]
    ):
        wm._validate_item_data()

    with patch("game_engine.world_manager.random.random", return_value=0.0), patch(
        "game_engine.world_manager.STATIC_RUMORS", ["murder by axe"]
    ):
        wm._handle_ambient_rumors()
    assert state.player_character.apparent_state == "paranoid"


def test_world_manager_update_npc_schedule_and_move_failures():
    npc = SimpleNamespace(
        name="NPC",
        is_player=False,
        schedule={"Morning": "B"},
        current_location="A",
        accessible_locations=["A", "B"],
    )
    state = SimpleNamespace(
        game_time=0,
        all_character_objects={"NPC": npc},
        current_location_name="A",
        _print_color=MagicMock(),
        npcs_in_current_location=[],
        player_character=None,
    )
    wm = WorldManager(state)
    with patch("game_engine.world_manager.random.random", return_value=0.0), patch(
        "game_engine.world_manager.LOCATIONS_DATA", {"A": {}, "B": {}}
    ):
        wm.update_npc_locations_by_schedule()
    assert npc.current_location == "B"

    state.player_character = SimpleNamespace(name="P", current_location="A")
    state._get_matching_exit = MagicMock(return_value=(None, False))
    with patch("game_engine.world_manager.LOCATIONS_DATA", {"A": {"exits": {}}}):
        moved, shown = wm._handle_move_to_command("north")
        assert moved is shown is False
