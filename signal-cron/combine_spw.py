import pandas as pd
import glob
import os

sleeves = []
for f in sorted(glob.glob("results/equity_DSSLP_*_spw_*.csv")):
    tag = os.path.basename(f).replace("equity_DSSLP_", "").replace(".csv", "")
    d = pd.read_csv(f, parse_dates=["timestamp"])
    d = d.set_index("timestamp")["equity"]
    sleeves.append((tag, d))
    print(tag, "n=", len(d), "x=", round(d.iloc[-1] / d.iloc[0], 3))

px = pd.concat([s for _, s in sleeves], axis=1)
px.columns = [t for t, _ in sleeves]
init = {t: s.iloc[0] for t, s in sleeves}
px = px.ffill().fillna(value=init)
px["TOTAL"] = px.sum(axis=1)
tot = px["TOTAL"]
print("INIT", round(tot.iloc[0], 2), "FINAL", round(tot.iloc[-1], 2), "x", round(tot.iloc[-1] / tot.iloc[0], 3))
peak = tot.cummax()
print("maxDD", round(((tot - peak) / peak * 100).min(), 2), "%")
yr = tot.resample("YE").last()
print("per tahun:")
print(((yr.pct_change().fillna(yr / tot.iloc[0] - 1)) * 100).round(1).to_string())
px[["TOTAL"]].to_csv("results/equity_SPOTW.csv")
