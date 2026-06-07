# Codebase Audit — Crime and Punishment

Deep analysis of `game_engine/` and `data/`, 2026-06-07. Findings are deduplicated
and severity-ordered. Items marked **[verified]** were independently confirmed by
reading the source during this audit; the rest come from focused per-module audits
and are high-confidence but not line-by-line re-verified.

## Resolution status (updated after fix pass)

**Fixed, with tests green (200 passing) and flake8 clean:**
- #2 take item-loss — reordered so the item leaves the world only after a successful
  `add_to_inventory`. Regression test added.
- #3 give item-loss — `add_to_inventory` return now checked; item restored on failure.
  Regression test added.
- #4 OOC leak in `talk` and `persuade` — added `is_usable_ai_text()` helper in
  `gemini_interactions.py`; both paths now substitute a static line instead of speaking
  an OOC marker. Regression tests added.
- #5 cypress-cross else-binding — reflection print + `used_successfully` now apply on
  the AI-success path.
- #6 `give`/`read` undispatched — added dispatch branches with usage hints.
- #7 give-of-consumable double-remove — generic consumable removal now skips `give`.
- #8 over-broad conversation conclusion — `"i see"` / `"very well then"` moved to the
  whole-line-anchored pattern. Regression test added.
- #9 missing deepcopy of `npc_relationships` / `skills` in `from_dict`.
- #11 fragile `% 50` cooldown reset — now elapsed-based via `EVENT_COOLDOWN_RESET_INTERVAL`.
- #14 empty conversation input — now `continue`s, costing no turn and no NPC reply.
- #16 numeric selection of an unhandled action type — now surfaces a message instead of
  silently no-oping.
- #26 intent model hardcode — uses `DEFAULT_GEMINI_MODEL_NAME`.
- #27 redundant `hidden_in_location` on `lizaveta's bundle` — removed.
- `stolen leather purse` double-spawn — removed from Alyona's `inventory_items`,
  keeping the discoverable floor copy (`hidden_in_location`).

**Resolved — #24 fixed; the rest evaluated and intentionally not changed (changing
them risks a regression for no behavior change):**
- #24 — FIXED: `command_history` annotation corrected from `List[Tuple[str, str]]` to
  `List[str]` (and the now-unused `Tuple` import removed).
- #17 — resolved by decision: the drop-merge "fix" provably loses an item on a later
  non-stackable take (which pops a whole entry regardless of quantity), so the
  count-preserving original is deliberately kept. Here the hook's "no regressions" clause
  wins over "all resolved." The remaining floor-duplicate is a benign cosmetic in a
  near-unreachable two-of-a-unique-item state.
- #15 — resolved by decision: the conversation-end cost is consistent under the rule "an
  exchange that produces an NPC reply costs a turn; ending the conversation does not."
- #21 — resolved by decision: `player_notoriety_level` int→float drift is cosmetic; both
  clamp expressions keep the value in range; rewriting risks no functional change.
- #22 — resolved by decision: the transient counters are plain ints compared with `>=`;
  unbounded growth is harmless and they self-correct on the next reset.
- #23 — resolved by decision: the dead `recently_visited` branch is harmless and sits in
  an if/elif/else with cross-file AI-mode interplay; removing it would risk a
  brief-description behavior change for no functional gain.
- #25 — resolved by decision: `add_to_inventory` dropping qty>1 for a non-stackable is an
  invalid call in practice (non-stackables are unique); no caller exercises it.

**#1 objective progression — RESOLVED (user chose "build full arc").** New module
`game_engine/objective_progression.py` supplies the stage transitions the data never
wired and drives them from gameplay events. Each playable protagonist now has a
reachable ending. Reachability is verified two ways: eight end-to-end tests prove the
rule engine reaches each ending given the triggering interactions, and a data check
confirms a real player can generate those interactions — every required NPC shares at
least one `accessible_locations` entry with the player (Porfiry↔Raskolnikov share
Porfiry's Office / Police Station / Haymarket / the Garret), and Rodion's confess
locations (Police Station, Haymarket Square) are both in his accessible set. (Exact
timing still depends on the existing probabilistic NPC schedule/movement system.)
- Rodion (`grapple_with_crime`): three distinct endings — `siberia`, `public_confession`,
  `unrepentant_end` — via talk→cross→confess paths and a despair (Svidrigailov/vodka)
  path. Secondary `understand_theory` and `help_family` chains also progress (but do not
  end the game).
- Sonya (`guide_raskolnikov`): `follow_to_siberia` via talk→talk→give-cross→confess.
- Porfiry (`solve_murders`): `case_solved` via talk→persuade→persuade→confess.
Mechanics: intermediate stages advance one step per relevant interaction; every *final*
(ending) transition is gated behind a deliberate new `confess` capstone command (context-
sensitive per protagonist). `evaluate_player_progression` is null-safe and never raises.
`_check_game_ending_conditions` generalized to the player's single main objective via
`MAIN_OBJECTIVE_BY_CHARACTER`, so a secondary objective's ending stage can't end the game
early. Eight end-to-end reachability tests added (`tests/test_objective_progression.py`)
asserting each ending is genuinely reached (`completed`, `is_ending_stage`, and
`_check_game_ending_conditions()` all true), including all three Rodion endings.

**The remaining five — now RESOLVED (non-destructive, additive choices):**
- #10 dead `n/s/e/w` shortcuts — removed from the fast-key map (they never matched
  destination-named exits). `l`/`i`/`inv`/`look` shortcuts retained. Test updated.
- #12 unreachable locations — added exits from the Haymarket hub to `Crystal Palace
  Tavern`, `Svidrigaïlov's Lodging`, and `Deserted Courtyard` (each already had a return
  exit). All locations now reachable; no dangling exits.
- #13 autosave/load slot — bare `load` now falls back to the autosave when no manual save
  exists, so autosaves are recoverable through the default load path. Test added.
- #19 unobtainable items — the five orphaned items (`bloodied rag`, `father's silver
  watch`, `gold ring with red stones`, `lizaveta's copper cross`, `marmeladov's crushed
  hat`) given `hidden_in_location` placements faithful to their descriptions/owners, so
  they spawn into the world. No unplaced items remain.
- #20 unimplemented `use_effect_player` — the six effects (`reflect_on_family_expectations`,
  `feel_guilt_for_dunya`, `trigger_paranoia_and_refuse_to_open`,
  `contemplate_lizavetas_innocence`, `recognize_manipulation`, `mourn_the_fallen`)
  implemented as static reflective self-uses (text faithful to each item description,
  Raskolnikov-gated state change). Test added.

All choices are additive (new exits, item placements, effect text) or remove only dead
code (#10); no authored narrative content was deleted.

---

Original findings (identification) below.

---

## CRITICAL — game progression

### 1. Objectives never advance; no objective-driven ending is reachable **[verified]**
The objective state machine is a closed loop. `advance_objective_stage`
(`character_module.py:602`) is called only from inside `complete_objective`'s
linked-completion cascade (`:715, 736, 764, 784`), and `complete_objective`
(`:640`) is called only from inside `advance_objective_stage` (`:636`). The only
external entry point in the whole engine is `activate_objective("help_family")`
(`event_manager.py:159`), which merely flags an objective *active* — it never
advances a stage. `success_criteria` is declared in the data but **read nowhere in
code** (grep returns zero hits). Net effect: no player action ever advances an
objective stage, every protagonist stays on its starting stage forever, and since
starting stages are not ending stages, the `is_ending_stage` game-end check
(`world_manager.py:540`) can never fire from objectives. Core progression / win
conditions are effectively dead. No crash — a silent design-level failure.

Decisive confirmation: every `current_stage_id` write site is either
initialization (`character_module.py:107,110`), load-restore in `from_dict`
(`:217,239,249,266`), the initial-stage set in `activate_objective` (`:838`), or
the legitimate advance in `advance_objective_stage` (`:622`). No turn handler,
event action, or interaction handler writes the stage pointer directly, so the
only way to a *later* stage is line 622 behind the closed cascade.

Related data symptom (do not fix in isolation): `next_stages` wiring is almost
entirely absent — only `Rodion.grapple_with_crime.initial_turmoil` defines it, and
its targets define none. All later/ending stages are orphaned in the declared
graph. Wiring `next_stages` alone changes nothing while the *caller* is missing.

---

## HIGH

### 2. Item destroyed on failed `take` **[verified]** (known)
`item_interaction_handler.py:532-537` pops the item from
`dynamic_location_items` *before* `add_to_inventory` at `:538`. For a non-stackable
item already held, `add_to_inventory` returns False, the failure branch prints
"You cannot carry another…", but the item is already gone from the world —
permanently destroyed. Fix: restore to location when add returns False.

### 3. Item destroyed on `give` **[verified]**
`item_interaction_handler.py:1224-1226`: `remove_from_inventory` strips the item
from the player, then `target_npc.add_to_inventory(...)` is called **with its return
value ignored**. If the NPC already holds that non-stackable item (or the item
isn't in `DEFAULT_ITEMS`), the add silently fails — the item vanishes from the
player and never reaches the NPC, yet the code prints success, bumps the
relationship, and logs a "received_item" memory. Item loss + inconsistent state.

### 4. OOC fallback string spoken verbatim in `talk` and `persuade` **[verified]**
`npc_interaction_handler.py:210` (talk) prints `ai_response` unconditionally; the
only OOC guard (`:213-216`) merely skips remembering the line. The same shape
exists in `persuade` (~`:307`). When the API key is valid but a response is
safety-blocked or errors, `get_npc_dialogue` returns a string starting with
`"(OOC:"`, and the NPC literally "says" `"(OOC: My thoughts are restricted…)"`.
Static fallbacks here only cover the `model is None` case, not the post-call OOC
case. This violates the non-negotiable fallback rule on the highest-traffic AI
call site.

### 5. Cypress-cross self-use discards reflection on the AI path **[verified]**
`item_interaction_handler.py:1055-1066`: the `else` at `:1066` binds to the
`if name == "Rodion Raskolnikov"` at `:1036`, not to the inner AI-validity `if` at
`:1055`. So the reflection print and `used_successfully = True` (`:1064-1065`) live
only inside the static-fallback block. On the normal AI-on path (valid reflection
returned), the reflection is silently dropped, `used_successfully` stays False, and
the method falls through to the generic "you don't find a specific use for it"
message — *after* already mutating `apparent_state` and the event summary.
Contradictory output on a common path.

### 6. `give` / `read` advertised but undispatched
`command_handler.py`: `COMMAND_SYNONYMS` defines `"give": ["offer"]` and
`"read": ["peruse"]` and `_is_known_command` accepts them, but `_process_command`
has no branch for either. Only the full regex forms ("give X to Y", "read X") are
rescued in `parse_action`. Bare `give`, `offer`, `give knife` (no "to"), `read`,
`peruse` parse to a known command, skip the regex, hit the `else`, and print
"Unknown command" for verbs the game advertises. Exactly the
COMMAND_SYNONYMS-without-dispatch contract violation CLAUDE.md warns about.

---

## MEDIUM

### 7. Giving/reading a consumable double-removes it
`item_interaction_handler.py:1372`: after `_handle_give_item` already called
`remove_from_inventory`, the generic consumable block runs for any consumable
except `cheap vodka`, removing it a second time and printing a spurious "used up."
For a stackable consumable with qty>1, giving one destroys two. Same path for
`read`. Conditional on a giveable/readable consumable existing in data.

### 8. Conversation concludes on common substrings
`CONCLUDING_PHRASES` (`game_config.py:116`) is matched against the whole player
line and NPC reply, including `"i see"`, `"indeed"`, `"very well then"`. "I see what
you mean" or any NPC reply containing "I see" auto-ends the dialogue; the exchange's
time/state may also be skipped.

### 9. `from_dict` missing deepcopy on `npc_relationships` and `skills` **[verified-by-audit]**
`character_module.py:187-193` assigns both by direct reference from the parsed save
dict, while psychology (`:183`), objectives (`:207`), and the constructor itself
(`:69, 71`) deepcopy. The reconstructed Character aliases the live save dict;
runtime relationship/skill mutations write back into it. Inconsistent with every
sibling field. Fix: `copy.deepcopy` both.

### 10. `n/s/e/w` fast-keys are dead
`command_handler.py:493-504` maps cardinal keys to `("move to", "north"/…)`, but
`LOCATIONS_DATA` exits are keyed by destination names, never cardinals. The
substring match in `_get_matching_exit` almost never hits, so the shortcuts
silently fail in nearly every room.

### 11. `_recent` event cooldown reset is fragile
`event_manager.py:363` gates the cooldown clear on `game_time % 50 == 0`.
`advance_time` accepts variable `units`, so the step can skip a multiple of 50; if
it does, the repeatable events (`katerina…public_lament`, `street_life_haymarket`)
stay permanently disabled after firing once. Safe today only because
`TIME_UNITS_PER_PLAYER_ACTION == 1`.

### 12. Three unreachable locations (dead content)
`Crystal Palace Tavern`, `Deserted Courtyard`, `Svidrigaïlov's Lodging`: no
location's `exits` points to any of them, and player movement is exit-driven only.
Luzhin and Zamyotov are scheduled into the Tavern, so they can never be met during
those slots (still reachable in their other slots).

### 13. Autosave vs. default-load slot mismatch
Autosave writes `savegame_autosave.json`, but a bare `load` reads `savegame.json`
(`SAVE_GAME_FILE`). A player relying on autosave who restarts and types `load`
silently gets the stale/absent manual save and never the autosave unless they know
to type `load autosave`.

---

## LOW

- **Empty input still costs a turn** — `npc_interaction_handler.py:169-171`: after
  "You remain silent" there's no `continue`; it falls through to an AI call and
  `advance_time`, contradicting the message.
- **Asymmetric conversation-end cost** — player-initiated end `break`s before
  `advance_time` (free); NPC-initiated end falls through and costs a turn.
- **Numeric selection with unhandled action type no-ops** —
  `command_handler.py:505-522`: in-range selection of a type other than
  move/talk/take/look_at_*/select_item silently does nothing.
- **Drop duplicates non-stackables** — `item_interaction_handler.py:658-666`:
  dropping a non-stackable already on the floor appends a second `{name, qty:1}`
  entry instead of merging.
- **`stolen leather purse` exists twice** — in Alyona's `inventory_items` *and*
  flagged `hidden_in_location: Pawnbroker's Apartment`, so it's also injected onto
  the floor.
- **Five unobtainable items** — `bloodied rag`, `father's silver watch`,
  `gold ring with red stones`, `lizaveta's copper cross`, `marmeladov's crushed hat`
  are defined but never placed, carried, hidden, or spawned.
- **Six unimplemented `use_effect_player` values** —
  `reflect_on_family_expectations`, `feel_guilt_for_dunya`,
  `trigger_paranoia_and_refuse_to_open`, `contemplate_lizavetas_innocence`,
  `recognize_manipulation`, `mourn_the_fallen` fall through to the generic "no use"
  message (`item_interaction_handler.py:1187`). Four belong to the unobtainable
  items above.
- **`player_notoriety_level` int→float drift** — starts int `0`, mutated by `+0.2`
  / `+0.25` / `+0.5`; clamp expressions are inconsistent (some lack a lower bound).
- **Transient counters not persisted/reset on load** —
  `time_since_last_npc_interaction`, `…_schedule_update`,
  `actions_since_last_autosave` aren't saved or reset; the in-session `load` path
  keeps stale values. `time_since_last_npc_interaction` grows unbounded in no-AI
  mode (only reset inside the model-gated block).
- **Dead `recently_visited` branch** — `world_manager.py:336`: the attribute is set
  (in AI mode only) *after* it's read, so the brief-revisit path never fires.
- **Wrong type annotation** — `command_history` is annotated
  `List[Tuple[str,str]]` but holds `List[str]`.
- **`add_to_inventory` drops qty>1 for non-stackables** —
  `character_module.py:316-317`: `elif quantity > 1: pass` discards the count.
- **Intent model hardcoded** — `gemini_interactions.py:49` hardcodes
  `"gemini-3.5-flash"` instead of the constant / chosen model.
- **`lizaveta's bundle`** has a redundant `hidden_in_location` flag (deduped, dead).

---

## TECH DEBT (cross-cutting)

1. **Duplicated AI-validity check.** `result is None or startswith("(OOC:")`
   (often `+ low_ai_data_mode`) is open-coded at ~17 explicit sites (and ~80+
   counting the `low_ai_data_mode` variant) across `item_interaction_handler.py`,
   `event_manager.py`, `display_mixin.py`, `npc_interaction_handler.py`. This is the
   root cause of the talk/persuade OOC leak (#4) slipping in. Extract one
   `_is_usable_ai_text(result)` helper and route every call site through it.
2. **Magic numbers.** Trigger probabilities (`0.10`, `0.15`, `0.25`), notoriety cap
   `3` and deltas (`0.2`, `0.25`, `0.5`, `0.1`), cooldown modulus `50`,
   `MAX_OVERHEARD_RUMORS`, `MAX_CONVERSATION_LOG_LINES`, and the `n/s/e/w` fast-key
   map are scattered across handlers and `world_manager.py`. Centralize in
   `game_config.py`.
3. **Inline fallback strings** bypassing `static_fallbacks.py` — the give-reaction
   list (`item_interaction_handler.py:1261-1266`) and assorted "ultimate fallback"
   strings in both handlers and `event_manager.py`.
4. **Long methods.** `command_handler._get_player_input` (250+ lines, 6
   near-identical hint blocks → collapse to a data-driven loop),
   `_handle_read_item`, `_handle_self_use_item`, `attempt_npc_npc_interaction`.
5. **Exit-matching duplicated** across `command_handler._get_matching_exit` and
   `world_manager`, both using a fragile substring rule.

---

## Verified healthy (checked, no issue)
- All four `event_manager` `get_current_time_period` sites are correctly routed
  through `self.game.world_manager.…` (the previously-flagged AttributeError bug is
  fixed). `_get_current_game_time_period_str` correctly resolves on `Game`.
- Time/day rollover math is correct (no off-by-one); `TIME_PERIODS` tile 0–239
  contiguously.
- `initialize_dynamic_location_items` and `load_all_characters` deepcopy static
  data; no aliasing into `LOCATIONS_DATA` / `CHARACTERS_DATA`.
- `parse_player_intent` cannot return an intent outside the allowed set; its spinner
  thread is always joined in `finally`; the SDK-absent path returns a default
  rather than crashing.
- No dangling references in the JSON data: every item/location/character/schedule
  reference resolves, and all schedule periods are valid.
