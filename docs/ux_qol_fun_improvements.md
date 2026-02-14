# UX / Quality-of-Life / Fun Improvement Opportunities

This review identifies practical improvements for the current text-adventure experience, based on the existing command model, progression systems, and AI fallback behavior.

## 1) Onboarding and Early-Game Clarity (High impact, low effort)

1. **Progressive help instead of one large help wall**
   - Problem: The help output is comprehensive but dense.
   - Improvement: Split into categories (`movement`, `social`, `items`, `meta`) and allow `help movement` style filtering.
   - Why it helps: Faster command discovery and better retention.

2. **Make parser failures actionable**
   - Problem: “Your mind is too clouded to focus on that.” is thematic, but not always informative.
   - Improvement: Show 2–3 example valid commands tied to current context (visible exits, NPC names, items).
   - Why it helps: Preserves tone while preventing player frustration loops.

## 2) Navigation and Interaction QoL (High impact, medium effort)

3. **Optional numbered choices for exits / NPCs / items**
   - Problem: Players must type full phrases repeatedly, which can be tiring.
   - Improvement: Add optional `1/2/3` shortcut mode after `look` (e.g., `1) talk to Sonya`).
   - Why it helps: Speeds play sessions and reduces typing friction, especially in long runs.

## 3) Save, Continuity, and Session Safety (High impact, low-medium effort)

4. **Multiple save slots + autosave**
   - Problem: Save data currently points to a single save file (`savegame.json`).
   - Improvement: Add named slots (`save slot1`, `load slot1`) and optional autosave every N turns.
   - Why it helps: Prevents accidental progress loss and supports experimentation.

## 4) Narrative Feedback and “Fun” Systems (Medium-high impact, medium effort)

5. **Escalation meter for tension / suspicion**
   - Problem: Notoriety exists internally, but players need stronger legible feedback loops.
   - Improvement: Add a visible “heat” indicator with thresholds triggering unique NPC behavior, patrol density, rumors, and dream intensity.
   - Why it helps: Increases strategic play and emotional stakes.

6. **Micro-events during travel/waiting**
   - Problem: `wait` and frequent movement can feel mechanically flat between major events.
   - Improvement: Add short reactive vignettes (pickpocket attempt, overheard clue, chance encounter) with lightweight choices.
   - Why it helps: Makes downtime entertaining and story-rich.

7. **Relationship milestones with perks/penalties**
   - Problem: Relationship shifts happen but can be invisible to players.
   - Improvement: Trigger milestone messages and unlocks at key thresholds (e.g., new dialogue branches, item gifts, denied help).
   - Why it helps: Makes social play legible and rewarding.

8. **Short-term “intent” goals for each protagonist**
   - Problem: Long-form objectives are good, but moment-to-moment motivation can drift.
   - Improvement: Add rotating mini-goals each day/period (e.g., “avoid Porfiry today,” “secure 20 kopeks,” “attend prayer”).
   - Why it helps: Improves pacing and replayability.

## 5) Prioritized Roadmap

### Quick wins (1–2 days)
- Progressive help categories.
- Better unknown-command / unknown-intent guidance with context examples.

### Mid-term wins (3–7 days)
- Save slots and autosave.
- Numbered interaction shortcuts.
- Relationship milestone surfacing.
- Travel/wait micro-events.

### Big experiential upgrades (1–3 weeks)
- Tension/suspicion meter with systemic consequences.
- Character-specific daily mini-goals.

## 6) Suggested Success Metrics

- **Onboarding success:** % of new players who issue 5+ commands in first session.
- **Friction reduction:** Unknown-command rate per 50 turns.
- **Engagement:** Median turns per session and return rate after first day.
- **Narrative agency:** % of players reaching alternate objective stages/endings.
- **Satisfaction proxy:** Frequency of voluntary use of optional systems (journal, reflect, status, mini-goals).
