# Data provenance and governance

Local evidence contains 12 CSV batch folders with labels dated May 24–28, 2017 and 108 CSV files. The associated FHIR archive is named `synthea_1m_fhir_3_0_May_24.tar.gz`. These labels are consistent with the historical SyntheticMass distribution, but filenames alone do not establish exact generator version, seed, original download date, or identity with a currently hosted archive.

[Synthea's official downloads page](https://synthetichealth.github.io/downloads.html) identifies SyntheticMass as Synthea-generated data and provides historical downloads. The separate FHIR corpus was inventoried by size only; no FHIR-to-CSV record equivalence is claimed. This audit's engineering findings concern the CSV-derived analytical branch.

The historical ingestion manifest records SHA-256 digests for all 108 source CSVs. A sanitized manifest retains those hashes, batch labels, sizes, and row counts; it omits private paths and malformed source-derived column labels. Source bytes still total 15,915,116,630. Full source-file rehashing was not required for lightweight verification and is not claimed.

`source_manifest.json` traces published code and aggregate extracts to local original SHA-256 digests. Original code and evidence remain unchanged. Aggregate extracts are explicitly transformed copies, not byte-identical report replacements. The patient QA's gender distribution contains source record fragments and is excluded completely; only allowlisted aggregate fields are published.

## Publication boundary

Publish only the reviewed files in this repository. Exclude all raw CSV/FHIR, archived datasets, DuckDB databases, Parquet, patient-level kill-test and atlas exports, original QA distributions, local logs, virtual environments, credentials, and unrelated manuscripts/CVs/signed documents. Even synthetic identifiers and addresses are omitted. No claim is made that scanning alone proves privacy: manual selection and aggregate-only review are the primary controls.

MIMIC-IV is outside this release. Do not add restricted clinical data to this repository or its issue tracker. Dataset licensing is separate from the software MIT license. The exact local download receipt and upstream archive checksum were not recovered, so exact source acquisition remains a documented reproducibility limitation.
