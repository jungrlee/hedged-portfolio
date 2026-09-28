<<<<<<< HEAD
"""Version 3: screened universe (300 stocks, US / KR / JP) -> valuation -> two-pass optimisation.

Inputs : screen/screen_results.json  (multiples screen + systematic valuation, from screen/valuation.py)
         results46.json["val"]        (hand-built valuations carried over from the earlier version)
Output : results_v3.json
Base currency KRW (Korean investor). Prices as of 22-28 Sep 2026.
=======
"""46-asset hedged portfolio: 22 US + 19 Korea + 5 Japan (Toyota held via NYSE ADR). Base currency KRW (Korean investor).
Valuation per stock, factor-model covariance, constrained optimisation, factor stress tests.
Prices as of 22-26 Sep 2026. Money amounts: USD bn / KRW tn (조).
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
"""
import json
import numpy as np
from scipy.optimize import minimize

<<<<<<< HEAD
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
=======
RF_US, ERP_US = 0.0523, 0.045
RF_KR, ERP_KR = 0.0441, 0.055
RF_JP, ERP_JP = 0.0307, 0.050    # JGB 10y (25 Sep 2026); Japan ERP assumption
RF_KRW_CASH = 0.028          # assumed KRW CD-rate (Sharpe hurdle for a KRW investor)


def ke(rf, b, erp):
    return rf + b * erp


def fade_dcf(rev0, g0, g1, m0, m1, W, G, nd, sh, n=10):
    gs, ms = np.linspace(g0, g1, n), np.linspace(m0, m1, n)
    rev, pv = rev0, 0.0
    for t in range(n):
        rev *= 1 + gs[t]
        f = rev * ms[t]
        pv += f / (1 + W) ** (t + 1)
    tv = f * (1 + G) / (W - G) / (1 + W) ** n
    return (pv + tv - nd) / sh


def two_stage(cf0, g1, n1, g2, k):
    pv, c = 0.0, cf0
    for t in range(1, n1 + 1):
        c *= 1 + g1
        pv += c / (1 + k) ** t
    return pv + c * (1 + g2) / (k - g2) / (1 + k) ** n1


def implied(fn, price, lo=0.04, hi=0.20):
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fn(mid) > price else (lo, mid)
    return mid


V = {}   # valuation results


def put(key, name, ccy, price, value, method, inputs, held, beta=None, grid=None, extra=None):
    d = dict(name=name, ccy=ccy, price=price, value=value, upside=value / price - 1, method=method,
             inputs=inputs, held=held, beta=beta)
    if grid:
        d["grid"] = grid
    if extra:
        d.update(extra)
    V[key] = d


# ============================== US STOCKS (held) ==============================
# UNH — 10y fade FCFF
b = 0.80
W = 0.85 * ke(RF_US, b, ERP_US) + 0.15 * 0.056 * 0.79
f_unh = lambda w_, G=0.03: fade_dcf(460, .06, .04, .045, .055, w_, G, 41.86, 349.53 / 376.59)
put("UNH", "UnitedHealth Group", "USD", 376.59, f_unh(W), "10-yr FCFF DCF",
    f"Rev $460bn; FCF margin 4.5%→5.5% (2019-23 avg ≈7%); WACC {W*100:.1f}%, g 3%", True, b,
    grid=dict(rows=[W - .01, W, W + .01], cols=[.025, .03, .035], rl="WACC", cl="g",
              v=[[f_unh(w_, g) for g in [.025, .03, .035]] for w_ in [W - .01, W, W + .01]]),
    extra=dict(implied_wacc=implied(f_unh, 376.59)))

# CI — two-stage FCFE: 5y +4% then 0% (PBM-reform haircut)
b = 0.70; k = ke(RF_US, b, ERP_US)
f_ci = lambda k_, g2=0.0: two_stage(8.0, .04, 5, g2, k_) / 72.95 * 274.47
put("CI", "Cigna Group", "USD", 274.47, f_ci(k), "2-stage FCFE",
    f"FCF $8.0bn (11% yield); +4%/yr 5 yrs then 0% forever; Ke {k*100:.1f}%", True, b,
    grid=dict(rows=[k - .01, k, k + .01], cols=[-.02, 0.0, .02], rl="Ke", cl="g₂",
              v=[[f_ci(k_, g) for g in [-.02, 0, .02]] for k_ in [k - .01, k, k + .01]]))

# CMCSA — declining perpetuity FCFE
b = 0.75; k = ke(RF_US, b, ERP_US)
f_cm = lambda k_, g=-0.02: 12.70 * (1 + g) / (k_ - g) / 94.46 * 21.91
put("CMCSA", "Comcast", "USD", 21.91, f_cm(k), "Declining-perpetuity FCFE",
    f"FCFE $12.7bn (13.4% yield); −2%/yr forever; Ke {k*100:.1f}%", True, b,
    grid=dict(rows=[k - .01, k, k + .01], cols=[-.04, -.02, 0.0], rl="Ke", cl="g",
              v=[[f_cm(k_, g) for g in [-.04, -.02, 0]] for k_ in [k - .01, k, k + .01]]))

# VZ — zero-growth FCFE
b = 0.45; k = ke(RF_US, b, ERP_US)
f_vz = lambda k_, g=0.0: 18.0 * (1 + g) / (k_ - g) / 207.82 * 47.08
put("VZ", "Verizon", "USD", 47.08, f_vz(k), "Zero-growth FCFE",
    f"FCFE ≈$18bn (OCF $37.1bn − capex); 0% growth; Ke {k*100:.1f}%", True, b,
    grid=dict(rows=[k - .01, k, k + .01], cols=[-.01, 0.0, .01], rl="Ke", cl="g",
              v=[[f_vz(k_, g) for g in [-.01, 0, .01]] for k_ in [k - .01, k, k + .01]]))

# PYPL — FCFE perpetuity, low growth
b = 1.17; k = ke(RF_US, b, ERP_US)
f_py = lambda k_, g=0.015: 5.6 * (1 + g) / (k_ - g) / 45.05 * 55.04
put("PYPL", "PayPal", "USD", 55.04, f_py(k), "Low-growth FCFE",
    f"FCF $5.6bn FY25 (12% yield); g 1.5%; Ke {k*100:.1f}%", True, b,
    grid=dict(rows=[k - .01, k, k + .01], cols=[0.0, .015, .03], rl="Ke", cl="g",
              v=[[f_py(k_, g) for g in [0, .015, .03]] for k_ in [k - .01, k, k + .01]]))

# ADBE — 10y fade, margin compression from AI competition
b = 1.10; W = ke(RF_US, b, ERP_US)
sh_ad = 102.35 / 263.14
f_ad = lambda w_, G=0.01: fade_dcf(26.6, .08, 0.0, .38, .30, w_, G, 1.4, sh_ad)
put("ADBE", "Adobe", "USD", 240.69, f_ad(W), "10-yr FCFF DCF (AI-disruption case)",
    f"Rev $26.6bn; growth 8%→0%; FCF margin 38%→30%; g 1%; WACC {W*100:.1f}%", True, b,
    grid=dict(rows=[W - .01, W, W + .01], cols=[0.0, .01, .02], rl="WACC", cl="g",
              v=[[f_ad(w_, g) for g in [0, .01, .02]] for w_ in [W - .01, W, W + .01]]))

# CRM
b = 1.10; W = ke(RF_US, b, ERP_US) - 0.003
f_cr = lambda w_, G=0.02: fade_dcf(45.6, .09, .02, .35, .33, w_, G, 31.0, 211.96 / 234.02)
put("CRM", "Salesforce", "USD", 234.02, f_cr(W), "10-yr FCFF DCF",
    f"Rev $45.6bn TTM; growth 9%→2%; FCF margin 35%→33%; WACC {W*100:.1f}%", False, b,
    grid=dict(rows=[W - .01, W, W + .01], cols=[.015, .02, .025], rl="WACC", cl="g",
              v=[[f_cr(w_, g) for g in [.015, .02, .025]] for w_ in [W - .01, W, W + .01]]))

# ============================== US STOCKS (rejected) ==============================
for tk, nm, price, rev, g0, g1, m0, m1, b, nd, sh in [
        ("MSFT", "Microsoft", 516.17, 331.8, .16, .04, .22, .33, 1.00, 51.97, 7.45),
        ("GOOGL", "Alphabet", 343.92, 445.9, .15, .04, .18, .27, 1.15, -121.68, 4150 / 343.92),
        ("JNJ", "Johnson & Johnson", 271.22, 97.8, .06, .035, .173, .21, .55, 28.28, 640.67 / 271.22)]:
    W = ke(RF_US, b, ERP_US) - 0.002
    fn = lambda w_, a=(rev, g0, g1, m0, m1, nd, sh): fade_dcf(a[0], a[1], a[2], a[3], a[4], w_, .035, a[5], a[6])
    put(tk, nm, "USD", price, fn(W), "10-yr FCFF DCF (generous margins)", "", False, b,
        extra=dict(implied_wacc=implied(fn, price)))
k = ke(RF_US, .5, ERP_US)
put("BMY", "Bristol-Myers Squibb", "USD", 62.86, two_stage(11.4, -.04, 5, 0.0, k) / 136.47 * 62.86,
    "FCFE, patent-cliff decline", "FCF $11.4bn, −4%/yr 5 yrs then flat", False, .5)
k = ke(RF_US, .9, ERP_US)
cvx_eq = 24.0 * 1.01 / (k - .01) + 8 / (1 + k) + 8 / (1 + k) ** 2 - 40
put("CVX", "Chevron", "USD", 205.17, cvx_eq / 2.0, "Mid-cycle FCF ($70 oil)", "", False, .9)
k = ke(RF_US, .55, ERP_US)
put("MO", "Altria", "USD", 68.72, 5.66 * 0.99 / (k + .01), "Declining earnings perpetuity", "", False, .55)
for tk, nm, price, pb, roe, b in [("C", "Citigroup", 134.28, 1.19, 1.19 / 10.22, 1.36),
                                  ("BAC", "Bank of America", 57.96, 1.51, 1.51 / 11.70, .82)]:
    k = ke(RF_US, b, ERP_US)
    put(tk, nm, "USD", price, (roe - .03) / (k - .03) * price / pb, "Justified P/B", "", False, b)
k = ke(RF_US, .85, ERP_US)
put("UPS", "UPS", "USD", 93.96, 5.56 * 1.01 / (k - .01) / 88.68 * 93.96, "FCFE perpetuity", "", False, .85)
put("PLD", "Prologis", "USD", 133.03, two_stage(6.26 * .87, .045, 5, .03, ke(RF_US, .95, ERP_US)),
    "2-stage AFFO", "", False, .95)

# ============================== US REITs ==============================
for tk, nm, price, affo, b, div in [("O", "Realty Income", 55.41, 4.445, .75, 3.26),
                                    ("VICI", "VICI Properties", 23.71, 2.685 / 1.068, .90, 1.84)]:
    k = ke(RF_US, b, ERP_US)
    fn = lambda k_, g2=0.015, a=affo: two_stage(a, .02, 5, g2, k_)
    put(tk, nm, "USD", price, fn(k), "2-stage AFFO discount (organic growth only)",
        f"AFFO ${affo:.2f} (P/AFFO {price/affo:.1f}x); g 2%→1.5%; k {k*100:.1f}%", True, b,
        grid=dict(rows=[k - .01, k, k + .01], cols=[.005, .015, .025], rl="k", cl="g₂",
                  v=[[fn(k_, g) for g in [.005, .015, .025]] for k_ in [k - .01, k, k + .01]]),
        extra=dict(div_yield=div / price, p_affo=price / affo))
V["VICI"]["stress_value"] = two_stage(2.685 / 1.068 * .85, .02, 5, .015, ke(RF_US, .9, ERP_US))

# ============================== KOREA STOCKS ==============================
# Samsung Electronics — normalised-cycle DCF, bought through the preferred share
sh_sec = 1674.9e3 / 286.5 / 1e3
w_s = ke(RF_KR, 1.10, ERP_KR)


def cycle_dcf(op_path, mid, W, net_cash, sh_bn, q4_op, tax=.22, Gt=.025):
    ops = op_path + [0.5 * (op_path[-1] + mid), mid]
    reinv = [.40] * len(op_path) + [.375, .35]
    fcfs = [o * (1 - tax) * (1 - r) for o, r in zip(ops, reinv)]
    pv = q4_op * .3 * (1 - tax) * .6 + sum(f / (1 + W) ** (t + 1) for t, f in enumerate(fcfs))
    tv = mid * (1 - tax) * .65 * (1 + Gt) / (W - Gt) / (1 + W) ** len(fcfs)
    return (pv + tv + net_cash) * 1e12 / (sh_bn * 1e9)


sam = lambda mid, W=w_s: cycle_dcf([499, 469], mid, W, 150, sh_sec, 362)
scen = {"Bear": sam(150), "Base": sam(200), "Bull": sam(260)}
put("SEC_P", "Samsung Electronics Pref.", "KRW", 222000, scen["Base"] * .9,
    "Normalised-cycle DCF, −10% no-vote haircut",
    f"OP ₩499tn/469tn (27-28E) → mid-cycle ₩200tn; WACC {w_s*100:.1f}%", True, 1.10,
    grid=dict(rows=[w_s - .01, w_s, w_s + .01], cols=[150, 200, 260], rl="WACC", cl="Mid-cycle OP ₩tn",
              v=[[sam(m, W_) * .9 for m in [150, 200, 260]] for W_ in [w_s - .01, w_s, w_s + .01]]),
    extra=dict(scen=scen, pref_disc=1 - 222000 / 286500, common_value=scen["Base"]))
put("SEC_C", "Samsung Electronics Common", "KRW", 286500, scen["Base"], "Normalised-cycle DCF", "", False, 1.1)
sh_hx = 1360.9e3 / 1863 / 1e3
put("HYNIX", "SK Hynix", "KRW", 1863000,
    cycle_dcf([386, 383], 150, ke(RF_KR, 1.3, ERP_KR), 50, sh_hx, 265), "Normalised-cycle DCF", "", False, 1.3)


def jpb(price, pb, roe, b, g):
    k_ = ke(RF_KR, b, ERP_KR)
    return (roe - g) / (k_ - g) * price / pb, k_


for tk, nm, price, pb, roe, b, g, note in [
        ("KB", "KB Financial Group", 173200, 1.01, 1.01 / 9.41, .9, .03, "ROE 10.7% (P/B÷P/E)"),
        ("HANA", "Hana Financial Group", 133100, 0.76, 0.76 / 8.23, .9, .03, "ROE 9.2% (P/B÷P/E)"),
        ("KIA", "Kia", 118500, 0.71, 0.10, 1.0, .025, "Normalised ROE 10% (trailing 10.8%)"),
        ("HMC", "Hyundai Motor", 357000, 0.76, 0.09, 1.0, .025, "Normalised ROE 9% (trailing 6.5%)"),
        ("KTG", "KT&G", 174300, 1.95, 0.141, .5, .025, "ROE 14.1%"),
        ("KEPCO", "Korea Electric Power", 30250, 0.41, 0.07, .6, .01, "Normalised ROE 7% (trailing 15.9%)")]:
    v_, k_ = jpb(price, pb, roe, b, g)
    bv = price / pb
    fn = lambda r_, kk, g=g, bv=bv: (r_ - g) / (kk - g) * bv
    put(tk, nm, "KRW", price, v_, "Justified P/B = (ROE−g)/(k−g)",
        "%s; k %.1f%%; g %.1f%%" % (note, k_ * 100, g * 100), True, b,
        grid=dict(rows=[roe - .02, roe, roe + .02] if tk == "KEPCO" else [roe - .01, roe, roe + .01],
                  cols=[k_ - .01, k_, k_ + .01], rl="ROE", cl="k",
                  v=[[fn(r_, kk) for kk in [k_ - .01, k_, k_ + .01]]
                     for r_ in ([roe - .02, roe, roe + .02] if tk == "KEPCO" else [roe - .01, roe, roe + .01])]),
        extra=dict(roe=roe, k=k_, pb=pb, jpb=(roe - g) / (k_ - g)))

# Korea rejected
v_, _ = jpb(379000, .65, .65 / 9.51, 1.0, .025)
put("MOBIS", "Hyundai Mobis", "KRW", 379000, v_, "Justified P/B", "", False, 1.0)
put("NAVER", "NAVER", "KRW", 196100, two_stage(12552, .05, 5, .03, ke(RF_KR, 1.1, ERP_KR)), "2-stage EPS", "", False, 1.1)
put("SKT", "SK Telecom", "KRW", 88200, 3540 * 1.01 / (ke(RF_KR, .5, ERP_KR) - .01), "DDM", "", False, .5)
put("LGE", "LG Electronics", "KRW", 210500, 10000 * 1.03 / (ke(RF_KR, 1.1, ERP_KR) - .03),
    "Normalised EPS ₩10,000 perpetuity", "", False, 1.1)
put("HANWHA", "Hanwha Aerospace", "KRW", 1072000,
    two_stage(1072000 / 26.73, .15, 5, .03, ke(RF_KR, 1.1, ERP_KR)), "2-stage EPS (15% growth)", "", False, 1.1)


# ============================== NEW US NAMES ==============================
b = 0.45; k = ke(RF_US, b, ERP_US)
f_t = lambda k_, g=0.0: 18.0 * (1 + g) / (k_ - g) / 177.41 * 25.38
put("T", "AT&T", "USD", 25.38, f_t(k), "Zero-growth FCFE",
    f"2026 FCF guidance $18bn+ (10% yield); 0% growth; Ke {k*100:.1f}%", True, b,
    grid=dict(rows=[k - .01, k, k + .01], cols=[-.01, 0.0, .01], rl="Ke", cl="g",
              v=[[f_t(k_, g) for g in [-.01, 0, .01]] for k_ in [k - .01, k, k + .01]]))
put("GILD", "Gilead Sciences", "USD", 150.93, two_stage(9.77, .03, 5, .01, ke(RF_US, .5, ERP_US)) / 181.46 * 150.93,
    "2-stage FCFE", "", False, .5)
put("MDT", "Medtronic", "USD", 88.64, 5.5 * 1.03 / (ke(RF_US, .5, ERP_US) - .03) / 116.03 * 88.64,
    "FCFE perpetuity (normalised $5.5bn)", "", False, .5)

# ============================== NEW KOREA NAMES ==============================
for tk, nm, price, pb, roe, b, g, note in [
        ("SHINHAN", "Shinhan Financial Group", 109300, 0.86, 0.86 / 8.81, .9, .03, "ROE 9.8% (P/B÷P/E)"),
        ("IBK", "Industrial Bank of Korea", 20400, 0.43, 0.43 / 5.81, .7, .02, "ROE 7.4% (P/B÷P/E)"),
        ("DBINS", "DB Insurance", 184600, 0.80, 0.80 / 7.36, .6, .025, "ROE 10.9% (P/B÷P/E)"),
        ("GLOVIS", "Hyundai Glovis", 196900, 1.35, 1.35 / 8.85, .9, .03, "ROE 15.3% (P/B÷P/E)")]:
    v_, k_ = jpb(price, pb, roe, b, g)
    bv = price / pb
    fn = lambda r_, kk, g=g, bv=bv: (r_ - g) / (kk - g) * bv
    put(tk, nm, "KRW", price, v_, "Justified P/B = (ROE−g)/(k−g)",
        "%s; k %.1f%%; g %.1f%%" % (note, k_ * 100, g * 100), True, b,
        grid=dict(rows=[roe - .01, roe, roe + .01], cols=[k_ - .01, k_, k_ + .01], rl="ROE", cl="k",
                  v=[[fn(r_, kk) for kk in [k_ - .01, k_, k_ + .01]] for r_ in [roe - .01, roe, roe + .01]]),
        extra=dict(roe=roe, k=k_, pb=pb, jpb=(roe - g) / (k_ - g)))
v_, _ = jpb(91100, .94, .11, 1.2, .03)
put("SSEC", "Samsung Securities", "KRW", 91100, v_, "Justified P/B (normalised ROE 11%)", "", False, 1.2)
v_, _ = jpb(311500, .41, .06, 1.2, .02)
put("POSCO", "POSCO Holdings", "KRW", 311500, v_, "Justified P/B (normalised ROE 6%)", "", False, 1.2)

# ============================== JAPAN ==============================
def jpe(eps, roe, g, k_):
    """Justified value from earnings: EPS × payout × (1+g)/(k−g), payout = 1 − g/ROE."""
    return eps * (1 - g / roe) * (1 + g) / (k_ - g)


for tk, nm, price, eps, roe, g, b, note, held in [
        ("TOYOTA", "Toyota Motor", 3025, 3025 / 10.82, .10, .02, 1.0, "Fwd EPS ¥280, ROE 10%", True),
        ("NTT", "NTT", 168.8, 168.8 / 13.05, .11, .01, .6, "Fwd EPS ¥12.9, ROE 11%", True),
        ("MUFG", "Mitsubishi UFJ", 23.48, 23.48 / 14.26, .11, .02, 1.1, "", False),
        ("SMFG", "Sumitomo Mitsui FG", 6938, 6938 / 14.39, .11, .02, 1.1, "", False),
        ("TOKIO", "Tokio Marine", 8214, 8214 / 17.10, .13, .03, .8, "", False),
        ("MITSU", "Mitsubishi Corp", 31.24, 31.24 / 20.94, .10, .02, 1.0, "", False),
        ("JT", "Japan Tobacco", 6886, 6886 / 17.87, .12, 0.0, .5, "", False),
        ("HONDA", "Honda Motor", 1695, 1695 / 18.89, .06, .015, 1.0, "", False)]:
    k_ = ke(RF_JP, b, ERP_JP)
    fn = lambda kk, gg, eps=eps, roe=roe: jpe(eps, roe, gg, kk)
    grid = dict(rows=[k_ - .01, k_, k_ + .01], cols=[g - .01, g, g + .01], rl="k", cl="g",
                v=[[fn(kk, gg) for gg in [g - .01, g, g + .01]] for kk in [k_ - .01, k_, k_ + .01]]) if held else None
    put(tk, nm, "JPY", price, fn(k_, g), "Justified P/E (ROE-based payout)",
        f"{note}; g {g*100:.0f}%; k {k_*100:.1f}%" if held else "", held, b, grid=grid)

# ============================== ASSET UNIVERSE ==============================
A = [  # key, ticker, name, country, sleeve, kind
    ("IVV", "IVV", "iShares Core S&P 500 ETF", "US", "Growth", "etf"),
    ("UNH", "UNH", "UnitedHealth Group", "US", "Growth", "stock"),
    ("CI", "CI", "Cigna Group", "US", "Growth", "stock"),
    ("CMCSA", "CMCSA", "Comcast", "US", "Growth", "stock"),
    ("VZ", "VZ", "Verizon", "US", "Growth", "stock"),
    ("PYPL", "PYPL", "PayPal", "US", "Growth", "stock"),
    ("ADBE", "ADBE", "Adobe", "US", "Growth", "stock"),
    ("USMV", "USMV", "iShares MSCI USA Min Vol Factor ETF", "US", "Growth", "etf"),
    ("O", "O", "Realty Income", "US", "Real assets", "reit"),
    ("VICI", "VICI", "VICI Properties", "US", "Real assets", "reit"),
    ("IEF", "IEF", "iShares 7-10Y Treasury ETF", "US", "Hedge", "etf"),
    ("VTIP", "VTIP", "Vanguard Short-Term TIPS ETF", "US", "Hedge", "etf"),
    ("SGOV", "SGOV", "iShares 0-3M T-Bill ETF", "US", "Hedge", "etf"),
    ("IAU", "IAU", "iShares Gold Trust", "US", "Hedge", "etf"),
    ("DBMF", "DBMF", "iMGP DBi Managed Futures ETF", "US", "Hedge", "etf"),
    ("TAIL", "TAIL", "Cambria Tail Risk ETF", "US", "Hedge", "etf"),
    ("BTAL", "BTAL", "AGF US Market Neutral Anti-Beta ETF", "US", "Hedge", "etf"),
    ("PDBC", "PDBC", "Invesco Optimum Yield Diversified Commodity ETF", "US", "Hedge", "etf"),
    ("K200", "069500", "KODEX 200", "KR", "Growth", "etf"),
    ("SEC_P", "005935", "Samsung Electronics Pref.", "KR", "Growth", "stock"),
    ("KB", "105560", "KB Financial Group", "KR", "Growth", "stock"),
    ("HANA", "086790", "Hana Financial Group", "KR", "Growth", "stock"),
    ("KIA", "000270", "Kia", "KR", "Growth", "stock"),
    ("HMC", "005380", "Hyundai Motor", "KR", "Growth", "stock"),
    ("KTG", "033780", "KT&G", "KR", "Growth", "stock"),
    ("KEPCO", "015760", "Korea Electric Power", "KR", "Growth", "stock"),
    ("KREIT", "329200", "TIGER REITs & Real Estate Infra", "KR", "Real assets", "etf"),
    ("KTB", "152380", "KODEX 10Y KTB Futures", "KR", "Hedge", "etf"),
    ("USDF", "261240", "KODEX USD Futures", "KR", "Hedge", "etf"),
    ("KCD", "459580", "KODEX CD Rate Active", "KR", "Hedge", "etf"),
    ("T", "T", "AT&T", "US", "Growth", "stock"),
    ("XLU", "XLU", "Utilities Select Sector SPDR ETF", "US", "Growth", "etf"),
    ("VNQ", "VNQ", "Vanguard Real Estate ETF", "US", "Real assets", "etf"),
    ("KMLM", "KMLM", "KFA Mount Lucas Managed Futures ETF", "US", "Hedge", "etf"),
    ("SHINHAN", "055550", "Shinhan Financial Group", "KR", "Growth", "stock"),
    ("IBK", "024110", "Industrial Bank of Korea", "KR", "Growth", "stock"),
    ("DBINS", "005830", "DB Insurance", "KR", "Growth", "stock"),
    ("GLOVIS", "086280", "Hyundai Glovis", "KR", "Growth", "stock"),
    ("KGOLD", "132030", "KODEX Gold Futures (H)", "KR", "Hedge", "etf"),
    ("KTB3", "114260", "KODEX 3Y KTB", "KR", "Hedge", "etf"),
    ("KINV", "114800", "KODEX Inverse (KOSPI 200)", "KR", "Hedge", "etf"),
    ("TOPIX", "1306", "NEXT FUNDS TOPIX ETF", "JP", "Growth", "etf"),
    ("TOYOTA", "TM", "Toyota Motor (NYSE ADR)", "JP", "Growth", "stock"),
    ("NTT", "9432", "NTT", "JP", "Growth", "stock"),
    ("JREIT", "1343", "NEXT FUNDS REIT Index ETF", "JP", "Real assets", "etf"),
    ("JGB", "2561", "iShares Core Japan Govt Bond ETF", "JP", "Hedge", "etf"),
]
# group ordering: US, KR, JP
A = [a for c in ("US", "KR", "JP") for sl in ("Growth", "Real assets", "Hedge") for a in A if a[3] == c and a[4] == sl]
keys = [a[0] for a in A]
ix = {k: i for i, k in enumerate(keys)}
N = len(A)
assert [sum(a[3] == c for a in A) for c in ("US", "KR", "JP")] == [22, 19, 5], [sum(a[3] == c for a in A) for c in ("US", "KR", "JP")]

# --------------- factor model (local-currency returns; FX added for USD assets) ---------------
F = ["US_EQ", "KR_EQ", "RATES", "INFL", "GOLD", "FX", "AUTO", "JP_EQ", "JPY", "KR_FIN"]
fvol = np.array([.16, .14, .07, .18, .15, .09, .12, .13, .11, .12])
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
fcor = np.eye(len(F))


def fc(a, b, c):
    i, j = F.index(a), F.index(b)
    fcor[i, j] = fcor[j, i] = c


<<<<<<< HEAD
=======
fc("US_EQ", "KR_EQ", 0.0)          # KR_EQ is the Korea-specific factor (orthogonal by construction)
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
fc("US_EQ", "RATES", -0.10); fc("US_EQ", "INFL", 0.20); fc("US_EQ", "GOLD", 0.05)
fc("US_EQ", "FX", -0.35); fc("KR_EQ", "FX", -0.45); fc("RATES", "INFL", -0.30)
fc("RATES", "GOLD", 0.25); fc("RATES", "FX", 0.15); fc("INFL", "GOLD", 0.35); fc("GOLD", "FX", 0.10)
fc("JPY", "US_EQ", -0.35); fc("JPY", "KR_EQ", -0.40); fc("JPY", "FX", 0.55); fc("JPY", "RATES", 0.20)
fc("JPY", "GOLD", 0.20); fc("JPY", "JP_EQ", -0.30); fc("JP_EQ", "FX", -0.15)
<<<<<<< HEAD
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
=======
Fcov = np.outer(fvol, fvol) * fcor
assert np.linalg.eigvalsh(Fcov).min() > 0

L = {  # factor loadings (local ccy) and idiosyncratic vol
    "IVV": ({"US_EQ": 1.0}, .02), "UNH": ({"US_EQ": .7}, .20), "CI": ({"US_EQ": .6}, .22),
    "CMCSA": ({"US_EQ": .8}, .20), "VZ": ({"US_EQ": .4, "RATES": .5}, .17),
    "PYPL": ({"US_EQ": 1.3}, .28), "ADBE": ({"US_EQ": 1.2}, .25), "USMV": ({"US_EQ": .7, "RATES": .2}, .04),
    "O": ({"US_EQ": .6, "RATES": 1.2}, .13), "VICI": ({"US_EQ": .8, "RATES": .9}, .16),
    "IEF": ({"RATES": 1.0}, .01), "VTIP": ({"RATES": .2, "INFL": .08}, .015), "SGOV": ({}, .005),
    "IAU": ({"GOLD": 1.0}, .02), "DBMF": ({"US_EQ": -.1, "RATES": -.3, "INFL": .3}, .10),
    "TAIL": ({"US_EQ": -.35, "RATES": .8}, .05), "BTAL": ({"US_EQ": -.5}, .08),
    "PDBC": ({"INFL": 1.0, "US_EQ": .15}, .05),
    "K200": ({"US_EQ": .8, "KR_EQ": 1.0}, .04), "SEC_P": ({"US_EQ": 1.0, "KR_EQ": 1.2}, .22),
    "KB": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .13), "HANA": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .14),
    "KIA": ({"US_EQ": .8, "KR_EQ": 1.0, "AUTO": 1.0}, .17), "HMC": ({"US_EQ": .8, "KR_EQ": 1.0, "AUTO": 1.0}, .17),
    "KTG": ({"US_EQ": .2, "KR_EQ": .4}, .16), "KEPCO": ({"US_EQ": .3, "KR_EQ": .6, "INFL": -.3}, .25),
    "KREIT": ({"US_EQ": .3, "KR_EQ": .4, "RATES": .6}, .10), "KTB": ({"RATES": .7}, .03),
    "USDF": ({"FX": 1.0}, .005), "KCD": ({}, .003),
    "T": ({"US_EQ": .35, "RATES": .5}, .17), "XLU": ({"US_EQ": .5, "RATES": .7}, .07),
    "VNQ": ({"US_EQ": .8, "RATES": 1.0}, .06), "KMLM": ({"US_EQ": -.1, "RATES": -.3, "INFL": .35}, .11),
    "SHINHAN": ({"US_EQ": .6, "KR_EQ": 1.0, "KR_FIN": 1.0}, .13), "IBK": ({"US_EQ": .4, "KR_EQ": .8, "KR_FIN": 1.0}, .14),
    "DBINS": ({"US_EQ": .3, "KR_EQ": .6, "KR_FIN": .5}, .17), "GLOVIS": ({"US_EQ": .6, "KR_EQ": .9, "AUTO": .5}, .20),
    "KGOLD": ({"GOLD": 1.0}, .02), "KTB3": ({"RATES": .3}, .01), "KINV": ({"US_EQ": -.8, "KR_EQ": -1.0}, .03),
    "TOPIX": ({"US_EQ": .8, "JP_EQ": 1.0}, .03), "TOYOTA": ({"US_EQ": .8, "JP_EQ": 1.0, "AUTO": .6}, .17),
    "NTT": ({"US_EQ": .3, "JP_EQ": .5}, .13), "JREIT": ({"US_EQ": .4, "JP_EQ": .4, "RATES": .5}, .12),
    "JGB": ({"RATES": .5}, .03),
}
country = {a[0]: a[3] for a in A}
B = np.zeros((N, len(F)))
idio = np.zeros(N)
for k_, (ld, s_) in L.items():
    for f_, v_ in ld.items():
        B[ix[k_], F.index(f_)] = v_
    if country[k_] == "US":
        B[ix[k_], F.index("FX")] += 1.0     # unhedged USD exposure for a KRW investor
    if country[k_] == "JP":
        B[ix[k_], F.index("JPY")] += 1.0    # unhedged JPY exposure for a KRW investor
    idio[ix[k_]] = s_
S = B @ Fcov @ B.T + np.diag(idio ** 2)
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
vol = np.sqrt(np.diag(S))
corr = S / np.outer(vol, vol)


<<<<<<< HEAD
=======
# --------------- expected returns (KRW base; FX drift assumed 0) ---------------
def alpha(up, h=3, shrink=.5):
    return (1 + shrink * up) ** (1 / h) - 1


mu = {}
for k_ in keys:
    if k_ in V and V[k_]["held"]:
        rf, erp = {"USD": (RF_US, ERP_US), "KRW": (RF_KR, ERP_KR), "JPY": (RF_JP, ERP_JP)}[V[k_]["ccy"]]
        mu[k_] = ke(rf, V[k_]["beta"], erp) + alpha(V[k_]["upside"])
mu.update({"IVV": .065, "USMV": .060, "K200": .085, "IEF": .050, "VTIP": .047, "SGOV": .042, "IAU": .040, "DBMF": .055,
           "TAIL": .010, "BTAL": .020, "PDBC": .045, "KREIT": .075, "KTB": .042, "USDF": -.012, "KCD": .028,
           "XLU": .065, "VNQ": .070, "KMLM": .055, "KGOLD": .026, "KTB3": .033, "KINV": -.030,
           "TOPIX": .075, "JREIT": .065, "JGB": .025})
m = np.array([mu[k_] for k_ in keys])

# --------------- optimisation ---------------
grow = [ix[k_] for k_ in keys if next(a for a in A if a[0] == k_)[4] == "Growth"]
real = [ix[k_] for k_ in keys if next(a for a in A if a[0] == k_)[4] == "Real assets"]
hedge = [ix[k_] for k_ in keys if next(a for a in A if a[0] == k_)[4] == "Hedge"]
kr = [ix[k_] for k_ in keys if country[k_] == "KR"]
jp = [ix[k_] for k_ in keys if country[k_] == "JP"]
kbank = [ix[k_] for k_ in ("KB", "HANA", "SHINHAN", "IBK")]
telco = [ix[k_] for k_ in ("VZ", "T")]
bounds = []
for a in A:
    k_, kind = a[0], a[5]
    if k_ == "IVV":
        bounds.append((.05, .12))
    elif k_ in ("K200", "TOPIX"):
        bounds.append((.02, .06))
    elif k_ in ("USMV", "XLU"):
        bounds.append((.01, .05))
    elif kind == "stock":
        bounds.append((.008, .03))
    elif kind == "reit" or k_ in ("KREIT", "VNQ", "JREIT"):
        bounds.append((.01, .03))
    elif k_ in ("SGOV", "KCD"):
        bounds.append((.01, .04))
    elif k_ in ("TAIL", "BTAL", "USDF", "KINV"):
        bounds.append((.01, .045))
    else:
        bounds.append((.015, .07))
cons = [{"type": "eq", "fun": lambda x: x.sum() - 1},
        {"type": "ineq", "fun": lambda x: x[grow].sum() - .45},
        {"type": "ineq", "fun": lambda x: .52 - x[grow].sum()},
        {"type": "ineq", "fun": lambda x: x[real].sum() - .06},
        {"type": "ineq", "fun": lambda x: .12 - x[real].sum()},
        {"type": "ineq", "fun": lambda x: x[jp].sum() - .06},
        {"type": "ineq", "fun": lambda x: .12 - x[jp].sum()},
        {"type": "ineq", "fun": lambda x: .09 - x[kbank].sum()},
        {"type": "ineq", "fun": lambda x: .05 - x[telco].sum()},
        {"type": "ineq", "fun": lambda x: x[hedge].sum() - .38},
        {"type": "ineq", "fun": lambda x: x[kr].sum() - .25},
        {"type": "ineq", "fun": lambda x: .36 - x[kr].sum()}]


def objective(x):
    sr = (x @ m - RF_KRW_CASH) / np.sqrt(x @ S @ x)
    rc = x * (S @ x); rc = rc / rc.sum()
    return -sr + 0.5 * np.sum((rc - rc.mean()) ** 2) * N


x0 = np.array([np.mean(b_) for b_ in bounds]); x0 /= x0.sum()
res = minimize(objective, x0, bounds=bounds, constraints=cons, method="SLSQP",
               options={"maxiter": 5000, "ftol": 1e-12})
w = np.round(res.x * 400) / 400            # 0.25% steps
w = np.clip(w, [b_[0] for b_ in bounds], [b_[1] for b_ in bounds])
diff = 1 - w.sum()
w[ix["IEF"]] += diff


>>>>>>> efe4472c87b93f627888289bbd503438331e197b
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
<<<<<<< HEAD
for tgt in np.linspace(.05, .12, 15):
    r2 = minimize(lambda x: x @ S @ x, res.x, bounds=bnds,
=======
for tgt in np.linspace(.05, .12, 25):
    r2 = minimize(lambda x: x @ S @ x, res.x, bounds=bounds,
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
                  constraints=cons + [{"type": "eq", "fun": lambda x, t=tgt: x @ m - t}],
                  method="SLSQP", options={"maxiter": 3000})
    if r2.success:
        frontier.append((float(np.sqrt(r2.fun)), float(tgt)))

<<<<<<< HEAD
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
=======
# --------------- factor stress tests (KRW base) ---------------
SC = {
    "2022-style rate & inflation shock": (dict(US_EQ=-.18, KR_EQ=-.06, RATES=-.15, INFL=.20, GOLD=-.01, FX=.06, AUTO=0, JP_EQ=0.0, JPY=-.08, KR_FIN=0),
                                          dict(KMLM=.30, DBMF=.22, TAIL=-.08, BTAL=.16, VTIP=-.03, SGOV=.015, KCD=.02)),
    "2008-style credit crash": (dict(US_EQ=-.37, KR_EQ=-.12, RATES=.18, INFL=-.35, GOLD=.05, FX=.30, AUTO=-.10, JP_EQ=-.10, JPY=.50, KR_FIN=-.10),
                                dict(KMLM=.18, DBMF=.20, TAIL=.15, BTAL=.15, SGOV=.02, KCD=.04)),
    "Memory downcycle, KRW weakens 15%": (dict(US_EQ=-.08, KR_EQ=-.12, RATES=.04, INFL=-.05, GOLD=.05, FX=.15, AUTO=0, JP_EQ=-.03, JPY=.12, KR_FIN=-.05),
                                    dict(SEC_P=-.45, SGOV=.04, KCD=.03)),
    "Oil / Middle-East inflation spike": (dict(US_EQ=-.12, KR_EQ=-.05, RATES=-.08, INFL=.25, GOLD=.20, FX=.08, AUTO=0, JP_EQ=-.05, JPY=.03, KR_FIN=0),
                                          dict(KMLM=.15, DBMF=.15, KEPCO=-.25, SGOV=.04, KCD=.03)),
    "AI-capex bust (tech −35%)": (dict(US_EQ=-.22, KR_EQ=-.08, RATES=.08, INFL=-.08, GOLD=.06, FX=.07, AUTO=0, JP_EQ=-.05, JPY=.08, KR_FIN=0),
                                  dict(SEC_P=-.40, BTAL=.12, SGOV=.04, KCD=.03)),
    "Risk-on rally, KRW strengthens 15%": (dict(US_EQ=.12, KR_EQ=.10, RATES=.04, INFL=.05, GOLD=-.03, FX=-.15, AUTO=.05, JP_EQ=.05, JPY=-.12, KR_FIN=.03),
                                                    dict(KMLM=.02, DBMF=.02, TAIL=-.06, BTAL=-.12, SGOV=.04, KCD=.03)),
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
}


def scen_ret(fs, ov):
<<<<<<< HEAD
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
=======
    fvec = np.array([fs[f_] for f_ in F])
    r = B @ fvec
    for k_, v_ in ov.items():                 # override = local return; add FX back for USD assets
        r[ix[k_]] = v_ + (fs["FX"] if country[k_] == "US" else 0) + (fs["JPY"] if country[k_] == "JP" else 0)
    return r


stress = {}
for nm, (fs, ov) in SC.items():
    r = scen_ret(fs, ov)
    stress[nm] = dict(port=float(w @ r), bench=float(wb @ r))

# --------------- output ---------------
port = dict(assets=[dict(key=a[0], ticker=a[1], name=a[2], country=a[3], sleeve=a[4], kind=a[5],
                         weight=float(w[ix[a[0]]]), mu=float(mu[a[0]]), vol=float(vol[ix[a[0]]]),
                         rc=float(rc[ix[a[0]]])) for a in A],
            er=er, sd=sd, sharpe=sr, beta_ivv=beta_ivv, beta_k200=beta_k200, var95=var95, cvar95=cvar95,
            div_ratio=div_ratio, bench=dict(er=erb, sd=sdb, sharpe=srb, var95=var95b, cvar95=cvar95b),
            stress=stress, frontier=frontier, opt_ok=bool(res.success),
            factors=F, fvol=fvol.tolist(), loadings=B.tolist(), corr=corr.tolist(), rf=RF_KRW_CASH)
>>>>>>> efe4472c87b93f627888289bbd503438331e197b


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
<<<<<<< HEAD
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
=======
    return o


json.dump(clean(dict(val=V, port=port)), open("results.json", "w"), indent=1)

print("VALUATIONS")
for k_, v_ in sorted(V.items(), key=lambda kv: -kv[1]["upside"]):
    print(f"  {k_:7s} {'HELD' if v_['held'] else 'rej ':4s} {v_['price']:>12,.2f} → {v_['value']:>12,.2f} {v_['upside']:+7.1%}")
print("\nopt ok", res.success, "| sum", round(w.sum(), 4))
for a in A:
    i = ix[a[0]]
    print(f"  {a[0]:6s} {a[3]} {a[4]:11s} w {w[i]:6.2%} mu {m[i]:6.1%} vol {vol[i]:5.1%} rc {rc[i]:6.1%}")
tot = lambda idx: w[idx].sum()
print(f"Growth {tot(grow):.1%} Real {tot(real):.1%} Hedge {tot(hedge):.1%} | KR {tot(kr):.1%}")
print(f"E[R] {er:.2%} vol {sd:.2%} SR {sr:.2f} betaIVV {beta_ivv:.2f} betaK200 {beta_k200:.2f} DR {div_ratio:.2f}")
print(f"Bench E[R] {erb:.2%} vol {sdb:.2%} SR {srb:.2f}")
print(f"VaR {var95:.2%} CVaR {cvar95:.2%} | bench VaR {var95b:.2%} CVaR {cvar95b:.2%}")
for k_, s_ in stress.items():
    print(f"  {k_:36s} port {s_['port']:+.1%}  bench {s_['bench']:+.1%}")
>>>>>>> efe4472c87b93f627888289bbd503438331e197b
