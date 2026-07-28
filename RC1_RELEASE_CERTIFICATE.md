# Release Candidate Certificate — RC1

| | |
|---|---|
| **Project** | Accessible Digital Twin Frameworks for Sustainable Traffic and Air Quality in 6G-Enabled Smart Cities |
| **Publication** | IntechOpen, *Smart Cities — Next-Generation Connectivity and Intelligence* |
| **Version** | v1.0.0 (Release Candidate 1) |
| **Date** | 2026-07-28 |
| **Prepared by** | Lohith Sai Andra |
| **Status** | Release Candidate — approved for public release once the author decisions below are closed |

---

## Scientific scope

This repository accompanies the chapter and reproduces every figure, table and reported metric
it contains. All datasets are synthetic and calibrated to published Inner-London priors; they are
not measurements. See `DISCLAIMER.md`.

---

## Verification performed

| Check | Result |
|---|---|
| Repository cleaned of build artefacts | Pass — no `__pycache__`, `.pyc`, `.DS_Store`, no duplicate archive |
| Dependencies pinned | Pass — five packages pinned in `requirements.txt`; no undeclared imports across 13 scripts |
| Paths portable | Pass — all scripts resolve paths with `pathlib`; zero absolute or user-specific paths |
| Single random seed | Pass — 20260516 used throughout |
| Licence present | Pass — MIT |
| Citation metadata | Pass — `CITATION.cff` (CFF 1.2.0, valid YAML) |
| Software metadata | Pass — `SOFTWARE_METADATA.md` |
| Code availability statement | Pass — `CODE_AVAILABILITY.md`, mirroring the chapter |
| Synthetic-data disclaimer | Pass — `DISCLAIMER.md` |
| Security policy | Pass — `SECURITY.md` |
| Version and history | Pass — `VERSION`, `CHANGELOG.md`, `RELEASE_NOTES.md` |
| Integrity manifest | Pass — `MANIFEST.sha256`, 57 files, self-verified with `sha256sum -c` |
| Documentation completeness | Pass — README answers install, run, runtime, outputs, output-to-manuscript mapping, versions, reproduction, citation |
| **Clean-room execution** | **Pass — all 12 pipeline steps completed from an emptied copy** |

---

## Reproduction results

The pipeline was executed end to end in a clean copy with `data/` and `figures/` emptied
beforehand, on Python 3.10.12 with the pinned dependencies.

**Reproduced:** Figures 1–12; the metrics behind chapter Tables 4 and 6; all Appendix D results.

**Byte-identical:** `london_corridor.csv`, `feature_importance.csv`, `scenarios.csv`,
`marl_learning_curve.csv`, `v2_network.npz`, `v2_adjacency.npy`, `v2_node_table.csv`.

**Identical:** `scenarios.json`, `health_results.json`, and — once machine-dependent timing
fields are excluded — `pinn_results.json`, `stgnn_results.json`, `marl_results.json`,
`semantic_results.json`.

**Observed differences, all understood:**

| Difference | Magnitude | Consequence |
|---|---|---|
| Random Forest metrics, last bit | max 1.8 × 10⁻¹⁵ | None. Values are reported to three decimals or fewer. Caused by thread-dependent summation order under `n_jobs=-1`; set `n_jobs=1` for bit-identical output. |
| `predictions.csv` | max 2.3 × 10⁻¹³ | None. |
| `fit_time_s`, `pred_time_ms` and equivalents | machine-dependent | None. Not reported in the chapter. |

**Resolved during RC1:** `health_results.json` had been generated from rounded inputs
(PM2.5 12.59 rather than 12.5926). It was regenerated from the current pipeline and now matches a
clean-room run exactly. `MANIFEST.sha256` was rebuilt afterwards.

**No value reported in the chapter changed as a result of any check in this certificate.**

---

## Known limitations, disclosed in the manuscript

- All data are synthetic; live LAQN and TfL feeds were unreachable during the study.
- Results come from a single seeded run, not an ensemble; no sampling interval accompanies them.
- Cross-validation, residual diagnostics and attribution methods such as SHAP were not performed.
- Scenario inputs — speed uplifts, peak-window demand reduction, and the direct delay terms in
  S2 and S3 — are assumptions, not model outputs.

---

## Author decisions — all closed

Recorded here because the certificate must reflect the state of the release it certifies.

| # | Decision | Outcome |
|---|---|---|
| 1 | 3% / 5% direct delay terms in S2 and S3 | **KEEP.** Classified as explicit modelling assumptions: the delay expression is a function of mean speed alone, so a controller that suppresses shock transients without raising mean speed would otherwise register no benefit. No published source is claimed for either value. Section 5.2 discloses both, and the conclusion quantifies their effect. No scientific result changed. |
| 2 | "Tahmasseby et al. 2024" | **REMOVED.** NOT VERIFIED against Crossref: the author is real (27 indexed works, transportation research) but no digital-twin meta-analysis exists in his record. The attribution was struck from the `03_run_scenarios.py` header. Scenario outputs unchanged. |
| 3 | 90-day versus 91-day window | **RESOLVED.** Corrected to "a 90-day window (1 September to 29 November) ... giving 2,160 records", matching `N_DAYS = 90` and the dataset exactly. |
| 4 | Literature verification | **PARTIAL — author task.** 13 of 34 DOIs verified against Crossref, including [25] and [34], which underpin the two comparison figures. None has failed. Reading back the eight quantitative figures to their sources remains with the author. |

## Release status

**Release Candidate 1.** All four author decisions are closed. Approved for public release,
Zenodo archival and manuscript submission. The release procedure is in
`ZENODO_METADATA.md`; the checklist is `_SUBMIT/10_RELEASE_CHECKLIST.txt`.

Figures were rendered with matplotlib 3.10.9; `requirements.txt` pins 3.10.8. Figure images are
not byte-reproducible across matplotlib patch versions. If byte-identical figures matter,
regenerate them in the pinned environment before tagging.
