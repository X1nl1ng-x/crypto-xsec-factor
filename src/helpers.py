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
    w["log_naive"] = np.log(w["naive"])                     # for regressions (naive is very skewed)
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


def quintile_returns(df, signal, ret="ret", stat = "mean"):
    """For each week: sort the coins into 5 groups by the signal; 
    mean (or meadian) return of each group.
    One row per week, with columns 1-5 and H-L (group 5 minus group 1)."""
    rows = {}
    for date, week in df.groupby("date"):
        week = week.dropna(subset=[signal, ret])
        g = groups(week[signal], 5)
        rows[date] = week.groupby(g)[ret].agg(stat)         # mean (or median) return of groups 1-5
    q = pd.DataFrame.from_dict(rows, orient="index")        # one row per week
    q["H-L"] = q[5] - q[1]
    return q

def zscore(x): # x is a pandas Series of one variable in one week
    """One variable in one week: clip at the 1st and 99th percentiles, then standardize."""
    x = x.clip(x.quantile(0.01), x.quantile(0.99))
    # z-score = (value - mean) / standard deviation
    return (x - x.mean()) / x.std()


def standardize(df, cols):
    """Clip and standardize the columns cols within each week; add size squared."""
    df = df.copy()
    for col in cols:
        df[col] = df.groupby("date")[col].transform(zscore)
    # use the squared size as a regressor in regressions, to capture the non-linear effect of size
    df["size_sq"] = df["size"] ** 2
    return df


def fama_macbeth(df, xs, ret="ret"):
    """For each week: regress the return on the variables xs (with a constant).
    One row of coefficients per week."""
    coefs = {}
    for date, week in df.groupby("date"):
        week = week.dropna(subset=xs + [ret])
        X = week[xs].copy()
        X["const"] = 1.0                                                   # to calculate the intercept
        b = np.linalg.lstsq(X.values, week[ret].values, rcond=None)[0]    # OLS coefficients
        coefs[date] = pd.Series(b, index=X.columns)
    return pd.DataFrame.from_dict(coefs, orient="index")

def double_sort(df, control, signal, ret="ret"):
    """For each week: split the coins into 3 groups by the control (e.g. size); 
    within each group, split again into 3 groups by the signal and take high minus low.
    One row per week: high-minus-low within control groups 1, 2, 3, and their average."""
    rows = {}
    for date, week in df.groupby("date"):
        week = week.dropna(subset=[control, signal, ret])
        control_group = groups(week[control], 3)
        hl = {}
        for c in [1, 2, 3]:
            part = week[control_group == c]                  # coins of similar size (or age)
            signal_group = groups(part[signal], 3)
            high = part.loc[signal_group == 3, ret].mean()
            low = part.loc[signal_group == 1, ret].mean()
            hl[c] = high - low
        rows[date] = hl
    out = pd.DataFrame.from_dict(rows, orient="index")      # one row per week
    out["avg"] = out[[1, 2, 3]].mean(axis=1)
    return out


def long_short(df, signal, ret="ret"):
    """For each week: long group 1 (lowest signal), short group 5 (highest), equal weights.
    This is the trade the hypothesis suggests: high variability -> low returns.
    One row per week: the return before costs, and the turnover = sum of |weight change|
    over both legs (it ignores how weights drift during the week)."""
    rows = {}
    last_long = pd.Series(dtype=float)      # last week's weights (empty in the first week)
    last_short = pd.Series(dtype=float)
    for date, week in df.groupby("date"):
        week = week.dropna(subset=[signal, ret])
        g = groups(week[signal], 5)
        coin = week["symbol"] + "_" + week["listing"].astype(str)     # one id per listing
        long = pd.Series(1 / (g == 1).sum(), index=coin[g == 1])       # equal weights, sum to 1
        short = pd.Series(1 / (g == 5).sum(), index=coin[g == 5])
        # weight change of each coin: how much more or less we hold than last week. 
        # If a coin is not held in one of the two weeks, its weight is 0.
        turnover = (long.sub(last_long, fill_value=0).abs().sum()
                    + short.sub(last_short, fill_value=0).abs().sum())
        gross = week.loc[g == 1, ret].mean() - week.loc[g == 5, ret].mean()
        rows[date] = {"gross": gross, "turnover": turnover}
        last_long, last_short = long, short
    return pd.DataFrame.from_dict(rows, orient="index")