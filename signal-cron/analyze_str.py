import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv")
print("=== PER BUCKET STRENGTH ===")
tr["bucket"] = pd.cut(tr.entry_str, [0, 25, 35, 40, 50, 100])
print(tr.groupby("bucket", observed=True)["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print()
print("=== LEMAH (<40) vs KUAT (>=40) ===")
lemah = tr[tr.entry_str < 40]
kuat = tr[tr.entry_str >= 40]
for nm, d in (("lemah<40", lemah), ("kuat>=40", kuat)):
    print(nm, "n=", len(d), "win%=", round((d.ret_eq > 0).mean() * 100, 1),
          "sum=", round(d.ret_eq.sum(), 2), "SL=", int((d.reason == "SL").sum()))
print()
print("=== LEMAH: per reason ===")
print(lemah.groupby("reason")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== KUAT: per reason ===")
print(kuat.groupby("reason")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
