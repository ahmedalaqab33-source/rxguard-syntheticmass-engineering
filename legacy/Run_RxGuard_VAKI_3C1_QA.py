from pathlib import Path
import duckdb
import json
import time
from collections import Counter

WORK = Path(r"D:\DRxGuard_Data\RxGuard_Analytics")
DB = WORK / "RxGuard_SyntheticMass.duckdb"
OUT = WORK / "reports"
OUT.mkdir(parents=True, exist_ok=True)

started = time.time()
con = duckdb.connect(str(DB))

def cols(view):
    return [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {view}").fetchall()]

def norm(s):
    return str(s).replace("\ufeff","").strip().lower()

def find_col(view, candidates):
    m = {norm(x): x for x in cols(view)}
    for c in candidates:
        if norm(c) in m:
            return m[norm(c)]
    return None

def q(name):
    return '"' + name.replace('"','""') + '"'

patient_cols = cols("bronze_patients")
obs_cols = cols("bronze_observations")
enc_cols = cols("bronze_encounters")

pid = find_col("bronze_patients", ["ID","PATIENT","PATIENT_ID"])
obs_pid = find_col("bronze_observations", ["PATIENT","PATIENT_ID","SUBJECT_ID"])
enc_pid = find_col("bronze_encounters", ["PATIENT","PATIENT_ID","SUBJECT_ID"])
birth = find_col("bronze_patients", ["BIRTHDATE","DOB","DATE_OF_BIRTH"])
gender = find_col("bronze_patients", ["GENDER","SEX"])
race = find_col("bronze_patients", ["RACE"])
eth = find_col("bronze_patients", ["ETHNICITY"])

if not pid or not obs_pid:
    raise RuntimeError("Required patient linkage columns not detected.")

qpid = q(pid)
qopid = q(obs_pid)
qepid = q(enc_pid) if enc_pid else None

# Core duplicate audit
patient_rows = con.execute("SELECT COUNT(*) FROM bronze_patients").fetchone()[0]
unique_patients = con.execute(
    f"SELECT COUNT(DISTINCT {qpid}) FROM bronze_patients WHERE {qpid} IS NOT NULL"
).fetchone()[0]
missing_patient_ids = con.execute(
    f"SELECT COUNT(*) FROM bronze_patients WHERE {qpid} IS NULL OR trim({qpid})=''"
).fetchone()[0]

dup_summary = con.execute(f"""
SELECT
    COUNT(*) AS duplicated_ids,
    SUM(n-1) AS excess_duplicate_rows,
    MAX(n) AS max_rows_per_id
FROM (
    SELECT {qpid} AS patient_id, COUNT(*) AS n
    FROM bronze_patients
    WHERE {qpid} IS NOT NULL
    GROUP BY 1
    HAVING COUNT(*) > 1
)
""").fetchone()

duplicate_ids = dup_summary[0] or 0
excess_duplicate_rows = dup_summary[1] or 0
max_rows_per_id = dup_summary[2] or 0

# Are duplicates exact rows or conflicting rows?
dup_conflict = con.execute(f"""
WITH d AS (
    SELECT {qpid} AS patient_id
    FROM bronze_patients
    WHERE {qpid} IS NOT NULL
    GROUP BY 1
    HAVING COUNT(*) > 1
),
x AS (
    SELECT p.*
    FROM bronze_patients p
    INNER JOIN d ON p.{qpid} = d.patient_id
)
SELECT COUNT(*) FROM x
""").fetchone()[0]

# Foreign-key linkage checks
obs_distinct_patients = con.execute(
    f"SELECT COUNT(DISTINCT {qopid}) FROM bronze_observations WHERE {qopid} IS NOT NULL"
).fetchone()[0]

orphan_obs_patients = con.execute(f"""
SELECT COUNT(*)
FROM (
    SELECT DISTINCT {qopid} AS patient_id
    FROM bronze_observations
    WHERE {qopid} IS NOT NULL
) o
LEFT JOIN (
    SELECT DISTINCT {qpid} AS patient_id
    FROM bronze_patients
    WHERE {qpid} IS NOT NULL
) p
ON o.patient_id = p.patient_id
WHERE p.patient_id IS NULL
""").fetchone()[0]

enc_distinct_patients = None
orphan_enc_patients = None
if qepid:
    enc_distinct_patients = con.execute(
        f"SELECT COUNT(DISTINCT {qepid}) FROM bronze_encounters WHERE {qepid} IS NOT NULL"
    ).fetchone()[0]
    orphan_enc_patients = con.execute(f"""
    SELECT COUNT(*)
    FROM (
        SELECT DISTINCT {qepid} AS patient_id
        FROM bronze_encounters
        WHERE {qepid} IS NOT NULL
    ) e
    LEFT JOIN (
        SELECT DISTINCT {qpid} AS patient_id
        FROM bronze_patients
        WHERE {qpid} IS NOT NULL
    ) p
    ON e.patient_id = p.patient_id
    WHERE p.patient_id IS NULL
    """).fetchone()[0]

# Patient schema irregularity
generic_cols = [c for c in patient_cols if c.lower().startswith("column")]
generic_nonnull = {}
for c in generic_cols:
    qc = q(c)
    n = con.execute(
        f"SELECT COUNT(*) FROM bronze_patients WHERE {qc} IS NOT NULL AND trim({qc}) <> ''"
    ).fetchone()[0]
    generic_nonnull[c] = n

# Demographic field completeness / domain checks
demographics = {}
for label, col in [("birthdate",birth),("gender",gender),("race",race),("ethnicity",eth)]:
    if col:
        qc=q(col)
        demographics[label] = {
            "column": col,
            "non_missing": con.execute(
                f"SELECT COUNT(*) FROM bronze_patients WHERE {qc} IS NOT NULL AND trim({qc})<>''"
            ).fetchone()[0],
            "distinct_values": con.execute(
                f"SELECT COUNT(DISTINCT {qc}) FROM bronze_patients WHERE {qc} IS NOT NULL AND trim({qc})<>''"
            ).fetchone()[0]
        }

# Birthdate parsing QC
birth_qc = None
if birth:
    qb=q(birth)
    birth_qc = con.execute(f"""
    SELECT
      COUNT(*) AS total_nonmissing,
      SUM(CASE WHEN TRY_CAST({qb} AS DATE) IS NULL THEN 1 ELSE 0 END) AS unparseable,
      MIN(TRY_CAST({qb} AS DATE)) AS min_date,
      MAX(TRY_CAST({qb} AS DATE)) AS max_date
    FROM bronze_patients
    WHERE {qb} IS NOT NULL AND trim({qb})<>''
    """).fetchone()

# Gender distribution
gender_distribution = None
if gender:
    qg=q(gender)
    gender_distribution = con.execute(f"""
    SELECT {qg}, COUNT(*) AS n
    FROM bronze_patients
    GROUP BY 1
    ORDER BY n DESC
    """).fetchall()

# Exact duplicate-row check using a stable row hash excluding hive batch
usable_cols = [c for c in patient_cols if c != "batch"]
hash_expr = " || '|' || ".join([f"coalesce(cast({q(c)} as varchar),'')" for c in usable_cols])
exact_dup_rows = con.execute(f"""
WITH x AS (
  SELECT {qpid} AS patient_id,
         md5({hash_expr}) AS row_hash
  FROM bronze_patients
  WHERE {qpid} IS NOT NULL
),
d AS (
  SELECT patient_id, row_hash, COUNT(*) n
  FROM x
  GROUP BY 1,2
  HAVING COUNT(*) > 1
)
SELECT COALESCE(SUM(n-1),0) FROM d
""").fetchone()[0]

conflicting_duplicate_rows = excess_duplicate_rows - exact_dup_rows

report = {
    "patient_columns": patient_cols,
    "patient_id_column": pid,
    "observation_patient_column": obs_pid,
    "encounter_patient_column": enc_pid,
    "patient_rows": patient_rows,
    "unique_patients": unique_patients,
    "missing_patient_ids": missing_patient_ids,
    "duplicated_patient_ids": duplicate_ids,
    "excess_duplicate_rows": excess_duplicate_rows,
    "exact_duplicate_rows": exact_dup_rows,
    "conflicting_duplicate_rows": conflicting_duplicate_rows,
    "max_rows_per_patient_id": max_rows_per_id,
    "distinct_observation_patients": obs_distinct_patients,
    "orphan_observation_patient_ids": orphan_obs_patients,
    "distinct_encounter_patients": enc_distinct_patients,
    "orphan_encounter_patient_ids": orphan_enc_patients,
    "generic_columns": generic_cols,
    "generic_column_nonmissing_counts": generic_nonnull,
    "demographics": demographics,
    "birthdate_qc": birth_qc,
    "gender_distribution": gender_distribution,
    "runtime_seconds": round(time.time()-started,3)
}

# Gate logic
hard_fail = []
review = []

if missing_patient_ids > 0:
    hard_fail.append("Missing patient IDs in patient table.")
if orphan_obs_patients > 0:
    hard_fail.append("Observation patient IDs not found in patients table.")
if orphan_enc_patients not in (None,0):
    hard_fail.append("Encounter patient IDs not found in patients table.")
if conflicting_duplicate_rows > 0:
    review.append("Some duplicate patient IDs contain non-identical rows.")
if any(v > 0 for v in generic_nonnull.values()):
    review.append("Generic column23+ fields contain data; demographic use requires schema inspection.")

if hard_fail:
    gate = "FAIL"
elif review:
    gate = "PASS_WITH_REVIEW"
else:
    gate = "PASS"

report["qa_gate"] = gate
report["hard_fail_reasons"] = hard_fail
report["review_flags"] = review

json_path = OUT / "VAKI_3C1_Patient_Schema_Duplicate_Linkage_Audit.json"
txt_path = OUT / "VAKI_3C1_Patient_Schema_Duplicate_Linkage_Audit.txt"
json_path.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")

lines = [
    "="*74,
    "RXGUARD VAKI-3C.1 — PATIENT SCHEMA + DUPLICATE/LINKAGE AUDIT",
    "="*74,
    f"QA GATE                         = {gate}",
    f"PATIENT ROWS                    = {patient_rows:,}",
    f"UNIQUE PATIENTS                 = {unique_patients:,}",
    f"MISSING PATIENT IDs             = {missing_patient_ids:,}",
    f"DUPLICATED PATIENT IDs          = {duplicate_ids:,}",
    f"EXCESS DUPLICATE ROWS           = {excess_duplicate_rows:,}",
    f"EXACT DUPLICATE ROWS            = {exact_dup_rows:,}",
    f"CONFLICTING DUPLICATE ROWS      = {conflicting_duplicate_rows:,}",
    f"MAX ROWS PER PATIENT ID         = {max_rows_per_id}",
    "",
    f"DISTINCT OBS PATIENTS           = {obs_distinct_patients:,}",
    f"ORPHAN OBS PATIENT IDs          = {orphan_obs_patients:,}",
    f"DISTINCT ENCOUNTER PATIENTS     = {enc_distinct_patients}",
    f"ORPHAN ENCOUNTER PATIENT IDs    = {orphan_enc_patients}",
    "",
    f"GENERIC PATIENT COLUMNS         = {generic_cols}",
    "GENERIC NON-MISSING COUNTS:"
]
for k,v in generic_nonnull.items():
    lines.append(f"  {k:20s} = {v:,}")

lines += ["", "REVIEW FLAGS:"]
if review:
    for x in review: lines.append("  - " + x)
else:
    lines.append("  - None")

lines += ["", "HARD FAIL REASONS:"]
if hard_fail:
    for x in hard_fail: lines.append("  - " + x)
else:
    lines.append("  - None")

lines += [
    "",
    f"RUNTIME SECONDS                 = {report['runtime_seconds']}",
    "="*74,
    f"JSON REPORT = {json_path}",
    "="*74,
]
txt_path.write_text("\n".join(lines),encoding="utf-8")

print("\n".join(lines))
con.close()
