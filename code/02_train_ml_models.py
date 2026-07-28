"""
02_train_ml_models.py
Train AI predictors for traffic flow, PM2.5, and NO2 on the calibrated
Inner-London dataset.

Models compared:
  - Random Forest (baseline, fast, interpretable)
  - XGBoost (gradient boosting, typically strongest on tabular AQ data)
  - Linear regression (as a low-baseline reference)

Time-series split: 70% train / 15% val / 15% test, contiguous in time
(no shuffle) to avoid temporal leakage.

Outputs:
  ../data/ml_results.json   summary metrics
  ../data/predictions.csv   per-row test predictions for plotting
  ../data/feature_importance.csv
"""

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import xgboost as xgb
import time

RNG = 20260516
from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
df = pd.read_csv(f"{DATA}/london_corridor.csv", parse_dates=["timestamp"])

# --- Feature engineering ---
df["hour_sin"] = np.sin(2 * np.pi * df.hour / 24)
df["hour_cos"] = np.cos(2 * np.pi * df.hour / 24)
df["dow_sin"]  = np.sin(2 * np.pi * df.dow / 7)
df["dow_cos"]  = np.cos(2 * np.pi * df.dow / 7)
# Lag-1 traffic and AQ (1-hour lag) - simulates real-time previous-step data
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

# Contiguous time split
n = len(df)
i_tr = int(0.70 * n)
i_va = int(0.85 * n)
train, val, test = df.iloc[:i_tr], df.iloc[i_tr:i_va], df.iloc[i_va:]
print(f"Train={len(train)}, Val={len(val)}, Test={len(test)}")

def fit_eval(model, Xtr, ytr, Xte, yte, name):
    t0 = time.time()
    model.fit(Xtr, ytr)
    t_fit = time.time() - t0
    t0 = time.time()
    pred = model.predict(Xte)
    t_pred = time.time() - t0
    return {
        "model": name,
        "r2":    float(r2_score(yte, pred)),
        "rmse":  float(np.sqrt(mean_squared_error(yte, pred))),
        "mae":   float(mean_absolute_error(yte, pred)),
        "fit_time_s":  float(t_fit),
        "pred_time_ms": float(1000 * t_pred / len(yte)),
    }, pred

results = {}
predictions = {"timestamp": test.timestamp.values}
fi_rows = []

for target, feats in target_specs.items():
    Xtr, ytr = train[feats].values, train[target].values
    Xte, yte = test[feats].values,  test[target].values
    target_results = []

    # Linear baseline
    r, pred = fit_eval(LinearRegression(), Xtr, ytr, Xte, yte, "LinearRegression")
    target_results.append(r)

    # Random Forest
    rf = RandomForestRegressor(n_estimators=200, max_depth=18,
                                min_samples_leaf=2, n_jobs=-1, random_state=RNG)
    r, pred_rf = fit_eval(rf, Xtr, ytr, Xte, yte, "RandomForest")
    target_results.append(r)

    # XGBoost
    xgbr = xgb.XGBRegressor(n_estimators=400, max_depth=6,
                             learning_rate=0.05, subsample=0.85,
                             colsample_bytree=0.85, n_jobs=1,
                             random_state=RNG, verbosity=0)
    r, pred_xgb = fit_eval(xgbr, Xtr, ytr, Xte, yte, "XGBoost")
    target_results.append(r)

    results[target] = target_results
    predictions[f"{target}_true"]  = yte
    predictions[f"{target}_rf"]    = pred_rf
    predictions[f"{target}_xgb"]   = pred_xgb

    # Feature importance (XGBoost)
    fi = pd.DataFrame({"target": target,
                       "feature": feats,
                       "importance": xgbr.feature_importances_}
                     ).sort_values("importance", ascending=False)
    fi_rows.append(fi)
    print(f"\n=== {target} ===")
    for r_ in target_results:
        print(f"  {r_['model']:18s}  R2={r_['r2']:.3f}  RMSE={r_['rmse']:.3f}  "
              f"MAE={r_['mae']:.3f}  pred={r_['pred_time_ms']:.3f} ms/sample")

with open(f"{DATA}/ml_results.json", "w") as f:
    json.dump(results, f, indent=2)
pd.DataFrame(predictions).to_csv(f"{DATA}/predictions.csv", index=False)
pd.concat(fi_rows).to_csv(f"{DATA}/feature_importance.csv", index=False)
print("\nSaved: ml_results.json, predictions.csv, feature_importance.csv")
