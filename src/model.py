"""Version 3: screened universe (300 stocks, US / KR / JP) -> valuation -> two-pass optimisation.

Inputs : screen/screen_results.json  (multiples screen + systematic valuation, from screen/valuation.py)
         results46.json["val"]        (hand-built valuations carried over from the earlier version)
Output : results_v3.json
Base currency KRW (Korean investor). Prices as of 22-28 Sep 2026.
"""
import json
import numpy as np
from scipy.optimize import minimize

RF = {"US": 0.0523, "KR": 0.0441, "JP": 0.0307}
ERP = {"US": 0.045, "KR": 0.055, "JP": 0.050}
RF_KRW_CASH = 0.028
HURDLE = 0.15
ROOT = "/home/claude/pf/"

SCR = json.load(open("data/screen_results.json"))
V46 = json.load(open("data/bespoke_valuations.json"))["val"]

# ------------------------------------------------------------------ display names
SHORT = {"015760": ("KEPCO", "Korea Electric Power"), "005830": ("DBINS", "DB Insurance"),
         "024110": ("IBK", "Industrial Bank of Korea"), "259960": ("KRAFTON", "Krafton"),
         "175330": ("JBFG", "JB Financial Group"), "021240": ("COWAY", "Coway"), "032640": ("LGU", "LG Uplus"),
         "316140": ("WOORI", "Woori Financial Group"), "030200": ("KT", "KT Corp"),
         "161390": ("HANKOOK", "Hankook Tire & Technology"), "086280": ("GLOVIS", "Hyundai Glovis"),
         "000270": ("KIA", "Kia"), "086790": ("HANA", "Hana Financial Group"), "033780": ("KTG", "KT&G"),
         "055550": ("SHINHAN", "Shinhan Financial Group"), "071050": ("KIH", "Korea Investment Holdings"),
         "105560": ("KB", "KB Financial Group"), "005380": ("HMC", "Hyundai Motor"),
         "005935": ("SEC_P", "Samsung Electronics Pref."),
         "1605": ("INPEX", "Inpex"), "8725": ("MSAD", "MS&AD Insurance"), "8630": ("SOMPO", "Sompo Holdings"),
         "5401": ("NSTEEL", "Nippon Steel"), "8591": ("ORIX", "ORIX"), "8053": ("SUMITOMO", "Sumitomo Corp"),
         "4503": ("ASTELLAS", "Astellas Pharma"), "9104": ("MOL", "Mitsui O.S.K. Lines"), "9432": ("NTT", "NTT"),
         "8604": ("NOMURA", "Nomura Holdings"), "8750": ("DAIICHI", "Dai-ichi Life"), "5020": ("ENEOS", "ENEOS Holdings"),
         "9101": ("NYK", "Nippon Yusen (NYK)"), "8601": ("DAIWA", "Daiwa Securities"), "8002": ("MARUBENI", "Marubeni"),
         "7269": ("SUZUKI", "Suzuki Motor"), "7203": ("TOYOTA", "Toyota Motor (NYSE ADR)"),
         "8309": ("SMTH", "Sumitomo Mitsui Trust"),
         "CI": ("CI", "Cigna Group"), "UNH": ("UNH", "UnitedHealth Group"), "LMT": ("LMT", "Lockheed Martin"),
         "VICI": ("VICI", "VICI Properties"), "PYPL": ("PYPL", "PayPal"), "T": ("T", "AT&T"),
         "CVS": ("CVS", "CVS Health"), "ADBE": ("ADBE", "Adobe"), "CMCSA": ("CMCSA", "Comcast"),
         "VZ": ("VZ", "Verizon"), "O": ("O", "Realty Income"), "CB": ("CB", "Chubb"), "TMUS": ("TMUS", "T-Mobile US")}
TICKER_OVERRIDE = {"7203": "TM"}          # Toyota held through the NYSE ADR

cands = [r for r in SCR if r["pass"]]
missing = [r["code"] for r in cands if r["code"] not in SHORT]
assert not missing, missing

# ------------------------------------------------------------------ stock records
STK = []
for r in cands:
    key, nm = SHORT[r["code"]]
    m = r["market"]
    bes = r.get("bespoke_key")
    if bes:
        b = V46[bes]
        beta, up, method, inputs = b["beta"], b["upside"], b["method"], b["inputs"]
        price, value, ccy = b["price"], b["value"], b["ccy"]
    else:
        beta = r["v_beta"]
        up, method, inputs = r["sys_upside"], r["v_method"], r["v_note"]
        price, value = r["price"], r["sys_value"]
        ccy = {"US": "USD", "KR": "KRW", "JP": "JPY"}[m]
    reit = r["code"] in ("O", "VICI")
    STK.append(dict(key=key, code=r["code"], ticker=TICKER_OVERRIDE.get(r["code"], r["code"]), name=nm, country=m,
                    sleeve="Real assets" if reit else "Growth", kind="reit" if reit else "stock",
                    sector=r["sector"], mtype=r.get("mtype"), beta=float(beta), upside=float(up), method=method,
                    inputs=inputs, price=price, value=value, ccy=ccy, bespoke=bool(bes),
                    sys_upside=r.get("sys_upside"), screen_rank=r.get("rank"), score=r.get("score"),
                    pe=r.get("pe"), fpe=r.get("fpe"), pb=r.get("pb"), roe=r.get("roe"), dy=r.get("dy"),
                    pfcf=r.get("pfcf")))

# ------------------------------------------------------------------ ETFs / hedges (unchanged from earlier version)
ETF = [("IVV", "IVV", "iShares Core S&P 500 ETF", "US", "Growth"),
       ("USMV", "USMV", "iShares MSCI USA Min Vol Factor ETF", "US", "Growth"),
       ("XLU", "XLU", "Utilities Select Sector SPDR ETF", "US", "Growth"),
       ("VNQ", "VNQ", "Vanguard Real Estate ETF", "US", "Real assets"),
       ("IEF", "IEF", "iShares 7-10Y Treasury ETF", "US", "Hedge"),
       ("VTIP", "VTIP", "Vanguard Short-Term TIPS ETF", "US", "Hedge"),
       ("SGOV", "SGOV", "iShares 0-3M T-Bill ETF", "US", "Hedge"),
       ("IAU", "IAU", "iShares Gold Trust", "US", "Hedge"),
       ("DBMF", "DBMF", "iMGP DBi Managed Futures ETF", "US", "Hedge"),
       ("KMLM", "KMLM", "KFA Mount Lucas Managed Futures ETF", "US", "Hedge"),
       ("TAIL", "TAIL", "Cambria Tail Risk ETF", "US", "Hedge"),
       ("BTAL", "BTAL", "AGF US Market Neutral Anti-Beta ETF", "US", "Hedge"),
       ("PDBC", "PDBC", "Invesco Optimum Yield Diversified Commodity ETF", "US", "Hedge"),
       ("K200", "069500", "KODEX 200", "KR", "Growth"),
       ("KREIT", "329200", "TIGER REITs & Real Estate Infra", "KR", "Real assets"),
       ("KTB", "152380", "KODEX 10Y KTB Futures", "KR", "Hedge"),
       ("KTB3", "114260", "KODEX 3Y KTB", "KR", "Hedge"),
       ("USDF", "261240", "KODEX USD Futures", "KR", "Hedge"),
       ("KCD", "459580", "KODEX CD Rate Active", "KR", "Hedge"),
       ("KGOLD", "132030", "KODEX Gold Futures (H)", "KR", "Hedge"),
       ("KINV", "114800", "KODEX Inverse (KOSPI 200)", "KR", "Hedge"),
       ("TOPIX", "1306", "NEXT FUNDS TOPIX ETF", "JP", "Growth"),
       ("JREIT", "1343", "NEXT FUNDS REIT Index ETF", "JP", "Real assets"),
       ("JGB", "2561", "iShares Core Japan Govt Bond ETF", "JP", "Hedge")]
ETF_L = {"IVV": ({"US_EQ": 1.0}, .02), "USMV": ({"US_EQ": .7, "RATES": .2}, .04), "XLU": ({"US_EQ": .5, "RATES": .7}, .07),
         "VNQ": ({"US_EQ": .8, "RATES": 1.0}, .06), "IEF": ({"RATES": 1.0}, .01), "VTIP": ({"RATES": .2, "INFL": .08}, .015),
         "SGOV": ({}, .005), "IAU": ({"GOLD": 1.0}, .02), "DBMF": ({"US_EQ": -.1, "RATES": -.3, "INFL": .3}, .10),
         "KMLM": ({"US_EQ": -.1, "RATES": -.3, "INFL": .35}, .11), "TAIL": ({"US_EQ": -.35, "RATES": .8}, .05),
         "BTAL": ({"US_EQ": -.5}, .08), "PDBC": ({"INFL": 1.0, "US_EQ": .15}, .05),
         "K200": ({"US_EQ": .8, "KR_EQ": 1.0}, .04), "KREIT": ({"US_EQ": .3, "KR_EQ": .4, "RATES": .6}, .10),
         "KTB": ({"RATES": .7}, .03), "KTB3": ({"RATES": .3}, .01), "USDF": ({"FX": 1.0}, .005), "KCD": ({}, .003),
         "KGOLD": ({"GOLD": 1.0}, .02), "KINV": ({"US_EQ": -.8, "KR_EQ": -1.0}, .03),
         "TOPIX": ({"US_EQ": .8, "JP_EQ": 1.0}, .03), "JREIT": ({"US_EQ": .4, "JP_EQ": .4, "RATES": .5}, .12),
         "JGB": ({"RATES": .5}, .03)}
ETF_MU = {"IVV": .065, "USMV": .060, "XLU": .065, "VNQ": .070, "IEF": .050, "VTIP": .047, "SGOV": .042, "IAU": .040,
          "DBMF": .055, "KMLM": .055, "TAIL": .010, "BTAL": .020, "PDBC": .045, "K200": .085, "KREIT": .075,
          "KTB": .042, "KTB3": .033, "USDF": -.012, "KCD": .028, "KGOLD": .026, "KINV": -.030, "TOPIX": .075,
          "JREIT": .065, "JGB": .025}

# ------------------------------------------------------------------ factor model
F = ["US_EQ", "KR_EQ", "RATES", "INFL", "GOLD", "FX", "AUTO", "JP_EQ", "JPY", "KR_FIN", "JP_FIN"]
fvol = np.array([.16, .14, .07, .18, .15, .09, .12, .13, .11, .12, .13])
fcor = np.eye(len(F))


def fc(a, b, c):
    i, j = F.index(a), F.index(b)
    fcor[i, j] = fcor[j, i] = c


fc("US_EQ", "RATES", -0.10); fc("US_EQ", "INFL", 0.20); fc("US_EQ", "GOLD", 0.05)
fc("US_EQ", "FX", -0.35); fc("KR_EQ", "FX", -0.45); fc("RATES", "INFL", -0.30)
fc("RATES", "GOLD", 0.25); fc("RATES", "FX", 0.15); fc("INFL", "GOLD", 0.35); fc("GOLD", "FX", 0.10)
fc("JPY", "US_EQ", -0.35); fc("JPY", "KR_EQ", -0.40); fc("JPY", "FX", 0.55); fc("JPY", "RATES", 0.20)
fc("JPY", "GOLD", 0.20); fc("JPY", "JP_EQ", -0.30); fc("JP_EQ", "FX", -0.15)
fc("JP_FIN", "KR_FIN", 0.30); fc("JP_FIN", "RATES", -0.30); fc("KR_FIN", "RATES", -0.15)
Fcov = np.outer(fvol, fvol) * fcor
assert np.linalg.eigvalsh(Fcov).min() > 0

L46 = {"UNH": ({"US_EQ": .7}, .20), "CI": ({"US_EQ": .6}, .22), "CMCSA": ({"US_EQ": .8}, .20),
       "VZ": ({"US_EQ": .4, "RATES": .5}, .17), "PYPL": ({"US_EQ": 1.3}, .28), "ADBE": ({"US_EQ": 1.2}, .25),
       "O": ({"US_EQ": .6, "RATES": 1.2}, .13), "VICI": ({"US_EQ": .8, "RATES": .9}, .16),
       "T": ({"US_EQ": .35, "RATES": .5}, .17), "SEC_P": ({"US_EQ": 1.0, "KR_EQ": 1.2}, .22),
       "KB": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .13), "HANA": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .14),
       "KIA": ({"US_EQ": .8, "KR_EQ": 1.0, "AUTO": 1.0}, .17), "HMC": ({"US_EQ": .8, "KR_EQ": 1.0, "AUTO": 1.0}, .17),
       "KTG": ({"US_EQ": .2, "KR_EQ": .4}, .16), "KEPCO": ({"US_EQ": .3, "KR_EQ": .6, "INFL": -.3}, .25),
       "SHINHAN": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .13), "IBK": ({"US_EQ": .4, "KR_EQ": .8, "KR_FIN": 1.0}, .14),
       "DBINS": ({"US_EQ": .3, "KR_EQ": .6, "KR_FIN": .5}, .17), "GLOVIS": ({"US_EQ": .6, "KR_EQ": .9, "AUTO": .5}, .20),
       "TOYOTA": ({"US_EQ": .8, "JP_EQ": 1.0, "AUTO": .6}, .17), "NTT": ({"US_EQ": .3, "JP_EQ": .5}, .13)}
INSURERS = {"CB", "DBINS", "MSAD", "SOMPO", "DAIICHI"}
BROKERS = {"KIH", "NOMURA", "DAIWA"}
INFL_LD = {"INPEX": .6, "ENEOS": .4, "NSTEEL": .3, "MOL": .3, "NYK": .3, "SUMITOMO": .3, "MARUBENI": .3}
AUTO_LD = {"SUZUKI": 1.0, "HANKOOK": .5}


def loadings(s):
    if s["key"] in L46:
        return L46[s["key"]]
    k, m, sec = s["key"], s["country"], s["sector"]
    b = float(np.clip(s["beta"], .4, 1.6))
    ld = {"US_EQ": b} if m == "US" else {"US_EQ": .6 * b, ("KR_EQ" if m == "KR" else "JP_EQ"): b}
    idio = .20
    if sec == "Financials":
        ff = "KR_FIN" if m == "KR" else ("JP_FIN" if m == "JP" else None)
        if ff:
            ld[ff] = .5 if k in INSURERS else 1.0
        idio = .15 if k in INSURERS else (.20 if k in BROKERS else .13)
    if sec in ("Telecom", "Utilities"):
        ld["RATES"] = .5; idio = .15
    if k in INFL_LD:
        ld["INFL"] = INFL_LD[k]; idio = .25
    if k in AUTO_LD:
        ld["AUTO"] = AUTO_LD[k]; idio = .18
    if s.get("mtype") == "cyc":
        idio = max(idio, .25)
    if b > 1.3:
        idio += .05
    return ld, idio


A = [dict(key=e[0], ticker=e[1], name=e[2], country=e[3], sleeve=e[4], kind="etf") for e in ETF] + STK
A = [a for c in ("US", "KR", "JP") for sl in ("Growth", "Real assets", "Hedge") for a in A
     if a["country"] == c and a["sleeve"] == sl]


def ke(m, b):
    return RF[m] + b * ERP[m]


def alpha(up, h=3, shrink=.5, cap=.60):
    return (1 + shrink * min(up, cap)) ** (1 / h) - 1


def build(assets):
    keys = [a["key"] for a in assets]
    N = len(keys)
    B = np.zeros((N, len(F))); idio = np.zeros(N); mu = np.zeros(N)
    for i, a in enumerate(assets):
        ld, s_ = ETF_L[a["key"]] if a["kind"] == "etf" else loadings(a)
        for f_, v_ in ld.items():
            B[i, F.index(f_)] = v_
        if a["country"] == "US" or a["key"] == "TOYOTA":
            pass
        if a["country"] == "US":
            B[i, F.index("FX")] += 1.0
        if a["country"] == "JP":
            B[i, F.index("JPY")] += 1.0
        idio[i] = s_
        mu[i] = ETF_MU[a["key"]] if a["kind"] == "etf" else ke(a["country"], a["beta"]) + alpha(a["upside"])
    S = B @ Fcov @ B.T + np.diag(idio ** 2)
    return keys, B, idio, S, mu


def bounds_for(a, stock_lo):
    k_, kind = a["key"], a["kind"]
    if k_ == "IVV":
        return (.05, .12)
    if k_ in ("K200", "TOPIX"):
        return (.02, .06)
    if k_ in ("USMV", "XLU"):
        return (.01, .05)
    if kind == "stock":
        return (stock_lo, .03)
    if kind == "reit" or k_ in ("KREIT", "VNQ", "JREIT"):
        return (stock_lo if kind == "reit" else .01, .03)
    if k_ in ("SGOV", "KCD"):
        return (.01, .04)
    if k_ in ("TAIL", "BTAL", "USDF", "KINV"):
        return (.01, .045)
    return (.015, .07)


MKT_CAP = .60          # any split: no market floors, single-market ceiling only
GROUP_CAPS = [  # (label, predicate, cap)
    ("KR financials", lambda a: a["country"] == "KR" and a.get("sector") == "Financials", .09),
    ("JP financials", lambda a: a["country"] == "JP" and a.get("sector") == "Financials", .09),
    ("US financials", lambda a: a["country"] == "US" and a.get("sector") in ("Financials", "Payments"), .06),
    ("Telecoms (all markets)", lambda a: a.get("sector") == "Telecom", .08),
    ("Autos (all markets)", lambda a: a.get("sector") == "Autos", .08),
    ("US managed care / pharmacy", lambda a: a["key"] in ("UNH", "CI", "CVS"), .06),
    ("Energy & shipping", lambda a: a["key"] in ("INPEX", "ENEOS", "MOL", "NYK"), .05),
    ("Trading houses & steel", lambda a: a["key"] in ("SUMITOMO", "MARUBENI", "NSTEEL"), .05),
]


def make_cons(assets):
    ix = lambda pred: [i for i, a in enumerate(assets) if pred(a)]
    grow, real, hedge = ix(lambda a: a["sleeve"] == "Growth"), ix(lambda a: a["sleeve"] == "Real assets"), ix(lambda a: a["sleeve"] == "Hedge")
    cons = [{"type": "eq", "fun": lambda x: x.sum() - 1},
            {"type": "ineq", "fun": lambda x: x[grow].sum() - .45},
            {"type": "ineq", "fun": lambda x: .52 - x[grow].sum()},
            {"type": "ineq", "fun": lambda x: x[real].sum() - .06},
            {"type": "ineq", "fun": lambda x: .12 - x[real].sum()},
            {"type": "ineq", "fun": lambda x: x[hedge].sum() - .38}]
    for c in ("US", "KR", "JP"):
        idx = ix(lambda a, c=c: a["country"] == c)
        cons.append({"type": "ineq", "fun": lambda x, idx=idx: MKT_CAP - x[idx].sum()})
    for _, pred, cap in GROUP_CAPS:
        idx = ix(pred)
        if idx:
            cons.append({"type": "ineq", "fun": lambda x, idx=idx, cap=cap: cap - x[idx].sum()})
    return cons, grow, real, hedge


def optimise(assets, stock_lo, lam):
    keys, B, idio, S, mu = build(assets)
    N = len(keys)
    bnds = [bounds_for(a, stock_lo) for a in assets]
    cons, grow, real, hedge = make_cons(assets)

    def obj(x):
        sr = (x @ mu - RF_KRW_CASH) / np.sqrt(x @ S @ x)
        if lam == 0:
            return -sr
        rc = x * (S @ x); rc = rc / rc.sum()
        return -sr + lam * np.sum((rc - rc.mean()) ** 2) * N

    x0 = np.array([np.mean(b_) for b_ in bnds]); x0 /= x0.sum()
    res = minimize(obj, x0, bounds=bnds, constraints=cons, method="SLSQP", options={"maxiter": 5000, "ftol": 1e-12})
    return res, keys, B, idio, S, mu, bnds, cons, grow, real, hedge


# ---------------- pass 1: pick names by resampled max-Sharpe (Michaud-style) ----------------
# Expected returns are noisy, so a single max-Sharpe run is fragile. Re-solve 60 times with the
# stock expected returns perturbed by N(0, 3%) (ETFs N(0, 1%)); keep a stock if it gets >= 0.5%
# in at least half of the runs.
N_DRAW, SEL_MIN, SEL_FREQ = 60, .005, .5
_k, _B, _i, S1, mu1 = build(A)
b1 = [bounds_for(a, 0.0) for a in A]
c1, *_ = make_cons(A)
isstk = np.array([a["kind"] != "etf" for a in A])
rng = np.random.default_rng(7)
x0 = np.array([np.mean(b_) for b_ in b1]); x0 /= x0.sum()
W1 = []
for _d in range(N_DRAW):
    mu_d = mu1 + rng.normal(0, .03, len(mu1)) * isstk + rng.normal(0, .01, len(mu1)) * ~isstk
    r_ = minimize(lambda x: -(x @ mu_d - RF_KRW_CASH) / np.sqrt(x @ S1 @ x), x0, bounds=b1, constraints=c1,
                  method="SLSQP", options={"maxiter": 3000, "ftol": 1e-12})
    W1.append(r_.x)
W1 = np.array(W1)
freq = dict(zip(_k, (W1 >= SEL_MIN).mean(0)))
w1 = dict(zip(_k, W1.mean(0)))
res1, keys1, *_ = optimise(A, 0.0, 0.0)          # single un-perturbed run, for reference
w1_single = dict(zip(keys1, res1.x))
selected = [a for a in A if a["kind"] == "etf" or freq[a["key"]] >= SEL_FREQ]
dropped = [(a["key"], freq[a["key"]]) for a in A if a["kind"] != "etf" and freq[a["key"]] < SEL_FREQ]

# ---------------- pass 2: final weights on selected names (risk-parity penalty) ----------------
LAM = 0.5
res, keys, B, idio, S, m, bnds, cons, grow, real, hedge = optimise(selected, .008, LAM)
AS = selected
N = len(keys)
ix = {k: i for i, k in enumerate(keys)}
w = np.round(res.x * 400) / 400
w = np.clip(w, [b_[0] for b_ in bnds], [b_[1] for b_ in bnds])
w[ix["IEF"]] += 1 - w.sum()


def enforce_caps(w):
    groups = [([ix[a["key"]] for a in AS if pred(a)], cap) for _, pred, cap in GROUP_CAPS]
    groups += [([ix[a["key"]] for a in AS if a["country"] == c], MKT_CAP) for c in ("US", "KR", "JP")]
    groups += [(grow, .52), (real, .12)]
    for _ in range(200):
        bad = [(idx, cap) for idx, cap in groups if idx and w[idx].sum() > cap + 1e-9]
        if not bad:
            break
        idx, cap = bad[0]
        j = max((i for i in idx if w[i] - .0025 >= bnds[i][0] - 1e-12), key=lambda i: w[i])
        w[j] -= .0025
        w[ix["IEF"]] += .0025
    return w


w = enforce_caps(w)
vol = np.sqrt(np.diag(S))
corr = S / np.outer(vol, vol)


def stats(x):
    er, sd = x @ m, np.sqrt(x @ S @ x)
    rc = x * (S @ x) / (x @ S @ x)
    return er, sd, (er - RF_KRW_CASH) / sd, rc


er, sd, sr, rc = stats(w)
wb = np.zeros(N); wb[ix["IVV"]] = .3; wb[ix["K200"]] = .3; wb[ix["IEF"]] = .2; wb[ix["KTB"]] = .2
erb, sdb, srb, _ = stats(wb)
z, phi = 1.645, .10314
var95, cvar95 = -(er - z * sd), -(er - sd * phi / .05)
var95b, cvar95b = -(erb - z * sdb), -(erb - sdb * phi / .05)
beta_ivv = (w @ S[:, ix["IVV"]]) / S[ix["IVV"], ix["IVV"]]
beta_k200 = (w @ S[:, ix["K200"]]) / S[ix["K200"], ix["K200"]]
div_ratio = (w @ vol) / sd

frontier = []
for tgt in np.linspace(.05, .12, 15):
    r2 = minimize(lambda x: x @ S @ x, res.x, bounds=bnds,
                  constraints=cons + [{"type": "eq", "fun": lambda x, t=tgt: x @ m - t}],
                  method="SLSQP", options={"maxiter": 3000})
    if r2.success:
        frontier.append((float(np.sqrt(r2.fun)), float(tgt)))

# ------------------------------------------------------------------ stress tests
country = {a["key"]: a["country"] for a in AS}
SC = {
    "2022-style rate & inflation shock": (dict(US_EQ=-.18, KR_EQ=-.06, RATES=-.15, INFL=.20, GOLD=-.01, FX=.06, AUTO=0, JP_EQ=0.0, JPY=-.08, KR_FIN=0, JP_FIN=.05),
                                          dict(KMLM=.30, DBMF=.22, TAIL=-.08, BTAL=.16, VTIP=-.03, SGOV=.015, KCD=.02)),
    "2008-style credit crash": (dict(US_EQ=-.37, KR_EQ=-.12, RATES=.18, INFL=-.35, GOLD=.05, FX=.30, AUTO=-.10, JP_EQ=-.10, JPY=.50, KR_FIN=-.10, JP_FIN=-.15),
                                dict(KMLM=.18, DBMF=.20, TAIL=.15, BTAL=.15, SGOV=.02, KCD=.04)),
    "Memory downcycle, KRW weakens 15%": (dict(US_EQ=-.08, KR_EQ=-.12, RATES=.04, INFL=-.05, GOLD=.05, FX=.15, AUTO=0, JP_EQ=-.03, JPY=.12, KR_FIN=-.05, JP_FIN=-.03),
                                          dict(SEC_P=-.45, SGOV=.04, KCD=.03)),
    "Oil / Middle-East inflation spike": (dict(US_EQ=-.12, KR_EQ=-.05, RATES=-.08, INFL=.25, GOLD=.20, FX=.08, AUTO=0, JP_EQ=-.05, JPY=.03, KR_FIN=0, JP_FIN=0),
                                          dict(KMLM=.15, DBMF=.15, KEPCO=-.25, SGOV=.04, KCD=.03)),
    "AI-capex bust (tech −35%)": (dict(US_EQ=-.22, KR_EQ=-.08, RATES=.08, INFL=-.08, GOLD=.06, FX=.07, AUTO=0, JP_EQ=-.05, JPY=.08, KR_FIN=0, JP_FIN=-.03),
                                  dict(SEC_P=-.40, BTAL=.12, SGOV=.04, KCD=.03)),
    "Risk-on rally, KRW strengthens 15%": (dict(US_EQ=.12, KR_EQ=.10, RATES=.04, INFL=.05, GOLD=-.03, FX=-.15, AUTO=.05, JP_EQ=.05, JPY=-.12, KR_FIN=.03, JP_FIN=.03),
                                           dict(KMLM=.02, DBMF=.02, TAIL=-.06, BTAL=-.12, SGOV=.04, KCD=.03)),
}


def scen_ret(fs, ov):
    r = B @ np.array([fs[f_] for f_ in F])
    for k_, v_ in ov.items():
        if k_ in ix:
            r[ix[k_]] = v_ + (fs["FX"] if country[k_] == "US" else 0) + (fs["JPY"] if country[k_] == "JP" else 0)
    return r


stress = {nm: dict(port=float(w @ scen_ret(fs, ov)), bench=float(wb @ scen_ret(fs, ov))) for nm, (fs, ov) in SC.items()}

# ------------------------------------------------------------------ funnel
SCR_ = [r for r in SCR if r["code"] != "005935"]
funnel = {}
for c in ("US", "KR", "JP", "ALL"):
    M = [r for r in SCR_ if c == "ALL" or r["market"] == c]
    held_c = [a for a in AS if a["kind"] != "etf" and (c == "ALL" or a["country"] == c)]
    funnel[c] = dict(universe=len(M), in_scope=sum(r["in_scope"] for r in M),
                     valued=sum(r["shortlist"] for r in M) + (1 if c in ("KR", "ALL") else 0),
                     passed=sum(1 for a in STK if c == "ALL" or a["country"] == c),
                     held=len(held_c),
                     check_pass=sum(r["check_pass"] for r in M),
                     missed=[r["code"] for r in M if r["check_pass"] and not r["shortlist"]])
bes_pairs = [(r["sys_upside"], r["bespoke_upside"]) for r in SCR if r.get("bespoke_upside") is not None and r.get("sys_upside") is not None]
bp = np.array(bes_pairs)
rk = lambda v: np.argsort(np.argsort(v))
calib = dict(n=len(bp), median_gap=float(np.median(bp[:, 0] - bp[:, 1])), corr=float(np.corrcoef(bp[:, 0], bp[:, 1])[0, 1]),
             rank_corr=float(np.corrcoef(rk(bp[:, 0]), rk(bp[:, 1]))[0, 1]),
             same_side=float(np.mean((bp[:, 0] >= HURDLE) == (bp[:, 1] >= HURDLE))))

# ------------------------------------------------------------------ output
out_assets = []
for a in AS:
    i = ix[a["key"]]
    d = {k: a.get(k) for k in ("key", "ticker", "name", "country", "sleeve", "kind", "sector", "upside", "method", "inputs",
                               "price", "value", "ccy", "bespoke", "sys_upside", "screen_rank", "beta", "pe", "fpe", "pb",
                               "roe", "dy", "code")}
    d.update(weight=float(w[i]), mu=float(m[i]), vol=float(vol[i]), rc=float(rc[i]), w_pass1=float(w1[a["key"]]), sel_freq=float(freq[a["key"]]))
    out_assets.append(d)
cand_out = [dict(key=a["key"], name=a["name"], country=a["country"], sector=a["sector"], upside=a["upside"],
                 w_pass1=float(w1[a["key"]]), sel_freq=float(freq[a["key"]]), held=any(a["key"] == s["key"] for s in AS), method=a["method"],
                 bespoke=a["bespoke"]) for a in STK]
port = dict(assets=out_assets, candidates=cand_out, er=er, sd=sd, sharpe=sr, beta_ivv=beta_ivv, beta_k200=beta_k200,
            var95=var95, cvar95=cvar95, div_ratio=div_ratio,
            bench=dict(er=erb, sd=sdb, sharpe=srb, var95=var95b, cvar95=cvar95b), stress=stress, frontier=frontier,
            opt_ok=bool(res.success), pass1_ok=bool(res1.success), factors=F, fvol=fvol.tolist(), loadings=B.tolist(),
            corr=corr.tolist(), rf=RF_KRW_CASH, funnel=funnel, calib=calib, group_caps=[(g[0], g[2]) for g in GROUP_CAPS],
            mkt_cap=MKT_CAP, lam=LAM, sel_min=SEL_MIN, sel_freq=SEL_FREQ, n_draw=N_DRAW)


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


json.dump(clean(dict(port=port)), open("data/results.json", "w"), indent=1)

if __name__ == "__main__":
    print("funnel", json.dumps(funnel))
    print("calib", calib)
    print("pass1 ok", res1.success, "pass2 ok", res.success, "sum", round(w.sum(), 4))
    print("dropped in pass 1:", ", ".join(f"{k} {v:.0%}" for k, v in dropped))
    for a in AS:
        i = ix[a["key"]]
        print(f"  {a['key']:9s} {a['country']} {a['sleeve']:11s} {a.get('sector') or '':12s} w {w[i]:6.2%} mu {m[i]:6.1%} vol {vol[i]:5.1%} rc {rc[i]:6.1%}"
              + (f" up {a['upside']:+.0%}" if a['kind'] != 'etf' else ""))
    tot = lambda pred: sum(w[ix[a['key']]] for a in AS if pred(a))
    print(f"Growth {tot(lambda a: a['sleeve']=='Growth'):.1%} Real {tot(lambda a: a['sleeve']=='Real assets'):.1%} Hedge {tot(lambda a: a['sleeve']=='Hedge'):.1%}")
    print("US {:.1%} KR {:.1%} JP {:.1%}".format(*[tot(lambda a, c=c: a['country'] == c) for c in ('US', 'KR', 'JP')]))
    print("stocks by market:", {c: sum(1 for a in AS if a['kind'] != 'etf' and a['country'] == c) for c in ('US', 'KR', 'JP')})
    print(f"E[R] {er:.2%} vol {sd:.2%} SR {sr:.2f} betaIVV {beta_ivv:.2f} betaK200 {beta_k200:.2f} DR {div_ratio:.2f}")
    print(f"Bench E[R] {erb:.2%} vol {sdb:.2%} SR {srb:.2f}; VaR {var95:.2%} CVaR {cvar95:.2%}")
    for k_, s_ in stress.items():
        print(f"  {k_:36s} port {s_['port']:+.1%}  bench {s_['bench']:+.1%}")
