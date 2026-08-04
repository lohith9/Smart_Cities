"""
v2_07_figures.py  — reviewer-safe regeneration of Figures 8-12.
Fixes applied (recorded in the author's internal figure-audit notes, which are
not part of this repository; an earlier version of this header named the file
"v2_07_figures_AUDITED.py" and cited a "FIGURE_AUDIT_REPORT.md" that the
repository does not contain):
  Fig8 : removed 'beats'; neutral title; honest log-RMSE incl. uncalibrated physics; modest ML gain shown on full R2 axis.
  Fig9 : full 0-1 R2 axis (no zoom); explicit note that local XGB matches/exceeds graph variants (null result).
  Fig10: error bars from delay_std; neutral title; naive 'always-throttle' reference bar; illustrative-proxy caveat.
  Fig11: readable legend; added per-channel fidelity panel at 4x showing twin-relevant channels.
  Fig12: 'Estimated health co-benefits under simulated scenarios'; modelled-estimate caveat.
"""
import json, random
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
FIG  = str(ROOT / "figures")
plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":9})
W = 5.0; DPI = 300
CAP_NOTE = "Synthetic calibrated data; results are internal demonstrations, not measured field accuracy."

# ============ FIG 8 : PINN hybrid ============
pinn = json.load(open(f"{DATA}/pinn_results.json"))
phys_r2, xgb_r2, hyb_r2 = pinn["physics_only"]["r2"], pinn["data_driven_xgb"]["r2"], pinn["physics_augmented"]["r2"]
phys_rmse, xgb_rmse, hyb_rmse = pinn["physics_only"]["rmse"], pinn["data_driven_xgb"]["rmse"], pinn["physics_augmented"]["rmse"]
fig, ax = plt.subplots(1, 2, figsize=(W+1.4, 2.8), dpi=DPI)
# left: RMSE (log) for all three -> honest, physics off-scale but visible
labs = ["Simplified\nphysics", "Data-driven\nXGB", "Physics-aug.\nhybrid"]
rmses = [phys_rmse, xgb_rmse, hyb_rmse]
cols = ["#9e9e9e","#62b9b8","#3a76c8"]
b = ax[0].bar(labs, rmses, color=cols, edgecolor="#222", lw=0.6)
ax[0].set_yscale("log")
for bb,v in zip(b,rmses): ax[0].text(bb.get_x()+bb.get_width()/2, v*1.12, f"{v:.1f}", ha="center", fontsize=7)
ax[0].set_ylabel("Test RMSE, NO$_2$ (log scale)")
ax[0].set_title("(a) Prediction error (all three)", fontsize=9)
ax[0].grid(axis="y", which="both", linestyle=":", alpha=0.4)
# right: R2 for the two usable ML models on full 0-1 axis (modest gain shown honestly)
b2 = ax[1].bar(["Data-driven\nXGB","Physics-aug.\nhybrid"], [xgb_r2, hyb_r2], color=["#62b9b8","#3a76c8"], edgecolor="#222", lw=0.6)
for bb,v in zip(b2,[xgb_r2,hyb_r2]): ax[1].text(bb.get_x()+bb.get_width()/2, v+0.02, f"{v:.3f}", ha="center", fontsize=8)
ax[1].set_ylim(0,1.05); ax[1].set_ylabel("Test R$^2$")
ax[1].set_title("(b) ML vs hybrid (modest gain)", fontsize=9)
ax[1].grid(axis="y", linestyle=":", alpha=0.4)
fig.suptitle("NO$_2$ prediction: simplified-physics, ML, and physics-augmented hybrid", fontsize=9.5, y=1.02)
fig.text(0.5, -0.10, "Simplified physics is an uncalibrated 1-D reference (R$^2$="+f"{phys_r2:.0f}"+"); the meaningful comparison is XGB vs hybrid (R$^2$ 0.951→0.962, RMSE −12%). "+CAP_NOTE,
         ha="center", fontsize=6.0, wrap=True)
plt.tight_layout(); plt.savefig(f"{FIG}/fig8_pinn_hybrid.png", dpi=DPI, bbox_inches="tight"); plt.close()

# ============ FIG 9 : ST-GCN (null result, honest axis) ============
st = json.load(open(f"{DATA}/stgnn_results.json"))["summary"]
names = [s["predictor"].replace("_"," ").replace("xgb","XGB") for s in st]
r2s = [s["r2_mean"] for s in st]; rmses = [s["rmse_mean"] for s in st]
best = int(np.argmax(r2s))
fig, ax = plt.subplots(figsize=(W+0.6, 2.9), dpi=DPI)
x = np.arange(len(names))
cols = ["#3a76c8" if i==best else "#9bbbe0" for i in range(len(names))]
b = ax.bar(x, r2s, 0.6, color=cols, edgecolor="#222", lw=0.6)
for i,(r,rm) in enumerate(zip(r2s,rmses)):
    ax.text(i, r+0.02, f"{r:.4f}\nRMSE {rm:.1f}", ha="center", fontsize=6.8)
ax.set_xticks(x); ax.set_xticklabels(names, rotation=12, fontsize=8)
ax.set_ylim(0,1.08); ax.set_ylabel("R$^2$ (mean across 10 nodes)")
ax.set_title("Traffic forecasting: graph vs local features", fontsize=9.5)
ax.grid(axis="y", linestyle=":", alpha=0.4)
ax.text(0.5, 0.40, "All variants within 0.001 R$^2$.\nThe local (no-graph) baseline is marginally best —\ngraph propagation did not improve forecasting here.",
        transform=ax.transAxes, ha="center", fontsize=7.0,
        bbox=dict(boxstyle="round", fc="#fff6e6", ec="#d8b04c", alpha=0.95))
fig.text(0.5,-0.06, CAP_NOTE, ha="center", fontsize=6.0)
plt.tight_layout(); plt.savefig(f"{FIG}/fig9_stgnn.png", dpi=DPI, bbox_inches="tight"); plt.close()

# ============ FIG 10 : MARL (error bars + naive-throttle reference + caveat) ============
marl = json.load(open(f"{DATA}/marl_results.json"))
curve = pd.DataFrame(marl["learning_curve"])
pols = marl["policies"]
# recompute naive always-throttle (action 0 -> 0.92x) under identical eval seeds for transparency
arr = np.load(f"{DATA}/v2_network.npz", allow_pickle=True); flow = arr["flow"]; T,N = flow.shape
CAP=1300
def dproxy(f): v=f/CAP; return np.maximum(0,v-0.5)**2*60
def ep(act, seed):
    r=random.Random(seed); ds=[]
    for _ in range(400):
        f=flow[r.randrange(T)].copy(); ds.append(dproxy(f*(1.0+(act-1)*0.08)).mean())
    return float(np.mean(ds))
thr_delays=[ep(0,100+t) for t in range(5)]; thr_mean=float(np.mean(thr_delays)); thr_std=float(np.std(thr_delays))
fig, axes = plt.subplots(1, 2, figsize=(W+1.4, 2.9), dpi=DPI)
axes[0].plot(curve.episode, curve.mean_delay, "-o", ms=2.5, color="#3a76c8")
axes[0].set_xlabel("Training episode"); axes[0].set_ylabel("Mean proxy delay (a.u.)")
axes[0].set_title("(a) Learning curve", fontsize=9); axes[0].grid(linestyle=":", alpha=0.5)
labels = ["fixed\ntime","greedy\npressure","MARL\nQ-learn","always-\nthrottle*"]
delays = [pols[0]["mean_delay"], pols[1]["mean_delay"], pols[2]["mean_delay"], thr_mean]
errs   = [pols[0]["delay_std"], pols[1]["delay_std"], pols[2]["delay_std"], thr_std]
cols = ["#9e9e9e","#d8b04c","#3a76c8","#c0708f"]
b = axes[1].bar(labels, delays, yerr=errs, capsize=3, color=cols, edgecolor="#222", lw=0.6, error_kw=dict(lw=0.8))
for bb,v in zip(b,delays): axes[1].text(bb.get_x()+bb.get_width()/2, v+0.025, f"{v:.3f}", ha="center", fontsize=7)
axes[1].set_ylabel("Mean proxy delay (a.u.)"); axes[1].set_title("(b) Policy comparison (±1 SD)", fontsize=9)
axes[1].grid(axis="y", linestyle=":", alpha=0.4)
fig.suptitle("MARL signal-control demonstration (illustrative delay proxy)", fontsize=9.5, y=1.03)
fig.text(0.5,-0.12, "*The delay proxy is monotone in served flow, so a naive constant throttle attains a similar reduction. "
         "Values are illustrative of the architecture, NOT validated traffic delay. "+CAP_NOTE, ha="center", fontsize=5.8, wrap=True)
plt.tight_layout(); plt.savefig(f"{FIG}/fig10_marl.png", dpi=DPI, bbox_inches="tight"); plt.close()

# ============ FIG 11 : Semantic (readable legend + per-channel panel) ============
sem = json.load(open(f"{DATA}/semantic_results.json")); df = pd.DataFrame(sem["models"])
fig, ax = plt.subplots(1, 2, figsize=(W+1.6, 2.9), dpi=DPI)
for method,color,marker in [("PCA","#9e9e9e","s"),("MLP_AE","#3a76c8","o")]:
    sub = df[df.method==method].sort_values("d_sem")
    ax[0].plot(sub.d_sem, sub.r2_mean, marker=marker, color=color, label=method, lw=1.5)
    for _,r in sub.iterrows(): ax[0].text(r.d_sem, r.r2_mean+0.02, f"{r.r2_mean:.2f}", ha="center", fontsize=6.5)
ax[0].set_xticks([2,3,4,6]); ax[0].set_xlabel("Semantic code dim $d_{sem}$")
ax[0].set_ylabel("Mean reconstruction R$^2$ (12 channels)"); ax[0].set_ylim(0.3,1.02)
ax[0].set_title("(a) Fidelity vs dimension", fontsize=9)
ax[0].legend(loc="lower right", frameon=True, framealpha=0.95, fontsize=8)
ax[0].grid(linestyle=":", alpha=0.5)
ax2 = ax[0].twiny(); ax2.set_xlim(ax[0].get_xlim()); ax2.set_xticks([2,3,4,6])
ax2.set_xticklabels([f"{12/d:.0f}×" for d in [2,3,4,6]]); ax2.set_xlabel("Compression ratio", fontsize=8)
# per-channel at d_sem=3 (4x), MLP
mlp3 = [m for m in sem["models"] if m["method"]=="MLP_AE" and m["d_sem"]==3][0]["r2_per_channel"]
order = ["no2","wind","pm25","flow","mh","hour_cos","temp","hdv","rh","dow_cos"]
vals = [mlp3[k] for k in order]
ccols = ["#3a76c8" if v>=0.8 else ("#d8b04c" if v>=0.5 else "#c0708f") for v in vals]
ax[1].barh(range(len(order)), vals, color=ccols, edgecolor="#222", lw=0.4)
ax[1].set_yticks(range(len(order))); ax[1].set_yticklabels(order, fontsize=7)
ax[1].invert_yaxis(); ax[1].set_xlim(0,1.05); ax[1].set_xlabel("R$^2$ at 4× (MLP)")
ax[1].set_title("(b) Per-channel fidelity at 4×", fontsize=9)
ax[1].axvline(0.704, color="#444", ls="--", lw=0.8); ax[1].text(0.704,9.4,"mean 0.70", fontsize=6, ha="center")
ax[1].grid(axis="x", linestyle=":", alpha=0.4)
fig.suptitle("Semantic 6G compression: fidelity vs. dimension", fontsize=9.5, y=1.03)
fig.text(0.5,-0.06,"Twin-relevant channels (NO$_2$, PM$_2.5$, flow, wind) reconstruct well at 4×; the mean is lowered by weather/calendar channels. "+CAP_NOTE, ha="center", fontsize=5.8, wrap=True)
plt.tight_layout(); plt.savefig(f"{FIG}/fig11_semantic.png", dpi=DPI, bbox_inches="tight"); plt.close()

# ============ FIG 12 : Health (neutral title + modelled-estimate caveat) ============
health = json.load(open(f"{DATA}/health_results.json"))
labels = [r["scenario"].replace(" AI+","\nAI+") for r in health[1:]]
deaths = [r["avoided_deaths_per_year_per_million"] for r in health[1:]]
daly   = [r["avoided_DALYs_per_year_per_million"] for r in health[1:]]
x = np.arange(len(labels)); w=0.38
fig, ax = plt.subplots(figsize=(W+0.6, 2.8), dpi=DPI)
b1 = ax.bar(x-w/2, deaths, w, color="#3a76c8", label="Avoided deaths /yr (left)")
ax2 = ax.twinx(); b2 = ax2.bar(x+w/2, daly, w, color="#d36b3a", label="Avoided DALYs /yr (right)")
for bb,v in zip(b1,deaths): ax.text(bb.get_x()+bb.get_width()/2, v+1.5, f"{v:.0f}", ha="center", fontsize=7)
for bb,v in zip(b2,daly):   ax2.text(bb.get_x()+bb.get_width()/2, v+30, f"{v:.0f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("Avoided deaths /yr per million", color="#3a76c8")
ax2.set_ylabel("Avoided DALYs /yr per million", color="#d36b3a")
ax.set_title("Estimated health co-benefits under simulated scenarios\n(per million population)", fontsize=9)
ax.grid(axis="y", linestyle=":", alpha=0.4)
h1,l1 = ax.get_legend_handles_labels(); h2,l2 = ax2.get_legend_handles_labels()
ax.legend(h1+h2, l1+l2, loc="upper left", fontsize=6.5, frameon=True, framealpha=0.95)
fig.text(0.5,-0.08,"Modelled estimates from concentration–response functions applied to simulated scenario air quality — not measured health outcomes; "
         "PM$_2.5$/NO$_2$ overlap mitigated by 0.75 weighting. "+CAP_NOTE, ha="center", fontsize=5.6, wrap=True)
plt.tight_layout(); plt.savefig(f"{FIG}/fig12_health.png", dpi=DPI, bbox_inches="tight"); plt.close()

import os
for f in sorted(os.listdir(FIG)):
    if f.endswith(".png"):
        print(f"  {f}  {os.path.getsize(f'{FIG}/{f}')/1024:.1f} KB")
print("AUDITED figures done.")
