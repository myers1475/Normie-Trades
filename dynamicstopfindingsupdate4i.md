## 4i. Update — Root Cause Found in Regime-Ratio Hour Lookup (Not DST)

Following up on 4h: rather than raise a sixth untested theory, CD ran the specific check 4h recommended — comparing actual regime-ratio *values* between the two backtests for trades where timing is already perfectly aligned (post-March-8, both pre- and post-DST-fix, since those timestamps matched exactly even before OG's DST fix).

**Test performed:** matched 43 trades by identical `armed_dt` (post-DST-boundary, so timing/timezone is a controlled variable) between CD's dump and OG's original dump, and directly compared the `regime_ratio` column.

**Result: 42 of 43 matched trades have meaningfully different ratio values — several by a large margin** (e.g., one trade: CD=3.2317, OG=1.0773; another: CD=1.2232, OG=3.3079). These aren't rounding differences — they look like two different quantities being computed, not the same quantity computed slightly differently.

**Mechanism found, by direct code inspection:** OG's script uses one shared helper, `get_prior_bucket`, for three different higher-timeframe lookups (4h EMA, 30m LOC, and 1h regime ratio):

```python
def get_prior_bucket(epoch, bucket_seconds, index_map):
    b = epoch - (epoch % bucket_seconds)
    return index_map.get(b - bucket_seconds)
```

This steps back **one full bucket** before returning anything — correct and necessary for the 4h EMA and 30m LOC lookups, since those values could still reflect an unclosed/forming bar if read at their own timestamp, and stepping back one bucket avoids that.

**It's the wrong pattern for the regime ratio specifically.** The regime-ratio construction (both scripts, confirmed identical) already excludes the current hour's own return from its own stored value — the ratio at hour X's row only reflects *prior* occurrences of hour X, so it's already safe to use at hour X's own timestamp, with no additional step-back needed. Applying `get_prior_bucket`'s extra step-back on top of that doesn't add safety margin — it looks up a **different hour-of-day bucket entirely**. A trade arming at 9:15am doesn't get hour 9's regime ratio; it gets hour 8's — a different baseline (0.395% vs. 0.491%) and an entirely different rolling-window history. That's not a timing nuance; it's comparing against the wrong reference distribution outright, and it would produce exactly the kind of large, seemingly uncorrelated value differences observed above.

**This is a strong, mechanistically precise candidate — found by code inspection with a concrete, numerically-verified symptom, not another blind hypothesis.** It also cleanly explains why the DST fix in 4h didn't resolve the sign disagreement: DST governs *which calendar hour* a bar falls into, but this bug governs *which hour-of-day's ratio gets fetched* once trades are already correctly bucketed — two independent things that happened to both be wrong.

### Recommended next steps
1. In OG's script, change the regime-ratio lookup to use the **current** hour bucket directly (no step-back), rather than reusing `get_prior_bucket`. E.g., a lookup that maps the FVG's epoch straight to its own containing hour bucket's already-safe stored ratio value — matching how CD's `merge_asof(direction="backward")` naturally resolves to the current (or most recent available) bucket, not one bucket earlier.
2. Re-run OG's full backtest with this fix applied (keep the DST fix from 4g/4h — it's real and correct, just not sufficient on its own).
3. Re-check the same trade-level ratio comparison done here (43 aligned trades, direct value diff) after the fix — if ratios now match closely between the two backtests, that's strong confirmation this was the actual cause, not just a plausible story.
4. Continue treating the dynamic stop as unvalidated until ratios and aggregate win rates both converge. Do not deploy live.
