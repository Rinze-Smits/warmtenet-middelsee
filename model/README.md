# Model warmtenet Middelsee

Eerst KNMI uitpakken: `cd data/knmi && unzip -o '*.zip'`. Maak een omgeving met numpy, pandas, scipy en matplotlib.

Draaien (vanuit `model/`, Python 3.9+):

    ../.venv/bin/python run_weer.py        # weerjaren, zon, prijzen, CO2
    ../.venv/bin/python run_scenarios.py   # uitvoer/scenarios.csv (ca. 40 s)
    ../.venv/bin/python run_kalibratie.py  # uitvoer/kalibratie.csv
    ../.venv/bin/python run_robuust.py     # uitvoer/robuust_*.csv (enkele minuten)
    ../.venv/bin/python run_kosten.py      # uitvoer/kosten.csv, bewoner.csv
    ../.venv/bin/python tabellen.py        # uitvoer/overzicht_varianten.csv
    ../.venv/bin/python grafieken.py       # rapport/figuren

Data staat in `data/` (KNMI 270, PVGIS 5.3, Energy-Charts, TNO-generator). Aannames staan in de code met bronlabel R, B, CE of A (eigen aanname).

TNO-generator: `run_wpg2.py` (met `run_wpg_basis.py`) gebruikt `data/energynl/res62xx.json`; `wpg_start.py` start een run met het e-mailadres van de opdrachtgever, alleen na akkoord.
