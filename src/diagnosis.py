"""Section 2: what does the naive measure capture? H1 size, H2 horizon, H3 new listings.
In-sample only (PERIOD = "in" in helpers.py)."""
import pandas as pd
from helpers import load_weekly, nw_t, rank_corr, groups, quintile_returns

all_contracts, contracts_90d = load_weekly()

# ---------- H1 and H2: do two measures rank the coins the same way? ----------
print("\nH1, H2: average weekly rank correlation (1 = same ranking, 0 = unrelated)")
for a, b, sample, df in [("naive", "size", "all", all_contracts),     # H1
                         ("naive", "size", "90d", contracts_90d),     # H1
                         ("naive", "cv90", "90d", contracts_90d),     # H2
                         ("cv90", "size", "90d", contracts_90d)]:     # how the purified measure relates to size
    corr = rank_corr(df, a, b)
    print(f"   {a:5s} vs {b:4s} [{sample}]  {corr.mean():6.3f}")

# ---------- H3, part 1: where do new coins end up in the naive ranking? ----------
df = all_contracts.copy()
df["new"] = df["age"] < 30                          # listed less than 30 days ago
df["group"] = 0
for date, week in df.groupby("date"):
    df.loc[week.index, "group"] = groups(week["naive"], 5)
print(f"\nH3: share of new coins (< 30 days) in each naive group; all groups together: {df['new'].mean():.3f}")
print(df.groupby("group")["new"].mean().round(3).to_string())

# ---------- H3, part 2: does the naive measure still predict returns without new coins? ----------
print("\nH3: naive measure with and without new coins")
for sample, d in [("all", all_contracts), ("no new coins", all_contracts[all_contracts["age"] >= 30])]:
    ic = rank_corr(d, "naive", "ret")
    q = quintile_returns(d, "naive")
    print(f"   {sample:13s} IC {ic.mean():6.3f} (t = {nw_t(ic):5.2f})   "
          f"H-L {q['H-L'].mean():7.4f} (t = {nw_t(q['H-L']):5.2f})")