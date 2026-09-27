"""Live paper trading (spot, long-only) — mirror dss_spot.py, tanpa order real.
Sleeve (equity awal): BTC 25/25, ETH/SOL/ZEC/BNB/XRP 5/5 (4H/1D).
Loop tiap 60 dtk: fetch Binance public -> sinyal closed-bar -> kelola posisi
(SL/TP1+BE/MOM/FVG/cash-1w/cycle/sesi/cooldown-3xSL) -> live_data.json + state.
Jalankan: py live_paper.py [--once]   (--once = 1 iterasi dry-run)
"""
import urllib.request
import json
import os
import sys
import time
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # pools.py lokal (repo ringan, tanpa CSV)
try:
    import pools as pools  # noqa: E402
except ImportError:
    OLD = os.path.abspath(os.path.join(HERE, "..", "scalp-backtest"))
    if not os.path.isdir(OLD):
        OLD = os.path.abspath(os.path.join(HERE, "..", "..", "scalp-backtest"))
    sys.path.insert(0, OLD)
    import pools as pools  # noqa: E402  (fallback arsip lokal)

BASES = ["https://data-api.binance.vision", "https://api.binance.com"]
BASE = BASES[0]

DLEN, DEMA, TRIG = 10, 9, 5
EXT_L, EXT_S = 30.0, 70.0
CX_OS = 20.0
FLAT_OS, FLAT_SLOPE = 15.0, 2.0
SWEEP_LB, MIN_STR = 3, 40.0
SL_ATR, SL_LB = 1.5, 4
TP1_R, TP1_QTY = 1.5, 0.25
FEE, SLIP = 0.0005, 0.000025
COOL_H = {"4h": 48, "1d": 288}

SLEEVES = [
    ("BTCUSDT", "4h", 25.0), ("BTCUSDT", "1d", 25.0),
    ("ETHUSDT", "4h", 5.0), ("ETHUSDT", "1d", 5.0),
    ("SOLUSDT", "4h", 5.0), ("SOLUSDT", "1d", 5.0),
    ("ZECUSDT", "4h", 5.0), ("ZECUSDT", "1d", 5.0),
    ("BNBUSDT", "4h", 5.0), ("BNBUSDT", "1d", 5.0),
    ("XRPUSDT", "4h", 5.0), ("XRPUSDT", "1d", 5.0),
]
STATE = os.path.join(HERE, "paper_live_state.json")
FEED = os.path.join(HERE, "live_data.json")
POLL = 60


def get(url, timeout=15, retry=3):
    global BASE
    last = None
    for _ in range(retry):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2)
    if BASE == BASES[0]:
        BASE = BASES[1]
        return get(url.replace(BASES[0], BASES[1]), timeout, retry)
    raise last


def klines(sym, tf, limit=500):
    raw = get(f"{BASE}/api/v3/klines?symbol={sym}&interval={tf}&limit={limit}")
    return [{"t": k[0] // 1000, "o": float(k[1]), "h": float(k[2]),
             "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in raw]


def price(sym):
    return float(get(f"{BASE}/api/v3/ticker/price?symbol={sym}")["price"])


def ema_all(v, n):
    k = 2 / (n + 1)
    e = v[0]
    out = [e]
    for x in v[1:]:
        e = x * k + e * (1 - k)
        out.append(e)
    return out


def dss_series(cc, hh, ll):
    n = len(cc)
    s1 = []
    for i in range(n):
        lo = min(ll[max(0, i - DLEN + 1):i + 1])
        hi = max(hh[max(0, i - DLEN + 1):i + 1])
        s1.append(100.0 * (cc[i] - lo) / (hi - lo) if hi > lo else 50.0)
    p1 = ema_all(s1, DEMA)
    s2 = []
    for i in range(n):
        lo = min(p1[max(0, i - DLEN + 1):i + 1])
        hi = max(p1[max(0, i - DLEN + 1):i + 1])
        s2.append(100.0 * (p1[i] - lo) / (hi - lo) if hi > lo else 50.0)
    d = ema_all(s2, DEMA)
    return d, ema_all(d, TRIG)


def atr_last(hh, ll, cc, n=14):
    trs = [hh[0] - ll[0]]
    for i in range(1, len(hh)):
        trs.append(max(hh[i] - ll[i], abs(hh[i] - cc[i - 1]), abs(ll[i] - cc[i - 1])))
    k = 1 / n
    e = trs[0]
    for v in trs[1:]:
        e = v * k + e * (1 - k)
    return e


def pool_tail(bars):
    """pools.compute atas closed bars; return 3 bar terakhir (sweepBuy/strBuy)."""
    import pandas as pd

    df = pd.DataFrame([{"timestamp": pd.to_datetime(b["t"], unit="s"), "open": b["o"],
                        "high": b["h"], "low": b["l"], "close": b["c"], "volume": b["v"]}
                       for b in bars])
    return pools.compute(df).tail(SWEEP_LB)


def fvg_bull_fills(h1bars):
    """Timestamp fill gap-bullish besar 1H/4H (terisi penuh + close)."""
    hh = [b["h"] for b in h1bars]
    ll = [b["l"] for b in h1bars]
    cc = [b["c"] for b in h1bars]
    tt = [b["t"] for b in h1bars]
    trs = [hh[0] - ll[0]]
    for i in range(1, len(hh)):
        trs.append(max(hh[i] - ll[i], abs(hh[i] - cc[i - 1]), abs(ll[i] - cc[i - 1])))
    import pandas as pd

    atr = pd.Series(trs).ewm(alpha=1 / 14, adjust=False).mean().tolist()
    fills = set()
    n = len(h1bars)
    for k in range(2, n):
        if ll[k] > hh[k - 2] and (ll[k] - hh[k - 2]) >= 0.5 * atr[k]:
            bot = hh[k - 2]
            for j in range(k + 1, n):
                if (tt[j] - tt[k]) > 14 * 86400:
                    break
                if cc[j] <= bot:
                    fills.add(tt[j])
                    break
    return fills


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    st = {"equity": {}, "positions": {}, "trades": [], "scan": [], "cool": {}, "consec": {}}
    for sym, tf, eq in SLEEVES:
        st["equity"][f"{sym}_{tf}"] = eq
    return st


def save_state(st):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f)


def wibnow():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)


def close_trade(st, key, exit_px, reason, r, qty, nowhm):
    st["trades"].append({"time": nowhm, "sym": key.split("_")[0], "tf": key.split("_")[1],
                         "reason": reason, "pnl": round(r * qty * 100, 2)})
    if reason == "SL":
        st["consec"][key] = st.get("consec", {}).get(key, 0) + 1
        if st["consec"][key] >= 3:
            tf = key.split("_")[1]
            st.setdefault("cool", {})[key] = time.time() + COOL_H[tf] * 3600
            st["consec"][key] = 0
    else:
        st.setdefault("consec", {})[key] = 0
    if key in st["positions"]:
        del st["positions"][key]


def sleeve_iter(st, sym, tf, market):
    key = f"{sym}_{tf}"
    nowhm = wibnow().strftime("%H:%M")
    bars = market.get((sym, tf))
    px = market.get((sym, "px"))
    if not bars or len(bars) < 60 or px is None:
        return [f"{key} data kurang"]
    closed = bars[:-1]
    cc = [b["c"] for b in closed]
    hh = [b["h"] for b in closed]
    ll = [b["l"] for b in closed]
    oo = [b["o"] for b in closed]
    dd, tt = dss_series(cc, hh, ll)
    atr = atr_last(hh, ll, cc)
    market[(sym, tf + "_dss")] = round(dd[-1], 1)
    eq = st["equity"].get(key, 0.0)
    poss = st["positions"].get(key)
    min_hold = 4 * 3600 if tf == "4h" else 24 * 3600
    hold_ok = True
    if poss:
        try:
            t0 = datetime.datetime.fromisoformat(poss["t"])
            hold_ok = (datetime.datetime.utcnow() - t0).total_seconds() >= min_hold
        except Exception:
            pass
    if poss:
        entry, sl = poss["entry"], poss["sl"]
        risk0 = poss["risk"]
        qty, tp1, mp = poss.get("qty", 1.0), poss.get("tp1", False), poss.get("mp", False)
        mfe = max(poss.get("mfe", 0.0), (max(hh[-1], px) - entry) / risk0)
        poss["mfe"] = mfe
        if not tp1 and (max(hh[-1], px) - entry) >= risk0 * TP1_R:
            x = entry + risk0 * TP1_R
            r = (x - entry) / entry
            eq *= (1 + r * TP1_QTY - 2 * FEE * TP1_QTY)
            st["trades"].append({"time": nowhm, "sym": sym, "tf": tf, "reason": "TP1",
                                 "pnl": round(r * TP1_QTY * 100, 2)})
            qty -= TP1_QTY
            sl = entry
            tp1 = True
            poss.update({"qty": qty, "sl": sl, "tp1": True})
            st["equity"][key] = eq
            return [f"{key} TP1"]
        if min(ll[-1], px) <= sl:
            r = (sl - entry) / entry
            eq *= (1 + r * qty - 2 * FEE * qty)
            reason = "SL-BE" if (tp1 or mp) else "SL"
            close_trade(st, key, sl, reason, r, qty, nowhm)
            st["equity"][key] = eq
            return [f"{key} {reason}"]
        xD = (dd[-2] <= tt[-2]) and (dd[-1] < tt[-1])
        pt = pool_tail(closed)
        swH = bool(pt["sweepSell"].iloc[-1])
        if hold_ok and (xD or swH):
            r = (px * (1 - SLIP) - entry) / entry
            tag = "X+SWP" if (xD and swH) else ("SWP" if swH else "X")
            if mfe >= 1.0 and not mp:
                pq = qty * 0.5
                eq *= (1 + r * pq - 2 * FEE * pq)
                st["trades"].append({"time": nowhm, "sym": sym, "tf": tf, "reason": "MOM-P:" + tag,
                                     "pnl": round(r * pq * 100, 2)})
                poss.update({"qty": qty - pq, "sl": entry + risk0, "mp": True})
                st["equity"][key] = eq
                return [f"{key} MOM-P"]
            eq *= (1 + r * qty - 2 * FEE * qty)
            close_trade(st, key, px, "MOM:" + tag, r, qty, nowhm)
            st["equity"][key] = eq
            return [f"{key} MOM"]
        if tf == "4h":
            fills = fvg_bull_fills(market[(sym, "1h")][:-1])
            t0 = datetime.datetime.fromisoformat(poss["t"]).timestamp()
            if hold_ok and any(f > t0 for f in fills):
                r = (px * (1 - SLIP) - entry) / entry
                if mfe >= 1.0 and not mp:
                    pq = qty * 0.5
                    eq *= (1 + r * pq - 2 * FEE * pq)
                    st["trades"].append({"time": nowhm, "sym": sym, "tf": tf, "reason": "MOM-P:FVG",
                                         "pnl": round(r * pq * 100, 2)})
                    poss.update({"qty": qty - pq, "sl": entry + risk0, "mp": True})
                    st["equity"][key] = eq
                    return [f"{key} MOM-P:FVG"]
                eq *= (1 + r * qty - 2 * FEE * qty)
                close_trade(st, key, px, "FVG", r, qty, nowhm)
                st["equity"][key] = eq
                return [f"{key} FVG"]
        st["equity"][key] = eq
        return [f"{key} IN POS"]
    # ---- entry (closed bar terakhir) ----
    if market.get("cash1w"):
        return [f"{key} SKIP cash"]
    if sym != "BTCUSDT" and market.get("cyc_block"):
        return [f"{key} SKIP cycle"]
    if tf == "4h":
        wib = wibnow()
        if wib.weekday() in (5, 6) or (7 <= wib.hour <= 15):
            return [f"{key} SKIP sesi"]
    if market.get("cool", {}).get(key, 0) > time.time():
        return [f"{key} SKIP cooldown"]
    pt = pool_tail(closed)
    swLw = bool(pt["sweepBuy"].any())
    strW = float(pt["strBuy"].max())
    dss, trg = dd[-1], tt[-1]
    is_btc = (sym == "BTCUSDT")
    trigL = swLw and dss <= EXT_L and strW >= MIN_STR
    flatL = (dss <= FLAT_OS) and abs(dss - dd[-3]) < FLAT_SLOPE
    cxL = (dd[-2] <= tt[-2]) and (dss > trg) and (dss <= CX_OS)
    take, src = False, ""
    if trigL and (is_btc or market.get("btc_up", True)):
        take, src = True, "sweep"
    elif is_btc and flatL:
        take, src = True, "flat"
    elif (not is_btc) and cxL and market.get("btc_up", True):
        take, src = True, "cross"
    if not take:
        return [f"{key} WAIT dss {dss:.0f}"]
    sl = ll[-1] - atr * SL_ATR
    if sl >= px:
        return [f"{key} SKIP SL-invalid"]
    if src in ("flat", "cross") and sl >= min(ll[-4:]):
        return [f"{key} SKIP rawan-sweep"]
    st["positions"][key] = {"entry": px * (1 + SLIP), "sl": sl,
                            "risk": abs(px * (1 + SLIP) - sl),
                            "qty": 1.0, "tp1": False, "mp": False, "mfe": 0.0,
                            "t": datetime.datetime.utcnow().isoformat(), "src": src}
    return [f"{key} ENTRY {src}"]


def write_feed(st, market):
    eq = sum(st["equity"].values())
    start = sum(eq0 for _, _, eq0 in SLEEVES)
    rets = [t["pnl"] for t in st["trades"]]
    n = len(rets)
    wins = [x for x in rets if x > 0]
    feed = {
        "updated": wibnow().strftime("%H:%M:%S"),
        "account": {
            "equity": round(eq, 2), "startEquity": start,
            "totalPnl": round(eq - start, 2),
            "roi": round((eq - start) / start * 100, 2) if start else 0.0,
            "totalTrades": n, "wins": len(wins), "losses": n - len(wins),
            "winRate": round(len(wins) / n * 100, 2) if n else 0.0,
            "leverage": 1.0, "riskPct": 0.0, "maxDd": 0.0, "volUsd": 0,
            "avgTrd": 0.0, "profitFactor": 0.0, "funding": 0.0,
        },
        "market": [{"sym": s, "price": market.get((s, "px"), 0),
                    "dss4": market.get((s, "4h_dss"), 0), "dss1": market.get((s, "1d_dss"), 0),
                    "vol": 0, "range24": 0, "trade": True}
                   for s in sorted({s for s, _, _ in SLEEVES})],
        "positions": [{"sym": k.split("_")[0], "tf": k.split("_")[1], "entry": p["entry"],
                       "mark": market.get((k.split("_")[0], "px"), p["entry"]),
                       "sl": p["sl"], "lev": 1} for k, p in st["positions"].items()],
        "log": st["trades"][-30:][::-1],
        "equityCurve": [], "scan": st.get("scan", [])[-24:][::-1], "wire": [],
    }
    with open(FEED, "w", encoding="utf-8") as f:
        json.dump(feed, f)


def market_snapshot():
    market = {}
    syms = sorted({s for s, _, _ in SLEEVES})
    for s in syms:
        for tf in ("4h", "1d", "1h"):
            try:
                market[(s, tf)] = klines(s, tf, 300)
            except Exception as e:
                print("fetch gagal", s, tf, e, flush=True)
        try:
            market[(s, "px")] = price(s)
        except Exception as e:
            print("price gagal", s, e, flush=True)
    # cash 1W BTC
    try:
        d = klines("BTCUSDT", "1d", 500)
        import pandas as pd

        b = pd.DataFrame([{"timestamp": pd.to_datetime(x["t"], unit="s"), "open": x["o"],
                           "high": x["h"], "low": x["l"], "close": x["c"]} for x in d])
        w = b.resample("W-SUN", on="timestamp").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        dd, _ = dss_series(w.close.tolist(), w.high.tolist(), w.low.tolist())
        market["cash1w"] = (dd[-2] < 50.0) and ((dd[-2] - dd[-4]) < 0)
    except Exception as e:
        print("cash_1w gagal:", e, flush=True)
        market["cash1w"] = False
    # cycle BTC anchors
    try:
        cyc = json.load(open(os.path.join(HERE, "cycle_btc.json"), encoding="utf-8"))
        anchors = sorted(cyc.get("dcl_wcl_coincide", []))
        today = wibnow().date().isoformat()
        past = [a for a in anchors if a <= today]
        import datetime as dt

        last = dt.date.fromisoformat(past[-1])
        days = (wibnow().date() - last).days - 14
        market["cyc_block"] = (150 <= days <= 320) or (days > 320)
    except Exception:
        market["cyc_block"] = False
    # tren BTC-1D untuk alt
    try:
        d = klines("BTCUSDT", "1d", 120)[:-1]
        dd, _ = dss_series([x["c"] for x in d], [x["h"] for x in d], [x["l"] for x in d])
        market["btc_up"] = (dd[-1] - dd[-3]) >= -1.0
    except Exception:
        market["btc_up"] = True
    return market


def main():
    once = ("--once" in sys.argv)
    st = load_state()
    while True:
        try:
            market = market_snapshot()
            market["cool"] = st.setdefault("cool", {})
            scans = []
            for sym, tf, _eq0 in SLEEVES:
                try:
                    scans += sleeve_iter(st, sym, tf, market)
                except Exception as e:
                    scans.append(f"{sym}_{tf} ERR {e}")
                    print("sleeve error", sym, tf, e, flush=True)
            st["scan"] = (st.get("scan", []) + [{"t": wibnow().strftime("%H:%M"), "msg": m}
                                                for m in scans])[-40:]
            save_state(st)
            write_feed(st, market)
            print(wibnow().strftime("%H:%M:%S"), "ok", len(st["positions"]), "pos", flush=True)
        except Exception as e:
            print("loop error:", e, flush=True)
        if once:
            break
        time.sleep(POLL)


if __name__ == "__main__":
    main()
