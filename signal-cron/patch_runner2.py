import io
p = "dss_spot.py"
s = io.open(p, encoding="utf-8").read()

# tp + tp2done di cabang flat-long & cross-long (sigL sudah dari patch sebelumnya)
old_flat = """                risk0 = abs(entry - sl) or 1e-9
                pos = 1
                ebar = i
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False"""
assert s.count(old_flat) == 2, s.count(old_flat)
s = s.replace(old_flat, """                risk0 = abs(entry - sl) or 1e-9
                _pool = nearA[i - 1] if i > 0 else float("nan")
                tp = _pool if (np.isfinite(_pool) and (_pool - entry) / entry * 100 >= MIN_TP_PCT) else entry + risk0 * TP_FALLBACK_R
                pos = 1
                ebar = i
                entry_dss = float(dssv[i])
                entry_str = 0.0
                qty = 1.0
                tp1done = False
                tp2done = False""")

# TP2 setelah TP1 (sweep mode saja), sisi long
old_tp1 = """                trades.append(base + (x, "TP1", r * NOTIONAL * TP1_QTY * 100))
                qty -= TP1_QTY
                sl = entry
                tp1done = True
                consec_sl = 0
            if lo[i] <= sl:"""
assert old_tp1 in s
s = s.replace(old_tp1, """                trades.append(base + (x, "TP1", r * NOTIONAL * TP1_QTY * 100))
                qty -= TP1_QTY
                sl = entry
                tp1done = True
                consec_sl = 0
            if RUNNER == "sweep" and tp1done and not tp2done and risk0 > 0 and h[i] >= tp:
                x = tp
                r = (x - entry) / entry
                eq *= (1 + r * NOTIONAL * TP2_QTY - 2 * FEE * NOTIONAL * TP2_QTY)
                trades.append(base + (x, "TP2", r * NOTIONAL * TP2_QTY * 100))
                qty -= TP2_QTY
                tp2done = True
                consec_sl = 0
            if lo[i] <= sl:""")

# runner sweep-only sisi long (setelah cabang MOM & FVG mode-mom)
old_fvg = """                trades.append(base + (x, "FVG", r * NOTIONAL * qty * 100))
                pos = 0
                consec_sl = 0
        else:"""
assert old_fvg in s
s = s.replace(old_fvg, """                trades.append(base + (x, "FVG", r * NOTIONAL * qty * 100))
                pos = 0
                consec_sl = 0
            elif RUNNER == "sweep" and hold_bars >= 1 and bool(swRvH[i]):
                # runner spot: HANYA sweep-lawan (tanpa cross/FVG) -> tutup sisa di close
                x = c[i] * (1 - SLIP)
                r = (x - entry) / entry
                eq *= (1 + r * NOTIONAL * qty - 2 * FEE * NOTIONAL * qty)
                trades.append(base + (x, "MOM:SWP", r * NOTIONAL * qty * 100))
                pos = 0
                consec_sl = 0
        else:""")

io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
