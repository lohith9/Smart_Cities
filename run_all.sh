#!/usr/bin/env bash
# Full pipeline — reproduces the 7 chapter-body figures AND the 5 Section 7
# supporting figures (PINN, ST-GCN, MARL, semantic, health). Runs from ANY cwd.
set -euo pipefail
cd "$(dirname "$0")/code"
echo "[1/12] 01_generate_dataset.py";    python3 01_generate_dataset.py
echo "[2/12] 02_train_ml_models.py";     python3 02_train_ml_models.py
echo "[3/12] 03_run_scenarios.py";       python3 03_run_scenarios.py
echo "[4/12] 04_make_figures.py";        python3 04_make_figures.py
echo "[5/12] 05_compute_mape.py";        python3 05_compute_mape.py
echo "[6/12] v2_01_network_dataset.py";  python3 v2_01_network_dataset.py
echo "[7/12] v2_02_pinn_dispersion.py";  python3 v2_02_pinn_dispersion.py
echo "[8/12] v2_03_stgnn.py";            python3 v2_03_stgnn.py
echo "[9/12] v2_04_marl.py";             python3 v2_04_marl.py
echo "[10/12] v2_05_semantic_6g.py";      python3 v2_05_semantic_6g.py
echo "[11/12] v2_06_health.py";          python3 v2_06_health.py
echo "[12/12] v2_07_figures.py";         python3 v2_07_figures.py
echo "PIPELINE COMPLETE — figs 1-7 (chapter body) and 8-12 (Section 7 supporting evidence)"
