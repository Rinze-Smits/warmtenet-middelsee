"""
Uurmodel warmtevoorziening Middelsee (Leeuwarden), versie 2.
Eenheden: MW, MWh, uurstap. Weer: KNMI station 270. Zon: PVGIS 5.3 (SARAH3).
Prijzen en productiemix: Energy-Charts (Fraunhofer ISE).

Wijzigingen ten opzichte van versie 1 (overdracht par. 8):
- echte uurdata in plaats van een synthetisch weerjaar;
- ruimteverwarming schaalt met een vaste factor uit het normaaljaar, zodat een koud jaar ook meer warmte vraagt;
- laadprofielen op lokale kloktijd, weer en zon op UT;
- twee COP-methoden: 'carnot' (versie 1) en 'co2' (transkritisch 65/30 C, Lorenz-benadering);
- HTO: rondgaand rendement 70 % (was 85 %) en laden met COP-boete;
- pompenergie net en bronnen expliciet;
- nieuw: bodemwarmtepomp, wijkbatterij, basaltopslag, teruglevergrens, slim laden als LP, flexibele tapwaterboilers.
"""
import json
import os
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_WON = 1647
GJ_RV, GJ_TW = 12.0, 8.0          # per woning; samen de 20 GJ uit de brochure
UTIL_WARMTE = 2000.0              # MWh/jaar, eigen aanname
HH, EV, UTIL_EL = 3300.0, 2800.0, 1500.0   # MWh/jaar, eigen aannames
PV_MIX = {"zuid35": 0.30, "oost15": 0.20, "west15": 0.20, "plat10": 0.30}
REF_JAAR = 2017                   # normaaljaar: graaduren gelijk aan de mediaan 2005-2025, zie run_weer.py
_cache = {}


def _knmi():
    if "knmi" not in _cache:
        frames = []
        for r in ["2001-2010", "2011-2020", "2021-2030"]:
            p = os.path.join(ROOT, "data/knmi", "uurgeg_270_%s.txt" % r)
            with open(p) as f:
                for n, line in enumerate(f):
                    if line.startswith("# STN"):
                        break
            d = pd.read_csv(p, skiprows=n, skipinitialspace=True, usecols=lambda c: c.strip() in ("YYYYMMDD", "HH", "T", "Q"))
            d.columns = [c.strip().lstrip("# ") for c in d.columns]
            frames.append(d)
        d = pd.concat(frames)
        # KNMI-uurvak HH loopt van HH-1 tot HH UT; index is het begin van het uurvak
        t = pd.to_datetime(d["YYYYMMDD"].astype(str)) + pd.to_timedelta(d["HH"].astype(int) - 1, unit="h")
        s = pd.DataFrame({"T": pd.to_numeric(d["T"], errors="coerce").values / 10.0,
                          "Q": pd.to_numeric(d["Q"], errors="coerce").values}, index=t)
        _cache["knmi"] = s[~s.index.duplicated()].interpolate(limit=6)
    return _cache["knmi"]


def _pvgis(name):
    key = "pv_" + name
    if key not in _cache:
        j = json.load(open(os.path.join(ROOT, "data/pvgis", "pv_%s.json" % name)))
        d = pd.DataFrame(j["outputs"]["hourly"])
        t = pd.to_datetime(d["time"], format="%Y%m%d:%H%M").dt.floor("h")
        _cache[key] = pd.Series(d["P"].values / 1000.0, index=t)  # kW per kWp
    return _cache[key]


def _uur(year, s):
    x = s.loc[str(year)]
    x = x[~((x.index.month == 2) & (x.index.day == 29))]
    if len(x) != 8760:
        raise ValueError("jaar %s: %d uren" % (year, len(x)))
    return x


def pv_profiel(year, mix=None):
    """kW per kWp; 2024 en later (geen PVGIS) via KNMI-straling, geschaald op de maandfactor uit het overlap-tijdvak."""
    mix = mix or PV_MIX
    if year <= 2023:
        return sum(w * _uur(year, _pvgis(n)).values for n, w in mix.items())
    ref = sum(w * _uur(2020, _pvgis(n)).values for n, w in mix.items())
    q = _uur(2020, _knmi()["Q"]).values
    return np.maximum(_uur(year, _knmi()["Q"]).values, 0) * ref.sum() / q.sum()


def _ha_mean(x, n):
    """Ondersteunt de gebouwtraagheid: exponentieel voortschrijdend gemiddelde over circa n uur."""
    if n <= 1:
        return np.asarray(x)
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().values


class Jaar:
    """Alle uurreeksen voor een weerjaar."""

    def __init__(self, year, traagheid=12, ev_mw=EV, n_won=N_WON):
        self.year = year
        k = _uur(year, _knmi())
        self.Tair = k["T"].values
        self.index = k.index
        loc = k.index.tz_localize("UTC").tz_convert("Europe/Amsterdam")
        self.hod = np.asarray(loc.hour)
        self.doy = np.asarray(k.index.dayofyear) - 1
        self.dagnr = np.arange(8760) // 24
        T = _ha_mean(self.Tair, traagheid)
        self.Teff = T
        ref = _uur(REF_JAAR, _knmi())["T"].values
        Tref = _ha_mean(ref, traagheid)
        sf = n_won * GJ_RV / 3.6 / np.maximum(0, 15 - Tref).sum()
        self.sh_won = sf * np.maximum(0, 15 - T)
        tw = np.array([.2, .15, .1, .1, .15, .4, 1.2, 1.8, 1.4, .9, .7, .6, .7, .6, .5, .6, .9, 1.3, 1.6, 1.7, 1.5, 1.1, .7, .4])
        v = tw[self.hod] * (1 + 0.12 * np.cos(2 * np.pi * (self.doy - 15) / 365))
        self.dhw_won = v / v.sum() * n_won * GJ_TW / 3.6
        occ = lambda h: np.where((h >= 7) & (h <= 18), 1.3, 0.6)
        hod_ref = np.asarray(_uur(REF_JAAR, _knmi()).index.tz_localize("UTC").tz_convert("Europe/Amsterdam").hour)
        su = UTIL_WARMTE / (np.maximum(0, 14 - Tref) * occ(hod_ref)).sum()
        self.sh_util = su * np.maximum(0, 14 - T) * occ(self.hod)
        hh = np.array([.45, .4, .38, .37, .38, .45, .7, .95, .9, .8, .8, .85, .85, .8, .8, .85, 1.05, 1.5, 1.75, 1.7, 1.5, 1.25, .95, .65])
        v = hh[self.hod] * (1 + 0.18 * np.cos(2 * np.pi * (self.doy - 15) / 365))
        self.hh = v / v.sum() * HH * n_won / N_WON
        ev = np.array([.6, .4, .2, .1, .05, .05, .05, .05, .05, .05, .05, .05, .05, .05, .05, .1, .5, 1.6, 2.0, 1.8, 1.5, 1.2, 1.0, .8])
        v = ev[self.hod]
        self.ev_ongestuurd = v / v.sum() * ev_mw
        v = np.where((self.hod >= 23) | (self.hod <= 6), 1.0, 0.0)
        self.ev_nacht = v / v.sum() * ev_mw
        self.ev_jaar = ev_mw
        v = np.where((self.hod >= 7) & (self.hod <= 21), 1.6, 0.5)
        self.util_el = v / v.sum() * UTIL_EL
        self.pv = pv_profiel(year)

    @property
    def D_core(self):
        return self.sh_won + self.dhw_won + self.sh_util


def carnot(Tc, Te, eta, cap):
    return np.minimum(eta * (Tc + 273.15) / (Tc - Te), cap)


def lorenz_gem(a, b):
    a, b = a + 273.15, b + 273.15
    return (a - b) / np.log(a / b)


def cop_centraal(j, Tsup=65, Tret=30, methode="co2"):
    """
    'carnot': versie 1, 0,55 x Carnot op condensor Tsup+3.
    'co2'   : transkritisch CO2 met temperatuurglijden; ankerpunt COP 3,5 op WKO-bedrijf 13/6 C en 30/65 C
              (ontwerpcondities uit de aanbesteding Heechterp). De 3,5 is een eigen aanname; de werkelijke waarde
              staat in de EMG-verklaring (Bijlage C) van die aanbesteding en is niet openbaar.
    """
    if methode == "carnot":
        Tsrc = np.maximum(j.Tair, 10.0)
        return carnot(Tsup + 3, Tsrc - 5, 0.55, 6.0)
    Th = lorenz_gem(Tsup + 3, Tret + 3)
    Tl_wko = lorenz_gem(13.0, 6.0) - 3.0
    eta = 3.5 * (Th - Tl_wko) / Th
    Tl = np.maximum(j.Tair + 273.15 - 8.0, Tl_wko)
    return np.minimum(eta * Th / (Th - Tl), 6.0)


def cop_lucht_ind(j):
    Te = j.Tair - 6
    defrost = np.where((j.Tair > -3) & (j.Tair < 5), 0.9, 1.0)
    return carnot(38.0, Te, 0.45, 6.0) * defrost, carnot(58.0, Te, 0.45, 4.0) * defrost


def cop_bodem_ind(j):
    """Gesloten bodemlus of bronnet; brontemperatuur volgt het seizoen met 2 maanden vertraging."""
    Tb = 10.0 + 3.5 * np.cos(2 * np.pi * (j.doy - 260) / 365)
    Te = Tb - 5
    return carnot(35.0, Te, 0.50, 7.0), carnot(58.0, Te, 0.45, 4.5)


def _ev(j, ev):
    return {"ongestuurd": j.ev_ongestuurd, "nacht": j.ev_nacht, "lp": np.zeros(8760), "geen": np.zeros(8760)}[ev]


def lp(j, D, cop, L, pv_mwp=0.0, qmax=7.5, buf=20.0, eb=2.0, hto=0.0, cop_hto=None, hto_eta=0.70,
       bat_mwh=0.0, bat_mw=0.0, basalt=0.0, basalt_mw=0.0, ev_lp=False, exp_lim=None,
       lb=0.002, c_imp=None, c_exp=None, wpk=3000.0, wpx=50.0):
    """
    Minimaliseert piekafname, daarna energiekosten. L is de vaste elektriciteitsvraag zonder zon.
    Geeft nettobelasting en inzet per uur. Rondlopende opslag: eind van het jaar sluit aan op het begin.
    """
    T = len(D)
    pv = pv_mwp * j.pv
    c_imp = np.ones(T) if c_imp is None else c_imp
    c_exp = 0.3 * np.ones(T) if c_exp is None else c_exp
    names = ["q", "e", "s", "ch", "dis", "sh", "imp", "exp", "cur", "bc", "bd", "bs", "bq", "bo", "bk", "ev"]
    ix = {n: np.arange(T) + i * T for i, n in enumerate(names)}
    ipk, ipx = len(names) * T, len(names) * T + 1
    n = ipx + 1
    prev = np.roll(np.arange(T), 1)
    r = np.arange(T)
    rows, cols, vals, beq = [], [], [], []
    cop_h = cop if cop_hto is None else cop_hto
    def add(rw, c, v):
        rows.append(rw); cols.append(c); vals.append(np.broadcast_to(v, (len(rw),)).astype(float))
    # warmtebalans
    add(r, ix["q"], 1); add(r, ix["e"], 1); add(r, ix["dis"], 1); add(r, ix["bo"], 1)
    add(r, ix["s"], -1); add(r, ix["s"][prev], 1 - lb)
    beq.append(D)
    # HTO
    r2 = r + T
    add(r2, ix["sh"], 1); add(r2, ix["sh"][prev], -(1 - 0.00004)); add(r2, ix["ch"], -1); add(r2, ix["dis"], 1 / hto_eta)
    beq.append(np.zeros(T))
    # elektriciteit
    r3 = r + 2 * T
    add(r3, ix["imp"], 1); add(r3, ix["exp"], -1); add(r3, ix["q"], -1 / cop); add(r3, ix["ch"], -1 / cop_h)
    add(r3, ix["e"], -1); add(r3, ix["dis"], -0.03); add(r3, ix["cur"], -1); add(r3, ix["bc"], -1); add(r3, ix["bd"], 1)
    add(r3, ix["bq"], -1); add(r3, ix["ev"], -1)
    beq.append(L - pv)
    # batterij
    r4 = r + 3 * T
    add(r4, ix["bs"], 1); add(r4, ix["bs"][prev], -(1 - 0.0001)); add(r4, ix["bc"], -0.95); add(r4, ix["bd"], 1 / 0.95)
    beq.append(np.zeros(T))
    # basalt: alleen elektrisch geladen (COP 1), 0,4 %/uur verlies
    r5 = r + 4 * T
    add(r5, ix["bk"], 1); add(r5, ix["bk"][prev], -(1 - 0.004)); add(r5, ix["bq"], -0.98); add(r5, ix["bo"], 1)
    beq.append(np.zeros(T))
    nrow = 5 * T
    sess = None
    if ev_lp:
        uur = j.hod
        venster = (uur >= 17) | (uur < 7)
        sess = (j.dagnr + (uur >= 17).astype(int)) % 365  # sessie loopt 17-07 u lokaal; 31 dec sluit aan op 1 jan
        ids = np.unique(sess)
        kol = np.where(venster)[0]
        sid = np.searchsorted(ids, sess[kol])
        rows.append(nrow + sid); cols.append(ix["ev"][kol]); vals.append(np.ones(len(kol)))
        e_per = j.ev_jaar / 365.0
        b = np.zeros(len(ids))
        tel = np.bincount(sid, minlength=len(ids))
        b[tel >= 6] = e_per
        b *= j.ev_jaar / b.sum()
        beq.append(b)
        nrow += len(ids)
    Aeq = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nrow, n))
    beq = np.concatenate(beq)
    # pieken en warmtepompvermogen
    one = np.ones(T)
    Aub = sparse.vstack([
        sparse.csr_matrix((np.r_[one, -one], (np.r_[r, r], np.r_[ix["imp"], np.full(T, ipk)])), shape=(T, n)),
        sparse.csr_matrix((np.r_[one, -one], (np.r_[r, r], np.r_[ix["exp"], np.full(T, ipx)])), shape=(T, n)),
        sparse.csr_matrix((np.r_[one, one], (np.r_[r, r], np.r_[ix["q"], ix["ch"]])), shape=(T, n)),
    ])
    bub = np.r_[np.zeros(2 * T), np.full(T, qmax)]
    h = hto > 0
    bounds = [(0, None)] * n
    def setb(name, lo, hi):
        for i, t in enumerate(ix[name]):
            bounds[t] = (lo, hi if np.isscalar(hi) or hi is None else hi[i])
    setb("q", 0, None); setb("e", 0, eb); setb("s", 0, buf)
    setb("ch", 0, 5.0 if h else 0); setb("dis", 0, 3.0 if h else 0); setb("sh", 0, hto)
    setb("imp", 0, None); setb("exp", 0, exp_lim); setb("cur", 0, pv)
    setb("bc", 0, bat_mw); setb("bd", 0, bat_mw); setb("bs", 0, bat_mwh)
    setb("bq", 0, basalt_mw); setb("bo", 0, basalt_mw * 2 if basalt else 0); setb("bk", 0, basalt)
    if ev_lp:
        hi = np.where(venster, 6.0, 0.0)
        setb("ev", 0, hi)
    else:
        setb("ev", 0, 0)
    c = np.zeros(n)
    c[ix["imp"]] = c_imp; c[ix["exp"]] = -c_exp; c[ix["e"]] = 0.01; c[ipk] = wpk; c[ipx] = wpx
    res = linprog(c, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    x = res.x
    v = {k: x[ix[k]] for k in names}
    v["net"] = v["imp"] - v["exp"]
    v["warmte_el"] = v["q"] / cop + v["ch"] / cop_h + v["e"] + 0.03 * v["dis"] + v["bq"]
    return v


def warmtenet(j, pv_mwp=0.0, Tsup=65, Tret=30, buf=20.0, eb=2.0, verlies=0.25, booster=False, methode="co2", ev="ongestuurd",
              hto=0.0, hto_eta=0.70, pomp=0.015, c_imp=None, c_exp=None, **kw):
    """Collectief net. verlies is de fractie van de opwekking; constant over het jaar."""
    D0 = j.D_core
    losses = np.full(8760, D0.sum() / (1 - verlies) * verlies / 8760)
    D = D0 + losses
    cop = cop_centraal(j, Tsup, Tret, methode)
    extra = pomp * D
    if booster:
        # LT-net: mini-warmtepomp in de woning levert circa 26 % van de tapwaterenergie met COP 4
        extra = extra + j.dhw_won * 0.26 / 4
        D = D - j.dhw_won * 0.26
    cop_hto = cop_centraal(j, 85, 30, methode) if hto else None
    L = j.hh + j.util_el + _ev(j, ev) + extra
    v = lp(j, D, cop, L, pv_mwp=pv_mwp, buf=buf, eb=eb, hto=hto, cop_hto=cop_hto, hto_eta=hto_eta, ev_lp=(ev == "lp"),
           c_imp=c_imp, c_exp=c_exp, **kw)
    v["warmte_el"] = v["warmte_el"] + extra
    v["verlies_MWh"] = losses.sum()
    v["D"] = D
    v["cop"] = cop
    return v


def individueel(j, pv_mwp=0.0, bron="lucht", ev="ongestuurd", dhw_flex_mwh=0.0, bat_mwh=0.0, bat_mw=0.0, c_imp=None, c_exp=None, exp_lim=None):
    """Individuele warmtepompen. dhw_flex_mwh: boilers in de wijk laden op afroep (per woning circa 4 kWh = 6,6 MWh)."""
    if bron == "lucht":
        cop_sh, cop_dhw = cop_lucht_ind(j)
        backup = np.where(j.Tair < -7, 0.2, 0.0)
    else:
        cop_sh, cop_dhw = cop_bodem_ind(j)
        backup = np.zeros(8760)
    el_sh = j.sh_won * (1 - backup) / cop_sh + j.sh_won * backup + j.sh_util / cop_sh
    if bron != "lucht":
        el_sh = el_sh + 0.01 * (j.sh_won + j.sh_util)  # bronpomp
    L = j.hh + j.util_el + _ev(j, ev) + el_sh
    v = lp(j, j.dhw_won, cop_dhw, L, pv_mwp=pv_mwp, qmax=1e3, buf=dhw_flex_mwh, eb=0.0, lb=0.004,
           bat_mwh=bat_mwh, bat_mw=bat_mw, ev_lp=(ev == "lp"), c_imp=c_imp, c_exp=c_exp, exp_lim=exp_lim)
    v["warmte_el"] = v["warmte_el"] + el_sh
    v["verlies_MWh"] = 0.0
    return v


def samenvatting(naam, j, v, pv_mwp):
    net = v["net"]
    imp = np.maximum(net, 0)
    ex = np.maximum(-net, 0)
    pv = pv_mwp * j.pv.sum()
    cur = v["cur"].sum()
    o = dict(scenario=naam, jaar=j.year, piek_afname_MW=net.max(), piek_terug_MW=ex.max(), afname_GWh=imp.sum() / 1e3,
             terug_GWh=ex.sum() / 1e3, stroom_warmte_GWh=v["warmte_el"].sum() / 1e3, pv_GWh=pv / 1e3, afgekapt_GWh=cur / 1e3,
             eigen_gebruik_pct=(100 * (pv - ex.sum() - cur) / pv) if pv > 0 else np.nan,
             uren_op_piek=int((net > 0.99 * net.max()).sum()), T_koudste_piekuur=float(j.Tair[net > 0.99 * net.max()].min()), eboiler_MWh=v["e"].sum(), hto_uit_MWh=v["dis"].sum())
    return o


def _vol_jaar(s, year):
    """Precies 8760 UT-uren; de bron stopt op lokale jaargrens, dus het laatste uur wordt aangevuld."""
    idx = pd.date_range("%d-01-01" % year, "%d-12-31 23:00" % year, freq="h")
    x = s.reindex(idx).interpolate(limit=6).ffill().bfill()
    x = x[~((x.index.month == 2) & (x.index.day == 29))]
    return x.values


def prijzen(year):
    """Day-ahead EUR/MWh per uur op UT-uurbasis, 8760 waarden."""
    j = json.load(open(os.path.join(ROOT, "data/prijs", "price_%d.json" % year)))
    s = pd.Series(j["price"], index=pd.to_datetime(j["unix_seconds"], unit="s"), dtype=float)
    s = s.resample("h").mean().interpolate(limit=6)
    return _vol_jaar(s, year)


EF = {"Fossil gas": 0.40, "Fossil hard coal": 0.85, "Fossil oil": 0.75, "Waste": 0.33, "Fossil coal-derived gas": 1.0, "Other": 0.40}


def co2_factoren(year):
    """kg CO2/kWh per uur op productie in NL (zonder import). Gemiddeld en een marginale benadering."""
    j = json.load(open(os.path.join(ROOT, "data/prijs", "power_%d.json" % year)))
    idx = pd.to_datetime(j["unix_seconds"], unit="s")
    em, tot, gas = 0, 0, 0
    for p in j["production_types"]:
        n = p["name"]
        if n in ("Load", "Residual load", "Renewable share of generation", "Renewable share of load", "Cross border electricity trading") or "Hydro pumped storage consumption" in n:
            continue
        x = pd.Series(p["data"], index=idx, dtype=float).fillna(0).clip(lower=0)
        tot = tot + x
        em = em + x * EF.get(n, 0.0)
        if n == "Fossil gas":
            gas = x
    g = _vol_jaar((em / tot.replace(0, np.nan)).resample("h").mean(), year)
    gas_h = _vol_jaar(gas.resample("h").mean(), year)
    marg = np.where(gas_h > 0.25 * np.nanmedian(gas_h), 0.42, 0.0)
    return g, marg
