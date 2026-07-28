"""
v2_06_health.py
Health-endpoint coupling: convert scenario AQ deltas into avoided premature
deaths and DALYs per million population.

Methodology:
  - PM2.5 -> all-cause mortality: GBD 2019 / Burnett et al. (PNAS 2018)
    GEMM model. We use a linearised approximation valid in 5-20 ug/m^3 range:
        RR(c) = 1 + alpha * (c - c0)
    with alpha (relative-risk per ug/m3) calibrated to GBD 2019 IER.
  - NO2 -> mortality: HRAPIE (WHO 2013) recommends RR = 1.039 per
    10 ug/m3 increment in NO2 (all-cause mortality, adults 30+).
  - Baseline mortality rate: ~9 per 1000 (population averaged for the UK).
  - DALYs: from GBD 2019, 1 premature death from ambient air pollution
    approximately = 16 years of life lost (YLL); we add a 0.15 multiplier
    for years lived with disability (YLD) from cardio-respiratory disease.
"""
import json
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

# Inputs: scenario mean AQ are READ from the pipeline output of 03_run_scenarios.py
_SHORT = ["S0 Baseline", "S1 AI+5G", "S2 AI+6G", "S3 AI+6G+Demand"]
with open(DATA / "scenarios.json") as _f:
    _scen_raw = json.load(_f)
SCEN = [
    {"name": _SHORT[i] if i < len(_SHORT) else _scen_raw[i]["scenario"],
     "pm25": float(_scen_raw[i]["mean_pm25_ugm3"]),
     "no2":  float(_scen_raw[i]["mean_no2_ugm3"])}
    for i in range(len(_scen_raw))
]

# Counter-factual minimum exposure (cf MRL): 5 ug/m3 (WHO 2021 AQG)
PM25_CF = 5.0
NO2_CF  = 5.0

# Relative-risk parameters
ALPHA_PM25 = 0.008   # per ug/m3 (linearised GBD IER, all-cause mort, urban adults)
RR_NO2_PER_10 = 1.039  # HRAPIE
YLL_PER_DEATH = 16.0
YLD_TO_YLL_RATIO = 0.15

# Baseline mortality rate per 100,000 person-years (UK all-cause, adults 30+)
BASE_MORT = 870.0
POP = 1_000_000   # per million

def attributable_fraction_pm25(c):
    rr = 1 + ALPHA_PM25 * max(c - PM25_CF, 0.0)
    return (rr - 1) / rr

def attributable_fraction_no2(c):
    rr_per_unit = np.power(RR_NO2_PER_10, max(c - NO2_CF, 0.0) / 10.0)
    return (rr_per_unit - 1) / rr_per_unit

# Avoid double-count: use 75% of NO2 effect when combined with PM2.5
NO2_WEIGHT_WHEN_COMBINED = 0.75

results = []
for s in SCEN:
    AF_pm = attributable_fraction_pm25(s["pm25"])
    AF_no = attributable_fraction_no2(s["no2"]) * NO2_WEIGHT_WHEN_COMBINED
    # Approximate combined AF (independent risks)
    AF_combined = 1 - (1 - AF_pm) * (1 - AF_no)
    deaths_per_year_per_M = BASE_MORT / 100000 * POP * AF_combined
    daly_per_year_per_M = deaths_per_year_per_M * YLL_PER_DEATH * (1 + YLD_TO_YLL_RATIO)
    results.append({
        "scenario": s["name"],
        "pm25": s["pm25"],
        "no2":  s["no2"],
        "AF_pm25":     float(AF_pm),
        "AF_no2_75pct": float(AF_no),
        "AF_combined": float(AF_combined),
        "premature_deaths_per_year_per_million": float(deaths_per_year_per_M),
        "DALYs_per_year_per_million": float(daly_per_year_per_M),
    })

# Compute avoided deaths/DALYs vs baseline
base = results[0]
for r in results:
    r["avoided_deaths_per_year_per_million"] = float(base["premature_deaths_per_year_per_million"] - r["premature_deaths_per_year_per_million"])
    r["avoided_DALYs_per_year_per_million"]   = float(base["DALYs_per_year_per_million"] - r["DALYs_per_year_per_million"])

print(f"\n=== Health-endpoint coupling (per million population) ===")
print(f"{'Scenario':24s} {'PM2.5':>6s} {'NO2':>6s} {'Deaths/yr':>10s} {'DALYs/yr':>10s} {'Avoid_deaths':>14s} {'Avoid_DALYs':>13s}")
for r in results:
    print(f"  {r['scenario']:22s} {r['pm25']:6.2f} {r['no2']:6.2f} "
          f"{r['premature_deaths_per_year_per_million']:10.1f} "
          f"{r['DALYs_per_year_per_million']:10.1f} "
          f"{r['avoided_deaths_per_year_per_million']:14.1f} "
          f"{r['avoided_DALYs_per_year_per_million']:13.1f}")

# Inner London has ~3.5M residents -> scale up
INNER_LONDON_POP = 3_500_000
print(f"\nScaling to Inner London ({INNER_LONDON_POP/1e6:.1f}M residents):")
for r in results[1:]:
    abs_deaths = r["avoided_deaths_per_year_per_million"] * INNER_LONDON_POP / 1e6
    abs_dalys  = r["avoided_DALYs_per_year_per_million"]  * INNER_LONDON_POP / 1e6
    r["avoided_deaths_inner_london"] = float(abs_deaths)
    r["avoided_DALYs_inner_london"]  = float(abs_dalys)
    print(f"  {r['scenario']:22s} avoided deaths/yr = {abs_deaths:6.0f}, avoided DALYs/yr = {abs_dalys:7.0f}")

with open(DATA / "health_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved -> health_results.json")
