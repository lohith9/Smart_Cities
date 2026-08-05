"""
v2_03_stgnn.py
Spatio-Temporal Graph Convolution traffic predictor.

We implement a lightweight ST-GCN in pure numpy + sklearn following the
formulation of Yu, Yin, Zhu (IJCAI 2018, 'Spatio-Temporal Graph Convolutional
Networks: A Deep Learning Framework for Traffic Forecasting', pp. 3634-3640,
doi:10.24963/ijcai.2018/505):

   H_l+1 = sigma( A_hat @ H_l @ W_l )    (spatial graph convolution)

We unfold the temporal axis through K=3 hourly lags per node, concatenate
them as input features, then apply a single graph-convolution propagation
step using the precomputed normalised adjacency. The propagated features
become inputs to a per-node XGBoost head that predicts the next-hour flow.

Baselines compared (all evaluated on the same chronological train/test split):
  (1) Local-only XGB    - no neighbour information
  (2) Mean-pool         - simple spatial averaging of neighbour flows
  (3) ST-GCN (1 layer)  - normalised graph propagation + XGB head
  (4) ST-GCN (2 layer)  - two propagation steps capture 2-hop neighbourhood

Outputs:
  ../data/stgnn_results.json    - per-node and aggregate metrics
"""
import json
import time
import numpy as np
import xgboost as xgb
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
arr = np.load(f"{DATA}/v2_network.npz", allow_pickle=True)
A   = np.load(f"{DATA}/v2_adjacency.npy")
flow = arr["flow"]   # (T,N)
T, N = flow.shape
print(f"T={T}, N={N}, A shape={A.shape}")

# ----- Build temporal lag tensor -------------------------------------------
K = 3  # number of hourly lags
def lag_stack(x, k):
    """Returns array shape (T-k, k+1, N) with [t-k, ..., t] history."""
    out = np.stack([x[k-i:T-i] for i in range(k+1)], axis=1)  # (T-k, k+1, N)
    return out

H = lag_stack(flow, K)            # shape (T-K, K+1, N)
y_full = flow[K+1:]               # shape (T-K-1, N) - predict next hour
H = H[:-1]                        # align with y; shape (T-K-1, K+1, N)
T_eff = H.shape[0]
print(f"After lag+shift: T_eff={T_eff}")

# Add meteorology + temporal features (broadcast across nodes)
wind = arr["wind_speed"][K+1:]
mh   = arr["mixing_h"][K+1:]
temp = arr["temp"][K+1:]
hod  = arr["hour_of_day"][K+1:]
dow  = arr["dow"][K+1:]
exog = np.column_stack([wind, mh, temp,
                        np.sin(2*np.pi*hod/24), np.cos(2*np.pi*hod/24),
                        np.sin(2*np.pi*dow/7),  np.cos(2*np.pi*dow/7)])  # (T_eff, 7)

# Split chronologically
i_tr = int(0.7 * T_eff)
i_va = int(0.85 * T_eff)

def evaluate(predictor_name, X_per_node, y, i_tr, i_va, max_depth=6):
    """X_per_node: list of N feature matrices each (T_eff, F)."""
    all_metrics = []
    t_total = 0
    preds = np.zeros_like(y)
    for n in range(N):
        Xn = X_per_node[n]
        yn = y[:, n]
        t0 = time.time()
        m = xgb.XGBRegressor(n_estimators=120, max_depth=min(max_depth, 5),
                             learning_rate=0.08, subsample=0.85,
                             colsample_bytree=0.85, random_state=20260516,
                             verbosity=0, n_jobs=1, tree_method="hist")
        m.fit(Xn[:i_tr], yn[:i_tr])
        pred = m.predict(Xn[i_va:])
        t_total += time.time() - t0
        preds[i_va:, n] = pred
        all_metrics.append({
            "r2":   float(r2_score(yn[i_va:], pred)),
            "rmse": float(np.sqrt(mean_squared_error(yn[i_va:], pred))),
            "mae":  float(mean_absolute_error(yn[i_va:], pred)),
        })
    agg = {
        "predictor": predictor_name,
        "r2_mean":   float(np.mean([m["r2"]   for m in all_metrics])),
        "rmse_mean": float(np.mean([m["rmse"] for m in all_metrics])),
        "mae_mean":  float(np.mean([m["mae"]  for m in all_metrics])),
        "train_time_s": float(t_total),
        "per_node": all_metrics,
    }
    return agg, preds

# (1) Local-only: features = own K lags + exog
X_local = []
for n in range(N):
    own_lags = H[:, :, n]   # (T_eff, K+1)
    X_local.append(np.column_stack([own_lags, exog]))
r1, _ = evaluate("local_xgb", X_local, y_full, i_tr, i_va)

# (2) Mean-pool: each node sees mean of own + neighbours' lag history
A_bin = (A > 0).astype(float)
A_bin = A_bin / A_bin.sum(axis=1, keepdims=True)  # row-normalised
X_mean = []
for n in range(N):
    # mean over neighbours including self
    own = H[:, :, n]
    nbrs_idx = np.where(A_bin[n] > 0)[0]
    nbr_mean = H[:, :, nbrs_idx].mean(axis=2)  # (T_eff, K+1)
    X_mean.append(np.column_stack([own, nbr_mean, exog]))
r2_, _ = evaluate("mean_pool", X_mean, y_full, i_tr, i_va)

# (3) ST-GCN 1 layer: H' = A_hat @ H along node dim, per timestep & per lag
H_gc1 = np.einsum("ij,tkj->tki", A, H)   # graph conv along nodes
X_gc1 = []
for n in range(N):
    own = H[:, :, n]
    propagated = H_gc1[:, :, n]
    X_gc1.append(np.column_stack([own, propagated, exog]))
r3, preds3 = evaluate("st_gcn_1layer", X_gc1, y_full, i_tr, i_va)

# (4) ST-GCN 2 layer
H_gc2 = np.einsum("ij,tkj->tki", A, H_gc1)
X_gc2 = []
for n in range(N):
    X_gc2.append(np.column_stack([H[:,:,n], H_gc1[:,:,n], H_gc2[:,:,n], exog]))
r4, preds4 = evaluate("st_gcn_2layer", X_gc2, y_full, i_tr, i_va)

results = {
    "summary": [
        {"predictor": r1["predictor"], "r2_mean": r1["r2_mean"], "rmse_mean": r1["rmse_mean"], "mae_mean": r1["mae_mean"]},
        {"predictor": r2_["predictor"], "r2_mean": r2_["r2_mean"], "rmse_mean": r2_["rmse_mean"], "mae_mean": r2_["mae_mean"]},
        {"predictor": r3["predictor"], "r2_mean": r3["r2_mean"], "rmse_mean": r3["rmse_mean"], "mae_mean": r3["mae_mean"]},
        {"predictor": r4["predictor"], "r2_mean": r4["r2_mean"], "rmse_mean": r4["rmse_mean"], "mae_mean": r4["mae_mean"]},
    ],
    "detailed": [r1, r2_, r3, r4],
}

print("\n=== ST-GCN traffic forecasting ===")
for s in results["summary"]:
    print(f"  {s['predictor']:18s}  R2_mean={s['r2_mean']:.4f}  RMSE_mean={s['rmse_mean']:.2f}  MAE_mean={s['mae_mean']:.2f}")

with open(f"{DATA}/stgnn_results.json", "w") as out:
    json.dump(results, out, indent=2)
print("Saved results JSON")
