"""Figuren voor het rapport. Kleuren uit het gevalideerde referentiepalet (eerste drie posities)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import middelsee as m

U = os.path.join(m.ROOT, "uitvoer")
F = os.path.join(m.ROOT, "rapport/figuren")
BLAUW, ORANJE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
LICHTBLAUW = "#9cc3ee"
INK, INK2, RAST, VLAK = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": RAST, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": VLAK, "axes.facecolor": VLAK, "font.family": "DejaVu Sans"})
from matplotlib.ticker import FuncFormatter
KOMMA = FuncFormatter(lambda v, _: ("%g" % round(v, 2)).replace(".", ",").replace("-", "−"))
t = pd.read_csv(os.path.join(U, "overzicht_varianten.csv"))
d = pd.read_csv(os.path.join(U, "scenarios.csv"))

# 1. piek normaal en koud jaar
keus = [("A lucht", "Lucht-waterwarmtepomp, ongestuurd"), ("A bodem (20k)", "Bodemwarmtepomp, ongestuurd"), ("A lucht, slim laden", "Lucht-water + slim laden"),
        ("A lucht, slim + boilers", "Lucht-water + slim laden + boilers"), ("A lucht, slim + boilers + batterij 5 MWh", "… + wijkbatterij 5 MWh"),
        ("A bodem (20k), slim + boilers", "Bodem + slim laden + boilers"), ("C net 65, buffer 5", "Warmtenet 65 °C, buffer 5 MWh"), ("C net 65, buffer 20", "Warmtenet 65 °C, buffer 20 MWh"),
        ("C net 65, slim laden, buffer 20", "Warmtenet + slim laden"), ("G LT 50, slim laden", "Lagetemperatuurnet + slim laden"), ("F HTO 3 GWh, slim laden", "Warmtenet + HTO + slim laden")]
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for i, (k, lab) in enumerate(keus[::-1]):
    r = t[t.variant == k].iloc[0]
    ax.plot([r.piek_2017, r.piek_2012], [i, i], color=RAST, lw=2, zorder=1)
    ax.scatter(r.piek_2017, i, s=64, color=LICHTBLAUW, edgecolor=VLAK, linewidth=2, zorder=2, label="Normaal jaar (2017)" if i == 0 else None)
    ax.scatter(r.piek_2012, i, s=64, color=BLAUW, edgecolor=VLAK, linewidth=2, zorder=3, label="Koud jaar (2012)" if i == 0 else None)
    ax.text(max(r.piek_2017, r.piek_2012) + 0.09, i, ("%.1f" % r.piek_2012).replace(".", ","), va="center", color=INK2, fontsize=9)
ax.set_yticks(range(len(keus))); ax.set_yticklabels([l for _, l in keus[::-1]], color=INK)
ax.set_xlim(1, 5.4); ax.set_xlabel("Hoogste afname wijk (MW)"); ax.grid(axis="x", color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.legend(frameon=False, loc="lower right", labelcolor=INK2)
ax.set_title("Zonder warmtenet is sturing nodig om de piek in een koud jaar te beperken", x=-0.42, loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(KOMMA); ax.yaxis.set_major_formatter(KOMMA) if ax.get_ylabel() else None; fig.tight_layout(); fig.savefig(os.path.join(F, "fig1_piek_varianten.png"), dpi=200); plt.close(fig)

# 2. buffer
def reeks(fmt, y):
    x, v = [], []
    for b in [0, 2, 5, 10, 15, 20, 25, 30, 50]:
        n = "C net 65 (CO2-COP)" if (b == 20 and "slim" not in fmt) else ("C net 65, slim laden" if b == 20 else fmt % b)
        x.append(b); v.append(d[(d.scenario == n) & (d.jaar == y)].piek_afname_MW.iloc[0])
    return x, v
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.axvspan(16, 23.5, color="#f0efe9", zorder=0)
ax.text(19.75, 3.98, "Heechterp\ngeschaald", ha="center", va="top", color=INK2, fontsize=9)
x, a = reeks("buffer %d MWh", 2012); ax.plot(x, a, color=BLAUW, lw=2, marker="o", ms=5)
x, b = reeks("buffer %d MWh, slim laden", 2012); ax.plot(x, b, color=ORANJE, lw=2, marker="o", ms=5)
ax.text(50.8, a[-1] + 0.06, "Zonder\nslim laden", color=INK, fontsize=9, va="bottom"); ax.text(50.8, b[-1] - 0.06, "Met\nslim laden", color=INK, fontsize=9, va="top")
ax.axhline(4.91, color=INK2, lw=1, ls=(0, (4, 3))); ax.text(50, 4.86, "Individuele lucht-waterwarmtepomp, ongestuurd: 4,9 MW", ha="right", va="top", color=INK2, fontsize=9)
ax.set_xlim(-1, 58); ax.set_ylim(1.5, 5.1); ax.set_xlabel("Buffergrootte (MWh)"); ax.set_ylabel("Hoogste afname wijk, 2012 (MW)")
ax.grid(axis="y", color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.set_title("Met slim laden is 5 MWh buffer al bijna genoeg; zonder is de buffer doorslaggevend", loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(KOMMA); ax.yaxis.set_major_formatter(KOMMA) if ax.get_ylabel() else None; fig.tight_layout(); fig.savefig(os.path.join(F, "fig2_buffer.png"), dpi=200); plt.close(fig)

# 3. kosten tegen piek
lab = {"A lucht": ("Lucht-water", 0.07, 0.03), "A lucht, slim laden": ("+ slim laden", 0.07, -0.07), "A lucht, slim + boilers": ("+ boilers", -0.05, -0.10),
       "A lucht, slim + boilers + batterij 5 MWh": ("+ batterij", -0.07, 0.09), "A bodem (20k)": ("Bodem", 0.07, 0.0), "A bodem (20k), slim + boilers": ("Bodem + slim + boilers", -0.07, 0.07),
       "C net 65, buffer 20": ("Warmtenet, 20 MWh", 0.07, 0.03), "C net 65, buffer 5": ("Warmtenet, 5 MWh", 0.07, 0.02), "C net 65, slim laden, buffer 20": ("+ slim laden", -0.07, 0.08),
       "G LT 50, slim laden": ("LT-net + slim laden", 0.07, 0.0), "F HTO 3 GWh, slim laden": ("Warmtenet + HTO + slim", 0.07, 0.0)}
fig, ax = plt.subplots(figsize=(8.6, 4.9))
for k, (l, dx, dy) in lab.items():
    r = t[t.variant == k].iloc[0]
    kl = BLAUW if k.startswith("A lucht") else (AQUA if k.startswith("A bodem") else ORANJE)
    ax.scatter(r.piek_2012, r.delta3_2023, s=70, color=kl, edgecolor=VLAK, linewidth=2, zorder=3)
    ax.text(r.piek_2012 + dx, r.delta3_2023 + dy, l, color=INK, fontsize=8.8, ha="left" if dx > 0 else "right", va="center")
for c, n in ((BLAUW, "Individueel, lucht"), (AQUA, "Individueel, bodem"), (ORANJE, "Collectief net")):
    ax.scatter([], [], s=70, color=c, label=n)
ax.axhline(0, color=INK2, lw=1)
ax.set_xlim(1.2, 5.6); ax.set_ylim(-0.3, 1.9)
ax.set_xlabel("Hoogste afname wijk in koud jaar 2012 (MW)"); ax.set_ylabel("Meerkosten t.o.v. lucht-water (mln € per jaar)")
ax.grid(color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0); ax.legend(frameon=False, loc="upper right", labelcolor=INK2)
ax.set_title("Sturing verlaagt de piek tegen lage kosten; het warmtenet werkt ook zonder sturing", loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(KOMMA); ax.yaxis.set_major_formatter(KOMMA) if ax.get_ylabel() else None; fig.tight_layout(); fig.savefig(os.path.join(F, "fig3_kosten_piek.png"), dpi=200); plt.close(fig)

# 4. kosten bewoner
stap = ["Brochure", "Vastrecht 80 %\n+ KDB over 30 jaar", "Idem, warmtepomp\nSCOP 3,0"]
net, wp = [1421, 1887, 1887], [1489, 1489, 1583]
fig, ax = plt.subplots(figsize=(8.6, 3.9))
for i in range(3):
    y = 2 - i
    ax.barh(y + 0.19, net[i], height=0.34, color=ORANJE, edgecolor=VLAK, linewidth=2, label="Warmtenet" if i == 0 else None)
    ax.barh(y - 0.19, wp[i], height=0.34, color=BLAUW, edgecolor=VLAK, linewidth=2, label="Warmtepomp" if i == 0 else None)
    ax.text(net[i] + 25, y + 0.19, ("€ %s" % format(net[i], ",").replace(",", ".")), va="center", color=INK2, fontsize=9)
    ax.text(wp[i] + 25, y - 0.19, ("€ %s" % format(wp[i], ",").replace(",", ".")), va="center", color=INK2, fontsize=9)
ax.set_yticks([2, 1, 0]); ax.set_yticklabels(stap, color=INK); ax.set_xlim(0, 2300); ax.set_xlabel("Kosten per jaar, inclusief btw (€)")
ax.grid(axis="x", color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, labelcolor=INK2)
ax.set_title("Met de aansluitbijdrage meegeteld is het warmtenet duurder", x=-0.2, loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig4_kosten_bewoner.png"), dpi=200); plt.close(fig)

# 5. CO2 warmte per variant
groep = ["Stroommix 2023", "Stroommix 2024", "Vaste factor\n0,14 kg/kWh", "Marginaal\n(gascentrale)"]
waarden = {"Bodemwarmtepomp": ([16.7, 14.5, 9.7, 28.9], AQUA), "Lucht-waterwarmtepomp": ([20.7, 17.7, 11.5, 34.3], BLAUW), "Warmtenet 65 °C": ([22.0, 17.6, 14.5, 43.2], ORANJE)}
fig, ax = plt.subplots(figsize=(8.6, 4.2))
for k, (n, (w, kl)) in enumerate(waarden.items()):
    xs = [i + (k - 1) * 0.27 for i in range(4)]
    ax.bar(xs, w, width=0.25, color=kl, edgecolor=VLAK, linewidth=2, label=n)
    for x, v in zip(xs, w):
        ax.text(x, v + 0.7, ("%.1f" % v).replace(".", ","), ha="center", color=INK2, fontsize=8.5)
ax.set_xticks(range(4)); ax.set_xticklabels(groep, color=INK); ax.set_ylabel("kg CO₂ per GJ geleverde warmte"); ax.set_ylim(0, 50)
ax.yaxis.set_major_formatter(KOMMA); ax.grid(axis="y", color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.legend(frameon=False, loc="upper left", labelcolor=INK2)
ax.set_title("Het warmtenet stoot niet minder uit, en meer dan een bodemwarmtepomp", loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig5_co2.png"), dpi=200); plt.close(fig)

# 6. Techum / De Zuidlanden
fig, ax = plt.subplots(figsize=(8.6, 3.6))
lab6, w6 = ["2022", "2024", "Etiket 2025"], [41.5, 84.8, 94]
ax.bar(lab6, w6, width=0.5, color=ORANJE, edgecolor=VLAK, linewidth=2)
for i, v in enumerate(w6):
    ax.text(i, v + 2, ("%g" % v).replace(".", ","), ha="center", color=INK2, fontsize=9.5)
ax.axhline(58.5, color=INK2, lw=1.2, ls=(0, (4, 3)))
ax.text(-0.42, 60.5, "CV-ketel: circa 58,5", color=INK2, fontsize=9)
ax.set_ylim(0, 110); ax.set_ylabel("kg CO₂ per GJ warmte"); ax.yaxis.set_major_formatter(KOMMA)
ax.grid(axis="y", color=RAST, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.set_title("Warmtenet De Zuidlanden: van biogas naar 100 % aardgas", loc="left", color=INK, fontsize=11.5, fontweight="bold", pad=12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig6_techum.png"), dpi=200); plt.close(fig)
