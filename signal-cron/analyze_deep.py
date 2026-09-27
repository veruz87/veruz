import pandas as pd
import numpy as np

DATA = "C:/Users/RANGGA/Documents/Default Project/data-backtest"
SYM = "BTCUSDT"
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h_spw_BTC_4h.csv", parse_dates=["entry_time", "exit_time"])
df = pd.read_csv(f"{DATA}/{SYM}/{SYM}_4h.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
tr1 = np.maximum(df.high - df.low, np.maximum((df.high - df.close.shift(1)).abs(), (df.low - df.close.shift(1)).abs()))
df["atr"] = tr1.ewm(alpha=1 / 14, adjust=False).mean()
tsidx = {t: i for i, t in enumerate(df.timestamp)}

print("=== 1) SL kena: lanjut turun atau sentuh-lalu-naik? (12 bar setelah exit) ===")
sl = tr[tr.reason == "SL"]
hunt, cont, mid = 0, 0, 0
drops = []
for _, t in sl.iterrows():
    e, x = tsidx.get(t.entry_time), tsidx.get(t.exit_time)
    if e is None or x is None or e == 0:
        continue
    slpx = df.low[e - 1] - df.atr[e] * 1.5
    risk = abs(t.entry - slpx)
    fwd = df.iloc[x:min(x + 12, len(df))]
    post_min = ((fwd.low - t.entry) / risk).min()  # sedalam apa lanjut turun (R)
    post_max = ((fwd.high - t.entry) / risk).max()  # setinggi apa pulih (R)
    drops.append(post_min)
    if post_max >= 1.0:
        hunt += 1  # sentuh SL lalu pulih +1R = stop-hunt
    elif post_min <= -2.0:
        cont += 1  # lanjut turun >=2R = stop tepat
    else:
        mid += 1
drops = pd.Series(drops)
print(f"SL total {len(sl)}: hunted (pulih +1R)={hunt} | tepat (lanjut -2R)={cont} | tengah2={mid}")
print(f"penetrasi melewati SL: median {drops.median():.2f}R, mean {drops.mean():.2f}R "
      f"(misal -1.5 = 0.5R di bawah SL)")
print(f"SL jebol dalam (>0.5R lewat SL): {int((drops < -1.5).sum())} dari {len(drops)}")

print()
print("=== 2) MOM exit saat sudah profit (mfe>=1): seberapa dalam jatuhnya setelah exit? ===")
mom = tr[(tr.reason.str.startswith("MOM")) & (tr.mfe_r >= 1.0)]
falls = []
saved = 0
for _, t in mom.iterrows():
    e, x = tsidx.get(t.entry_time), tsidx.get(t.exit_time)
    if e is None or x is None or e == 0:
        continue
    slpx = df.low[e - 1] - df.atr[e] * 1.5
    risk = abs(t.entry - slpx)
    fwd = df.iloc[x:min(x + 12, len(df))]
    post_min = ((fwd.low - t.entry) / risk).min()
    falls.append(post_min)
    if post_min <= -1.0:
        saved += 1  # jatuh >=1R setelah exit = exit menyelamatkan
falls = pd.Series(falls)
print(f"MOM-profit total {len(mom)}: jatuh >=1R setelah exit (exit tepat)={saved} | tidak jatuh={len(mom) - saved}")
print(f"kedalaman jatuh: median {falls.median():.2f}R, terburuk {falls.min():.2f}R")
