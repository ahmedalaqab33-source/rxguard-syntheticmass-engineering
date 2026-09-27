# Changelog

All notable changes to this repository are documented here.

The project follows a release-oriented research-software workflow: scientific scope, provenance, reproducibility, and safety limitations are versioned alongside code.

## [1.0.0] - 2026-09-27

### Added
- Reproducible SyntheticMass CSV-to-Parquet/DuckDB engineering pipeline.
- Canonical patient-identifier registry with explicit orphan and demographic-conflict handling.
- Renal creatinine heterogeneity kill-test with a preserved engineering-only stop decision.
- Fixture-based pipeline tests and provenance-preservation checks.
- Publication-safety audit that blocks data files, secrets, record-like identifiers, and oversized artifacts.
- Reviewed aggregate evidence under `results/`.
- Architecture, provenance, limitations, reproducibility, scientific-scope, and portfolio documentation.
- MIT license and CFF citation metadata.
- GitHub Actions continuous integration.

### Scientific boundary
This release does not claim AKI diagnosis, vancomycin nephrotoxicity estimation, clinical predictive performance, or MIMIC-IV validation.
