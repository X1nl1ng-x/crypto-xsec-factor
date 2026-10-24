import numpy as np
import pandas as pd

KEYS = ["symbol", "listing"]

# ---------- 1. load the daily panel, keep the coins in the universe ----------
d = pd.read_parquet("data/clean/daily_panel.parquet")
universe = pd.read_csv("results/universe.csv")
keep = universe.loc[universe["keep"], "symbol"]
d = d[d["symbol"].isin(keep)]
d = d.sort_values(KEYS + ["date"]).reset_index(drop=True)
d["funding"] = d["funding"].fillna(0.0)     # missing funding = 0
print("coins:", d["symbol"].nunique(), " listings:", d.groupby(KEYS).ngroups, " rows:", len(d))


def roll_mean(x, n, min_periods):
    """Mean of x over the last n rows (days), within each listing."""
    return d.groupby(KEYS)[x].transform(lambda s: s.rolling(n, min_periods=min_periods).mean())


def roll_std(x, n, min_periods):
    """Standard deviation of x over the last n rows (days), within each listing."""
    return d.groupby(KEYS)[x].transform(lambda s: s.rolling(n, min_periods=min_periods).std())


def log_cv(x, n):
    """log(std / mean) of x over the last n days; NaN unless all n days are full days."""
    # min_periods = n: a value only once the window is there
    return np.log(roll_std(x, n, n) / roll_mean(x, n, n))


# ---------- 2. signals and controls for every day (known at the end of that day) ----------
# volume measures use full days only: listing and delisting days have only a few hours
full = d["n_hours"] == 24
for col in ["dv", "dv_buy", "dv_sell"]:
    d[col + "_full"] = d[col].where(full)

for n in [60, 90, 120]:
    d[f"cv{n}"] = log_cv("dv_full", n)                 # purified measure (90 = main)
d["cv90_buy"] = log_cv("dv_buy_full", 90)              # mechanism: buyer-initiated volume
d["cv90_sell"] = log_cv("dv_sell_full", 90)            # mechanism: seller-initiated volume

prev_close = d.groupby(KEYS)["close"].shift(1)      # previous day's close, within each listing
d["ret_d"] = d["close"] / prev_close - 1                                    # daily return
# size is proxied, for lack of market-cap data, by the level of dollar volume
d["size"] = np.log(roll_mean("dv_full", 90, 1))      
# momemtum: return over the past 30 days,skipping the last day to avoid look-ahead bias                     
d["mom"] = prev_close / d.groupby(KEYS)["close"].shift(31) - 1             
d["rev"] = d["ret_d"]                                                       # last day's return as a reversal signal
d["vol"] = roll_std("ret_d", 30, 30)                                        # 30-day return volatility
# avg daily funding over the last 7 days, because funding is a noisy signal and we want to avoid overreacting to one day's funding
d["fund7"] = roll_mean("funding", 7, 7)            
# start date of each listing, with minimum date
d["start"] = d.groupby(KEYS)["date"].transform("min")                  

# ---------- 3. weekly table: signals from Sunday, trades at Monday 01:00 ----------
SIGNALS = ["naive", "cv60", "cv90", "cv120", "cv90_buy", "cv90_sell",
           "size", "mom", "rev", "vol", "fund7"]

# step 1: Sunday's signals become Monday's signals
w = d.loc[d["date"].dt.dayofweek == 6, KEYS + ["date", "start"] + SIGNALS].copy()   # Sundays
w["date"] = w["date"] + pd.Timedelta(days=1)        # formation: Monday 00:00 UTC
w["age"] = (w["date"] - w["start"]).dt.days         # days since listing

# step 2: on Monday we buy at the 01:00 open; from then on a long pays funding
# (each day's funding runs from 01:00 to 01:00 the next day)
d["monday"] = d["date"] - pd.to_timedelta(d["date"].dt.dayofweek, unit="D")   # Monday of each day's week
d["fund_week"] = d.groupby(KEYS + ["monday"])["funding"].transform("sum")     # Mon 01:00 to next Mon 01:00

entry = d[KEYS + ["date", "open_01", "funding", "fund_week"]]
entry = entry.rename(columns={"open_01": "entry", "funding": "paid_1d", "fund_week": "paid_1w"})
w = w.merge(entry, on=KEYS + ["date"], how="left")
w = w.dropna(subset=["entry"])                                  # not tradable at Monday 01:00
w = w[w["date"] + pd.Timedelta(days=7) <= d["date"].max()]      # the week must end inside the data

# step 3: we sell at the 01:00 open one day later (check) or one week later (main)
w["date_1d"] = w["date"] + pd.Timedelta(days=1)
w["date_1w"] = w["date"] + pd.Timedelta(days=7)
opens = d[KEYS + ["date", "open_01"]]
w = w.merge(opens.rename(columns={"date": "date_1d", "open_01": "exit_1d"}), on=KEYS + ["date_1d"], how="left")
w = w.merge(opens.rename(columns={"date": "date_1w", "open_01": "exit_1w"}), on=KEYS + ["date_1w"], how="left")

# step 4: contracts delisted before we sell: use their last available price
last = d.groupby(KEYS).agg(last_date=("date", "max"), last_close=("close", "last")).reset_index()
w = w.merge(last, on=KEYS)
gone_1d = w["exit_1d"].isna() & (w["last_date"] <= w["date_1d"])
gone_1w = w["exit_1w"].isna() & (w["last_date"] <= w["date_1w"])
w.loc[gone_1d, "exit_1d"] = w.loc[gone_1d, "last_close"]
w.loc[gone_1w, "exit_1w"] = w.loc[gone_1w, "last_close"]

# step 5: returns of a long, net of funding
w["ret"] = w["exit_1w"] / w["entry"] - 1 - w["paid_1w"]
w["ret1d"] = w["exit_1d"] / w["entry"] - 1 - w["paid_1d"]
print("delisting exits: week", gone_1w.sum(), " day", gone_1d.sum())
print("missing returns: week", w["ret"].isna().sum(), " day", w["ret1d"].isna().sum())

w = w[["date"] + KEYS + ["age"] + SIGNALS + ["ret", "ret1d"]]
w.to_parquet("data/clean/weekly.parquet", index=False)

# ---------- checks ----------
print("rows:", len(w), " weeks:", w["date"].nunique(),
      " first:", w["date"].min().date(), " last:", w["date"].max().date())
print("first week with cv90:", w.loc[w["cv90"].notna(), "date"].min().date())
print("coins per week (median): all", w.groupby("date").size().median(),
      " with cv90", w[w["cv90"].notna()].groupby("date").size().median())
print(w.drop(columns=KEYS + ["date"]).describe().T[["count", "mean", "50%", "min", "max"]].round(3))