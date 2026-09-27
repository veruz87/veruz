import pandas as pd
import numpy as np

DATA = "C:/Users/RANGGA/Documents/Default Project/data-backtest"
b = pd.read_csv(f"{DATA}/BTCUSDT/BTCUSDT_1d.csv", parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def stoch(c, h, l, n):
    lo = l.rolling(n).min()
    hi = h.rolling(n).max()
    return ((c - lo) / (hi - lo).replace(0, np.nan) * 100.0).fillna(50.0)


def dss(df):
    s1 = stoch(df.close, df.high, df.low, 10)
    p1 = ema(s1, 9)
    d = ema(stoch(p1, p1, p1, 10), 9)
    t = ema(d, 5)
    return d, t


for tf, rule in (("W", "W-SUN"), ("ME", "ME")):
    g = b.resample(rule, on="timestamp").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
    d, t = dss(g)
    g["dss"] = d
    g["bear"] = (g.dss < 50) & ((g.dss - g.dss.shift(2)) < 0)
    print(f"=== 1{tf} DSS: {len(g)} bar, bearish {int(g.bear.sum())} ({g.bear.mean() * 100:.0f}%) ===")
    print(g[["timestamp", "close", "dss"]].tail(8).round(1).to_string(index=False))
    # bentang bearish terpanjang
    g["grp"] = (g.bear != g.bear.shift()).cumsum()
    spans = g[g.bear].groupby("grp").agg(mulai=("timestamp", "first"), akhir=("timestamp", "last"), n=("timestamp", "count"))
    print("bentang bearish terpanjang:")
    print(spans.sort_values("n", ascending=False).head(5).to_string())
