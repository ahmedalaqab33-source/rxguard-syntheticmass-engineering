from pathlib import Path
import duckdb, json, time, statistics

WORK = Path(r"D:\DRxGuard_Data\RxGuard_Analytics")
DB = WORK / "RxGuard_SyntheticMass.duckdb"
OUT = WORK / "VAKI_3D1"
OUT.mkdir(parents=True, exist_ok=True)

started = time.time()
con = duckdb.connect(str(DB))

tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
views = {r[0] for r in con.execute("SHOW ALL TABLES").fetchall()} if False else set()

def cols(view):
    return [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {view}").fetchall()]

def norm(s):
    return str(s).replace("\ufeff","").strip().lower()

def find_col(view, candidates):
    m={norm(x):x for x in cols(view)}
    for c in candidates:
        if norm(c) in m:
            return m[norm(c)]
    return None

def q(name):
    return '"' + name.replace('"','""') + '"'

try:
    con.execute("SELECT 1 FROM silver_creatinine_events LIMIT 1")
except Exception:
    obs_pid=find_col("bronze_observations",["PATIENT","PATIENT_ID","SUBJECT_ID"])
    obs_date=find_col("bronze_observations",["DATE","DATETIME","START"])
    obs_desc=find_col("bronze_observations",["DESCRIPTION","DISPLAY"])
    obs_value=find_col("bronze_observations",["VALUE","RESULT"])
    obs_units=find_col("bronze_observations",["UNITS","UNIT"])
    if not all([obs_pid,obs_date,obs_desc,obs_value]):
        raise RuntimeError("Could not detect required observation columns.")
    qpid,qdate,qdesc,qval=q(obs_pid),q(obs_date),q(obs_desc),q(obs_value)
    qunits=q(obs_units) if obs_units else None
    con.execute(f"""
    CREATE OR REPLACE VIEW silver_creatinine_events AS
    SELECT
      trim({qpid}) AS patient_id,
      TRY_CAST({qdate} AS TIMESTAMP) AS observation_time,
      TRY_CAST({qval} AS DOUBLE) AS creatinine_value,
      {qunits + ' AS units' if qunits else 'NULL::VARCHAR AS units'}
    FROM bronze_observations
    WHERE lower({qdesc}) LIKE '%creatinine%'
      AND {qpid} IS NOT NULL AND trim({qpid})<>''
    """)

global_stats = con.execute("""
SELECT
  COUNT(*) AS rows_total,
  COUNT(creatinine_value) AS rows_numeric,
  COUNT(DISTINCT creatinine_value) AS unique_values,
  MIN(creatinine_value) AS min_value,
  QUANTILE_CONT(creatinine_value,0.01) AS p01,
  QUANTILE_CONT(creatinine_value,0.05) AS p05,
  QUANTILE_CONT(creatinine_value,0.25) AS p25,
  MEDIAN(creatinine_value) AS median_value,
  QUANTILE_CONT(creatinine_value,0.75) AS p75,
  QUANTILE_CONT(creatinine_value,0.95) AS p95,
  QUANTILE_CONT(creatinine_value,0.99) AS p99,
  MAX(creatinine_value) AS max_value,
  SUM(CASE WHEN creatinine_value=1.0 THEN 1 ELSE 0 END) AS rows_equal_1
FROM silver_creatinine_events
""").fetchone()

keys = ["rows_total","rows_numeric","unique_values","min","p01","p05","p25","median","p75","p95","p99","max","rows_equal_1"]
g = dict(zip(keys,global_stats))
g["pct_equal_1"] = round(100*g["rows_equal_1"]/g["rows_numeric"],4) if g["rows_numeric"] else None

top_values = con.execute("""
SELECT creatinine_value, COUNT(*) AS n,
       ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM silver_creatinine_events WHERE creatinine_value IS NOT NULL),4) AS pct
FROM silver_creatinine_events
WHERE creatinine_value IS NOT NULL
GROUP BY 1
ORDER BY n DESC, creatinine_value
LIMIT 20
""").fetchall()

con.execute("""
CREATE OR REPLACE TABLE gold_creatinine_variability_killtest AS
SELECT
  patient_id,
  COUNT(*) AS measurement_count,
  COUNT(creatinine_value) AS numeric_count,
  COUNT(DISTINCT creatinine_value) AS unique_numeric_values,
  MIN(creatinine_value) AS min_value,
  MAX(creatinine_value) AS max_value,
  AVG(creatinine_value) AS mean_value,
  MEDIAN(creatinine_value) AS median_value,
  STDDEV_POP(creatinine_value) AS sd_value,
  VAR_POP(creatinine_value) AS variance_value,
  FIRST(creatinine_value ORDER BY observation_time)
     FILTER (WHERE creatinine_value IS NOT NULL AND observation_time IS NOT NULL) AS first_value,
  LAST(creatinine_value ORDER BY observation_time)
     FILTER (WHERE creatinine_value IS NOT NULL AND observation_time IS NOT NULL) AS last_value,
  date_diff('day',MIN(observation_time),MAX(observation_time)) AS followup_days
FROM silver_creatinine_events
GROUP BY 1
""")

patient_stats = con.execute("""
SELECT
  COUNT(*) AS patients_total,
  SUM(CASE WHEN measurement_count>=2 THEN 1 ELSE 0 END) AS patients_ge2,
  SUM(CASE WHEN measurement_count>=3 THEN 1 ELSE 0 END) AS patients_ge3,
  SUM(CASE WHEN measurement_count>=2 AND unique_numeric_values=1 THEN 1 ELSE 0 END) AS ge2_constant,
  SUM(CASE WHEN unique_numeric_values>=2 THEN 1 ELSE 0 END) AS any_variation,
  SUM(CASE WHEN measurement_count>=2 AND unique_numeric_values>=2 THEN 1 ELSE 0 END) AS ge2_with_variation,
  SUM(CASE WHEN sd_value>0 THEN 1 ELSE 0 END) AS sd_positive,
  MEDIAN(sd_value) FILTER (WHERE measurement_count>=2) AS median_sd_ge2,
  QUANTILE_CONT(sd_value,0.95) FILTER (WHERE measurement_count>=2) AS p95_sd_ge2,
  MEDIAN(max_value-min_value) FILTER (WHERE measurement_count>=2) AS median_range_ge2,
  QUANTILE_CONT(max_value-min_value,0.95) FILTER (WHERE measurement_count>=2) AS p95_range_ge2,
  SUM(CASE WHEN first_value IS NOT NULL AND last_value IS NOT NULL AND first_value<>last_value THEN 1 ELSE 0 END) AS first_last_changed,
  SUM(CASE WHEN first_value IS NOT NULL AND last_value IS NOT NULL AND first_value=last_value THEN 1 ELSE 0 END) AS first_last_same
FROM gold_creatinine_variability_killtest
""").fetchone()

pkeys = ["patients_total","patients_ge2","patients_ge3","ge2_constant","any_variation","ge2_with_variation","sd_positive","median_sd_ge2","p95_sd_ge2","median_range_ge2","p95_range_ge2","first_last_changed","first_last_same"]
p = dict(zip(pkeys,patient_stats))

p["pct_ge2_constant"] = round(100*p["ge2_constant"]/p["patients_ge2"],4) if p["patients_ge2"] else None
p["pct_ge2_with_variation"] = round(100*p["ge2_with_variation"]/p["patients_ge2"],4) if p["patients_ge2"] else None
den = (p["first_last_changed"] or 0)+(p["first_last_same"] or 0)
p["pct_first_last_changed"] = round(100*p["first_last_changed"]/den,4) if den else None

variation_value_counts = con.execute("""
SELECT unique_numeric_values, COUNT(*) AS patients
FROM gold_creatinine_variability_killtest
GROUP BY 1
ORDER BY 1
LIMIT 30
""").fetchall()

units = []
try:
    units = con.execute("""
    SELECT units, COUNT(*) n
    FROM silver_creatinine_events
    GROUP BY 1 ORDER BY n DESC
    """).fetchall()
except Exception:
    pass

reasons=[]
if g["unique_values"] <= 3:
    reasons.append("Extremely low number of unique creatinine values.")
if g["pct_equal_1"] is not None and g["pct_equal_1"] >= 90:
    reasons.append("At least 90% of numeric creatinine rows equal 1.0.")
if p["pct_ge2_constant"] is not None and p["pct_ge2_constant"] >= 90:
    reasons.append("At least 90% of longitudinal patients have no within-patient creatinine variation.")
if p["median_sd_ge2"] in (0,0.0,None):
    reasons.append("Median within-patient SD among patients with >=2 measurements is zero.")

go_conditions = [
    g["unique_values"] >= 10,
    g["pct_equal_1"] is not None and g["pct_equal_1"] < 80,
    p["pct_ge2_with_variation"] is not None and p["pct_ge2_with_variation"] >= 20,
    p["median_sd_ge2"] is not None and p["median_sd_ge2"] > 0,
]

if all(go_conditions):
    decision="CLINICAL_SIGNAL_GO_FOR_FURTHER_PHENOTYPE_TESTING"
elif len(reasons)>=2:
    decision="ENGINEERING_ONLY_SYNTHETICMASS"
else:
    decision="INCONCLUSIVE_REQUIRES_REVIEW"

csv_path = OUT/"gold_creatinine_variability_killtest.csv"
pq_path = OUT/"gold_creatinine_variability_killtest.parquet"
con.execute(f"COPY gold_creatinine_variability_killtest TO '{str(csv_path).replace(chr(39),chr(39)*2)}' (HEADER, DELIMITER ',')")
con.execute(f"COPY gold_creatinine_variability_killtest TO '{str(pq_path).replace(chr(39),chr(39)*2)}' (FORMAT PARQUET, COMPRESSION ZSTD)")

report={
    "step":"VAKI-3D.1",
    "decision":decision,
    "decision_reasons":reasons,
    "scientific_scope":"Integrity/variability kill-test only. Does not diagnose AKI.",
    "global_distribution":g,
    "patient_variability":p,
    "top_20_values":[{"value":r[0],"rows":r[1],"pct":r[2]} for r in top_values],
    "unique_value_count_distribution":[{"unique_values_per_patient":r[0],"patients":r[1]} for r in variation_value_counts],
    "units":[{"units":r[0],"rows":r[1]} for r in units],
    "runtime_seconds":round(time.time()-started,3),
    "artifacts":{"csv":str(csv_path),"parquet":str(pq_path),"output_folder":str(OUT)}
}
json_path=OUT/"VAKI_3D1_Creatinine_Distribution_Integrity_KillTest.json"
json_path.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")

lines=[
    "="*80,
    "RXGUARD VAKI-3D.1 - CREATININE DISTRIBUTION INTEGRITY KILL-TEST",
    "="*80,
    f"DECISION                              = {decision}",
    "",
    "GLOBAL DISTRIBUTION",
    "-"*80,
]
for k,v in g.items():
    lines.append(f"{k.upper():38s} = {v}")
lines += ["","PATIENT-LEVEL VARIABILITY","-"*80]
for k,v in p.items():
    lines.append(f"{k.upper():38s} = {v}")
lines += ["","TOP 20 CREATININE VALUES","-"*80]
for value,n,pct in top_values:
    lines.append(f"VALUE={str(value):12s} ROWS={n:12,d} PCT={pct}")
lines += ["","DECISION REASONS","-"*80]
if reasons:
    for r in reasons:
        lines.append(" - "+r)
else:
    lines.append(" - No automatic failure reason triggered.")
lines += [
    "",
    "SCIENTIFIC INTERPRETATION",
    "-"*80,
    "This test evaluates whether SyntheticMass contains sufficient creatinine heterogeneity",
    "for further renal phenotype development. It does NOT diagnose AKI or establish clinical validity.",
    "="*80,
    f"JSON REPORT = {json_path}",
    f"OUTPUT FOLDER = {OUT}",
    "="*80
]
txt_path=OUT/"VAKI_3D1_Creatinine_Distribution_Integrity_KillTest.txt"
txt_path.write_text("\n".join(lines),encoding="utf-8")

print("\n".join(lines))
con.close()
