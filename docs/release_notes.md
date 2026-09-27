# v1.0.0-engineering-audit

- Preserves the existing SyntheticMass ingestion and Parquet/DuckDB workflow with source hashes and reviewed aggregate evidence.
- Adds configurable execution in new workspaces, leaving canonical source data and historical outputs unchanged.
- Reproduces canonical registry/linkage QA and the full-scale renal feasibility kill-test.
- Documents 64,654,706 observations, 15,109,427 encounters, 4,781,956 medication rows, and the original-versus-repaired patient-row discrepancy.
- Retains the engineering-only conclusion: all tested creatinine values are 1.0 mg/dL, no longitudinal variation, and no vancomycin description matches.
- Records the evidence-driven pivot to MIMIC-IV. **MIMIC-IV clinical validation is not part of this release.**
- Adds meaningful software fixtures, preservation checks, dependency documentation, and publication-safety checks.

Known exceptions: unresolved patient parser/demographic defects; historical performance observations are not portable benchmarks; exact upstream download provenance and independent preregistration were not recovered. These limitations are explicit in the README and audit.
