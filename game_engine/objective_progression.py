# objective_progression.py
"""Drives player objective-stage advancement in response to gameplay events.

The objective *stages* live in the character data (`data/characters.json`); this
module supplies the *transitions* between them — which the data never wired — plus
the few side effects that accompany a beat (e.g. Sonya offering Raskolnikov her
cross). It is the single place that decides how a playable protagonist's story
moves toward an ending.

Design:
- Each playable protagonist has one ending-bearing "main" objective
  (`MAIN_OBJECTIVE_BY_CHARACTER`). The game-ending check looks only at that
  objective, so completing a *secondary* objective that happens to carry an
  `is_ending_stage` does NOT end the story.
- Intermediate stages advance one step per relevant interaction (talk / persuade /
  give); the stage itself is the counter.
- Every *final* (ending) transition is gated behind the deliberate `confess`
  capstone act, so endings are earned rather than tripped during exploration.
- `evaluate_player_progression` is null-safe and never raises; a failure here must
  not break the action that triggered it.
"""

from .game_config import Colors, DEBUG_LOGS

# The one ending-bearing objective per playable protagonist.
MAIN_OBJECTIVE_BY_CHARACTER = {
    "Rodion Raskolnikov": "grapple_with_crime",
    "Sonya Marmeladova": "guide_raskolnikov",
    "Porfiry Petrovich": "solve_murders",
}

# Exact data keys (must match data/locations.json / data/characters.json).
_POLICE = "Police Station (General Area)"
_HAYMARKET = "Haymarket Square"
_PUBLIC_CONFESSION_LOCATIONS = {_POLICE, _HAYMARKET}
_CROSS = "sonya's cypress cross"

_SONYA = "Sonya Marmeladova"
_PORFIRY = "Porfiry Petrovich"
_RODION = "Rodion Raskolnikov"
_LUZHIN = "Pyotr Petrovich Luzhin"
_SVIDRIGAILOV = "Arkady Svidrigailov"
_DUNYA = "Dunya Raskolnikova"


def _npc_present(name):
    return lambda game: any(
        getattr(n, "name", None) == name
        for n in getattr(game, "npcs_in_current_location", []) or []
    )


def _at_any(locations):
    return lambda game: getattr(game, "current_location_name", None) in locations


def _stage_not_at(obj_id, stage_id):
    """Return a predicate that is True when the given objective is NOT at stage_id.

    Used to prevent a side-quest event from incidentally firing a main-arc rule
    when the same NPC is involved in both.
    """
    def _predicate(game):
        pc = getattr(game, "player_character", None)
        if pc is None:
            return True
        obj = pc.get_objective_by_id(obj_id)
        if not obj or not obj.get("active"):
            return True
        stage = pc.get_current_stage_for_objective(obj_id)
        return stage is None or stage.get("stage_id") != stage_id
    return _predicate


# Each rule: objective_id, from-stage, event, optional target / secondary match,
# optional require(game) predicate, to-stage, optional item to grant, narration.
_RULES = {
    _RODION: [
        # --- grapple_with_crime (main) ---
        {"obj": "grapple_with_crime", "from": "initial_turmoil", "event": "talk_to",
         "target": _SONYA, "to": "seek_sonya",
         "narrate": "Sonya's quiet suffering draws you, almost against your will, toward the thought of confession."},
        {"obj": "grapple_with_crime", "from": "initial_turmoil", "event": "talk_to",
         "target": _PORFIRY, "to": "engage_porfiry_intellectually",
         "narrate": "The duel with Porfiry begins; you resolve to match wits and conceal the truth."},
        {"obj": "grapple_with_crime", "from": "initial_turmoil", "event": "talk_to",
         "target": _SVIDRIGAILOV,
         # Only advance the main arc when the player is not in the middle of the
         # family side-quest at the "confront Svidrigailov about Dunya" step, so
         # the help_family arc cannot silently hijack the main moral arc.
         "require": _stage_not_at("help_family", "confront_luzhin"),
         "to": "isolate_further",
         "narrate": "Svidrigailov's casual abyss pulls at you; you feel yourself drifting from all human warmth."},
        {"obj": "grapple_with_crime", "from": "initial_turmoil", "event": "use_item",
         "target": "cheap vodka", "to": "isolate_further",
         "narrate": "The vodka's oblivion only deepens your isolation."},
        # Convergence: Sonya offers her cross from any of the three first branches.
        {"obj": "grapple_with_crime", "from": "seek_sonya", "event": "talk_to",
         "target": _SONYA, "to": "received_cross_from_sonya", "grant": _CROSS,
         "narrate": "Sonya presses her cypress cross into your hand. \"Take it — we will go to suffering together.\""},
        {"obj": "grapple_with_crime", "from": "engage_porfiry_intellectually", "event": "talk_to",
         "target": _SONYA, "to": "received_cross_from_sonya", "grant": _CROSS,
         "narrate": "Sonya presses her cypress cross into your hand, and your defenses waver."},
        {"obj": "grapple_with_crime", "from": "isolate_further", "event": "talk_to",
         "target": _SONYA, "to": "received_cross_from_sonya", "grant": _CROSS,
         "narrate": "Even in your isolation, Sonya presses her cypress cross into your hand."},
        # Capstone: confess to Sonya (she must be present).
        {"obj": "grapple_with_crime", "from": "received_cross_from_sonya", "event": "confess",
         "require": _npc_present(_SONYA), "to": "confessed_to_sonya",
         "narrate": "The words break out of you at last. Sonya hears your confession and does not turn away."},
        # Endings (each from a distinct path / place).
        {"obj": "grapple_with_crime", "from": "confessed_to_sonya", "event": "confess",
         "require": _at_any({_POLICE}), "to": "siberia",
         "narrate": "At the police station, cross in hand, you give yourself up — and turn toward Siberia and the slow hope of rebirth."},
        {"obj": "grapple_with_crime", "from": "confessed_to_sonya", "event": "confess",
         "require": _at_any({_HAYMARKET}), "to": "public_confession",
         "narrate": "You kneel in the Haymarket, kiss the earth, and confess your crime before the crowd."},
        {"obj": "grapple_with_crime", "from": "isolate_further", "event": "confess",
         "require": _at_any(_PUBLIC_CONFESSION_LOCATIONS), "to": "unrepentant_end",
         "narrate": "You confess, but without contrition — your theory intact, your heart cold. There is no rebirth here."},
        # --- understand_theory (secondary) ---
        {"obj": "understand_theory", "from": "initial_validation", "event": "talk_to",
         "target": _PORFIRY, "to": "challenged_by_reality",
         "narrate": "Porfiry's probing makes the theory feel less like granite and more like sand."},
        {"obj": "understand_theory", "from": "challenged_by_reality", "event": "talk_to",
         "target": _SONYA, "to": "theory_shattered",
         "narrate": "Beside Sonya's faith, the 'extraordinary man' looks like a sickness, not a truth."},
        # --- help_family (secondary; does not end the game) ---
        {"obj": "help_family", "from": "learn_of_arrival", "event": "talk_to",
         "target": _LUZHIN, "to": "confront_luzhin"},
        {"obj": "help_family", "from": "confront_luzhin", "event": "talk_to",
         "target": _SVIDRIGAILOV, "to": "warn_dunya_svidrigailov"},
        {"obj": "help_family", "from": "warn_dunya_svidrigailov", "event": "talk_to",
         "target": _DUNYA, "to": "family_secure",
         "narrate": "Dunya is warned and safe; your mother breathes a little easier."},
    ],
    _SONYA: [
        {"obj": "guide_raskolnikov", "from": "initial_encounter", "event": "talk_to",
         "target": _RODION, "to": "lazarus_reading",
         "narrate": "You read to him the raising of Lazarus; the words tremble in the candlelight."},
        {"obj": "guide_raskolnikov", "from": "lazarus_reading", "event": "talk_to",
         "target": _RODION, "to": "offer_cross",
         "narrate": "You sense the moment has come to offer him your cypress cross."},
        {"obj": "guide_raskolnikov", "from": "offer_cross", "event": "give_item",
         "target": _CROSS, "secondary": _RODION, "to": "receive_confession",
         "narrate": "He takes the cross. The walls he built around himself begin to give way."},
        # Capstone: resolve to follow him (Raskolnikov present).
        {"obj": "guide_raskolnikov", "from": "receive_confession", "event": "confess",
         "require": _npc_present(_RODION), "to": "follow_to_siberia",
         "narrate": "You make your choice without hesitation: you will follow him into exile and share his suffering."},
    ],
    _PORFIRY: [
        {"obj": "solve_murders", "from": "initial_suspicion", "event": "talk_to",
         "target": _RODION, "to": "psychological_probes",
         "narrate": "A few idle questions, and the young man's composure flickers. The probing has begun."},
        {"obj": "solve_murders", "from": "psychological_probes", "event": "persuade",
         "target": _RODION, "to": "closing_the_net",
         "narrate": "You let him glimpse how much you understand of his mind. The net draws tighter."},
        {"obj": "solve_murders", "from": "closing_the_net", "event": "persuade",
         "target": _RODION, "to": "encourage_confession",
         "narrate": "You offer him the one door left open: confess, and the suffering may be lighter."},
        # Capstone: press him to confession (Raskolnikov present).
        {"obj": "solve_murders", "from": "encourage_confession", "event": "confess",
         "require": _npc_present(_RODION), "to": "case_solved",
         "narrate": "You lay the truth before him plainly, and at last Raskolnikov breaks and confesses. The case is solved."},
    ],
}


def _target_matches(rule_value, actual):
    if rule_value is None:
        return True
    if actual is None:
        return False
    return str(rule_value).lower() == str(actual).lower()


def evaluate_player_progression(game, event, target=None, secondary=None):
    """Advance the player character's objectives in response to a gameplay event.

    Returns True if at least one objective advanced. Never raises: progression must
    not break the action that triggered it.
    """
    try:
        pc = getattr(game, "player_character", None)
        if pc is None:
            return False
        rules = _RULES.get(getattr(pc, "name", None))
        if not rules:
            return False

        advanced_objs = set()
        for rule in rules:
            obj_id = rule["obj"]
            if obj_id in advanced_objs:
                continue  # at most one advance per objective per event
            if rule["event"] != event:
                continue
            obj = pc.get_objective_by_id(obj_id)
            if not obj or not obj.get("active") or obj.get("completed"):
                continue
            current = pc.get_current_stage_for_objective(obj_id)
            if not current or current.get("stage_id") != rule["from"]:
                continue
            if not _target_matches(rule.get("target"), target):
                continue
            if not _target_matches(rule.get("secondary"), secondary):
                continue
            require = rule.get("require")
            if require is not None and not require(game):
                continue

            if pc.advance_objective_stage(obj_id, rule["to"]):
                advanced_objs.add(obj_id)
                grant = rule.get("grant")
                if grant and not pc.has_item(grant):
                    pc.add_to_inventory(grant, 1)
                narrate = rule.get("narrate")
                if narrate:
                    game._print_narrative(narrate, Colors.CYAN + Colors.BOLD)
        return bool(advanced_objs)
    except Exception as exc:
        # Progression is best-effort; an unexpected state must never break the
        # talk/give/persuade/confess action that called us.
        if DEBUG_LOGS:
            import traceback
            print(f"[DEBUG] evaluate_player_progression error (event={event!r}, target={target!r}): {exc}")
            traceback.print_exc()
        return False


def validate_rules(characters_data, locations_data, items_data):
    """Warn at startup when _RULES reference strings that don't exist in data.

    Called once by world_manager during initialization so content drift is caught
    early rather than at runtime when a rule silently fails to match.
    """
    warnings = []
    all_item_names = set(items_data.keys())

    for char_name, rules in _RULES.items():
        char = characters_data.get(char_name)
        if char is None:
            warnings.append(f"  _RULES: unknown character {char_name!r}")
            continue
        obj_map = {o["id"]: o for o in char.get("objectives", [])}
        for i, rule in enumerate(rules):
            obj_id = rule["obj"]
            obj = obj_map.get(obj_id)
            if obj is None:
                warnings.append(f"  _RULES[{char_name}][{i}]: unknown objective {obj_id!r}")
                continue
            stage_ids = {s["stage_id"] for s in obj.get("stages", [])}
            for key in ("from", "to"):
                s = rule.get(key)
                if s and s not in stage_ids:
                    warnings.append(
                        f"  _RULES[{char_name}][{i}] obj={obj_id!r}: unknown {key}-stage {s!r}"
                    )
            tgt = rule.get("target")
            if tgt and tgt not in characters_data and tgt not in all_item_names:
                warnings.append(
                    f"  _RULES[{char_name}][{i}] obj={obj_id!r}: target {tgt!r} not in characters or items"
                )
            grant = rule.get("grant")
            if grant and grant not in all_item_names:
                warnings.append(
                    f"  _RULES[{char_name}][{i}] obj={obj_id!r}: grant item {grant!r} not in items"
                )

    if warnings:
        print("[WARNING] objective_progression._RULES has data mismatches:")
        for w in warnings:
            print(w)
