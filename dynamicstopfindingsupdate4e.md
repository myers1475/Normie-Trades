## 4e. Update — Data-Sourcing Method Tested and Ruled Out; NQ vs. MNQ Instrument Is the Last Remaining Candidate

Following up on 4d: per OG's own recommended next step, CD directly tested the data-sourcing theory rather than leaving it as the last untested guess.

**Test performed:** CD derived 30m/4h/1h bars by bucketing its own 15m source file (matching OG's method exactly — simple time-bucketing, not a separate export), then re-ran the full backtest on top of that, keeping everything else identical to the 4c timing-corrected version.

| | Win Rate | Net R | Trades |
|---|---|---|---|
| Fixed 42.5pt (CD, bucketed data) | 60.2% | 258 | 1,328 |
| Dynamic stop (CD, bucketed data) | **62.2%** | **300** | 1,328 |

**Dynamic still outperforms.** So the data-sourcing *method* (bucketed vs. separately-exported higher-timeframe bars) is now tested and ruled out too — same treatment as the two theories closed in 4c and 4d.

**Status: three candidates eliminated by direct test, zero remaining explanations from the original list.** Every specific mechanism raised so far (timing offset, counter-FVG-at-touch, bucketed-vs-separate data sourcing) has been tested head-on and shown not to be the cause. The sign disagreement between CD's and OG's backtests persists regardless.

**One variable was never actually isolated, even in this latest test: the underlying instrument.** CD's bucketing test still used its own MNQ (Micro E-mini) 15-minute file as the source — it was never re-run against NQ (full-size E-mini) data, which is what OG's script uses throughout. CD does not currently have an NQ CSV to test this directly. This is now the only candidate left from the original list that hasn't been tested — not because it's been ruled in, but simply because it hasn't been tested at all yet.

Worth naming plainly: with three real theories eliminated and the disagreement still standing, this may not resolve to a simple "one side has a bug" answer. It's possible the two backtests are genuinely testing on different-enough data (NQ vs. MNQ specifically, or some other still-unidentified factor) that both results are locally "correct" for what they measured, without either implementation containing an actual defect.

### Recommended next steps
1. **Most direct remaining test:** either CD obtains an NQ 15m CSV and re-runs its full pipeline against it, or OG obtains an MNQ 15m CSV and re-runs its pipeline against that — whichever is easier to source. If the result flips when the instrument changes (holding everything else constant), that's the answer. If it doesn't, the instrument is ruled out too and a full trade-by-trade diff on a small shared window becomes the only path left.
2. Given three eliminated theories, a trade-by-trade diff (matching individual signals by timestamp between the two scripts, on a short shared window) is probably worth doing regardless of what the instrument test shows — it would surface any remaining difference directly rather than requiring another round of hypothesis-and-test.
3. Continue treating the dynamic stop as unvalidated either way until this converges. Do not deploy live.
