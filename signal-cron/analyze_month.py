import pandas as pd
import glob
import os

allp = []
for f in sorted(glob.glob("results/trades_DSSLP_*_spw_*.csv")):
    tr = pd.read_csv(f, parse_dates=["entry_time", "exit_time"])
    pos = tr.groupby(["entry_time", "side"]).size().reset_index()[["entry_time"]]
    pos["coin"] = os.path.basename(f).split("_pf_")[0].replace("trades_DSSLP_", "")
    allp.append(pos)
p = pd.concat(allp)
p["bln"] = p.entry_time.dt.to_period("M")
m = p.groupby("bln").size()
print("total posisi:", len(p))
print("rata2 per bulan:", round(len(p) / len(m), 1))
print("bulan tersepi:", m.min(), "| tersibuk:", m.max())
print()
print("=== per bulan kalender (akumulasi 2021-2025) ===")
p["mm"] = p.entry_time.dt.month
print(p.groupby("mm").size().to_string())
