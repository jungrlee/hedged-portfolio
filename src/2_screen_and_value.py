"""Systematic screen + valuation of the 300-stock universe (US / KR / JP).

Stage 1  multiples screen (all 300): value composite = mean within-market percentile of
         forward earnings yield, FCF yield and ROE / (P/B).  Loss-makers, NAV-type holding
         companies and REITs without AFFO data are out of scope.
Stage 2  full valuation of the top 30 per market + every name that already had a bespoke
         model.  One model per business type:
           Financials   justified P/B = (ROE - g) / (k - g)
           Cyclicals    justified P/B on a mid-cycle ROE (memory, shipping, steel, oil, ...)
           Everything else  10-yr earnings model: 5 yrs at capped consensus growth, 5-yr fade
                        to terminal g, payout = 1 - g/ROE; blended 50/50 with the same
                        growth path applied to free cash flow when FCF > 0.
         Hand-built models from the earlier version override the systematic value.
Stage 3  hurdle: upside >= 15 %.
As a check, the Stage-2 model is also run on every in-scope name, so we can see what the
Stage-1 screen threw away.
"""
import json
import numpy as np


RF = {"US": 0.0523, "KR": 0.0441, "JP": 0.0307}
ERP = {"US": 0.045, "KR": 0.055, "JP": 0.050}
GT = {"US": 0.030, "KR": 0.025, "JP": 0.015}
G_CAP, G_FLOOR = 0.10, -0.05
BETA_LO, BETA_HI = 0.8, 1.6
BROKER_ROE = 0.12
HURDLE = 0.15
TOP_PER_MARKET = 30

R = json.load(open("data/universe.json"))

# ---------------------------------------------------------------- classification
FIN = set("JPM BAC MS GS WFC C COF CB PGR BRK.B SCHW".split()
          + "105560 055550 086790 316140 024110 138040 032830 000810 005830 071050 005940 323410 016360 039490 006800 175330".split()
          + "8306 8316 8411 7182 8766 8725 6178 8750 8630 8308 8309 8604 8601 8591".split())
INSURER = set("CB PGR BRK.B 032830 000810 005830 8766 8725 8750 8630".split())
BROKER = set("MS GS SCHW 071050 005940 016360 039490 006800 138040 8604 8601".split())
CYC = {}   # code -> (mid-cycle ROE, label)
for c in "MU SNDK WDC STX 285A 000660 005930".split():
    CYC[c] = (0.14, "memory / storage")
for c in "011200 9101 9104".split():
    CYC[c] = (0.08, "container shipping")
for c in "005490 5401 010130 5713 5016".split():
    CYC[c] = (0.07, "steel / metals")
for c in "051910 4004".split():
    CYC[c] = (0.07, "commodity chemicals")
for c in "XOM CVX COP 1605".split():
    CYC[c] = (0.11, "oil & gas")
for c in "096770 010950 5020".split():
    CYC[c] = (0.08, "refining")
for c in "329180 009540 010140 042660".split():
    CYC[c] = (0.11, "shipbuilding")
CYC["003490"] = (0.07, "airline")
CYC["NEM"] = (0.10, "gold mining")
HOLDCO = set("402340 034730 003550 000880 267250 006260 180640 000150 028260 9984 078930".split())
NO_DATA = {"WELL"}                        # REIT: no AFFO in the data set
REIT = {"O", "VICI", "PLD"}

SECTOR_KW = [("Financials", ["financ", "bank", "insur", "capital market", "securities"]),
             ("Semis", ["semicon"]),
             ("Tech", ["software", "technolog", "internet", "it services", "cyber", "network", "information", "computing", "electronic", "research serv"]),
             ("Health", ["pharma", "health", "bio", "medical", "life science", "diagnos"]),
             ("Telecom", ["telecom"]),
             ("Utilities", ["utilit"]),
             ("Energy", ["energy", "oil", "gas"]),
             ("Materials", ["steel", "metal", "mining", "chemical", "materials", "gases", "rubber", "tire"]),
             ("Autos", ["auto"]),
             ("Staples", ["tobacco", "beverage", "staples", "food", "personal care", "consumer goods", "cosmetic"]),
             ("Real estate", ["real estate", "reit"]),
             ("Industrials", ["industr", "machin", "aerospace", "defense", "electrical", "shipbuild", "construction",
                              "transport", "logistic", "railroad", "shipping", "marine", "conglomerate", "trading", "security serv",
                              "staffing", "optical", "photograph"]),
             ("Consumer", ["retail", "restaurant", "entertain", "gaming", "travel", "apparel", "consumer", "airline", "hospital"])]
SECTOR_FIX = {"AAPL": "Tech", "AMZN": "Consumer", "META": "Tech", "GOOGL": "Tech", "MSFT": "Tech", "TSLA": "Autos",
              "STX": "Semis", "WDC": "Semis", "DELL": "Tech", "V": "Payments", "MA": "Payments", "PYPL": "Payments",
              "AXP": "Payments", "SPGI": "Financials", "BLK": "Financials", "BX": "Financials", "UBER": "Consumer",
              "GLW": "Tech", "APH": "Tech", "NEM": "Materials", "7974": "Consumer", "6758": "Tech", "6501": "Industrials",
              "006260": "Industrials", "007660": "Tech", "021240": "Consumer", "009830": "Energy", "6146": "Semis",
              "4689": "Tech", "9434": "Telecom", "8058": "Industrials", "9983": "Consumer", "4901": "Health",
              "002790": "Staples", "005930": "Semis", "402340": "Semis", "O": "Real estate", "VICI": "Real estate",
              "PLD": "Real estate", "WELL": "Real estate", "GEV": "Industrials", "BRK.B": "Financials", "1925": "Real estate",
              "8591": "Financials", "6178": "Financials", "5803": "Industrials", "5802": "Industrials", "5801": "Industrials",
              "001440": "Industrials", "353200": "Tech", "011070": "Tech", "009150": "Tech", "066570": "Tech",
              "373220": "Industrials", "006400": "Industrials", "003670": "Materials", "4062": "Semis", "7735": "Semis",
              "6723": "Semis", "000990": "Semis", "042700": "Semis", "278470": "Staples", "443060": "Industrials",
              "028050": "Industrials", "047040": "Industrials", "000720": "Industrials", "064350": "Industrials"}


def sector(r):
    if r["code"] in SECTOR_FIX:
        return SECTOR_FIX[r["code"]]
    ind = (r["industry"] or "").lower()
    for s, kws in SECTOR_KW:
        if any(k in ind for k in kws):
            return s
    return "Other"


def model_type(code):
    if code in HOLDCO:
        return "holdco"
    if code in NO_DATA:
        return "nodata"
    if code in REIT:
        return "reit"
    if code in FIN:
        return "fin"
    if code in CYC:
        return "cyc"
    return "gen"


def ke(m, b):
    return RF[m] + b * ERP[m]


# ---------------------------------------------------------------- models
def earnings_model(E1, roe, g1, gT, k, n1=5, n2=5):
    path = [g1] * n1 + list(np.linspace(g1, gT, n2 + 1)[1:]) + [gT]   # growth into year t+1
    E, pv = E1, 0.0
    for t in range(1, n1 + n2 + 1):
        gn = path[t - 1] if t - 1 < len(path) else gT
        pv += E * (1 - max(gn, 0) / roe) / (1 + k) ** t
        E *= 1 + gn
    tv = E * (1 - gT / roe) / (k - gT) / (1 + k) ** (n1 + n2)
    return pv + tv


def cash_model(C1, g1, gT, k, n1=5, n2=5):
    path = [g1] * n1 + list(np.linspace(g1, gT, n2 + 1)[1:])
    C, pv = C1, 0.0
    for t in range(1, n1 + n2 + 1):
        pv += C / (1 + k) ** t
        C *= 1 + path[t - 1]
    return pv + C / (k - gT) / (1 + k) ** (n1 + n2)


def value(r, dk=0.0, dx=0.0):
    m, c, p = r["market"], r["code"], r["price"]
    b_raw = r["beta"] if r["beta"] is not None else 1.0
    b = float(np.clip(b_raw, BETA_LO, BETA_HI))
    k, gT = ke(m, b) + dk, GT[m]
    mt = model_type(c)
    out = dict(k=k, beta=b, gT=gT, model=mt)
    eps_f = p / r["fpe"] if r["fpe"] and r["fpe"] > 0 else None
    eps_t = p / r["pe"] if r["pe"] and r["pe"] > 0 else None
    E1 = eps_f or eps_t
    if mt in ("holdco", "nodata", "reit"):
        return None, out
    if mt == "fin":
        if not r["pb"]:
            return None, out
        bv = p / r["pb"]
        roes = [x for x in (r["roe"], (r["pb"] / r["fpe"]) if r["fpe"] else None) if x is not None]
        roe = float(np.clip(np.mean(roes), 0.03, 0.25))
        if c in BROKER:
            roe = min(roe, BROKER_ROE)
        roe += dx
        out.update(roe=roe, method="Justified P/B",
                   note=f"ROE {roe:.1%} ({'capped, broker' if c in BROKER and roe == BROKER_ROE else 'trailing/fwd avg'}), k {k:.1%}, g {gT:.1%}")
        return bv * (roe - gT) / (k - gT), out
    if mt == "cyc":
        if not r["pb"]:
            return None, out
        roe, lab = CYC[c]
        roe += dx
        out.update(roe=roe, method="Mid-cycle justified P/B", note=f"{lab}: mid-cycle ROE {roe:.0%}, k {k:.1%}")
        return p / r["pb"] * (roe - gT) / (k - gT), out
    # general
    if E1 is None:
        return None, out
    if r["g3"] is not None:
        gc, gsrc = r["g3"], "consensus 3y"
    elif eps_f and eps_t:
        gc, gsrc = min(eps_f / eps_t - 1, 0.08), "trailing→fwd EPS"
    else:
        gc, gsrc = 0.03, "default"
    roe = r["roe"] if r["roe"] is not None else ((r["pb"] / r["fpe"]) if (r["pb"] and r["fpe"]) else 0.12)
    roe = float(np.clip(roe, 0.08, 0.30))
    g1 = 0.5 * gc + 0.5 * gT                       # shrink consensus halfway to terminal
    g1 = float(np.clip(g1, G_FLOOR, min(G_CAP, 0.6 * roe))) + dx
    gTf = min(gT, max(g1, 0.0))                     # shrinking businesses do not get market terminal growth
    ve = earnings_model(E1, roe, g1, gTf, k)
    fcf_ps = r["fcf"] / r["mcap"] * p if r["fcf"] and r["mcap"] else None
    if fcf_ps and fcf_ps > 0:
        c1 = min(fcf_ps, E1)                        # FCF leg never credited above earnings
        vc = cash_model(c1 * (1 + g1), g1, gTf, k)
        v = 0.5 * ve + 0.5 * vc
        how = "earnings/FCF blend"
    else:
        vc, v, how = None, ve, "earnings only (FCF ≤ 0)"
    out.update(roe=roe, g1=g1, gc=gc, gsrc=gsrc, gTf=gTf, v_earn=ve, v_fcf=vc,
               method="10-yr earnings/FCF model" if vc else "10-yr earnings model",
               note=f"{how}; g {g1:.1%} (½ {gsrc} {gc:.0%} + ½ terminal) → {gTf:.1%}; ROE {roe:.0%}; k {k:.1%}")
    return v, out


# ---------------------------------------------------------------- stage 1: screen
for r in R:
    r["sector"] = sector(r)
    r["mtype"] = model_type(r["code"])
    pos = (r["fpe"] and r["fpe"] > 0) or (r["pe"] and r["pe"] > 0)
    r["in_scope"] = bool(pos) and r["mtype"] not in ("holdco", "nodata")
    r["ey"] = 1 / r["fpe"] if r["fpe"] and r["fpe"] > 0 else (1 / r["pe"] if r["pe"] and r["pe"] > 0 else None)
    r["fy"] = 1 / r["pfcf"] if r["pfcf"] and r["pfcf"] > 0 and r["mtype"] != "fin" else None
    r["by"] = r["roe"] / r["pb"] if r["roe"] is not None and r["pb"] else None


def pct(vals):
    arr = np.array([v for v in vals if v is not None])
    return [None if v is None else float((arr < v).mean() + 0.5 * (arr == v).mean()) for v in vals]


for m in ("US", "KR", "JP"):
    S = [r for r in R if r["market"] == m and r["in_scope"]]
    for f in ("ey", "fy", "by"):
        for r, p_ in zip(S, pct([r[f] for r in S])):
            r["p_" + f] = p_
    for r in S:
        ps = [r["p_" + f] for f in ("ey", "fy", "by") if r["p_" + f] is not None]
        r["score"] = float(np.mean(ps)) if ps else None
    S.sort(key=lambda r: -(r["score"] or 0))
    for i, r in enumerate(S):
        r["rank"] = i + 1

# names with a hand-built model from the earlier version (code -> key in results46.json)
BESPOKE = {"UNH": "UNH", "CI": "CI", "CMCSA": "CMCSA", "VZ": "VZ", "PYPL": "PYPL", "ADBE": "ADBE", "CRM": "CRM",
           "MSFT": "MSFT", "GOOGL": "GOOGL", "JNJ": "JNJ", "BMY": "BMY", "CVX": "CVX", "MO": "MO", "C": "C",
           "BAC": "BAC", "PLD": "PLD", "O": "O", "VICI": "VICI", "T": "T", "GILD": "GILD", "MDT": "MDT",
           "005930": "SEC_C", "000660": "HYNIX", "105560": "KB", "086790": "HANA", "000270": "KIA", "005380": "HMC",
           "033780": "KTG", "015760": "KEPCO", "012330": "MOBIS", "035420": "NAVER", "017670": "SKT", "066570": "LGE",
           "012450": "HANWHA", "055550": "SHINHAN", "024110": "IBK", "005830": "DBINS", "086280": "GLOVIS",
           "016360": "SSEC", "005490": "POSCO", "7203": "TOYOTA", "9432": "NTT", "8306": "MUFG", "8316": "SMFG",
           "8766": "TOKIO", "8058": "MITSU", "2914": "JT", "7267": "HONDA"}
V46 = json.load(open("data/bespoke_valuations.json"))["val"]

for r in R:
    r["shortlist"] = bool(r["in_scope"] and (r.get("rank", 999) <= TOP_PER_MARKET or r["code"] in BESPOKE))
    v, info = value(r) if r["in_scope"] or r["code"] in REIT else (None, {})
    r["sys_value"] = v
    r["sys_upside"] = v / r["price"] - 1 if v else None
    r.update({"v_" + k: val for k, val in info.items()})
    if r["code"] in BESPOKE:
        b = V46[BESPOKE[r["code"]]]
        r["bespoke_key"] = BESPOKE[r["code"]]
        r["bespoke_upside"] = b["upside"]
        r["bespoke_method"] = b["method"]
    r["upside"] = r.get("bespoke_upside", r["sys_upside"]) if r["shortlist"] else None
    r["pass"] = bool(r["shortlist"] and r["upside"] is not None and round(r["upside"], 3) >= HURDLE)
    if v and r["shortlist"]:
        dxs = [-.02, 0, .02] if info["model"] == "gen" else [-.01, 0, .01]
        r["grid"] = dict(rows=[-.01, 0, .01], cols=dxs, rl="k", cl="g" if info["model"] == "gen" else "ROE",
                         v=[[(value(r, dk, dx)[0] or 0) / r["price"] - 1 for dx in dxs] for dk in [-.01, 0, .01]])
    r["check_pass"] = bool(r["in_scope"] and r["sys_upside"] is not None and r["sys_upside"] >= HURDLE)

# Samsung Electronics preferred (not in the data feed; bespoke model from the earlier version)
sp = V46["SEC_P"]
R.append(dict(market="KR", code="005935", name="Samsung Electronics Co., Ltd. (Pref.)", industry="Semiconductors",
              sector="Semis", mtype="cyc", price=sp["price"], beta=1.1, in_scope=True, shortlist=True, rank=None,
              score=None, sys_value=None, sys_upside=None, bespoke_key="SEC_P", bespoke_upside=sp["upside"],
              bespoke_method=sp["method"], upside=sp["upside"], **{"pass": round(sp["upside"], 3) >= HURDLE},
              check_pass=False, fpe=None, pe=None, pb=None, pfcf=None, roe=None, dy=None, g3=None, mcap=None))


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


json.dump(clean(R), open("data/screen_results.json", "w"), indent=0)

# ---------------------------------------------------------------- report
fun = {}
for m in ("US", "KR", "JP"):
    M = [r for r in R if r["market"] == m]
    fun[m] = dict(universe=sum(r["code"] != "005935" for r in M), in_scope=sum(r["in_scope"] for r in M),
                  valued=sum(r["shortlist"] for r in M), passed=sum(r["pass"] for r in M),
                  check_pass=sum(r["check_pass"] for r in M),
                  missed=[r["code"] for r in M if r["check_pass"] and not r["shortlist"]])
print(json.dumps(fun, indent=1))
for m in ("US", "KR", "JP"):
    print("\n==", m)
    for r in sorted([r for r in R if r["market"] == m and r["shortlist"]], key=lambda r: -(r["upside"] or -9)):
        su = r["sys_upside"]
        print(f"  {r['code']:7s} {r['name'][:26]:26s} {r['sector'][:11]:11s} {r['mtype']:4s} rk {str(r.get('rank')):>4s} "
              f"sys {'   NA ' if su is None else f'{su:+6.0%}'} "
              f"bes {'' if 'bespoke_upside' not in r else format(r['bespoke_upside'], '+.0%'):>5s} "
              f"{'PASS' if r['pass'] else ''}")
