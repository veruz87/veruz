import pandas as pd
import sys
SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
TF = sys.argv[2] if len(sys.argv) > 2 else "4h"
tr = pd.read_csv(f"results/trades_DSSLP_{SYM}_{TF}.csv", parse_dates=["entry_time", "exit_time"])
eq = pd.read_csv(f"results/equity_DSSLP_{SYM}_{TF}.csv", parse_dates=["timestamp"])
tr = tr.sort_values("exit_time").reset_index(drop=True)
n = len(tr)
wins = (tr.ret_eq > 0).sum()
gross_w = tr[tr.ret_eq > 0].ret_eq.sum()
gross_l = -tr[tr.ret_eq < 0].ret_eq.sum()
pf = gross_w / gross_l if gross_l > 0 else 0
peak = eq.equity.cummax()
maxdd = ((eq.equity - peak) / peak * 100).min()
print("=== KONFIG ===")
print("Entry: DSS<=30+sweepBuy(str>=40) / DSS>=70+sweepSell(str>=40) (3 bar, tanpa cross), eksekusi open+1bar+slip")
print("SL: wick bar sblm entry +-1.5 ATR | TP1 25%@1.5R + BE, runner tanpa TP pool")
print("Exit: SL > TP1 > MOM(cross/sweep lawan) > FVG-1H-besar | Sesi: skip Asia 07-15 + London 15 WIB + weekend | Cooldown 48h stlh 3xSL")
print("Biaya: fee 0.05%/side, slip 0.0025%, funding 0.01%/8h | Size: 5% eq lev 5x | 2020-01-01 s/d 2025-11-30 TF 4H")
print("=== OVERALL ===")
print(f"trades={n} win={wins} ({wins / n * 100:.1f}%) sum={tr.ret_eq.sum():.2f}% avg={tr.ret_eq.mean():.3f}% PF={pf:.2f}")
print(f"equity akhir={eq.equity.iloc[-1]:.2f} (x{eq.equity.iloc[-1] / 100:.2f}) maxDD={maxdd:.2f}%")
print("=== PER REASON ===")
print(tr.groupby("reason")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== PER SIDE ===")
print(tr.groupby("side")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== PER SIDE x REASON ===")
print(tr.groupby(["side", "reason"])["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== PER TAHUN ===")
tr["y"] = tr.exit_time.dt.year
print(tr.groupby("y")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== 5 BULAN TERBURUK / TERBAIK ===")
tr["ym"] = tr.exit_time.dt.to_period("M")
m = tr.groupby("ym")["ret_eq"].agg(["count", "sum"]).round(3)
print(m.sort_values("sum").head(5).to_string())
print(m.sort_values("sum").tail(5).to_string())
print("=== HOLD JAM (median/mean/max) ===")
print(tr.groupby("reason")["hold_hours"].agg(["count", "median", "mean", "max"]).round(1).to_string())
print("hold>168h:", int((tr.hold_hours > 168).sum()))
print("=== MFE/MAE (R) ===")
print("SL mfe>=1:", int(((tr.reason == "SL") & (tr.mfe_r >= 1)).sum()), "| SL mfe<0.3:", int(((tr.reason == "SL") & (tr.mfe_r < 0.3)).sum()))
print("=== ENTRY SESSION WIB ===")
print(tr.groupby("in_hr_wib")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print(tr.groupby("in_dow")["ret_eq"].agg(["count", "mean", "sum"]).round(3).to_string())
print("=== STREAK ===")
is_loss = (tr.ret_eq < 0).tolist()
runs, i, N = [], 0, len(tr)
while i < N:
    if is_loss[i]:
        j = i
        while j < N and is_loss[j]:
            j += 1
        runs.append(j - i)
        i = j
    else:
        i += 1
from collections import Counter
print("max lose:", max(runs), "| run>=3:", sum(1 for L in runs if L >= 3), "| dist:", dict(sorted(Counter(runs).items())))
print("=== 5 TRADE TERAKHIR ===")
print(tr.tail(5)[["entry_time", "exit_time", "side", "entry", "entry_dss", "hold_hours", "mfe_r", "exit", "reason", "ret_eq"]].to_string(index=False))
