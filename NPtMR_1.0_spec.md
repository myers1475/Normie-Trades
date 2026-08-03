# NPtMR 1.0 — Normie NOB Primero tick-logic Mitigation Reverses

**Locked:** August 3, 2026
**Status:** Backtest-verified, NOT yet implemented in either live Pine script (`normie_excursion_nob.pine` / `normie_excursion_nob_dollar_tpsl.pine`). Requires building the Scenario B reversal logic before deployment.
**Versioning:** Any future change to entry/exit/mitigation/reversal logic becomes 1.1, 1.2, etc. This document describes 1.0 exactly as backtested.

---

## Summary

NPtMR is the full, honest tick-reactive version of the Normie Excursion NOB entry mechanism — every genuine live confirmation is treated as a real trade, including the subset ("Scenario B") that the earlier NPM version silently excluded. Scenario B trades are handled with a reversal rather than dropped, turning a net-losing subset into a net contributor.

**Full backtested result:** n=1,766, Win Rate 66.67%, Mean R +0.2615, Total R +461.8, over the same 158-day MNQ dataset used throughout this strategy family's development.

---

## Complete trade-intent logic

1. **Bias check** — is `close` above the 15m EMA5 (long) or below it (short)? If not, no zone can arm or survive.

2. **Normie FVG detection** — does the 3-candle pattern qualify (C1/C3 gap, C2 relationship)? If yes, and bias agrees, the zone arms.

3. **OB detection** — search backward from C1 up to 20 bars for the first opposite-color candle. If none found, the zone never arms at all.

4. **OB size filter** — is the found OB's range ≥5pt? If not, discard — no zone.

5. **Zone dedup** — is there already a pending zone within 13pt of this new one? If yes, remove the old one before adding the new.

6. **Zone armed** — pending, tracking begins.

7. **Every subsequent bar, in order:**
   - **7a. Bias still true?** If not, zone dies immediately.
   - **7b. Excursion update** — does this bar's high extend the running peak distance from the FVG's near edge? Record it regardless of what else happens this bar.
   - **7c. Mitigation check** — has this bar's close fallen below C1's own extreme (`gbot`)? If yes, zone dies — *unless* 7d is also true this same bar.
   - **7d. Confirmation check** — has excursion reached ≥9pt (qualifies) AND has this bar's wick touched the 20%-buffer level inside the OB (confirms)? If both true, the trade fires — this overrides 7c entirely, live, even if 7c would also be true.
   - **7e. Timeout** — if neither fired nor mitigated, has it been >30 bars since arming? If yes, zone dies.

8. **If confirmed (7d fired):** enter market order at the buffer-confirmed price. SL = OB's opposite boundary. TP = same distance, 1:1.

9. **Scenario split, checked on the same bar the trade fired:**
   - **9a. Scenario A** — does this bar's close stay above `gbot`? Trade resolves normally (forward TP/SL check from the next bar).
   - **9b. Scenario B** — does this bar's close fall below `gbot`, *after* the trade already opened? If yes → reverse: close the original leg at this bar's close, open the opposite direction, same size.

10. **Reversal bracket (Scenario B only):** SL = original bracket's opposite level, widened 2pt further from entry. TP = original bracket's opposite level, widened 2pt further from entry, in the *correct* direction for the new trade.

11. **Resolution** — first of TP or SL touched (from the bar after entry, or after reversal entry) determines win/loss; both on the same bar = scratch.

---

## Key parameters (1.0)

| Parameter | Value |
|---|---|
| Bias timeframe / EMA | 15m EMA5 |
| Min excursion to qualify | 9pt |
| Zone dedup distance | 13pt |
| OB lookback | 20 bars |
| Min OB size | 5pt |
| Confirmation buffer | 20% of OB size |
| Zone timeout | 30 bars |
| Original bracket ratio | 1:1 (TP = SL distance) |
| Reversal bracket | Original bracket's opposite level, widened 2pt further from entry on both sides |

---

## Backtested results

| Segment | n | Win Rate | Mean R | Total R |
|---|---|---|---|---|
| Scenario A (unchanged, resolves normally) | 969 | 70.64% | +0.3731 | +361.6 |
| Scenario B (reversal, +2pt widened) | 797 | 61.86% | +0.1258 | +100.2 |
| **NPtMR combined (full live-honest trade set)** | **1,766** | **66.67%** | **+0.2615** | **+461.8** |

---

## Why these specific choices (rationale, for future reference)

- **Confirmation overrides mitigation on a same-bar tie (step 7c/7d):** matches genuine live tick-by-tick execution — a real, current-price confirmation event cannot be un-fired by information (the bar's eventual close) that doesn't exist yet at that instant. Verified this is what `alert.freq_once_per_bar` already does live in Pine; the distinction between "mitigation-first" (NPM) and "confirmation-first" (NPC) behavior only matters when reconstructing a bar *after the fact* from static OHLC (backtests, chart reloads) — live ticks resolve the true order on their own.
- **Scenario B is a real, distinct population, not noise:** isolated and confirmed net-losing on its own (36.15% WR / -0.3156 MeanR) before any fix — this is why NPM's original backtest looked stronger than true live execution actually is; NPM was unintentionally filtering for Scenario A only.
- **Reversal, not close-and-wait or breakeven:** tested three alternatives for handling Scenario B — immediate close (worse), move stop to breakeven (much worse, 4.94% WR), and reversal (the only one that worked). Confirms Scenario B's mitigation is often a genuine reversal signal, not just an unlucky wick.
- **Reuse the original bracket's levels, not a freshly-computed one:** tested computing a fresh OB-based bracket from the new (post-mitigation) entry price — this was substantially worse, since by the time reversal happens price is typically already through the OB, making a fresh measurement from it too tight.
- **+2pt widening on both sides, not the target alone:** widening only the target (either as a flat addition or "further in the correct direction") was worse in every variant tested — it skews the risk:reward ratio without adding real edge. Widening both sides symmetrically preserves the ratio while giving genuine winners slightly more room; +2pt tested best, with +3pt close behind and +4pt starting to give it back.

---

## Open items before live deployment

- Reversal logic (steps 9b, 10) is not yet built into either Pine script. Requires: extending the open-position tracking to also store `gbot`/C1's extreme, checking mitigation against an *already-open* position (not just pending zones), and implementing the close-and-reverse mechanism through the live order pipeline.
- Not yet run through the full stress-test suite (distribution/concentration, lookahead, slippage, fees, random-null) that earlier locked versions in this family went through.
