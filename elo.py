"""Global Elo with cross-league calibration + Poisson goal model + honest backtest."""
import json, math, sys
from collections import defaultdict
import numpy as np
from scipy.optimize import minimize

M = json.load(open("matches_canon.json"))
M.sort(key=lambda m: m["d"])
DOM = {"ENG1", "GER1", "ESP1", "ITA1", "FRA1", "NED1", "POR1"}
EURO = {"CL", "CLQ", "EL", "ELQ", "UECL", "UECLQ"}
CUT = "2024-07-01"      # backtest cut-off
TUNE_FROM = "2015-07-01"

lg_teams = defaultdict(set)
for m in M:
    if m["comp"] in DOM:
        lg_teams[(m["comp"], m["s"])].update([m["hid"], m["aid"]])
first_idx = {}
for i, m in enumerate(M):
    if m["comp"] in DOM:
        first_idx.setdefault((m["comp"], m["s"]), i)

LN10 = math.log(10)


def G(gd):
    gd = abs(gd)
    return 1.0 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8.0)


def run(Kd, Ke, HFA, off, res_until=None, tune_window=None):
    R = {}
    pre = [None] * len(M)
    rsum = defaultdict(float)
    rcnt = defaultdict(int)
    err = 0.0
    n_err = 0
    started = set()
    for i, m in enumerate(M):
        comp = m["comp"]
        if comp in DOM:
            key = (comp, m["s"])
            if key not in started and first_idx[key] == i:
                started.add(key)
                cur = lg_teams[key]
                prev = lg_teams.get((comp, m["s"] - 1))
                newc = [t for t in cur if t not in R]
                if newc:
                    base = None
                    if prev:
                        rel = [R[t] for t in prev - cur if t in R]
                        if rel:
                            base = sum(rel) / len(rel)
                    for t in newc:
                        c = t.split(":")[0]
                        R[t] = base if base is not None else 1500 + off.get(c, 0.0)
        h, a = m["hid"], m["aid"]
        for t in (h, a):
            if t not in R:
                R[t] = 1500 + off.get(t.split(":")[0], 0.0)
        rh, ra = R[h], R[a]
        hfa = 0.0 if m["n"] else HFA
        E = 1.0 / (1.0 + 10 ** (-(rh - ra + hfa) / 400.0))
        gd = m["hg"] - m["ag"]
        S = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        pre[i] = (rh, ra, E)
        K = Kd if comp in DOM else Ke
        d = K * G(gd) * (S - E)
        R[h] = rh + d
        R[a] = ra - d
        if comp in EURO and (res_until is None or m["d"] < res_until):
            r = S - E
            rsum[m["hc"]] += r
            rcnt[m["hc"]] += 1
            rsum[m["ac"]] -= r
            rcnt[m["ac"]] += 1
        if tune_window and tune_window[0] <= m["d"] < tune_window[1]:
            err += (S - E) ** 2
            n_err += 1
    return R, pre, rsum, rcnt, (err / n_err if n_err else None)


def fit_offsets(Kd, Ke, HFA, iters=14, res_until=None, off=None, verbose=False):
    off = defaultdict(float, off or {})
    for it in range(iters):
        R, pre, rsum, rcnt, _ = run(Kd, Ke, HFA, off, res_until)
        mx = 0.0
        for c, n in rcnt.items():
            if n < 20 or c == "UNK":
                continue
            step = 0.7 * (rsum[c] / n) / 0.0014 * (n / (n + 40.0))
            off[c] += step
            if c in ("ENG", "GER", "ESP", "ITA", "FRA", "NED", "POR"):
                mx = max(mx, abs(step))
        if verbose:
            print(f"  iter {it+1}: max big-league step {mx:.1f}")
        if mx < 1.0:
            break
    return off


# ---------- 1) tune K / HFA (offsets from default config, pre-cutoff only)
print("fitting offsets (default params, pre-cutoff data only) ...")
off0 = fit_offsets(20, 25, 70, res_until=CUT, verbose=True)
best = None
for Kd in (6, 8, 10, 12, 14, 16):
    for Ke in (8, 12, 16, 20):
        for HFA in (50, 60, 70):
            *_, mse = run(Kd, Ke, HFA, off0, CUT, (TUNE_FROM, CUT))
            if best is None or mse < best[0]:
                best = (mse, Kd, Ke, HFA)
print("best grid:", best)
_, Kd, Ke, HFA = best
off_bt = fit_offsets(Kd, Ke, HFA, off=off0, res_until=CUT)

# ---------- 2) Poisson fit helpers
def build_xy(pre, lo, hi):
    X, hg, ag = [], [], []
    for m, p in zip(M, pre):
        if lo <= m["d"] < hi:
            hfa = 0.0 if m["n"] else HFA
            X.append((p[0] - p[1] + hfa) / 400.0)
            hg.append(m["hg"])
            ag.append(m["ag"])
    return np.array(X), np.array(hg), np.array(ag)


def fit_poisson(X, hg, ag):
    def nll(th):
        ah, aa, b = th
        lh = np.exp(ah + b * X)
        la = np.exp(aa - b * X)
        return float(np.sum(lh - hg * np.log(lh) + la - ag * np.log(la)))
    r = minimize(nll, [0.3, 0.1, 0.5], method="BFGS")
    return r.x


def tau(x, y, lh, la, rho):
    if x == 0 and y == 0: return 1 - lh * la * rho
    if x == 0 and y == 1: return 1 + lh * rho
    if x == 1 and y == 0: return 1 + la * rho
    if x == 1 and y == 1: return 1 - rho
    return 1.0


def fit_rho(X, hg, ag, th):
    ah, aa, b = th
    lh = np.exp(ah + b * X); la = np.exp(aa - b * X)
    best = (-1e18, 0.0)
    for rho in np.linspace(-0.25, 0.1, 36):
        ll = 0.0
        for k in range(len(X)):
            if hg[k] <= 1 and ag[k] <= 1:
                t = tau(hg[k], ag[k], lh[k], la[k], rho)
                if t <= 0: ll = -1e18; break
                ll += math.log(t)
        if ll > best[0]:
            best = (ll, rho)
    return best[1]


MAXG = 10
FACT = [math.factorial(i) for i in range(MAXG + 1)]


def probs(lh, la, rho):
    P = np.zeros((MAXG + 1, MAXG + 1))
    for x in range(MAXG + 1):
        for y in range(MAXG + 1):
            P[x, y] = math.exp(-lh) * lh ** x / FACT[x] * math.exp(-la) * la ** y / FACT[y] * tau(x, y, lh, la, rho)
    P /= P.sum()
    return P


def outcome_probs(P):
    h = float(np.tril(P, -1).sum()); d = float(np.trace(P)); a = float(np.triu(P, 1).sum())
    return h, d, a


# ---------- 3) honest backtest
R_bt, pre_bt, *_ = run(Kd, Ke, HFA, off_bt, CUT)
Xtr, htr, atr = build_xy(pre_bt, "2013-07-01", CUT)
th_bt = fit_poisson(Xtr, htr, atr)
rho_bt = fit_rho(Xtr, htr, atr, th_bt)
print("train params (pre-cutoff):", np.round(th_bt, 3), "rho", round(rho_bt, 3), "n", len(Xtr))
# baseline: outcome frequencies in training window (home/draw/away)
tr = [(m["hg"], m["ag"]) for m, p in zip(M, pre_bt) if "2013-07-01" <= m["d"] < CUT]
fr = np.array([sum(1 for x, y in tr if x > y), sum(1 for x, y in tr if x == y), sum(1 for x, y in tr if x < y)], float)
fr /= fr.sum()
ll_m = ll_b = 0.0; n = 0; hit = 0; hit_b = 0
rows = []
for m, p in zip(M, pre_bt):
    if m["d"] >= CUT and (m["comp"] in DOM or m["comp"] in ("CL", "EL", "UECL")):
        hfa = 0.0 if m["n"] else HFA
        x = (p[0] - p[1] + hfa) / 400.0
        lh, la = math.exp(th_bt[0] + th_bt[2] * x), math.exp(th_bt[1] - th_bt[2] * x)
        ph, pd, pa = outcome_probs(probs(lh, la, rho_bt))
        o = 0 if m["hg"] > m["ag"] else (1 if m["hg"] == m["ag"] else 2)
        pm = (ph, pd, pa)[o]
        ll_m += -math.log(max(pm, 1e-9)); ll_b += -math.log(fr[o]); n += 1
        hit += int(max(range(3), key=lambda k: (ph, pd, pa)[k]) == o)
        hit_b += int(o == 0)
        rows.append((ph, pd, pa, o, m["comp"]))
print(f"BACKTEST on {n} matches since {CUT}: model log-loss {ll_m/n:.4f} vs baseline {ll_b/n:.4f} "
      f"({(1-ll_m/ll_b)*100:.1f}% better) | top-pick accuracy {hit/n:.3f} vs always-home {hit_b/n:.3f}")
# calibration table for home win prob
bins = defaultdict(lambda: [0, 0.0, 0])
for ph, pd, pa, o, c in rows:
    b = min(int(ph * 10), 9)
    bins[b][0] += 1; bins[b][1] += ph; bins[b][2] += int(o == 0)
print("calibration (home win): predicted -> actual")
for b in sorted(bins):
    c, sp, w = bins[b]
    if c >= 25:
        print(f"  {sp/c:.2f} -> {w/c:.2f}  (n={c})")

# ---------- 4) production fit on all data
print("\nproduction fit (all data) ...")
off = fit_offsets(Kd, Ke, HFA, off=off_bt, res_until=None, verbose=True)
R, pre, *_ = run(Kd, Ke, HFA, off, None)
X, hg, ag = build_xy(pre, "2013-07-01", "2100-01-01")
th = fit_poisson(X, hg, ag)
rho = fit_rho(X, hg, ag, th)
print("production poisson:", np.round(th, 4), "rho", round(rho, 3), "| K_dom", Kd, "K_eur", Ke, "HFA", HFA)
print("country offsets:", {c: round(v) for c, v in sorted(off.items(), key=lambda kv: -kv[1]) if c in ("ENG", "ESP", "GER", "ITA", "FRA", "DEN", "POR", "NED", "BEL", "SCO", "TUR", "NOR", "SWE", "AUT", "SUI", "CRO", "GRE", "POL")})

json.dump(dict(R=R, pre=pre, off=dict(off), params=dict(Kd=Kd, Ke=Ke, HFA=HFA, ah=th[0], aa=th[1], b=th[2], rho=rho)), open("elo_out.json", "w"))
json.dump(dict(n=n, ll_model=ll_m / n, ll_base=ll_b / n, acc=hit / n, acc_home=hit_b / n, cut=CUT), open("backtest.json", "w"))

# sanity: top ratings among teams active in 2025-26 domestic
teams = json.load(open("teams.json"))
cur = set()
for k in (("ENG1", 2025), ("GER1", 2025), ("ESP1", 2025), ("ITA1", 2025), ("FRA1", 2025), ("NED1", 2025), ("POR1", 2025)):
    cur |= lg_teams[k]
top = sorted(((R[t], teams[t]["raw"], teams[t]["country"]) for t in cur), reverse=True)
print("\nTOP 25 (active big-4 league teams):")
for r, nme, c in top[:25]:
    print(f"  {r:6.0f}  {nme} ({c})")
print("BOTTOM 5:", [(round(r), nme) for r, nme, c in top[-5:]])
for c in ("ENG", "GER", "ESP", "ITA", "FRA", "NED", "POR"):
    v = [R[t] for t in cur if t.startswith(c + ":")]
    print(f"league mean {c}: {sum(v)/len(v):.0f} (n={len(v)})")
