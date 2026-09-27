import io
p = "dss_liquidity.py"
s = io.open(p, encoding="utf-8").read()
subs = [
    ('F1H = os.path.join(OLD, f"{SYM}_1h.csv")', 'F1H = os.path.join(OLD, f"{SYM}_{FVG_TF}.csv")'),
    ('SESSI = True  # skip Asia', 'SESSI = (TF == "4h")  # sesi intraday 4H saja; 1D tanpa filter (STRATEGI.py SESSI=0) # skip Asia'),
    ("FUND_4H * NOTIONAL", "FUND_BAR * NOTIONAL"),
    ("hold_hours = hold_bars * 4", "hold_hours = hold_bars * TF_H"),
    ('np.timedelta64(48, "h")', 'np.timedelta64(COOL_H, "h")'),
    ('f"trades_DSSLP_{SYM}_4h{OUT_SUFFIX}.csv"', 'f"trades_DSSLP_{SYM}_{TF}{OUT_SUFFIX}.csv"'),
    ('f"equity_DSSLP_{SYM}_4h{OUT_SUFFIX}.csv"', 'f"equity_DSSLP_{SYM}_{TF}{OUT_SUFFIX}.csv"'),
    ("[DSSLP-{SYM}]", "[DSSLP-{SYM}-{TF}]"),
]
for a, b in subs:
    assert a in s, a
    s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
