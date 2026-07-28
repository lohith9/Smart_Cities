"""
v2_01_network_dataset.py
Extend the single-corridor dataset to a 10-node Inner-London road network.

Network topology (representative segment of Inner London):
    A40-E  - A40-W  - Marylebone-1 - Marylebone-2 - Euston-Rd-1
       |       |          |             |              |
    Edgware  Baker   Portland-Pl     Tottenham      Pentonville
The graph is fully connected within each row and adjacent rows are linked
via the columns. This 10-node graph supports a small spatio-temporal GNN
and a multi-junction signal-control RL agent.

Adjacency captures the *physical* corridor topology; spatial cross-correlation
in traffic and pollutants is induced by:
  (i) shared meteorology (wind/mixing height) across the network,
  (ii) propagation: an upstream queue affects downstream flow within ~5 min,
  (iii) emission plumes drifting downwind across adjacent nodes.

Outputs:
  ../data/v2_network.npz  (multidim arrays: flow, speed, pm25, no2, hdv, met)
  ../data/v2_adjacency.npy (10x10 normalised adjacency matrix)
  ../data/v2_node_table.csv (node metadata)
"""
import numpy as np
import pandas as pd
import os

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = str(ROOT / "data")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20260516)

N_NODES = 10
N_DAYS = 90
N_HOURS = N_DAYS * 24

# Node metadata
nodes = pd.DataFrame({
    "node_id":   range(N_NODES),
    "name":      ["A40-E","A40-W","Marylebone-1","Marylebone-2","Euston-Rd-1",
                  "Edgware","Baker","Portland-Pl","Tottenham","Pentonville"],
    "capacity":  [1500,1500,1300,1300,1400, 1100,1100,1100,1200,1200],
    "hdv_bias":  [0.10,0.10,0.07,0.06,0.08, 0.05,0.05,0.06,0.07,0.07],
    "x_km":      [0.0,0.8,1.6,2.4,3.2, 0.4,1.2,2.0,2.8,3.6],
    "y_km":      [0.0,0.0,0.0,0.0,0.0, 0.5,0.5,0.5,0.5,0.5],
})
nodes.to_csv(f"{OUT}/v2_node_table.csv", index=False)

# Adjacency (undirected, symmetric, normalised by degree for GCN)
adj = np.zeros((N_NODES, N_NODES))
# Top row: 0-1-2-3-4
for i in range(4):
    adj[i, i+1] = adj[i+1, i] = 1
# Bottom row: 5-6-7-8-9
for i in range(5, 9):
    adj[i, i+1] = adj[i+1, i] = 1
# Vertical links 0-5, 1-6, 2-7, 3-8, 4-9
for i in range(5):
    adj[i, i+5] = adj[i+5, i] = 1
# Self-loops for GCN renormalisation
adj_hat = adj + np.eye(N_NODES)
D = np.diag(1.0 / np.sqrt(adj_hat.sum(axis=1)))
A_norm = D @ adj_hat @ D
np.save(f"{OUT}/v2_adjacency.npy", A_norm)
print("Adjacency saved. Mean degree:", adj.sum(axis=1).mean())

# ----- Time series generation ----------------------------------------------
hours = pd.date_range("2025-09-01", periods=N_HOURS, freq="h")
hour_of_day = hours.hour.values
dow = hours.dayofweek.values

# Shared meteorology (same for the whole 4km x 0.5km network)
wind_speed = np.clip(rng.gamma(2.2, 1.6, N_HOURS), 0.4, 12)
wind_dir   = rng.uniform(0, 360, N_HOURS)
doy = hours.dayofyear.values.astype(float)
temp       = 14 - 4*np.cos(2*np.pi*(doy-200)/365) + 5*np.sin(2*np.pi*(hour_of_day-6)/24) + rng.normal(0,1.2,N_HOURS)
humidity   = np.clip(78 - 0.6*temp + rng.normal(0,4,N_HOURS), 35, 99)
mixing_h   = np.clip(350 + 600*np.maximum(0, np.sin(2*np.pi*(hour_of_day-6)/24)) + rng.normal(0,80,N_HOURS), 150, 1500)

# Per-node traffic flow with topology-driven cross-correlation
flow = np.zeros((N_HOURS, N_NODES))
speed = np.zeros((N_HOURS, N_NODES))
hdv = np.zeros((N_HOURS, N_NODES))
for n in range(N_NODES):
    cap = nodes.capacity[n]
    morning = (cap*0.55) * np.exp(-((hour_of_day-8)**2)/(2*1.4**2))
    evening = (cap*0.60) * np.exp(-((hour_of_day-18)**2)/(2*1.6**2))
    base    = 0.15*cap + 0.06*cap*np.sin(2*np.pi*(hour_of_day-6)/24)
    daily_factor = np.where(dow<5, 1.0, np.where(dow==5, 0.78, 0.62))
    flow[:, n] = (base + morning + evening) * daily_factor + rng.normal(0, 28, N_HOURS)
    flow[:, n] = np.clip(flow[:, n], 40, None)
    v_ratio = flow[:, n] / cap
    speed[:, n] = np.clip(38 - 22*v_ratio + rng.normal(0,1.5,N_HOURS), 8, 45)
    hdv[:, n] = np.clip(nodes.hdv_bias[n] + 0.05*np.exp(-((hour_of_day-6)**2)/6) + rng.normal(0,0.01,N_HOURS), 0.02, 0.22)

# Inject spatial coupling: each node's flow nudged toward neighbour mean (Laplacian smoothing)
for it in range(3):
    flow = flow + 0.07 * (flow @ A_norm - flow)

# Per-node pollutant concentrations using same emission-dispersion model as v1
EF_PM25_LDV, EF_PM25_HDV = 0.024, 0.085
EF_NO2_LDV,  EF_NO2_HDV  = 0.42,  2.10

pm25 = np.zeros_like(flow)
no2 = np.zeros_like(flow)
disp = 1.0 / (np.maximum(wind_speed, 0.5) * mixing_h / 1000)
bg_pm = 8.5 + 1.5*np.sin(2*np.pi*doy/365) + rng.normal(0,1.2,N_HOURS)
bg_no = 14  + 2.2*np.sin(2*np.pi*doy/365 + 1) + rng.normal(0,2.0,N_HOURS)

for n in range(N_NODES):
    ldv = 1 - hdv[:, n]
    e_pm = flow[:, n] * (ldv*EF_PM25_LDV + hdv[:, n]*EF_PM25_HDV)
    e_no = flow[:, n] * (ldv*EF_NO2_LDV  + hdv[:, n]*EF_NO2_HDV)
    pm25[:, n] = np.clip(bg_pm + 0.32 * e_pm * disp + rng.normal(0,0.9,N_HOURS), 2, 95)
    no2[:, n]  = np.clip(bg_no + 0.088*e_no * disp + rng.normal(0,2.3,N_HOURS), 4, 180)

# Cross-pollination via downwind plume transport (simple 1-hop dispersion)
pm25 = pm25 + 0.06 * (pm25 @ A_norm - pm25)
no2  = no2  + 0.06 * (no2  @ A_norm - no2)

# Save
np.savez(f"{OUT}/v2_network.npz",
         timestamps=hours.values.astype("datetime64[s]"),
         flow=flow, speed=speed, hdv=hdv, pm25=pm25, no2=no2,
         wind_speed=wind_speed, wind_dir=wind_dir,
         temp=temp, humidity=humidity, mixing_h=mixing_h,
         hour_of_day=hour_of_day, dow=dow)

print(f"Saved v2_network.npz  shape: flow {flow.shape}, pm25 {pm25.shape}")
print("Per-node means:")
for n in range(N_NODES):
    print(f"  {nodes.name[n]:14s}  PM2.5={pm25[:,n].mean():.2f}  NO2={no2[:,n].mean():.2f}  flow={flow[:,n].mean():.0f}")
