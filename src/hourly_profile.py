"""Figure 2 (H2): the daily rhythm of trading, in-sample (2020-2024).
For each coin: the average share of a day's dollar volume traded in each hour (UTC);
then the average over all coins, so that every coin counts the same."""
import pandas as pd
import matplotlib.pyplot as plt
from build_panel import load_klines

universe = pd.read_csv("results/universe.csv")
coins = universe.loc[universe["keep"], "symbol"]

profiles = {}      # one Series per coin: hour -> average share of the day's volume
cv63 = []          # one number per coin: its typical 63-hour coefficient of variation of hourly volume
for sym in coins:
    k = load_klines(sym)
    k = k[k["time"] < "2025-01-01"].copy()                                # in-sample only

    # (1) how much hourly volume moves around within 63 hours, as in the naive measure but scale-free
    v = k["quote_volume"]
    cv = v.rolling(63).std() / v.rolling(63).mean()

    # (2) share of each day's volume traded in each hour; full days with some volume only
    k["date"] = k["time"].dt.floor("D")
    k["hour"] = k["time"].dt.hour
    k["day_total"] = k.groupby("date")["quote_volume"].transform("sum")
    k["n_hours"] = k.groupby("date")["quote_volume"].transform("size")
    k = k[(k["n_hours"] == 24) & (k["day_total"] > 0)].copy()
    if len(k) == 0:
        continue                                                          # no full in-sample day
    k["share"] = k["quote_volume"] / k["day_total"]
    profiles[sym] = k.groupby("hour")["share"].mean()
    cv63.append(cv.median())

profile = pd.DataFrame(profiles).mean(axis=1) * 100                       # % of daily volume, per hour
rhythm_cv = profile.std() / profile.mean()
print("coins:", len(profiles))
print("busiest hour:", profile.idxmax(), round(profile.max(), 2), "%   quietest hour:", profile.idxmin(),
      round(profile.min(), 2), "%   ratio:", round(profile.max() / profile.min(), 2))
print("CV of the 24 hourly shares (average daily profile):", round(rhythm_cv, 3))
print("typical 63-hour CV of hourly volume (median over coins):", round(pd.Series(cv63).median(), 3))

# ---------- the chart ----------
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.bar(profile.index, profile.values, width=0.6, color="#2a78d6")
ax.hlines(100 / 24, -0.5, 23.5, color="#52514e", linewidth=1, linestyle="--")      # a flat day: 1/24 per hour
ax.text(23.8, 100 / 24, "flat day\n(4.17%)", color="#52514e", fontsize=8, va="center")
ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
ax.set_xlim(-0.7, 25.5)
ax.set_xlabel("Hour of the day (UTC)", color="#52514e", fontsize=9)
ax.set_ylabel("Share of daily volume (%)", color="#52514e", fontsize=9)
ax.set_title("Average share of a day's dollar volume traded in each hour, 2020-2024", fontsize=10, loc="left")
ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(colors="#52514e", labelsize=9)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
for side in ["left", "bottom"]:
    ax.spines[side].set_color("#c3c2b7")
fig.tight_layout()
fig.savefig("results/figure2_hourly_profile.png", dpi=200)
print("saved results/figure2_hourly_profile.png")
