import pandas as pd
import numpy as np

DATA = "C:/Users/RANGGA/Documents/Default Project/data-backtest"
SYM = "BTCUSDT"
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h_spw_BTC_4h.csv", parse_dates=["entry_time", "exit_time"])
df = pd.read_csv(f"{DATA}/{SYM}/{SYM}_4h.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
tr1 = np.maximum(df.high - df.low, np.maximum((df.high - df.close.shift(1)).abs(), (df.low - df.close.shift(1)).abs()))
df["atr"] = tr1.ewm(alpha=1 / 14, adjust=False).mean()
tsidx = {t: i for i, t in enumerate(df.timestamp)}

print("MOM/SL exit: berapa R maksimal 12 bar SETELAH exit (peluang runner yang kepotong)?")
rows = []
for _, t in tr.iterrows():
    if not str(t.reason).startswith("MOM") and t.reason != "SL":
        continue
    e = tsidx.get(t.entry_time)
    x = tsidx.get(t.exit_time)
    if e is None or x is None or e == 0:
        continue
    sl = df.low[e - 1] - df.atr[e] * 1.5
    risk = abs(t.entry - sl)
    if risk <= 0:
        continue
    post = 0.0
    for j in range(x, min(x + 12, len(df))):
        post = max(post, (df.high[j] - t.entry) / risk)
    rows.append((t.reason, t.ret_eq, round(post, 2)))
r = pd.DataFrame(rows, columns=["reason", "ret", "postR"])
print(f"n={len(r)} | exit dgn postR>=1.5 (kepotong runner): {int((r.postR >= 1.5).sum())} ({(r.postR >= 1.5).mean() * 100:.0f}%)")
print(f"postR>=2.5: {int((r.postR >= 2.5).sum())} | postR<0.5 (exit tepat, tidak ada lanjutan): {int((r.postR < 0.5).sum())}")
print(r.groupby("reason")["postR"].agg(["count", "median", "mean", "max"]).round(2).to_string())
