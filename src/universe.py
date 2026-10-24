"""
Keep: perpetual contracts on crypto coins (contractType PERPETUAL, underlyingType COIN
in Binance's exchangeInfo), plus delisted crypto contracts that are no longer listed there.
Drop:
  - tradfi:      stocks, ETFs, commodities, FX and pre-IPO companies (TRADIFI_PERPETUAL)
  - index:       index contracts (underlyingType INDEX, plus delisted BLUEBIRDUSDT, FOOTBALLUSDT, DOTECOUSDT)
  - stablecoin:  USDCUSDT
  - gold token:  PAXGUSDT, XAUTUSDT
Special cases:
  - MDTUSDT is kept: in our data it is the crypto MDT; Binance gave the symbol to a stock
    only on 2026-10-21, after our sample ends.
  - USTCUSDT is kept: it lost its peg in 2022 and trades like any other coin.

Output: results/universe.csv, one row per symbol with keep (True/False) and the reason.
"""

import json
import os
import pandas as pd

panel = pd.read_parquet("data/clean/daily_panel.parquet")
with open("data/raw/exchange_info.json") as f:
    info = {s["symbol"]: s for s in json.load(f)["symbols"]}   # symbol -> its official info

missing = sorted(s for s in panel["symbol"].unique() if s not in info)
print(len(missing), "symbols in daily_panel but not in exchangeInfo:", missing)

# look up each symbol type and decide whether to keep it or not
MANUAL = {
    "BLUEBIRDUSDT": "index",       # delisted index contract, not in exchangeInfo
    "FOOTBALLUSDT": "index",     
    "DOTECOUSDT": "index",
    "USDCUSDT": "stablecoin",
    "PAXGUSDT": "gold token",      # price follows gold
    "XAUTUSDT": "gold token",
    "MDTUSDT": "",                 # crypto MDT in our data; symbol given to a stock on 2026-10-21
}

rows = []
for sym in sorted(panel["symbol"].unique()):
    s = info.get(sym)              # None if the contract is no longer in exchangeInfo
    if sym in MANUAL:
        reason = MANUAL[sym]
    elif s is None:
        reason = ""                # delisted crypto contracts
    elif s["contractType"] == "TRADIFI_PERPETUAL":
        reason = "tradfi"          # stocks, ETFs, commodities, FX, pre-IPO companies
    elif s["underlyingType"] == "INDEX":
        reason = "index"
    else:
        reason = ""
    rows.append({"symbol": sym, "keep": reason == "", "reason": reason})

universe = pd.DataFrame(rows)
os.makedirs("results", exist_ok=True)
universe.to_csv("results/universe.csv", index=False)
print(universe["reason"].replace("", "kept").value_counts())