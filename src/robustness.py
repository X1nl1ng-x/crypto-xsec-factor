"""Section 5, robustness: only the checks fixed in the proposal, all for the purified measure.
Windows of 60 and 120 days; without the smallest 20% of coins; year by year; one-day holding period."""
import pandas as pd
from helpers import (MIN_COINS, load_weekly, nw_t, rank_corr, quintile_returns,
                     standardize, fama_macbeth)

all_contracts, contracts_90d = load_weekly()
CONTROLS = ["size", "size_sq", "log_age", "mom", "rev", "vol", "fund7"]


def main_stats(name, df, signal, ret="ret"):
    """One row: rank IC, quintile H-L and the Fama-MacBeth coefficient with all controls, each with its t."""
    ic = rank_corr(df, signal, ret)
    q = quintile_returns(df, signal, ret)
    z = standardize(df, [signal, "size", "log_age", "mom", "rev", "vol", "fund7"])
    coefs = fama_macbeth(z, [signal] + CONTROLS, ret)
    return {"variant": name,
            "IC": ic.mean(), "IC t": nw_t(ic),
            "H-L": q["H-L"].mean(), "H-L t": nw_t(q["H-L"]),
            "FM": coefs[signal].mean(), "FM t": nw_t(coefs[signal])}


# coins with 120 full days; start in the first week with at least 20 of them (same rule as load_weekly)
with_cv120 = contracts_90d[contracts_90d["cv120"].notna()]
coins = with_cv120.groupby("date").size()
with_cv120 = with_cv120[with_cv120["date"] >= coins[coins >= MIN_COINS].index.min()]

# each week, drop the smallest 20% of coins by dollar volume
big = []
for date, week in contracts_90d.groupby("date"):
    big.append(week[week["size"] >= week["size"].quantile(0.2)])
no_small = pd.concat(big)

rows = [main_stats("main: cv90", contracts_90d, "cv90"),
        main_stats("window 60 days", contracts_90d, "cv60"),
        main_stats("window 120 days", with_cv120, "cv120"),
        main_stats("without smallest 20%", no_small, "cv90"),
        main_stats("hold 1 day", contracts_90d, "cv90", ret="ret1d")]
for year in [2020, 2021, 2022, 2023, 2024]:
    one_year = contracts_90d[contracts_90d["date"].dt.year == year]
    rows.append(main_stats(f"year {year}", one_year, "cv90"))

print("\nRobustness of the purified measure (t = Newey-West t-statistic)")
table = pd.DataFrame(rows).round({"IC": 3, "IC t": 2, "H-L": 4, "H-L t": 2, "FM": 4, "FM t": 2})
print(table.to_string(index=False))