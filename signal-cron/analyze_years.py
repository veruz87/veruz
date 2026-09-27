import pandas as pd
for sym in ["SOLUSDT", "ETHUSDT", "ZECUSDT"]:
    tr = pd.read_csv(f"results/trades_DSSLP_{sym}_4h.csv", parse_dates=["entry_time", "exit_time"])
    tr["y"] = tr.exit_time.dt.year
    print(f"=== {sym} 4H per tahun ===")
    print(tr.groupby("y")["ret_eq"].agg(["count", "mean", "sum"]).round(2).to_string())
