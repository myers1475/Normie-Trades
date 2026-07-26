# Trading Strategy & Prop Firm Reference — Ground Truth

**Purpose:** This document is the authoritative summary of an extended, multi-session research and validation effort. Any AI assistant or person reading this should treat it as confirmed, tested fact — not a proposal to second-guess from first principles. Where something is a judgment call or lower-confidence, it's labeled as such explicitly.

**Revision note:** this is the third correction to this document. The first added the dynamic stop as validated (wrong — the test was incomplete). The second reversed that entirely (also wrong — that test used the wrong scope and, separately, a materially incomplete flatten implementation). This version reflects the properly corrected methodology: complete flatten mechanism (both bias/LOC invalidation AND counter-FVG-during-monitoring), tested consistently across both in-sample-excluding and full-period scopes. Read this version alone.

---

## 1. Core Strategy Methodology ("Normie FVG")

**Pattern:** 3-candle Fair Value Gap (FVG) — candle 1 and candle 3 don't overlap, candle 3 closes back inside candle 1's range (a "normie" retrace, not a full breakaway).

**Entry logic:**
- Detect the FVG on the entry timeframe.
- Bias filter: price must be above/below a 5-period EMA on a higher bias timeframe (checked both at FVG formation AND re-checked at the moment of touch/fill — bias can flip between formation and fill).
- Counter-FVG filter: if the candle that fills the entry also forms a fresh FVG in the *opposite* direction, skip/invalidate the trade (early warning of reversal).
- Entry fills via a resting limit order at the FVG edge (not market order).
- Exit: fixed R:R stop/target (1:1 confirmed optimal for GOAT specifically — see Section 3). **Stop distance (flat vs. dynamic regime-scaled) is variant-specific — see Section 2's table. Do not assume one choice transfers to all variants.**

**Continuous monitoring (not touch-only):** Bias/LOC are re-checked every bar while a limit order is pending, not just once at touch. This was specifically tested — touch-only checking is simpler but costs ~7% of edge; continuous monitoring is correct.

**Flatten mechanism — has TWO separate conditions, both required for correct testing:**
1. **Bias/LOC invalidation** — checked every bar while a position is open.
2. **Counter-FVG forming since the position was opened** — checked once per new bar close on the entry timeframe. **This condition is the dominant one in practice** — in testing, it fires roughly 2-3x more often than the bias/LOC condition. **An early version of the dynamic-stop investigation (see Section 6) omitted this second condition entirely, testing only bias/LOC — this produced a materially wrong conclusion about whether the dynamic stop helps, and was corrected only after a second research session caught the gap by direct code inspection.** Any future strategy-modification test MUST include both conditions, confirmed correct by checking the exit-reason breakdown, not just assuming completeness.

Together, this mechanism means an open position can close early, before hitting stop or target — this isn't just a loss-limiter; flattened trades average slightly positive, since invalidation often happens after a partial favorable move.

**LOC (Line of Control) filter:** a lower-timeframe gap-tracking state machine — sticky, holds a directional bias until a genuine new closing FVG confirms a flip (NOT a simple "which side of the line is price on" check — that was tried and is wrong, confirmed by testing). LOC timeframe should be proportional to entry timeframe (~2:1 ratio, matching the original 15m entry / 30m LOC pairing).

**Volatility regime-scaled dynamic stop — variant-specific, do NOT enable universally.** A feature scales the stop with current market volatility relative to that hour-of-day's historical norm, rather than staying fixed. **After extensive investigation (Section 6), the corrected, trustworthy result is: this helps on 2 of the 5 account-plan variants, hurts on 2, and is genuinely unresolved on the 5th. See Section 2 for the exact per-variant configuration. There is no universal answer — every variant needed its own independent test, and even then, one variant's result remains ambiguous.**

---

## 2. Validated Variants and FINAL Stop Configuration

| Variant | Entry TF | Bias TF | LOC | Stop Configuration | Confidence |
|---|---|---|---|---|---|
| **NQ main** | 15m | 4h | 30m | **DYNAMIC** (regime-scaled, base 42.5 pts) — confirmed to help, consistent across both scopes | **High** |
| **BTC 1h/Daily** | 1h | Daily | none | **FLAT** (485.5 pts) — dynamic result is ambiguous (see below), default to flat until resolved | **High** |
| NQ 5m/1h | 5m | 1h | none | **FLAT** (27.0 pts) — dynamic confirmed to hurt, consistent across both scopes | Moderate |
| **BTC 5m/4h+LOC** | 5m | 4h | 10m | **DYNAMIC** (regime-scaled, base 210.0 pts) — confirmed to help, consistent across both scopes | Moderate |
| NQ 1m/15m | 1m | 15m | none | **FLAT** (21.2 pts) — dynamic confirmed to hurt, consistent across both scopes | **Low — watch closely, checkpoint at ~50 live trades** |

**Real, complete-methodology mean R-multiple results (both scopes shown, since consistency across scopes is itself the confidence signal):**

| Variant | Out-of-sample: Flat / Dynamic | Full-period: Flat / Dynamic | Consistent? |
|---|---|---|---|
| NQ main | +0.182 / **+0.191** | +0.124 / **+0.148** | Yes |
| NQ 5m/1h | **+0.280** / +0.174 | **+0.226** / +0.209 | Yes |
| NQ 1m/15m | **+0.374** / +0.263 | **+0.214** / +0.140 | Yes |
| BTC 1h/Daily | **+0.218** / +0.198 | +0.115 / +0.117 (near tie) | **No — this is why it's unresolved** |
| BTC 5m/4h+LOC | +0.193 / **+0.234** | +0.208 / **+0.228** | Yes |

**BTC 1h/Daily is the one genuine open question left in this whole investigation.** Out-of-sample clearly favors flat; full-period is close enough to a coin flip that it shouldn't be read as favoring dynamic either. Default to flat (the well-established baseline) until this is resolved with a larger sample or a different scope-discipline approach — don't let an ambiguous result default to "adopt the new thing."

**Original flat-stop win rates (all variants, for reference — these predate the dynamic-stop investigation and remain accurate baselines):**

| Variant | Win Rate (flat stop) | Trades (OOS) | OOS Span |
|---|---|---|---|
| NQ main | 60.05% | 728 | 314 days |
| BTC 1h/Daily | 60.90% | 578 | 730 days |
| NQ 5m/1h | 66.12% (top 5 hours: 20,08,11,00,09 ET) | 245 | 100 days |
| BTC 5m/4h+LOC | 64.35% (top 5 hours: 08,09,06,13,23 ET) | 216 | 93 days |
| NQ 1m/15m | 72.92% (hour 00 ET only) | 48 | 22 days |

**Other notes, unchanged from earlier versions of this document:**
- BTC variants trade **CME Micro Bitcoin futures (MBT)** via **Tradovate**, confirmed available. MBT = 0.10 BTC/contract, $0.10/point value (NOT the same as MNQ's $2/point or Bybit perpetual mechanics).
- The BTC system was originally validated on Bybit perpetual data; it was **re-validated on real CME MBT 1-hour data directly** and the edge transferred cleanly. The original 485.5-point stop outperforms a CME-recalibrated 330-point stop on the actual CME out-of-sample data — keep 485.5 as the base for that variant.
- Hour-restricted variants (5m/1h, 5m/4h, 1m/15m) were tuned specifically to bring trade frequency down toward ~2.4/day to match the main systems, and carry real overfitting risk proportional to how thin their samples are — see confidence column.
- LOC was tested on the alternate timeframes: it hurts the NQ 5m/1h variant and helps modestly on BTC 5m/4h. Never assume a feature transfers between variants without a dedicated test — this lesson was reinforced twice over in the dynamic-stop saga (Section 6).

---

## 3. Prop Firm: GOAT Futures Funding — FINAL CHOICE (not Apex)

**Product: Flex Challenge, 100K tier.** Chosen over Apex after correcting several early modeling errors (see Section 5). Chosen over GOAT's own EOD and Instant Funded products after testing all three.

**Real, confirmed Flex 100K rules:**
- Profit target: $6,000 (6%)
- Max drawdown: $3,000, **EOD trailing** (locks at starting balance once reached)
- **No daily loss limit**, either eval or funded phase
- **No consistency rule on funded** (50% rule applies during eval only)
- Payout every **5 winning days** (a winning day = net P&L ≥ 0.2% of account balance)
- Payout = 50% of profit, capped at **$2,500 flat** every cycle
- Profit split: **90/10** (paid for the add-on; $165/account for the 100K 5-pack including the add-on, $104/account for the 50K 5-pack)
- Contract limit: 5 mini / 50 micro — not a binding constraint at our sizing

**Risk sizing:** Eval $1,500/trade, Funded $750/trade — swept and confirmed optimal for GOAT's no-daily-limit structure. NOT the same as the old Apex-era $900/$450.

**Payout strategy:** request every single time you're eligible, immediately.

**For reference:** Apex's confirmed rules (100% profit split, real payout ladders) are in `prop-firm-economics-final.md` — GOAT still wins clearly at every comparable tier.

---

## 4. Account Plan: 5-Variant Diversification, 10 Accounts

**Structure:** 2 accounts per variant, 10 total, GOAT Flex 100K, $1,500/$750 risk sizing. **Each variant uses the stop configuration from Section 2's table — this is a mix of flat and dynamic, not uniform.**

**Why diversify:** a single-strategy 10-account plan showed a real "boom or bust" problem once properly modeled with correlated trades. Diversifying across 5 genuinely different signals cut realistic bad-month risk substantially without sacrificing typical performance.

**Final, corrected Monte Carlo (per-variant optimal stop configuration, complete flatten mechanism):**

| Metric | Value |
|---|---|
| Median month | $66,431 |
| Mean | $66,231 |
| 5th pct (bad month) | $53,772 |
| 90th pct (great month) | $75,477 |
| Worst month observed (3,000 trials) | $34,554 — still solidly positive |
| % Negative months | 0.0% |

This is the current, trustworthy reference figure — it supersedes any earlier version of this Monte Carlo, since this one uses the fully corrected per-trade methodology across all 5 variants, not just the 2 that changed stop type.

**Rollout plan (staggered, as actually being executed):** currently trading 3 accounts live. Add 2 more once profitable → 5. Add 3 more once profitable → 8. Add final 2 → 10. Once at 10, replace any individual breach as it happens.

**Risk-of-ruin note on BTC 1h/Daily:** this variant's slow trade frequency (0.79/day) gives it meaningfully higher ruin risk than the others, purely due to spending longer in the risky eval window. Tested reducing its eval-stage risk to compensate — found to cost more in lost speed/profit than it saves, so full $1,500 eval risk was kept, matching the others.

---

## 5. Explicitly Corrected Mistakes — Account Economics & Rollout Modeling

- **Apex vs. GOAT comparison was wrong on the first several passes** — an inflated Apex figure came from wrongly assuming full-balance withdrawal instead of a real, capped payout ladder. Corrected, GOAT wins clearly at every tier.
- **A methodology bug inflated/deflated several early Monte Carlo runs** by treating every simulated "month" as a cold restart from a fresh eval. Corrected via steady-state measurement.
- **Payout-eligibility bug**: an early sim let leftover balance from a prior payout immediately re-trigger a new payout without requiring genuinely fresh profit — corrected.
- **Consistency-check bug**: an early sim computed "max single day ÷ total profit" using only winning days, understating the true ratio — corrected.
- **This system runs on FIXED DOLLAR RISK per trade, not proportional-to-account-size sizing.** Because of this, virtually every "reduce risk/size for safety" idea tested lost money — the fixed-risk structure means speed/volume of trades dominates the economics. Default assumption should be against adding extra caution unless specifically tested and shown to help.

---

## 6. Dynamic Regime-Scaled Stop — Complete Investigation History

**Final answer: the dynamic stop is not a universal improvement or a universal harm — it's genuinely variant-specific, confirmed correct only when tested with the complete strategy methodology at consistent results across multiple scopes. See Section 2 for the exact per-variant configuration.**

**This took an unusually long and genuinely humbling path to get right — worth recording in full so the same mistakes aren't repeated:**

1. **Round 1 (bugs in testing tools, not the strategy):** the feature shipped with an in-code comment claiming a backtested improvement. Two independent research sessions ("OG" and "CD") initially disagreed on direction. Two real bugs were found in the *Python backtest replications* (not the live Pine script, which was correct throughout): a DST-unaware timezone, and a regime-ratio lookup that mistakenly reused a step-back helper meant for a different calculation. Both replications then agreed: dynamic beats flat, using a **simplified backtest that only checked stop/target hits — no flatten mechanism at all.**

2. **Round 2 (the "closed" conclusion was reopened, correctly at first, then incorrectly):** applying the complete methodology (including flatten) to the main NQ system showed dynamic losing, reversing Round 1's conclusion. This was reported as a genuine finding.

3. **Round 3 (the reversal itself had two of its own real flaws, found by continuing the same discipline rather than stopping at a satisfying-sounding answer):**
   - **Scope inconsistency:** the flatten-inclusive test used out-of-sample-only data, inconsistent with the full-period convention the investigation had already established for comparing across the two sessions. Correcting scope alone flipped the direction back toward dynamic winning.
   - **An incomplete flatten implementation:** even after fixing scope, one session's flatten mechanism only checked bias/LOC invalidation — it was missing the counter-FVG-during-monitoring condition entirely, which turned out to be the *dominant* exit mechanism (firing 2-3x more often than bias/LOC in testing). This was caught not by assumption but by one session directly asking the other to check its own code line-by-line — and it was confirmed present in seconds once actually checked.

4. **Round 4 (properly complete, and this is what's trustworthy):** with both the scope and the flatten-completeness issues fixed, all 5 account-plan variants were tested at both out-of-sample and full-period scope, with the complete two-condition flatten mechanism. **4 of 5 variants now show internally consistent results across both scopes** (no more scope-dependent flip-flopping) — 2 favor dynamic, 2 favor flat. **The 5th (BTC 1h/Daily) remains genuinely ambiguous** — the two scopes disagree even under the corrected methodology, and this is reported honestly as unresolved rather than forced to a conclusion.

**The single most important lesson from this entire saga, worth internalizing for any future feature test on this strategy:** a simplified backtest is a legitimate tool for isolating a specific technical bug, but (a) its conclusion about whether a feature actually *helps* must be re-confirmed against the complete methodology before trusting it, and (b) even a "complete methodology" test should be checked for internal consistency across multiple valid scopes before being trusted — agreement between two scopes is itself evidence of correctness; disagreement is a sign something is still wrong or the answer is genuinely inconclusive, not a coin flip to call either way.

**Status: closed for 4 of 5 variants (Section 2's configuration is trustworthy for those). Open for BTC 1h/Daily specifically — defaults to flat until resolved.**

---

*This document reflects an extended, multi-session, multi-participant validation effort. Every backtest figure cites real historical price data (NQ and CME MBT futures) with in-sample/out-of-sample splits; every firm rule was confirmed against official documentation or direct account experience, not assumed; every bug fix and every reversal described above was verified by direct, numerical re-testing, not just reasoned about.*
