"""Shared code for the tests: loading the weekly table, and one function per kind of test.
Every test works the same way: for each week, compute one number (or one row of numbers);
then report the average over all weeks with a Newey-West t-statistic."""

import numpy as np
import pandas as pd

# "in": in-sample (2020-2024), where all development happen. Set it like "training + development set"
# "out": out-of-sample (January 2025 - September 2026), run once at the very end. Set it like "test set"
PERIOD = "in"
# start with the first week in which at least 20 coins have the purified measure
MIN_COINS = 20    

def load_weekly():
    """The weekly table of PERIOD, as two samples: all contracts, and contracts with 90 full days."""
    w = pd.read_parquet("data/clean/weekly.parquet")
    if PERIOD == "in": 
        w = w[w["date"] <= "2024-12-31"]
    else:
        w = w[w["date"] >= "2025-01-01"]
    coins = w[w["cv90"].notna()].groupby("date").size()     # coins with cv90, per week
    first_week = coins[coins >= MIN_COINS].index.min()      # first week with >= 20 coins that have cv90
    w = w[w["date"] >= first_week].copy()                   # keep that week and all later weeks
    w["log_age"] = np.log(w["age"])
    print(PERIOD, "sample:", w["date"].min().date(), "to", w["date"].max().date(),
          " weeks:", w["date"].nunique(), " coin-weeks:", len(w))
    return w, w[w["cv90"].notna()]


def nw_t(series, lags=4):
    """t-statistic of the mean of a weekly series, with Newey-West standard errors.
    (Newey and West, 1987):
        t = mean / standard error
        standard error = sqrt(var / T)
        var = gamma_0 + 2 * sum over k = 1..lags of (1 - k / (lags + 1)) * gamma_k
        gamma_k = covariance between weeks k apart (gamma_0 = the variance)
    """
    x = series.dropna().values
    T = len(x) # number of weeks
    d = x - x.mean()    # each weeks's distrance from the mean
    nw_var = np.mean(d*d)  # gamma_0, the ordinary variance of the series
    for k in range(1, lags+1):
        # gamma_k = ∑(xt-mean)(xt-k-mean) / T, the covariance between weeks k apart
        gamma_k = np.sum(d[k:] * d[:-k]) / T  
        nw_var += 2 * (1 - k/(lags+1)) * gamma_k   # Newey-West weights
    return x.mean() / np.sqrt(nw_var / T)   # t-statistic of the mean

def rank_corr(df, a, b):
    """For each week: the correlation between the ranks of column a and the ranks of column b."""
    corr = {}
    for date, week in df.groupby("date"):
        week = week.dropna(subset=[a, b])
        corr[date] = week[a].rank().corr(week[b].rank())
    return pd.Series(corr)

def groups(x, n):
    """Group number 1..n of each value, in equal-sized groups (1 = lowest values).
    rank(method="first") gives tied values different ranks, so qcut can always cut into n equal parts."""
    return pd.qcut(x.rank(method="first"), n, labels=False) + 1


def quintile_returns(df, signal, ret="ret"):
    """For each week: sort the coins into 5 groups by the signal; average return of each group.
    One row per week, with columns 1-5 and H-L (group 5 minus group 1)."""
    rows = {}
    for date, week in df.groupby("date"):
        week = week.dropna(subset=[signal, ret])
        g = groups(week[signal], 5)
        rows[date] = week.groupby(g)[ret].mean()            # average return of groups 1-5
    q = pd.DataFrame.from_dict(rows, orient="index")        # one row per week
    q["H-L"] = q[5] - q[1]
    return q