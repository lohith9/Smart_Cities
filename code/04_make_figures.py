"""
04_make_figures.py
Generate all 7 chapter figures at 300 dpi, sized for IntechOpen
(<= 130mm wide ~= 5.118 in). Figures are saved to ../figures/.

Figures:
  Figure 1: Five-layer system architecture (schematic)
  Figure 2: Data and modelling pipeline
  Figure 3: AI prediction performance (R2 / RMSE bars per model & target)
  Figure 4: Observed vs predicted PM2.5 + NO2 time series on the test set
  Figure 5: Scenario comparison - delay, PM2.5, NO2 reductions
  Figure 6: 6G latency vs control update frequency; state-lag sensitivity
  Figure 7: Sensitivity to traffic demand (+/-20%) and HDV share
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
})

WIDTH_IN = 5.0   # ~127mm
DPI = 300
EN = "\u2013"
from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
OUT = str(ROOT / "figures")
_os.makedirs(DATA, exist_ok=True)
_os.makedirs(OUT, exist_ok=True)

# Load artifacts
df_data = pd.read_csv(f"{DATA}/london_corridor.csv", parse_dates=["timestamp"])
with open(f"{DATA}/ml_results.json") as f:
    ml = json.load(f)
df_pred = pd.read_csv(f"{DATA}/predictions.csv", parse_dates=["timestamp"])
scenarios = pd.read_csv(f"{DATA}/scenarios.csv")

# ----------------------------------------------------------------------
# FIG 1 - Five-layer architecture diagram
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.5), dpi=DPI)
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
layers = [
    ("Layer 5 – 6G-Enabled Real-Time Control\n(edge intelligence, <1 ms RTT, 10 Hz loops)", "#3a76c8"),
    ("Layer 4 – Traffic-to-Emissions Coupling\n(COPERT-style EF + Gaussian dispersion)", "#4c9ec9"),
    ("Layer 3 – AI Analytics\n(RandomForest / XGBoost predictors)", "#62b9b8"),
    ("Layer 2 – Digital Twin Modelling\n(SUMO microsim + GIS road network)", "#8ac7a3"),
    ("Layer 1 – Open Data Ingestion\n(LAQN, TfL, MetOffice, OSM)", "#c3d68f"),
]
y0, dy = 0.5, 1.65
for i, (txt, col) in enumerate(layers):
    box = FancyBboxPatch((0.6, y0 + i*dy), 8.8, 1.35,
                         boxstyle="round,pad=0.04,rounding_size=0.15",
                         facecolor=col, edgecolor="#222", linewidth=0.8)
    ax.add_patch(box)
    ax.text(5.0, y0 + i*dy + 0.67, txt, ha="center", va="center", fontsize=9,
            color="white" if i < 3 else "black", weight="bold" if i==0 else "normal")
# Up arrow on left, Down arrow on right
ax.annotate("", xy=(0.4, 9.0), xytext=(0.4, 1.0),
            arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6",
                            color="#222", lw=1.4))
ax.annotate("", xy=(9.6, 1.0), xytext=(9.6, 9.0),
            arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6",
                            color="#222", lw=1.4))
ax.text(0.15, 5.0, "Data flow up", rotation=90, ha="center", va="center", fontsize=8, color="#444")
ax.text(9.85, 5.0, "Control flow down", rotation=270, ha="center", va="center", fontsize=8, color="#444")
plt.tight_layout()
plt.savefig(f"{OUT}/fig1_architecture.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 2 - Data & modelling pipeline (flow diagram)
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.4), dpi=DPI)
ax.set_xlim(0, 11); ax.set_ylim(0, 6); ax.axis("off")
def node(x, y, w, h, txt, col):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.04,rounding_size=0.12",
                                facecolor=col, edgecolor="#222", linewidth=0.7))
    ax.text(x + w/2, y + h/2, txt, ha="center", va="center", fontsize=8)
def arrow(x0,y0,x1,y1):
    ax.annotate("", xy=(x1,y1), xytext=(x0,y0),
                arrowprops=dict(arrowstyle="->", color="#333", lw=1))
node(0.1, 4.2, 2.2, 1.0, "Open Datasets\n(LAQN, TfL, OSM)", "#c3d68f")
node(0.1, 2.5, 2.2, 1.0, "Meteorology\n(MetOffice / ERA5)", "#c3d68f")
node(0.1, 0.8, 2.2, 1.0, "OSM Road Network", "#c3d68f")
node(3.0, 3.4, 2.2, 1.0, "Feature\nEngineering", "#dbe4a6")
node(3.0, 1.6, 2.2, 1.0, "SUMO Network\n(netconvert)", "#dbe4a6")
node(6.0, 4.5, 2.0, 1.0, "Traffic\nPredictor (RF)", "#62b9b8")
node(6.0, 2.9, 2.0, 1.0, "AQ Predictor\n(XGBoost)", "#62b9b8")
node(6.0, 1.3, 2.0, 1.0, "Emission\nCoupling", "#4c9ec9")
node(8.7, 2.9, 2.1, 1.5, "Digital Twin\nScenario Engine\n(SUMO + AI)", "#3a76c8")
for a,b in [((2.3,4.7),(3.0,3.9)),((2.3,3.0),(3.0,3.7)),((2.3,1.3),(3.0,2.1)),
            ((5.2,3.9),(6.0,5.0)),((5.2,3.6),(6.0,3.3)),((5.2,2.0),(6.0,1.7)),
            ((8.0,5.0),(8.7,4.0)),((8.0,3.3),(8.7,3.5)),((8.0,1.7),(8.7,3.0))]:
    arrow(a[0],a[1],b[0],b[1])
plt.tight_layout()
plt.savefig(f"{OUT}/fig2_pipeline.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 3 - Bar chart of R2 across models and targets
# ----------------------------------------------------------------------
targets = ["traffic_flow_vph", "pm25_ugm3", "no2_ugm3"]
target_labels = ["Traffic flow", r"PM$_{2.5}$", r"NO$_2$"]
models = ["LinearRegression", "RandomForest", "XGBoost"]
model_colors = ["#9e9e9e", "#3a76c8", "#62b9b8"]

fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.0), dpi=DPI)
x = np.arange(len(targets))
w = 0.27
for i, m in enumerate(models):
    vals = [next(r["r2"] for r in ml[t] if r["model"] == m) for t in targets]
    ax.bar(x + (i-1)*w, vals, w, label=m, color=model_colors[i], edgecolor="#222", lw=0.6)
    for j, v in enumerate(vals):
        ax.text(x[j] + (i-1)*w, v + 0.012, f"{v:.3f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(target_labels)
ax.set_ylabel(r"R$^2$ on held-out test set")
ax.set_ylim(0, 1.08)
ax.set_title("Prediction accuracy across models and targets")
ax.legend(loc="lower right", frameon=False)
ax.grid(axis="y", linestyle=":", alpha=0.5)
plt.tight_layout()
plt.savefig(f"{OUT}/fig3_r2_bars.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 4 - Time series: observed vs predicted PM2.5 and NO2 on test set
# ----------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(WIDTH_IN, 4.8), dpi=DPI, sharex=True)
# Plot first 7 days of test set for readability
plot_len = min(7*24, len(df_pred))
sub = df_pred.iloc[:plot_len]
axes[0].plot(sub.timestamp, sub.pm25_ugm3_true, "k-", lw=1.0, label="Observed")
axes[0].plot(sub.timestamp, sub.pm25_ugm3_rf,   "--", color="#3a76c8", lw=1.0, label="RandomForest")
axes[0].plot(sub.timestamp, sub.pm25_ugm3_xgb,  ":", color="#d36b3a", lw=1.0, label="XGBoost")
axes[0].set_ylabel(r"PM$_{2.5}$ ($\mu$g/m$^3$)")
axes[0].legend(loc="upper right", frameon=False, ncol=3)
axes[0].set_title("Observed vs predicted air quality – first week of test set")
axes[0].grid(linestyle=":", alpha=0.5)

axes[1].plot(sub.timestamp, sub.no2_ugm3_true, "k-", lw=1.0, label="Observed")
axes[1].plot(sub.timestamp, sub.no2_ugm3_rf,   "--", color="#3a76c8", lw=1.0, label="RandomForest")
axes[1].plot(sub.timestamp, sub.no2_ugm3_xgb,  ":", color="#d36b3a", lw=1.0, label="XGBoost")
axes[1].set_ylabel(r"NO$_2$ ($\mu$g/m$^3$)")
axes[1].grid(linestyle=":", alpha=0.5)
for ax_ in axes:
    ax_.tick_params(axis="x", rotation=20)
plt.tight_layout()
plt.savefig(f"{OUT}/fig4_predictions.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 5 - Scenario comparison (3-panel: delay, PM2.5, NO2)
# ----------------------------------------------------------------------
scen_short = ["S0", "S1", "S2", "S3"]
fig, axes = plt.subplots(1, 3, figsize=(WIDTH_IN+1.7, 3.1), dpi=DPI)
colors = ["#9e9e9e", "#62b9b8", "#3a76c8", "#1e4a8a"]
metrics = [
    ("mean_delay_min_per_km", "Mean delay (min/km)", "delay_red_pct"),
    ("mean_pm25_ugm3",        r"Mean PM$_{2.5}$ ($\mu$g/m$^3$)", "pm25_red_pct"),
    ("mean_no2_ugm3",         r"Mean NO$_2$ ($\mu$g/m$^3$)",  "no2_red_pct"),
]
for ax, (col, lab, redcol) in zip(axes, metrics):
    vals = scenarios[col].values
    reds = scenarios[redcol].values
    bars = ax.bar(scen_short, vals, color=colors, edgecolor="#222", lw=0.6)
    for b, v, r in zip(bars, vals, reds):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
        if r > 0.01:
            ax.text(b.get_x() + b.get_width()/2, v*0.5, f"{EN}{r:.0f}%", ha="center", va="center", fontsize=7, color="white", weight="bold")
    ax.set_title(lab)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_ylim(0, max(vals) * 1.30)
plt.tight_layout(w_pad=1.6)
plt.savefig(f"{OUT}/fig5_scenarios.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 6 - 6G impact: latency vs update frequency & state-lag
# ----------------------------------------------------------------------
# Sweep update Hz from 0.001 to 100, compute state-lag
hz = np.logspace(-3, 2, 100)
state_lag = (1.0 / hz) * 0.0464  # veh/s std
fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.2), dpi=DPI)
ax.loglog(hz, state_lag, "b-", lw=1.4, label="State drift per control period")
ax.axvline(0.0033, color="#9e9e9e", ls="--", lw=1, alpha=0.8)
ax.axvline(1.0,    color="#62b9b8", ls="--", lw=1, alpha=0.8)
ax.axvline(10.0,   color="#3a76c8", ls="--", lw=1, alpha=0.8)
ax.set_ylim(5e-4, 5e2)
ax.text(0.0033, 1.4e2, "4G/fixed-time\n(0.003 Hz)", fontsize=7, color="#555", ha="center", va="top")
ax.text(1.0,    1.4e2, "5G adaptive\n(1 Hz)",       fontsize=7, color="#3a766b", ha="center", va="top")
ax.text(10.0,   1.4e2, "6G edge\n(10 Hz)",          fontsize=7, color="#1e4a8a", ha="center", va="top")
ax.set_xlabel("Control loop frequency (Hz)")
ax.set_ylabel("Vehicles drifted per cycle (uncaptured state)")
ax.set_title("State drift per control cycle vs. control-loop frequency", pad=12)
ax.grid(which="both", linestyle=":", alpha=0.5)
plt.tight_layout()
plt.savefig(f"{OUT}/fig6_6g_latency.png", dpi=DPI, bbox_inches="tight")
plt.close()

# ----------------------------------------------------------------------
# FIG 7 - Sensitivity: vary peak demand & HDV share; effect on NO2
# ----------------------------------------------------------------------
demand_range = np.linspace(0.7, 1.3, 7)
hdv_range    = np.linspace(0.04, 0.20, 7)
EF_NO2_LDV, EF_NO2_HDV = 0.42, 2.10
mean_no2_grid = np.zeros((len(demand_range), len(hdv_range)))
for i, dmul in enumerate(demand_range):
    for j, hdv in enumerate(hdv_range):
        flow = df_data.traffic_flow_vph * dmul
        ldv = 1 - hdv
        e_no = flow * (ldv * EF_NO2_LDV + hdv * EF_NO2_HDV)
        disp = 1.0 / (np.maximum(df_data.wind_speed_ms, 0.5) * df_data.mixing_height_m / 1000)
        mean_no2_grid[i, j] = (14 + 0.088 * e_no * disp).mean()
fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.4), dpi=DPI)
im = ax.imshow(mean_no2_grid, origin="lower", aspect="auto",
               extent=[hdv_range[0]*100, hdv_range[-1]*100,
                       demand_range[0]*100, demand_range[-1]*100],
               cmap="YlOrRd")
cb = fig.colorbar(im, ax=ax)
cb.set_label(r"Mean NO$_2$ ($\mu$g/m$^3$)")
ax.set_xlabel("HDV share (%)")
ax.set_ylabel("Peak demand vs baseline (%)")
ax.set_title(r"Sensitivity of NO$_2$ to traffic demand & HDV share")
ax.axhline(100, color="white", ls="--", lw=0.8)
ax.axvline(10, color="white", ls="--", lw=0.8)
plt.tight_layout()
plt.savefig(f"{OUT}/fig7_sensitivity.png", dpi=DPI, bbox_inches="tight")
plt.close()

print("All figures generated in", OUT)
import os
for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    sz = os.path.getsize(p)
    print(f"  {f}  {sz/1024:.1f} KB")
