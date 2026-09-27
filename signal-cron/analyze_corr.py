import pandas as pd

def positions(sym, tf="4h"):
    tr = pd.read_csv(f"results/trades_DSSLP_{sym}_{tf}.csv", parse_dates=["entry_time", "exit_time"])
    g = tr.groupby(["entry_time", "side"], as_index=False).agg(
        exit_time=("exit_time", "max"), ret_eq=("ret_eq", "sum"))
    return g

btc = positions("BTCUSDT")
print("=== Alt SHORT rugi saat BTC LONG terbuka ===")
for sym in ["ETHUSDT", "SOLUSDT", "ZECUSDT"]:
    alt = positions(sym)
    lose_short = alt[(alt.side == -1) & (alt.ret_eq < 0)]
    n_clash, clash_loss = 0, 0.0
    btc_long_win_overlap = 0
    for _, a in lose_short.iterrows():
        ov = btc[(btc.side == 1) & (btc.entry_time <= a.exit_time) & (btc.exit_time >= a.entry_time)]
        if len(ov):
            n_clash += 1
            clash_loss += a.ret_eq
            if (ov.ret_eq > 0).any():
                btc_long_win_overlap += 1
    print(f"{sym}: short-rugi total {len(lose_short)} (sum {lose_short.ret_eq.sum():+.2f}) | "
          f"tabrakan BTC-long {n_clash} (sum {clash_loss:+.2f}, {btc_long_win_overlap}x BTC-long-nya profit)")
