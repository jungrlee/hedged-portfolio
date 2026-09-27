import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

os.makedirs("charts", exist_ok=True)
R = json.load(open("results.json"))
P, V = R["port"], R["val"]
AS = P["assets"]

BLUE, ORANGE, AQUA, GRAY = "#1a7a4c", "#c9a227", "#2f6fb3", "#9a9893"   # SKK green, gold, blue
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SLEEVE_C = {"Growth": BLUE, "Real assets": ORANGE, "Hedge": AQUA}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})
SHORT = {"SEC_P": "Samsung Pref", "K200": "KODEX 200", "KB": "KB Fin.", "HANA": "Hana Fin.", "KIA": "Kia",
         "HMC": "Hyundai Mtr", "KTG": "KT&G", "KEPCO": "KEPCO", "KREIT": "TIGER REITs", "KTB": "KODEX KTB10",
         "USDF": "KODEX USD", "KCD": "KODEX CD", "SHINHAN": "Shinhan Fin.", "IBK": "IBK",
         "DBINS": "DB Insurance", "GLOVIS": "Hyundai Glovis", "KGOLD": "KODEX Gold(H)", "KTB3": "KODEX KTB3",
         "KINV": "KODEX Inverse", "TOPIX": "TOPIX ETF", "TOYOTA": "Toyota (TM ADR)", "NTT": "NTT", "JREIT": "J-REIT ETF",
         "JGB": "JGB ETF"}
sh = lambda k: SHORT.get(k, k)


def save(fig, name):
    fig.savefig(f"charts/{name}.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. Weights: grouped by country, coloured by sleeve
fig = plt.figure(figsize=(7.2, 5.0))
gs = fig.add_gridspec(24, 2, wspace=.45)
ax_us = fig.add_subplot(gs[:, 0]); ax_kr = fig.add_subplot(gs[0:18, 1]); ax_jp = fig.add_subplot(gs[19:24, 1])
for ax, cty, title in [(ax_us, "US", "US (22)"), (ax_kr, "KR", "Korea (19)"), (ax_jp, "JP", "Japan (5)")]:
    rows = [a for a in AS if a["country"] == cty]
    y = np.arange(len(rows))[::-1]
    for yi, a in zip(y, rows):
        ax.barh(yi, a["weight"] * 100, color=SLEEVE_C[a["sleeve"]], height=.72, edgecolor="white", lw=.8)
        ax.text(a["weight"] * 100 + .1, yi, f"{a['weight']*100:.2f}".rstrip("0").rstrip(".") + "%",
                va="center", fontsize=5.8, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([sh(a["key"]) for a in rows], fontsize=6)
    ax.tick_params(axis="y", length=0); ax.xaxis.set_visible(False); ax.spines["bottom"].set_visible(False)
    ax.set_ylim(-.6, len(rows) - .4)
    tot = sum(a["weight"] for a in rows)
    ax.set_title(f"{title} · {tot*100:.1f}%", pad=3, fontsize=7.5)
    ax.set_xlim(0, 6.2)
tot = {s: sum(a["weight"] for a in AS if a["sleeve"] == s) for s in SLEEVE_C}
h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in SLEEVE_C.values()]
fig.legend(h, [f"{s} {tot[s]*100:.1f}%" for s in SLEEVE_C], loc="upper center", ncol=3, frameon=False,
           fontsize=7, bbox_to_anchor=(0.5, .97))
save(fig, "d_weights")

# 2. Scoreboard (all stocks & REITs valued)
items = sorted(V.items(), key=lambda kv: kv[1]["upside"])
fig, ax = plt.subplots(figsize=(7.2, 6.6))
y = np.arange(len(items))
for yi, (k, v) in zip(y, items):
    u = v["upside"] * 100
    ax.barh(yi, u, color=BLUE if v["held"] else GRAY, height=.68, edgecolor="white", lw=.8)
    ax.text(u + (1.5 if u >= 0 else -1.5), yi, f"{u:+.0f}%", va="center", ha="left" if u >= 0 else "right",
            fontsize=6, color=INK)
lab = [f"{v['name']}" + {"KRW": " (KR)", "JPY": " (JP)"}.get(v["ccy"], "") for _, v in items]
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=5.6); ax.tick_params(axis="y", length=0)
ax.axvline(0, color=INK2, lw=.8); ax.axvline(15, color=INK2, lw=.8, ls=(0, (3, 2)))
ax.text(16, 1, "15% hurdle", fontsize=6.5, color=INK2)
ax.set_xlim(-50, 135); ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_xlabel("Base-case intrinsic value vs price (%)", fontsize=7)
h = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=GRAY)]
ax.legend(h, [f"Held ({sum(v['held'] for v in V.values())})", f"Screened out ({sum(not v['held'] for v in V.values())})"],
          frameon=False, fontsize=7, loc="lower right")
ax.set_title("Valuation scoreboard: every single stock and REIT considered", pad=4)
save(fig, "d_scoreboard")


# 3. Football fields
def football(keys, name, title, xmax):
    fig, ax = plt.subplots(figsize=(7.2, .38 * len(keys) + .7))
    y = np.arange(len(keys))[::-1]
    for yi, k in zip(y, keys):
        v = V[k]
        vals = np.array(v["grid"]["v"]).ravel() / v["price"] * 100 - 100
        lo, hi, base = vals.min(), vals.max(), v["upside"] * 100
        ax.barh(yi, hi - lo, left=lo, height=.5, color=BLUE, alpha=.3)
        ax.plot([base, base], [yi - .3, yi + .3], color=BLUE, lw=2.4)
        ax.text(lo - 2, yi, f"{lo:+.0f}%", va="center", ha="right", fontsize=6.3, color=INK)
        ax.text(hi + 2, yi, f"{hi:+.0f}%", va="center", ha="left", fontsize=6.3, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([V[k]["name"] for k in keys], fontsize=6.8); ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=INK2, lw=.8); ax.axvline(15, color=INK2, lw=.8, ls=(0, (3, 2)))
    ax.set_xlim(-60, xmax); ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
    ax.set_xlabel("Upside across each model's 3×3 sensitivity grid (bar) and base case (tick); dashed = 15% hurdle",
                  fontsize=6.5)
    ax.set_title(title, pad=4)
    save(fig, name)


football(["UNH", "CI", "CMCSA", "VZ", "T", "PYPL", "ADBE", "O", "VICI"], "d_ff_us",
         "US stocks & REITs: how wrong can the inputs be?", 160)
football(["SEC_P", "KB", "HANA", "SHINHAN", "IBK", "DBINS", "KIA", "HMC", "GLOVIS", "KTG", "KEPCO", "TOYOTA", "NTT"],
         "d_ff_kr", "Korean and Japanese stocks: how wrong can the inputs be?", 250)

# 4. Samsung OP path
fig, ax = plt.subplots(figsize=(3.4, 2.1))
yrs = ["2018A", "2026E", "2027E", "2028E", "2029M", "2030M+"]
cons = [58.9, 362, 499, 469]
xs = np.arange(len(yrs))
ax.bar(xs[:4], cons, color=[GRAY, BLUE, BLUE, BLUE], width=.6, edgecolor="white")
for sc, mo, col, ls in [("Bull", 260, AQUA, (0, (4, 2))), ("Base", 200, INK, "-"), ("Bear", 150, ORANGE, (0, (2, 2)))]:
    ax.plot(xs[3:], [469, .5 * (469 + mo), mo], color=col, lw=1.8, ls=ls)
    ax.text(xs[-1] + .12, mo, f"{sc} ₩{mo}tn", va="center", fontsize=6, color=INK)
for xi, c in zip(xs[:4], cons):
    ax.text(xi, c + 8, f"{c:.0f}", ha="center", fontsize=6.3, color=INK)
ax.set_xticks(xs); ax.set_xticklabels(yrs, fontsize=6.3); ax.tick_params(axis="x", length=0)
ax.set_xlim(-.6, 6.5); ax.set_ylim(0, 560); ax.yaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_ylabel("Operating profit (₩tn)", fontsize=6.8)
ax.set_title("Samsung: consensus peak → mid-cycle", pad=4, fontsize=8)
save(fig, "d_samsung")

# 5. Factor exposure heatmap (30 × factors)
F = P["factors"]
Bm = np.array(P["loadings"])
fnames = {"US_EQ": "US equity", "KR_EQ": "Korea\nequity", "RATES": "Rates\n(duration)", "INFL": "Inflation/\ncommod.",
          "GOLD": "Gold", "FX": "USD vs\nKRW", "AUTO": "Autos", "JP_EQ": "Japan\nequity", "JPY": "JPY vs\nKRW",
          "KR_FIN": "Korean\nfinancials"}
cm = LinearSegmentedColormap.from_list("div", ["#2f6fb3", "#f4f1e6", "#c9a227"])
fig, ax = plt.subplots(figsize=(4.2, 8.6))
im = ax.imshow(Bm, cmap=cm, vmin=-1.3, vmax=1.3, aspect="auto")
ax.set_xticks(range(len(F))); ax.set_xticklabels([fnames[f] for f in F], fontsize=5.2)
ax.xaxis.tick_top()
ax.set_yticks(range(len(AS))); ax.set_yticklabels([sh(a["key"]) + {"KR": "  ·KR", "JP": "  ·JP"}.get(a["country"], "") for a in AS], fontsize=5.6)
ax.tick_params(length=0)
for i in range(len(AS)):
    for j in range(len(F)):
        if abs(Bm[i, j]) > 1e-9:
            ax.text(j, i, f"{Bm[i,j]:.1f}".replace("-", "−"), ha="center", va="center", fontsize=5, color=INK)
for s_ in ax.spines.values():
    s_.set_visible(False)
ax.axhline(21.5, color=INK2, lw=.8); ax.axhline(40.5, color=INK2, lw=.8)
ax.set_title("Factor exposures (KRW investor)", pad=26, fontsize=8)
save(fig, "d_factors")

# 6. Frontier
fig, ax = plt.subplots(figsize=(3.5, 2.7))
fr = np.array(P["frontier"])
ax.plot(fr[:, 0] * 100, fr[:, 1] * 100, color=BLUE, lw=2)
for a in AS:
    if a["kind"] != "stock":
        continue
    if a["mu"] < .19:
        ax.scatter(a["vol"] * 100, a["mu"] * 100, s=8, color=GRAY, zorder=2)
ax.scatter([], [], s=8, color=GRAY, label="Single stocks")
ax.scatter(P["sd"] * 100, P["er"] * 100, s=46, color=ORANGE, zorder=3, edgecolor="white", lw=1.5)
ax.annotate("Portfolio", (P["sd"] * 100, P["er"] * 100), xytext=(6, -3), textcoords="offset points", fontsize=7, weight="bold")
b = P["bench"]
ax.scatter(b["sd"] * 100, b["er"] * 100, s=38, color=INK2, marker="D", zorder=3, edgecolor="white", lw=1.5)
ax.annotate("Benchmark*", (b["sd"] * 100, b["er"] * 100), xytext=(6, -3), textcoords="offset points", fontsize=7)
ax.annotate("frontier", (fr[-1, 0] * 100, fr[-1, 1] * 100), xytext=(4, 0), textcoords="offset points", fontsize=6, color=BLUE)
ax.set_xlabel("Volatility in KRW (%)", fontsize=7); ax.set_ylabel("Expected return (%)", fontsize=7)
ax.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True); ax.set_xlim(0, 36); ax.set_ylim(4, 19)
ax.text(35, 18.3, "KEPCO, IBK, DB Ins. (μ > 19%) off scale", fontsize=5.5, color=INK2, ha="right")
ax.legend(frameon=False, fontsize=6, loc="upper left")
ax.set_title("Risk / return (ex-ante, KRW)", pad=4, fontsize=8)
save(fig, "d_frontier")

# 7. Risk budget by sleeve-country
groups = {}
for a in AS:
    g = f"{a['sleeve']} · {a['country']}"
    groups.setdefault(g, [0, 0])
    groups[g][0] += a["weight"]; groups[g][1] += a["rc"]
order = ["Growth · US", "Growth · KR", "Growth · JP", "Real assets · US", "Real assets · KR", "Real assets · JP",
         "Hedge · US", "Hedge · KR", "Hedge · JP"]
fig, ax = plt.subplots(figsize=(3.5, 2.7))
x = np.arange(len(order))
ax.bar(x - .2, [groups[g][0] * 100 for g in order], .38, color=BLUE, label="Capital")
ax.bar(x + .2, [groups[g][1] * 100 for g in order], .38, color=ORANGE, label="Risk contribution")
for xi, g in zip(x, order):
    ax.text(xi - .2, groups[g][0] * 100 + .6, f"{groups[g][0]*100:.0f}", ha="center", fontsize=5.8)
    ax.text(xi + .2, groups[g][1] * 100 + .6, f"{groups[g][1]*100:.0f}", ha="center", fontsize=5.8)
ax.set_xticks(x); ax.set_xticklabels([g.replace("Real assets", "Real").replace(" · ", "\n") for g in order], fontsize=5.6)
ax.tick_params(axis="x", length=0); ax.yaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_ylabel("% of total", fontsize=7); ax.set_ylim(0, 40)
ax.legend(frameon=False, fontsize=6.3, loc="upper left", ncol=2)
ax.set_title("Capital vs risk budget", pad=4, fontsize=8)
save(fig, "d_risk")

# 8. Stress
st = P["stress"]
names = list(st)
fig, ax = plt.subplots(figsize=(7.2, 2.4))
y = np.arange(len(names))[::-1]
pv = [st[n]["port"] * 100 for n in names]; bv = [st[n]["bench"] * 100 for n in names]
ax.barh(y + .19, pv, .36, color=BLUE, label="This portfolio")
ax.barh(y - .19, bv, .36, color=GRAY, label="Benchmark* (30% IVV / 30% KODEX 200 / 20% IEF / 20% KTB)")
for yi, p_, b_ in zip(y, pv, bv):
    for val, off, col in [(p_, .19, INK), (b_, -.19, INK2)]:
        ax.text(val + (.3 if val >= 0 else -.3), yi + off, f"{val:+.1f}%", va="center",
                ha="left" if val >= 0 else "right", fontsize=6.2, color=col)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=6.8); ax.tick_params(axis="y", length=0)
ax.axvline(0, color=INK2, lw=.8); ax.set_xlim(-17, 13)
ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_xlabel("Scenario return in KRW (%)", fontsize=7)
ax.legend(frameon=False, fontsize=6.5, loc="lower left", ncol=2, bbox_to_anchor=(0, -.42))
ax.set_title("Stress tests (factor-shock scenarios, KRW base)", pad=4)
save(fig, "d_stress")
print("charts ok")

# ============ Optimiser findings ============
O = json.load(open("results_opt.json"))
MS = O["methods"]
# 9. Method comparison: Sharpe + max risk contribution
names = list(MS)
short = {"1/N equal weight": "1/N equal\nweight", "Long-only max Sharpe": "Long-only\nmax Sharpe",
         "Minimum variance": "Minimum\nvariance", "Risk parity": "Risk\nparity",
         "Final (mandate + RP penalty)": "Final\n(used)"}
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.0))
for ax, (key, lab, fmt) in zip(axes, [("sharpe", "Sharpe ratio (ex-ante)", "{:.2f}"),
                                       ("maxrc", "Largest single risk contribution", "{:.0%}"),
                                       ("effn", "Effective no. of holdings (1/Σw²)", "{:.0f}")]):
    vals = [MS[n][key] for n in names]
    cols = [BLUE if n.startswith("Final") else GRAY for n in names]
    ax.bar(range(len(names)), vals, color=cols, width=.65, edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(i, v * 1.02 + (0.01 if key != "effn" else .3), fmt.format(v), ha="center", fontsize=6)
    ax.set_xticks(range(len(names))); ax.set_xticklabels([short[n] for n in names], fontsize=5.3)
    ax.tick_params(axis="x", length=0); ax.set_title(lab, fontsize=7.2, pad=4)
    ax.yaxis.set_visible(False); ax.spines["left"].set_visible(False)
    ax.set_ylim(0, max(vals) * 1.22)
fig.tight_layout(w_pad=1.5)
save(fig, "d_methods")

# 10. Weight stability
keysO = O["keys"]; wf = np.array(O["final"]); p5 = np.array(O["p5"]); p95 = np.array(O["p95"])
fig, ax = plt.subplots(figsize=(7.2, 2.1))
x = np.arange(len(keysO))
ax.vlines(x, p5 * 100, p95 * 100, color=BLUE, lw=5, alpha=.3, label="5–95% range, 200 re-optimisations with noisy μ (±2pp)")
ax.scatter(x, wf * 100, color=ORANGE, s=14, zorder=3, edgecolor="white", lw=.6, label="Final weight")
ax.set_xticks(x); ax.set_xticklabels([sh(k) for k in keysO], rotation=90, fontsize=5.2)
ax.tick_params(axis="x", length=0); ax.yaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_ylabel("Weight (%)", fontsize=7); ax.legend(frameon=False, fontsize=6, loc="upper left", ncol=2)
ax.set_ylim(0, 8)
ax.set_title("How much do weights move when expected returns are wrong?", pad=4, fontsize=8)
save(fig, "d_stability")
print("opt charts ok")
