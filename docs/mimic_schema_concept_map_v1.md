# MIMIC-IV v3.1 — Schema Inventory + Concept Mapping v1.0

Status: **DOCUMENTATION-VERIFIED; BIGQUERY EXECUTION PENDING**

This document records the Stage 6 schema/concept map before patient-level extraction. It is deliberately conservative: a field is marked **verified** only when supported by MIMIC-IV v3.1 documentation or the official MIT-LCP MIMIC code repository. BigQuery execution must confirm the exact live schema before cohort extraction.

## Version lock

- Resource: **MIMIC-IV v3.1**
- PhysioNet release date: 2024-10-11
- BigQuery versioned datasets documented by PhysioNet:
  - `physionet-data.mimiciv_v3_1_hosp`
  - `physionet-data.mimiciv_v3_1_icu`
- Important v3.1 change: `d_labitems` / `labevents` item IDs were corrected to be consistent with v2.2.
- Dates are deidentified by patient-specific shifts; intervals within a patient remain internally consistent, while calendar dates are not comparable across patients.

## Schema inventory

| Domain | Dataset/table | Key linkage/timing fields | Stage-6 use | Verification status |
|---|---|---|---|---|
| Patient | hosp.patients | subject_id | patient identity / demographics | docs-verified |
| Admission | hosp.admissions | subject_id, hadm_id, admit/discharge time fields | hospitalization linkage | docs-verified |
| Transfer | hosp.transfers | subject_id, hadm_id | location chronology | docs-verified |
| ICU stay | icu.icustays | subject_id, hadm_id, stay_id, intime, outtime | ICU linkage / windows | docs-verified |
| Laboratory dictionary | hosp.d_labitems | itemid + label/category/fluid metadata | concept verification | docs-verified |
| Laboratory events | hosp.labevents | subject_id, hadm_id, itemid, charttime, valuenum, valueuom | serum creatinine | code/docs-verified |
| Medication administration | hosp.emar | subject_id/hadm_id, medication, emar_id, emar_seq and event time fields | administration evidence | docs-verified at table/domain level; exact live columns pending |
| Medication detail | hosp.emar_detail | emar_id + formulary/dose details | dose/formulary detail | docs-verified at table/domain level; exact live columns pending |
| Prescription | hosp.prescriptions | subject_id/hadm_id, drug/medication descriptors | medication-order discovery | docs-verified |
| Pharmacy | hosp.pharmacy | prescription-linked pharmacy detail | route/frequency/dose support | docs-verified at domain level; exact live columns pending |
| ICU inputs | icu.inputevents | stay_id, itemid, starttime, endtime, amount | ICU IV medication/fluids | code/docs-verified |
| ICU outputs | icu.outputevents | stay_id, itemid, charttime, value | urine output | code/docs-verified |
| ICU charting | icu.chartevents | stay_id, itemid, charttime, value/valuenum | weight + CRRT/RRT concepts | code/docs-verified |
| ICU procedures | icu.procedureevents | stay_id, itemid, start/end time fields | RRT/IHD/CRRT evidence | code-verified |
| ICU item dictionary | icu.d_items | itemid + labels/categories | ICU concept verification | docs-verified |

## Concept map — frozen discovery targets

### Serum creatinine

Official MIT-LCP MIMIC code currently uses:

- Source: `hosp.labevents`
- Laboratory item ID: **50912**
- Meaning: blood chemistry creatinine
- Numeric requirement: `valuenum IS NOT NULL`
- Official chemistry concept excludes non-positive values and caps creatinine at 150 mg/dL as an outlier guard.
- Official KDIGO creatinine concept links `labevents` to ICU stays and searches from **7 days before ICU intime through ICU outtime**.
- Primary readiness analysis will independently profile units and values before adopting any outlier rule.

### KDIGO creatinine windows

Official MIT-LCP implementation:

- previous 48-hour minimum creatinine,
- previous 7-day minimum creatinine,
- Stage 1: rise >=0.3 mg/dL within 48 h or >=1.5x the 7-day baseline,
- Stage 2: >=2.0x the 7-day baseline,
- Stage 3: >=3.0x baseline, or creatinine >=4.0 mg/dL with an acute qualifying rise.

### Urine output

Official MIT-LCP urine-output concept uses `icu.outputevents` and the following item IDs:

`226559, 226560, 226561, 226584, 226563, 226564, 226565, 226567, 226557, 226558, 227488, 227489`.

The rate concept calculates 6 h, 12 h, and 24 h weight-normalized urine-output rates and uses time-varying weights.

### RRT / CRRT

The official MIT-LCP concepts identify dialysis evidence from `chartevents`, `inputevents`, and `procedureevents`. Examples include:

- CRRT mode: **227290**
- Hemodialysis output: **226499**
- Hemodialysis procedure: **225441**
- Dialysis–CRRT procedure: **225802**
- CVVHD: **225803**
- Peritoneal dialysis: **225805**
- CVVHDF: **225809**
- SCUF: **225955**

These IDs are discovery anchors, not a substitute for live `d_items` verification.

### Vancomycin

No single universal MIMIC medication table is sufficient. MIMIC documentation explicitly describes medication information as distributed across multiple sources. Stage 6 therefore uses hierarchical discovery:

1. `emar.medication` — preferred evidence of documented administration.
2. `emar_detail` — formulary/dose details linked by `emar_id`.
3. `prescriptions` — order-level drug/generic/NDC/GSN descriptors.
4. `pharmacy` — pharmacy-level route/frequency/dose support.
5. `inputevents` + `d_items` — ICU IV medication administrations.
6. Normalized text matching is used only after identifier/dictionary discovery and is audited explicitly.

**No substring-only vancomycin definition is allowed as the final exposure phenotype.**

## Linkage hierarchy

- Patient: `subject_id`
- Hospitalization: `hadm_id`
- ICU stay: `stay_id`
- eMAR event: `emar_id`
- Lab concept: `itemid`
- ICU concept: `itemid`

## Required live-schema checks before extraction

The file `analysis/mimic_v3_1/01_schema_inventory.sql` must be run first. It records table and column metadata without returning patient-level values.

Required pass conditions:

1. Both v3.1 datasets are visible.
2. Required tables exist.
3. Exact medication timestamp/dose/route columns are confirmed before exposure SQL is written.
4. `d_labitems` confirms the creatinine concept in the live v3.1 data.
5. `d_items` confirms urine-output and RRT/CRRT concept labels before use.

## Governance

Do not commit:
- patient-level rows,
- restricted query exports,
- credentials/tokens,
- identifiable or row-level MIMIC-derived datasets.

Allowed public outputs:
- SQL/code,
- schema metadata,
- concept IDs/labels,
- aggregate counts,
- QC summaries,
- publication-safe tables/figures.

## Freeze note

This is **Concept Mapping v1.0**. Any concept-ID or field change after live BigQuery inspection must be logged as a protocol amendment or a documented schema correction, not silently substituted.
