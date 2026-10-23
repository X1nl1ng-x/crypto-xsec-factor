import requests
import os
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# Symbol list: this bucket also contains delisted contracts -> no survivorship bias.
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}" # XML namesspace prefix
SYMBOL_FILE = "data/raw/symbols_um_usdt.txt"
FILE_LIST = "data/raw/file_list.csv"
START, END = "2020-01", "2026-09"

def get(url, params = None):
    """requests.get, but try 3 times because the network sometimes fails."""
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2)

def list_folders(prefix):
    """Return the names of all sub-folders directly under `prefix`."""
    names = []
    marker = ""
    while True:
        params = {"delimiter": "/", "prefix": prefix}
        if marker:
            params["marker"] = marker
        root = ET.fromstring(get(BASE, params).content)

        for cp in root.findall(NS + "CommonPrefixes"):
            path = cp.find(NS + "Prefix").text        # ".../klines/BTCUSDT/"
            names.append(path.split("/")[-2])         # -> "BTCUSDT"

        if root.find(NS + "IsTruncated").text == "true":
            marker = root.find(NS + "NextMarker").text
        else:
            return names

def list_files(prefix):
    """Return the full paths (keys) of all files directly under `prefix`."""
    keys = []
    marker = ""
    while True:
        params = {"delimiter": "/", "prefix": prefix}
        if marker:
            params["marker"] = marker
        root = ET.fromstring(get(BASE, params).content)

        for c in root.findall(NS + "Contents"):
            keys.append(c.find(NS + "Key").text)

        if root.find(NS + "IsTruncated").text == "true":
            marker = root.find(NS + "NextMarker").text
        else:
            return keys       


# ---------- Step A: list of USDT perpetuals (skip if already done) ----------
if not os.path.exists(SYMBOL_FILE):
    os.makedirs("data/raw", exist_ok=True)
    all_symbols = list_folders("data/futures/um/monthly/klines/")
    usdt = [s for s in all_symbols if s.endswith("USDT") and "_" not in s]
    with open(SYMBOL_FILE, "w") as f:
        f.write("\n".join(usdt))

with open(SYMBOL_FILE) as f:
    symbols = f.read().split("\n")
print("symbols:", len(symbols))


# ---------- Step B: which monthly files exist (skip if already done) ----------
if not os.path.exists(FILE_LIST):
    rows = []
    for i, sym in enumerate(symbols):
        kline_keys = list_files(f"data/futures/um/monthly/klines/{sym}/1h/")
        funding_keys = list_files(f"data/futures/um/monthly/fundingRate/{sym}/")

        for key in kline_keys:
            month = key[-11:-4]                       # "...-2020-01.zip" -> "2020-01"
            if key.endswith(".zip") and START <= month <= END:
                rows.append(f"klines,{sym},{key}")

        for key in funding_keys:
            month = key[-11:-4]
            if key.endswith(".zip") and START <= month <= END:
                rows.append(f"funding,{sym},{key}")

        if i % 50 == 0:
            print(f"listed {i}/{len(symbols)} symbols")

    with open(FILE_LIST, "w") as f:
        f.write("kind,symbol,key\n" + "\n".join(rows))

with open(FILE_LIST) as f:
    lines = f.read().split("\n")[1:]                 # [1:] skips the header line
print("kline files:", len([l for l in lines if l.startswith("klines")]))
print("funding files:", len([l for l in lines if l.startswith("funding")]))


# ---------- Step C: download all files (skip files we already have) ----------
DOWNLOAD_BASE = "https://data.binance.vision/"

def download(line):
    """Download one file from the list. Return 'ok', 'skip' or 'fail <key>'."""
    kind, sym, key = line.split(",")
    folder = f"data/raw/{kind}/{sym}"
    path = f"{folder}/{key.split('/')[-1]}"
    if os.path.exists(path):
        return "skip"
    os.makedirs(folder, exist_ok=True)
    try:
        r = get(DOWNLOAD_BASE + key)
    except requests.RequestException:
        return "fail " + key
    with open(path + ".part", "wb") as f:          # write to a temporary name first
        f.write(r.content)
    os.rename(path + ".part", path)                 # rename only when complete
    return "ok"


todo = [l for l in lines if l]                      # drop empty lines, just in case
results = []
for start in range(0, len(todo), 1000):
    chunk = todo[start:start + 1000]
    with ThreadPoolExecutor(max_workers=16) as pool:
        results += list(pool.map(download, chunk))
    print(f"{start + len(chunk)}/{len(todo)} files done")

failed = [r for r in results if r.startswith("fail")]
with open("data/raw/failed.txt", "w") as f:
    f.write("\n".join(failed))
print("ok:", results.count("ok"), " skip:", results.count("skip"), " fail:", len(failed))