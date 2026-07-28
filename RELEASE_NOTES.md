# Release notes

## v1.0.0 — submission of the revised chapter

Reproducibility package accompanying the revised chapter submitted to IntechOpen,
*Smart Cities — Next-Generation Connectivity and Intelligence*.

### Contents
- `code/01`–`05`: corridor pipeline reproducing chapter Figures 3–7 and Table 4.
- `code/v2_01`–`v2_07`: demonstrations supporting Supplementary Appendix D (Figures 8–12).
- `data/`: the calibrated synthetic dataset and every generated result file.
- `figures/`: all twelve figures at 300 DPI.
- `code/marl_diagnostic.py`: a self-critical diagnostic for the Appendix D.3 result.

### Added during revision
- `05_compute_mape.py`, which reports MAPE alongside the previously published
  R², RMSE and MAE. It reuses the dataset, feature set, contiguous 70/15/15 split,
  seed (20260516) and hyperparameters of `02_train_ml_models.py`, and re-verifies
  the recomputed R²/RMSE/MAE against `data/ml_results.json` before reporting
  anything. If that check fails the script exits rather than emit metrics that do
  not correspond to the published run. Output goes to a separate file,
  `data/ml_results_with_mape.json`; the original results file is not modified.

### Known scope limits
- All data are synthetic. Live LAQN and TfL feeds were unreachable during the study.
- Reported scenario results come from a single seeded run, not an ensemble; no
  sampling interval accompanies them.
- Cross-validation, residual diagnostics and attribution methods such as SHAP were
  not performed.
- The Appendix D.3 delay reduction depends on a simplified delay proxy. See
  `code/marl_diagnostic.py`, which shows a naive constant throttle achieving a
  comparable reduction.
