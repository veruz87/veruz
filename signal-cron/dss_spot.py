"""DSS + Liquidity bersih (signal-cron): mirror 2 indikator TV, simetris, closed-bar.
TV: dss bressert.txt PDS=10 EMA=9 TRIG=5 OB=80 OS=20.
LP: lp pro.txt pivot=8 right=2 tol=0.25xATR str>=25 wick+sweep+close-balik.
Rule: LONG  = DSS<=30  + sweepBuy dalam 3 bar 4H terakhir (tanpa tunggu cross).
       SHORT = DSS>=70  + sweepSell dalam 3 bar 4H terakhir (tanpa tunggu cross).
SL: wick bar sebelum entry +- 1.5xATR (long: low[i-1]-1.5ATR, short: high[i-1]+1.5ATR).
TP: ikut indikator pool terdekat searah (nearAbove/nearBelow pools.py), min jarak 0.5%,
    fallback 3R jika tidak ada pool valid.
Simetris dua arah. Tanpa bias 1D, tanpa CHoCH, tanpa impulse (itu tambahan strategi lama).
Slot DCL/WCL: CYCLE = "ALL" (nanti: LATE/IN_WINDOW/NEW_LOW) — untuk sekarang nonaktif.
Biaya realistis: taker 0.05%/side, slip 0.0025%, funding 0.01%/8jam.
Data dibaca dari ../scalp-backtest/*.csv (read-only). Output ke signal-cron/results/.
Jalankan: py dss_liquidity.py [SYM] [TF]  (default BTCUSDT 4h; TF 4h|1d)
Penyesuaian 1D: file 1d, funding 3x/bar, tanpa filter sesi, FVG runner di 4H, cooldown 12 hari.
"""
import os
import sys
import json
import pandas as pd
import numpy as np

SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
TF = sys.argv[2] if len(sys.argv) > 2 else "4h"  # 4h | 1d
TF_H = {"4h": 4, "1d": 24}[TF]
FVG_TF = {"4h": "1h", "1d": "4h"}[TF]  # runner FVG 1 TF di bawah: 4H->1H, 1D->4H
HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(os.path.dirname(HERE), "Default Project", "scalp-backtest")
# fallback: repo ini -> ../scalp-backtest
if not os.path.isdir(OLD):
    OLD = os.path.join(HERE, "..", "scalp-backtest")
OLD = os.path.abspath(OLD)
sys.path.insert(0, OLD)
import pools as pools  # reuse tanpa copy (read-only)

DATA_DIR = os.environ.get("DATA_DIR")  # misal .../data-backtest (layout {SYM}/{SYM}_{TF}.csv)


def datpath(sym, tf):
    if DATA_DIR:
        return os.path.join(DATA_DIR, sym, f"{sym}_{tf}.csv")
    return os.path.join(OLD, f"{sym}_{tf}.csv")

F4 = datpath(SYM, TF)
F15 = os.path.join(OLD, f"{SYM}_15m.csv")  # legacy, tidak dipakai lagi (exit CH15 dicabut)
TP1_R = 1.5  # TP1 25% di +1.5R + SL ke BE (sesuai diskusi)
TP1_QTY = 0.25
TP2_QTY = 0.25  # runner sweep-mode: TP2 25% di pool, sisa 50% hanya keluar di sweep-lawan/SL
PIV15 = 5  # pivot CHoCH 15M untuk exit runner
DLEN, DEMA, TRIG = 10, 9, 5
OS, OB = 20.0, 80.0
EXT_L, EXT_S = 30.0, 70.0
SWEEP_LB = 3
SL_ATR = 1.5  # SL = wick bar sebelum entry +- 1.5xATR (sesuai diskusi)
TP_FALLBACK_R = 3.0  # jika pool tidak valid
MIN_TP_PCT = 0.5  # pool minimal 0.5% dari entry (filter jarak magnet)
FEE, SLIP = 0.0005, 0.000025
FUND_8H = float(os.environ.get("FUND_8H", "0.0001"))  # spot: 0 (tanpa funding)
USE_PCT = float(os.environ.get("USE_PCT", "0.05"))
LEV = float(os.environ.get("LEV", "5.0"))  # spot: 1 (tanpa leverage)
FUND_BAR = FUND_8H * TF_H / 8.0  # funding per bar: 4H->0.5x, 1D->3x
COOL_H = 48 if TF == "4h" else 288  # cooldown 3xSL: 48 jam (4H) / 12 hari (1D)
USE_PCT = float(os.environ.get("USE_PCT", "0.05"))
LEV = float(os.environ.get("LEV", "5.0"))  # spot: 1 (tanpa leverage)
NOTIONAL = USE_PCT * LEV
START, END = "2020-01-01", "2025-11-30"
INIT_EQ = float(os.environ.get("INIT_EQ", "100.0"))  # alokasi sleeve (compounding per sleeve)
CYCLE = "ALL"  # slot DCL/WCL nanti


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def stoch(c, h, l, n):
    lo = l.rolling(n).min()
    hi = h.rolling(n).max()
    return ((c - lo) / (hi - lo).replace(0, np.nan) * 100.0).fillna(50.0)


df = pd.read_csv(F4, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
df = df[(df["timestamp"] >= START) & (df["timestamp"] <= END)].reset_index(drop=True)
s1 = stoch(df.close, df.high, df.low, DLEN)
# FILTER SIKLUS BTC-WCL (khusus ALT): anchor manual cycle_btc.json (DCL+WCL bertepatan).
# IN_WINDOW (150-320 hari sejak WCL terakhir / overdue) -> alt stop entry long.
# NEW_LOW (<=21 hari sejak WCL terkonfirmasi, lag konfirmasi 14 hari) -> gas penuh.
# BTC sendiri tanpa filter (dia acuannya).
CYCW_ON = os.environ.get("CYCW_ON", "1") == "1"
CYCW_WIN_LO, CYCW_WIN_HI, CYCW_NEW = 150, 320, 21
CYCW_LAG = 14
try:
    _cyc = json.load(open(os.path.join(HERE, "cycle_btc.json"), encoding="utf-8"))
    _anchors = sorted(pd.to_datetime(_cyc.get("dcl_wcl_coincide", [])))
except Exception:
    _anchors = []
if SYM != "BTCUSDT" and CYCW_ON and _anchors:
    _ad = pd.DataFrame({"anchor": _anchors})
    _tmp = pd.DataFrame({"timestamp": pd.to_datetime(df.timestamp.values)})
    _tmp = pd.merge_asof(_tmp.sort_values("timestamp"), _ad.sort_values("anchor"),
                         left_on="timestamp", right_on="anchor", direction="backward")
    _last = _tmp.anchor.values
    _dssince = (_tmp.timestamp.values - _last) / np.timedelta64(1, "D")
    _dssince = np.where(pd.isna(_last), -1e9, _dssince)
    _eff = _dssince - CYCW_LAG  # low baru sah setelah lag konfirmasi
    df["cyc_block"] = (_eff >= CYCW_WIN_LO) & (_eff <= CYCW_WIN_HI) | (_eff > CYCW_WIN_HI)
    df["cyc_new"] = (_eff >= 0) & (_eff <= CYCW_NEW)
else:
    df["cyc_block"] = False
    df["cyc_new"] = False
# FILTER CASH 1W-BTC (semua pair incl BTC): saat weekly bearish (dss<50 & turun),
# skip semua entry long — pegang cash. Anti-bear 2022. Kausal (weekly kelar dulu).
CASHW_ON = os.environ.get("CASHW_ON", "1") == "1"
_bw = pd.read_csv(datpath("BTCUSDT", "1d"), parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
_bw = _bw.resample("W-SUN", on="timestamp").agg(
    {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna().reset_index()
_ws1 = stoch(_bw.close, _bw.high, _bw.low, DLEN)
_wp1 = ema(_ws1, DEMA)
_bw["dss"] = ema(stoch(_wp1, _wp1, _wp1, DLEN), DEMA)
_bw["cash"] = (_bw.dss < 50.0) & ((_bw.dss - _bw.dss.shift(2)) < 0)
_bwm = _bw[["timestamp", "cash"]].copy()
_bwm["cash"] = _bwm.cash.shift(1)
df = pd.merge_asof(df, _bwm, on="timestamp", direction="backward")
df["cash"] = df.cash.fillna(False)
if not CASHW_ON:
    df["cash"] = False
# FILTER TREN BTC-1D (khusus ALT, closed, backward-merge): long & short wajib searah daily BTC.
# long jika btc1d<=30 ATAU (30-70 dan naik/datar); short jika btc1d>=70 ATAU (30-70 dan turun/datar).
# BTC sendiri tanpa filter (dia acuannya). Berlaku di TF 4H maupun 1D.
BTC_SLOPE = 1.0
if SYM != "BTCUSDT":
    _b = pd.read_csv(datpath("BTCUSDT", "1d"), parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    _bs1 = stoch(_b.close, _b.high, _b.low, DLEN)
    _bp1 = ema(_bs1, DEMA)
    _b["dss"] = ema(stoch(_bp1, _bp1, _bp1, DLEN), DEMA)
    _b["slope"] = _b.dss - _b.dss.shift(2)
    _midb = (_b.dss > EXT_L) & (_b.dss < EXT_S)
    _b["withBTC_L"] = (_b.dss <= EXT_L) | (_midb & (_b.slope >= -BTC_SLOPE))
    _b["withBTC_S"] = (_b.dss >= EXT_S) | (_midb & (_b.slope <= BTC_SLOPE))
    _bm = _b[["timestamp", "withBTC_L", "withBTC_S"]].copy()
    _bm[["withBTC_L", "withBTC_S"]] = _bm[["withBTC_L", "withBTC_S"]].shift(1)
    df = pd.merge_asof(df, _bm, on="timestamp", direction="backward")
    df["withBTC_L"] = df.withBTC_L.fillna(True)
    df["withBTC_S"] = df.withBTC_S.fillna(True)
else:
    df["withBTC_L"] = True
    df["withBTC_S"] = True
# BIAS 1D (closed, backward-merge): jangan lawan arah daily.
# long jika dss1d<=30 ATAU (30-70 dan naik/datar); short jika dss1d>=70 ATAU (30-70 dan turun/datar).
DIR1D_ON = False  # dicabut 2026-09-26 (kedua kali): dobel dengan filter tren BTC, bunuh 90% sinyal
D1_SLOPE = 1.0
d1 = pd.read_csv(datpath(SYM, "1d"), parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
_d1s1 = stoch(d1.close, d1.high, d1.low, DLEN)
_d1p1 = ema(_d1s1, DEMA)
d1["dss"] = ema(stoch(_d1p1, _d1p1, _d1p1, DLEN), DEMA)
d1["slope"] = d1.dss - d1.dss.shift(2)
_mid = (d1.dss > EXT_L) & (d1.dss < EXT_S)
d1["dirL"] = (d1.dss <= EXT_L) | (_mid & (d1.slope >= -D1_SLOPE))
d1["dirS"] = (d1.dss >= EXT_S) | (_mid & (d1.slope <= D1_SLOPE))
d1m = d1[["timestamp", "dirL", "dirS"]].copy()
d1m[["dirL", "dirS"]] = d1m[["dirL", "dirS"]].shift(1)
df = pd.merge_asof(df, d1m, on="timestamp", direction="backward")
df["dirL"] = df.dirL.fillna(True)
df["dirS"] = df.dirS.fillna(True)
if not DIR1D_ON:
    df["dirL"] = True
    df["dirS"] = True
p1 = ema(s1, DEMA)
df["dss"] = ema(stoch(p1, p1, p1, DLEN), DEMA)
df["trg"] = ema(df["dss"], TRIG)
tr = np.maximum(df.high - df.low, np.maximum((df.high - df.close.shift(1)).abs(),
                                             (df.low - df.close.shift(1)).abs()))
df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
p4 = pools.compute(df[["timestamp", "open", "high", "low", "close", "volume"]])
df["swL"] = p4.sweepBuy.values
df["swH"] = p4.sweepSell.values
df["strL"] = p4.strBuy.values
df["strH"] = p4.strSell.values
df["nearA"] = p4.nearAbove.values  # pool aktif terdekat di atas (TP long)
df["nearB"] = p4.nearBelow.values  # pool aktif terdekat di bawah (TP short)
df["xU"] = (df.dss.shift(1) <= df.trg.shift(1)) & (df.dss > df.trg) & (df.dss <= EXT_L)
df["xD"] = (df.dss.shift(1) >= df.trg.shift(1)) & (df.dss < df.trg) & (df.dss >= EXT_S)
# cross polos (tanpa filter ekstrem) untuk EXIT momentum lawan
df["xU_any"] = (df.dss.shift(1) <= df.trg.shift(1)) & (df.dss > df.trg)
df["xD_any"] = (df.dss.shift(1) >= df.trg.shift(1)) & (df.dss < df.trg)
# sweep dalam 3 bar terakhir (closed, termasuk bar ini)
df["swL_w"] = df.swL.rolling(SWEEP_LB).max().fillna(0).astype(bool)
df["swH_w"] = df.swH.rolling(SWEEP_LB).max().fillna(0).astype(bool)
# FVG 1H: exit runner saat gap searah terisi penuh + candle close.
# Bullish FVG: low[t] > high[t-2], zona [high[t-2], low[t]]; terisi saat close <= bawah.
# Bearish FVG: high[t] < low[t-2], zona [high[t], low[t-2]]; terisi saat close >= atas.
# Hanya gap lahir setelah entry & terisi max 14 hari (kausal, tanpa intip).
F1H = datpath(SYM, FVG_TF)
h1 = pd.read_csv(F1H, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
h1 = h1[(h1["timestamp"] >= START) & (h1["timestamp"] <= END)].reset_index(drop=True)
_h1o = h1.open.values
_h1h = h1.high.values
_h1l = h1.low.values
_h1c = h1.close.values
_h1t = h1.timestamp.values
FVG_MAX_AGE = np.timedelta64(14, "D")
FVG_MIN_ATR = 0.5  # saring gap: tinggi gap min 0.5xATR 1H (gap kecil = noise)
_tr1 = np.maximum(_h1h - _h1l, np.maximum(np.abs(_h1h - np.roll(_h1c, 1)), np.abs(_h1l - np.roll(_h1c, 1))))
_tr1[0] = _h1h[0] - _h1l[0]
_atr1 = pd.Series(_tr1).ewm(alpha=1 / 14, adjust=False).mean().values
_fillsBull = []  # (fill_ts, birth_ts) bullish gap terisi
_fillsBear = []
_n1 = len(h1)
for _k in range(2, _n1):
    _bt = _h1t[_k]
    if _h1l[_k] > _h1h[_k - 2] and (_h1l[_k] - _h1h[_k - 2]) >= FVG_MIN_ATR * _atr1[_k]:  # bullish gap besar
        _bot = _h1h[_k - 2]
        for _j in range(_k + 1, _n1):
            if _h1t[_j] - _bt > FVG_MAX_AGE:
                break
            if _h1c[_j] <= _bot:
                _fillsBull.append((_h1t[_j], _bt))
                break
    if _h1h[_k] < _h1l[_k - 2] and (_h1l[_k - 2] - _h1h[_k]) >= FVG_MIN_ATR * _atr1[_k]:  # bearish gap besar
        _top = _h1l[_k - 2]
        for _j in range(_k + 1, _n1):
            if _h1t[_j] - _bt > FVG_MAX_AGE:
                break
            if _h1c[_j] >= _top:
                _fillsBear.append((_h1t[_j], _bt))
                break
print(f"FVG {FVG_TF}: bull_fills={len(_fillsBull)} bear_fills={len(_fillsBear)}")
# strength pool terkuat dalam window sweep (untuk analisa kualitas + filter)
df["strL_w"] = df.strL.rolling(SWEEP_LB).max().fillna(0)
df["strS_w"] = df.strH.rolling(SWEEP_LB).max().fillna(0)
# ENTRY: ekstrem + sweep langsung, tanpa tunggu cross (cross sering ketinggalan)
# Filter strength>=40 (pool 2x sentuhan, lihat analisa: pool lemah 25-35 = -21.29)
MIN_STR = 40.0
IS_BTC = (SYM == "BTCUSDT")  # flat-meladai khusus BTC; alt pakai cross-ekstrem 20/80
FLAT_OS = float(os.environ.get("FLAT_OS", "15.0"))  # ketat (uji 20 gagal: x1.07/maxDD-48%)
FLAT_OB = float(os.environ.get("FLAT_OB", "85.0"))
FLAT_SLOPE = float(os.environ.get("FLAT_SLOPE", "2.0"))  # ketat (uji 3 gagal)
CX_OS, CX_OB = 20.0, 80.0  # cross ekstrem alt: long cross-up & DSS<=20 / short cross-down & DSS>=80
SL_LB = 4  # SL 1.5ATR wajib di luar range SL_LB bar terakhir, kalau di dalam = rawan sweep, skip
MOM_ON = os.environ.get("MOM_ON", "1") == "1"  # uji varian: MOM_ON=0 = tanpa exit momentum
FVG_ON = os.environ.get("FVG_ON", "1") == "1"  # FVG_ON=0 = tanpa exit FVG (runner MOM saja)
RUNNER = os.environ.get("RUNNER", "mom")  # mom = TP1+MOM+FVG; sweep = TP1+TP2(pool)+runner-hanya-sweep-lawan  # FVG_ON=0 = tanpa exit FVG (runner MOM saja)
LONG_ONLY = os.environ.get("LONG_ONLY", "0") == "1"  # LONG_ONLY=1 = spot: skip semua entry short
OUT_SUFFIX = os.environ.get("OUT_SUFFIX", "")
df["sigL"] = df.swL_w & (df.dss <= EXT_L) & (df.strL_w >= MIN_STR) & df.dirL & df.withBTC_L & (~df.cyc_block)
df["sigS"] = df.swH_w & (df.dss >= EXT_S) & (df.strS_w >= MIN_STR) & df.dirS & df.withBTC_S
# ENTRY: BTC = DSS melandai di 15/85 (tanpa sweep); ALT = cross di zona 20/80. Semua ikut bias 1D + tren BTC.
df["flatL"] = (df.dss <= FLAT_OS) & ((df.dss - df.dss.shift(2)).abs() < FLAT_SLOPE) & df.dirL & df.withBTC_L & (~df.cyc_block)
df["flatS"] = (df.dss >= FLAT_OB) & ((df.dss - df.dss.shift(2)).abs() < FLAT_SLOPE) & df.dirS & df.withBTC_S
df["cxL"] = (df.dss.shift(1) <= df.trg.shift(1)) & (df.dss > df.trg) & (df.dss <= CX_OS) & df.dirL & df.withBTC_L & (~df.cyc_block)
df["cxS"] = (df.dss.shift(1) >= df.trg.shift(1)) & (df.dss < df.trg) & (df.dss >= CX_OB) & df.dirS & df.withBTC_S
# geser 1 bar: sinyal dieksekusi di open bar berikut (anti-repaint, mirip barstate.isconfirmed)
df["sigL"] = df.sigL.shift(1).fillna(False)
df["sigS"] = df.sigS.shift(1).fillna(False)
df["flatL"] = df.flatL.shift(1).fillna(False)
df["flatS"] = df.flatS.shift(1).fillna(False)
df["cxL"] = df.cxL.shift(1).fillna(False)
df["cxS"] = df.cxS.shift(1).fillna(False)

print(f"sweepBuy={int(df.swL.sum())} sweepSell={int(df.swH.sum())} "
      f"sigL={int(df.sigL.sum())} sigS={int(df.sigS.sum())} "
      f"flatL={int(df.flatL.sum())} flatS={int(df.flatS.sum())} "
      f"cxL={int(df.cxL.sum())} cxS={int(df.cxS.sum())}")

ts = df.timestamp.values
o = df.open.values
c = df.close.values
h = df.high.values
lo = df.low.values
atr = df.atr.values
dssv = df.dss.values
trgv = df.trg.values
swRvL = df.swL.values
swRvH = df.swH.values
xUany = df.xU_any.values
xDany = df.xD_any.values
nearA = df.nearA.values
nearB = df.nearB.values
sigL = df.sigL.values
sigS = df.sigS.values
sigFL = df.flatL.values
sigFS = df.flatS.values
sigXL = df.cxL.values
sigXS = df.cxS.values
strLw = df.strL_w.values
strSw = df.strS_w.values
_fB = np.array([f[0] for f in _fillsBull]) if _fillsBull else np.array([], dtype="datetime64[ns]")
_fBb = np.array([f[1] for f in _fillsBull]) if _fillsBull else np.array([], dtype="datetime64[ns]")
_fR = np.array([f[0] for f in _fillsBear]) if _fillsBear else np.array([], dtype="datetime64[ns]")
_fRb = np.array([f[1] for f in _fillsBear]) if _fillsBear else np.array([], dtype="datetime64[ns]")
SESSI = (TF == "4h")  # sesi intraday 4H saja; 1D tanpa filter (STRATEGI.py SESSI=0) # skip Asia 07-15 WIB + open London 15 WIB + weekend (lihat STRATEGI.py:79-84)

eq = INIT_EQ
pos = 0
entry = sl = tp = 0.0
risk0 = 1e-9
ebar = -1
src = ""
entry_dss = 0.0
entry_str = 0.0
qty = 1.0  # sisa posisi (1.0 -> 0.75 setelah TP1 25%)
tp1done = False
tp2done = False
momPdone = False
fvgB_ptr = 0  # pointer fills bullish (exit long)
fvgR_ptr = 0  # pointer fills bearish (exit short)
fvgTrigL = False  # latch: gap searah long sudah terisi penuh sejak entry
fvgTrigS = False
mfe_r = 0.0  # max profit perjalanan dalam R
mae_r = 0.0  # max loss perjalanan dalam R
consec_sl = 0  # SL beruntun (MOM/TP memutus)
cool_until = np.datetime64("2000-01-01")
n_cool = 0  # berapa sinyal dilewati karena cooldown
trades = []
curve = []
for i in range(len(df)):
    # funding tiap bar 4H untuk posisi open (long bayar, short terima saat funding positif)
    if pos != 0:
        eq *= (1 - FUND_BAR * NOTIONAL * pos)
        # lacak MFE/MAE perjalanan (dalam R) pakai high/low bar ini
        if risk0 > 0:
            if pos == 1:
                mfe_r = max(mfe_r, (h[i] - entry) / risk0)
                mae_r = min(mae_r, (lo[i] - entry) / risk0)
            else:
                mfe_r = max(mfe_r, (entry - lo[i]) / risk0)
                mae_r = min(mae_r, (entry - h[i]) / risk0)
    if not np.isfinite(atr[i]) or atr[i] <= 0:
        curve.append(eq)
        continue
    if pos == 0:
        if CYCLE != "ALL":
            curve.append(eq)
            continue
        if bool(df.cash.values[i]):
            curve.append(eq)
            continue
        if ts[i] < cool_until:
            n_cool += int(bool(sigL[i] or sigS[i] or sigFL[i] or sigFS[i] or sigXL[i] or sigXS[i]))
            curve.append(eq)
            continue
        if SESSI:
            wib = pd.Timestamp(ts[i]) + pd.Timedelta(hours=7)
            if wib.dayofweek in (5, 6):
                curve.append(eq)
                continue
            if 7 <= wib.hour <= 15:
                curve.append(eq)
                continue
        if sigL[i]:
            entry = o[i] * (1 + SLIP)
            sl = lo[i - 1] - atr[i] * SL_ATR if i > 0 else entry - atr[i] * SL_ATR
            if sl >= entry:  # guard sisi salah
                sl = entry - atr[i] * SL_ATR
            risk0 = abs(entry - sl) or 1e-9
            _pool = nearA[i - 1] if i > 0 else float("nan")
            tp = _pool if (np.isfinite(_pool) and (_pool - entry) / entry * 100 >= MIN_TP_PCT) else entry + risk0 * TP_FALLBACK_R
            pos = 1
            ebar = i
            src = "sweep"
            entry_dss = float(dssv[i])
            entry_str = float(strLw[i - 1]) if i > 0 else float(strLw[i])
            qty = 1.0
            tp1done = False
            momPdone = False
            tp2done = False
            fvgTrigL = False
            fvgTrigS = False
            mfe_r = 0.0
            mae_r = 0.0
        elif IS_BTC and sigFL[i]:
            # entry BTC: DSS melandai — SL wajib di luar range SL_LB bar terakhir, else skip
            _sl = lo[i - 1] - atr[i] * SL_ATR if i > 0 else None
            _outside = bool(i >= SL_LB and _sl is not None and _sl < lo[i - SL_LB:i].min())
            if _sl is not None and _sl < o[i] * (1 + SLIP) and _outside:
                entry = o[i] * (1 + SLIP)
                sl = _sl
                risk0 = abs(entry - sl) or 1e-9
                _pool = nearA[i - 1] if i > 0 else float("nan")
                tp = _pool if (np.isfinite(_pool) and (_pool - entry) / entry * 100 >= MIN_TP_PCT) else entry + risk0 * TP_FALLBACK_R
                pos = 1
                ebar = i
                src = "flat"
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False
                momPdone = False
                tp2done = False
                fvgTrigL = False
                fvgTrigS = False
                mfe_r = 0.0
                mae_r = 0.0
        elif (not LONG_ONLY) and IS_BTC and sigFS[i]:
            _sl = h[i - 1] + atr[i] * SL_ATR if i > 0 else None
            _outside = bool(i >= SL_LB and _sl is not None and _sl > h[i - SL_LB:i].max())
            if _sl is not None and _sl > o[i] * (1 - SLIP) and _outside:
                entry = o[i] * (1 - SLIP)
                sl = _sl
                risk0 = abs(entry - sl) or 1e-9
                pos = -1
                ebar = i
                src = "flat"
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False
                tp2done = False
                momPdone = False
                fvgTrigL = False
                fvgTrigS = False
                mfe_r = 0.0
                mae_r = 0.0
        elif (not LONG_ONLY) and sigS[i]:
            entry = o[i] * (1 - SLIP)
            sl = h[i - 1] + atr[i] * SL_ATR if i > 0 else entry + atr[i] * SL_ATR
            if sl <= entry:
                sl = entry + atr[i] * SL_ATR
            risk0 = abs(entry - sl) or 1e-9
            pos = -1
            ebar = i
            src = "sweep"
            entry_dss = float(dssv[i])
            entry_str = float(strSw[i - 1]) if i > 0 else float(strSw[i])
            qty = 1.0
            tp1done = False
            tp2done = False
            momPdone = False
            fvgTrigL = False
            fvgTrigS = False
            mfe_r = 0.0
            mae_r = 0.0
        elif (not IS_BTC) and sigXL[i]:
            # entry ALT: cross-up di <=20 — SL wajib di luar range SL_LB bar, else skip
            _sl = lo[i - 1] - atr[i] * SL_ATR if i > 0 else None
            _outside = bool(i >= SL_LB and _sl is not None and _sl < lo[i - SL_LB:i].min())
            if _sl is not None and _sl < o[i] * (1 + SLIP) and _outside:
                entry = o[i] * (1 + SLIP)
                sl = _sl
                risk0 = abs(entry - sl) or 1e-9
                _pool = nearA[i - 1] if i > 0 else float("nan")
                tp = _pool if (np.isfinite(_pool) and (_pool - entry) / entry * 100 >= MIN_TP_PCT) else entry + risk0 * TP_FALLBACK_R
                pos = 1
                ebar = i
                src = "cross"
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False
                momPdone = False
                tp2done = False
                fvgTrigL = False
                fvgTrigS = False
                mfe_r = 0.0
                mae_r = 0.0
        elif (not LONG_ONLY) and (not IS_BTC) and sigXS[i]:
            _sl = h[i - 1] + atr[i] * SL_ATR if i > 0 else None
            _outside = bool(i >= SL_LB and _sl is not None and _sl > h[i - SL_LB:i].max())
            if _sl is not None and _sl > o[i] * (1 - SLIP) and _outside:
                entry = o[i] * (1 - SLIP)
                sl = _sl
                risk0 = abs(entry - sl) or 1e-9
                pos = -1
                ebar = i
                src = "cross"
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False
                tp2done = False
                momPdone = False
                fvgTrigL = False
                fvgTrigS = False
                mfe_r = 0.0
                mae_r = 0.0
    else:
        # majukan pointer fills FVG 1H + latch jika gap lahir-setelah-entry terisi
        _et = ts[ebar]
        while fvgB_ptr < len(_fB) and _fB[fvgB_ptr] <= ts[i]:
            if _fB[fvgB_ptr] > _et and _fBb[fvgB_ptr] > _et:
                fvgTrigL = True
            fvgB_ptr += 1
        while fvgR_ptr < len(_fR) and _fR[fvgR_ptr] <= ts[i]:
            if _fR[fvgR_ptr] > _et and _fRb[fvgR_ptr] > _et:
                fvgTrigS = True
            fvgR_ptr += 1
        wib_in = pd.Timestamp(ts[ebar]) + pd.Timedelta(hours=7)
        hold_bars = i - ebar
        hold_hours = hold_bars * TF_H
        base = (ts[ebar], ts[i], pos, entry, entry_dss, round(entry_str, 1), int(wib_in.dayofweek),
                int(wib_in.hour), hold_bars, hold_hours, round(mfe_r, 2), round(mae_r, 2), round(qty, 2), src)
        if pos == 1:
            # TP1 25% di +1.5R + SL ke BE (entry)
            if not tp1done and risk0 > 0 and (h[i] - entry) >= risk0 * TP1_R:
                x = entry + risk0 * TP1_R
                r = (x - entry) / entry
                eq *= (1 + r * NOTIONAL * TP1_QTY - 2 * FEE * NOTIONAL * TP1_QTY)
                trades.append(base + (x, "TP1", r * NOTIONAL * TP1_QTY * 100))
                qty -= TP1_QTY
                sl = entry
                tp1done = True
                consec_sl = 0
            if RUNNER == "sweep" and tp1done and not tp2done and risk0 > 0 and h[i] >= tp:
                x = tp
                r = (x - entry) / entry
                eq *= (1 + r * NOTIONAL * TP2_QTY - 2 * FEE * NOTIONAL * TP2_QTY)
                trades.append(base + (x, "TP2", r * NOTIONAL * TP2_QTY * 100))
                qty -= TP2_QTY
                tp2done = True
                consec_sl = 0
            if lo[i] <= sl:
                r = (sl - entry) / entry
                eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                trades.append(base + (sl, "SL-BE" if (tp1done or momPdone) else "SL", r * NOTIONAL * qty * 100))
                pos = 0
                if not (tp1done or momPdone):
                    consec_sl += 1
                    if consec_sl >= 3:
                        cool_until = ts[i] + np.timedelta64(COOL_H, "h")
                        consec_sl = 0
                else:
                    consec_sl = 0
            elif RUNNER == "mom" and MOM_ON and hold_bars >= 1 and (bool(xDany[i]) or bool(swRvH[i])):
                # MOM saat profit (+1R): parsial 50% + kunci SL +1R, runner lanjut (sekali saja)
                # MOM saat belum profit: full exit seperti sebelumnya
                x = c[i] * (1 - SLIP)
                r = (x - entry) / entry
                mt = "+".join([s for s, f in (("X", bool(xDany[i])), ("SWP", bool(swRvH[i]))) if f])
                if mfe_r >= 1.0 and not momPdone:
                    pq = qty * 0.5
                    eq *= (1 + r * NOTIONAL * pq - 2 * FEE * NOTIONAL * pq)
                    trades.append(base + (x, "MOM-P:" + mt, r * NOTIONAL * pq * 100))
                    qty -= pq
                    sl = entry + risk0
                    momPdone = True
                    consec_sl = 0
                else:
                    eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                    trades.append(base + (x, "MOM:" + mt, r * NOTIONAL * qty * 100))
                    pos = 0
                    consec_sl = 0
            elif RUNNER == "mom" and FVG_ON and hold_bars >= 1 and fvgTrigL:
                # FVG saat profit: parsial 50% + kunci +1R (sekali saja), else full exit
                x = c[i] * (1 - SLIP)
                r = (x - entry) / entry
                if mfe_r >= 1.0 and not momPdone:
                    pq = qty * 0.5
                    eq *= (1 + r * NOTIONAL * pq - 2 * FEE * NOTIONAL * pq)
                    trades.append(base + (x, "MOM-P:FVG", r * NOTIONAL * pq * 100))
                    qty -= pq
                    sl = entry + risk0
                    momPdone = True
                    consec_sl = 0
                else:
                    eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                    trades.append(base + (x, "FVG", r * NOTIONAL * qty * 100))
                    pos = 0
                    consec_sl = 0
            elif RUNNER == "sweep" and hold_bars >= 1 and bool(swRvH[i]):
                # runner spot: sweep-lawan -> parsial 50% + kunci +1R jika profit, else full
                x = c[i] * (1 - SLIP)
                r = (x - entry) / entry
                if mfe_r >= 1.0 and not momPdone:
                    pq = qty * 0.5
                    eq *= (1 + r * NOTIONAL * pq - 2 * FEE * NOTIONAL * pq)
                    trades.append(base + (x, "MOM-P:SWP", r * NOTIONAL * pq * 100))
                    qty -= pq
                    sl = entry + risk0
                    momPdone = True
                    consec_sl = 0
                else:
                    eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                    trades.append(base + (x, "MOM:SWP", r * NOTIONAL * qty * 100))
                    pos = 0
                    consec_sl = 0
        else:
            # TP1 25% di +1.5R + SL ke BE (entry)
            if not tp1done and risk0 > 0 and (entry - lo[i]) >= risk0 * TP1_R:
                x = entry - risk0 * TP1_R
                r = (entry - x) / entry
                eq *= (1 + r * NOTIONAL * TP1_QTY - 2 * FEE * NOTIONAL * TP1_QTY)
                trades.append(base + (x, "TP1", r * NOTIONAL * TP1_QTY * 100))
                qty -= TP1_QTY
                sl = entry
                tp1done = True
                consec_sl = 0
            if h[i] >= sl:
                r = (entry - sl) / entry
                eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                trades.append(base + (sl, "SL-BE" if tp1done else "SL", r * NOTIONAL * qty * 100))
                pos = 0
                if not tp1done:
                    consec_sl += 1
                    if consec_sl >= 3:
                        cool_until = ts[i] + np.timedelta64(COOL_H, "h")
                        consec_sl = 0
                else:
                    consec_sl = 0
            elif MOM_ON and hold_bars >= 1 and (bool(xUany[i]) or bool(swRvL[i])):
                # runner: momentum lawan 4H cross-up / sweepBuy -> tutup sisa di close
                x = c[i] * (1 + SLIP)
                r = (entry - x) / entry
                eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                mt = "+".join([s for s, f in (("X", bool(xUany[i])), ("SWP", bool(swRvL[i]))) if f])
                trades.append(base + (x, "MOM:" + mt, r * NOTIONAL * qty * 100))
                pos = 0
                consec_sl = 0
            elif FVG_ON and hold_bars >= 1 and fvgTrigS:
                # runner: FVG-1H bearish pendukung terisi penuh + close -> tutup sisa di close
                x = c[i] * (1 + SLIP)
                r = (entry - x) / entry
                eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                trades.append(base + (x, "FVG", r * NOTIONAL * qty * 100))
                pos = 0
                consec_sl = 0
        if eq <= 0:
            break
    curve.append(eq)

outdir = os.path.join(HERE, "results")
os.makedirs(outdir, exist_ok=True)
tr = pd.DataFrame(trades, columns=["entry_time", "exit_time", "side", "entry", "entry_dss", "entry_str",
                                  "in_dow", "in_hr_wib", "hold_bars", "hold_hours",
                                  "mfe_r", "mae_r", "qty", "src", "exit", "reason", "ret_eq"])
tr.to_csv(os.path.join(outdir, f"trades_DSSLP_{SYM}_{TF}{OUT_SUFFIX}.csv"), index=False)
pd.DataFrame({"timestamp": df.timestamp[:len(curve)], "equity": curve}).to_csv(
    os.path.join(outdir, f"equity_DSSLP_{SYM}_{TF}{OUT_SUFFIX}.csv"), index=False)
dd = (pd.Series(curve) / pd.Series(curve).cummax() - 1).min() * 100 if curve else 0
wr = (tr.ret_eq > 0).mean() * 100 if len(tr) else 0
print(f"[DSSLP-{SYM}-{TF}] trades={len(tr)} equity={eq:.2f} (x{eq / INIT_EQ:.2f}) "
      f"winrate={wr:.1f}% maxDD={dd:.2f}% cooldown_skip={n_cool}")
if len(tr):
    print(tr.reason.value_counts().to_dict())
