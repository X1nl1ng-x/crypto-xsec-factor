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
    f = f.copy()
    f["day"] = (f["time"] - pd.Timedelta(hours=1)).dt.floor("D")
    daily["funding"] = f.groupby("day")["funding_rate"].sum()

    return daily.reset_index()

# ---------- quick test on BTC (we replace this part later) ----------
k = load_klines("BTCUSDT")
f = load_funding("BTCUSDT")
d = to_daily(k, f)

print(d.shape)
print(d.head(3))
print(d.tail(3))
print("days with < 24 hours:", (d["n_hours"] < 24).sum())
print("days without funding:", d["funding"].isna().sum())
print("dollar volume check:", round(d["dv"].sum() / k["quote_volume"].sum(), 6))
print("share of taker buys:", round((d["dv_buy"] / d["dv"]).mean(), 3))