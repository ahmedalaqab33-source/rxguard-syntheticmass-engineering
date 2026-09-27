# Engineering audit — 2026-09-27

## Discovery and preservation

The canonical source is the existing `DRxGuard_Data` project identified through the user's prior research index and verified against actual artifacts. At discovery it contained approximately 89.54 decimal GB and 268,320 files, including the large FHIR branch. The original root was not a Git repository and had no inherited parent Git history. No alternative complete/current copy was found in targeted Desktop/OneDrive/Documents/Downloads and research-workspace searches.

`RxGuard_Analytics` is the canonical CSV analytical branch: ingestion/cohort scripts, a 103,821,312-byte DuckDB database, Parquet table folders, historical reports, atlas outputs, and kill-test outputs. `RxGuard_Audit` contains the earlier integrity report. `RxGuard_CSV_Batches` contains the 108 source CSVs. Two 3D execution packages and multiple fixed batch/Python wrappers are older or alternative implementations within the same root. They are preserved, not deleted or promoted over completed evidence.

The root also mixes unrelated manuscripts, signed forms, CVs, personal documents, images, partial downloads, and temporary Office files. These are excluded completely. R scripts, notebooks, package/environment declarations, a project README, a license, citation metadata, and tests were not found in the selected canonical analytical branch. SQL is embedded in Python. No clinical dataset is added to this release.

The publication directory is a curated derivative of existing code and evidence. Source SHA-256 provenance and original Python snapshots are retained; canonical originals are unchanged. Local forensic inventory records full private locations separately from public repository files.

## Completion matrix

| Component | Evidence | Status | Action |
| --- | --- | --- | --- |
| Discovery and preservation | Actual source inventory, code hashes, original snapshots | PASS | Curated derivative; no deletion or source overwrite |
| Large-scale ingestion | 108-entry manifest, current source sizes, nine table counts | PASS | Verify metadata and Parquet; do not claim a new full CSV run |
| Patient row fidelity | 1,595,050 original vs 1,594,711 repaired | NEEDS WORK | Preserve both; disclose 339-row difference |
| Parquet schemas | One schema per nonpatient table, four patient variants | NEEDS WORK | Document overflow and semantic restrictions |
| Original DuckDB access | Read-only open succeeds; old-path views fail | NEEDS WORK | Preserve original; CLI builds new correctly located views |
| Reproducible current access | New-workspace full-scale execution | PASS | Registry and kill-test rerun completed |
| Canonical registry | 1,595,720 unique nonempty IDs; zero event-ID anti-join gaps | PASS | Retain orphan flags and no-imputation policy |
| Demographic validity | 43 conflicts, 461 missing-ID rows, malformed fields | NEEDS WORK | Historical QA FAIL retained; no clinical subgroup inference |
| Renal feasibility | Full-scale aggregate query and matching rerun | PASS | Reproduce negative feasibility result |
| Vancomycin discovery | Case-insensitive description query yields zero | PASS | Bound claim to the actual search |
| Clinical validation | No supported SyntheticMass clinical signal | NOT APPLICABLE | Engineering-only scope; MIMIC-IV is a separate pathway |
| Code/reproducibility | Preserved stages, CLI, observed dependencies | PASS | Add configuration and non-overwrite controls |
| Tests | Fixture execution and source-preservation tests | PASS | See acceptance evidence |
| Documentation/governance | README, scope, provenance, limitations, release notes | PASS | Publish only reviewed code and aggregate evidence |
| GitHub publication | Repository creation unavailable until browser sign-in | BLOCKED | Local release prepared; no public URL claimed |

## Verified findings and discrepancies

All nonpatient table counts match the original manifest. Current patient counts match the repaired manifest and historical QA. The pre-repair backup retains the original 1,595,050 count. Original source-size totals are unchanged. The historical ratio is based on 15,915,116,630 source bytes and 1,827,048,827 original Parquet bytes; active repaired Parquet totals 1,801,835,388 bytes. Existing reports label sizes as GB but compute with 1024^3.

The original QA failed for missing patient IDs and orphan events. Reconciliation retains 1,854 event-linked IDs without a patient row and holds 43 conflicting demographic identities. It does not erase that QA result. The 1,593,823 `DEMOGRAPHICS_ELIGIBLE` IDs satisfy the registry conflict rule only; remaining schema defects still require investigation.

Read-only queries confirmed 1,913,439 numeric creatinine rows, a single value of 1.0, 389,788 represented patients, 361,193 with >=2 measurements, zero varying multi-measurement patients, and median population SD zero. The new execution matched every substantive field in both the saved registry and kill-test reports; only runtime and artifact paths were excluded from equality comparison.

## Public-release audit coverage

Scientific integrity: preserved negative result and explicit clinical boundary. Code quality: minimal, reviewable adapters and preserved originals. Reproducibility: tested fixtures and full-scale selective reproduction, with acquisition gaps disclosed. Documentation: evidence-linked README, architecture, limitations, citation, and portfolio wording. Privacy/security: aggregate allowlists, excluded record fragments, exact staged-byte checks, no data files admitted. Organization/Git hygiene: a separate curated Git root, no artificial historical commits. Large-file safety: 1 MiB per-file publication gate and data extension exclusions. Licensing/citation: MIT software license and CFF metadata without a fabricated DOI. Portfolio readability: evidence-based claims with limitations alongside achievements.

Exact local acceptance results and publication status are recorded in `results/qc/acceptance.json`; do not infer remote success from prepared release notes.
