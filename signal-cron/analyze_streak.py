import pandas as pd
tr = pd.read_csv("results/trades_DSSLP_BTCUSDT_4h.csv", parse_dates=["entry_time", "exit_time"])
tr = tr.sort_values("exit_time").reset_index(drop=True)
is_loss = (tr.ret_eq < 0).tolist()
n = len(tr)
# hitung run kekalahan
runs = []
cur = 0
for v in is_loss:
    if v:
        cur += 1
    else:
        if cur >= 1:
            runs.append(cur)
        cur = 0
if cur >= 1:
    runs.append(cur)
from collections import Counter
print("total trade:", n, "| loss:", sum(is_loss), "| win:", n - sum(is_loss))
print("max lose streak:", max(runs) if runs else 0)
print("distribusi run loss:", dict(sorted(Counter(runs).items())))
# hitung kejadian 3x beruntun (non-overlapping window per run: run L memberi L-2 kejadian tumpang-tindih, floor(L/3) non-overlapping)
overlap = sum(max(0, L - 2) for L in runs)
nonoverlap = sum(L // 3 for L in runs)
print("kejadian 3x-beruntun (tumpang-tindih):", overlap)
print("kejadian 3x-beruntun (non-overlapping blok 3):", nonoverlap)
print("run loss >=3 sebanyak:", sum(1 for L in runs if L >= 3), "kali")
# tampilkan posisi run >=3
idx = 0
shown = 0
for L in runs:
    start = idx
    idx += L + 1  # +1 win pemisah (kasar)
    if L >= 3 and shown < 10:
        seg = tr.iloc[start:start + L]
        print(f"--- run loss {L}x mulai {seg.exit_time.iloc[0]} ---")
        print(seg[["exit_time", "side", "reason", "ret_eq"]].to_string(index=False))
        shown += 1
