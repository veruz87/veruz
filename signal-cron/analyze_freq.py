import pandas as pd
import glob
import os

for f in sorted(glob.glob("results/trades_DSSLP_*_spw_*.csv")):
    tag = os.path.basename(f).replace("trades_DSSLP_", "").replace(".csv", "")
    tr = pd.read_csv(f, parse_dates=["entry_time", "exit_time"])
    pos = tr.groupby(["entry_time", "side"]).agg(n=("exit_time", "count")).reset_index()
    npos = len(pos)
    months = (tr.exit_time.max() - tr.exit_time.min()).days / 30.44
    years = (tr.exit_time.max() - tr.exit_time.min()).days / 365.25
    print(f"{tag}: posisi={npos} | per bulan={npos / months:.1f} | per tahun={npos / years:.1f}")
