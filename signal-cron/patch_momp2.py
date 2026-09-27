import io
p = "dss_spot.py"
lines = io.open(p, encoding="utf-8").read().split("\n")
out = []
for i, ln in enumerate(lines):
    out.append(ln)
    if ln.strip() == "tp1done = False":
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        ind = ln[:len(ln) - len(ln.lstrip())]
        if nxt != "tp2done = False":
            out.append(ind + "tp2done = False")
        if nxt != "momPdone = False" and (len(out) < 2 or out[-2].strip() != "momPdone = False"):
            # cek baris berikut asli juga
            nxt2 = lines[i + 2].strip() if i + 2 < len(lines) else ""
            if nxt != "momPdone = False" and nxt2 != "momPdone = False":
                out.append(ind + "momPdone = False")
io.open(p, "w", encoding="utf-8").write("\n".join(out))
print("patched OK")
