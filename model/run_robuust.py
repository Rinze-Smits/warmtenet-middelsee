"""
Stap 10: hoe afhankelijk is de piekreductie van perfecte voorkennis?
1. Vermogensgrens: de centrale houdt de wijk onder een vaste grens en houdt de buffer zo vol mogelijk. Geen voorspelling nodig.
   De grens wordt vooraf vastgelegd op het normale jaar; daarna draait de regelaar op koude jaren.
2. Rollend LP: 48 uur vooruit, elk uur opnieuw, met voorspelfouten in temperatuur en overige vraag.
"""
import os
import sys
import multiprocessing as mp
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog
import middelsee as m


def invoer(j, verlies=0.25, methode="co2", ev="ongestuurd"):
    D0 = j.D_core
    D = D0 + D0.sum() / (1 - verlies) * verlies / 8760
    cop = m.cop_centraal(j, 65, 30, methode)
    L = j.hh + j.util_el + m._ev(j, ev) + 0.015 * D
    return D, cop, L


def grens_regelaar(D, cop, L, buf, tau, qmax=7.5, eta=0.002):
    """Warmtepomp mag draaien tot de wijk op tau zit, en vult dan de buffer. Tekort aan warmte wordt alsnog geleverd (overschrijding)."""
    s = buf
    net = np.zeros(len(D))
    for t in range(len(D)):
        s *= (1 - eta)
        ruimte = max(tau - L[t], 0.0) * cop[t]
        q = min(ruimte, qmax, D[t] + (buf - s))
        s2 = s + q - D[t]
        if s2 < 0:
            q += -s2  # buffer leeg: warmte moet toch geleverd worden
            s2 = 0.0
        s = min(s2, buf)
        net[t] = L[t] + q / cop[t]
    return net


def kleinste_grens(D, cop, L, buf):
    lo, hi = L.max() * 0.5, (L + D / cop).max()
    for _ in range(30):
        mid = (lo + hi) / 2
        if grens_regelaar(D, cop, L, buf, mid).max() <= mid + 1e-4:
            hi = mid
        else:
            lo = mid
    return hi


def rollend(j, buf=20.0, H=48, sd_T=0.25, sd_L=0.03, seed=1, start=None, stop=None, eb=2.0, pk0=0.0, rho=0.97):
    """Elk uur: los H uur vooruit op met voorspelde vraag; voer alleen het eerste uur uit met de werkelijke vraag."""
    rng = np.random.default_rng(seed)
    D, cop, L = invoer(j)
    sf = j.sh_won.sum() / np.maximum(0, 15 - j.Teff).sum()
    N = len(D)
    t0, t1 = (0, N) if start is None else (start, stop)
    s = buf * 0.5
    pk = pk0
    eps = rng.normal(0, 1)
    net = np.full(N, np.nan)
    A_b = None
    for t in range(t0, t1):
        idx = (t + np.arange(H)) % N
        # voorspelling wordt langzaam bijgesteld (rho per uur); rho=0 geeft een nieuwe, onafhankelijke fout per uur
        eps = rho * eps + np.sqrt(1 - rho ** 2) * rng.normal(0, 1)
        e_T = sd_T * np.sqrt(np.arange(H)) * eps
        dD = sf * (np.maximum(0, 15 - (j.Teff[idx] + e_T)) - np.maximum(0, 15 - j.Teff[idx]))
        Df = np.maximum(D[idx] + dD, 0.0)
        # voorspelfout loopt door in de tijd: een gemeenschappelijke afwijking die groeit met de horizon
        e_L = np.minimum(sd_L * np.sqrt(np.arange(H)), 0.10) * eps
        Lf = L[idx] * (1 + e_L)
        # variabelen: q(H), e(H), s(H), imp(H), pk
        # met grens: het huidige uur blijft onder de grens, tenzij de buffer op is (variabele io, zwaar beboet)
        n = 4 * H + 2
        iq, ie, isx, ii, ip, io = np.arange(H), H + np.arange(H), 2 * H + np.arange(H), 3 * H + np.arange(H), 4 * H, 4 * H + 1
        r = np.arange(H)
        rows = np.r_[r, r, r, r[1:], H + r, H + r, H + r]
        cols = np.r_[iq, ie, isx, isx[:-1], ii, iq, ie]
        vals = np.r_[np.ones(H), np.ones(H), -np.ones(H), np.full(H - 1, 1 - 0.002), np.ones(H), -1 / cop[idx], -np.ones(H)]
        Aeq = sparse.csr_matrix((vals, (rows, cols)), shape=(2 * H, n))
        b = np.r_[Df, Lf]
        b[0] -= s * (1 - 0.002)
        kol = np.full(H, ip)
        if pk0 > 0:
            kol[0] = io
        Aub = sparse.csr_matrix((np.r_[np.ones(H), -np.ones(H)], (np.r_[r, r], np.r_[ii, kol])), shape=(H, n))
        bu = np.zeros(H)
        if pk0 > 0:
            bu[0] = pk
        c = np.zeros(n)
        c[ii] = 1.0; c[ip] = 3000.0; c[ie] = 0.01; c[io] = 20000.0
        c[isx[-1]] = -0.2  # restwaarde aan het eind van de horizon
        if pk0 > 0:
            c[isx] -= 0.2 / H  # regel bij een grens: houd de buffer vol zolang de wijk eronder zit
        bounds = [(0, 7.5)] * H + [(0, eb)] * H + [(0, buf)] * H + [(0, None)] * H + [(pk, None), (0, None)]
        res = linprog(c, A_ub=Aub, b_ub=bu, A_eq=Aeq, b_eq=b, bounds=bounds, method="highs")
        if res.status != 0:
            q0, e0 = max(0.0, D[t] - s), 0.0
        else:
            q0, e0 = res.x[iq[0]], res.x[ie[0]]
        s2 = s * (1 - 0.002) + q0 + e0 - D[t]
        if s2 < 0:
            q0 += -s2; s2 = 0.0
        s = min(s2, buf)
        net[t] = L[t] + q0 / cop[t] + e0
        pk = max(pk, net[t])
    return net


def job_rollend(a):
    y, buf, seed, pk0, rho = a
    j = m.Jaar(y)
    # winter: tot 1 april en vanaf 1 november; de piek van het warmtenet valt daarin
    n1 = rollend(j, buf=buf, seed=seed, start=0, stop=24 * 90, pk0=pk0, rho=rho)
    n2 = rollend(j, buf=buf, seed=seed + 1, start=24 * 304, stop=8760, pk0=pk0, rho=rho)
    p = np.nanmax(np.r_[n1[:24 * 90], n2[24 * 304:]])
    print("rollend", y, buf, seed, pk0, rho, round(p, 2), flush=True)
    return dict(jaar=y, buffer=buf, seed=seed, grens_vooraf=pk0, rho=rho, piek_rollend=p)


if __name__ == "__main__":
    rows = []
    for buf in [0.01, 5, 10, 15, 20, 30, 50]:
        for met in ["co2", "carnot"]:
            jn = m.Jaar(2017)
            Dn, cn, Ln = invoer(jn, methode=met)
            tau = kleinste_grens(Dn, cn, Ln, buf)
            o = dict(buffer=buf, cop=met, grens_2017=tau)
            for y in [2017, 2012, 2010, 2021, 2013, 2018]:
                j = m.Jaar(y)
                D, c, L = invoer(j, methode=met)
                o["piek_%d_vaste_grens" % y] = grens_regelaar(D, c, L, buf, tau).max()
                if y != 2017:
                    o["min_grens_%d" % y] = kleinste_grens(D, c, L, buf)
            rows.append(o)
    d = pd.DataFrame(rows).round(2)
    d.to_csv(os.path.join(m.ROOT, "uitvoer/robuust_grens.csv"), index=False)
    pd.set_option("display.width", 220)
    print(d.to_string(index=False))
    if len(sys.argv) > 1 and sys.argv[1] == "grens":
        sys.exit()
    grens = {5: 3.11, 10: 2.76, 20: 2.43, 30: 2.43}  # kleinste grens normaal jaar, CO2-COP
    taken = [(y, b, s, grens[b], 0.97) for y in [2012, 2017] for b in [5, 10, 20, 30] for s in [1, 11, 21]]
    taken += [(y, b, s, 0.0, 0.97) for y in [2012, 2017] for b in [20] for s in [1, 11, 21]]
    taken += [(y, b, s, 0.0, 0.0) for y in [2012, 2017] for b in [20] for s in [1, 11, 21]]
    with mp.Pool(max(2, (os.cpu_count() or 4) - 2)) as p:
        r = p.map(job_rollend, taken, chunksize=1)
    pd.DataFrame(r).round(3).to_csv(os.path.join(m.ROOT, "uitvoer/robuust_rollend.csv"), index=False)
    print(pd.DataFrame(r).groupby(["jaar", "buffer", "grens_vooraf", "rho"]).piek_rollend.agg(["mean", "min", "max"]).round(2))
