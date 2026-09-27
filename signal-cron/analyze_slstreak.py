import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv", parse_dates=["entry_time", "exit_time"])
tr = tr.sort_values("exit_time").reset_index(drop=True)
is_sl = (tr.reason == "SL").tolist()
runs = []
i, n = 0, len(tr)
while i < n:
    if is_sl[i]:
        j = i
        while j < n and is_sl[j]:
            j += 1
        runs.append((i, j - i))
        i = j
    else:
        i += 1
print("run SL murni >=3:", sum(1 for _, L in runs if L >= 3))
print("max SL streak:", max([L for _, L in runs], default=0))
for s, L in runs:
    if L >= 3:
        seg = tr.iloc[s:s + L]
        print(f"--- {L}x SL mulai {seg.exit_time.iloc[0]} ---")
        print(seg[["exit_time", "side", "reason", "ret_eq"]].to_string(index=False))
