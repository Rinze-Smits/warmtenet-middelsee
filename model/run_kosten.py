"""
Stap 5-6: kosten en CO2 per variant. Maatschappelijk perspectief: exclusief btw, energiebelasting en subsidie.
Uurprijzen en productiemix horen bij hetzelfde jaar als het weer (2023 en 2024), zodat de samenhang tussen koude, zon en prijs behouden blijft.
Bedragen met bron R (raadsvoorstel), B (brochure), CE (CE Delft 2026) zijn overgenomen; A is een eigen aanname.
"""
import multiprocessing as mp
import os
import numpy as np
import pandas as pd
import middelsee as m
from middelsee import warmtenet as W, individueel as I

BTW = 1.21
N = m.N_WON
PV = 15.0
GJ_GELEVERD = (m.N_WON * 20 + m.UTIL_WARMTE * 3.6)


def ann(c, n, r):
    return c * r / (1 - (1 + r) ** -n)


def posten(s, r):
    """Jaarlast in EUR. Elke post: (investering, levensduur, opex per jaar)."""
    wp_lucht = (14000 / BTW * N, 15, 150 / BTW * N)                 # B
    util_ind = (1.0e6, 20, 2.0e4)                                   # A: eigen warmtepompen utiliteit
    bod = s.get("bodem_eur", 20000)                                 # A; band 15-25k
    wp_bod = [(0.6 * bod * N, 18, 150 / BTW * N), (0.4 * bod * N, 40, 0)]
    net = [(0.4 * 41.8e6, 20, 0.015 * 41.8e6), (0.6 * 41.8e6, 40, 0)]  # R voor het totaal; verdeling en opex A
    p = {}
    if s["type"] == "lucht":
        p["warmtepompen"] = wp_lucht; p["utiliteit"] = util_ind
    if s["type"] == "bodem":
        p["warmtepomp"] = wp_bod[0]; p["bron"] = wp_bod[1]; p["utiliteit"] = util_ind
    if s["type"] in ("net", "lt"):
        p["net_centrale"] = net[0]; p["net_leidingen"] = net[1]
    if s["type"] == "lt":
        p["boosters"] = (3500 * N, 15, 30 * N)                      # A
    if s.get("buffer_extra_mwh"):
        p["buffer_delta"] = (s["buffer_extra_mwh"] * 10000.0, 30, 0)  # A: 10 EUR/kWh, band 3-20
    if s.get("slim"):
        p["slim_laden"] = (300 * 1100, 10, 5e4)                     # A: 1.100 laadpunten, coordinatie
    if s.get("boilers"):
        p["boilerregeling"] = (100 * N, 15, 2e4)                    # A
    if s.get("bat"):
        p["batterij"] = (s["bat"] * 350e3, 15, 0.015 * s["bat"] * 350e3)  # A: 350 EUR/kWh
    if s.get("hto"):
        p["hto"] = (s.get("hto_eur", 5.0e6), 30, s.get("hto_opex", 4.0e5))  # CE: 5-9 mln in de praktijk, opex 0,4-0,9 mln
    if s.get("basalt"):
        p["basalt"] = (s["basalt"] * 40e3, 25, 0.01 * s["basalt"] * 40e3)  # A: 40 EUR/kWh
    if s.get("pv"):
        p["zon"] = (7e6 * 1.0 + 2.5e6 * 0.8 + 5.5e6 * 1.8, 25, 0.015 * 18.9e6)  # A: EUR/Wp dak 1,0 / utiliteit 0,8 / overkapping 1,8
    if s.get("pv_dak"):
        p["zon"] = (7e6 * 1.0 + 2.5e6 * 0.8, 25, 0.015 * 9.0e6)
    return {k: ann(c, n, r) + o for k, (c, n, o) in p.items()}


S = {
    "A lucht": dict(type="lucht", f=lambda j, k: I(j, **k)),
    "A lucht, slim laden": dict(type="lucht", slim=1, f=lambda j, k: I(j, ev="lp", **k)),
    "A lucht, slim + boilers": dict(type="lucht", slim=1, boilers=1, f=lambda j, k: I(j, ev="lp", dhw_flex_mwh=6.6, **k)),
    "A lucht, slim + boilers + batterij 5 MWh": dict(type="lucht", slim=1, boilers=1, bat=5, f=lambda j, k: I(j, ev="lp", dhw_flex_mwh=6.6, bat_mwh=5, bat_mw=2.5, **k)),
    "A bodem (15k)": dict(type="bodem", bodem_eur=15000, f=lambda j, k: I(j, bron="bodem", **k)),
    "A bodem (20k)": dict(type="bodem", bodem_eur=20000, f=lambda j, k: I(j, bron="bodem", **k)),
    "A bodem (25k)": dict(type="bodem", bodem_eur=25000, f=lambda j, k: I(j, bron="bodem", **k)),
    "A bodem (20k), slim + boilers": dict(type="bodem", bodem_eur=20000, slim=1, boilers=1, f=lambda j, k: I(j, bron="bodem", ev="lp", dhw_flex_mwh=6.6, **k)),
    "C net 65, buffer 20": dict(type="net", f=lambda j, k: W(j, **k)),
    "C net 65, buffer 5": dict(type="net", buffer_extra_mwh=-15, f=lambda j, k: W(j, buf=5, **k)),
    "C net 65, slim laden, buffer 20": dict(type="net", slim=1, f=lambda j, k: W(j, ev="lp", **k)),
    "C net 65, slim laden, buffer 5": dict(type="net", slim=1, buffer_extra_mwh=-15, f=lambda j, k: W(j, buf=5, ev="lp", **k)),
    "C net 65 + batterij 5 MWh": dict(type="net", bat=5, f=lambda j, k: W(j, bat_mwh=5, bat_mw=2.5, **k)),
    "C net 65, buffer 5 + basalt 50 MWh": dict(type="net", buffer_extra_mwh=-15, basalt=50, f=lambda j, k: W(j, buf=5, basalt=50, basalt_mw=3, **k)),
    "G LT 50 + boosters": dict(type="lt", f=lambda j, k: W(j, Tsup=50, Tret=25, verlies=0.19, booster=True, methode="carnot", **k)),
    "G LT 50, slim laden": dict(type="lt", slim=1, f=lambda j, k: W(j, Tsup=50, Tret=25, verlies=0.19, booster=True, methode="carnot", ev="lp", **k)),
    "F HTO 3 GWh, slim laden": dict(type="net", slim=1, hto=1, f=lambda j, k: W(j, hto=3000, ev="lp", **k)),
    "A lucht + zon": dict(type="lucht", pv=1, f=lambda j, k: I(j, pv_mwp=PV, **k)),
    "A bodem (20k) + zon": dict(type="bodem", pv=1, f=lambda j, k: I(j, bron="bodem", pv_mwp=PV, **k)),
    "C net 65 + zon": dict(type="net", pv=1, f=lambda j, k: W(j, pv_mwp=PV, **k)),
    "A lucht + zon dak 9,5 MWp": dict(type="lucht", pv_dak=1, f=lambda j, k: I(j, pv_mwp=9.5, **k)),
    "C net 65 + zon dak 9,5 MWp": dict(type="net", pv_dak=1, f=lambda j, k: W(j, pv_mwp=9.5, **k)),
    "F HTO + buffer 100 + zon, slim laden": dict(type="net", pv=1, slim=1, hto=1, buffer_extra_mwh=80, f=lambda j, k: W(j, pv_mwp=PV, buf=100, eb=4, hto=3000, ev="lp", **k)),
}


def job(a):
    naam, y = a
    s = S[naam]
    j = m.Jaar(y)
    spot = m.prijzen(y)
    g, mg = m.co2_factoren(y)
    ci = np.maximum(spot + 15, 0.0) / 100.0
    ce = np.maximum(spot, 0.0) * 0.9 / 100.0
    v = s["f"](j, dict(c_imp=ci, c_exp=ce))
    net = v["net"]
    imp = np.maximum(net, 0)
    ex = np.maximum(-net, 0)
    e_kost = (imp * (spot + 15)).sum() - (ex * np.maximum(spot, 0) * 0.9).sum()
    # warmtestroom apart gewaardeerd op het uurprofiel, zonder zon, voor de warmtekostprijs
    he = v["warmte_el"]
    o = dict(scenario=naam, jaar=y, piek=net.max(), afname_GWh=imp.sum() / 1e3, terug_GWh=ex.sum() / 1e3, warmte_el_GWh=he.sum() / 1e3,
             energie_MEUR=e_kost / 1e6, warmte_el_MEUR=(he * np.maximum(spot + 15, 0)).sum() / 1e6,
             gem_prijs_warmte=(he * (spot + 15)).sum() / he.sum(),
             co2_gem_t=(imp * g).sum(), co2_warmte_t=(he * g).sum(), co2_warmte_marg_t=(he * mg).sum(),
             co2_warmte_kg_GJ=(he * g).sum() * 1e3 / GJ_GELEVERD, co2_warmte_kg_GJ_014=he.sum() * 140 / GJ_GELEVERD,
             co2_factor_gem=(he * g).sum() / he.sum())
    for r in (0.03, 0.05):
        p = posten(s, r)
        o["kapitaal_opex_MEUR_%d" % (r * 100)] = sum(p.values()) / 1e6
    return o


def bewoner():
    """Correctie van de brochurevergelijking (bedragen inclusief btw, EUR per jaar)."""
    vast70, vast80, gj, afl, meet = 430.50, 492.53, 778.40, 178.51, 33.73
    r = []
    wn0 = vast70 + gj + afl + meet
    wn1 = vast80 + gj + afl + meet
    def wp(scop, prijs=0.27, inv=14000, jr=15, ond=150):
        return 5556 / scop * prijs + inv / jr + ond
    r.append(("Brochure, zoals gepubliceerd (vastrecht 70 %, KDB niet meegeteld, SCOP 3,7)", wn0, wp(5556 / 1501)))
    r.append(("Stap 1: vastrecht 80 % volgens raadsvoorstel", wn1, wp(5556 / 1501)))
    for kdb_ex, lab in [(10000, "10.000 ex btw (raadsvoorstel, na Realisatiestimulans)"), (12000, "12.000 ex btw (raadsvoorstel, zonder stimulans)")]:
        k = kdb_ex * BTW
        r.append(("Stap 2: KDB %s lineair over 30 jaar, warmtepomp ongewijzigd" % lab, wn1 + k / 30, wp(5556 / 1501)))
        r.append(("Stap 2b: idem, KDB lineair over 15 jaar (zelfde termijn als warmtepomp)", wn1 + k / 15, wp(5556 / 1501)))
    k15, k18 = 15000, 18755
    r.append(("Stap 2c: KDB brochure 15.000 incl. btw, 30 jaar", wn1 + k15 / 30, wp(5556 / 1501)))
    r.append(("Stap 2d: KDB brochure 18.755 incl. btw, 30 jaar", wn1 + k18 / 30, wp(5556 / 1501)))
    k = 10000 * BTW
    r.append(("Stap 3: KDB 10.000 ex btw/30 jaar, warmtepomp SCOP 3,0", wn1 + k / 30, wp(3.0)))
    r.append(("Stap 3b: idem, warmtepomp SCOP 2,7 (lucht, koud profiel)", wn1 + k / 30, wp(2.7)))
    r.append(("Stap 4: beide inclusief 4 % rente (KDB 30 jaar, warmtepomp 15 jaar), SCOP 3,0", wn1 + k * 0.04 / (1 - 1.04 ** -30),
              5556 / 3.0 * 0.27 + 14000 * 0.04 / (1 - 1.04 ** -15) + 150))
    d = pd.DataFrame(r, columns=["stap", "warmtenet", "warmtepomp"]).round(0)
    d["verschil_net_min_wp"] = d.warmtenet - d.warmtepomp
    return d


if __name__ == "__main__":
    taken = [(n, y) for n in S for y in [2023, 2024]]
    with mp.Pool(max(2, (os.cpu_count() or 4) - 2)) as p:
        d = pd.DataFrame(p.map(job, taken, chunksize=1))
    ref = d[d.scenario == "A lucht"].set_index("jaar")
    for r in (3, 5):
        d["totaal_%d" % r] = d["kapitaal_opex_MEUR_%d" % r] + d["energie_MEUR"]
        d["delta_%d" % r] = d["totaal_%d" % r] - d.jaar.map(ref["kapitaal_opex_MEUR_%d" % r] + ref["energie_MEUR"])
        d["warmte_EUR_GJ_%d" % r] = (d["kapitaal_opex_MEUR_%d" % r] + d["warmte_el_MEUR"]) * 1e6 / GJ_GELEVERD
    # piek uit de scenario's staat apart; break-even per kW volgt in de rapportage
    d.round(3).to_csv(os.path.join(m.ROOT, "uitvoer/kosten.csv"), index=False)
    pd.set_option("display.width", 240, "display.max_columns", 40, "display.max_colwidth", 44, "display.max_rows", 100)
    print(d[d.jaar == 2023][["scenario", "piek", "afname_GWh", "warmte_el_GWh", "gem_prijs_warmte", "energie_MEUR", "kapitaal_opex_MEUR_3", "totaal_3", "delta_3", "delta_5", "warmte_EUR_GJ_3", "warmte_EUR_GJ_5", "co2_warmte_t", "co2_warmte_kg_GJ", "co2_warmte_kg_GJ_014", "co2_factor_gem"]].round(2).to_string(index=False))
    print(d[d.jaar == 2024][["scenario", "delta_3", "delta_5", "gem_prijs_warmte", "co2_warmte_kg_GJ"]].round(2).to_string(index=False))
    b = bewoner()
    b.to_csv(os.path.join(m.ROOT, "uitvoer/bewoner.csv"), index=False)
    pd.set_option("display.max_colwidth", 90)
    print(b.to_string(index=False))
