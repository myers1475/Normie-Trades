## 4g. RESOLVED — Root Cause Found: OG's Fixed UTC-4 Offset Doesn't Handle DST

Following up on 4f: CD generated the requested identical trade dump for March 2026 (66 trades, same columns as OG's 64-trade list) and lined the two up side by side. The divergence point was immediate and unambiguous.

**The pattern:**
- **Every trade armed before March 8, 2026** (the US spring-forward DST transition): OG's timestamp is exactly **1 hour later** than CD's, on every single row.
- **Every trade armed on or after March 8, 2026**: the two lists match **exactly**, to the minute, on every row checked (e.g., `2026-03-09 20:45`, `2026-03-10 03:30`, `2026-03-10 04:15`, `2026-03-10 23:45`, `2026-03-11 05:00`, `2026-03-11 19:45`, `2026-03-11 22:45` — identical in both).

**Root cause:** OG's script sets timezone via a fixed offset:

```python
TZ = timezone(timedelta(hours=-4))  # ET approximation, matches rest of project
```

Real US Eastern Time is UTC-5 (EST) for roughly the November–mid-March window and only UTC-4 (EDT) the rest of the year. A fixed `-4` offset is silently wrong for about 8 months of every year — it treats every EST-period timestamp as if it were 1 hour later than it actually is in true ET. CD's pipeline uses proper DST-aware timezone conversion (`zoneinfo("America/New_York")`), which is why the two lists agree perfectly once DST is actually in effect and diverge by exactly one hour whenever it isn't.

**Why this produced the specific symptom seen throughout this whole investigation** (dynamic stop disagreeing, flat-stop baselines staying close): both the hour-exclusion rule (16:00/18:00 ET) and the entire regime-ratio calculation are keyed on hour-of-day. A systematic 1-hour misattribution, active across roughly 8 months of the ~21-month dataset, would scramble which hour's rolling history bucket a huge fraction of returns get sorted into — directly corrupting the regime-ratio computation specifically, while leaving the flat 42.5pt baseline comparatively unaffected (it doesn't depend on hour-of-day at all beyond the exclusion rule). This lines up exactly with what was actually observed: the flat baselines between the two backtests were always close (60.3%–60.7% across every round), while only the dynamic-stop numbers disagreed.

**Status: root cause identified and directly evidenced (not just hypothesized) via exact timestamp matching either side of a known, checkable calendar boundary.** This is not a new untested candidate — the DST transition boundary is a hard fact, and the before/after match is exact.

### Recommended next steps
1. Fix OG's `TZ` handling to use a real DST-aware timezone conversion (`zoneinfo("America/New_York")`, `pytz`, or equivalent) instead of a fixed offset, matching CD's approach.
2. Re-run OG's full backtest (fixed vs. dynamic stop) with this corrected timezone handling. Given the mechanism identified, dynamic stop should now be expected to outperform, matching CD's result and the original script comment — but confirm this empirically rather than assuming it.
3. Once both backtests agree using correctly DST-aware timestamps, the dynamic-stop feature can be considered validated and the `useDynamicStop` default can be safely reverted to `true` in the live script.
