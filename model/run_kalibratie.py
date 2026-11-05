"""Stap 3: zijn 'maximaal 1 MW' en 'twee keer zoveel woningen' te reproduceren, en onder welke aannames?"""
import os
import numpy as np
import pandas as pd
import middelsee as m

rows = []
for y in [2017, 2012, 2010]:
    j = m.Jaar(y)
    cs, cd = m.cop_lucht_ind(j)
    back = np.where(j.Tair < -7, 0.2, 0.0)
    el_won = j.sh_won * (1 - back) / cs + j.sh_won * back + j.dhw_won / cd
    bs, bd = m.cop_bodem_ind(j)
    el_bod = j.sh_won / bs + j.dhw_won / bd + 0.01 * j.sh_won
    i = int(np.argmax(el_won))
    print("%d: warmte-only piek per woning lucht %.2f kW (T %.1f), bodem %.2f kW; D_core max %.2f MW, D incl. verlies max %.2f MW; COP lucht bij piek %.2f" % (
        y, 1e3 * el_won.max() / m.N_WON, j.Tair[i], 1e3 * el_bod.max() / m.N_WON, j.D_core.max(),
        j.D_core.max() + j.D_core.sum() / 0.75 * 0.25 / 8760, cs[i]))
    w = m.warmtenet(j)
    print("    warmtenet: gem COP (seizoen) %.2f; COP in koudste uur %.2f" % ((w["q"].sum() / (w["q"] / w["cop"]).sum()), w["cop"][np.argmin(j.Tair)]))

    for label, ev, util in [("woning+warmte", "geen", 0.0), ("+utiliteit", "geen", 1.0), ("+utiliteit+EV", "ongestuurd", 1.0)]:
        j2 = m.Jaar(y)
        j2.util_el = j2.util_el * util
        # warmtenet zonder utiliteitswarmte is hier niet aangepast: de centrale levert ook aan utiliteit in alle varianten
        a = m.individueel(j2, ev=ev)["net"].max()
        ab = m.individueel(j2, bron="bodem", ev=ev)["net"].max()
        for b in [0, 5, 10, 15, 20, 30]:
            for met in ["co2", "carnot"]:
                c = m.warmtenet(j2, ev=ev, buf=b, methode=met)["net"].max()
                rows.append(dict(jaar=y, lasten=label, buffer=b, cop=met, A_lucht=a, A_bodem=ab, net=c, reductie_MW=a - c, factor=a / c,
                                 reductie_tov_bodem=ab - c, factor_bodem=ab / c, kW_per_woning_A=1e3 * a / m.N_WON, kW_per_woning_net=1e3 * c / m.N_WON))
d = pd.DataFrame(rows).round(2)
d.to_csv(os.path.join(m.ROOT, "uitvoer/kalibratie.csv"), index=False)
pd.set_option("display.width", 200, "display.max_rows", 200)
print(d[(d.cop == "co2") & (d.jaar.isin([2017, 2012]))].to_string(index=False))
