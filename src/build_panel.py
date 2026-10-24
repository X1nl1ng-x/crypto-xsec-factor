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
    files = sorted(glob.glob(f"{RAW}/funding/{sym}/*.zip"))
    if not files:
        return pd.DataFrame(columns=["time", "funding_rate"])
    parts = []
    for f in files:
        raw = pd.read_csv(f, header=None)
        parts.append(pd.DataFrame({"calc_time": raw.iloc[:, 0],        # first column
                                   "funding_rate": raw.iloc[:, -1]}))  # last column
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


# ---------- quick test on BTC (we replace this part later) ----------
k = load_klines("BTCUSDT")
f = load_funding("BTCUSDT")

full_hours = pd.date_range(k["time"].min(), k["time"].max(), freq="h")
print("klines:", k.shape, k["time"].min(), "->", k["time"].max())
print("missing hours:", len(full_hours) - len(k))
print(k.head(3))
print("funding:", f.shape, f["time"].min(), "->", f["time"].max())
print(f.head(3))
