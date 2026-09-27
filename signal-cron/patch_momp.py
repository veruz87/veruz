import io
p = "dss_spot.py"
lines = io.open(p, encoding="utf-8").read().split("\n")
out = []
for i, ln in enumerate(lines):
    out.append(ln)
    if ln.strip() == "tp1done = False":
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if nxt != "tp2done = False":
            ind = ln[:len(ln) - len(ln.lstrip())]
            out.append(ind + "tp2done = False")
            out.append(ind + "momPdone = False")
io.open(p, "w", encoding="utf-8").write("\n".join(out))
print("patched OK")

# label SL trailed: SL-BE jika tp1done ATAU momPdone (SL sudah di entry/+1R)
b = '''trades.append(base + (sl, "SL-BE" if tp1done else "SL", r * NOTIONAL * qty * 100))
                pos = 0
                if not tp1done:'''
assert b in s
s = s.replace(b, '''trades.append(base + (sl, "SL-BE" if (tp1done or momPdone) else "SL", r * NOTIONAL * qty * 100))
                pos = 0
                if not (tp1done or momPdone):''')

io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
