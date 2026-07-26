# Trading Strategy & Prop Firm Reference — Ground Truth

**Purpose:** This document is the authoritative summary of an extended, multi-session research and validation effort. Any AI assistant or person reading this should treat it as confirmed, tested fact — not a proposal to second-guess from first principles. Where something is a judgment call or lower-confidence, it's labeled as such explicitly.

**Revision note:** this replaces the original version of this document. It is not a separate update — it's a corrected, complete version reflecting everything learned since, including a since-validated feature and two testing-tool bugs found and fixed along the way. Read this document alone; don't treat the original version as a separate source to reconcile against.

---

## 1. Core Strategy Methodology ("Normie FVG")

**Pattern:** 3-candle Fair Value Gap (FVG) — candle 1 and candle 3 don't overlap, candle 3 closes back inside candle 1's range (a "normie" retrace, not a full breakaway).

**Entry logic:**
- Detect the FVG on the entry timeframe.
- Bias filter: price must be above/below a 5-period EMA on a higher bias timeframe (checked both at FVG formation AND re-checked at the moment of touch/fill — bias can flip between formation and fill).
- Counter-FVG filter: if the candle that fills the entry also forms a fresh FVG in the *opposite* direction, skip/invalidate the trade (early warning of reversal).
- Entry fills via a resting limit order at the FVG edge (not market order).
- Exit: fixed R:R stop/target (1:1 confirmed optimal for GOAT specifically — see Section 3).

**Continuous monitoring (not touch-only):** Bias/LOC are re-checked every bar while a limit order is pending, not just once at touch. This was specifically tested — touch-only checking is simpler but costs ~7% of edge; continuous monitoring is correct.

**Flatten mechanism:** an open position is closed early (before hitting stop or target) if bias/LOC invalidates, or if the touch candle retroactively forms a counter-FVG once it closes. This isn't just a loss-limiter — flattened trades average slightly positive (+0.15R in testing), since invalidation often happens after a partial favorable move.

**LOC (Line of Control) filter:** a lower-timeframe gap-tracking state machine — sticky, holds a directional bias until a genuine new closing FVG confirms a flip (NOT a simple "which side of the line is price on" check — that was tried and is wrong, confirmed by testing). LOC timeframe should be proportional to entry timeframe (~2:1 ratio, matching the original 15m entry / 30m LOC pairing).

**Volatility regime-scaled dynamic stop (added and validated after the original version of this document):** the NQ script's stop can scale with current market volatility relative to that hour-of-day's own 5-year historical norm, rather than staying fixed at 42.5 points. Confirmed to outperform the flat baseline after an extensive independent-verification process (see Section 6). Default is `useDynamicStop = true` in the live script. A related, separate feature (`useRegimeFilter`, blocking entries during unusually elevated or compressed hours) exists in the same script section but defaults to **off** and has not been validated either way — don't assume it helps just because the dynamic stop does.

---

## 2. Validated Variants (real backtested data, in/out-of-sample split)

| Variant | Entry TF | Bias TF | LOC | Stop | Win Rate | Trades (OOS) | OOS Span | Confidence |
|---|---|---|---|---|---|---|---|---|
| **NQ main** | 15m | 4h | 30m | 42.5 pts (flat) or dynamic — see below | 60.05% (flat stop) | 728 | 314 days | **High** |
| **BTC 1h/Daily** | 1h | Daily | none | 485.5 pts | 60.90% | 578 | 730 days | **High** |
| NQ 5m/1h | 5m | 1h | none | 27.0 pts | 66.12% (top 5 hours: 20,08,11,00,09 ET) | 245 | 100 days | Moderate |
| BTC 5m/4h+LOC | 5m | 4h | 10m | 210.0 pts | 64.35% (top 5 hours: 08,09,06,13,23 ET) | 216 | 93 days | Moderate |
| NQ 1m/15m | 1m | 15m | none | 21.2 pts | 72.92% (hour 00 ET only) | 48 | 22 days | **Low — watch closely, checkpoint at ~50 live trades** |

**Important caveat on the win-rate figures above:** every number in this table was validated using the **flat** stop, before the dynamic stop feature existed. The dynamic stop is now confirmed to outperform the flat stop specifically on the main NQ system (see Section 6) — meaning the true live performance of that variant is likely modestly better than 60.05% going forward. **The other four variants have not yet been re-tested with the dynamic stop enabled** — don't assume their win rates in this table already reflect it, and don't assume the dynamic stop's benefit transfers to them without checking, the same way LOC's benefit didn't transfer cleanly across timeframes (see below).

**Other notes, unchanged from the original version of this document:**
- BTC variants trade **CME Micro Bitcoin futures (MBT)** via **Tradovate**, confirmed available. MBT = 0.10 BTC/contract, $0.10/point value (NOT the same as MNQ's $2/point or Bybit perpetual mechanics).
- The BTC system was originally validated on Bybit perpetual data; it was **re-validated on real CME MBT 1-hour data directly** and the edge transferred cleanly (60.90% vs. original ~59.31%). The original 485.5-point stop outperforms a CME-recalibrated 330-point stop on the actual CME out-of-sample data — **keep 485.5, no change needed.**
- Hour-restricted variants (5m/1h, 5m/4h, 1m/15m) were tuned specifically to bring trade frequency down toward ~2.4/day to match the main systems, and carry real overfitting risk proportional to how thin their samples are — see confidence column.
- LOC was tested on the alternate timeframes: it **hurts** the NQ 5m/1h variant slightly (don't use it there) and **helps modestly** on BTC 5m/4h (use it there). LOC's benefit appears specific to certain timeframe pairings, not universal — this is exactly the kind of thing that also turned out to be true of the dynamic stop (see Section 6), so treat every feature as needing its own validation per variant, not something that transfers by default.

---

## 3. Prop Firm: GOAT Futures Funding — FINAL CHOICE (not Apex)

**Product: Flex Challenge, 100K tier.** Chosen over Apex after correcting several early modeling errors (see Section 5). Chosen over GOAT's own EOD and Instant Funded products after testing all three.

**Real, confirmed Flex 100K rules:**
- Profit target: $6,000 (6%)
- Max drawdown: $3,000, **EOD trailing** (locks at starting balance once reached — not static, not intraday-trailing)
- **No daily loss limit**, either eval or funded phase
- **No consistency rule on funded** (50% rule applies during eval only)
- Payout every **5 winning days** (a winning day = net P&L ≥ 0.2% of account balance)
- Payout = 50% of profit, capped at **$2,500 flat** every cycle (not a ladder — same cap every time, no account closure/lifetime cap)
- Profit split: **90/10** (paid for the add-on; $165/account for the 100K 5-pack including the add-on, $104/account for the 50K 5-pack)
- Contract limit: 5 mini / 50 micro — not a binding constraint at our sizing

**Risk sizing (swept and confirmed optimal for GOAT's no-daily-limit structure):**
- **Eval: $1,500 risk/trade**
- **Funded: $750 risk/trade**
- This is NOT the same as the old $900/$450 Apex-era numbers (those were calibrated for Apex's $1,000 daily loss limit, which GOAT doesn't have — don't reuse them).

**Payout strategy:** request every single time you're eligible, immediately. The cap doesn't grow with delay — waiting only exposes unwithdrawn profit to a future drawdown for no benefit. (This was tested directly — delaying payouts costs money, doesn't earn more.)

**For reference:** Apex's own confirmed rules (100% profit split, real payout ladders, and a full corrected economics comparison) are documented separately in `prop-firm-economics-final.md` — GOAT still wins clearly at every comparable tier once both are modeled with their real, complete rules.

---

## 4. Account Plan: 5-Variant Diversification, 10 Accounts

**Structure:** 2 accounts per variant (all 5 variants above), 10 accounts total, GOAT Flex 100K, $1,500/$750 risk sizing throughout.

**Why:** a single-strategy 10-account plan (all 10 running the identical NQ 15m/4h signal) showed a real "boom or bust" problem once properly modeled with **correlated** trades — since all copies of one signal move together, a bad stretch hits all 10 accounts simultaneously. Tested via Monte Carlo:

| | Single strategy, 10 accounts (correlated) | **5-variant diversified, 10 accounts** |
|---|---|---|
| Median month | $65,746 | $69,525 |
| 5th pct (bad month) | $15,900 | **$56,506** |
| Worst month ever observed (3,000 trials) | — | **$40,335** (still solidly positive) |
| % Negative months | 4.2% | **0.0%** |

Diversifying across 5 genuinely different signals (different timeframes, two different underlying assets) cut the realistic bad-month risk by roughly 3.5x without sacrificing typical performance. This is the core justification for running 5 variants instead of 1 or 2.

**Rollout plan (staggered, as actually being executed):** currently trading 3 accounts live. Add 2 more once profitable → 5. Add 3 more once profitable → 8. Add final 2 → 10. Once at 10, replace any individual breach as it happens (not synchronized batch resets).

**Risk-of-ruin note on BTC 1h/Daily specifically:** this variant's slow trade frequency (0.79/day) gives it meaningfully higher ruin risk than the others over a long horizon, purely due to spending longer in the risky eval window and more calendar-time exposure generally — NOT a flaw in its edge. Tested reducing its eval-stage risk to compensate — **this was found to cost more in lost speed/profit than it saves in reduced resets, so full $1,500 eval risk was kept for this variant too, matching the others.** With only 2 accounts on this variant (not all 10), the extra reset frequency is a minor, absorbable cost against its actual edge.

---

## 5. Explicitly Corrected Mistakes — Account Economics & Rollout Modeling

- **Apex vs. GOAT comparison was wrong on the first several passes** — an inflated Apex figure came from wrongly assuming full-balance withdrawal instead of a real, capped payout ladder ($2,000→$2,500→$2,500→$3,000→$4,000→$4,000 for 100K, account closes after the 6th payout). Corrected, GOAT wins clearly at every tier.
- **A methodology bug inflated/deflated several early Monte Carlo runs** by treating every simulated "month" as a cold restart from a fresh eval, rather than modeling an already-established, ongoing account. Corrected via steady-state measurement (a later month after a warmup period).
- **Payout-eligibility bug**: an early sim let leftover balance from a prior payout immediately re-trigger a new payout without requiring genuinely fresh profit — corrected.
- **Consistency-check bug**: an early sim computed "max single day ÷ total profit" using only the sum of winning days (ignoring losing days), understating the true ratio — corrected to use true net profit.
- **This system runs on FIXED DOLLAR RISK per trade, not proportional-to-account-size sizing.** Because of this, virtually every "reduce risk/size for safety" idea tested throughout this whole process **lost money** rather than helping — the fixed-risk structure means speed/volume of trades dominates the economics, and anything that slows down trade cycling (tighter filters, smaller size, waiting to withdraw, hour restrictions beyond what's been tested) tends to cost more than it saves. Default assumption should be against adding extra caution unless it's specifically tested and shown to help.

---

## 6. Dynamic Regime-Scaled Stop — Validation History (Resolved)

**Question investigated:** does the volatility-regime-scaled dynamic stop (Section 1) outperform the flat 42.5-point baseline on the main NQ system?

**Answer: yes, confirmed by two independent parallel research sessions ("OG" and "CD" in the investigation's own terminology) working from separate Python backtest replications, after a genuinely rigorous, multi-round investigation.**

**Important clarifying finding: the two bugs uncovered during this investigation existed only in the Python backtest replications built to test the strategy — the deployed Pine script itself never had either issue.** TradingView's native `hour(time, "America/New_York")` call is properly DST-aware by default, and the live script's regime-ratio lookup was always a direct, correct read with no erroneous offset. The script's logic was correct throughout; what was actually being validated was whether that already-correct logic performs well — not whether the live script needed fixing.

**Brief path of the investigation, condensed from twelve rounds of back-and-forth:**
1. The feature shipped with an in-code comment claiming a backtested +3.0 pt WR / +73 net R improvement.
2. One independent replication initially showed the opposite result (dynamic losing).
3. Five candidate explanations were raised and tested directly, one at a time, rather than debated: a timing offset (real, but didn't explain the discrepancy), a counter-FVG-at-touch filter present in only one replication (real design difference, didn't explain it either), data-sourcing method (ruled out), NQ-vs-MNQ instrument choice (ruled out), and DST handling (a real bug, but fixing it alone still didn't resolve the disagreement).
4. The actual cause was found by direct code inspection: one replication mistakenly reused a "step back one bucket" helper — correct for its 4h EMA and 30m LOC lookups — for the regime-ratio lookup too, fetching an entirely different hour-of-day's baseline than intended. Fixed, and both replications then agreed: dynamic beats flat.
5. A separate, previously-unnoticed scope mismatch (one replication's reported trade counts were out-of-sample-only throughout, while the other always ran the full period) explained a persistent "roughly 2x, suspiciously stable" trade-count gap that had nothing to do with any bug.
6. With scope matched, a full trade-by-trade diff across the whole overlapping period showed roughly 86% of trades matching exactly, with the remaining ~14% fully accounted for by: the counter-FVG filter (known design difference), a short tail where one data file simply ended before the other's, small real NQ-vs-MNQ price differences, legitimate LOC-state divergence (LOC is path-dependent, so two correlated-but-distinct instruments can genuinely land in different states), and same-bar stop/target resolution ambiguity at 15-minute granularity (a limitation honestly flagged in the investigation's own tooling documentation from its very first version, not a convenient excuse invented at the end).

**Status: closed.** `useDynamicStop` stays at its default `true`. The separate entry-blocking feature in the same script section (`useRegimeFilter`) remains unvalidated and defaults to off — don't conflate the two.

---

*This document reflects an extended, multi-session, multi-participant validation effort. Every backtest figure cites real historical price data (NQ and CME MBT futures) with in-sample/out-of-sample splits; every firm rule was confirmed against official documentation or direct account experience, not assumed; every bug fix described above was verified by direct, numerical re-testing, not just reasoned about.*
