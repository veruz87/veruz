import pandas as pd
import glob
import os
rows = {}
for f in sorted(glob.glob("results/equity_DSSLP_*_pf_*.csv")):
    tag = os.path.basename(f).replace("equity_DSSLP_", "").replace(".csv", "")
    d = pd.read_csv(f, parse_dates=["timestamp"]).set_index("timestamp")["equity"]
    y = d.resample("YE").last()
    r = (y.pct_change().fillna(y / d.iloc[0] - 1)) * 100
    rows[tag] = r.round(1)
out = pd.DataFrame(rows).T
out.columns = [str(c)[:4] for c in out.columns]
print(out.to_string())
