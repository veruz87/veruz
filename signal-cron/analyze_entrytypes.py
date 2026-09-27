import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h_spc_BTC_4h.csv", parse_dates=["entry_time", "exit_time"])
pos = tr.groupby(["entry_time", "side"], as_index=False).agg(
    nrow=("exit_time", "count"), mfe=("mfe_r", "max"), ret=("ret_eq", "sum"),
    estr=("entry_str", "first"), edss=("entry_dss", "first"))


def typ(r):
    if r.estr >= 40:
        return "sweep"
    if r.edss <= 15 or r.edss >= 85:
        return "flat"
    return "cross?"


pos["type"] = pos.apply(typ, axis=1)
g = pos.groupby("type").agg(n=("nrow", "count"), win=("ret", lambda s: round((s > 0).mean() * 100, 1)),
                            avgR=("ret", "mean"), mfe_med=("mfe", "median"), mfe_max=("mfe", "max"),
                            tp1rate=("nrow", lambda s: ""))
print(g.round(3).to_string())
print()
print("TP1 per tipe:")
print(tr[tr.reason == "TP1"].groupby(tr[tr.reason == "TP1"].entry_time.map(
    dict(zip(pos.entry_time.astype(str), pos.type))))["ret_eq"].count().to_string() if False else "")
tp1pos = set(tr[tr.reason == "TP1"].entry_time.astype(str))
pos["tp1"] = pos.entry_time.astype(str).isin(tp1pos)
print(pos.groupby("type")["tp1"].agg(["sum", "mean"]).round(3).to_string())
print()
print("SL rate per tipe:")
slpos = set(tr[tr.reason == "SL"].entry_time.astype(str))
pos["sl"] = pos.entry_time.astype(str).isin(slpos)
print(pos.groupby("type")["sl"].agg(["sum", "mean"]).round(3).to_string())
