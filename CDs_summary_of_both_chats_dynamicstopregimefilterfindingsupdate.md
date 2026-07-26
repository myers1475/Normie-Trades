## 4c. Update — Timing-Offset Theory Tested and Ruled Out; New Candidate Found

Following up on 4b: CD directly tested the one-bar timing-offset theory rather than just noting it as a candidate.

**Test performed:** CD's script was confirmed to check bias/LOC/session/regime-ratio at loop index `i`, one bar *after* candle-3 (the FVG's confirming, just-closed candle, at `i-1`) — while OG Claude's script checks all of these at candle-3's own bar, with no lag. This was a real, confirmed discrepancy between the two implementations.

CD re-ran the backtest with this fixed — checking all arm-time conditions (bias, LOC, session, and which regime-ratio value feeds the dynamic stop) at candle-3's own bar, exactly matching OG's timing:

| | Win Rate | Net R | Trades |
|---|---|---|---|
| Fixed 42.5pt (CD, timing-corrected) | 60.2% | 251 | 1,296 |
| Dynamic stop (CD, timing-corrected) | **62.6%** | **303** | 1,296 |

**Dynamic still outperforms after the fix.** So the timing offset was real and worth correcting (now fixed in CD's script), but it is **not** the cause of the sign disagreement with OG's result — that theory is now tested and ruled out, not just suspected.

**New candidate found while investigating:** OG's script includes a step CD's does not model at all — a **counter-FVG check at the touch candle**, which cancels a trade if the candle that fills the entry also forms a fresh FVG in the opposite direction. This is a real, previously-unflagged behavioral gap between the two backtests (not a bug exactly — CD's version simply never implemented this filter), and it could plausibly be affecting which trades get included and how they resolve.

**Candidate #2 from section 4b — different data sourcing** (CD: four genuinely separate CSV exports, MNQ; OG: 30m/4h/1h bars bucketed from a single 15m NQ export) — remains untested and unruled-out. Nothing new to report on this one yet.

**Status: still unresolved.** One candidate eliminated, one new candidate found, one old candidate still open. Do not deploy the dynamic stop live based on either backtest until this converges.

### Recommended next steps
1. Add the counter-FVG-at-touch check to CD's script so both implementations model the same trade-invalidation rules, then re-run and compare again.
2. Independently test the data-sourcing question — e.g., have CD's pipeline also try deriving 30m/4h/1h bars by bucketing its own 15m file (matching OG's method) rather than using separate exports, to see if that alone changes the result.
3. Only once both implementations agree trade-for-trade on a small shared sample window should the win-rate/net-R comparison be trusted.
