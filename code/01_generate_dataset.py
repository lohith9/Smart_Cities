"""
01_generate_dataset.py
Build a calibrated synthetic Inner-London traffic + air quality dataset for the
digital twin case study.

Calibration anchors (published London measurements; see chapter Sections 4.1 and 5.1):
  - PM2.5 annual mean, Inner London 2018-2019: ~11-13 ug/m3
    (GLA, Air Quality in London 2016-2024, Table 9. NOTE: an earlier version of
    this header dated the band to 2023 and attributed it to Marylebone Road.
    Both were wrong: the 2023 London annual means are 7.8-10.0 ug/m3, and the
    site attribution was never verified.)
  - NO2 annual mean, inner-London roadside 2018-2019: ~35-50 ug/m3
    (GLA, Air Quality in London 2016-2024, Table 7. Central London roadside is
    substantially higher, 63-93 ug/m3 over 2016-2019.)
  - Diurnal traffic pattern peaks 07:30-09:30 and 17:00-19:00 (TfL flow data)
  - Average inner-London car flow on a major corridor: ~600-900 veh/h peak,
    150-300 veh/h off-peak
  - Wind speed mean: 3.5 m/s, RH ~75% (Heathrow met)
The generated CSV is statistically realistic but is NOT a substitute for live
LAQN/TfL feeds. The chapter's reproducibility note explains how to swap in real
data with no code changes.
"""

import numpy as np
import pandas as pd
import os

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
os.makedirs(DATA, exist_ok=True)
rng = np.random.default_rng(seed=20260516)  # fixed seed for reproducibility

N_DAYS = 90  # ~3 months of hourly data -> 2160 records
hours = pd.date_range("2025-09-01 00:00", periods=N_DAYS * 24, freq="h")

def diurnal_traffic(h):
    """Vehicles per hour on a major Inner-London corridor."""
    # Two-peak diurnal pattern
    morning = 750 * np.exp(-((h - 8) ** 2) / (2 * 1.4 ** 2))
    evening = 820 * np.exp(-((h - 18) ** 2) / (2 * 1.6 ** 2))
    base = 220 + 80 * np.sin(2 * np.pi * (h - 6) / 24)
    return np.maximum(base + morning + evening, 60)

def weekday_factor(dow):
    # Mon-Fri full, Sat 0.78, Sun 0.62 (TfL flow surveys)
    return np.where(dow < 5, 1.0, np.where(dow == 5, 0.78, 0.62))

# --- Traffic ---
df = pd.DataFrame({"timestamp": hours})
df["hour"] = df.timestamp.dt.hour
df["dow"] = df.timestamp.dt.dayofweek
df["is_weekend"] = (df.dow >= 5).astype(int)
df["month"] = df.timestamp.dt.month

base_flow = diurnal_traffic(df.hour.values) * weekday_factor(df.dow.values)
df["traffic_flow_vph"] = np.clip(base_flow + rng.normal(0, 35, len(df)), 40, None).round()

# Speed (km/h) - inversely related to congestion
capacity = 1400
v_ratio = df.traffic_flow_vph / capacity
df["mean_speed_kmh"] = (38 - 22 * v_ratio + rng.normal(0, 1.5, len(df))).clip(8, 45).round(1)
# HDV fraction (heavy duty vehicles) - elevated in morning freight window
df["hdv_fraction"] = (0.08 + 0.06 * np.exp(-((df.hour - 6) ** 2) / 6) +
                      rng.normal(0, 0.01, len(df))).clip(0.02, 0.22).round(3)

# --- Meteorology ---
# Wind speed (m/s) - lognormal-ish
df["wind_speed_ms"] = rng.gamma(shape=2.2, scale=1.6, size=len(df)).clip(0.4, 12).round(2)
# Wind direction (degrees)
df["wind_dir_deg"] = rng.uniform(0, 360, len(df)).round(0)
# Temperature - seasonal (Sep-Nov in this sample) with diurnal
season_t = 14 - 4 * np.cos(2 * np.pi * (df.timestamp.dt.dayofyear - 200) / 365)
diurnal_t = 5 * np.sin(2 * np.pi * (df.hour - 6) / 24)
df["temp_c"] = (season_t + diurnal_t + rng.normal(0, 1.2, len(df))).round(1)
df["humidity_pct"] = (78 - 0.6 * df.temp_c + rng.normal(0, 4, len(df))).clip(35, 99).round(0)
# Mixing height (m) - lower at night, higher daytime; key for dispersion
df["mixing_height_m"] = (350 + 600 * np.maximum(0, np.sin(2 * np.pi * (df.hour - 6) / 24))
                          + rng.normal(0, 80, len(df))).clip(150, 1500).round(0)

# --- Pollutant generation (calibrated emission-based model) ---
# Emission factors (g/km), based on COPERT/EEA inventory averages for Inner London fleet 2023:
EF_PM25_LDV = 0.024  # g/km for light-duty vehicles (PM2.5)
EF_PM25_HDV = 0.085  # g/km for heavy-duty vehicles
EF_NO2_LDV  = 0.42   # g/km
EF_NO2_HDV  = 2.10   # g/km

ldv_share = 1 - df.hdv_fraction
# Emission rate (g/h) per km of corridor
emiss_pm25 = df.traffic_flow_vph * (ldv_share * EF_PM25_LDV + df.hdv_fraction * EF_PM25_HDV)
emiss_no2  = df.traffic_flow_vph * (ldv_share * EF_NO2_LDV  + df.hdv_fraction * EF_NO2_HDV)

# Simplified dispersion: concentration ~ emission / (wind * mixing_height)
disp = 1.0 / (np.maximum(df.wind_speed_ms, 0.5) * df.mixing_height_m / 1000)

# Background levels (regional, non-traffic)
bg_pm25 = 8.5 + 1.5 * np.sin(2 * np.pi * df.timestamp.dt.dayofyear / 365) + rng.normal(0, 1.2, len(df))
bg_no2  = 14 + 2.2 * np.sin(2 * np.pi * df.timestamp.dt.dayofyear / 365 + 1) + rng.normal(0, 2.0, len(df))

# Final concentration with calibrated scaling so means land in published range
df["pm25_ugm3"] = (bg_pm25 + 0.32 * emiss_pm25 * disp + rng.normal(0, 0.9, len(df))).clip(2, 95).round(2)
df["no2_ugm3"]  = (bg_no2  + 0.088 * emiss_no2  * disp + rng.normal(0, 2.3, len(df))).clip(4, 180).round(2)

# Sanity check vs Inner London published means
print(f"Records: {len(df)}")
print(f"PM2.5 mean = {df.pm25_ugm3.mean():.2f} ug/m3 (target ~11-13)")
print(f"NO2  mean = {df.no2_ugm3.mean():.2f} ug/m3 (target ~30-50)")
print(f"Traffic flow peak hour mean = {df[df.hour.isin([8,17,18])].traffic_flow_vph.mean():.0f} veh/h")
print(f"Off-peak (2-5am) mean = {df[df.hour.isin([2,3,4,5])].traffic_flow_vph.mean():.0f} veh/h")

df.to_csv(f"{DATA}/london_corridor.csv", index=False)
print("Saved -> ../data/london_corridor.csv")