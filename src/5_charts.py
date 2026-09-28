"""Charts for version 3 (screened universe). Reads results_v3.json, results_opt_v3.json, screen_results.json."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = ""
P = json.load(open("data/results.json"))["port"]
SCR = json.load(open("data/screen_results.json"))
V46 = json.load(open("data/bespoke_valuations.json"))["val"]
AS = P["assets"]
HELD = {a["key"] for a in AS if a["kind"] != "etf"}

BLUE, ORANGE, AQUA, GRAY = "#1a7a4c", "#c9a227", "#2f6fb3", "#9a9893"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
MKT_C = {"US": BLUE, "KR": ORANGE, "JP": AQUA}
MKT_N = {"US": "US", "KR": "Korea", "JP": "Japan"}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})
SHORT = {"K200": "KODEX 200", "KREIT": "TIGER REITs", "KTB": "KODEX KTB10", "USDF": "KODEX USD", "KCD": "KODEX CD",
         "KGOLD": "KODEX Gold(H)", "KTB3": "KODEX KTB3", "KINV": "KODEX Inverse", "TOPIX": "TOPIX ETF",
         "JREIT": "J-REIT ETF", "JGB": "JGB ETF"}
NAME = {a["key"]: (a["ticker"] if a["kind"] == "etf" else a["name"]) for a in AS}
NAME.update({c["key"]: c["name"] for c in P["candidates"]})
sh = lambda k: SHORT.get(k, NAME.get(k, k) if k in HELD or k in NAME else k)


def save(fig, name):
    fig.savefig(f"images/{name}.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. Funnel -------------------------------------------------------------------
fu = P["funnel"]
stages = [("universe", "Universe (largest by market cap)"), ("in_scope", "In scope (profitable, not a holding co.)"),
          ("valued", "Valued in full"), ("passed", "Clear the 15% hurdle"), ("held", "Held after optimisation")]
fig, ax = plt.subplots(figsize=(7.2, 2.1))
y = np.arange(len(stages))[::-1]
for yi, (k, lab) in zip(y, stages):
    left = 0
    for m in ("US", "KR", "JP"):
        n = fu[m][k]
        ax.barh(yi, n, left=left, color=MKT_C[m], height=.62, edgecolor="white", lw=.8)
        if n >= 3:
            ax.text(left + n / 2, yi, str(n), ha="center", va="center", fontsize=6.3, color="white" if m != "KR" else INK)
        left += n
    ax.text(left + 3, yi, f"{fu['ALL'][k]}", va="center", fontsize=7, color=INK, weight="bold")
ax.set_yticks(y); ax.set_yticklabels([s[1] for s in stages], fontsize=6.8); ax.tick_params(axis="y", length=0)
ax.xaxis.set_visible(False); ax.spines["bottom"].set_visible(False); ax.set_xlim(0, 320)
h = [plt.Rectangle((0, 0), 1, 1, color=MKT_C[m]) for m in MKT_C]
ax.legend(h, [MKT_N[m] for m in MKT_C], frameon=False, fontsize=6.5, ncol=3, loc="lower right")
ax.set_title("From 300 stocks to the portfolio", pad=4)
save(fig, "d3_funnel")

# 2. Validation: screen vs model, systematic vs hand-built ---------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.7))
val = [r for r in SCR if r.get("shortlist") and r.get("upside") is not None and r.get("score") is not None]
for m in ("US", "KR", "JP"):
    xs = [r["score"] * 100 for r in val if r["market"] == m]
    ys = [np.clip(r["upside"] * 100, -80, 130) for r in val if r["market"] == m]
    a1.scatter(xs, ys, s=10, color=MKT_C[m], label=MKT_N[m], alpha=.85, edgecolor="white", lw=.3)
x_all = np.array([r["score"] for r in val]); y_all = np.array([r["upside"] for r in val])
rho = np.corrcoef(np.argsort(np.argsort(x_all)), np.argsort(np.argsort(y_all)))[0, 1]
a1.axhline(15, color=INK2, lw=.8, ls=(0, (3, 2))); a1.axhline(0, color=INK2, lw=.6)
a1.text(2, 19, "15% hurdle", fontsize=6, color=INK2)
a1.set_xlabel("Multiples screen score (percentile within market)", fontsize=6.5)
a1.set_ylabel("Model upside (%)", fontsize=6.5); a1.set_ylim(-85, 135); a1.set_xlim(0, 100)
a1.grid(True, color=GRID, lw=.5); a1.set_axisbelow(True)
a1.legend(frameon=False, fontsize=6, loc="upper left")
a1.set_title(f"(a) Cheap on multiples → more upside (rank corr. {rho:.2f})", fontsize=7.5, pad=4)
bp = [(r["sys_upside"] * 100, r["bespoke_upside"] * 100, r["market"]) for r in SCR
      if r.get("bespoke_upside") is not None and r.get("sys_upside") is not None]
for m in ("US", "KR", "JP"):
    a2.scatter([np.clip(b[1], -60, 160) for b in bp if b[2] == m], [np.clip(b[0], -80, 160) for b in bp if b[2] == m],
               s=12, color=MKT_C[m], edgecolor="white", lw=.3)
a2.plot([-60, 160], [-60, 160], color=INK2, lw=.7)
a2.axhline(15, color=INK2, lw=.6, ls=(0, (3, 2))); a2.axvline(15, color=INK2, lw=.6, ls=(0, (3, 2)))
a2.set_xlabel("Hand-built model upside (%)", fontsize=6.5); a2.set_ylabel("Systematic model upside (%)", fontsize=6.5)
a2.set_xlim(-60, 140); a2.set_ylim(-85, 160); a2.grid(True, color=GRID, lw=.5); a2.set_axisbelow(True)
c = P["calib"]
a2.set_title(f"(b) Systematic vs hand-built, {c['n']} names (corr. {c['corr']:.2f})", fontsize=7.5, pad=4)
fig.tight_layout(w_pad=2)
save(fig, "d3_validation")

# 3. Candidates: selection frequency -------------------------------------------
cand = sorted(P["candidates"], key=lambda c: (-c["sel_freq"], -c["upside"]))
fig, ax = plt.subplots(figsize=(7.2, 6.3))
y = np.arange(len(cand))[::-1]
for yi, c_ in zip(y, cand):
    col = MKT_C[c_["country"]] if c_["held"] else GRAY
    ax.barh(yi, c_["sel_freq"] * 100, color=col, height=.7, edgecolor="white", lw=.6, alpha=1 if c_["held"] else .55)
    ax.text(c_["sel_freq"] * 100 + 1, yi, f"{c_['sel_freq']*100:.0f}%   upside {c_['upside']*100:+.0f}%", va="center", fontsize=5.6, color=INK)
ax.set_yticks(y)
ax.set_yticklabels([f"{c_['name']} ({c_['country']})" for c_ in cand], fontsize=5.6)
ax.tick_params(axis="y", length=0)
ax.axvline(50, color=INK2, lw=.8, ls=(0, (3, 2)))
ax.text(51, 2, "held if chosen in ≥50% of runs", fontsize=6, color=INK2)
ax.set_xlim(0, 125); ax.xaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
ax.set_xlabel(f"Share of {P['n_draw']:.0f} re-optimisations (noisy expected returns) that give the stock ≥0.5%", fontsize=6.5)
h = [plt.Rectangle((0, 0), 1, 1, color=MKT_C[m]) for m in MKT_C] + [plt.Rectangle((0, 0), 1, 1, color=GRAY, alpha=.55)]
ax.legend(h, ["Held · US", "Held · Korea", "Held · Japan", "Passed hurdle, not held"], frameon=False, fontsize=6,
          loc="lower right")
ax.set_title(f"The {len(cand)} stocks that cleared the hurdle, and which ones the optimiser kept", pad=4)
save(fig, "d3_candidates")

# 4. Football field for held stocks -------------------------------------------
SCR_BY = {r["code"]: r for r in SCR}
held = [a for a in AS if a["kind"] != "etf"]


def grid_of(a):
    r = SCR_BY.get(a["code"])
    if a["bespoke"] and r and r.get("bespoke_key") and "grid" in V46[r["bespoke_key"]]:
        v = V46[r["bespoke_key"]]
        return np.array(v["grid"]["v"]).ravel() / v["price"] - 1
    if r and "grid" in r:
        return np.array(r["grid"]["v"]).ravel()
    return None


def football(items, name, title, xmax):
    fig, ax = plt.subplots(figsize=(7.2, .31 * len(items) + .8))
    y = np.arange(len(items))[::-1]
    for yi, a in zip(y, items):
        g = grid_of(a)
        base = a["upside"] * 100
        col = MKT_C[a["country"]]
        if g is not None:
            lo, hi = g.min() * 100, g.max() * 100
            ax.barh(yi, hi - lo, left=lo, height=.5, color=col, alpha=.3)
            ax.text(lo - 2, yi, f"{lo:+.0f}%", va="center", ha="right", fontsize=5.8, color=INK)
            ax.text(hi + 2, yi, f"{hi:+.0f}%", va="center", ha="left", fontsize=5.8, color=INK)
        ax.plot([base, base], [yi - .3, yi + .3], color=col, lw=2.4)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{a['name']}" + ("  ·hand-built" if a["bespoke"] else "") for a in items], fontsize=6.3)
    ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=INK2, lw=.8); ax.axvline(15, color=INK2, lw=.8, ls=(0, (3, 2)))
    ax.set_xlim(-40, xmax); ax.xaxis.grid(True, color=GRID, lw=.5); ax.set_axisbelow(True)
    ax.set_xlabel("Upside across a 3×3 grid (cost of equity ±1pp × growth ±2pp or ROE ±1pp); tick = base case; dashed = 15% hurdle",
                  fontsize=6)
    ax.set_title(title, pad=4)
    save(fig, name)


football(sorted(held, key=lambda a: ("US", "KR", "JP").index(a["country"])), "d3_ff", "Held stocks: how wrong can the inputs be?", 260)

# 5. Factor heatmap --------------------------------------------------------------
F = P["factors"]
Bm = np.array(P["loadings"])
fnames = {"US_EQ": "US\nequity", "KR_EQ": "Korea\nequity", "RATES": "Rates", "INFL": "Infl./\ncomm.",
          "GOLD": "Gold", "FX": "USD vs\nKRW", "AUTO": "Autos", "JP_EQ": "Japan\nequity", "JPY": "JPY vs\nKRW",
          "KR_FIN": "KR\nfin.", "JP_FIN": "JP\nfin."}
cm = LinearSegmentedColormap.from_list("div", ["#2f6fb3", "#f4f1e6", "#c9a227"])
fig, ax = plt.subplots(figsize=(4.4, 8.2))
ax.imshow(Bm, cmap=cm, vmin=-1.3, vmax=1.3, aspect="auto")
ax.set_xticks(range(len(F))); ax.set_xticklabels([fnames[f] for f in F], fontsize=5.0)
ax.xaxis.tick_top()
ax.set_yticks(range(len(AS)))
ax.set_yticklabels([sh(a["key"]) + {"KR": "  ·KR", "JP": "  ·JP"}.get(a["country"], "") for a in AS], fontsize=5.4)
ax.tick_params(length=0)
for i in range(len(AS)):
    for j in range(len(F)):
        if abs(Bm[i, j]) > 1e-9:
            ax.text(j, i, f"{Bm[i,j]:.1f}".replace("-", "−"), ha="center", va="center", fontsize=4.8, color=INK)
for s_ in ax.spines.values():
    s_.set_visible(False)
nus = sum(a["country"] == "US" for a in AS); nkr = sum(a["country"] == "KR" for a in AS)
ax.axhline(nus - .5, color=INK2, lw=.8); ax.axhline(nus + nkr - .5, color=INK2, lw=.8)
ax.set_title("Factor exposures (KRW investor)", pad=24, fontsize=8)
save(fig, "d3_factors")

# 6. Frontier ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(3.5, 2.7))
fr = np.array(P["frontier"])
ax.plot(fr[:, 0] * 100, fr[:, 1] * 100, color=BLUE, lw=2)
for a in AS:
    if a["kind"] == "etf":
        continue
    ax.scatter(a["vol"] * 100, a["mu"] * 100, s=8, color=MKT_C[a["country"]], zorder=2)
ax.scatter(P["sd"] * 100, P["er"] * 100, s=46, color=INK, zorder=3, edgecolor="white", lw=1.5)
ax.annotate("Portfolio", (P["sd"] * 100, P["er"] * 100), xytext=(6, -3), textcoords="offset points", fontsize=7, weight="bold")
b = P["bench"]
ax.scatter(b["sd"] * 100, b["er"] * 100, s=38, color=INK2, marker="D", zorder=3, edgecolor="white", lw=1.5)
ax.annotate("Benchmark*", (b["sd"] * 100, b["er"] * 100), xytext=(6, -3), textcoords="offset points", fontsize=7)
ax.annotate("frontier", (fr[-1, 0] * 100, fr[-1, 1] * 100), xytext=(4, 0), textcoords="offset points", fontsize=6, color=BLUE)
for m in MKT_C:
    ax.scatter([], [], s=8, color=MKT_C[m], label=f"Stocks · {MKT_N[m]}")
ax.set_xlabel("Volatility in KRW (%)", fontsize=7); ax.set_ylabel("Expected return (%)", fontsize=7)
ax.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True); ax.set_xlim(0, 32); ax.set_ylim(4, 20)
ax.legend(frameon=False, fontsize=5.6, loc="lower right")
ax.set_title("Risk / return (ex-ante, KRW)", pad=4, fontsize=8)
save(fig, "d3_frontier")

# 7. Risk budget ------------------------------------------------------------------
groups = {}
for a in AS:
    g = f"{a['sleeve']} · {a['country']}"
    groups.setdefault(g, [0, 0])
    groups[g][0] += a["weight"]; groups[g][1] += a["rc"]
order = [g for g in ["Growth · US", "Growth · KR", "Growth · JP", "Real assets · US", "Real assets · KR", "Real assets · JP",
                     "Hedge · US", "Hedge · KR", "Hedge · JP"] if g in groups]
fig, ax = plt.subplots(figsize=(3.5, 2.7))
x = np.arange(len(order))
ax.bar(x - .2, [groups[g][0] * 100 for g in order], .38, color=BLUE, label="Capital")
ax.bar(x + .2, [groups[g][1] * 100 for g in order], .38, color=ORANGE, label="Risk contribution")
for xi, g in zip(x, order):
    ax.text(xi - .2, groups[g][0] * 100 + .6, f"{groups[g][0]*100:.0f}", ha="center", fontsize=5.8)
    ax.text(xi + .2, groups[g][1] * 100 + .6, f"{groups[g][1]*100:.0f}", ha="center", fontsize=5.8)
ax.set_xticks(x); ax.set_xticklabels([g.replace("Real assets", "Real").replace(" · ", "\n") for g in order], fontsize=5.6)
ax.tick_params(axis="x", length=0); ax.yaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_ylabel("% of total", fontsize=7); ax.set_ylim(0, 50)
ax.legend(frameon=False, fontsize=6.3, loc="upper right", ncol=1)
ax.set_title("Capital vs risk budget", pad=4, fontsize=8)
save(fig, "d3_risk")

# 8. Stress --------------------------------------------------------------------------
st = P["stress"]
names = list(st)
fig, ax = plt.subplots(figsize=(7.2, 2.4))
y = np.arange(len(names))[::-1]
pv = [st[n]["port"] * 100 for n in names]; bv = [st[n]["bench"] * 100 for n in names]
ax.barh(y + .19, pv, .36, color=BLUE, label="This portfolio")
ax.barh(y - .19, bv, .36, color=GRAY, label="Benchmark* (30% IVV / 30% KODEX 200 / 20% IEF / 20% KTB)")
for yi, p_, b_ in zip(y, pv, bv):
    for v_, off, col in [(p_, .19, INK), (b_, -.19, INK2)]:
        ax.text(v_ + (.3 if v_ >= 0 else -.3), yi + off, f"{v_:+.1f}%", va="center",
                ha="left" if v_ >= 0 else "right", fontsize=6.2, color=col)
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=6.8); ax.tick_params(axis="y", length=0)
ax.axvline(0, color=INK2, lw=.8); ax.set_xlim(-17, 14)
ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_xlabel("Scenario return in KRW (%)", fontsize=7)
ax.legend(frameon=False, fontsize=6.5, loc="lower left", ncol=2, bbox_to_anchor=(0, -.42))
ax.set_title("Stress tests (factor-shock scenarios, KRW base)", pad=4)
save(fig, "d3_stress")
print("charts ok")

# 9-10. Optimiser findings --------------------------------------------------------
O = json.load(open("data/results_opt.json"))
MS = O["methods"]
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
save(fig, "d3_methods")

keysO = O["keys"]; wf = np.array(O["final"]); p5 = np.array(O["p5"]); p95 = np.array(O["p95"])
fig, ax = plt.subplots(figsize=(7.2, 2.2))
x = np.arange(len(keysO))
ax.vlines(x, p5 * 100, p95 * 100, color=BLUE, lw=5, alpha=.3,
          label=f"5–95% range, {O['n_draws']:.0f} re-optimisations with noisy μ (±2pp)")
ax.scatter(x, wf * 100, color=ORANGE, s=14, zorder=3, edgecolor="white", lw=.6, label="Final weight")
ax.set_xticks(x); ax.set_xticklabels([sh(k) for k in keysO], rotation=90, fontsize=5.2)
ax.tick_params(axis="x", length=0); ax.yaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_ylabel("Weight (%)", fontsize=7); ax.legend(frameon=False, fontsize=6, loc="upper left", ncol=2)
ax.set_ylim(0, 9)
ax.set_title("How much do weights move when expected returns are wrong?", pad=4, fontsize=8)
save(fig, "d3_stability")
print("opt charts ok")
