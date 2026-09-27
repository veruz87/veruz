import io
p = "dss_liquidity.py"
s = io.open(p, encoding="utf-8").read()
subs = [
    ('F4 = os.path.join(OLD, f"{SYM}_{TF}.csv")', "F4 = datpath(SYM, TF)"),
    ('F1H = os.path.join(OLD, f"{SYM}_{FVG_TF}.csv")', "F1H = datpath(SYM, FVG_TF)"),
    ('_b = pd.read_csv(os.path.join(OLD, "BTCUSDT_1d.csv")', '_b = pd.read_csv(datpath("BTCUSDT", "1d")'),
    ('d1 = pd.read_csv(os.path.join(OLD, f"{SYM}_1d.csv")', 'd1 = pd.read_csv(datpath(SYM, "1d")'),
    ("elif IS_BTC and sigFS[i]:", "elif (not LONG_ONLY) and IS_BTC and sigFS[i]:"),
    ("elif sigS[i]:", "elif (not LONG_ONLY) and sigS[i]:"),
    ("elif (not IS_BTC) and sigXS[i]:", "elif (not LONG_ONLY) and (not IS_BTC) and sigXS[i]:"),
]
for a, b in subs:
    assert a in s, a
    s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
