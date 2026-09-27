import re
s = open("dss_spot.py", encoding="utf-8").read().split("\n")
for i, ln in enumerate(s):
    if 'src = "' in ln and ("sweep" in ln or "flat" in ln or "cross" in ln or ln.strip() == 'src = ""'):
        print(i + 1, ln.strip())
