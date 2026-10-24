import json
import requests

r = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=30)
r.raise_for_status()
with open("data/raw/exchange_info.json", "w") as f:
    json.dump(r.json(), f)
print("symbols in exchangeInfo:", len(r.json()["symbols"]))