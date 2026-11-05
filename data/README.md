# Brondata

| Map | Inhoud | Bron |
|---|---|---|
| `knmi/` | Uurgegevens station 270 Leeuwarden, 2001–2026 (zip) | [KNMI](https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens) |
| `pvgis/` | Uurlijkse zonopbrengst per oriëntatie, 2009–2023 | [PVGIS 5.3, EU JRC](https://re.jrc.ec.europa.eu/pvg_tools/) |
| `prijs/` | Day-ahead-prijzen en productiemix NL, 2021, 2023–2025 | [Energy-Charts, Fraunhofer ISE](https://api.energy-charts.info) (CC BY 4.0, oorsprong in de bestanden) |
| `energynl/` | Warmteprofielen en invoer | [Warmteprofielengenerator, TNO/RVO](https://energy.nl/tools/warmteprofielengenerator/) |

**Runs in `energynl/`:** 6075 is Zuiderburen (Eelde 2013). 6204–6208 zijn Wiarda (Eelde 2013): lucht-water, bodem, en warmtenet met 10, 4 en 6 kW.

**Uitkomsten van het model** staan in [`../uitvoer/`](../uitvoer).
