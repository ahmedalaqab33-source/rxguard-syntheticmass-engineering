# Architecture and preserved analytical lineage

The release separates source data, execution state, and publishable evidence. All scientific SQL is inherited from the existing project, with path configuration and a backup-overwrite guard added for safe execution.

| Stage | Source lineage | Behavior |
| --- | --- | --- |
| Ingestion | `VAKI_3B_build_bigdata.py` | Read CSV as VARCHAR, write ZSTD Parquet, record hashes/sizes/counts, create DuckDB views |
| Patient repair | `Run_RxGuard_VAKI_3C_REPAIR.py` | Explicit comma/quote parsing, permissive width handling, retain pre-repair Parquet backup |
| Registry | `Run_RxGuard_VAKI_3C2_Reconcile.py` | Union identifiers, detect core-demographic conflicts, apply use-status flags |
| Kill-test | Decoded `RxGuard_VAKI_3D1_KILL_TEST_ONE_FILE.bat` | Distribution and within-patient variation, preserved decision thresholds |

`legacy/` contains byte-preserved Python originals and the decoded kill-test payload. Original wrappers, older fixed/repair variants, atlas packages, and generated outputs remain at the canonical source location. Their existence is not treated as evidence that every variant succeeded. The atlas is excluded from the runnable release path because it is unnecessary for the engineering feasibility conclusion and could invite misleading demographic interpretation.

`src/rxguard/stages/` preserves analytical code rather than replacing it with a new framework. Only `WORK`/CSV-root bindings use environment variables; the CLI configures them internally. The patient-repair stage now refuses to delete an existing backup. Direct stage execution is unsupported: run the CLI so the new-workspace guard applies. No dependencies on R, notebooks, Polars, or PyArrow are introduced.

The Parquet reuse route creates a new database with views referencing the selected source directory; it does not modify or patch the relocated original database. Moving source files again requires another run. The CSV route constructs a self-contained local output layout except that stored paths remain absolute, an inherited limitation.

Registry linkage is deterministic for the same inputs. Runtime timings are not deterministic. Core demographic signatures retain the original MD5 of pipe-separated, null-coalesced fields; these are engineering comparison signatures, not cryptographic identity proofs. The implementation's delimiter/null equivalence and missing-core-field behavior remain limitations.
