import pandas as pd

btc = pd.read_csv("../scalp-backtest/BTCUSDT_4h.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
px = btc.set_index("timestamp")["close"]

print("=== Alt SHORT rugi: BTC naik selama posisi (melawan tren BTC)? ===")
for sym in ["ETHUSDT", "SOLUSDT", "ZECUSDT"]:
    tr = pd.read_csv(f"results/trades_DSSLP_{sym}_4h.csv", parse_dates=["entry_time", "exit_time"])
    g = tr.groupby(["entry_time", "side"], as_index=False).agg(exit_time=("exit_time", "max"), ret_eq=("ret_eq", "sum"))
    lose_short = g[(g.side == -1) & (g.ret_eq < 0)]
    vs_btc = 0
    for _, a in lose_short.iterrows():
        try:
            c0 = px.loc[a.entry_time]
            c1 = px.loc[a.exit_time]
            if c1 > c0:
                vs_btc += 1
        except KeyError:
            pass
    print(f"{sym}: short-rugi {len(lose_short)} | BTC naik selama posisi: {vs_btc} ({vs_btc / max(1, len(lose_short)) * 100:.0f}%)")
