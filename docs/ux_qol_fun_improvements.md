# UX / Quality-of-Life / Fun Improvement Opportunities

This review identifies practical improvements for the current text-adventure experience, based on the existing command model, progression systems, and AI fallback behavior.

## 1) Onboarding and Early-Game Clarity (High impact, low effort)

1. **Add a guided first-turn tutorial**
   - Problem: New players currently get a broad `help` menu, but no contextual “do this now” progression.
   - Improvement: For the first 3–5 turns, provide a soft tutorial with suggested commands (e.g., `look`, `talk to ...`, `objectives`, `move to ...`) and explain what each reveals.
   - Why it helps: Reduces cognitive load and gets players to meaningful interactions faster.

2. **Progressive help instead of one large help wall**
   - Problem: The help output is comprehensive but dense.
   - Improvement: Split into categories (`movement`, `social`, `items`, `meta`) and allow `help movement` style filtering.
   - Why it helps: Faster command discovery and better retention.

3. **Make parser failures actionable**
   - Problem: “Your mind is too clouded to focus on that.” is thematic, but not always informative.
   - Improvement: Show 2–3 example valid commands tied to current context (visible exits, NPC names, items).
   - Why it helps: Preserves tone while preventing player frustration loops.

## 2) Navigation and Interaction QoL (High impact, medium effort)

4. **Optional numbered choices for exits / NPCs / items**
   - Problem: Players must type full phrases repeatedly, which can be tiring.
   - Improvement: Add optional `1/2/3` shortcut mode after `look` (e.g., `1) talk to Sonya`).
   - Why it helps: Speeds play sessions and reduces typing friction, especially in long runs.

5. **“Recent commands” and quick repeat**
   - Problem: Repeating high-frequency commands like `look`, `inventory`, and `move to ...` is cumbersome.
   - Improvement: Add shortcuts like `!!` (repeat last command) and `/history` to display recent commands.
   - Why it helps: Strong quality-of-life gain for terminal-first gameplay.

6. **Smart disambiguation with confidence hints**
   - Problem: Prefix matching already asks clarifying questions, but could be richer.
   - Improvement: If ambiguous, display category and short descriptors (e.g., item type, NPC role, location tag).
   - Why it helps: Faster correction with fewer failed turns.

## 3) Save, Continuity, and Session Safety (High impact, low-medium effort)

7. **Multiple save slots + autosave**
   - Problem: Save data currently points to a single save file (`savegame.json`).
   - Improvement: Add named slots (`save slot1`, `load slot1`) and optional autosave every N turns.
   - Why it helps: Prevents accidental progress loss and supports experimentation.

8. **Session recap on load**
   - Problem: After loading, players may forget context.
   - Improvement: Show a concise recap: location, current objective stage, last 3 key events, and relationship highlights.
   - Why it helps: Better re-entry for intermittent players.

## 4) Narrative Feedback and “Fun” Systems (Medium-high impact, medium effort)

9. **Escalation meter for tension / suspicion**
   - Problem: Notoriety exists internally, but players need stronger legible feedback loops.
   - Improvement: Add a visible “heat” indicator with thresholds triggering unique NPC behavior, patrol density, rumors, and dream intensity.
   - Why it helps: Increases strategic play and emotional stakes.

10. **Micro-events during travel/waiting**
   - Problem: `wait` and frequent movement can feel mechanically flat between major events.
   - Improvement: Add short reactive vignettes (pickpocket attempt, overheard clue, chance encounter) with lightweight choices.
   - Why it helps: Makes downtime entertaining and story-rich.

11. **Relationship milestones with perks/penalties**
   - Problem: Relationship shifts happen but can be invisible to players.
   - Improvement: Trigger milestone messages and unlocks at key thresholds (e.g., new dialogue branches, item gifts, denied help).
   - Why it helps: Makes social play legible and rewarding.

12. **Short-term “intent” goals for each protagonist**
   - Problem: Long-form objectives are good, but moment-to-moment motivation can drift.
   - Improvement: Add rotating mini-goals each day/period (e.g., “avoid Porfiry today,” “secure 20 kopeks,” “attend prayer”).
   - Why it helps: Improves pacing and replayability.

## 5) Accessibility and Readability (Medium impact, low effort)

13. **Color accessibility profiles**
   - Problem: Heavy color usage may be difficult for some players/terminals.
   - Improvement: Add `theme` presets (`default`, `high-contrast`, `mono`) and persistent preference.
   - Why it helps: Improves readability and inclusion.

14. **Output density controls**
   - Problem: AI-rich responses can be long, especially in constrained terminal windows.
   - Improvement: Add verbosity levels (`brief`, `standard`, `rich`) affecting atmospheric and reflective text length.
   - Why it helps: Players can tune narrative depth to session style.

15. **Clear separators for turn boundaries**
   - Problem: Long transcripts can blur actions and consequences.
   - Improvement: Add optional turn headers including day/time, location, and last action result icon.
   - Why it helps: Better scanability in long play sessions.

## 6) AI Reliability and Trust (Medium impact, medium effort)

16. **Explicit mode indicator when fallback text is active**
   - Problem: Players may not realize they are seeing static fallback content.
   - Improvement: Show a subtle indicator in status/help when low-AI mode or fallback paths are active.
   - Why it helps: Sets expectation and increases trust.

17. **Regenerate/rephrase option for AI outputs**
   - Problem: Sometimes generated responses may miss player intent.
   - Improvement: Add `retry`/`rephrase` command after AI-generated narrative outputs.
   - Why it helps: Improves perceived responsiveness without forcing a full turn reset.

## 7) Prioritized Roadmap

### Quick wins (1–2 days)
- Progressive help categories.
- Better unknown-command / unknown-intent guidance with context examples.
- Session recap on load.
- Accessibility themes and verbosity toggle scaffolding.

### Mid-term wins (3–7 days)
- Save slots and autosave.
- Numbered interaction shortcuts.
- Relationship milestone surfacing.
- Travel/wait micro-events.

### Big experiential upgrades (1–3 weeks)
- Tension/suspicion meter with systemic consequences.
- Character-specific daily mini-goals.
- AI regenerate/rephrase flow and clearer reliability signals.

## 8) Suggested Success Metrics

- **Onboarding success:** % of new players who issue 5+ commands in first session.
- **Friction reduction:** Unknown-command rate per 50 turns.
- **Engagement:** Median turns per session and return rate after first day.
- **Narrative agency:** % of players reaching alternate objective stages/endings.
- **Satisfaction proxy:** Frequency of voluntary use of optional systems (journal, reflect, status, mini-goals).
