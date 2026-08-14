# Accessible Digital Twin Frameworks for Sustainable Traffic and Air Quality in 6G-Enabled Smart Cities — Supplementary Code

| | |
|---|---|
| **Status** | Stable release |
| **Version** | v1.0.5 — archived and cited release: **v1.0.0** (see `CHANGELOG.md`) |
| **Reproducibility** | Fully reproducible from source — `bash run_all.sh` |
| **Data** | Synthetic, calibrated — see `DISCLAIMER.md` |
| **Software DOI** | [10.5281/zenodo.21679390](https://doi.org/10.5281/zenodo.21679390) (v1.0.0) · concept DOI [10.5281/zenodo.21679389](https://doi.org/10.5281/zenodo.21679389) |
| **Paper DOI** | Pending publication |
| **License** | MIT |

See `CODE_AVAILABILITY.md`, `REPRODUCIBILITY.md` and `DISCLAIMER.md` for the full statements.



Reproducibility package for the chapter (IntechOpen, *Smart Cities — Next-Generation Connectivity and Intelligence*).

> **Note on structure.** The advanced extensions (PINN, ST-GCN, MARL, semantic communications, health) were moved out of the chapter body into the Supplementary Material as Appendix D during revision. The `v2_*` scripts support that appendix. Chapter references below use the revised numbering.
Author: **Lohith Sai Andra** (Independent Researcher, Richmond, Virginia, USA).

> **Synthetic-data disclaimer.** All datasets in `data/` are synthetic but statistically calibrated to published Inner-London priors (LAQN air quality, TfL traffic, Heathrow meteorology). They are **not** live measurements. The pipeline runs unchanged on real LAQN/TfL feeds; only the input CSV needs swapping. Every reported metric is an internal demonstration on calibrated synthetic data.

## Repository structure

```
Supplementary/
├── README.md  LICENSE  requirements.txt  run_all.sh
├── code/      12 pipeline scripts + marl_diagnostic.py
│   ├── 01–05            v1 corridor pipeline (figures 1–7 and Table 4 metrics)
│   └── v2_01–v2_07      Appendix D demonstrations (PINN, ST-GCN, MARL, semantic, health, figs 8–12)
├── data/      pipeline inputs + result JSON/CSV (both v1 and v2)
├── figures/   figures 1–12 (300 DPI PNG; 1–7 embedded in chapter, 8–12 supporting Appendix D)
└── (see CHANGELOG.md, REPRODUCIBILITY.md, SOFTWARE_METADATA.md)
```

## Environment setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.10
pip install -r requirements.txt
```

## Run order

All scripts use script-relative paths (`pathlib`) — run from any working directory.
One-command: `bash run_all.sh`. Manual:

```bash
cd code
# --- v1 chapter-body figures (Section 6) ---
python3 01_generate_dataset.py   # -> data/london_corridor.csv
python3 02_train_ml_models.py    # -> data/ml_results.json, predictions.csv, feature_importance.csv
python3 03_run_scenarios.py      # -> data/scenarios.json, scenarios.csv
python3 04_make_figures.py       # -> figures/fig1..fig7  (used in chapter body)
python3 05_compute_mape.py       # -> data/ml_results_with_mape.json (Table 4; reproduces
                                 #    R2/RMSE/MAE from step 2, then adds MAPE. Aborts if the
                                 #    reproduction check fails.)

# --- v2 Appendix D demonstrations ---
python3 v2_01_network_dataset.py # -> data/v2_network.npz, v2_adjacency.npy, v2_node_table.csv
python3 v2_02_pinn_dispersion.py # -> data/pinn_results.json (Appendix D.1)
python3 v2_03_stgnn.py           # -> data/stgnn_results.json (Appendix D.2)
python3 v2_04_marl.py            # -> data/marl_results.json, marl_learning_curve.csv (Appendix D.3)
python3 v2_05_semantic_6g.py     # -> data/semantic_results.json (Appendix D.4)
python3 v2_06_health.py          # reads data/scenarios.json -> data/health_results.json (Appendix D.5)
python3 v2_07_figures.py         # -> figures/fig8..fig12 (Appendix D evidence)
```

`v2_06_health.py` reads `data/scenarios.json` from step 3, so the v1 pipeline must run before `v2_06`.

## Expected outputs

- `data/`: `london_corridor.csv`, `ml_results.json`, `ml_results_with_mape.json`, `predictions.csv`, `feature_importance.csv`, `scenarios.{json,csv}`, `v2_network.npz`, `v2_adjacency.npy`, `v2_node_table.csv`, `pinn_results.json`, `stgnn_results.json`, `marl_results.json`, `marl_learning_curve.csv`, `semantic_results.json`, `health_results.json`.
- `figures/`: `fig1_architecture.png` … `fig12_health.png`.


## Runtime

The v1 pipeline (steps 1-5) completes in a few minutes on a single CPU core; no GPU is required.
The v2 demonstrations (steps 6-12) add a few further minutes. `bash run_all.sh` runs all twelve.

## How outputs map to the manuscript

| Manuscript item | Produced by | Output file |
|---|---|---|
| Figure 1 (architecture) | `04_make_figures.py` | `figures/fig1_architecture.png` |
| Figure 2 (pipeline) | `04_make_figures.py` | `figures/fig2_pipeline.png` |
| Figure 3 (R2 by target/model) | `02` then `04_make_figures.py` | `figures/fig3_r2_bars.png` |
| Figure 4 (observed vs predicted) | `02` then `04_make_figures.py` | `figures/fig4_predictions.png`, `data/predictions.csv` |
| Figure 5 (scenario comparison) | `03` then `04_make_figures.py` | `figures/fig5_scenarios.png` |
| Figure 6 (state drift vs control frequency) | `03` then `04_make_figures.py` | `figures/fig6_6g_latency.png` |
| Figure 7 (NO2 sensitivity surface) | `04_make_figures.py` | `figures/fig7_sensitivity.png` |
| Table 3 (hyperparameters) | declared in `02_train_ml_models.py` | — |
| Table 4 (R2, RMSE, MAE, MAPE) | `02` then `05_compute_mape.py` | `data/ml_results.json`, `data/ml_results_with_mape.json` |
| Table 5 (corridor characterisation) | `01_generate_dataset.py` | `data/london_corridor.csv` |
| Table 6 (scenario outcomes) | `03_run_scenarios.py` | `data/scenarios.json`, `data/scenarios.csv` |
| Supplement Appendix D.1 (physics-augmented) | `v2_02_pinn_dispersion.py` | `data/pinn_results.json`, `figures/fig8_pinn_hybrid.png` |
| Supplement Appendix D.2 (graph forecasting) | `v2_03_stgnn.py` | `data/stgnn_results.json`, `figures/fig9_stgnn.png` |
| Supplement Appendix D.3 (RL signal control) | `v2_04_marl.py` | `data/marl_results.json`, `figures/fig10_marl.png` |
| Supplement Appendix D.4 (semantic uplink) | `v2_05_semantic_6g.py` | `data/semantic_results.json`, `figures/fig11_semantic.png` |
| Supplement Appendix D.5 (health) | `v2_06_health.py` | `data/health_results.json`, `figures/fig12_health.png` |

Figures 1-7 are embedded in the chapter. Figures 8-12 support Supplementary Appendix D.

## Reproducibility notes

- Seeds fixed throughout (`np.random.default_rng(20260516)`, scikit-learn / XGBoost `random_state=20260516`, evaluation seeds 100–104).
- Single-thread XGBoost (`n_jobs=1`) for cross-machine determinism; multi-thread Random Forest is deterministic given random_state.
- The Appendix D.3 MARL delay reduction depends on a simplified delay proxy; see `code/marl_diagnostic.py` for the proof that a naive constant throttle achieves a similar reduction. Appendix D.3 hedges accordingly.
- Tested on Python 3.10, package versions pinned in `requirements.txt`.

## How to cite

Please cite the chapter. If you use the code or the generated dataset directly, please also cite the
software archive.

**Chapter**
> Andra, L. S. Accessible Digital Twin Frameworks for Sustainable Traffic and Air Quality in 6G-Enabled
> Smart Cities. In: *Smart Cities - Next-Generation Connectivity and Intelligence*. London: IntechOpen.
> DOI: Pending publication.

**Software and data**
> Andra, L. S. Supplementary code and calibrated dataset for "Accessible Digital Twin Frameworks for
> Sustainable Traffic and Air Quality in 6G-Enabled Smart Cities".
> DOI: 10.5281/zenodo.21679390

The software DOI above resolves to the archived v1.0.0 release. The paper DOI will be added
once IntechOpen assigns it. Repository: https://github.com/lohith9/Smart_Cities

## License

MIT (code). Synthetic data may be reused under the same terms with attribution.
