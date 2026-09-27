"""Preserved creatinine heterogeneity gate adapted to a configurable workspace."""
from pathlib import Path
import os
import duckdb, json, time

WORK=Path(os.environ["RXGUARD_WORK"])
DB=WORK/"RxGuard_SyntheticMass.duckdb"
OUT=WORK/"VAKI_3D1"
OUT.mkdir(parents=True,exist_ok=True)
started=time.time()
con=duckdb.connect(str(DB))

def cols(view):
    return [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {view}").fetchall()]
def norm(s):
    return str(s).replace("\ufeff","").strip().lower()
def find_col(view,candidates):
    m={norm(x):x for x in cols(view)}
    for c in candidates:
        if norm(c) in m:return m[norm(c)]
def q(name):
    return '"' + name.replace('"','""') + '"'

try:
    con.execute("SELECT 1 FROM silver_creatinine_events LIMIT 1")
except Exception:
    pid=find_col("bronze_observations",["PATIENT","PATIENT_ID","SUBJECT_ID"])
    date=find_col("bronze_observations",["DATE","DATETIME","START"])
    desc=find_col("bronze_observations",["DESCRIPTION","DISPLAY"])
    value=find_col("bronze_observations",["VALUE","RESULT"])
    units=find_col("bronze_observations",["UNITS","UNIT"])
    if not all([pid,date,desc,value]):
        raise RuntimeError("Could not detect required observation columns")
    con.execute(f"""
      CREATE OR REPLACE VIEW silver_creatinine_events AS
      SELECT trim({q(pid)}) patient_id,
             TRY_CAST({q(date)} AS TIMESTAMP) observation_time,
             TRY_CAST({q(value)} AS DOUBLE) creatinine_value,
             {q(units)+' AS units' if units else 'NULL::VARCHAR AS units'}
      FROM bronze_observations
      WHERE lower({q(desc)}) LIKE '%creatinine%'
        AND {q(pid)} IS NOT NULL AND trim({q(pid)})<>''
    """)

row=con.execute("""
SELECT COUNT(*),COUNT(creatinine_value),COUNT(DISTINCT creatinine_value),
MIN(creatinine_value),QUANTILE_CONT(creatinine_value,.01),QUANTILE_CONT(creatinine_value,.05),
QUANTILE_CONT(creatinine_value,.25),MEDIAN(creatinine_value),QUANTILE_CONT(creatinine_value,.75),
QUANTILE_CONT(creatinine_value,.95),QUANTILE_CONT(creatinine_value,.99),MAX(creatinine_value),
SUM(CASE WHEN creatinine_value=1.0 THEN 1 ELSE 0 END)
FROM silver_creatinine_events
""").fetchone()
keys=["rows_total","rows_numeric","unique_values","min","p01","p05","p25","median","p75","p95","p99","max","rows_equal_1"]
g=dict(zip(keys,row))
g["pct_equal_1"]=round(100*g["rows_equal_1"]/g["rows_numeric"],4) if g["rows_numeric"] else None

con.execute("""
CREATE OR REPLACE TABLE gold_creatinine_variability_killtest AS
SELECT patient_id,COUNT(*) measurement_count,COUNT(creatinine_value) numeric_count,
COUNT(DISTINCT creatinine_value) unique_numeric_values,MIN(creatinine_value) min_value,
MAX(creatinine_value) max_value,AVG(creatinine_value) mean_value,MEDIAN(creatinine_value) median_value,
STDDEV_POP(creatinine_value) sd_value,VAR_POP(creatinine_value) variance_value,
FIRST(creatinine_value ORDER BY observation_time) FILTER
 (WHERE creatinine_value IS NOT NULL AND observation_time IS NOT NULL) first_value,
LAST(creatinine_value ORDER BY observation_time) FILTER
 (WHERE creatinine_value IS NOT NULL AND observation_time IS NOT NULL) last_value,
date_diff('day',MIN(observation_time),MAX(observation_time)) followup_days
FROM silver_creatinine_events GROUP BY 1
""")
row=con.execute("""
SELECT COUNT(*),SUM(measurement_count>=2),SUM(measurement_count>=3),
SUM(measurement_count>=2 AND unique_numeric_values=1),SUM(unique_numeric_values>=2),
SUM(measurement_count>=2 AND unique_numeric_values>=2),SUM(sd_value>0),
MEDIAN(sd_value) FILTER (WHERE measurement_count>=2),
QUANTILE_CONT(sd_value,.95) FILTER (WHERE measurement_count>=2),
MEDIAN(max_value-min_value) FILTER (WHERE measurement_count>=2),
QUANTILE_CONT(max_value-min_value,.95) FILTER (WHERE measurement_count>=2),
SUM(first_value IS NOT NULL AND last_value IS NOT NULL AND first_value<>last_value),
SUM(first_value IS NOT NULL AND last_value IS NOT NULL AND first_value=last_value)
FROM gold_creatinine_variability_killtest
""").fetchone()
pkeys=["patients_total","patients_ge2","patients_ge3","ge2_constant","any_variation",
"ge2_with_variation","sd_positive","median_sd_ge2","p95_sd_ge2","median_range_ge2",
"p95_range_ge2","first_last_changed","first_last_same"]
p=dict(zip(pkeys,row))
p["pct_ge2_constant"]=round(100*p["ge2_constant"]/p["patients_ge2"],4) if p["patients_ge2"] else None
p["pct_ge2_with_variation"]=round(100*p["ge2_with_variation"]/p["patients_ge2"],4) if p["patients_ge2"] else None
den=(p["first_last_changed"] or 0)+(p["first_last_same"] or 0)
p["pct_first_last_changed"]=round(100*p["first_last_changed"]/den,4) if den else None

reasons=[]
if g["unique_values"]<=3:reasons.append("Extremely low number of unique creatinine values.")
if g["pct_equal_1"] is not None and g["pct_equal_1"]>=90:reasons.append("At least 90% of numeric creatinine rows equal 1.0.")
if p["pct_ge2_constant"] is not None and p["pct_ge2_constant"]>=90:reasons.append("At least 90% of longitudinal patients have no within-patient creatinine variation.")
if p["median_sd_ge2"] in (0,0.0,None):reasons.append("Median within-patient SD among patients with >=2 measurements is zero.")
go=[g["unique_values"]>=10,g["pct_equal_1"] is not None and g["pct_equal_1"]<80,
    p["pct_ge2_with_variation"] is not None and p["pct_ge2_with_variation"]>=20,
    p["median_sd_ge2"] is not None and p["median_sd_ge2"]>0]
decision=("CLINICAL_SIGNAL_GO_FOR_FURTHER_PHENOTYPE_TESTING" if all(go)
          else "ENGINEERING_ONLY_SYNTHETICMASS" if len(reasons)>=2
          else "INCONCLUSIVE_REQUIRES_REVIEW")

top=con.execute("""SELECT creatinine_value,COUNT(*) n,
ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM silver_creatinine_events WHERE creatinine_value IS NOT NULL),4) pct
FROM silver_creatinine_events WHERE creatinine_value IS NOT NULL GROUP BY 1 ORDER BY n DESC,1 LIMIT 20""").fetchall()
uv=con.execute("""SELECT unique_numeric_values,COUNT(*) FROM gold_creatinine_variability_killtest
GROUP BY 1 ORDER BY 1 LIMIT 30""").fetchall()
units=con.execute("SELECT units,COUNT(*) FROM silver_creatinine_events GROUP BY 1 ORDER BY 2 DESC").fetchall()
csv_path=OUT/"gold_creatinine_variability_killtest.csv"
pq_path=OUT/"gold_creatinine_variability_killtest.parquet"
con.execute(f"COPY gold_creatinine_variability_killtest TO '{str(csv_path).replace(chr(39),chr(39)*2)}' (HEADER)")
con.execute(f"COPY gold_creatinine_variability_killtest TO '{str(pq_path).replace(chr(39),chr(39)*2)}' (FORMAT PARQUET,COMPRESSION ZSTD)")
report={"step":"VAKI-3D.1","decision":decision,"decision_reasons":reasons,
"scientific_scope":"Integrity/variability kill-test only. Does not diagnose AKI.",
"global_distribution":g,"patient_variability":p,
"top_20_values":[{"value":x[0],"rows":x[1],"pct":x[2]} for x in top],
"unique_value_count_distribution":[{"unique_values_per_patient":x[0],"patients":x[1]} for x in uv],
"units":[{"units":x[0],"rows":x[1]} for x in units],"runtime_seconds":round(time.time()-started,3),
"artifacts":{"csv":str(csv_path),"parquet":str(pq_path),"output_folder":str(OUT)}}
(OUT/"VAKI_3D1_Creatinine_Distribution_Integrity_KillTest.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
print(json.dumps({"decision":decision,"reasons":reasons},indent=2))
con.close()
