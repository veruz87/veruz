import pandas as pd
import numpy as np

SYM = "BTCUSDT"
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv", parse_dates=["entry_time", "exit_time"])
df = pd.read_csv(f"../scalp-backtest/{SYM}_4h.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
tr1 = np.maximum(df.high - df.low, np.maximum((df.high - df.close.shift(1)).abs(), (df.low - df.close.shift(1)).abs()))
df["atr"] = tr1.ewm(alpha=1 / 14, adjust=False).mean()
tsidx = {t: i for i, t in enumerate(df.timestamp)}

print("FVG exit: lanjutkan 7 hari ke depan, kena SL dulu atau +1.5R dulu?")
for _, t in tr[tr.reason == "FVG"].iterrows():
    e = tsidx[t.entry_time]
    x = tsidx[t.exit_time]
    sl = df.low[e - 1] - df.atr[e] * 1.5 if t.side == 1 else df.high[e - 1] + df.atr[e] * 1.5
    risk = abs(t.entry - sl)
    res = "netral"
    for j in range(x, min(x + 42, len(df))):
        if t.side == 1:
            if df.low[j] <= sl:
                res = "SL-valid"
                break
            if df.high[j] >= t.entry + risk * 1.5:
                res = "NOISE-tp15"
                break
        else:
            if df.high[j] >= sl:
                res = "SL-valid"
                break
            if df.low[j] <= t.entry - risk * 1.5:
                res = "NOISE-tp15"
                break
    print(f"{t.entry_time.date()} {'L' if t.side == 1 else 'S'} ret={t.ret_eq:+.2f}% -> {res}")
