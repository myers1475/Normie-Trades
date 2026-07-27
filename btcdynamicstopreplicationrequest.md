# BTC 1h/Daily Dynamic Regime-Scaled Stop — Independent Replication Requested

**Status: promising first-pass result, needs independent replication before treating as validated. Same process that resolved the NQ dynamic-stop investigation (see trading-strategy-reference.md Section 6) — build it separately, diff the results, chase any disagreement.**

## What was built

The same volatility-regime-scaled dynamic stop validated for NQ 15m/4h was ported to the BTC 1h/Daily variant, using Bybit BTCUSDT perpetual data (1h + Daily, ~4.5 years / ~6 years respectively).

**One real methodology difference from NQ, worth naming upfront:** NQ's baseline table came from an external source (NQStats). No equivalent external BTC volatility reference exists, so the baseline here was **self-derived** — full-sample stdev of hourly returns, per hour-of-day (NY time), computed directly from the same dataset used for backtesting. This is a real, structural difference from NQ's version and a legitimate thing to scrutinize independently.

**Mechanism (otherwise identical to NQ):**
- Rolling 10-occurrence stdev of hourly returns, tracked separately per hour-of-day (0-23)
- `regime ratio = rolling stdev / that hour's derived baseline`
- `dynamic stop = 485.5 pts × ratio`, clamped 0.5x–2.0x (same clamp bounds as NQ — never re-tested for BTC specifically)
- No LOC filter (this variant doesn't use one)

## Result (single independent pass so far)

| | Win Rate | Net R | Trades |
|---|---|---|---|
| Fixed 485.5pt stop | 58.3% | 338 | 2,115 |
| **Dynamic stop** | **62.1%** | **476** | 2,115 |

**+3.8 pts WR / +138 net R** — comparable direction and even slightly larger magnitude than NQ's validated result.

## Sanity checks already performed (by CD, single-session)

1. **Hand-verification**: manually recomputed one specific regime-ratio value from raw data — matched the pipeline's stored value exactly (0.8242, both ways).
2. **Adjacent-hour check**: three consecutive hours on the same date produced three distinct, plausible ratio values (1.30, 0.82, 0.76) — no sign of an hour-bucket-swap bug like the one found in NQ's investigation.
3. **Temporal stability**: dynamic beats fixed in **both halves** of the full history independently, not just in aggregate —

| | Fixed WR / Net R | Dynamic WR / Net R |
|---|---|---|
| First half (1,057 trades) | 53.8% / 79 | 56.7% / 137 |
| Second half (1,058 trades) | 63.1% / 259 | 68.1% / 339 |

## What hasn't been done yet (the actual gap to "final word")

1. **No independent second builder.** Every bug found in the NQ investigation (DST handling, the regime-ratio hour-lookup bug) was found specifically *because* two sessions built it separately and disagreed. This BTC version has had exactly one builder — the equivalent of NQ's very first, still-buggy pass.
2. **No true out-of-sample split.** Full history was used both to build the baseline and to test against it. NQ's validated variants all report a specific held-out OOS trade count; this doesn't have one.
3. **Clamp bounds (0.5x-2.0x) were inherited from NQ, never re-swept for BTC specifically.**
4. **No live/forward-test stretch** — purely a backtest finding so far.

## Recommended next steps

1. **OG: build this independently from scratch**, using your own data source if practical (or the same Bybit BTCUSDT data if not, but ideally from a separately-pulled export) — same mechanism (rolling-10 hourly regime ratio, dynamic stop, 0.5x-2.0x clamp), same win-rate/net-R comparison.
2. **Compare results.** If they closely match CD's numbers above, that's real confirmation. If they disagree — even by a little — that's the signal to do a trade-by-trade diff, the same discipline that found both real bugs in the NQ investigation. Don't assume either side is right just because the numbers look "close enough."
3. **Once both sides agree**, worth doing a proper in/out-of-sample split before calling this validated, and ideally a sensitivity sweep on the clamp bounds specific to BTC.
4. **Only after that** should this go into `trading-strategy-reference.md` as a documented, cross-validated finding for the BTC variant — do not fold it into live BTC risk/account planning before then.
