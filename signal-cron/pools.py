"""MESIN POOL LP — JANGAN UBAH (bagian dari INDIKATOR BEKU).
Meniru Liquidity Pools Pro v1.1.5: Adaptive Pivot Length ON, Right Confirm 2,
Equality Tolerance 0.25xATR, Max Lookback 200, Max Pools 40, Half-Life 150,
Volume-Weighted ON, Min Strength Signal 25. Tanpa HTF confluence (default TV OFF).
API: compute(df) -> sinyal per bar TERTUTUP: sweepBuy/sweepSell/strBuy/strSell/nearAbove/nearBelow.
"""
import pandas as pd
import numpy as np

LEFT = 8
RIGHT = 2
ADAPTIVE = True           # samakan TV: Adaptive Pivot Length ON
TOL_ATR = 0.25
MAX_LOOKBACK = 200
MAX_POOLS = 40
HALF_LIFE = 150
MIN_STR_SIG = 25


def _pivots(high, low, L=LEFT, R=RIGHT):
    h = pd.Series(high)
    l = pd.Series(low)
    w = L + R + 1
    wmax = h.rolling(w).max().values
    wmin = l.rolling(w).min().values
    hv, lv = h.values, l.values
    n = len(h)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(n):
        j = i - R
        if j < 0 or np.isnan(wmax[i]):
            continue
        if hv[j] == wmax[i]:
            ph[i] = hv[j]
        if lv[j] == wmin[i]:
            pl[i] = lv[j]
    return ph, pl


def _adaptive_left(atr14, atr50):
    vr = atr14 / atr50 if atr50 > 0 else 1.0
    return int(round(max(4.0, min(16.0, 10.0 / max(0.5, vr)))))


def compute(df, vol_col="volume"):
    high = df.high.values; low = df.low.values; close = df.close.values
    vol = df[vol_col].values if vol_col in df.columns else np.zeros(len(df))
    ts = df.timestamp.values if "timestamp" in df.columns else np.arange(len(df))
    # ATR Wilder sederhana
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().values
    # ATR50 utk adaptive pivot (persis LP: volRatio = ATR14/ATR50)
    atr50 = pd.Series(tr).ewm(alpha=1/50, adjust=False).mean().values
    n = len(df)
    # pools: dict list
    pools = []  # {level, top, bot, lastIdx, touch, cumVol, isHigh, state}
    swBuy = np.zeros(n, bool); swSell = np.zeros(n, bool)
    swBuyS = np.zeros(n); swSellS = np.zeros(n)
    nearAbove = np.full(n, np.nan); nearBelow = np.full(n, np.nan)
    vols = []
    volMed = np.nan
    miti = 0
    for i in range(n):
        tol = atr[i] * TOL_ATR
        # --- pivot adaptif terkonfirmasi di bar i (pivot di i-RIGHT) ---
        L = _adaptive_left(atr[i], atr50[i]) if ADAPTIVE else LEFT
        j = i - RIGHT
        newPH, newPL = np.nan, np.nan
        if j >= L:
            if high[j] == np.max(high[j-L+1:i+1]):
                newPH = high[j]
            if low[j] == np.min(low[j-L+1:i+1]):
                newPL = low[j]
        # --- nearest active pools (untuk TP) ---
        bestA, bestB = np.inf, -np.inf
        for p in pools:
            if p["state"] != 0:
                continue
            if p["isHigh"] and p["level"] > close[i] and p["level"] < bestA:
                bestA = p["level"]
            if not p["isHigh"] and p["level"] < close[i] and p["level"] > bestB:
                bestB = p["level"]
        nearAbove[i] = bestA if np.isfinite(bestA) else np.nan
        nearBelow[i] = bestB if np.isfinite(bestB) else np.nan
        # --- volume median ---
        if len(pools) >= 3 and (np.isnan(volMed) or i % 25 == 0):
            volMed = float(np.median([p["cumVol"] for p in pools]))
        # --- akumulasi volume-at-level ---
        bv = vol[i] if np.isfinite(vol[i]) else 0.0
        if bv > 0:
            for p in pools:
                if p["state"] == 0 and i > p["lastIdx"]:
                    if (high[i] >= p["bot"] and high[i] <= p["top"]) or \
                       (low[i] >= p["bot"] and low[i] <= p["top"]) or \
                       (low[i] <= p["bot"] and high[i] >= p["top"]):
                        p["cumVol"] += bv
        # --- strength + sweep check per pool (pakai toleransi bar ini) ---
        for p in pools:
            if p["state"] != 0 or i < p["lastIdx"] + RIGHT + 1:
                continue
            age = i - p["lastIdx"]
            touchPts = min(35.0, (p["touch"] - 1) * 9.0)
            recency = 35.0 * (0.5 ** (age / HALF_LIFE))
            volPts = 0.0
            if np.isfinite(volMed) and volMed > 0:
                r = p["cumVol"] / volMed
                volPts = min(20.0, np.log(max(1.0, r)) * 8.0)
            s = max(0.0, min(100.0, touchPts + recency + volPts))
            top = p["level"] + tol / 2.0
            bot = p["level"] - tol / 2.0
            if p["isHigh"]:
                wick = high[i] > top
                back = close[i] < p["level"]
                if wick and back:
                    p["state"] = 2; p["sweptIdx"] = i
                    if s >= MIN_STR_SIG:
                        swSell[i] = True
                        swSellS[i] = max(swSellS[i], s)
                elif wick:
                    p["state"] = 1; p["sweptIdx"] = i
            else:
                wick = low[i] < bot
                back = close[i] > p["level"]
                if wick and back:
                    p["state"] = 2; p["sweptIdx"] = i
                    if s >= MIN_STR_SIG:
                        swBuy[i] = True
                        swBuyS[i] = max(swBuyS[i], s)
                elif wick:
                    p["state"] = 1; p["sweptIdx"] = i
        # --- proses pivot baru di bar i (sudah terkonfirmasi kanan) ---
        if not np.isnan(newPH):
            _add_touch(pools, float(newPH), j, float(vol[j] if np.isfinite(vol[j]) else 0.0),
                       True, tol, MAX_LOOKBACK)
        if not np.isnan(newPL):
            _add_touch(pools, float(newPL), j, float(vol[j] if np.isfinite(vol[j]) else 0.0),
                       False, tol, MAX_LOOKBACK)
        # --- prune ---
        if len(pools) > MAX_POOLS:
            swept = [p for p in pools if p["state"] != 0]
            if swept:
                victim = min(swept, key=lambda p: p.get("sweptIdx", 10**9))
                pools.remove(victim)
            else:
                # weakest active (strength kasar: touch - age/50)
                victim = min(pools, key=lambda p: p["touch"] * 9 - (i - p["lastIdx"]) / 50)
                pools.remove(victim)
    return pd.DataFrame({"timestamp": ts, "sweepBuy": swBuy, "sweepSell": swSell,
                         "strBuy": swBuyS, "strSell": swSellS,
                         "nearAbove": nearAbove, "nearBelow": nearBelow})


def _add_touch(pools, price, idx, pv, isHigh, tol, lookback):
    for p in pools:
        if p["state"] == 0 and p["isHigh"] == isHigh and \
           abs(price - p["level"]) <= tol and (idx - p["lastIdx"]) <= lookback:
            p["level"] = (p["level"] * p["touch"] + price) / (p["touch"] + 1)
            p["lastIdx"] = idx
            p["touch"] += 1
            p["cumVol"] += pv
            return
    pools.append({"level": price, "top": price, "bot": price, "lastIdx": idx,
                  "touch": 1, "cumVol": pv, "isHigh": isHigh, "state": 0,
                  "sweptIdx": 10**9})
