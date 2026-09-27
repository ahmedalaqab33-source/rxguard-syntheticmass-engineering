"""Run preserved analytic stages in a NEW workspace; never alter source artifacts."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import runpy
import duckdb

TABLES = ('allergies','careplans','conditions','encounters','immunizations',
          'medications','observations','patients','procedures')

def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"

def mount_parquet(source, work):
    """Create a new database referencing local Parquet, excluding historical backups."""
    con = duckdb.connect(str(work / 'RxGuard_SyntheticMass.duckdb'))
    try:
        for table in TABLES:
            if not list((source/table).glob('batch=*/*.parquet')):
                if table in ('patients','observations','encounters','medications'):
                    raise ValueError(f'Missing required Parquet table: {table}')
                continue
            pattern = source/table/'batch=*'/'*.parquet'
            con.execute(f'CREATE VIEW bronze_{table} AS SELECT * FROM read_parquet('
                        f'{sql_literal(pattern)},union_by_name=true,hive_partitioning=true)')
    finally:
        con.close()

def run_pipeline(work, *, parquet_root=None, csv_root=None):
    if (parquet_root is None) == (csv_root is None):
        raise ValueError('Provide exactly one source directory')
    work = Path(work).resolve()
    source = Path(parquet_root or csv_root).resolve()
    if not source.is_dir():
        raise ValueError('Source directory does not exist')
    if work == source or work in source.parents or source in work.parents:
        raise ValueError('Input and output directories must be disjoint')
    if csv_root:
        seen=set()
        files=sorted(source.rglob('*.csv'))
        if not files:
            raise ValueError('No CSV files found')
        for path in files:
            batch=next((part for part in path.parts if part.lower().startswith('output_')),None)
            key=(batch,path.stem.lower())
            if batch is None or key[1] not in TABLES or key in seen:
                raise ValueError('CSV layout requires known tables and unique output_ batch/table pairs')
            seen.add(key)
        if not {'patients','observations','encounters','medications'} <= {key[1] for key in seen}:
            raise ValueError('CSV layout missing required core tables')
    work.mkdir(parents=True, exist_ok=False)
    stages = ['registry','kill_test']
    old = {key: os.environ.get(key) for key in ('RXGUARD_WORK','RXGUARD_CSV_ROOT')}
    try:
        os.environ['RXGUARD_WORK'] = str(work)
        if csv_root:
            os.environ['RXGUARD_CSV_ROOT'] = str(source)
            stages = ['ingestion','patient_repair'] + stages
        else:
            mount_parquet(source, work)
        with (work/'execution.log').open('w',encoding='utf-8') as log:
            with contextlib.redirect_stdout(log):
                for stage in stages:
                    runpy.run_module('rxguard.stages.'+stage,run_name='__main__')
        report=json.loads((work/'VAKI_3D1/VAKI_3D1_Creatinine_Distribution_Integrity_KillTest.json').read_text())
        return report
    finally:
        for key,value in old.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value

def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--parquet-root',type=Path,help='Existing active parquet table directory')
    source.add_argument('--csv-root',type=Path,help='Local CSV batches; runs original ingestion and patient repair')
    p.add_argument('--work',type=Path,required=True,help='NEW private output directory; existing directories refused')
    args=p.parse_args()
    try:
        result=run_pipeline(args.work,parquet_root=args.parquet_root,csv_root=args.csv_root)
    except (ValueError,FileExistsError) as exc:
        p.error(str(exc))
    print(json.dumps({'decision':result['decision'],'scientific_scope':result['scientific_scope']},indent=2))

if __name__ == '__main__':
    main()
