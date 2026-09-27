# Reproducibility guide

## Environment and execution order

Install the project in a separate virtual environment using the README commands. The original environment is not modified. Python plus DuckDB is sufficient; the `requirements.txt` pin reflects the observed successful local run.

For an existing Parquet tree, provide table directories such as `patients/batch=.../patients.parquet`, `observations/batch=.../observations.parquet`, `encounters/batch=.../encounters.parquet`, and `medications/batch=.../medications.parquet`. The CLI admits the nine original table names, excludes `patients_PRE_REPAIR_BACKUP`, and requires the four core tables.

For CSVs, preserve batch directories beginning with `output_`; table names derive from CSV filename stems. Do not combine unrelated CSV files beneath the source root. The inherited ingestion expects one table file per batch and does not resolve duplicate table/batch destinations. Validate source layout before running.

Execution order is:

1. CSV ingestion and manifest (CSV route only).
2. Explicit patient parsing repair and retained original Parquet backup (CSV route only).
3. Canonical registry and demographic-use restrictions.
4. Creatinine variability kill-test and private outputs.

The CLI refuses existing destinations and overlapping input/output paths. To retry a failure, use another new destination; never overwrite the failed evidence. Do not invoke archived legacy scripts or stage modules directly against the canonical source.

## Output interpretation

`reports/VAKI_3C2_Canonical_Patient_Registry_Linkage_Reconciliation.json` records identifier classes and restrictions. `VAKI_3D1/VAKI_3D1_Creatinine_Distribution_Integrity_KillTest.json` records distribution, variation, and the decision. Runtime/path fields vary across runs. Patient-level CSV/Parquet, database, and execution logs are private local artifacts, excluded from publication.

The historical patient QA stage failed before reconciliation and still flags genuine source problems. Registry success must not replace that result. Check `results/summaries/patient_qa.json` and the limitations before interpreting any demographic summaries.

Run the independent aggregate checks against an existing complete project root:

```sh
python scripts/verify_local.py --project-root /path/to/DRxGuard_Data --output .local/verification-01.json
```

This utility opens the original database read-only and queries relocated Parquet through an in-memory connection. It requires the historical manifest, registry tables, and pre-repair backup to reproduce this audit's full evidence context. It refuses to overwrite its evidence output.

## What was actually reproduced

The acceptance audit read the original database in read-only mode, mounted relocated Parquet in memory, verified every table count, inspected schema variation, checked registry uniqueness/empty IDs, and queried encounter/observation anti-joins. A new database then reran the preserved registry and kill-test stages over full-scale current Parquet. All non-runtime registry results and all substantive kill-test report fields matched the saved originals. Evidence is in `results/qc/reproduction_comparison.json`.

The fixture suite exercises actual CSV ingestion, patient repair, registry conflict and orphan policies, variability decisions, and non-overwrite controls. Source-preservation checks compare byte hashes and analytic ASTs. No full raw conversion rerun or new clinical analysis is claimed.

## Publication checks

After reviewing changes, run `python scripts/audit_release.py` in a Git checkout. It checks the exact staged file set when staging exists and otherwise the tracked set, rejects data extensions/large files/path or identifier patterns, verifies legacy provenance, and exercises ignore rules with sample excluded paths. Review staged diffs manually as well. New or changed aggregate JSON must be inspected for record-level content before publication.
