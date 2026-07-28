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
single-threaded (`n_jobs=1`) for cross-machine determinism; Random Forest is deterministic
given `random_state`. Evaluation seeds 100–104 are used in the Appendix D scripts.

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

### One stale artefact

The shipped `data/health_results.json` was produced from rounded inputs (PM2.5 12.59 rather than
12.5926) and therefore differs from a fresh run by up to 0.032 per cent. No value from this file
appears in the chapter or the supplement, so no claim is affected. Running `run_all.sh` once
before tagging brings every shipped output into correspondence with a single consistent run.

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
