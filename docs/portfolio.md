# Evidence-based portfolio wording

## CV

- Engineered and audited a SyntheticMass CSV-to-Parquet/DuckDB workflow spanning 64.65 million observations, 15.11 million encounters, and 4.78 million medication rows, with documented ingestion and schema limitations.
- Built and reproduced a 1.596-million-identifier canonical registry with explicit orphan retention, conflicting-demographic holds, and linkage QA; documented the unresolved patient parsing discrepancy.
- Applied a renal feasibility kill-test that exposed invariant creatinine and absent vancomycin description matches, supporting an engineering-only SyntheticMass conclusion and an evidence-driven pivot to MIMIC-IV clinical validation.

## LinkedIn project description

RxGuard's SyntheticMass engineering phase demonstrates large-scale health-data ingestion, DuckDB/Parquet analytics, reproducible execution, patient-identifier reconciliation, and data-quality gating. The audit reproduces registry and renal feasibility outputs while preserving historical evidence and documenting parser defects. A negative clinical feasibility result—constant creatinine and no vancomycin description matches—defined the boundary of valid use and motivated a separate MIMIC-IV validation pathway. No AKI or nephrotoxicity performance validation is claimed.

## GitHub About

SyntheticMass engineering audit: DuckDB/Parquet pipelines, patient linkage QA, and a reproducible renal feasibility stop. Engineering only; no clinical validation.

Suggested topics: `clinical-data-science`, `duckdb`, `parquet`, `data-engineering`, `reproducible-research`, `data-quality`, `clinical-pharmacy`, `synthetic-data`.

## Research portfolio

This project combines research software engineering with explicit limits on scientific interpretation. It preserves a large SyntheticMass analytical workflow, independently verifies its core engineering outputs, and packages reproducible software tests and source provenance. Canonical identifier reconciliation supports event linkage while retaining unresolved demographic restrictions. The renal kill-test demonstrated that scale and successful ingestion alone do not make a dataset suitable for clinical evaluation; the clinical pathway was therefore moved to MIMIC-IV, outside this release.
