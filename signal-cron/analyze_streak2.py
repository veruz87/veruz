import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv", parse_dates=["entry_time", "exit_time"])
tr = tr.sort_values("exit_time").reset_index(drop=True)
is_loss = (tr.ret_eq < 0).tolist()
runs = []  # (start_idx, length)
i = 0
n = len(tr)
while i < n:
    if is_loss[i]:
        j = i
        while j < n and is_loss[j]:
            j += 1
        runs.append((i, j - i))
        i = j
    else:
        i += 1
print("run loss >=3:", sum(1 for _, L in runs if L >= 3), "kali")
for s, L in runs:
    if L >= 5:
        seg = tr.iloc[s:s + L]
        print(f"--- run {L}x mulai {seg.exit_time.iloc[0]} ---")
        print(seg[["exit_time", "side", "reason", "ret_eq"]].to_string(index=False))
