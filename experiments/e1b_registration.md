# E1b — pre-registration (WRITTEN BEFORE ANY RUN — 2026-07-31)

Same design as E1 (5 pairs, cold vs equipped, same seed/config/learner),
with the two E1-derived fixes active in BOTH arms:
  F-E1a fix: bank-time dedup + full banked list on board
  F-E1b fix: fogged statements surfaced on board

## Pre-registered success criteria (all graded at 5 pairs)
1. MECHANISM-1 (dedup works): equipped duplicate count <= 2 per run
   (E1 baseline: 14, 2, 8, 1, 33).
2. MECHANISM-2 (fog works): re-proposals of an already-fogged statement
   <= 5 per run, either arm (E1 baseline: 10-40 per run).
3. HEADLINE (the retested bet): equipped cost-per-unique-dot <= cold
   AND equipped unique dots >= cold +15%.
   (E1 result: +17.7% uniques at +8.4% cost — the fixes should keep the
   knowledge gain and delete the tax.)

## Kill criteria
- If MECHANISM-1 or -2 fail, the fixes are wrong as built — stop, autopsy,
  no criterion-3 grading (mechanisms gate the headline).
- If mechanisms pass but criterion 3 fails, BANK's efficiency claim dies
  permanently as designed; inheritance is repositioned as a depth/frontier
  tool only (which E1 already supports at 5/5 mutation reach).

Grading: R1 gates + dedup-adjusted counts, identical to E1. Voids published.
