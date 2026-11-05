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


