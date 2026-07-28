# Code availability

This repository accompanies the chapter

> **Accessible Digital Twin Frameworks for Sustainable Traffic and Air Quality in 6G-Enabled
> Smart Cities**
> Lohith Sai Andra. In: *Smart Cities — Next-Generation Connectivity and Intelligence*.
> London: IntechOpen.

| | |
|---|---|
| Repository version | v1.0.0 |
| Repository DOI | Pending Zenodo deposit |
| Paper DOI | Pending publication |
| Licence | MIT |

## Contents

- Source code — twelve pipeline scripts plus `marl_diagnostic.py`
- Calibrated synthetic dataset — `data/london_corridor.csv` and all generated result files
- Figures — twelve, at 300 DPI
- Reproducibility scripts — `run_all.sh` runs the full pipeline in order

## Scope of reproduction

This repository reproduces every figure, table and metric reported in the chapter. The mapping
from each script and output file to the specific manuscript figure or table is given in
`README.md`. Two qualifications apply, and they are stated in the chapter as well:

- Results come from a **single seeded run**, not an ensemble, so no sampling interval
  accompanies them.
- The scenario **inputs** — speed uplifts, the peak-window demand reduction, and the direct
  delay terms in S2 and S3 — are assumptions rather than model outputs. See chapter Section 5.2.

## Preservation

The repository is archived on Zenodo so that the version underlying the published chapter
remains retrievable independently of the hosting platform.

## Correspondence with the chapter

The chapter's Data and Code Availability section states that the reference implementation,
calibrated dataset and trained model artefacts will be released in a permissively licensed
public repository at the time of publication. This repository is that release.
