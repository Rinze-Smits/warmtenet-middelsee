"""Stap 3, 4, 7, 9: alle scenario's over een normaal jaar (2017) en twee koude jaren (2012, 2010)."""
import multiprocessing as mp
import os
import sys
import time
import pandas as pd
import middelsee as m
from middelsee import warmtenet as W, individueel as I

PV = 15.0
SC = {
    # referentie individueel
    "A lucht": lambda j: (I(j), 0),
    "A lucht + PV": lambda j: (I(j, pv_mwp=PV), PV),
    "A lucht, slim laden": lambda j: (I(j, ev="lp"), 0),
    "A lucht, slim laden + boilers flex": lambda j: (I(j, ev="lp", dhw_flex_mwh=6.6), 0),
    "A lucht, slim laden + boilers + batterij 5 MWh": lambda j: (I(j, ev="lp", dhw_flex_mwh=6.6, bat_mwh=5, bat_mw=2.5), 0),
    "A bodem": lambda j: (I(j, bron="bodem"), 0),
    "A bodem + PV": lambda j: (I(j, bron="bodem", pv_mwp=PV), PV),
    "A bodem, slim laden": lambda j: (I(j, bron="bodem", ev="lp"), 0),
    "A bodem, slim laden + boilers flex": lambda j: (I(j, bron="bodem", ev="lp", dhw_flex_mwh=6.6), 0),
    # warmtenet
    "C net 65 (CO2-COP)": lambda j: (W(j), 0),
    "C net 65 (Carnot-COP)": lambda j: (W(j, methode="carnot"), 0),
    "C net 65, slim laden": lambda j: (W(j, ev="lp"), 0),
    "C net 65 + PV": lambda j: (W(j, pv_mwp=PV), PV),
    "C net 65 + PV (Carnot-COP)": lambda j: (W(j, pv_mwp=PV, methode="carnot"), PV),
    "E net 65 + PV + buffer 100 + eboiler 4": lambda j: (W(j, pv_mwp=PV, buf=100, eb=4), PV),
    "F net 65 + PV + buffer 100 + HTO 3 GWh": lambda j: (W(j, pv_mwp=PV, buf=100, eb=4, hto=3000), PV),
    "F net 65 + PV + buffer 100 + HTO 3 GWh, slim laden": lambda j: (W(j, pv_mwp=PV, buf=100, eb=4, hto=3000, ev="lp"), PV),
    "F HTO 3 GWh zonder PV, slim laden": lambda j: (W(j, buf=20, hto=3000, ev="lp"), 0),
    "F HTO, rendement 40 % (eerste jaren)": lambda j: (W(j, pv_mwp=PV, buf=100, eb=4, hto=3000, hto_eta=0.40), PV),
    # lagetemperatuur
    "G LT 50 + boosters": lambda j: (W(j, Tsup=50, Tret=25, verlies=0.19, booster=True, methode="carnot"), 0),
    "G LT 50 + boosters + PV": lambda j: (W(j, Tsup=50, Tret=25, verlies=0.19, booster=True, methode="carnot", pv_mwp=PV), PV),
    "G LT 50 + boosters, slim laden": lambda j: (W(j, Tsup=50, Tret=25, verlies=0.19, booster=True, methode="carnot", ev="lp"), 0),
    # opslag elektrisch of hoogwaardig
    "C net 65 + wijkbatterij 5 MWh/2,5 MW": lambda j: (W(j, bat_mwh=5, bat_mw=2.5), 0),
    "C net 65, slim laden + wijkbatterij 5 MWh": lambda j: (W(j, ev="lp", bat_mwh=5, bat_mw=2.5), 0),
    "C net 65 buffer 5 + basalt 50 MWh/3 MW": lambda j: (W(j, buf=5, basalt=50, basalt_mw=3), 0),
    # teruglevergrens
    "C net 65 + PV, terug max 5 MW": lambda j: (W(j, pv_mwp=PV, exp_lim=5.0), PV),
    "C net 65 + PV, terug max 3 MW": lambda j: (W(j, pv_mwp=PV, exp_lim=3.0), PV),
    "C net 65 + PV, terug 0": lambda j: (W(j, pv_mwp=PV, exp_lim=0.0), PV),
    "F HTO + PV, terug max 3 MW": lambda j: (W(j, pv_mwp=PV, buf=100, eb=4, hto=3000, exp_lim=3.0), PV),
    "A lucht + PV, terug max 5 MW": lambda j: (I(j, pv_mwp=PV, exp_lim=5.0), PV),
    "A lucht + PV, terug max 3 MW": lambda j: (I(j, pv_mwp=PV, exp_lim=3.0), PV),
}
for b in [0, 2, 5, 10, 15, 25, 30, 50, 100]:
    SC["buffer %d MWh" % b] = (lambda b: (lambda j: (W(j, buf=b), 0)))(b)
    SC["buffer %d MWh, slim laden" % b] = (lambda b: (lambda j: (W(j, buf=b, ev="lp"), 0)))(b)
for v in [0.15, 0.20, 0.30]:
    SC["verlies %d %%" % (v * 100)] = (lambda v: (lambda j: (W(j, verlies=v), 0)))(v)
    SC["verlies %d %% (Carnot)" % (v * 100)] = (lambda v: (lambda j: (W(j, verlies=v, methode="carnot"), 0)))(v)
for e in [0, 1, 4]:
    SC["eboiler %d MW" % e] = (lambda e: (lambda j: (W(j, eb=e), 0)))(e)

JAREN = [2017, 2012, 2010]


def job(a):
    naam, y = a
    t = time.time()
    j = m.Jaar(y)
    v, pv = SC[naam](j)
    o = m.samenvatting(naam, j, v, pv)
    o["rekentijd_s"] = round(time.time() - t, 1)
    print(naam, y, "piek %.2f, %ss" % (o["piek_afname_MW"], o["rekentijd_s"]), flush=True)
    return o


if __name__ == "__main__":
    taken = [(n, y) for n in SC for y in JAREN]
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print(job(("A lucht", 2017)))
        print(job(("C net 65 (CO2-COP)", 2012)))
        print(job(("F net 65 + PV + buffer 100 + HTO 3 GWh, slim laden", 2012)))
        sys.exit()
    with mp.Pool(max(2, (os.cpu_count() or 4) - 2)) as p:
        r = p.map(job, taken, chunksize=1)
    df = pd.DataFrame(r)
    df.to_csv(os.path.join(m.ROOT, "uitvoer/scenarios.csv"), index=False)
    print("klaar", len(df))
