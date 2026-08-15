# Changelog

All notable changes to this reproducibility package.
Format follows Keep a Changelog; versioning follows Semantic Versioning.

## [1.0.5] — remove duplicated scenario logic

Code-quality only. Verified against the chapter and its Supplementary Material line by line
before and after this change: every equation, constant, clip bound, noise amplitude,
hyperparameter, scenario multiplier, and every value in Tables 4-6, matches exactly — see the
verification note below. No emission factor, coupling coefficient, background formula, scenario
multiplier, or seed was touched.

### Changed
- `code/03_run_scenarios.py`: removed `scenario_arr()`, a 28-line near-duplicate of `scenario()`
  whose only real difference was accepting a per-row array instead of a scalar for the flow
  multiplier (needed for S3's peak-window-only demand reduction). `scenario()`'s `flow_mult`
  parameter already broadcasts correctly against either a scalar or a numpy array via pandas'
  standard elementwise multiplication (`df.traffic_flow_vph * flow_mult`), so the two functions
  computed identically and existed only because of a naming accident, not a real difference in
  behaviour. S3 now calls the single `scenario()` function directly. Net: -30 lines, two
  divergence-prone copies of the delay/emission/dispersion computation collapsed into one.

### Verification
- `ast.parse` succeeds; `pyflakes` clean.
- Full 12-step pipeline re-run in a fresh pinned environment (Windows, packages exactly per
  `requirements.txt`) via `tests/verify_reproduction.py`: `data/scenarios.json` and
  `data/scenarios.csv` — the two files this change could possibly affect — show **zero**
  differences against the committed values, at any tolerance. Every other data file's
  divergence count (the known, already-documented XGBoost cross-platform effect from v1.0.4)
  is unchanged: still exactly 1225 flagged values, confirming this change affected nothing else
  in the pipeline either.
- Cross-checked the running code, after this change, against `_SUBMIT/02_Chapter.pdf` and
  `_SUBMIT/06_Supplementary_Material.pdf` (the submitted, frozen source of truth): Equations
  1-3, every constant in Appendix B, Tables 3-6, and the two specific counterfactual delay
  percentages stated in the Conclusion (recomputing S3 without its direct delay term reproduces
  43.33%, matching the chapter's "~43%"; S2's uplift without that term reproduces 34.07%,
  matching "~34%") all still hold exactly.

## [1.0.4] — reproduction harness, measured determinism, static cleanup

Adds a runnable reproduction check and documents what it found. No seed, hyperparameter,
emission factor, coupling coefficient, scenario multiplier, or split ratio was changed. No
`data/` or `figures/` file changed (confirmed: `git diff --stat -- data figures` empty
throughout this pass). For each of the seven edited `.py` files, `ast.parse` succeeds and the
change is a real (not cosmetic) removal of dead code — see "Fixed — code" below; this release
does not claim AST identity for those seven files the way v1.0.2/v1.0.3 did for docstring-only
edits, because these edits are not docstring-only. All seven were verified behaviour-preserving
by actually running the full 12-step pipeline afterward and confirming every non-XGBoost output
still matches the committed `data/` files exactly (see below).

### Added
- `tests/verify_reproduction.py` and `tests/README.md`. A clean-room reproduction harness: runs
  all 12 pipeline steps in a temporary directory (never touches this repository's `data/` or
  `figures/`) and compares every output against the committed files. No network access, no
  SUMO. Run against the pinned environment on Windows 11 (Intel Core 7 150U, Python 3.11.9): all
  12 steps exit zero; every non-XGBoost output — `LinearRegression` and `RandomForestRegressor`
  results, `scenarios.json/.csv`, `health_results.json`, the `v2_network` files,
  `marl_results.json`, `london_corridor.csv` — matches the shipped values (generated on Linux,
  per `SOFTWARE_METADATA.md`) exactly. `XGBRegressor`-derived values do not: see
  `REPRODUCIBILITY.md`, "Determinism, measured", for the full account. Two real bugs in the
  harness's own comparison logic were found and fixed while establishing this (documented in
  `tests/README.md`) — an exception-based short-circuit that silently skipped sibling keys after
  the first mismatch, and a filename-parsing bug that mis-classified `stgnn_results.json`.

### Fixed — documentation
- `REPRODUCIBILITY.md`: new "Determinism, measured" section. Two things were actually measured,
  not assumed: (1) the same training step run 10 times on one machine — `XGBRegressor` and
  `LinearRegression` were bit-identical across all 10 runs; `RandomForestRegressor` showed the
  last-bit thread-summation noise `RC1_RELEASE_CERTIFICATE.md` already documents (max ~2.7e-15
  absolute), confirming that documented claim independently with 10 runs instead of 2; (2)
  cross-platform reproduction (this Windows run vs. the Linux-generated shipped data) — every
  non-XGBoost output is exact, while `XGBRegressor` aggregate `r2` diverges by 5.7e-4 to 1.7e-2
  relative across the three `02_train_ml_models.py` targets, individual predictions by up to
  ~30%. This is the opposite of what `RC1_RELEASE_CERTIFICATE.md` names as the noise source (it
  discusses only RandomForest). Not a defect in the pipeline's seeding or design — see the new
  section for the mechanism and what it means for reproducing Table 4 on a non-Linux platform.
- `REPRODUCIBILITY.md`, "Random seeds": removed the claim that `n_jobs=1` gives XGBoost
  "cross-machine determinism". Measured directly (above): `n_jobs=1` gives exact same-machine
  determinism, which is what was actually verified; it does not give cross-machine determinism,
  which was not previously tested and is now shown not to hold.
- `.gitignore`: added `.pytest_cache/`, missing despite `__pycache__/` and `.venv/` already being
  covered.

### Fixed — code (pyflakes, behaviour-preserving)
Eight findings from `pyflakes` across the 13 scripts, each confirmed inert either by construction
(dead imports/locals that were never read; an f-string with no `{}` placeholder, which Python
evaluates identically to the plain string) or by re-running the full pipeline afterward:
- `code/04_make_figures.py`: removed unused `FancyArrowPatch` import (the script uses
  `ax.annotate` for arrows, not this class).
- `code/v2_02_pinn_dispersion.py`: removed a dead local `T = arr_dict["flow"].shape[0]` inside
  `build_feats()`, never read afterward in that function.
- `code/v2_03_stgnn.py`: removed unused `import pandas as pd` (the script never calls `pd.*`).
- `code/v2_04_marl.py`: removed a dead local `h = s % N_HOUR_STATES` inside `greedy_policy()`,
  never read afterward; and removed an unnecessary `f` prefix from a string with no placeholder.
- `code/v2_05_semantic_6g.py`, `code/v2_06_health.py`: same unnecessary-`f`-prefix fix.
- `code/v2_07_figures.py`: removed unused `import os as _os`. The script's `os.listdir`/
  `os.path.getsize` calls near the end of the file use a separate, plain `import os` already
  present at line 156 — confirmed by grep before removing the alias, since the two names look
  similar enough to invite a mistake here.

### Not changed
- No emission factor, coupling coefficient, background formula, clip bound, scenario multiplier,
  split ratio, or seed.
- No `data/` or `figures/` file (manifest confirms: 61 files now, up from 59 — the two new
  `tests/` files — everything else hash-identical to v1.0.3).
- Chapter §4.2's SUMO/network-release gap (already disclosed as an accepted limitation) — left
  unchanged. A concrete plan for closing it honestly, without touching the manuscript or any
  published number, was written up for the author's review but not implemented this pass.

## [1.0.3] — second source-verification pass over code comments and documentation

Documentation and code comments only. Executable code is unchanged: for each of the seven edited
scripts, the abstract syntax tree with all docstrings stripped is identical to v1.0.2. No data
file, no figure and no reported result changes; `data/` and `figures/` are byte-identical to
v1.0.2 (28 files, SHA-256 verified).

### Fixed — code comments

- `code/01_generate_dataset.py` header, corridor flow anchor. The header gave "~600-900 veh/h
  peak", a band the generator's own output exceeds: the shipped `data/london_corridor.csv` has a
  peak-hour mean of 907 veh/h. No published average was located. DfT road traffic statistics
  (raw hourly counts, 2019, principal A roads across eight inner-London boroughs, n = 145
  link-direction-days) give a per-direction peak-hour mean with median 497 veh/h and quartiles
  336-1133 veh/h, and 1506-2284 veh/h on the A501. Replaced with the generator's realised
  values and the retrieved DfT distribution.
- `code/01_generate_dataset.py` header, meteorology. "Wind speed mean: 3.5 m/s, RH ~75%
  (Heathrow met)" attributed two generator parameters to Heathrow observations. The generated
  series has wind mean 3.53 m/s and RH mean 69.6%; the Heathrow means for 1 April 2018 to
  28 February 2020 are 4.02 m/s and 76.02% (Hajmohammadi & Heydecker 2022, Table 2). Restated
  as generator parameters, with the Heathrow reference values given.
- `code/01_generate_dataset.py`, emission factors. "based on COPERT/EEA inventory averages for
  Inner London fleet 2023" asserted an averaging step and a fleet-year that were never verified.
  Aligned with chapter Section 4.4: fleet-average model parameters of the same order as the
  class-specific factors tabulated in the EMEP/EEA inventory, not quoted from any single table,
  with the guidebook's NOx-as-NO2-equivalent convention now disclosed.
- `code/03_run_scenarios.py`, idling penalty. "+12% emission per 25% speed drop (empirical)"
  described neither the code nor any source: the implemented penalty is the inverse of
  `speed_mult`, so a 25% speed reduction raises emissions by 33%. Restated to match the code and
  labelled an assumed relation.
- `code/v2_03_stgnn.py`, misquoted title. Yu, Yin & Zhu (IJCAI 2018) is
  "Spatio-Temporal Graph Convolutional Networks: A Deep Learning Framework for Traffic
  Forecasting" (doi:10.24963/ijcai.2018/505), not "STGCN: Spatio-Temporal Graph Convolutional
  Networks for Traffic Forecasting" as quoted.
- `code/v2_04_marl.py` header. The stated reward `-|pressure| - 0.05 * delay_proxy` and the
  three-level state discretisation both contradicted `train_marl`, which uses
  `-|pressure|/200 - 0.5 * delay_proxy` and five-bin discretisation over 125 states. The header
  also gave PressLight's directed upstream-minus-downstream pressure while the code uses an
  undirected own-minus-neighbour-mean form. Corrected to describe the implementation.
- `code/v2_05_semantic_6g.py` header. Calvanese Strinati & Barbarossa's two-author paper is
  Computer Networks 190:107930, 2021, not 2024. The Gunduz citation verified exact. No
  Proceedings of the IEEE 2023 paper by Shi on semantic communications was located; marked
  NOT VERIFIED rather than removed.
- `code/v2_06_health.py`. Four corrections. HRAPIE does not recommend RR = 1.039 for NO2; its
  recommendation is 1.055 (95% CI 1.031-1.080) per 10 µg/m³, all natural-cause mortality, age
  30+, above an annual mean of 20 µg/m³ (Héroux et al., Int J Public Health 2015, Table 1). The
  5 µg/m³ counterfactual is the WHO 2021 AQG level for PM2.5 but not for NO2, whose 2021 AQG
  level is 10 µg/m³. `BASE_MORT = 870` per 100,000 was labelled "adults 30+" in one comment and
  "population averaged for the UK" in another; it is an all-ages crude rate (ONS: 893.1 per
  100,000, England and Wales, 2019). The "16 YLL per death" attribution to GBD 2019 could not be
  located and is now marked NOT VERIFIED. All four constants are unchanged.
- `code/v2_07_figures.py` header named a non-existent filename (`v2_07_figures_AUDITED.py`) and
  cited a `FIGURE_AUDIT_REPORT.md` that is not in the repository.

### Fixed — documentation

- `REPRODUCIBILITY.md`, "One stale artefact". The claim that `data/health_results.json` was built
  from rounded inputs is refuted by the shipped file, which carries the full-precision values of
  `data/scenarios.json`. `RC1_RELEASE_CERTIFICATE.md` already recorded the fix; the two documents
  contradicted each other.
- `RC1_RELEASE_CERTIFICATE.md`: the integrity manifest holds 59 entries, not 57
  (60 tracked files less `MANIFEST.sha256`, which the manifest excludes by design).
- `DOI_UPDATE_CHECKLIST.md`: the DOIs were applied on 2026-07-29, not 2026-07-28 — DataCite
  records both as registered 2026-07-29T14:27:29Z. Three checklist items already completed were
  still shown unchecked.
- `run_all.sh` still described Figures 8-12 as "Section 7"; that material became Supplementary
  Appendix D during revision, as `README.md` records.
- `requirements.txt` claimed the pins were the versions used for the shipped figures. The figures
  were rendered with matplotlib 3.10.9 against a 3.10.8 pin, as `RC1_RELEASE_CERTIFICATE.md`
  states. Scope of the claim narrowed to `data/`.
- `RELEASE_NOTES.md` credited `01`–`05` with Figures 3-7 and Table 4 only; the README mapping
  table, which is authoritative, also assigns Figures 1-2 and Tables 5 and 6.
- `VERSION` still read `v1.0.0` at tags v1.0.1 and v1.0.2. It now tracks the tag, and `README.md`,
  `SOFTWARE_METADATA.md` and `CODE_AVAILABILITY.md` distinguish the repository version from the
  archived and cited release, which remains **v1.0.0**. `CITATION.cff` is deliberately unchanged:
  it describes the Zenodo deposit, whose version, DOI and release date are all v1.0.0.
- `MANIFEST.sha256` regenerated.

### Not changed

- No executable code, no `data/` file, no `figures/` file.
- Figure 1 labels the coupling layer "COPERT-style EF + Gaussian dispersion" and Figures 1-2 name
  SUMO in the pipeline. The implemented dispersion is a box-dilution form, not a Gaussian plume,
  and no SUMO run contributes to any reported result. These strings are executable code that
  renders into shipped figures, so they were reported rather than edited.

## [1.0.2] — source-verification corrections to documentation

Documentation and code comments only. Executable code is unchanged: the abstract syntax trees of
both edited scripts, with docstrings stripped, are identical to v1.0.1. No data file, figure or
reported result changes.

### Fixed
- `code/01_generate_dataset.py` header. The PM2.5 and NO2 calibration anchors were dated to 2023
  and the PM2.5 band was attributed to LAQN Marylebone Road. Both were wrong. Verified against
  GLA, *Air Quality in London 2016-2024*: the 11-13 ug/m3 PM2.5 band and 35-50 ug/m3 roadside NO2
  band correspond to 2018-2019, not 2023 (2023 London annual mean PM2.5 is 7.8-10.0 ug/m3), and
  the site attribution was never verified. Corrected to cite the GLA tables and the correct years,
  and to note that central-London roadside NO2 is substantially higher than the stated band.
- `code/03_run_scenarios.py` header. The scenario magnitudes were attributed to Eom & Kim 2020
  (European Transport Research Review 12:50) after an earlier unverifiable 2024 attribution was
  removed. The full text of Eom & Kim contains no percentage figures of any kind; it classifies
  72 papers by performance index and reports no delay reductions. The attribution has been
  removed and no replacement is claimed. The parameters remain disclosed as assumed inputs.
- `MANIFEST.sha256` regenerated for the two edited files.

## [1.0.1] — DOI insertion

Identical to v1.0.0 in code, data and figures. The only change is that the Zenodo DOI and paper
DOI are filled in across `README.md`, `CITATION.cff`, `SOFTWARE_METADATA.md` and
`CODE_AVAILABILITY.md`. **v1.0.0 is the tag archived on Zenodo and is the one that matches
`MANIFEST.sha256` as deposited.** Released and tagged.

## [1.0.0] — public release accompanying the revised chapter

### Added
- `05_compute_mape.py`. Reports MAPE alongside the previously published R², RMSE and MAE.
  Reuses the dataset, feature set, contiguous 70/15/15 split, seed (20260516) and
  hyperparameters of `02_train_ml_models.py`, and re-verifies recomputed R²/RMSE/MAE
  against `data/ml_results.json` before reporting. Exits without output if that check
  fails. Writes to `data/ml_results_with_mape.json`; does not modify the original results.
- `CITATION.cff`, `VERSION`, `CHANGELOG.md`, `RELEASE_NOTES.md`, `REPRODUCIBILITY.md`,
  `SOFTWARE_METADATA.md`, `ZENODO_METADATA.md`, `CODE_AVAILABILITY.md`, `DISCLAIMER.md`,
  `SECURITY.md`, `MANIFEST.sha256`, `make_manifest.sh`.
- Clean-room reproduction verified; results recorded in `REPRODUCIBILITY.md`.
- README: runtime, an output-to-manuscript mapping table, and citation instructions.

### Changed
- `run_all.sh` extended from 11 to 12 steps to include `05_compute_mape.py`.
- README corrected: chapter title, script count, and references to the relocated
  advanced-extensions material (now Supplementary Appendix D).
- `marl_diagnostic.py` moved from `audit/` to `code/`, since Appendix D.3 cites it as
  evidence for its own hedge.

### Removed
- `figures.zip` (byte-identical duplicate of `figures/`).
- `audit/` internal development reports, retained privately by the author.
- Build artefacts (`__pycache__`, `.pyc`, `.DS_Store`).
