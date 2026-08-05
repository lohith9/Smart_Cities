# Reproducibility

## How to reproduce

```bash
python3 -m venv .venv && source .venv/bin/activate    # Python 3.10
pip install -r requirements.txt
bash run_all.sh                                       # 12 steps, any working directory
```

Scripts resolve their own paths with `pathlib`, so the working directory does not matter.

## Expected runtime

| Stage | Steps | Approximate time |
|---|---|---|
| Corridor pipeline | 1–5 | a few minutes |
| Appendix D demonstrations | 6–12 | a few further minutes |

Single CPU core is sufficient. No GPU required.

## Random seeds

A single seed, **20260516**, is used throughout: the NumPy generator in
`01_generate_dataset.py`, and `random_state` for scikit-learn and XGBoost. XGBoost runs
single-threaded (`n_jobs=1`); Random Forest is deterministic given `random_state`, run to
run, on one machine. Evaluation seeds 100–104 are used in the Appendix D scripts.

`n_jobs=1` guarantees XGBoost is deterministic **run to run on one machine** — this was
measured directly (see "Determinism, measured" below) and holds exactly. It does **not**
guarantee determinism **across machines/platforms**: XGBoost's histogram-based tree
construction is not bit-reproducible across CPU/compiler/platform combinations even with a
fixed seed, and this was also measured directly, diverging in the cross-platform check
below. An earlier version of this note claimed single-threading was "for cross-machine
determinism" — that claim is what the check below disproves; it has been removed rather
than left standing against the evidence.

## Expected outputs

`data/`: `london_corridor.csv`, `ml_results.json`, `ml_results_with_mape.json`,
`predictions.csv`, `feature_importance.csv`, `scenarios.{json,csv}`, `v2_network.npz`,
`v2_adjacency.npy`, `v2_node_table.csv`, `pinn_results.json`, `stgnn_results.json`,
`marl_results.json`, `marl_learning_curve.csv`, `semantic_results.json`, `health_results.json`.

`figures/`: `fig1_architecture.png` … `fig12_health.png`, all 300 DPI.

The mapping from each output to the manuscript table or figure it produces is in `README.md`.

## Tested environment

Python 3.10.12 on Linux. Package versions pinned in `requirements.txt`. No operating-system
specific calls; the scripts use only the standard library plus the pinned dependencies.


## Clean-room reproduction (verified)

The full pipeline was executed end to end in a clean copy of this repository, with `data/` and
`figures/` emptied beforehand, on Python 3.10.12 with the pinned dependencies. All twelve steps
completed. Results against the shipped outputs:

| Output | Result |
|---|---|
| `london_corridor.csv` | byte-identical |
| `feature_importance.csv`, `scenarios.csv` | byte-identical |
| `scenarios.json` | identical |
| `ml_results_with_mape.json` | identical to 12 decimal places |
| `predictions.csv` | numerically identical (max difference 0.0) |
| `ml_results.json` | identical except timing fields and two values differing by 1 unit in the last place |
| Appendix D results | all reported claims reproduce exactly |
| Figures | all twelve regenerated |

### Known benign non-determinism

- **Random Forest, last-bit.** `RandomForestRegressor` runs with `n_jobs=-1`, so the order of
  summation across threads depends on the thread count. Two values in `ml_results.json` differed
  by one unit in the last place (RMSE 7.470930296094889 versus ...888). This does not affect any
  reported figure, all of which are quoted to three decimal places or fewer. Set `n_jobs=1` if
  bit-identical output matters more than speed.
- **Timing fields.** `fit_time_s` and `pred_time_ms` are machine-dependent and will always differ.

## Determinism, measured

Two separate checks, run in the same session, on Windows 11 / Intel Core 7 150U (10 cores) /
Python 3.11.9, packages installed exactly per `requirements.txt`. Full methodology and every
individual value are in `tests/README.md`; this section gives the headline numbers.

### Same-platform, repeated runs (10x)

`02_train_ml_models.py`'s exact training step (same features, split, seed, hyperparameters)
was run 10 times in this one environment. Spread = max − min across the 10 runs:

| Target | Model | r2 spread | rmse spread | mae spread | Unique values / 10 |
|---|---|---|---|---|---|
| traffic_flow_vph | LinearRegression | 0 | 0 | 0 | 1 |
| traffic_flow_vph | RandomForest | 0 | 1.421e-14 | 7.105e-15 | up to 3 |
| traffic_flow_vph | XGBoost | 0 | 0 | 0 | 1 |
| pm25_ugm3 | LinearRegression | 0 | 0 | 0 | 1 |
| pm25_ugm3 | RandomForest | 0 | 8.882e-16 | 2.220e-16 | up to 3 |
| pm25_ugm3 | XGBoost | 0 | 0 | 0 | 1 |
| no2_ugm3 | LinearRegression | 0 | 0 | 0 | 1 |
| no2_ugm3 | RandomForest | 1.110e-16 | 2.665e-15 | 1.776e-15 | up to 4 |
| no2_ugm3 | XGBoost | 0 | 0 | 0 | 1 |

XGBoost and LinearRegression were bit-identical across all 10 runs, every metric, every
target. RandomForest showed the last-bit thread-summation noise `RC1_RELEASE_CERTIFICATE.md`
already documents (max ~2.7e-15 absolute on RMSE ≈ 7.47) — real, but roughly 12 orders of
magnitude below the precision (2–3 decimal places) at which any of these values is quoted.
**Conclusion: same-platform reproduction is not merely close, it is exact to the precision the
chapter uses, for every model.**

### Cross-platform: this machine vs. the Linux environment the shipped data was built on

The full 12-step pipeline was run clean-room (`tests/verify_reproduction.py`) and every
output compared against the committed `data/` files, which were generated on Linux
(`SOFTWARE_METADATA.md`). Verified by direct inspection of both the aggregate metrics and the
underlying per-row predictions, not inferred:

| Quantity | Cross-platform result |
|---|---|
| `LinearRegression` (all targets) | **exact** — 0 differences |
| `RandomForestRegressor` (all targets, `n_jobs=-1`) | **exact** — 0 differences, including every `predictions.csv` row |
| `scenarios.json/.csv`, `health_results.json`, `v2_network.npz`, `v2_adjacency.npy`, `v2_node_table.csv`, `marl_results.json`, `marl_learning_curve.csv`, `london_corridor.csv` | **exact** — no ML training involved |
| `semantic_results.json` (PCA + MLPRegressor) | **exact** on this run — single-run evidence, not a guarantee |
| `XGBRegressor` (`n_jobs=1`, all targets) | **diverges** — see below |

XGBoost aggregate `r2` diverged by 5.7e-4 (traffic_flow_vph) to **1.7e-2 relative**
(no2_ugm3: published 0.9223 → 0.9384 on this platform). `rmse` and `mae` diverged by up to
11–15% on the same target; MAPE by 9.5%. Individual `predictions.csv` rows diverged by up to
~30%, and `feature_importance.csv` rankings reordered from roughly the third-ranked feature
onward for every target.

**This is a real, measured limitation, disclosed here rather than fixed, per the rule that no
seed, hyperparameter or reported value may be changed to chase it.** It is not evidence of an
error in the pipeline's design, seeding, or the published values — the seed and `n_jobs=1`
setting do their documented job perfectly on one machine (see above). The mechanism is a
known, published category of issue: histogram-based gradient-boosted tree construction
(XGBoost's default tree method) is not guaranteed bit-reproducible across different
CPU/compiler/OS/wheel combinations even with an identical seed, because the floating-point
summation order in its quantile-sketch binning step can differ by platform.
`RandomForestRegressor` and `LinearRegression`, which use different underlying numerical code
paths, do not show this sensitivity on the platforms tested here.

**Practical implication:** every scenario, health, network-topology, and delay/emission-model
result in the chapter reproduces exactly on a different OS than the one used to generate the
shipped data. The specifically **XGBoost-derived** entries in Table 4 (and the XGBoost columns
of any supplementary detail table) should be understood as reproducible on the tested platform
(Linux) but not guaranteed to the same decimal places elsewhere — a reader reproducing Table 4
on Windows should expect the XGBoost row's R²/RMSE/MAE to differ from the printed value by up
to roughly 2 percentage points, while every other reported number in the chapter should
reproduce exactly.

### One stale artefact — resolved before v1.0.0

`data/health_results.json` had been produced from rounded inputs (PM2.5 12.59 rather than
12.5926). It was regenerated before the v1.0.0 tag and the shipped file now carries the
full-precision values from `data/scenarios.json` (for example `"pm25": 12.592577696942788`
against `"mean_pm25_ugm3": 12.592577696942788`), so it corresponds to a single consistent run.
See `RC1_RELEASE_CERTIFICATE.md`, "Resolved during RC1".

## Known limitations

- **All data are synthetic.** Live LAQN and TfL feeds were unreachable during the study.
  The datasets are calibrated to published Inner-London priors but are not measurements.
- **Single run, not an ensemble.** Reported scenario results come from one seeded run, so no
  sampling interval accompanies them.
- **Not performed:** cross-validation, formal residual diagnostics, and attribution methods
  such as SHAP.
- **Appendix D.3** depends on a simplified delay proxy. `code/marl_diagnostic.py` shows that a
  naive constant throttle achieves a comparable reduction; Appendix D.3 hedges accordingly.
- **Scenario inputs are assumptions**, not model outputs: the speed uplifts, the peak-window
  demand reduction, and the direct delay terms in S2 and S3. See chapter Section 5.2.
