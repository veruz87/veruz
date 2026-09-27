import pandas as pd
import numpy as np

b = pd.read_csv("C:/Users/RANGGA/Documents/Default Project/data-backtest/BTCUSDT/BTCUSDT_1d.csv",
                parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
L = R = 10
w = L + R + 1
wmin = b.low.rolling(w).min().values
lv = b.low.values
pl = [lv[j] if (j - R >= 0 and lv[j - R] == wmin[j]) else np.nan for j in range(len(b))]
b["pivLow"] = pl
lows = b.dropna(subset=["pivLow"])[["timestamp", "pivLow"]].reset_index(drop=True)
lows["gap"] = lows.timestamp.diff().dt.days
print("=== swing low 1D (pivot 10) -> jarak low-to-low ===")
print(lows.tail(15).to_string(index=False))
print()
print("median gap:", lows.gap.median(), "| mean:", round(lows.gap.mean(), 1))
print("gap 45-75 hari (DCL 54-66 + toleransi):", int(((lows.gap >= 45) & (lows.gap <= 75)).sum()), "dari", len(lows) - 1)
print("gap 95-115 hari (klaim 106 chart):", int(((lows.gap >= 95) & (lows.gap <= 115)).sum()))
print()
print("=== low terendah per tahun (cek 4YCL) ===")
b["y"] = b.timestamp.dt.year
print(b.groupby("y").agg(tgl=("timestamp", lambda s: s.iloc[s.sub(s.min()).idxmin()] if False else s.min()), low=("low", "min")).to_string() if False else "")
ann = b.groupby("y").apply(lambda d: d.loc[d.low.idxmin(), ["timestamp", "low"]], include_groups=False)
print(ann.to_string())
