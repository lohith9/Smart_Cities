"""
v2_05_semantic_6g.py
Semantic-communication autoencoder for 6G uplink compression.

Following Gunduz et al. (IEEE JSAC 2023, 'Beyond Transmitting Bits: Context,
Semantics, and Task-Oriented Communications'), Shi et al. (Proc IEEE 2023)
and Strinati & Barbarossa (2024), we encode the multi-modal sensor packet
{flow, hdv, pm25, no2, wind, mh, temp, rh, hour_sin, hour_cos, dow_sin,
dow_cos} -> 12 floats per timestep, into a compressed semantic representation
of dimension d_sem in {2, 3, 4, 6}, and reconstruct it at the edge twin.

Two encoder families compared:
  - PCA (linear autoencoder, optimal MSE under linear constraint)
  - MLP autoencoder (sklearn MLPRegressor used as an explicit bottleneck)

Metric: per-channel reconstruction R^2, mean R^2, and uplink bandwidth
saved if the link goes from 12 float32 (48 bytes) to d_sem float16 (2*d_sem B).

Outputs:
  ../data/semantic_results.json
  ../data/semantic_reconstruction.csv
"""
import json, time
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import r2_score, mean_squared_error

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
arr = np.load(f"{DATA}/v2_network.npz", allow_pickle=True)

# Build the 12-feature semantic packet across all 10 nodes -> stack timesteps as rows
def packet_for_node(n):
    return np.column_stack([
        arr["flow"][:, n],
        arr["hdv"][:, n],
        arr["pm25"][:, n],
        arr["no2"][:, n],
        arr["wind_speed"],
        arr["mixing_h"],
        arr["temp"],
        arr["humidity"],
        np.sin(2*np.pi*arr["hour_of_day"]/24),
        np.cos(2*np.pi*arr["hour_of_day"]/24),
        np.sin(2*np.pi*arr["dow"]/7),
        np.cos(2*np.pi*arr["dow"]/7),
    ])

X = np.vstack([packet_for_node(n) for n in range(10)])
print(f"Packet matrix: {X.shape}")
n_features = X.shape[1]
feature_names = ["flow","hdv","pm25","no2","wind","mh","temp","rh",
                 "hour_sin","hour_cos","dow_sin","dow_cos"]

# Time-based split: take 85% train (first 85% of each node), 15% test
T = arr["flow"].shape[0]
per_node = T
test_mask = np.zeros(X.shape[0], dtype=bool)
for n in range(10):
    test_mask[n*per_node + int(0.85*per_node) : (n+1)*per_node] = True

scaler = StandardScaler().fit(X[~test_mask])
Xn_tr = scaler.transform(X[~test_mask])
Xn_te = scaler.transform(X[test_mask])

results = {"models": []}
recon_dump = {}

for d_sem in [2, 3, 4, 6]:
    # --- PCA ---
    t0 = time.time()
    pca = PCA(n_components=d_sem).fit(Xn_tr)
    z_tr = pca.transform(Xn_tr); z_te = pca.transform(Xn_te)
    Xhat_tr = pca.inverse_transform(z_tr); Xhat_te = pca.inverse_transform(z_te)
    t_pca = time.time() - t0

    r2_per = [r2_score(Xn_te[:, i], Xhat_te[:, i]) for i in range(n_features)]
    pca_summary = {
        "method": "PCA",
        "d_sem": d_sem,
        "compression_ratio": float(n_features / d_sem),
        "uplink_bytes_per_packet_float16": int(2 * d_sem),
        "uplink_bytes_baseline": int(4 * n_features),
        "r2_mean":      float(np.mean(r2_per)),
        "r2_per_channel": {feature_names[i]: float(r2_per[i]) for i in range(n_features)},
        "rmse_total":   float(np.sqrt(mean_squared_error(Xn_te, Xhat_te))),
        "encode_decode_time_us_per_sample": float(1e6 * t_pca / X.shape[0]),
    }
    results["models"].append(pca_summary)

    # --- MLP autoencoder (small, sklearn) ---
    t0 = time.time()
    mlp = MLPRegressor(hidden_layer_sizes=(16, d_sem, 16),
                       activation="relu",
                       solver="adam", learning_rate_init=0.005,
                       max_iter=80, random_state=20260516, early_stopping=False)
    mlp.fit(Xn_tr, Xn_tr)
    Xhat_te_mlp = mlp.predict(Xn_te)
    t_mlp = time.time() - t0
    r2_per_mlp = [r2_score(Xn_te[:, i], Xhat_te_mlp[:, i]) for i in range(n_features)]
    mlp_summary = {
        "method": "MLP_AE",
        "d_sem": d_sem,
        "compression_ratio": float(n_features / d_sem),
        "uplink_bytes_per_packet_float16": int(2 * d_sem),
        "uplink_bytes_baseline": int(4 * n_features),
        "r2_mean":      float(np.mean(r2_per_mlp)),
        "r2_per_channel": {feature_names[i]: float(r2_per_mlp[i]) for i in range(n_features)},
        "rmse_total":   float(np.sqrt(mean_squared_error(Xn_te, Xhat_te_mlp))),
        "train_time_s": float(t_mlp),
    }
    results["models"].append(mlp_summary)
    print(f"d_sem={d_sem}  PCA R2_mean={pca_summary['r2_mean']:.3f}  MLP_AE R2_mean={mlp_summary['r2_mean']:.3f}  ratio={n_features/d_sem:.1f}x")

    # Keep reconstructed timeseries at d_sem=3 for plotting
    if d_sem == 3:
        recon_dump = pd.DataFrame({
            "feature": np.tile(np.arange(n_features), 100),
            "obs":    Xn_te[:100].flatten(),
            "pca":    Xhat_te[:100].flatten(),
            "mlp":    Xhat_te_mlp[:100].flatten(),
        })

# Bandwidth saved (Mbps) per 1000 stations updating at 10 Hz
N_STATIONS = 1000
F_HZ = 10
base_mbps = (4 * n_features * 8 * N_STATIONS * F_HZ) / 1e6
print(f"\nBaseline uplink (12 float32 @ 10 Hz x 1000 stations): {base_mbps:.1f} Mbps")
for r in results["models"]:
    new_mbps = (r["uplink_bytes_per_packet_float16"] * 8 * N_STATIONS * F_HZ) / 1e6
    r["uplink_mbps_per_1000_stations_10Hz"] = float(new_mbps)
    r["uplink_savings_pct"] = float(100 * (base_mbps - new_mbps) / base_mbps)

results["baseline_uplink_mbps_per_1000_stations_10Hz"] = float(base_mbps)

with open(f"{DATA}/semantic_results.json", "w") as f:
    json.dump(results, f, indent=2)
if isinstance(recon_dump, pd.DataFrame):
    recon_dump.to_csv(f"{DATA}/semantic_reconstruction.csv", index=False)
print(f"Saved -> semantic_results.json")
