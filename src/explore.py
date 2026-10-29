"""Exploratory analysis, added after seeing the in-sample results (not pre-registered).
Hypothesis: coins with more variable trading activity usually do worse (lower median return),
but a few of them rise sharply, so their average return is not lower."""
import pandas as pd
from helpers import load_weekly, nw_t, groups, quintile_returns, double_sort, rank_corr

all_contracts, contracts_90d = load_weekly()

# ---------- (i) mean vs median return of the five cv90 groups ----------
rows = []
for stat in ["mean", "median"]:
    q = quintile_returns(contracts_90d, "cv90", stat=stat)
    avg = q.mean()                     # average over all weeks, for each column
    rows.append({"weekly return": stat,
                 "Q1": avg[1], "Q2": avg[2], "Q3": avg[3], "Q4": avg[4], "Q5": avg[5],
                 "H-L": avg["H-L"], "t": nw_t(q["H-L"])})
print("\n(i) Mean and median weekly return of the five cv90 groups (Q1 = lowest)")
print(pd.DataFrame(rows).round(4).to_string(index=False))

# ---------- (ii) big winners: coin-weeks with a return above +50% ----------
df = contracts_90d.dropna(subset=["cv90", "ret"]).copy()
df["group"] = 0
for date, week in df.groupby("date"):
    df.loc[week.index, "group"] = groups(week["cv90"], 5)
df["big_winner"] = df["ret"] > 0.5
print("\n(ii) Share of coin-weeks with a return above +50%, by cv90 group (in %)")
print((df.groupby("group")["big_winner"].mean() * 100).round(2).to_string())

# ---------- added after the out-of-sample run: is it just price volatility? ----------
# (iii) big losers: a return below -33% is the mirror image of +50% (1.5 x 2/3 = 1)
df["big_loser"] = df["ret"] < -1 / 3
print("\n(iii) Share of coin-weeks with a return below -33%, by cv90 group (in %)")
print((df.groupby("group")["big_loser"].mean() * 100).round(2).to_string())

# (iv) median spread of cv90 among coins with similar price volatility
print("\n(iv) Median return, high minus low cv90 (3 groups), within 3 groups of 30-day return volatility")
ds = double_sort(contracts_90d, "vol", "cv90", stat="median")
for c, label in [(1, "group 1 (lowest)"), (2, "group 2"), (3, "group 3 (highest)"), ("avg", "average")]:
    print(f"   {label:18s} {ds[c].mean():8.4f}  (t = {nw_t(ds[c]):5.2f})")

# for comparison: the same median spread (3 groups, same coins) without holding volatility fixed
spread = {}
for date, week in contracts_90d.dropna(subset=["cv90", "ret", "vol"]).groupby("date"):
    g = groups(week["cv90"], 3)
    spread[date] = week.loc[g == 3, "ret"].median() - week.loc[g == 1, "ret"].median()
spread = pd.Series(spread)
print(f"   without holding vol fixed {spread.mean():8.4f}  (t = {nw_t(spread):5.2f})")
shrink = ds["avg"] - spread      # how much holding volatility fixed shrinks the median spread
print(f"   reduction                 {shrink.mean():8.4f}  (t = {nw_t(shrink):5.2f})")

print("rank correlation of cv90 and return volatility (average week):",
      round(rank_corr(contracts_90d, "cv90", "vol").mean(), 3))