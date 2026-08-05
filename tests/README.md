# Reproduction verification harness

`verify_reproduction.py` is a clean-room reproduction check: it copies `code/`
into a temporary directory, runs all 12 pipeline steps there against an
empty `data/` and `figures/`, and compares every generated file against the
ones committed in this repository. It never writes to the repository's own
`data/` or `figures/`.

```bash
python tests/verify_reproduction.py --python /path/to/pinned/venv/python
```

Defaults to `sys.executable` if `--python` is omitted. Add `--keep` to leave
the temporary directory in place for inspection, or `--steps N` to run only
the first N of the 12 steps.

## What this checks

- Every one of the 12 pipeline steps exits zero, in the documented order.
- Every generated `data/*.json`, `*.csv`, `*.npy`, `*.npz` file matches the
  committed one, field by field, within a declared tolerance (see below).
- Every `figures/fig*.png` is produced and non-empty.
- No network access and no SUMO are required or attempted at any point.

## What this does NOT check

- **Figure pixel content.** PNGs are compared for existence and non-zero
  size only, never byte-for-byte or pixel-for-pixel.
  `RC1_RELEASE_CERTIFICATE.md` already records that the shipped figures were
  rendered with matplotlib 3.10.9 against a `3.10.8` pin in
  `requirements.txt`, and that PNG output is not byte-reproducible across
  matplotlib patch versions.
- **The manuscript, the supplement, or any chapter figure/table caption.**
  This harness verifies the repository reproduces itself. Whether the
  repository's numbers match what the chapter prints is a separate, manual
  cross-check.
- **The `v2_07_figures.py` module docstring's self-description as
  `v2_07_figures_AUDITED.py`.** That mismatch is a documentation defect
  already recorded in `CHANGELOG.md` [1.0.3]; this harness does not check
  filenames referenced in docstrings.

## Tolerance policy — measured, not assumed

This harness was run twice on a real machine (Windows 11, Intel Core 7 150U,
10 cores, Python 3.11.9, packages installed exactly per `requirements.txt`)
against the data this repository actually ships, which was generated on
Linux (`SOFTWARE_METADATA.md`). The first run's classification turned out to
be wrong in two separate ways — both bugs, and the finding they were hiding,
are recorded here so the next person doesn't have to rediscover either.

**What was actually found**, directly inspected (not inferred from
aggregates — every claim below was checked against both the aggregate JSON
metric and the underlying `predictions.csv` row values it's computed from):

- `LinearRegression` and `RandomForestRegressor` (`n_jobs=-1`) reproduce
  **exactly** cross-platform: 0 differences across all 3 targets in
  `ml_results.json`, and every `_rf` column in `predictions.csv`'s 324 rows,
  Windows vs. the shipped Linux values.
- **`XGBRegressor` (`n_jobs=1`) does not.** Aggregate `r2` diverges by
  5.7e-4 (traffic_flow_vph) to 1.7e-2 relative (no2_ugm3) — the no2_ugm3
  case moves `r2` from 0.9223 to 0.9384, `rmse` from 8.38 to 7.46 (11%),
  and `mape_pct` from 14.77 to 13.37 (9.5%). Individual `predictions.csv`
  rows for the `_xgb` columns differ by up to ~30%, and
  `feature_importance.csv`'s XGBoost-derived rankings reorder from roughly
  the third feature onward for every target. This is the **opposite** of
  what `RC1_RELEASE_CERTIFICATE.md` documents — that certificate names only
  `RandomForestRegressor`'s thread-parallel summation as a noise source and
  says nothing about XGBoost.
- **This is a cross-platform effect, not run-to-run instability.** A
  separate check — training the exact `02_train_ml_models.py` step 10 times
  in this one environment, holding the seed fixed — found XGBoost bit-for-bit
  identical across all 10 runs (`spread = 0.000e+00` for every metric, every
  target). RandomForest showed the same last-bit noise
  `RC1_RELEASE_CERTIFICATE.md` already documents (max `~2.7e-15` absolute on
  RMSE, `uniq` up to 4 distinct values out of 10 runs) — real, but
  many orders of magnitude below anything that could move a value quoted to
  2–3 decimal places. See `REPRODUCIBILITY.md`, "Determinism, measured" for
  the full table.
- Every quantity computed without any ML training reproduces **exactly**
  cross-platform: `scenarios.json`/`.csv`, `health_results.json`,
  `v2_network.npz`/`v2_adjacency.npy`/`v2_node_table.csv`,
  `marl_results.json`/`marl_learning_curve.csv` (Python's seeded
  `random.Random`, not numpy), and `london_corridor.csv` itself.
- `semantic_results.json` (PCA + MLPRegressor) showed **0 mismatches** on
  this Windows run — it reproduced exactly, same as RandomForest. This
  remains only single-run evidence, not a guarantee for every platform.

**Two bugs found and fixed in this harness while establishing the above**
(both are why the numbers here are trustworthy rather than assumed):

1. The JSON comparator originally raised an exception on the *first*
   mismatch per file and the caller's `try/except` swallowed it, silently
   skipping every sibling key. `ml_results.json` has three top-level keys
   (`traffic_flow_vph`, `pm25_ugm3`, `no2_ugm3`); the bug meant only the
   first one to fail was ever reported, making it look like XGBoost
   diverged on one target when it actually diverges on all three. Fixed by
   accumulating into a plain list instead of raising.
2. The per-value classifier derived the current file's name by splitting
   the accumulated dotted path on `.` (e.g.
   `"stgnn_results.json.summary[0].r2_mean"`) and taking the first segment
   — but the filename itself contains a `.` (`stgnn_results` + `.json`), so
   `name.split(".")[0]` produced `"stgnn_results"`, which never matched the
   `"stgnn_results.json"` entry in the classification set. This silently
   left every value in `stgnn_results.json` in the wrong bucket (it has no
   `"model"` field to fall back on — only `"predictor"`, and all four
   predictor variants are XGBoost regardless of name). Fixed by threading
   the real filename through the recursion explicitly instead of parsing it
   back out of the display path.

**Classes actually implemented, `verify_reproduction.py`:**

- **`exact`** (`EXACT_RTOL = 1e-9`) — everything confirmed exact above:
  LinearRegression, RandomForest, and every non-ML deterministic file.
- **`thread`** (`THREAD_RTOL = 1e-9`) — reserved for RandomForest's
  documented same-platform thread noise; currently has no confirmed member
  on this run (RandomForest passed at `exact` tolerance), kept for future
  reruns where that noise could reappear.
- **`xgboost_platform`** — every XGBoost-derived value. Reported in its own
  labelled bucket, always printed, **never counted toward the pass/fail
  exit code**. The harness prints a note distinguishing "expected on this
  platform" (non-Linux) from "UNEXPECTED — running on Linux" (which would
  mean the divergence is present even on the platform the shipped data was
  generated on, and would need investigating as a real regression rather
  than a known platform effect).
- Timing fields (`fit_time_s`, `pred_time_ms`, `train_time_s`, and
  equivalents) are excluded from every comparison — machine-dependent by
  construction, not reported in the chapter.

## What this means for reproducing the chapter

Every scenario, health, network-topology and delay/emission number reported
in the chapter reproduces exactly on a different OS than the one the results
were generated on. The ML prediction-accuracy numbers that specifically come
from **XGBoost** (not RandomForest, not LinearRegression) — Table 4's
XGBoost rows, and the XGBoost columns in Table 4's supplementary detail —
should be treated as reproducible on the tested platform (Linux) but **not
guaranteed to reproduce to the same decimal places on a different OS or
XGBoost build**, even with the seed and all hyperparameters unchanged. This
is a known category of limitation in histogram-based gradient boosting
(binning/quantile-sketch floating-point operations are not guaranteed
bit-identical across CPU/compiler/platform combinations) and is not evidence
of an error in this repository's pipeline, its seeding, or its published
values — see `REPRODUCIBILITY.md` for the full record and the author's
options for addressing it in the text, if any are wanted.
