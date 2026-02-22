from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from game_engine.character_module import Character, load_characters_data
from game_engine.command_handler import CommandHandler
from game_engine.gemini_interactions import GeminiAPI, NaturalLanguageParser
from game_engine.world_manager import WorldManager
from tests.test_coverage_core_modules import _make_state


def test_load_characters_data_error_paths(tmp_path):
    assert load_characters_data(str(tmp_path / "missing.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json")
    assert load_characters_data(str(bad)) == {}


@patch.dict("game_engine.game_config.DEFAULT_ITEMS", {"rock": {}, "coin": {"value": 1}}, clear=True)
def test_character_edge_paths_inventory_psychology_and_memory_formats():
    c = Character("C", "p", "g", "L", ["L"], objectives=[], is_player=False)
    c.apply_psychology_changes(None)
    c.apply_psychology_changes({"suspicion": "2", "fear": -999, "unknown": 4})
    assert 0 <= c.psychology["fear"] <= 100

    assert c.add_to_inventory("rock", 3) is True
    assert c.remove_from_inventory("rock", 2) is False
    assert c.add_to_inventory("coin", 2) is True
    assert c.remove_from_inventory("coin", 5) is False
    assert c.has_item("rock", 2) is False

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
