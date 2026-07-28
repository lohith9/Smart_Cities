"""
03_run_scenarios.py
Compute four operational scenarios for the case study:
  S0 - BASELINE: fixed-time signals, no AI control, 4G/LTE backhaul (~50 ms RTT)
  S1 - AI-OPT (5G):   AI-optimized signal timing with 5G backhaul (~10 ms RTT)
  S2 - AI-OPT (6G):   AI-optimized + 6G ultra-low latency (~1 ms RTT,
                       distributed edge control updating at 10 Hz)
  S3 - AI-OPT (6G) + DEMAND MGMT: same + congestion-aware soft demand reduction
                       (-15% peak), e.g. dynamic pricing / route advisories.

Scenario parameters are ASSUMED INPUTS, not derived quantities. Their
magnitudes are of the order reported for adaptive signal control in the
review literature (see chapter reference [34], Eom & Kim 2020, European
Transport Research Review 12:50), but this implementation does not derive
them from any specific source:
  - adaptive control: speed uplift assumption
  - sub-second update loops: the extra_delay_red term below
  - coupled demand management: peak flow multiplier plus speed uplift
An earlier version of this header attributed these magnitudes to a 2024
meta-analysis that could not be verified in Crossref and has been removed.
See chapter Section 5.2, which discloses every parameter used here.

Pollutant response uses the same dispersion/emission model the dataset was
calibrated to, ensuring internal consistency.
"""

import json
import numpy as np
import pandas as pd

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
df = pd.read_csv(f"{DATA}/london_corridor.csv", parse_dates=["timestamp"])
EF_PM25_LDV, EF_PM25_HDV = 0.024, 0.085
EF_NO2_LDV,  EF_NO2_HDV  = 0.42,  2.10

def scenario(name, *, flow_mult, speed_mult, ctrl_latency_ms, ctrl_hz,
             extra_delay_red=0.0):
    flow  = df.traffic_flow_vph * flow_mult
    spd   = (df.mean_speed_kmh * speed_mult).clip(8, 50)
    # Travel time per km
    tt_min = 60.0 / spd
    # Delay vs free-flow (40 km/h)
    free = 60.0 / 40.0
    delay = (tt_min - free).clip(lower=0)
    delay = delay * (1 - extra_delay_red)
    # Re-compute pollutant via same dispersion/emission engine
    ldv = 1 - df.hdv_fraction
    e_pm = flow * (ldv * EF_PM25_LDV + df.hdv_fraction * EF_PM25_HDV)
    e_no = flow * (ldv * EF_NO2_LDV  + df.hdv_fraction * EF_NO2_HDV)
    disp = 1.0 / (np.maximum(df.wind_speed_ms, 0.5) * df.mixing_height_m / 1000)
    # Slower speed -> more idling -> +12% emission per 25% speed drop (empirical)
    # Smoother flow at higher speeds -> less stop-and-go -> lower emission factor.
    # COPERT-style: emissions scale ~ 1/speed at low urban speeds.
    idle_penalty = (df.mean_speed_kmh / np.maximum(spd, 5)).clip(0.78, 1.5)
    bg_pm, bg_no = 8.5, 14
    pm25 = bg_pm + 0.32  * e_pm * disp * idle_penalty
    no2  = bg_no + 0.088 * e_no * disp * idle_penalty
    return {
        "scenario": name,
        "mean_flow_vph":   float(flow.mean()),
        "peak_flow_vph":   float(flow[df.hour.isin([8,17,18])].mean()),
        "mean_speed_kmh":  float(spd.mean()),
        "mean_delay_min_per_km": float(delay.mean()),
        "peak_delay_min_per_km": float(delay[df.hour.isin([8,17,18])].mean()),
        "mean_pm25_ugm3":  float(pm25.mean()),
        "mean_no2_ugm3":   float(no2.mean()),
        "peak_pm25_ugm3":  float(pm25[df.hour.isin([8,17,18])].mean()),
        "peak_no2_ugm3":   float(no2[df.hour.isin([8,17,18])].mean()),
        "no2_exceedance_pct":  float((no2 > 40).mean() * 100),
        "ctrl_latency_ms": ctrl_latency_ms,
        "ctrl_hz":         ctrl_hz,
    }

# Baseline: dataset values, fixed-time, 4G ~50 ms loop, signal plan ~once/5min (0.0033 Hz)
s0 = scenario("S0 Baseline (Fixed-time, 4G)",
              flow_mult=1.00, speed_mult=1.00,
              ctrl_latency_ms=50.0, ctrl_hz=0.0033)

# AI-OPT with 5G: speed +6%, ~1Hz adaptive plans
s1 = scenario("S1 AI-Adaptive (5G)",
              flow_mult=1.00, speed_mult=1.06,
              ctrl_latency_ms=10.0, ctrl_hz=1.0,
              extra_delay_red=0.0)

# AI-OPT with 6G: speed +9%, 10Hz edge loops, sub-ms RTT
s2 = scenario("S2 AI-Adaptive (6G)",
              flow_mult=1.00, speed_mult=1.09,
              ctrl_latency_ms=0.8, ctrl_hz=10.0,
              extra_delay_red=0.03)

# AI + demand mgmt: -15% peak demand, +12% speed, dynamic routing
peak_mask = df.hour.isin([7,8,9,17,18,19]).values
flow_mult_arr = np.where(peak_mask, 0.85, 1.0)
def scenario_arr(name, flow_mult_arr, speed_mult, ctrl_latency_ms, ctrl_hz, extra_red):
    flow  = df.traffic_flow_vph * flow_mult_arr
    spd   = (df.mean_speed_kmh * speed_mult).clip(8, 50)
    tt = 60.0 / spd
    free = 60.0 / 40.0
    delay = (tt - free).clip(lower=0) * (1 - extra_red)
    ldv = 1 - df.hdv_fraction
    e_pm = flow * (ldv * EF_PM25_LDV + df.hdv_fraction * EF_PM25_HDV)
    e_no = flow * (ldv * EF_NO2_LDV  + df.hdv_fraction * EF_NO2_HDV)
    disp = 1.0 / (np.maximum(df.wind_speed_ms, 0.5) * df.mixing_height_m / 1000)
    idle = (df.mean_speed_kmh / np.maximum(spd, 5)).clip(0.78, 1.5)
    pm25 = 8.5 + 0.32  * e_pm * disp * idle
    no2  = 14  + 0.088 * e_no * disp * idle
    return {
        "scenario": name,
        "mean_flow_vph":   float(flow.mean()),
        "peak_flow_vph":   float(flow[df.hour.isin([8,17,18])].mean()),
        "mean_speed_kmh":  float(spd.mean()),
        "mean_delay_min_per_km": float(delay.mean()),
        "peak_delay_min_per_km": float(delay[df.hour.isin([8,17,18])].mean()),
        "mean_pm25_ugm3":  float(pm25.mean()),
        "mean_no2_ugm3":   float(no2.mean()),
        "peak_pm25_ugm3":  float(pm25[df.hour.isin([8,17,18])].mean()),
        "peak_no2_ugm3":   float(no2[df.hour.isin([8,17,18])].mean()),
        "no2_exceedance_pct":  float((no2 > 40).mean() * 100),
        "ctrl_latency_ms": ctrl_latency_ms,
        "ctrl_hz":         ctrl_hz,
    }
s3 = scenario_arr("S3 AI + 6G + Demand-Mgmt", flow_mult_arr,
                  speed_mult=1.12, ctrl_latency_ms=0.8, ctrl_hz=10.0,
                  extra_red=0.05)

rows = [s0, s1, s2, s3]
# Compute % changes vs baseline
for r in rows:
    r["delay_red_pct"] = 100 * (s0["mean_delay_min_per_km"] - r["mean_delay_min_per_km"]) / s0["mean_delay_min_per_km"]
    r["pm25_red_pct"]  = 100 * (s0["mean_pm25_ugm3"] - r["mean_pm25_ugm3"]) / s0["mean_pm25_ugm3"]
    r["no2_red_pct"]   = 100 * (s0["mean_no2_ugm3"]  - r["mean_no2_ugm3"])  / s0["mean_no2_ugm3"]

# Compute control update miss rate: probability the underlying state changes
# faster than the control loop can react.
# State volatility (per-second flow change) approximated from minute-to-minute std
flow_change_per_sec = np.std(np.diff(df.traffic_flow_vph.values)) / 3600
print(f"State volatility (veh/s std): {flow_change_per_sec:.4f}")
for r in rows:
    period_s = 1.0 / r["ctrl_hz"]
    # Miss rate ~ fraction of state change uncaptured within control loop
    r["est_state_lag_veh"] = period_s * flow_change_per_sec
    r["est_state_lag_pct"] = 100 * period_s * flow_change_per_sec / df.traffic_flow_vph.mean()

results_df = pd.DataFrame(rows)
results_df.to_csv(f"{DATA}/scenarios.csv", index=False)
with open(f"{DATA}/scenarios.json", "w") as f:
    json.dump(rows, f, indent=2)

# Pretty print
print("\n=== Scenario comparison ===")
cols = ["scenario", "mean_flow_vph", "mean_speed_kmh",
        "mean_delay_min_per_km", "mean_pm25_ugm3", "mean_no2_ugm3",
        "no2_exceedance_pct",
        "ctrl_latency_ms", "ctrl_hz",
        "delay_red_pct", "pm25_red_pct", "no2_red_pct"]
print(results_df[cols].to_string(index=False, float_format=lambda v: f"{v:.2f}"))
print("\nSaved -> ../data/scenarios.csv  ../data/scenarios.json")
