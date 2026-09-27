import io
p = "dss_spot.py"
s = io.open(p, encoding="utf-8").read()

# 1) flag mode runner
a = 'FVG_ON = os.environ.get("FVG_ON", "1") == "1"'
assert a in s
s = s.replace(a, a + '  # FVG_ON=0 = tanpa exit FVG (runner MOM saja)\nRUNNER = os.environ.get("RUNNER", "mom")  # mom = TP1+MOM+FVG; sweep = TP1+TP2(pool)+runner-hanya-sweep-lawan')

# 2) TP pool dihitung lagi saat entry long (untuk TP2)
old_sigL = """            risk0 = abs(entry - sl) or 1e-9
            pos = 1
            ebar = i
            entry_dss = float(dssv[i])
            entry_str = float(strLw[i - 1]) if i > 0 else float(strLw[i])
            qty = 1.0
            tp1done = False"""
assert old_sigL in s
s = s.replace(old_sigL, """            risk0 = abs(entry - sl) or 1e-9
            _pool = nearA[i - 1] if i > 0 else float("nan")
            tp = _pool if (np.isfinite(_pool) and (_pool - entry) / entry * 100 >= MIN_TP_PCT) else entry + risk0 * TP_FALLBACK_R
            pos = 1
            ebar = i
            entry_dss = float(dssv[i])
            entry_str = float(strLw[i - 1]) if i > 0 else float(strLw[i])
            qty = 1.0
            tp1done = False
            tp2done = False""")

# 3) TP2 + runner-sweep-only untuk sisi long: bungkus exit MOM:X & FVG
old_momx = "            elif MOM_ON and hold_bars >= 1 and (bool(xDany[i]) or bool(swRvH[i])):"
assert old_momx in s
s = s.replace(old_momx, """            elif RUNNER == "mom" and MOM_ON and hold_bars >= 1 and (bool(xDany[i]) or bool(swRvH[i])):""")
old_fvg = "            elif FVG_ON and hold_bars >= 1 and fvgTrigL:"
assert old_fvg in s
s = s.replace(old_fvg, """            elif RUNNER == "mom" and FVG_ON and hold_bars >= 1 and fvgTrigL:""")

io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
