"""CSV-to-Parquet ingestion for the supported reproducibility path."""
from pathlib import Path
import os
import duckdb
import json
import hashlib
import time

CSV_ROOT=Path(os.environ["RXGUARD_CSV_ROOT"])
WORK=Path(os.environ["RXGUARD_WORK"])
PARQUET=WORK/"parquet"
REPORTS=WORK/"reports"
DB=WORK/"RxGuard_SyntheticMass.duckdb"
PARQUET.mkdir(parents=True,exist_ok=True)
REPORTS.mkdir(parents=True,exist_ok=True)
started=time.time()

def quote(s):
    return str(s).replace("'","''")

files=sorted(CSV_ROOT.rglob("*.csv"))
if not files:
    raise RuntimeError("No CSV files found")

manifest=[]
seen=set()
for path in files:
    batch=next((p for p in path.parts if p.lower().startswith("output_")),None)
    table=path.stem.lower()
    if batch is None:
        raise RuntimeError(f"CSV outside output_ batch: {path.name}")
    key=(batch,table)
    if key in seen:
        raise RuntimeError(f"Duplicate batch/table pair: {batch}/{table}")
    seen.add(key)
    outdir=PARQUET/table/f"batch={batch}"
    outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/f"{table}.parquet"
    con=duckdb.connect()
    con.execute(f"""
        COPY (
          SELECT * FROM read_csv(
            '{quote(path)}',
            header=true,
            all_varchar=true,
            strict_mode=false,
            null_padding=true,
            union_by_name=true
          )
        ) TO '{quote(out)}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    rows=con.execute(f"SELECT COUNT(*) FROM read_parquet('{quote(out)}')").fetchone()[0]
    con.close()
    manifest.append({
        "batch":batch,"table":table,"rows":rows,
        "source_bytes":path.stat().st_size,
        "source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "parquet_bytes":out.stat().st_size
    })

con=duckdb.connect(str(DB))
for table in sorted({m["table"] for m in manifest}):
    pattern=PARQUET/table/"batch=*"/"*.parquet"
    con.execute(
        f"CREATE OR REPLACE VIEW bronze_{table} AS "
        f"SELECT * FROM read_parquet('{quote(pattern)}',union_by_name=true,hive_partitioning=true)"
    )
con.close()

summary={
    "csv_files":len(manifest),
    "batches":len({m["batch"] for m in manifest}),
    "tables":sorted({m["table"] for m in manifest}),
    "total_source_bytes":sum(m["source_bytes"] for m in manifest),
    "total_parquet_bytes":sum(m["parquet_bytes"] for m in manifest),
    "runtime_seconds":round(time.time()-started,3),
    "files":manifest
}
(REPORTS/"VAKI_3B_Parquet_Manifest.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in summary.items() if k!="files"},indent=2))
