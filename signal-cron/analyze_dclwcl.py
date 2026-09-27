import pandas as pd
import numpy as np

DATA = "C:/Users/RANGGA/Documents/Default Project/data-backtest"
b = pd.read_csv(f"{DATA}/BTCUSDT/BTCUSDT_1d.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

# 1) swing low pivot-12 (kandidat DCL) + konfirmasi oscillator (DSS cross-up <=10 bar setelahnya)
L = R = int(__import__("os").environ.get("PIV", "12"))
w = L + R + 1
wmin = b.low.rolling(w).min().values
lv = b.low.values
_b = b.copy()
_b["piv"] = np.nan
for j in range(len(b)):
    if j - R >= 0 and not np.isnan(wmin[j]) and lv[j - R] == wmin[j]:
        _b.loc[j - R, "piv"] = lv[j - R]  # timestamp = bar low aktual

DLEN, DEMA, TRIG = 10, 9, 5


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def stoch(c, h, l, n):
    lo = l.rolling(n).min()
    hi = h.rolling(n).max()
    return ((c - lo) / (hi - lo).replace(0, np.nan) * 100.0).fillna(50.0)


s1 = stoch(b.close, b.high, b.low, DLEN)
p1 = ema(s1, DEMA)
b["dss"] = ema(stoch(p1, p1, p1, DLEN), DEMA)
b["trg"] = ema(b.dss, TRIG)
b["xU"] = ((b.dss.shift(1) <= b.trg.shift(1)) & (b.dss > b.trg)).values

piv = _b.dropna(subset=["piv"]).reset_index()
dcls = []
for _, r in piv.iterrows():
    i = int(r["index"])
    conf = bool(b.xU.iloc[i:i + 11].any())  # cross dalam 10 bar setelah low aktual (konfirmasi PDF)
    dcls.append((b.timestamp[i], float(r.piv), conf))
d = pd.DataFrame(dcls, columns=["t", "low", "conf"])
d["gap"] = d.t.diff().dt.days
print(f"=== DCL kandidat: {len(d)} (terkonfirmasi DSS: {int(d.conf.sum())}) ===")
dc = d[d.conf].reset_index(drop=True)
dc["gap"] = dc.t.diff().dt.days
print(f"DCL terkonfirmasi: {len(dc)}, median gap {dc.gap.median():.0f}, mean {dc.gap.mean():.0f}")
print(f"masuk window 54-66: {int(((dc.gap >= 54) & (dc.gap <= 66)).sum())}/{len(dc) - 1} "
      f"({((dc.gap >= 54) & (dc.gap <= 66)).sum() / max(1, len(dc) - 1) * 100:.0f}%)")
print(dc[["t", "low", "gap"]].to_string(index=False))
# 2) WCL: rangkai DCL sampai span 168-294 hari, WCL = terendah grup
print()
print("=== WCL (rantai DCL span 168-294 hari) ===")
wcls = []
i = 0
n = len(dc)
while i < n:
    j = i
    while j + 1 < n and (dc.t[j + 1] - dc.t[i]).days < 168:
        j += 1
    k = j
    while k + 1 < n and (dc.t[k + 1] - dc.t[i]).days <= 294:
        k += 1
    grp = dc.iloc[i:k + 1]
    wl = grp.loc[grp.low.idxmin()]
    wcls.append((dc.t[i].date(), wl.t.date(), wl.low, (dc.t[k] - dc.t[i]).days, len(grp)))
    i = k + 1
w = pd.DataFrame(wcls, columns=["mulai", "wcl", "low", "span", "ndcl"])
print(w.to_string(index=False))
