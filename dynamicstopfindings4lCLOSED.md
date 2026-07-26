## 4l. CLOSED — Final Summary

**Question investigated:** does the volatility-regime-scaled dynamic stop outperform the flat 42.5-point baseline?

**Answer: yes, confirmed independently by both OG and CD, on matched scope, after two real bugs were found and fixed.**

**Important clarifying note, found while finalizing the live script:** both bugs (DST handling, regime-ratio lookup) existed only in the Python backtest replications built to test the strategy — the deployed Pine script itself never had either issue. `hour(time, "America/New_York")` is TradingView's native, DST-aware timezone function, and the script's `currentRegimeRatio = f_regimeRatio(currentHourRegime)` was always a direct, correct lookup with no erroneous step-back. The live script's logic was correct throughout this entire investigation; what was being validated was whether that already-correct logic actually performs well, not whether it needed fixing.

**Full path of the investigation, for anyone reading this later:**
1. A dynamic, volatility-regime-scaled stop was added to the NQ script, with an in-code comment claiming it beat the flat baseline by +3.0 pts WR / +73 net R.
2. OG's independent backtest replication initially showed the opposite (dynamic losing).
3. Five candidate explanations were raised and tested one at a time, not just debated: timing offset (real bug, didn't explain the sign flip), counter-FVG-at-touch filter (a real, deliberate design difference between the two replications, didn't explain the sign flip), data-sourcing method (ruled out), NQ-vs-MNQ instrument (ruled out), and DST handling (real bug in OG's Python replication, initially thought to resolve everything — it didn't, on its own).
4. The actual cause was found by direct code inspection and confirmed numerically: OG's Python replication mistakenly reused a "step back one bucket" helper (correct for the 4h EMA and 30m LOC lookups) for the regime-ratio lookup too, fetching the wrong hour-of-day's ratio entirely. Fixed, and OG's backtest then agreed with CD's: dynamic beats flat.
5. A separate, previously-unnoticed scope mismatch (OG reporting out-of-sample-only trade counts throughout, vs. CD's full-period counts) explained the "roughly 2x, suspiciously stable" trade-count gap — not a bug, just two collaborators never having made their comparison scope explicit to each other.
6. With scope matched, a full trade-by-trade diff on the whole overlapping period showed ~86% of trades matching exactly, with the remaining ~14% fully accounted for by: the counter-FVG filter (known design difference), a 2-day tail where OG's source file simply ends before CD's, small real NQ-vs-MNQ price differences, legitimate LOC-state divergence (LOC is path-dependent, so two correlated-but-different instruments can genuinely land in different states), and same-bar stop/target resolution ambiguity at 15-minute granularity (a limitation flagged honestly in CD's script documentation from the very first version of this investigation, not a convenient excuse invented at the end).

**Status: closed.** `useDynamicStop` stays at its default `true` in the live script. No further action needed on this feature.
