"""Section 5, tests 1-5: the naive measure, the purified measure and the buy/sell measures."""
import pandas as pd
from helpers import load_weekly, nw_t, rank_corr, quintile_returns


all_contracts, contracts_90d = load_weekly()

# which signal is tested on which sample
TESTS = [("naive", "all", all_contracts),
         ("naive", "90d", contracts_90d),
         ("cv90", "90d", contracts_90d),
         ("cv90_buy", "90d", contracts_90d),
         ("cv90_sell", "90d", contracts_90d)]

# ---------- test 1: rank IC ----------
rows = []
for signal, sample, df in TESTS:
    ic = rank_corr(df, signal, "ret")     # rank IC = rank correlation of signal and next week's return （Information Coefficient）
    rows.append({"signal": signal, "sample": sample, "mean IC": ic.mean(), "t": nw_t(ic)})
print("\nTest 1: rank IC")
print(pd.DataFrame(rows).round(3).to_string(index=False))

# ---------- test 2: quintile portfolios ----------
rows = []
for signal, sample, df in TESTS:
    q = quintile_returns(df, signal)
    avg = q.mean()                     # average over all weeks, for each column
    rows.append({"signal": signal, "sample": sample,
                 "Q1": avg[1], "Q2": avg[2], "Q3": avg[3], "Q4": avg[4], "Q5": avg[5],
                 "H-L": avg["H-L"], "t": nw_t(q["H-L"])})
print("\nTest 2: average weekly return of the five groups (Q1 = lowest signal)")
print(pd.DataFrame(rows).round(4).to_string(index=False))