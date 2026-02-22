from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from game_engine.character_module import Character
from game_engine.gemini_interactions import GeminiAPI
from game_engine.world_manager import WorldManager
from game_engine.command_handler import CommandHandler
from tests.test_coverage_core_modules import _make_state


@patch.dict(
    "game_engine.game_config.DEFAULT_ITEMS",
    {
        "coin": {"value": 1},
        "book": {"description": "book", "is_notable": True},
        "worn coin": {"value": 1, "notable_threshold": 20},
    },
    clear=True,
)
def test_character_inventory_and_memory_and_objectives():
    obj = {
        "id": "o1",
        "description": "Do thing",
        "stages": [
            {"stage_id": "s1", "description": "start", "next_stages": ["s2"]},
            {"stage_id": "s2", "description": "next"},
        ],
    }
    c = Character("C", "p", "g", "L", ["L"], objectives=[obj], is_player=True)
    c.add_journal_entry("note", "hello", "Day 1")
    assert "NOTE" in c.get_journal_summary()
    assert c.add_to_inventory("coin", 3) is True
    assert c.has_item("coin", 2) is True
    assert c.remove_from_inventory("coin", 1) is True
    assert "coin" in c.get_inventory_description()

    c.inventory.append({"name": "book"})
    c.inventory.append({"name": "worn coin", "quantity": 30})
    s = c.get_notable_carried_items_summary()
    assert "book" in s and "sum of money" in s

    c.add_to_history("N", "C", "hi")
    assert "hi" in c.get_formatted_history("N")

    c.add_player_memory("dialogue_exchange", 5, {"player_statement": "test", "topic_hint": "crime"}, 1)
    c.add_player_memory("player_action_observed", 1, {"action": "took", "target_item": "axe", "location": "L"}, 0)
    c.add_player_memory("relationship_change", 0, {"change": -1, "reason": "rude"}, -1)
    summary = c.get_player_memory_summary(current_turn=6)
    assert "Key things you recall" in summary

    c.update_relationship("you are kind but foolish", ["kind"], ["foolish"], game_turn=7)
    assert -10 <= c.relationship_with_player <= 10

    assert c.get_objective_by_id("o1") is not None
    assert c.get_current_stage_for_objective("o1")["stage_id"] == "s1"
    assert c.advance_objective_stage("o1", "s2") is True
    assert c.complete_objective("o1") is True
    assert c.activate_objective("o1", set_stage_id="s1") is True


@patch("game_engine.character_module.random.randint", return_value=6)
def test_character_dict_roundtrip_and_skill(_r):
    static = {
        "persona": "p",
        "greeting": "g",
        "default_location": "L",
        "accessible_locations": ["L"],
        "objectives": [{"id": "o", "description": "d", "stages": [{"stage_id": "a", "description": "A"}]}],
    }
    data = {
        "name": "C",
        "current_location": "L",
        "inventory": [],
        "objectives": [{"id": "o", "current_stage_id": "missing", "stages": [{"stage_id": "a", "description": "A"}]}],
    }
    c = Character.from_dict(data, static)
    dumped = c.to_dict()
    assert dumped["name"] == "C"
    c.skills["persuasion"] = 2
    assert c.check_skill("persuasion", difficulty_threshold=4) is True


def test_gemini_wrapper_methods_call_fallback_and_dialogue_history():
    api = GeminiAPI()
    api._generate_content_with_fallback = MagicMock(return_value="text")
    npc = SimpleNamespace(
        name="NPC",
        apparent_state="calm",
        persona="persona",
        relationship_with_player=0,
        add_to_history=MagicMock(),
        get_formatted_history=MagicMock(return_value=""),
        psychology={"suspicion": 0, "fear": 0, "respect": 50},
        apply_psychology_changes=MagicMock(),
    )
    player = SimpleNamespace(name="Player", apparent_state="tense", persona="p", add_to_history=MagicMock(), get_formatted_history=MagicMock(return_value=""))

    assert api.get_player_reflection(player, "L", "Morning", "ctx") == "text"
    assert api.get_atmospheric_details(player, "L", "Morning") == "text"
    assert api.get_npc_to_npc_interaction(npc, npc, "L", "Morning") == "text"
    assert api.get_item_interaction_description(player, "item", {"description": "d"}) == "text"
    assert api.get_dream_sequence(player, "events", "obj", "rels") == "text"
    assert api.get_rumor_or_gossip(npc, "L", "Morning", "facts", 0, "neutral", "obj") == "text"
    assert api.get_newspaper_article_snippet("topic", "L", "Morning", "facts") == "text"
    assert api.get_scenery_observation(player, "L", "desc", "Morning") == "text"
    assert api.get_generated_text_document("letter", "prompt", "ctx") == "text"
    assert api.get_enhanced_observation(player, "NPC", "person", "base", "ctx") == "text"
    assert api.get_street_life_event_description("L", "Morning", "ctx") == "text"

    api._generate_content_with_fallback = MagicMock(return_value='"Reply"')
    api.generate_npc_response = MagicMock(return_value={"response_text": "\"Reply\""})
    out = api.get_npc_dialogue(npc, player, "Hello", "L", "Morning", "neutral", "memory")
    assert out == "Reply"
    assert npc.add_to_history.called and player.add_to_history.called

    api._generate_content_with_fallback = MagicMock(return_value="Persuaded")
    out2 = api.get_npc_dialogue_persuasion_attempt(npc, player, "Please", "L", "Morning", "neutral", "memory", "normal", "none", "events", "obj", "pobj", "SUCCESS")
    assert out2 == "Persuaded"


def test_world_manager_branches_for_move_endings_and_world_state_updates():
    player = SimpleNamespace(
        name="Rodion Raskolnikov",
        current_location="Start",
        apparent_state="normal",
        get_objective_by_id=MagicMock(return_value={"completed": True}),
        get_current_stage_for_objective=MagicMock(return_value={"is_ending_stage": True, "description": "ending"}),
    )
    state = SimpleNamespace(
        current_location_name="Start",
        player_character=player,
        _print_color=MagicMock(),
        _get_matching_exit=MagicMock(return_value=("Pawnbroker's Apartment", False)),
        current_location_description_shown_this_visit=True,
        last_significant_event_summary=None,
        player_notoriety_level=0,
        low_ai_data_mode=True,
        gemini_api=SimpleNamespace(model=None),
        npcs_in_current_location=[],
        event_manager=SimpleNamespace(check_and_trigger_events=MagicMock(return_value=True), attempt_npc_npc_interaction=MagicMock(return_value=False)),
        key_events_occurred=[],
        player_action_count=0,
        actions_since_last_autosave=0,
        autosave_interval_actions=1,
        save_game=MagicMock(),
        time_since_last_npc_interaction=999,
    )
    wm = WorldManager(state)
    with patch("game_engine.world_manager.LOCATIONS_DATA", {"Start": {"exits": {"Pawnbroker's Apartment": "north"}}, "Pawnbroker's Apartment": {"exits": {}}}):
        wm.update_current_location_details = MagicMock()
        moved, shown = wm._handle_move_to_command("north")
        assert moved and shown
    assert state.player_notoriety_level > 0

    wm.advance_time = MagicMock()
    wm._update_world_state_after_action("look", True, 5)
    assert state.save_game.called
    assert wm._check_game_ending_conditions() is True


def test_gemini_attempt_api_setup_success_and_failure_paths():
    api = GeminiAPI()
    logs = []
    api._print_color_func = lambda *args, **kwargs: logs.append(args[0])

    class GoodModel:
        def generate_content(self, *_a, **_k):
            return SimpleNamespace(text="test")

    class BadModel:
        def generate_content(self, *_a, **_k):
            return SimpleNamespace(text="nope")

    with patch.object(api, "_load_genai", return_value=True):
        api.genai = SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(models=SimpleNamespace(generate_content=lambda *a, **k: SimpleNamespace(text="test"))))
        assert api._attempt_api_setup("k", "src", "m") is True

        with patch.object(api, "_GeminiModelAdapter", return_value=BadModel()):
            assert api._attempt_api_setup("k", "src", "m") is False

        with patch.object(api, "_GeminiModelAdapter", side_effect=RuntimeError("boom")):
            assert api._attempt_api_setup("k", "src", "m") is False


@patch("game_engine.gemini_interactions.os.getenv", return_value="env-key")
def test_gemini_handle_env_and_config_and_generate_fallback(_getenv, tmp_path):
    api = GeminiAPI()
    api._log_message = MagicMock()
    api._print_color_func = MagicMock()
    api._input_color_func = MagicMock(return_value="n")

    with patch.object(api, "_attempt_api_setup", return_value=True):
        out = api._handle_env_key()
        assert out["api_configured"] is True

    cfg = tmp_path / "gemini_config.json"
    cfg.write_text('{"gemini_api_key":"abc","chosen_model_name":"gemini-3-flash-preview"}')
    with patch("game_engine.gemini_interactions.API_CONFIG_FILE", str(cfg)), patch.object(api, "_load_genai", return_value=True), patch.object(
        api, "_attempt_api_setup", return_value=False
    ), patch.object(api, "_rename_invalid_config_file"):
        out2 = api._handle_config_file_key()
        assert out2 is None

    api.model = None
    assert "Gemini API not configured" in api._generate_content_with_fallback("p", "ctx")

    api.model = SimpleNamespace(generate_content=lambda *a, **k: SimpleNamespace(text=""))
    out3 = api._generate_content_with_fallback("p", "ctx")
    assert "unclear or restricted" in out3


@patch.dict("game_engine.command_handler.DEFAULT_ITEMS", {"book": {"is_notable": True}}, clear=True)
def test_command_handler_hint_construction_branches():
    state = _make_state()
    state.numbered_actions_context = [
        {"type": "talk", "target": "Sonia"},
        {"type": "take", "target": "book"},
        {"type": "look_at_item", "target": "book"},
        {"type": "move", "target": "Street"},
    ]
    state._input_color.return_value = "inventory"
    handler = CommandHandler(state)
    cmd, arg = handler._get_player_input()
    assert (cmd, arg) == ("inventory", None)


def test_world_manager_advance_time_new_day_with_dream_static():
    player = SimpleNamespace(
        name="Rodion Raskolnikov",
        apparent_state="feverish",
        add_journal_entry=MagicMock(),
        add_player_memory=MagicMock(),
    )
    sonya = SimpleNamespace(relationship_with_player=1)
    state = SimpleNamespace(
        game_time=95,
        current_day=1,
        _print_color=MagicMock(),
        key_events_occurred=[],
        last_significant_event_summary=None,
        player_character=player,
        all_character_objects={"Sonya Marmeladova": sonya},
        low_ai_data_mode=True,
        gemini_api=SimpleNamespace(model=None, get_dream_sequence=MagicMock()),
        _get_recent_events_summary=lambda: "events",
        _get_objectives_summary=lambda c: "obj",
        get_relationship_text=lambda r: "neutral",
        _get_current_game_time_period_str=lambda: "Day 2, Morning",
        time_since_last_npc_interaction=0,
        time_since_last_npc_schedule_update=0,
    )
    wm = WorldManager(state)
    with patch("game_engine.world_manager.MAX_TIME_UNITS_PER_DAY", 100), patch("game_engine.world_manager.random.random", return_value=0.0), patch(
        "game_engine.world_manager.STATIC_DREAM_SEQUENCES", ["blood and terror"]
    ):
        wm.update_npc_locations_by_schedule = MagicMock()
        wm.advance_time(10)
    assert state.current_day == 2
    assert player.add_journal_entry.called
