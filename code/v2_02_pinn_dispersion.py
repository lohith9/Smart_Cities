"""
v2_02_pinn_dispersion.py
Physics-augmented ML for AQ dispersion (PINN-style hybrid).

This module implements three predictors and compares them:

(A) Pure data-driven (XGBoost) - baseline.
(B) Pure physics: 1-D advection-diffusion finite-difference solver of the
    pollutant transport PDE along the corridor.
(C) Hybrid Physics-Augmented Neural Network (PANN): XGBoost predicts the
    residual between the physics solver and reality. Inspired by
    Karpatne et al. (2022) "Knowledge-Guided Machine Learning" and the
    physics-informed neural network family (Raissi et al., J Comp Phys 2019).

The PDE governing roadside pollutant concentration C(x,t) is:
    dC/dt + u * dC/dx = K * d2C/dx2 + S(x,t) - lambda*C        (PDE)
where:
    u       = advection (wind speed component along corridor) [m/s]
    K       = turbulent diffusion coefficient [m2/s]
    S(x,t)  = emission source strength derived from traffic flow [ug/m3/s]
    lambda  = first-order decay (deposition + chemistry) [1/s]

We solve PDE with an upwind explicit finite-difference scheme on a 10-cell
grid corresponding to the 10 network nodes. Each cell is 400 m wide.

Outputs:
  ../data/pinn_results.json
  ../data/pinn_predictions.csv
"""
import numpy as np
import pandas as pd
import json
import xgboost as xgb
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import time

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
rng = np.random.default_rng(20260516)

# ----- Load multi-corridor data --------------------------------------------
arr = np.load(f"{DATA}/v2_network.npz", allow_pickle=True)
flow = arr["flow"]                  # (T, N)
hdv  = arr["hdv"]
no2  = arr["no2"]
wind = arr["wind_speed"]
mh   = arr["mixing_h"]
T, N = flow.shape
print(f"Loaded: T={T} timesteps, N={N} nodes")

# ----- (B) Physics-only PDE solver -----------------------------------------
EF_NO2_LDV, EF_NO2_HDV = 0.42, 2.10  # g/km
dx = 400.0       # cell width [m]
dt = 60.0        # solver step [s]
K_diff = 8.0     # turbulent diffusion [m^2/s] - typical urban canopy
decay  = 5e-5    # 1/s (~5 hr e-folding) - chemistry + deposition

def physics_step(C, u, S, dt, dx):
    """Single upwind explicit advection-diffusion step. C, S: (N,)."""
    # Advection (upwind, assume positive u flow direction)
    adv = np.zeros_like(C)
    if u >= 0:
        adv[1:] = -u * (C[1:] - C[:-1]) / dx
        adv[0]  = -u * (C[0] - C[-1]) / dx  # periodic BC for stability
    else:
        adv[:-1] = -u * (C[1:] - C[:-1]) / dx
        adv[-1]  = -u * (C[0] - C[-1]) / dx
    # Diffusion (central)
    diff = np.zeros_like(C)
    diff[1:-1] = K_diff * (C[2:] - 2*C[1:-1] + C[:-2]) / dx**2
    diff[0]    = K_diff * (C[1] - C[0]) / dx**2
    diff[-1]   = K_diff * (C[-2] - C[-1]) / dx**2
    return C + dt * (adv + diff + S - decay * C)

def emission_source_no2(flow_n, hdv_n, mh_n):
    """Source strength in ug/m3/s per cell, normalised by mixing-height column."""
    ldv = 1 - hdv_n
    g_per_km_h = flow_n * (ldv * EF_NO2_LDV + hdv_n * EF_NO2_HDV)
    # Convert: emission per km per hour -> per cell-volume per second
    # Cell volume approx dx * lane_width * mixing_h. lane_width~10m effective
    cell_vol_m3 = dx * 10.0 * np.maximum(mh_n, 100.0)
    # 1 g = 1e6 ug
    return (g_per_km_h * 1e6 / 3600.0) * (dx / 1000.0) / cell_vol_m3

# Pre-compute all source terms vectorised
S_all = np.zeros((T, N))
for n in range(N):
    ldv = 1 - hdv[:, n]
    g_per_km_h = flow[:, n] * (ldv * EF_NO2_LDV + hdv[:, n] * EF_NO2_HDV)
    cell_vol_m3 = dx * 10.0 * np.maximum(mh, 100.0)
    S_all[:, n] = (g_per_km_h * 1e6 / 3600.0) * (dx / 1000.0) / cell_vol_m3

u_all = wind * 0.7  # along-corridor projection (T,)

# Run physics solver - vectorised inner step
C_phys = np.zeros((T, N))
C_phys[0] = 14.0
dt_sub = 120.0   # 2-min substep (satisfies CFL for u<3.3 m/s; clipped below)
substeps = int(3600 / dt_sub)  # 30 substeps per hour

for t in range(1, T):
    C = C_phys[t-1].copy()
    # Effective u clipped to satisfy CFL with this substep
    u_t = np.clip(u_all[t], -3.0, 3.0)
    S_t = S_all[t]
    for _ in range(substeps):
        # Advection (upwind)
        adv = np.zeros_like(C)
        if u_t >= 0:
            adv[1:] = -u_t * (C[1:] - C[:-1]) / dx
            adv[0]  = -u_t * (C[0] - C[-1]) / dx
        else:
            adv[:-1] = -u_t * (C[1:] - C[:-1]) / dx
            adv[-1]  = -u_t * (C[0] - C[-1]) / dx
        # Diffusion (central)
        diff = np.zeros_like(C)
        diff[1:-1] = K_diff * (C[2:] - 2*C[1:-1] + C[:-2]) / dx**2
        diff[0]    = K_diff * (C[1] - C[0]) / dx**2
        diff[-1]   = K_diff * (C[-2] - C[-1]) / dx**2
        C = C + dt_sub * (adv + diff + S_t - decay * C)
    C_phys[t] = C + 14.0
C_phys = np.clip(C_phys, 4, 180)
print(f"Physics-only mean NO2: {C_phys.mean():.2f}  (obs={no2.mean():.2f})")

# ----- (A) Pure data-driven (XGBoost) ---------------------------------------
def build_feats(arr_dict, n):
    """Per-node feature matrix."""
    T = arr_dict["flow"].shape[0]
    f = np.column_stack([
        arr_dict["flow"][:, n],
        arr_dict["hdv"][:, n],
        arr_dict["wind_speed"],
        arr_dict["mixing_h"],
        arr_dict["temp"],
        arr_dict["humidity"],
        np.sin(2*np.pi*arr_dict["hour_of_day"]/24),
        np.cos(2*np.pi*arr_dict["hour_of_day"]/24),
        np.sin(2*np.pi*arr_dict["dow"]/7),
        np.cos(2*np.pi*arr_dict["dow"]/7),
    ])
    return f

# Use node 2 (Marylebone-1) as the focus station for comparison
NODE = 2
X = build_feats(arr, NODE)
y_obs = no2[:, NODE]
y_phys = C_phys[:, NODE]

# Time split
i_tr = int(0.7 * T)
i_va = int(0.85 * T)

# (A) Pure data-driven
t0 = time.time()
xgb_pure = xgb.XGBRegressor(n_estimators=400, max_depth=6, learning_rate=0.05,
                            subsample=0.85, colsample_bytree=0.85,
                            random_state=20260516, verbosity=0, n_jobs=1)
xgb_pure.fit(X[:i_tr], y_obs[:i_tr])
pred_pure = xgb_pure.predict(X[i_va:])
t_a = time.time() - t0

# (C) Physics-augmented: XGB learns residual r = y_obs - y_phys
residual = y_obs - y_phys
xgb_resid = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                              subsample=0.85, colsample_bytree=0.85,
                              random_state=20260516, verbosity=0, n_jobs=1)
xgb_resid.fit(X[:i_tr], residual[:i_tr])
pred_resid = xgb_resid.predict(X[i_va:])
pred_hybrid = y_phys[i_va:] + pred_resid
t_c = time.time() - t0

y_te = y_obs[i_va:]
results = {
    "node_focus": str(NODE),
    "node_name": "Marylebone-1",
    "physics_only": {
        "r2":   float(r2_score(y_te, y_phys[i_va:])),
        "rmse": float(np.sqrt(mean_squared_error(y_te, y_phys[i_va:]))),
        "mae":  float(mean_absolute_error(y_te, y_phys[i_va:])),
    },
    "data_driven_xgb": {
        "r2":   float(r2_score(y_te, pred_pure)),
        "rmse": float(np.sqrt(mean_squared_error(y_te, pred_pure))),
        "mae":  float(mean_absolute_error(y_te, pred_pure)),
        "train_time_s": float(t_a),
    },
    "physics_augmented": {
        "r2":   float(r2_score(y_te, pred_hybrid)),
        "rmse": float(np.sqrt(mean_squared_error(y_te, pred_hybrid))),
        "mae":  float(mean_absolute_error(y_te, pred_hybrid)),
        "train_time_s": float(t_c),
    },
}
print("\n=== PINN-style hybrid AQ predictor ===")
for k, v in results.items():
    if isinstance(v, dict):
        print(f"  {k}: R2={v['r2']:.3f}, RMSE={v['rmse']:.3f}, MAE={v['mae']:.3f}")

# Save predictions for plotting
pd.DataFrame({
    "obs":           y_obs,
    "physics_only":  y_phys,
}).to_csv(f"{DATA}/pinn_full_timeseries.csv", index=False)

pd.DataFrame({
    "obs":      y_te,
    "physics":  y_phys[i_va:],
    "xgb_pure": pred_pure,
    "hybrid":   pred_hybrid,
}).to_csv(f"{DATA}/pinn_predictions.csv", index=False)

print("\nPDE residual diagnostic:")
res_pde = []
for t in range(2, T):
    dCdt = (C_phys[t] - C_phys[t-1]) / 3600.0
    dCdx = np.zeros(N)
    dCdx[1:] = (C_phys[t, 1:] - C_phys[t, :-1]) / dx
    d2Cdx2 = np.zeros(N)
    d2Cdx2[1:-1] = (C_phys[t, 2:] - 2*C_phys[t, 1:-1] + C_phys[t, :-2]) / dx**2
    u_t = np.clip(u_all[t], -3.0, 3.0)
    res = dCdt + u_t * dCdx - K_diff * d2Cdx2 - S_all[t] + decay * C_phys[t]
    res_pde.append(float(np.abs(res).mean()))
results["pde_residual_mean"] = float(np.mean(res_pde))
print(f"  Mean |PDE residual|: {np.mean(res_pde):.4e}")

with open(f"{DATA}/pinn_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved -> {DATA}/pinn_results.json")
