"""Bundelt scenario's en kosten tot de tabellen in het rapport."""
import os
import pandas as pd
import middelsee as m
d = pd.read_csv(os.path.join(m.ROOT, "uitvoer/scenarios.csv"))
k = pd.read_csv(os.path.join(m.ROOT, "uitvoer/kosten.csv"))
p = d.pivot(index="scenario", columns="jaar", values="piek_afname_MW")
MAP = {"A lucht": "A lucht", "A lucht, slim laden": "A lucht, slim laden", "A lucht, slim + boilers": "A lucht, slim laden + boilers flex",
       "A lucht, slim + boilers + batterij 5 MWh": "A lucht, slim laden + boilers + batterij 5 MWh",
       "A bodem (15k)": "A bodem", "A bodem (20k)": "A bodem", "A bodem (25k)": "A bodem", "A bodem (20k), slim + boilers": "A bodem, slim laden + boilers flex",
       "C net 65, buffer 20": "C net 65 (CO2-COP)", "C net 65, buffer 5": "buffer 5 MWh", "C net 65, slim laden, buffer 20": "C net 65, slim laden",
       "C net 65, slim laden, buffer 5": "buffer 5 MWh, slim laden", "C net 65 + batterij 5 MWh": "C net 65 + wijkbatterij 5 MWh/2,5 MW",
       "C net 65, buffer 5 + basalt 50 MWh": "C net 65 buffer 5 + basalt 50 MWh/3 MW", "G LT 50 + boosters": "G LT 50 + boosters", "G LT 50, slim laden": "G LT 50 + boosters, slim laden",
       "F HTO 3 GWh, slim laden": "F HTO 3 GWh zonder PV, slim laden"}
a = k[k.jaar == 2023].set_index("scenario")
b = k[k.jaar == 2024].set_index("scenario")
r = []
for n, s in MAP.items():
    pk17, pk12 = p.loc[s, 2017], p.loc[s, 2012]
    r.append(dict(variant=n, piek_2017=pk17, piek_2012=pk12, red_2017=p.loc["A lucht", 2017] - pk17, red_2012=p.loc["A lucht", 2012] - pk12,
                  stroom_warmte_GWh=d[(d.scenario == s) & (d.jaar == 2017)].stroom_warmte_GWh.iloc[0],
                  delta3_2023=a.loc[n, "delta_3"], delta5_2023=a.loc[n, "delta_5"], delta3_2024=b.loc[n, "delta_3"], delta5_2024=b.loc[n, "delta_5"],
                  warmte_gj3=a.loc[n, "warmte_EUR_GJ_3"], warmte_gj5=a.loc[n, "warmte_EUR_GJ_5"],
                  co2_2023=a.loc[n, "co2_warmte_kg_GJ"], co2_2024=b.loc[n, "co2_warmte_kg_GJ"], co2_014=a.loc[n, "co2_warmte_kg_GJ_014"], co2_marg_t=a.loc[n, "co2_warmte_marg_t"], co2_t=a.loc[n, "co2_warmte_t"]))
t = pd.DataFrame(r)
for c, red in (("eur_kw_2017", "red_2017"), ("eur_kw_2012", "red_2012")):
    t[c] = (t.delta3_2023 * 1e6 / (t[red] * 1e3)).where(t[red] > 0.05)
t.round(2).to_csv(os.path.join(m.ROOT, "uitvoer/overzicht_varianten.csv"), index=False)
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 42)
print(t.round(2).to_string(index=False))
print(k[k.scenario.str.contains("zon")][["scenario", "jaar", "piek", "afname_GWh", "terug_GWh", "delta_3", "delta_5"]].round(2).to_string(index=False))
print(d[d.scenario.str.contains("terug|\\+ PV$|\\+ PV ")][d.jaar == 2017][["scenario", "piek_terug_MW", "terug_GWh", "afgekapt_GWh", "eigen_gebruik_pct", "eboiler_MWh"]].round(2).to_string(index=False))
print(pd.read_csv(os.path.join(m.ROOT, "uitvoer/robuust_rollend.csv")).groupby(["jaar", "buffer", "grens_vooraf", "rho"]).piek_rollend.mean().round(2))
