import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h_src_BTC_4h.csv", parse_dates=["entry_time", "exit_time"])
pos = tr.groupby(["entry_time", "side"], as_index=False).agg(
    nrow=("exit_time", "count"), mfe=("mfe_r", "max"), ret=("ret_eq", "sum"),
    src=("src", "first"), edss=("entry_dss", "first"))
print(pos.groupby("src").agg(n=("nrow", "count"),
                             win=("ret", lambda s: round((s > 0).mean() * 100, 1)),
                             avgR=("ret", "mean"),
                             mfe_med=("mfe", "median"),
                             mfe_max=("mfe", "max")).round(3).to_string())
print()
tp1 = set(tr[tr.reason == "TP1"].entry_time.astype(str))
sl = set(tr[tr.reason == "SL"].entry_time.astype(str))
pos["tp1"] = pos.entry_time.astype(str).isin(tp1)
pos["sl"] = pos.entry_time.astype(str).isin(sl)
print("TP1 rate:"); print(pos.groupby("src")["tp1"].agg(["sum", "mean"]).round(3).to_string())
print("SL rate:"); print(pos.groupby("src")["sl"].agg(["sum", "mean"]).round(3).to_string())
