# Changelog

All notable changes to this reproducibility package.
Format follows Keep a Changelog; versioning follows Semantic Versioning.

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
