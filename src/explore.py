"""Exploratory analysis, added after seeing the in-sample results (not pre-registered).
Hypothesis: coins with more variable trading activity usually do worse (lower median return),
but a few of them rise sharply, so their average return is not lower."""
import pandas as pd
from helpers import load_weekly, nw_t, groups, quintile_returns

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