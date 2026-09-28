"""Optimiser comparison + robustness for version 3. Writes results_opt_v3.json."""
import io, json, contextlib
import numpy as np
from scipy.optimize import minimize

g = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(open("src/model.py").read().replace("if __name__ == \"__main__\":", "if False:"), g)
S, m, N, keys, bounds, cons, rf = g["S"], g["m"], g["N"], g["keys"], g["bnds"], g["cons"], g["RF_KRW_CASH"]
w_final = g["w"]
hedge = g["hedge"]
kr = [i for i, a in enumerate(g["AS"]) if a["country"] == "KR"]


def stats(w):
    er, sd = w @ m, np.sqrt(w @ S @ w)
    rc = w * (S @ w) / (w @ S @ w)
    return dict(er=er, vol=sd, sharpe=(er - rf) / sd, maxw=w.max(), effn=1 / np.sum(w ** 2),
                maxrc=rc.max(), effn_risk=1 / np.sum(rc ** 2), hedge=w[hedge].sum(), korea=w[kr].sum())


neg_sr = lambda w: -(w @ m - rf) / np.sqrt(w @ S @ w)
budget = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
w_eq = np.ones(N) / N
out = {}
out["1/N equal weight"] = w_eq
out["Long-only max Sharpe"] = minimize(neg_sr, w_eq, bounds=[(0, 1)] * N, constraints=budget, method="SLSQP",
                                       options={"maxiter": 2000, "ftol": 1e-12}).x
rb = [(0, 0) if k == "KCD" else (0, 1) for k in keys]
out["Minimum variance"] = minimize(lambda w: w @ S @ w, w_eq, bounds=rb, constraints=budget, method="SLSQP",
                                   options={"maxiter": 2000, "ftol": 1e-14}).x
rcv = lambda w: w * (S @ w) / (w @ S @ w)
w0 = np.where(np.array(keys) == "KCD", 0, 1 / (N - 1))
rpb = [(0, 0) if k == "KCD" else (1e-4, 1) for k in keys]
out["Risk parity"] = minimize(lambda w: np.sum((rcv(w)[w > 0] - 1 / (N - 1)) ** 2) * 1e4, w0, bounds=rpb,
                              constraints=budget, method="SLSQP", options={"maxiter": 3000, "ftol": 1e-14}).x
out["Final (mandate + RP penalty)"] = w_final
excess = m - rf
sr_max = float(np.sqrt(excess @ np.linalg.solve(S, excess)))
w_dir = np.linalg.solve(S, excess); w_tan = w_dir * .067 / np.sqrt(w_dir @ S @ w_dir)
tangency = dict(sr=sr_max, gross=float(np.abs(w_tan).sum()))


def objective(w, lam, mv):
    rc = w * (S @ w); rc = rc / rc.sum()
    return -(w @ mv - rf) / np.sqrt(w @ S @ w) + lam * N * np.sum((rc - rc.mean()) ** 2)


def opt(lam=.5, mv=m):
    x0 = np.array([np.mean(b) for b in bounds]); x0 /= x0.sum()
    return minimize(objective, x0, args=(lam, mv), bounds=bounds, constraints=cons, method="SLSQP",
                    options={"maxiter": 5000, "ftol": 1e-12})


lam_tab = {}
for lam in [0, .25, .5, 1, 5]:
    lam_tab[str(lam)] = stats(opt(lam).x)
rng = np.random.default_rng(42)
draws = []
for _ in range(100):
    r = opt(mv=m + rng.normal(0, .02, N))
    if r.success:
        draws.append(r.x)
draws = np.array(draws)
res = dict(methods={k: dict(stats(v), weights=v.tolist()) for k, v in out.items()}, tangency=tangency,
           lam=lam_tab, keys=keys, final=w_final.tolist(), n_draws=len(draws),
           p5=np.percentile(draws, 5, 0).tolist(), p95=np.percentile(draws, 95, 0).tolist(),
           mean=draws.mean(0).tolist(),
           avg_band=float(np.mean(np.percentile(draws, 95, 0) - np.percentile(draws, 5, 0))))


def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)): return float(o)
    return o


json.dump(clean(res), open("data/results_opt.json", "w"), indent=1)
for k, v in res["methods"].items():
    print(f"{k:30s} ER {v['er']:.2%} vol {v['vol']:.2%} SR {v['sharpe']:.2f} maxw {v['maxw']:.1%} effN {v['effn']:.1f} maxRC {v['maxrc']:.1%} hedge {v['hedge']:.1%}")
print("tangency", tangency)
for k, v in lam_tab.items():
    print("lam", k, f"SR {v['sharpe']:.3f} vol {v['vol']:.2%} maxrc {v['maxrc']:.1%} effn {v['effn']:.1f}")
print("draws", len(draws), "avg 5-95 band", res["avg_band"])
