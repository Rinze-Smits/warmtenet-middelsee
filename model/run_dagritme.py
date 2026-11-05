"""
Stresstest: de ruimteverwarming krijgt een dagritme (nachtverlaging, opwarmen in ochtend en avond).
Het basismodel volgt alleen de buitentemperatuur. De vormen zijn eigen aannames, geen uitvoer van de Warmteprofielengenerator.
"""
import os
import numpy as np
import pandas as pd
import middelsee as m

TNO = pd.read_csv(os.path.join(m.ROOT, "uitvoer/wpg_dagvorm_job6075.csv"), index_col=0)["koud (<0 C)"].values  # Zuiderburen, Eelde 2013
VORM = {
    "geen (basis)": None,
    "mild": {"nacht": 0.85, "ochtend": 1.25, "dag": 0.95, "avond": 1.10},
    "sterk": {"nacht": 0.60, "ochtend": 1.70, "dag": 0.90, "avond": 1.30},
    "TNO Zuiderburen": TNO,
}


def pas_toe(j, v):
    if v is None:
        return
    if isinstance(v, np.ndarray):
        f = v[j.hod]
    else:
        f = np.select([(j.hod >= 23) | (j.hod < 5), (j.hod >= 5) & (j.hod < 9), (j.hod >= 9) & (j.hod < 17)], [v["nacht"], v["ochtend"], v["dag"]], v["avond"])
    # per etmaal normaliseren: de warmtevraag per dag blijft gelijk
    x = j.sh_won * f
    dag = np.arange(8760) // 24
    som = np.bincount(dag, j.sh_won) / np.maximum(np.bincount(dag, x), 1e-9)
    j.sh_won = x * som[dag]


S = {"Lucht-water": lambda j: m.individueel(j), "Lucht-water + slim + boilers": lambda j: m.individueel(j, ev="lp", dhw_flex_mwh=6.6),
     "Bodem": lambda j: m.individueel(j, bron="bodem"), "Bodem + slim + boilers": lambda j: m.individueel(j, bron="bodem", ev="lp", dhw_flex_mwh=6.6),
     "Warmtenet, buffer 5": lambda j: m.warmtenet(j, buf=5), "Warmtenet, buffer 20": lambda j: m.warmtenet(j), "Warmtenet, buffer 30": lambda j: m.warmtenet(j, buf=30),
     "Warmtenet + slim, buffer 5": lambda j: m.warmtenet(j, buf=5, ev="lp"), "Warmtenet + slim, buffer 20": lambda j: m.warmtenet(j, ev="lp")}
r = []
for y in (2017, 2012):
    for vn, v in VORM.items():
        for n, f in S.items():
            j = m.Jaar(y)
            pas_toe(j, v)
            r.append(dict(jaar=y, dagritme=vn, variant=n, piek=f(j)["net"].max()))
    for tr in (1, 6):
        for n, f in S.items():
            j = m.Jaar(y, traagheid=tr)
            r.append(dict(jaar=y, dagritme="traagheid %d u" % tr, variant=n, piek=f(j)["net"].max()))
d = pd.DataFrame(r)
d.round(3).to_csv(os.path.join(m.ROOT, "uitvoer/dagritme.csv"), index=False)
pd.set_option("display.width", 200)
print(d.pivot_table(index="variant", columns=["jaar", "dagritme"], values="piek", sort=False).round(2).to_string())
