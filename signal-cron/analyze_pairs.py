import pandas as pd
for sym in ["ETHUSDT", "SOLUSDT", "ZECUSDT", "HYPEUSDT"]:
    tr = pd.read_csv(f"results/trades_DSSLP_{sym}_4h.csv")
    tr["src"] = tr.entry_str.apply(lambda s: "sweep" if s >= 40 else ("flat" if s == 0 else "sweep-weak"))
    g = tr.groupby("src")["ret_eq"].agg(["count", "mean", "sum"]).round(2)
    print(f"=== {sym} ===")
    print(g.to_string())
    print("SL per src:", tr[tr.reason == "SL"].groupby("src").size().to_dict())
