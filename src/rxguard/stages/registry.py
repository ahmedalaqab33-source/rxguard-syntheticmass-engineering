from pathlib import Path
import os
import duckdb, json, time

WORK = Path(os.environ["RXGUARD_WORK"])
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

pid = find_col("bronze_patients", ["ID","PATIENT","PATIENT_ID"])
opid = find_col("bronze_observations", ["PATIENT","PATIENT_ID","SUBJECT_ID"])
epid = find_col("bronze_encounters", ["PATIENT","PATIENT_ID","SUBJECT_ID"])

if not pid or not opid or not epid:
    raise RuntimeError(f"Patient linkage keys missing: patients={pid}, observations={opid}, encounters={epid}")

qpid, qopid, qepid = q(pid), q(opid), q(epid)

con.execute(f"""
CREATE OR REPLACE TABLE silver_patient_registry AS
WITH p AS (
    SELECT DISTINCT trim({qpid}) AS patient_id
    FROM bronze_patients
    WHERE {qpid} IS NOT NULL AND trim({qpid}) <> ''
),
o AS (
    SELECT DISTINCT trim({qopid}) AS patient_id
    FROM bronze_observations
    WHERE {qopid} IS NOT NULL AND trim({qopid}) <> ''
),
e AS (
    SELECT DISTINCT trim({qepid}) AS patient_id
    FROM bronze_encounters
    WHERE {qepid} IS NOT NULL AND trim({qepid}) <> ''
),
u AS (
    SELECT patient_id FROM p
    UNION
    SELECT patient_id FROM o
    UNION
    SELECT patient_id FROM e
)
SELECT
    u.patient_id,
    p.patient_id IS NOT NULL AS in_patients,
    o.patient_id IS NOT NULL AS in_observations,
    e.patient_id IS NOT NULL AS in_encounters,
    CASE
      WHEN p.patient_id IS NOT NULL AND o.patient_id IS NOT NULL AND e.patient_id IS NOT NULL THEN 'PRESENT_ALL_3'
      WHEN p.patient_id IS NOT NULL AND o.patient_id IS NOT NULL THEN 'PATIENTS_OBSERVATIONS'
      WHEN p.patient_id IS NOT NULL AND e.patient_id IS NOT NULL THEN 'PATIENTS_ENCOUNTERS'
      WHEN o.patient_id IS NOT NULL AND e.patient_id IS NOT NULL THEN 'OBSERVATIONS_ENCOUNTERS_NO_PATIENT_ROW'
      WHEN p.patient_id IS NOT NULL THEN 'PATIENTS_ONLY'
      WHEN o.patient_id IS NOT NULL THEN 'OBSERVATIONS_ONLY'
      WHEN e.patient_id IS NOT NULL THEN 'ENCOUNTERS_ONLY'
      ELSE 'UNKNOWN'
    END AS linkage_class
FROM u
LEFT JOIN p USING(patient_id)
LEFT JOIN o USING(patient_id)
LEFT JOIN e USING(patient_id)
""")

patient_cols = cols("bronze_patients")
core_candidates = ["BIRTHDATE","DEATHDATE","GENDER","RACE","ETHNICITY","MARITAL"]
core_cols = [find_col("bronze_patients",[c]) for c in core_candidates]
core_cols = [c for c in core_cols if c]

sig_expr = " || '|' || ".join([f"coalesce(trim(cast({q(c)} AS varchar)),'')" for c in core_cols]) if core_cols else "''"

con.execute(f"""
CREATE OR REPLACE TABLE silver_patient_identity_qc AS
SELECT
    trim({qpid}) AS patient_id,
    COUNT(*) AS patient_rows,
    COUNT(DISTINCT md5({sig_expr})) AS distinct_core_demographic_signatures,
    CASE
      WHEN COUNT(*) = 1 THEN 'UNIQUE_ROW'
      WHEN COUNT(DISTINCT md5({sig_expr})) = 1 THEN 'EXACT_OR_CORE_EQUIVALENT_DUPLICATE'
      ELSE 'CONFLICTING_DUPLICATE'
    END AS duplicate_status
FROM bronze_patients
WHERE {qpid} IS NOT NULL AND trim({qpid}) <> ''
GROUP BY 1
""")

con.execute("""
CREATE OR REPLACE VIEW silver_patient_registry_enriched AS
SELECT
    r.*,
    q.patient_rows,
    q.distinct_core_demographic_signatures,
    q.duplicate_status,
    CASE
      WHEN r.in_patients = FALSE THEN 'NO_DEMOGRAPHIC_ROW'
      WHEN q.duplicate_status = 'CONFLICTING_DUPLICATE' THEN 'DEMOGRAPHICS_HOLD'
      ELSE 'DEMOGRAPHICS_ELIGIBLE'
    END AS demographic_use_status
FROM silver_patient_registry r
LEFT JOIN silver_patient_identity_qc q USING(patient_id)
""")

summary = {}
summary["registry_total_ids"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry").fetchone()[0]
summary["present_all_3"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry WHERE linkage_class='PRESENT_ALL_3'").fetchone()[0]
summary["obs_enc_no_patient_row"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry WHERE linkage_class='OBSERVATIONS_ENCOUNTERS_NO_PATIENT_ROW'").fetchone()[0]
summary["observations_only"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry WHERE linkage_class='OBSERVATIONS_ONLY'").fetchone()[0]
summary["encounters_only"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry WHERE linkage_class='ENCOUNTERS_ONLY'").fetchone()[0]
summary["patients_only"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry WHERE linkage_class='PATIENTS_ONLY'").fetchone()[0]
summary["demographics_eligible"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry_enriched WHERE demographic_use_status='DEMOGRAPHICS_ELIGIBLE'").fetchone()[0]
summary["demographics_hold"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry_enriched WHERE demographic_use_status='DEMOGRAPHICS_HOLD'").fetchone()[0]
summary["no_demographic_row"] = con.execute("SELECT COUNT(*) FROM silver_patient_registry_enriched WHERE demographic_use_status='NO_DEMOGRAPHIC_ROW'").fetchone()[0]
summary["missing_patient_id_rows"] = con.execute(f"SELECT COUNT(*) FROM bronze_patients WHERE {qpid} IS NULL OR trim({qpid})=''").fetchone()[0]
summary["missing_observation_patient_id_rows"] = con.execute(f"SELECT COUNT(*) FROM bronze_observations WHERE {qopid} IS NULL OR trim({qopid})=''").fetchone()[0]
summary["missing_encounter_patient_id_rows"] = con.execute(f"SELECT COUNT(*) FROM bronze_encounters WHERE {qepid} IS NULL OR trim({qepid})=''").fetchone()[0]

desc = find_col("bronze_observations", ["DESCRIPTION","DISPLAY"])
if not desc:
    raise RuntimeError("Observation description column not detected.")
qdesc = q(desc)
cr_where = f"lower({qdesc}) LIKE '%creatinine%'"

summary["creatinine_rows"] = con.execute(f"SELECT COUNT(*) FROM bronze_observations WHERE {cr_where}").fetchone()[0]
summary["creatinine_unique_patients"] = con.execute(
    f"SELECT COUNT(DISTINCT trim({qopid})) FROM bronze_observations WHERE {cr_where} AND {qopid} IS NOT NULL AND trim({qopid})<>''"
).fetchone()[0]
summary["creatinine_patients_with_demographics"] = con.execute(f"""
SELECT COUNT(DISTINCT trim(o.{qopid}))
FROM bronze_observations o
JOIN silver_patient_registry_enriched r
  ON trim(o.{qopid}) = r.patient_id
WHERE {cr_where.replace(qdesc, 'o.'+qdesc)}
  AND r.demographic_use_status='DEMOGRAPHICS_ELIGIBLE'
""").fetchone()[0]

linkage_distribution = con.execute("""
SELECT linkage_class, COUNT(*) n
FROM silver_patient_registry
GROUP BY 1 ORDER BY n DESC
""").fetchall()

dup_distribution = con.execute("""
SELECT duplicate_status, COUNT(*) n
FROM silver_patient_identity_qc
GROUP BY 1 ORDER BY n DESC
""").fetchall()

summary["event_analytics_gate"] = "PASS_WITH_CANONICAL_REGISTRY"
summary["demographic_analytics_gate"] = "RESTRICT_TO_DEMOGRAPHICS_ELIGIBLE"
summary["runtime_seconds"] = round(time.time()-started,3)

report = {
    "summary": summary,
    "linkage_distribution": linkage_distribution,
    "duplicate_distribution": dup_distribution,
    "rules": {
        "patient_registry_definition": "Union of non-empty patient identifiers from patients, observations, and encounters.",
        "no_imputation": True,
        "orphan_policy": "Retain event-linked IDs in canonical registry; do not invent demographic rows.",
        "conflicting_duplicate_policy": "Hold demographics for conflicting duplicate patient IDs; do not arbitrarily choose a row.",
        "risk_atlas_policy": "Event/renal atlas may proceed using canonical IDs. Demographic subgroup analyses require DEMOGRAPHICS_ELIGIBLE."
    }
}

json_path = OUT / "VAKI_3C2_Canonical_Patient_Registry_Linkage_Reconciliation.json"
txt_path = OUT / "VAKI_3C2_Canonical_Patient_Registry_Linkage_Reconciliation.txt"
json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

lines = [
    "="*76,
    "RXGUARD VAKI-3C.2 — CANONICAL PATIENT REGISTRY + LINKAGE RECONCILIATION",
    "="*76,
]
for k,v in summary.items():
    lines.append(f"{k.upper():40s} = {v}")
lines += ["", "LINKAGE DISTRIBUTION:"]
for k,v in linkage_distribution:
    lines.append(f"  {k:45s} = {v:,}")
lines += ["", "DUPLICATE STATUS DISTRIBUTION:"]
for k,v in dup_distribution:
    lines.append(f"  {str(k):45s} = {v:,}")
lines += [
    "",
    "SCIENTIFIC POLICY:",
    "  - No patient identity or demographic values were imputed.",
    "  - Orphan event IDs are retained in the canonical registry with provenance flags.",
    "  - Conflicting patient duplicates are excluded from demographic subgroup analyses.",
    "  - Renal/event analytics can proceed using canonical patient IDs.",
    "="*76,
    f"REPORT = {json_path}",
    "="*76
]
txt_path.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
con.close()
