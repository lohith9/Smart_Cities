"""
05_compute_mape.py
Adds MAPE to the reported test-set metrics, in response to the Academic Editor's
request that accuracy be expressed in the units of each target as well as in
normalised form.

This script does NOT alter the study. It reuses the identical dataset, feature
set, contiguous 70/15/15 split, random seed and hyperparameters of
02_train_ml_models.py, and re-verifies R2/RMSE/MAE against the stored
ml_results.json before reporting MAPE. If the re-check fails, it aborts rather
than emitting numbers that do not correspond to the published run.

Output: ../data/ml_results_with_mape.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import xgboost as xgb

RNG = 20260516                      # identical to 02_train_ml_models.py
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

df = pd.read_csv(DATA / "london_corridor.csv", parse_dates=["timestamp"])

# --- Feature engineering (identical to 02_train_ml_models.py) ---
df["hour_sin"] = np.sin(2 * np.pi * df.hour / 24)
df["hour_cos"] = np.cos(2 * np.pi * df.hour / 24)
df["dow_sin"] = np.sin(2 * np.pi * df.dow / 7)
df["dow_cos"] = np.cos(2 * np.pi * df.dow / 7)
for col in ["traffic_flow_vph", "pm25_ugm3", "no2_ugm3", "mean_speed_kmh"]:
    df[f"{col}_lag1"] = df[col].shift(1)
df = df.dropna().reset_index(drop=True)

base_features = ["hour", "dow", "is_weekend", "month",
                 "hour_sin", "hour_cos", "dow_sin", "dow_cos",
                 "wind_speed_ms", "wind_dir_deg", "temp_c",
                 "humidity_pct", "mixing_height_m"]

target_specs = {
    "traffic_flow_vph": base_features + ["traffic_flow_vph_lag1", "mean_speed_kmh_lag1"],
    "pm25_ugm3":        base_features + ["traffic_flow_vph", "hdv_fraction",
                                         "pm25_ugm3_lag1", "no2_ugm3_lag1"],
    "no2_ugm3":         base_features + ["traffic_flow_vph", "hdv_fraction",
                                         "no2_ugm3_lag1", "pm25_ugm3_lag1"],
}

n = len(df)
i_tr, i_va = int(0.70 * n), int(0.85 * n)
train, test = df.iloc[:i_tr], df.iloc[i_va:]


def mape(y_true, y_pred):
    """Mean absolute percentage error, guarding against division by zero."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) > 1e-9
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def build(name):
    if name == "LinearRegression":
        return LinearRegression()
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=200, max_depth=18,
                                     min_samples_leaf=2, n_jobs=-1,
                                     random_state=RNG)
    return xgb.XGBRegressor(n_estimators=400, max_depth=6, learning_rate=0.05,
                            subsample=0.85, colsample_bytree=0.85, n_jobs=1,
                            random_state=RNG, verbosity=0)


published = json.loads((DATA / "ml_results.json").read_text())

out, mismatches = {}, []
TOL = 5e-3                                   # tolerance on reproduction check

for target, feats in target_specs.items():
    Xtr, ytr = train[feats].values, train[target].values
    Xte, yte = test[feats].values, test[target].values
    rows = []
    for entry in published[target]:
        name = entry["model"]
        model = build(name).fit(Xtr, ytr)
        pred = model.predict(Xte)
        r2 = float(r2_score(yte, pred))
        rmse = float(np.sqrt(mean_squared_error(yte, pred)))
        mae = float(mean_absolute_error(yte, pred))

        for key, got in (("r2", r2), ("rmse", rmse), ("mae", mae)):
            ref = entry[key]
            rel = abs(got - ref) / max(abs(ref), 1e-9)
            if rel > TOL:
                mismatches.append(f"{target}/{name}/{key}: published={ref:.6f} recomputed={got:.6f}")

        rows.append({"model": name, "r2": r2, "rmse": rmse, "mae": mae,
                     "mape_pct": mape(yte, pred)})
    out[target] = rows

if mismatches:
    print("ABORT - recomputed metrics do not match the published run:")
    for m in mismatches:
        print("   ", m)
    raise SystemExit(1)

(DATA / "ml_results_with_mape.json").write_text(json.dumps(out, indent=2))

print("Reproduction check passed: R2/RMSE/MAE match ml_results.json within "
      f"{TOL:.1%} for all 9 model-target pairs.\n")
hdr = f"{'target':18s} {'model':17s} {'R2':>7s} {'RMSE':>9s} {'MAE':>9s} {'MAPE %':>8s}"
print(hdr); print("-" * len(hdr))
for target, rows in out.items():
    for r in rows:
        print(f"{target:18s} {r['model']:17s} {r['r2']:7.3f} {r['rmse']:9.3f} "
              f"{r['mae']:9.3f} {r['mape_pct']:8.2f}")
print("\nSaved: data/ml_results_with_mape.json")
