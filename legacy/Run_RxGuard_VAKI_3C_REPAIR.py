from pathlib import Path
import duckdb, json, time, shutil

CSV_ROOT = Path(r"D:\DRxGuard_Data\RxGuard_CSV_Batches")
WORK = Path(r"D:\DRxGuard_Data\RxGuard_Analytics")
PARQUET_PATIENTS = WORK / "parquet" / "patients"
DB = WORK / "RxGuard_SyntheticMass.duckdb"
REPORTS = WORK / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

started = time.time()
patient_csvs = sorted(CSV_ROOT.rglob("patients.csv"))
if not patient_csvs:
    raise SystemExit("ERROR: No patients.csv files found.")

print("=" * 72)
print("RXGUARD VAKI-3C REPAIR — PATIENT TABLE + RENAL COHORT AUDIT")
print("=" * 72)
print("PATIENT CSV FILES FOUND =", len(patient_csvs))

if PARQUET_PATIENTS.exists():
    backup = WORK / "parquet" / "patients_PRE_REPAIR_BACKUP"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.move(str(PARQUET_PATIENTS), str(backup))
    print("BACKUP CREATED =", backup)

PARQUET_PATIENTS.mkdir(parents=True, exist_ok=True)
manifest = []

for idx, csv_path in enumerate(patient_csvs, 1):
    batch = next((p for p in csv_path.parts if p.lower().startswith("output_")), f"batch_{idx}")
    out_dir = PARQUET_PATIENTS / f"batch={batch}"
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / "patients.parquet"
    print(f"[{idx}/{len(patient_csvs)}] Rebuilding {batch}")
    con_tmp = duckdb.connect()
    src = str(csv_path).replace("'", "''")
    dst = str(pq).replace("'", "''")
    con_tmp.execute(f"""
        COPY (
            SELECT * FROM read_csv(
                '{src}',
                delim=',',
                header=true,
                quote='"',
                escape='"',
                all_varchar=true,
                strict_mode=false,
                null_padding=true
            )
        )
        TO '{dst}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    schema = [r[0] for r in con_tmp.execute(f"DESCRIBE SELECT * FROM read_parquet('{dst}')").fetchall()]
    row_count = con_tmp.execute(f"SELECT COUNT(*) FROM read_parquet('{dst}')").fetchone()[0]
    con_tmp.close()
    normalized = [x.replace("\ufeff","").strip() for x in schema]
    if "ID" not in normalized:
        raise RuntimeError(f"ID still not detected after explicit CSV parsing. Schema={schema}")
    manifest.append({"batch":batch,"source":str(csv_path),"parquet":str(pq),"rows":row_count,"schema":schema})

con = duckdb.connect(str(DB))
glob_path = str(PARQUET_PATIENTS / "batch=*" / "*.parquet").replace("'", "''")
con.execute(f"""
CREATE OR REPLACE VIEW bronze_patients AS
SELECT * FROM read_parquet('{glob_path}', union_by_name=true, hive_partitioning=true)
""")

def cols(view): return [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {view}").fetchall()]
def norm(s): return str(s).replace("\ufeff","").strip().lower()
def find_col(view,cands):
    m={norm(x):x for x in cols(view)}
    for c in cands:
        if norm(c) in m: return m[norm(c)]
    return None
def q(name): return '"' + name.replace('"','""') + '"'

patient_id=find_col("bronze_patients",["ID","PATIENT","PATIENT_ID"])
obs_patient=find_col("bronze_observations",["PATIENT","PATIENT_ID","SUBJECT_ID"])
obs_desc=find_col("bronze_observations",["DESCRIPTION","DISPLAY"])
enc_id=find_col("bronze_encounters",["ID","ENCOUNTER","ENCOUNTER_ID"])

print("\nPATIENT COLUMNS AFTER REPAIR =", cols("bronze_patients"))
print("DETECTED PATIENT KEY =", repr(patient_id))

if not patient_id or not obs_patient or not obs_desc:
    raise RuntimeError("Required keys still not detected after repair.")

q_pid,q_opid,q_desc=q(patient_id),q(obs_patient),q(obs_desc)
q_eid=q(enc_id) if enc_id else None

patient_rows=con.execute("SELECT COUNT(*) FROM bronze_patients").fetchone()[0]
unique_patients=con.execute(f"SELECT COUNT(DISTINCT {q_pid}) FROM bronze_patients WHERE {q_pid} IS NOT NULL").fetchone()[0]
unique_encounters=con.execute(f"SELECT COUNT(DISTINCT {q_eid}) FROM bronze_encounters WHERE {q_eid} IS NOT NULL").fetchone()[0] if q_eid else None
cr_where=f"lower({q_desc}) LIKE '%creatinine%'"
creatinine_rows=con.execute(f"SELECT COUNT(*) FROM bronze_observations WHERE {cr_where}").fetchone()[0]
patients_with_cr=con.execute(f"SELECT COUNT(DISTINCT {q_opid}) FROM bronze_observations WHERE {cr_where} AND {q_opid} IS NOT NULL").fetchone()[0]
depth=con.execute(f"""
WITH cr AS (
 SELECT {q_opid} AS patient_id, COUNT(*) AS n
 FROM bronze_observations
 WHERE {cr_where} AND {q_opid} IS NOT NULL
 GROUP BY 1
)
SELECT COUNT(*),
SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END),
SUM(CASE WHEN n>=3 THEN 1 ELSE 0 END),
SUM(CASE WHEN n>=5 THEN 1 ELSE 0 END),
SUM(CASE WHEN n>=10 THEN 1 ELSE 0 END),
MEDIAN(n), MAX(n)
FROM cr
""").fetchone()

coverage=round(100*patients_with_cr/unique_patients,2) if unique_patients else None
report={
 "patient_csv_files":len(patient_csvs),
 "patient_rows":patient_rows,
 "unique_patients":unique_patients,
 "duplicate_patient_rows":patient_rows-unique_patients,
 "unique_encounters":unique_encounters,
 "creatinine_rows":creatinine_rows,
 "patients_with_creatinine":patients_with_cr,
 "renal_coverage_pct":coverage,
 "patients_ge1":depth[0],
 "patients_ge2":depth[1],
 "patients_ge3":depth[2],
 "patients_ge5":depth[3],
 "patients_ge10":depth[4],
 "median_cr_per_patient":depth[5],
 "max_cr_per_patient":depth[6],
 "runtime_seconds":round(time.time()-started,3)
}
json_path=REPORTS/"VAKI_3C_REPAIRED_Renal_Cohort_Audit.json"
manifest_path=REPORTS/"VAKI_3C_REPAIRED_Patient_Manifest.json"
json_path.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
manifest_path.write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")

print("\n"+"="*72)
print("RXGUARD VAKI-3C — REPAIRED RENAL COHORT RESULTS")
print("="*72)
for k,v in report.items(): print(f"{k.upper():32s} = {v}")
print("="*72)
print("AUDIT REPORT =",json_path)
con.close()
