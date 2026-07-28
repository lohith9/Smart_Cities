# DOI update checklist

Run this **after** Zenodo mints the DOI and **before** building the final submission ZIP.
Every line below was located by scanning for placeholder strings; no other file contains one.

## Repository files

- [ ] **`README.md`** — 4 placeholders
  - status table: `Software DOI` → Zenodo DOI
  - status table: `Paper DOI` → chapter DOI
  - "How to cite", chapter entry: `DOI: Pending publication.`
  - "How to cite", software entry: `DOI: Pending Zenodo deposit.`
- [ ] **`CITATION.cff`** — 3 placeholders
  - `message:` line — replace "pending publication and Zenodo deposit"
  - `repository-code: "TO BE ADDED - public repository URL"`
  - `date-released: "TO BE ADDED"`
  - *(add a `doi:` field once known)*
- [ ] **`SOFTWARE_METADATA.md`** — 5 placeholders
  - `ORCID`, `Repository`, `Software DOI`, `Paper DOI`, `Release date`
- [ ] **`CODE_AVAILABILITY.md`** — 2 placeholders
  - `Repository DOI`, `Paper DOI`
- [ ] **`ZENODO_METADATA.md`** — 3 placeholders
  - `ORCID`, `Related identifier` (chapter DOI), `Funding`
  - *(this file records what you entered; update for the record)*

## Outside the repository

- [ ] **`../Andra_FullChapter_IntechOpen_REVISED.docx`** — Data and Code Availability section.
      Currently: "will be released in a permissively licensed public repository at the time of
      publication." Replace with the repository URL and Zenodo DOI.

## After editing

- [ ] `bash make_manifest.sh` (the manifest hashes change)
- [ ] `git add -A && git commit -m "Add Zenodo DOI after release"`
- [ ] `git tag -a v1.0.1 -m "Documentation-only: DOI insertion"` — see CHANGELOG
- [ ] Build the submission ZIP from the tag you intend to cite
