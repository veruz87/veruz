import pandas as pd
for sym in ["SOLUSDT", "ETHUSDT", "ZECUSDT"]:
    tr = pd.read_csv(f"results/trades_DSSLP_{sym}_4h.csv")
    sl = tr[tr.reason == "SL"]
    mom = tr[tr.reason.str.startswith("MOM")]
    print(f"=== {sym} ===")
    print(f"SL {len(sl)}: mfe>=1 (sempat profit, gagal exit): {int((sl.mfe_r >= 1).sum())} | mfe<0.3 (langsung salah): {int((sl.mfe_r < 0.3).sum())}")
    print(f"MOM {len(mom)}: mean {mom.ret_eq.mean():+.3f} | MOM:SWP mean: {mom[mom.reason == 'MOM:SWP'].ret_eq.mean():+.3f}")
    print(f"hold SL median: {sl.hold_hours.median()}h | MOM median: {mom.hold_hours.median()}h")
