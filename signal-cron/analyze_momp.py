import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h_spm_BTC_4h.csv", parse_dates=["entry_time", "exit_time"])
for et, g in tr.groupby("entry_time"):
    if (g.mfe_r >= 1.0).any() and g.reason.str.startswith("MOM-P").any() == False and (g.reason.str.startswith("MOM") & (g.mfe_r >= 1.0)).any():
        print("---", et, "---")
        print(g[["exit_time", "reason", "mfe_r", "qty", "ret_eq"]].to_string(index=False))
