"""
Normie NQ - Dynamic Regime-Scaled Stop Backtest
=================================================
Self-contained reproduction of the backtest used to justify the dynamic-stop
feature in normie_nq_debug.pine. Given directly to another session for a
line-by-line diff against its own independent implementation, since the two
backtests currently disagree on whether the dynamic stop helps or hurts.

INPUT FILES (edit paths below to match your environment):
  - 15-minute OHLC CSV  (drives FVG signal detection)
  - 30-minute OHLC CSV  (drives the sticky LOC state machine)
  - 4-hour OHLC CSV     (drives the bias EMA)
  - 1-hour OHLC CSV     (drives the volatility regime ratio)

All CSVs expected in TradingView export format: columns time,open,high,low,close
(time = unix seconds, UTC).

KNOWN SIMPLIFICATIONS vs. the live Pine script (flagged honestly, not hidden):
  - Touch/fill/outcome resolution uses 15-MINUTE bar granularity, not true
    1-minute precision. This is coarser than live execution and is the most
    likely source of any remaining discrepancy with a 1m-precision backtest.
  - No proximity-dedup logic (the "skip new zone if an unfilled zone already
    exists nearby" rule) is modeled here.
  - Assumes continuous bias/LOC monitoring on pending zones (confirmed correct
    per project ground truth), sticky gap-based LOC (also confirmed correct).
"""

import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# CONFIG - edit these paths
# ---------------------------------------------------------------------------
PATH_15M = "CME_MINI_MNQ1___15_108a6.csv"
PATH_30M = "CME_MINI_MNQ1___30_1d18b.csv"
PATH_4H  = "CME_MINI_MNQ1___240_823a7.csv"
PATH_1H  = "CME_MINI_MNQ1___60_6be9b.csv"

BASE_STOP = 42.5          # points, flat baseline stop
MAX_WAIT_15M_BARS = 30    # zone expires if unfilled after this many 15m bars
EXCLUDED_HOURS_ET = {16, 18}
REGIME_ROLL_LEN = 10      # rolling window length, in OCCURRENCES of a given hour
STOP_FLOOR_MULT = 0.5
STOP_CEIL_MULT = 2.0

# 5-year hourly baseline stdev (%, ETH). Hours 16/17 have no coverage (na).
REGIME_BASELINE = {
    0:0.122, 1:0.149, 2:0.170, 3:0.236, 4:0.220, 5:0.171, 6:0.186, 7:0.219,
    8:0.395, 9:0.491, 10:0.508, 11:0.400, 12:0.331, 13:0.419, 14:0.352, 15:0.425,
    16:np.nan, 17:np.nan,
    18:0.232, 19:0.166, 20:0.189, 21:0.172, 22:0.142, 23:0.115,
}


def load_csv(path):
    df = pd.read_csv(path)
    df["dt_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.sort_values("dt_utc").reset_index(drop=True)


def compute_bias_ema(df4h, length=5):
    """4h EMA(length), offset by 1 bar (avoids using the still-forming bar's own EMA)."""
    df4h = df4h.copy()
    df4h["ema"] = df4h["close"].ewm(span=length, adjust=False).mean()
    df4h["htfEma"] = df4h["ema"].shift(1)
    return df4h[["dt_utc", "htfEma"]].dropna()


def compute_sticky_loc(df30):
    """
    Sticky gap-based LOC state machine. Direction only changes when a genuine
    2-bar gap forms AND (for a reversal) the close confirms past the prior
    locPrice level. Holds its last direction otherwise - this is the
    CONFIRMED-CORRECT definition per project ground truth (not the simple
    close-vs-line comparison, which independent backtesting found inferior).
    """
    df30 = df30.copy()
    h = df30["high"].values
    l = df30["low"].values
    c = df30["close"].values
    n = len(df30)

    direction = np.zeros(n, dtype=int)
    loc_price = np.full(n, np.nan)
    dir_cur, price_cur = 0, np.nan

    for i in range(n):
        if i >= 2:
            bull_gap = h[i - 2] < l[i]
            bear_gap = l[i - 2] > h[i]
            if bull_gap:
                if dir_cur == 0:
                    dir_cur, price_cur = 1, l[i]
                elif dir_cur == -1 and c[i] > price_cur:
                    dir_cur, price_cur = 1, l[i]
                elif dir_cur == 1:
                    price_cur = l[i]
            if bear_gap:
                if dir_cur == 0:
                    dir_cur, price_cur = -1, h[i]
                elif dir_cur == 1 and c[i] < price_cur:
                    dir_cur, price_cur = -1, h[i]
                elif dir_cur == -1:
                    price_cur = h[i]
        direction[i] = dir_cur
        loc_price[i] = price_cur

    df30["stickyDir_raw"] = direction
    df30["locPrice_raw"] = loc_price
    # [1] offset - matches how the script reads it (direction[1], locPrice[1])
    df30["stickyDir"] = df30["stickyDir_raw"].shift(1)
    df30["locPrice"] = df30["locPrice_raw"].shift(1)
    return df30[["dt_utc", "stickyDir", "locPrice"]].dropna()


def compute_regime_ratio(df1h, roll_len=REGIME_ROLL_LEN, baseline=REGIME_BASELINE):
    """
    Rolling volatility regime ratio, tracked SEPARATELY per hour-of-day (NY tz).
    For each hourly bar, the ratio uses only PRIOR occurrences of that same
    hour - the current/just-closed hour's own return is added to history only
    AFTER its ratio is computed, so there is no lookahead.
    """
    df1h = df1h.copy()
    df1h["dt_ny"] = df1h["dt_utc"].dt.tz_convert(ZoneInfo("America/New_York"))
    df1h["hour_ny"] = df1h["dt_ny"].dt.hour
    df1h["ret"] = (df1h["close"] - df1h["open"]) / df1h["open"]

    hour_hist = {h: [] for h in range(24)}
    ratios = []
    for _, row in df1h.iterrows():
        hh, ret = row["hour_ny"], row["ret"]
        base = baseline[hh]
        ratio = np.nan
        if len(hour_hist[hh]) >= roll_len and not np.isnan(base) and base != 0:
            ratio = np.std(hour_hist[hh][-roll_len:], ddof=1) * 100 / base
        ratios.append(ratio)
        if not np.isnan(ret):
            hour_hist[hh].append(ret)
            if len(hour_hist[hh]) > roll_len:
                hour_hist[hh].pop(0)

    df1h["regimeRatio"] = ratios
    return df1h[["dt_utc", "regimeRatio"]].dropna()


def generate_trades(df15, htf_ema, sticky_loc, regime_ratio):
    """
    FVG detection + zone arm/monitor simulation.
    - Arm requires: FVG pattern + bias/LOC agreement + not an excluded hour.
    - Monitor: CONTINUOUS bias/LOC re-check every bar while pending (confirmed
      correct design - NOT touch-only, which independent testing found costs
      ~7% of edge).
    - FVG offsets use bars [i-1, i-2, i-3] relative to the "current" 15m bar i,
      matching the script's own [1],[2],[3] shift (reads the last CLOSED
      candle, not a still-forming one).
    """
    df = df15.copy()
    df = pd.merge_asof(df.sort_values("dt_utc"), htf_ema.sort_values("dt_utc"), on="dt_utc", direction="backward")
    df = pd.merge_asof(df.sort_values("dt_utc"), sticky_loc.sort_values("dt_utc"), on="dt_utc", direction="backward")
    df = pd.merge_asof(df.sort_values("dt_utc"), regime_ratio.sort_values("dt_utc"), on="dt_utc", direction="backward")
    df["hour_ny"] = df["dt_utc"].dt.tz_convert(ZoneInfo("America/New_York")).dt.hour

    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    htfEma = df["htfEma"].values
    stickyDir = df["stickyDir"].values
    regimeRatio = df["regimeRatio"].values
    hour_ny = df["hour_ny"].values
    n = len(df)

    trades = []
    pending = []
    for i in range(3, n):
        bull_bias = c[i] > htfEma[i] if not np.isnan(htfEma[i]) else False
        bear_bias = c[i] < htfEma[i] if not np.isnan(htfEma[i]) else False
        loc_ok_bull = (stickyDir[i] == 1) if not np.isnan(stickyDir[i]) else False
        loc_ok_bear = (stickyDir[i] == -1) if not np.isnan(stickyDir[i]) else False
        valid_bull = bull_bias and loc_ok_bull
        valid_bear = bear_bias and loc_ok_bear
        in_session = hour_ny[i] not in EXCLUDED_HOURS_ET

        h0, h1, h2 = h[i - 1], h[i - 2], h[i - 3]
        l0, l1, l2 = l[i - 1], l[i - 2], l[i - 3]
        c0 = c[i - 1]
        bull_gap = h2 < l0
        bull_normie = bull_gap and c0 <= h1
        bear_gap = l2 > h0
        bear_normie = bear_gap and c0 >= l1

        if bull_normie and valid_bull and in_session:
            pending.append({"dir": "LONG", "entry": l0, "armed_i": i})
        if bear_normie and valid_bear and in_session:
            pending.append({"dir": "SHORT", "entry": h0, "armed_i": i})

        still_pending = []
        for z in pending:
            expired = (i - z["armed_i"]) > MAX_WAIT_15M_BARS
            vb = valid_bull if z["dir"] == "LONG" else valid_bear
            if not vb:
                continue  # continuous invalidation - cancelled immediately
            touched = (l[i] <= z["entry"]) if z["dir"] == "LONG" else (h[i] >= z["entry"])
            if touched:
                trades.append({"dir": z["dir"], "entry": z["entry"], "armed_i": z["armed_i"], "fill_i": i})
            elif not expired:
                still_pending.append(z)
        pending = still_pending

    return trades, h, l, regimeRatio, n


def resolve_outcomes(trades, h, l, regimeRatio, n, stop_mode, max_lookforward=2000):
    outcomes = []
    for t in trades:
        entry, d, fi, ai = t["entry"], t["dir"], t["fill_i"], t["armed_i"]
        if stop_mode == "fixed":
            stop_dist = BASE_STOP
        else:
            ratio = regimeRatio[ai]
            mult = ratio if not np.isnan(ratio) else 1.0
            mult = max(STOP_FLOOR_MULT, min(STOP_CEIL_MULT, mult))
            stop_dist = BASE_STOP * mult

        if d == "LONG":
            target, stop = entry + stop_dist, entry - stop_dist
        else:
            target, stop = entry - stop_dist, entry + stop_dist

        outcome = "unresolved"
        for j in range(fi, min(fi + max_lookforward, n)):
            hit_target = (h[j] >= target) if d == "LONG" else (l[j] <= target)
            hit_stop = (l[j] <= stop) if d == "LONG" else (h[j] >= stop)
            if hit_target and hit_stop:
                outcome = "ambiguous"
                break
            elif hit_target:
                outcome = "win"
                break
            elif hit_stop:
                outcome = "loss"
                break
        outcomes.append(outcome)
    return outcomes


def summarize(label, outcomes):
    wins = outcomes.count("win")
    losses = outcomes.count("loss")
    decided = wins + losses
    wr = wins / decided * 100 if decided else float("nan")
    net_r = wins - losses
    print(f"{label:35s}: n={len(outcomes):5d}  Wins={wins:4d}  Losses={losses:4d}  WR={wr:5.1f}%  NetR={net_r:5d}")


if __name__ == "__main__":
    df15 = load_csv(PATH_15M)
    df30 = load_csv(PATH_30M)
    df4h = load_csv(PATH_4H)
    df1h = load_csv(PATH_1H)

    htf_ema = compute_bias_ema(df4h)
    sticky_loc = compute_sticky_loc(df30)
    regime_ratio = compute_regime_ratio(df1h)

    trades, h, l, regimeRatio, n = generate_trades(df15, htf_ema, sticky_loc, regime_ratio)
    print(f"Total trades generated: {len(trades)}\n")

    for label, mode in [("Fixed 42.5pt stop", "fixed"), ("Dynamic stop (0.5x-2.0x regime)", "dynamic")]:
        outcomes = resolve_outcomes(trades, h, l, regimeRatio, n, mode)
        summarize(label, outcomes)
