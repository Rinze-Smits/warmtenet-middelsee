"""
Warmteprofielen van de TNO-generator (Wiarda, 262 woningen na 2014, weer Eelde 2013, opgeschaald naar 1.647 woningen) in het eigen model.
Ruimteverwarming komt uit de generator; tapwater, utiliteit, huishoudens en laden blijven eigen aannames.
'tno': jaarvraag van de generator. '12gj': alleen de vorm, geschaald naar 12 GJ per woning uit de brochureaanname (x weerfactor 2013).
"""
import json, os
import numpy as np, pandas as pd
import middelsee as m
D = os.path.join(m.ROOT, "data/energynl")
RUN = {"lucht": 6204, "bodem": 6205, "net": 6206}
N_WIARDA = 262


def profiel(job):
    u = json.load(open(os.path.join(D, "res%d.json" % job)))["user_job_results"]["timeseries"]
    h = np.array([x["value"] for x in u["heat_profile"]], float) / 1e6  # Wh per uur -> MW
    T = np.array([x["value"] for x in u["outside_temperature"]], float)
    # eerste waarde is 2012-12-31 23:00 UT; schuif een uur op zodat de index gelijk loopt met 2013 UT
    return np.roll(h, -1) * m.N_WON / N_WIARDA, np.roll(T, -1)


def jaar(job, schaal):
    j = m.Jaar(2013)
    eigen = j.sh_won.sum()
    h, T = profiel(job)
    j.Tair = T
    j.sh_won = h if schaal == "tno" else h / h.sum() * eigen
    return j


S = {"Lucht-water": ("lucht", lambda j: m.individueel(j)), "Lucht-water + slim + boilers": ("lucht", lambda j: m.individueel(j, ev="lp", dhw_flex_mwh=6.6)),
     "Lucht-water + slim + boilers + batterij": ("lucht", lambda j: m.individueel(j, ev="lp", dhw_flex_mwh=6.6, bat_mwh=5, bat_mw=2.5)),
     "Bodem": ("bodem", lambda j: m.individueel(j, bron="bodem")), "Bodem + slim + boilers": ("bodem", lambda j: m.individueel(j, bron="bodem", ev="lp", dhw_flex_mwh=6.6)),
     "Warmtenet, buffer 0": ("net", lambda j: m.warmtenet(j, buf=0)), "Warmtenet, buffer 5": ("net", lambda j: m.warmtenet(j, buf=5)), "Warmtenet, buffer 10": ("net", lambda j: m.warmtenet(j, buf=10)),
     "Warmtenet, buffer 20": ("net", lambda j: m.warmtenet(j)), "Warmtenet, buffer 30": ("net", lambda j: m.warmtenet(j, buf=30)), "Warmtenet, buffer 50": ("net", lambda j: m.warmtenet(j, buf=50)),
     "Warmtenet + slim, buffer 5": ("net", lambda j: m.warmtenet(j, buf=5, ev="lp")), "Warmtenet + slim, buffer 20": ("net", lambda j: m.warmtenet(j, ev="lp"))}
r = []
j0 = m.Jaar(2013)
print("eigen profiel 2013: %.1f GJ/woning, piek %.2f MW" % (j0.sh_won.sum() * 3.6 / m.N_WON, j0.sh_won.max()))
for k, job in RUN.items():
    h, T = profiel(job)
    print(k, "TNO: %.1f GJ/woning, piek warmte %.2f MW (%.2f kW/woning), gem. per etmaal max %.2f MW; koudste uur %.1f C" % (h.sum() * 3.6 / m.N_WON, h.max(), 1e3 * h.max() / m.N_WON, h.reshape(365, 24).mean(1).max(), T.min()))
for sch in ("tno", "12gj"):
    for n, (k, f) in S.items():
        j = jaar(RUN[k], sch)
        try:
            v = f(j)
            r.append(dict(schaal=sch, variant=n, piek=v["net"].max(), stroom_warmte=v["warmte_el"].sum() / 1e3, D_max=(j.D_core).max(), eboiler=v["e"].sum(), q_max=v["q"].max()))
        except RuntimeError as e:
            r.append(dict(schaal=sch, variant=n, piek=np.nan, stroom_warmte=np.nan))
            print("onoplosbaar", sch, n, e)
for n, f in [("Lucht-water", lambda j: m.individueel(j)), ("Lucht-water + slim + boilers", lambda j: m.individueel(j, ev="lp", dhw_flex_mwh=6.6)), ("Lucht-water + slim + boilers + batterij", lambda j: m.individueel(j, ev="lp", dhw_flex_mwh=6.6, bat_mwh=5, bat_mw=2.5)),
             ("Bodem", lambda j: m.individueel(j, bron="bodem")), ("Bodem + slim + boilers", lambda j: m.individueel(j, bron="bodem", ev="lp", dhw_flex_mwh=6.6)),
             ("Warmtenet, buffer 20", lambda j: m.warmtenet(j)), ("Warmtenet + slim, buffer 20", lambda j: m.warmtenet(j, ev="lp"))]:
    j = m.Jaar(2013); v = f(j)
    r.append(dict(schaal="eigen profiel", variant=n, piek=v["net"].max(), stroom_warmte=v["warmte_el"].sum() / 1e3, D_max=j.D_core.max(), eboiler=v["e"].sum(), q_max=v["q"].max()))
d = pd.DataFrame(r); d.round(3).to_csv(os.path.join(m.ROOT, "uitvoer/wpg_scenarios.csv"), index=False)
pd.set_option("display.width", 200)
print(d.pivot_table(index="variant", columns="schaal", values=["piek", "stroom_warmte"], sort=False).round(2).to_string())
print(d[d.variant.str.startswith("Warmtenet")][["schaal", "variant", "D_max", "eboiler", "q_max"]].round(2).to_string(index=False))
