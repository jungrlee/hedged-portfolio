"""Parse raw stockanalysis multiples (all.txt) into a clean table (universe.json)."""
import json, re
COLS = "market code name industry price mcap pe fpe pb pfcf roe dy beta fcf netcash g3".split()
MULT = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}

def num(s):
    s = s.strip().replace(",", "").replace("%", "").replace("¥", "").replace("₩", "").replace("$", "")
    if s in ("", "NA", "N/A", "-", "n/a", "None"): return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)([TBMK]?)", s)
    if not m: return None
    return float(m.group(1)) * MULT.get(m.group(2), 1)

rows = []
for line in open("data/screen_raw.txt"):
    p = [x.strip() for x in line.strip().split("|")]
    if len(p) != 16: continue
    d = dict(zip(COLS, p))
    for c in COLS[4:]:
        d[c] = num(d[c])
    for c in ("roe", "dy", "g3"):
        if d[c] is not None: d[c] /= 100
    rows.append(d)
json.dump(rows, open("data/universe.json", "w"), indent=0)
print(len(rows))
import collections
print(collections.Counter(r["market"] for r in rows))
for c in COLS[4:]:
    print(c, sum(r[c] is None for r in rows))
