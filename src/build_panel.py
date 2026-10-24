import os
import glob
import pandas as pd

RAW = "data/raw"
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume",
              "ignore"]


def load_klines(sym):
    """All hourly klines of one symbol, sorted by time, one row per hour."""
    files = sorted(glob.glob(f"{RAW}/klines/{sym}/*.zip"))
    df = pd.concat([pd.read_csv(f, header=None, names=KLINE_COLS) for f in files],
                   ignore_index=True)

    # convert time to numbers; header lines ("open_time") become NaN
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    # drop rows whose time is NaN (= the header lines); only look at this column
    df = df.dropna(subset=["open_time"])
    # us = microseconds (µs): True where the time looks like microseconds (> 10^14)
    us = df["open_time"] > 1e14
    # for those rows only, convert microseconds to milliseconds
    df.loc[us, "open_time"] = df.loc[us, "open_time"] / 1000
    # milliseconds since 1970-01-01 -> readable UTC timestamp (start of the hour)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

    keep = ["open", "close", "quote_volume", "taker_buy_quote_volume", "count"]
    df[keep] = df[keep].astype(float)
    # keep needed columns, drop hours that appear twice (overlapping files), sort by time
    df = df[["time"] + keep].drop_duplicates("time").sort_values("time")
    # renumber rows 0, 1, 2, ... and throw away the old row numbers
    return df.reset_index(drop=True)


def load_funding(sym):
    """All funding settlements of one symbol: time (rounded to the hour) and rate."""
    # all monthly files of this symbol, sorted by month
    files = sorted(glob.glob(f"{RAW}/funding/{sym}/*.zip")) 
    if not files:
        return pd.DataFrame(columns=["time", "funding_rate"])
    parts = []
    # one monthly file per iteration
    for f in files:
        raw = pd.read_csv(f, header=None)
        parts.append(pd.DataFrame({"calc_time": raw.iloc[:, 0],        # first column
                                   "funding_rate": raw.iloc[:, -1]}))  # last column
    # concatenate all monthly parts into one DataFrame, ignore the old row numbers (index) and create new ones
    df = pd.concat(parts, ignore_index=True)

    # same steps as for klines: numbers only, drop header lines, microseconds -> ms
    df["calc_time"] = pd.to_numeric(df["calc_time"], errors="coerce")
    df = df.dropna(subset=["calc_time"])
    us = df["calc_time"] > 1e14
    df.loc[us, "calc_time"] = df.loc[us, "calc_time"] / 1000
    # round to the full hour: some settlement times are a few milliseconds off
    df["time"] = pd.to_datetime(df["calc_time"], unit="ms", utc=True).dt.floor("h")
    df["funding_rate"] = df["funding_rate"].astype(float)

    df = df[["time", "funding_rate"]].drop_duplicates("time").sort_values("time")
    return df.reset_index(drop=True)

def to_daily(k, f):
    """One row per UTC day: volumes, prices, the naive measure and funding."""
    k = k.copy()
    # remove "fake" hours: after a contract dislisted, Biance's files continue with a frozen price and zero trades.
    # keep only the period between the first and the last real trade
    traded = k["count"] >0  # count of trades in that hour > 0
    first, last = k.loc[traded, "time"].min(), k.loc[traded, "time"].max()
    k = k[(k["time"] >= first ) & (k["time"] <= last)]
    
    # new column "date": round each hour down to its UTC day (13:00 -> 0:00 of that day)
    k["date"] = k["time"].dt.floor("D")                  # the UTC day of each hour

    daily = k.groupby("date").agg(
        dv=("quote_volume", "sum"),                      # daily dollar volume
        dv_buy=("taker_buy_quote_volume", "sum"),        # volume from taker buys
        n_hours=("quote_volume", "size"),                # hours with data (24 = full day)
        close=("close", "last"),                         # price at the end of the day
    )
    daily["dv_sell"] = daily["dv"] - daily["dv_buy"]     # volume from taker sells

    # entry/exit price: the open of the 01:00 UTC bar (one hour after the signal)
    # to avoid lookahead bias
    at_01 = k[k["time"].dt.hour == 1] # boolean mask: only keep the rows where the hour is 1
    daily["open_01"] = at_01.set_index("date")["open"]

    # naive measure, exactly as in the original code: rolling std of hourly quote
    # volume over 63 hours, min_periods=1, missing values set to 0.
    # at each hour t, std of hourly quote volume over the last 63 hours (t-62, t-61, ..., t) (the window looks back only so no future data is used)
    # We keep its value at the end of each day.
    k["naive"] = k["quote_volume"].rolling(63, min_periods=1).std().fillna(0.0)
    daily["naive"] = k.groupby("date")["naive"].last()

    # funding paid by a long position between 01:00 today and 01:00 tomorrow
    # (shift by one hour, so a settlement at 00:00 tomorrow counts for today)
    if len(f) > 0:
        f = f.copy()
        f["day"] = (f["time"] - pd.Timedelta(hours=1)).dt.floor("D")
        daily["funding"] = f.groupby("day")["funding_rate"].sum()
    else:
        daily["funding"] = float("nan")  # no funding data at all, so we fill the column with NaN

    return daily.reset_index()

# ---------- build the daily panel for all coins ----------
symbols = sorted(s for s in os.listdir(f"{RAW}/klines")
                 if os.path.isdir(f"{RAW}/klines/{s}"))      # folders only (skip .DS_Store)
panel = []
for i, sym in enumerate(symbols):
    d = to_daily(load_klines(sym), load_funding(sym))
    d["symbol"] = sym
    panel.append(d)
    if i % 50 == 0:
        print(f"{i}/{len(symbols)} {sym}")

panel = pd.concat(panel, ignore_index=True)

# ---------- contracts that stopped trading and came back later ----------
# Some contracts stopped trading for weeks or years (frozen price, zero volume) and were relisted later. 
# as a new listing: 0 = first listing, 1 = relisted.
panel = panel[panel["dv"] > 0].copy() # only keep rows with non-zero daily volume (drop frozen rows)
panel["gap"] = panel.groupby("symbol")["date"].diff().dt.days      # days since this coin's previous row
panel["new_listing"] = panel["gap"] > 7
panel["listing"] = panel.groupby("symbol")["new_listing"].cumsum()  # 0 = first listing, 1 = relisted
panel = panel.drop(columns=["gap", "new_listing"])

os.makedirs("data/clean", exist_ok=True)
panel.to_parquet("data/clean/daily_panel.parquet", index=False)

print("coins:", panel["symbol"].nunique(), " rows:", len(panel))
print("days with < 24 hours:", (panel["n_hours"] < 24).sum())
print("days without funding:", panel["funding"].isna().sum())
print("coins with some missing funding:",
      panel.loc[panel["funding"].isna(), "symbol"].nunique())

relisted = panel.groupby("symbol")["listing"].max()
print("relisted symbols:", list(relisted[relisted > 0].index))