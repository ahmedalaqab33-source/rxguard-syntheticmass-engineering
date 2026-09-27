# Contributing

Contributions are welcome when they preserve the repository's research-integrity and data-governance boundaries.

## Before opening a pull request

1. Do not add raw SyntheticMass CSV/FHIR, Parquet, DuckDB files, patient-level extracts, credentials, restricted clinical data, or unrelated documents.
2. Keep clinical claims within the documented scope. Engineering feasibility must not be described as clinical validation.
3. Add or update tests for behavior changes.
4. Run:
   ```sh
   python -m pip install -e .
   python -m unittest discover -s tests -v
   python scripts/audit_release.py
   ```
5. Update documentation when interfaces, evidence interpretation, or limitations change.

## Code changes

Prefer small, reviewable changes. Preserve original analytical lineage under `legacy/`; supported execution belongs under `src/rxguard/`. Do not silently alter inherited scientific thresholds or identity-handling rules.

## Evidence changes

Only reviewed aggregate evidence belongs in `results/`. Any new result must state whether it is historical, newly reproduced, fixture-only, or clinically validated. Never infer clinical validity from software-test success.

## Commit and pull-request guidance

Use concise imperative commit messages and explain:
- what changed,
- why it changed,
- how it was tested,
- whether scientific interpretation changed,
- whether any data-governance boundary was affected.
