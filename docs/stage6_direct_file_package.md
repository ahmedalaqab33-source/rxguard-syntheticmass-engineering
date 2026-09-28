# Stage 6 — Direct-file execution package

This package is the fallback execution path when BigQuery authorization is unavailable while authorized PhysioNet MIMIC-IV v3.1 file access is confirmed.

## Design principles

- Use only MIMIC-IV v3.1.
- Do not request access again.
- Do not download the 9.8 GB ZIP as the first step.
- Download only the files needed for the current analysis stage.
- Keep all restricted files outside Git.
- Never store credentials in source code, shell history, logs, or Git.
- Produce aggregate, publication-safe outputs only.

## Local restricted-data layout

The scripts default to:

```text
../data_restricted/mimiciv_3_1/
├── SHA256SUMS.txt
├── hosp/
│   ├── d_labitems.csv.gz
│   └── labevents.csv.gz
└── icu/
    └── ...
```

The directory is intentionally outside the repository root when the repository is in its usual location.

## Phase A — credential-safe targeted download

Run:

```bash
python analysis/mimic_v3_1/direct_file_download.py --phase creatinine
```

The script:
1. prompts for the PhysioNet username;
2. requests the password with a masked `getpass` prompt;
3. downloads `SHA256SUMS.txt`;
4. downloads only:
   - `hosp/d_labitems.csv.gz`
   - `hosp/labevents.csv.gz`
5. validates gzip integrity;
6. verifies SHA-256 when the official checksum can be resolved;
7. writes only non-sensitive metadata to `results/mimic_v3_1/data_access_manifest.json`.

The password is never printed or written to disk.

## Phase B — creatinine concept profile

Run:

```bash
python analysis/mimic_v3_1/05_direct_creatinine_profile.py
```

This verifies the live dictionary and profiles itemid 50912 using DuckDB directly over the compressed CSV. It writes aggregate-only JSON:

- `results/mimic_v3_1/creatinine_concept_profile.json`
- `results/mimic_v3_1/creatinine_units.json`
- `results/mimic_v3_1/creatinine_concept_qc.json`

PASS requires:
- itemid 50912 is present in the live MIMIC-IV v3.1 dictionary;
- its label is creatinine-related;
- numeric data are present;
- units are explicitly profiled.

No longitudinal-readiness conclusion is made at this step.

## Phase C — longitudinal creatinine readiness

Only after Phase B passes:

```bash
python analysis/mimic_v3_1/06_direct_creatinine_longitudinal.py
```

The script computes aggregate-only readiness metrics using time-respecting comparisons:
- subjects with >=1, >=2, >=3 SCr measurements;
- measurement count distribution;
- any within-patient SCr change;
- zero within-patient variation;
- within-patient range distribution;
- 48-hour prior-comparison eligibility;
- 7-day prior-comparison eligibility;
- KDIGO-creatinine evaluability;
- counts meeting >=0.3 mg/dL within 48 h or >=1.5x prior 7-day minimum.

Patient-level working tables exist only inside DuckDB execution memory/temp space and are not exported.

## Phase D — later targeted downloads

After creatinine readiness passes, run:

```bash
python analysis/mimic_v3_1/direct_file_download.py --phase renal-icu
python analysis/mimic_v3_1/direct_file_download.py --phase vancomycin
```

`renal-icu` targets:
- `icu/d_items.csv.gz`
- `icu/icustays.csv.gz`
- `icu/outputevents.csv.gz`
- `icu/inputevents.csv.gz`
- `icu/chartevents.csv.gz`
- `icu/procedureevents.csv.gz`

`vancomycin` targets:
- `hosp/emar.csv.gz`
- `hosp/emar_detail.csv.gz`
- `hosp/prescriptions.csv.gz`
- `hosp/pharmacy.csv.gz`
- plus ICU `d_items/inputevents` if not already present.

## Fail-fast rules

Stop if:
- authentication fails;
- a requested official file returns HTTP 401/403/404;
- gzip integrity fails;
- an available official SHA-256 checksum does not match;
- disk free space is lower than the script's safety estimate;
- itemid 50912 cannot be verified from the live dictionary.

Do not weaken a frozen scientific gate to force progression.

## Git policy

Never commit raw MIMIC files. The repository's deny-by-default `.gitignore` already excludes compressed files, CSV, Parquet, and data directories. The direct-file scripts also refuse to place downloads inside the Git worktree by default.

Commit only code, documentation, aggregate JSON/QC, and publication-safe outputs.
