import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv", parse_dates=["entry_time", "exit_time"])
print(tr.groupby("reason")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("MOM positive:", int((tr[tr.reason == "MOM"].ret_eq > 0).sum()), "dari", int((tr.reason == "MOM").sum()))
print("hold_hours max per reason:")
print(tr.groupby("reason")["hold_hours"].max().to_string())
print("hold>168h total:", int((tr.hold_hours > 168).sum()))
