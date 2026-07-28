# Zenodo deposit metadata

Fill these fields when archiving the GitHub release. Anything marked TO BE ADDED requires a
decision or a value that does not yet exist — do not invent them.

| Zenodo field | Value to enter |
|---|---|
| Upload type | Software |
| Title | Supplementary code and calibrated dataset for "Accessible Digital Twin Frameworks for Sustainable Traffic and Air Quality in 6G-Enabled Smart Cities" |
| Authors | Andra, Lohith Sai — Independent Researcher, Richmond, Virginia, USA |
| ORCID | TO BE ADDED |
| Description | Reproducibility package for an accessible, open-source digital twin framework coupling microscopic traffic simulation, supervised machine learning and an emission-coupled dispersion model, with a communication-aware control layer. Includes the calibrated synthetic dataset, all generated results, twelve figures at 300 DPI, and twelve scripts reproducing every reported figure and table. All data are synthetic and calibrated to published Inner-London priors; they are not measurements. |
| Version | v1.0.0 |
| License | MIT |
| Keywords | digital twin; traffic simulation; air quality; machine learning; 6G; smart cities; reproducibility; synthetic data |
| Related identifier | "is supplement to" → chapter DOI (add once IntechOpen assigns it) |
| Related identifier | "is supplemented by" → GitHub repository URL |
| Funding | TO BE ADDED — state none if unfunded |
| Language | English |
| Publication date | Date of Zenodo deposit |

## Order of operations

The GitHub Release, the Zenodo archive and the submitted ZIP must all be the **same immutable
release**. Build them in this order and they cannot diverge.

1. Freeze the repository — no further content changes.
2. Tag `v1.0.0`.
3. Create the GitHub Release from that tag, using `RELEASE_NOTES.md`.
4. Archive that release on Zenodo; Zenodo mints the DOI.
5. Write the DOI into `README.md`, `CITATION.cff`, `SOFTWARE_METADATA.md`,
   `CODE_AVAILABILITY.md`, and the chapter's Data and Code Availability section.
6. Build the submission ZIP **from the tagged v1.0.0 tree**, not from the working directory,
   so that the ZIP, the GitHub Release and the Zenodo archive are byte-equivalent in content:
   `git archive --format=zip -o Supplementary_Code_v1.0.0.zip v1.0.0`
7. Submit the manuscript with that ZIP.

Steps 5 and 6 are the only ordering trap: if the ZIP is built before the DOI exists, it ships an
archive that cannot cite itself.

## Versioning: why the DOI update becomes v1.0.1

Zenodo archives exactly the tree tagged `v1.0.0`. Writing the minted DOI back into `README.md`,
`CITATION.cff`, `SOFTWARE_METADATA.md` and `CODE_AVAILABILITY.md` necessarily changes that tree,
so the repository is no longer the thing Zenodo holds. Rather than blur the two, record the
change:

```
v1.0.0   the archived release. Matches the Zenodo record and MANIFEST.sha256 exactly.
             DOI fields read "pending".
   |
   v
v1.0.1   identical in code, data and figures. Differs only in that the DOI is now filled in.
             Commit message: "Add Zenodo DOI after release"
```

State in `CHANGELOG.md` which tag corresponds to the archived record. Submit the ZIP built from
`v1.0.0`, since that is what the DOI resolves to; cite the DOI in the chapter.

If you would rather submit a ZIP that already contains the DOI, archive `v1.0.1` on Zenodo as
well — Zenodo issues a version DOI plus a concept DOI covering all versions — and cite the
concept DOI in the chapter. Either is defensible. What is not defensible is a ZIP whose contents
do not correspond to any tagged release.

## Integrity

`MANIFEST.sha256` lists a SHA-256 hash for every file in the release. Anyone can verify a
downloaded copy with:

```bash
sha256sum -c MANIFEST.sha256
```

Regenerate it with `bash make_manifest.sh` immediately before tagging, and again after the DOI
edits if you tag `v1.0.1`.
