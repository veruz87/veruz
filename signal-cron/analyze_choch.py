import pandas as pd
import numpy as np

SYM = "BTCUSDT"
tr = pd.read_csv(f"results/trades_DSSLP_{SYM}_4h.csv", parse_dates=["entry_time", "exit_time"])
m15 = pd.read_csv(f"../scalp-backtest/{SYM}_15m.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

PIV15 = 5
L = R = PIV15
h, l = m15["high"], m15["low"]
w = L + R + 1
wm = h.rolling(w).max()
wn = l.rolling(w).min()
ph = np.where(h.shift(R) == wm, h.shift(R), np.nan)
pl = np.where(l.shift(R) == wn, l.shift(R), np.nan)
m15["lPH"] = pd.Series(ph, index=m15.index).ffill()
m15["lPL"] = pd.Series(pl, index=m15.index).ffill()
m15["chochU"] = (m15.close > m15.lPH).shift(1).fillna(False)
m15["chochD"] = (m15.close < m15.lPL).shift(1).fillna(False)
m15 = m15[["timestamp", "chochU", "chochD"]]

mx = tr[tr.reason.str.startswith("MOM:X", na=False)].copy()
print("MOM:X total:", len(mx))
rows = []
for _, t in mx.iterrows():
    side = t.side
    win = m15[(m15.timestamp > t.entry_time) & (m15.timestamp <= t.exit_time)]
    if side == 1:  # long exit cross-down -> cari chochD
        hit = bool(win.chochD.any()) if len(win) else False
    else:
        hit = bool(win.chochU.any()) if len(win) else False
    rows.append(hit)
mx["choch_ok"] = rows
print("ada CHoCH 15M searah sebelum exit:", int(mx.choch_ok.sum()), f"({mx.choch_ok.mean() * 100:.1f}%)")
print(mx.groupby(["side", "choch_ok"])["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("MOM:X tanpa CHoCH berarti cross 4H jalan sendiri tanpa konfirmasi 15M.")
