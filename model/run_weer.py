"""Stap 1-2: weerjaren kiezen en zonprofiel controleren."""
import numpy as np
import pandas as pd
import middelsee as m

k = m._knmi()
rows = []
for y in range(2005, 2026):
    x = m._uur(y, k)
    T = x["T"].values
    dag = pd.Series(T).groupby(np.arange(8760) // 24).mean()
    d3 = dag.rolling(3).mean().min()
    rows.append(dict(jaar=y, gem=T.mean(), graaduren15=np.maximum(0, 15 - T).sum(), min_uur=T.min(), min_dag=dag.min(), min_3dag=d3))
df = pd.DataFrame(rows).round(2)
df["t.o.v._mediaan_pct"] = (100 * (df.graaduren15 / df.graaduren15.median() - 1)).round(1)
print(df.to_string(index=False))

print("\nZonprofiel (kWh/kWp per jaar, mix %s)" % m.PV_MIX)
for y in [2010, 2015, 2018, 2021, 2022, 2023]:
    p = m.pv_profiel(y)
    print(y, "opbrengst %.0f, piek %.2f kW/kWp" % (p.sum(), p.max()))
ps = np.array([m.pv_profiel(y).sum() for y in range(2009, 2024)])
print("gemiddeld 2009-2023: %.0f (min %.0f, max %.0f)" % (ps.mean(), ps.min(), ps.max()))
p = pd.Series(m.pv_profiel(2023), index=m._uur(2023, k).index)
print("maandfractie 2023:", (p.groupby(p.index.month).sum() / p.sum()).round(3).tolist())
print("correlatie KNMI-straling en PVGIS-mix, 2020:", np.corrcoef(m._uur(2020, k)["Q"].fillna(0).values, m.pv_profiel(2020))[0, 1].round(3))

for y in [2021, 2023, 2024, 2025]:
    pr = m.prijzen(y)
    g, mg = m.co2_factoren(y)
    print(y, "prijs gem %.0f EUR/MWh, p5 %.0f, p95 %.0f, uren<0: %d | CO2 gem %.3f, marginaal gem %.3f" % (pr.mean(), np.percentile(pr, 5), np.percentile(pr, 95), (pr < 0).sum(), g.mean(), mg.mean()))
