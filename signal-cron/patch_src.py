import io
import re
p = "dss_spot.py"
lines = io.open(p, encoding="utf-8").read().split("\n")

cur = None
out = []
for ln in lines:
    out.append(ln)
    m = re.search(r"if sigL\[i\]:|elif IS_BTC and sigFL\[i\]:|elif \(not LONG_ONLY\) and IS_BTC and sigFS\[i\]:|elif \(not LONG_ONLY\) and sigS\[i\]:|elif \(not IS_BTC\) and sigXL\[i\]:|elif \(not LONG_ONLY\) and \(not IS_BTC\) and sigXS\[i\]:", ln)
    if m:
        t = m.group(0)
        if "sigL" in t or "sigS" in t and "sigX" not in t and "sigF" not in t:
            cur = "sweep"
        elif "sigFL" in t or "sigFS" in t:
            cur = "flat"
        else:
            cur = "cross"
    if re.search(r"^\s*ebar = i\s*$", ln) and cur:
        ind = ln[:len(ln) - len(ln.lstrip())]
        out.append(ind + f'src = "{cur}"')
        cur = None

s = "\n".join(out)
# init state
a = "ebar = -1"
assert a in s
s = s.replace(a, 'ebar = -1\nsrc = ""', 1)
# base + kolom
b = "int(wib_in.hour), hold_bars, hold_hours, round(mfe_r, 2), round(mae_r, 2), round(qty, 2))"
assert b in s
s = s.replace(b, "int(wib_in.hour), hold_bars, hold_hours, round(mfe_r, 2), round(mae_r, 2), round(qty, 2), src)")
c = '"mfe_r", "mae_r", "qty", "exit", "reason", "ret_eq"])'
assert c in s
s = s.replace(c, '"mfe_r", "mae_r", "qty", "src", "exit", "reason", "ret_eq"])')
io.open(p, "w", encoding="utf-8").write(s)
print("patched OK")
