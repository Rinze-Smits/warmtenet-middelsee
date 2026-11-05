"""Warmtenet met vergelijkbaar woningvermogen (4, 6, 10 kW) naast lucht-water en bodem (3,5 kW), Wiarda-profielen, weer Eelde 2013."""
import os
import numpy as np, pandas as pd
import middelsee as m
from run_wpg_basis import profiel, jaar
r, inf = [], []
for naam, job in [("lucht 3,5 kW", 6204), ("bodem 3,5 kW", 6205), ("net 4 kW", 6207), ("net 6 kW", 6208), ("net 10 kW", 6206)]:
    h, T = profiel(job)
    inf.append(dict(profiel=naam, GJ_woning=h.sum() * 3.6 / m.N_WON, piek_MW=h.max(), kW_woning=1e3 * h.max() / m.N_WON, etmaal_max_MW=h.reshape(365, 24).mean(1).max(), piek_gem=h.max() / h.mean()))
print(pd.DataFrame(inf).round(2).to_string(index=False))
def W(job, sch, **k):
    j = jaar(job, sch)
    try:
        v = m.warmtenet(j, **k)
        return v["net"].max(), v["warmte_el"].sum() / 1e3, v["e"].sum()
    except RuntimeError:
        return np.nan, np.nan, np.nan
def I(job, sch, **k):
    v = m.individueel(jaar(job, sch), **k)
    return v["net"].max(), v["warmte_el"].sum() / 1e3, 0.0
T = [("Lucht-water", lambda s: I(6204, s)), ("Lucht-water + slim + boilers", lambda s: I(6204, s, ev="lp", dhw_flex_mwh=6.6)),
     ("Lucht-water + slim + boilers + batterij", lambda s: I(6204, s, ev="lp", dhw_flex_mwh=6.6, bat_mwh=5, bat_mw=2.5)),
     ("Bodem", lambda s: I(6205, s, bron="bodem")), ("Bodem + slim + boilers", lambda s: I(6205, s, bron="bodem", ev="lp", dhw_flex_mwh=6.6))]
for jb, kw in [(6207, 4), (6208, 6), (6206, 10)]:
    for b in [5, 10, 20, 30, 50]:
        T.append(("Net %d kW, buffer %d" % (kw, b), (lambda jb, b: (lambda s: W(jb, s, buf=b)))(jb, b)))
    T.append(("Net %d kW + slim, buffer 20" % kw, (lambda jb: (lambda s: W(jb, s, ev="lp")))(jb)))
    T.append(("Net %d kW + slim, buffer 5" % kw, (lambda jb: (lambda s: W(jb, s, buf=5, ev="lp")))(jb)))
for n, f in T:
    for s in ("tno", "12gj"):
        p, g, e = f(s)
        r.append(dict(variant=n, schaal=s, piek=p, stroom_warmte=g, eboiler=e))
d = pd.DataFrame(r); d.round(3).to_csv(os.path.join(m.ROOT, "uitvoer/wpg_scenarios2.csv"), index=False)
pd.set_option("display.width", 180)
print(d.pivot_table(index="variant", columns="schaal", values=["piek", "stroom_warmte"], sort=False).round(2).to_string())
