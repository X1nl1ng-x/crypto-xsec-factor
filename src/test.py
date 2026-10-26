"""Section 5, tests 1-5: the naive measure, the purified measure and the buy/sell measures."""
import pandas as pd
from helpers import load_weekly, nw_t, rank_corr, quintile_returns, standardize, fama_macbeth, double_sort, long_short


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

# ---------- test 3: Fama-MacBeth regressions ----------
COLS = ["naive", "log_naive", "cv90", "cv90_buy", "cv90_sell",
        "size", "log_age", "mom", "rev", "vol", "fund7"]
z_all = standardize(all_contracts, COLS)
z_90d = standardize(contracts_90d, COLS)
CONTROLS = ["size", "size_sq", "log_age", "mom", "rev", "vol", "fund7"]

MODELS = [("naive alone", "all", z_all, ["naive"]),
          ("naive + size", "all", z_all, ["naive", "size", "size_sq"]),
          ("naive + age", "all", z_all, ["naive", "log_age"]),
          ("naive + controls", "90d", z_90d, ["naive"] + CONTROLS),
          ("log naive alone", "all", z_all, ["log_naive"]),
          ("log naive + size", "all", z_all, ["log_naive", "size", "size_sq"]),
          ("log naive + age", "all", z_all, ["log_naive", "log_age"]),
          ("log naive + controls", "90d", z_90d, ["log_naive"] + CONTROLS),
          ("cv90 alone", "90d", z_90d, ["cv90"]),
          ("cv90 + controls", "90d", z_90d, ["cv90"] + CONTROLS),
          ("buy + sell + controls", "90d", z_90d, ["cv90_buy", "cv90_sell"] + CONTROLS)]

print("\nTest 3: Fama-MacBeth, average weekly coefficient per 1 standard deviation")
for name, sample, df, xs in MODELS:
    coefs = fama_macbeth(df, xs)
    print(f"\n{name} [{sample}]")
    for x in xs:
        print(f"   {x:10s} {coefs[x].mean():8.4f}  (t = {nw_t(coefs[x]):5.2f})")

# mechanism test: is the buy-side coefficient different from the sell-side coefficient?
coefs = fama_macbeth(z_90d, ["cv90_buy", "cv90_sell"] + CONTROLS)
diff = coefs["cv90_buy"] - coefs["cv90_sell"]
print(f"\nbuy - sell: {diff.mean():.4f}  (t = {nw_t(diff):.2f})")
print("correlation of buy and sell measures (average week):",
      round(rank_corr(contracts_90d, "cv90_buy", "cv90_sell").mean(), 3))

# ---------- test 4: double sorts ----------
print("\nTest 4: high minus low signal (3 groups), within 3 groups of size or age")
for signal, sample, df, control in [("naive", "all", all_contracts, "size"),
                                    ("naive", "all", all_contracts, "age"),
                                    ("cv90", "90d", contracts_90d, "size"),
                                    ("cv90", "90d", contracts_90d, "age")]:
    ds = double_sort(df, control, signal)
    print(f"\n{signal} [{sample}], within groups of {control}")
    for c, label in [(1, "group 1 (lowest)"), (2, "group 2"), (3, "group 3 (highest)"), ("avg", "average")]:
        print(f"   {label:18s} {ds[c].mean():8.4f}  (t = {nw_t(ds[c]):5.2f})")

# ---------- test 5: turnover and costs ----------
print("\nTest 5: long group 1, short group 5; weekly return before and after costs")
for signal, sample, df in TESTS[:3]:            # naive (all), naive (90d), cv90 (90d)
    port = long_short(df, signal)
    print(f"\n{signal} [{sample}]   turnover per week: {port['turnover'].mean():.2f}")
    print(f"   before costs     {port['gross'].mean():8.4f}  (t = {nw_t(port['gross']):5.2f})")
    for bp in [5, 10]:
        net = port["gross"] - bp / 10000 * port["turnover"]     # each unit traded costs bp basis points
        print(f"   after {bp:2d} bp      {net.mean():8.4f}  (t = {nw_t(net):5.2f})")