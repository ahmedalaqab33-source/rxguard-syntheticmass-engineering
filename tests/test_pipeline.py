"""Small invented software fixtures, never evidence about clinical performance."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
import duckdb
from rxguard.cli import run_pipeline

def fixture(root, varying=False):
    folder=root/'output_fixture'/'csv'
    folder.mkdir(parents=True)
    def write(name,header,rows):
        with (folder/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(header);writer.writerows(rows)
    write('patients',['ID','BIRTHDATE','DEATHDATE','GENDER','RACE','ETHNICITY','MARITAL'],[
        ['fixture-a','1980-01-01','','F','test','test','S'],
        ['fixture-conflict','1980-01-01','','F','test','test','S'],
        ['fixture-conflict','1981-01-01','','F','test','test','S'],
        ['','1990-01-01','','M','test','test','S']])
    rows=[['2020-01-%02d'%i,'fixture-a','Creatinine',str(i if varying else 1),'mg/dL'] for i in range(1,13)]
    rows += [['2020-01-01','fixture-orphan','Creatinine','1','mg/dL']]
    write('observations',['DATE','PATIENT','DESCRIPTION','VALUE','UNITS'],rows)
    write('encounters',['ID','PATIENT'],[['fixture-e1','fixture-a'],['fixture-e2','fixture-orphan'],['fixture-e3','fixture-enc-only']])
    write('medications',['PATIENT','DESCRIPTION'],[['fixture-a','fixture medication']])

class PipelineTests(unittest.TestCase):
    def test_ingestion_registry_and_constant_gate(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);fixture(base/'source')
            report=run_pipeline(base/'run',csv_root=base/'source')
            self.assertEqual(report['decision'],'ENGINEERING_ONLY_SYNTHETICMASS')
            self.assertEqual(report['global_distribution']['rows_total'],13)
            self.assertEqual(report['patient_variability']['ge2_with_variation'],0)
            summary=json.loads((base/'run/reports/VAKI_3C2_Canonical_Patient_Registry_Linkage_Reconciliation.json').read_text())['summary']
            self.assertEqual(summary['registry_total_ids'],4)
            self.assertEqual(summary['demographics_hold'],1)
            self.assertEqual(summary['no_demographic_row'],2)
            self.assertEqual(summary['missing_patient_id_rows'],1)
            con=duckdb.connect(str(base/'run/RxGuard_SyntheticMass.duckdb'),read_only=True)
            self.assertEqual(con.execute('SELECT count(*)=count(distinct patient_id) FROM silver_patient_registry').fetchone(),(True,))
            con.close()
            second=run_pipeline(base/'second',parquet_root=base/'run/parquet')
            self.assertEqual(second['global_distribution'],report['global_distribution'])

    def test_varying_fixture_reaches_further_testing_only(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);fixture(base/'source',varying=True)
            report=run_pipeline(base/'run',csv_root=base/'source')
            self.assertEqual(report['decision'],'CLINICAL_SIGNAL_GO_FOR_FURTHER_PHENOTYPE_TESTING')
            self.assertEqual(report['patient_variability']['ge2_with_variation'],1)

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);fixture(base/'source');(base/'run').mkdir()
            marker=base/'run/evidence.txt';marker.write_text('preserve')
            with self.assertRaises(FileExistsError):
                run_pipeline(base/'run',csv_root=base/'source')
            self.assertEqual(marker.read_text(),'preserve')

    def test_missing_parquet_schema_fails(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);(base/'source').mkdir()
            with self.assertRaisesRegex(ValueError,'Missing required'):
                run_pipeline(base/'run',parquet_root=base/'source')

    def test_nested_output_refused(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);fixture(base/'source')
            with self.assertRaisesRegex(ValueError,'disjoint'):
                run_pipeline(base/'source/run',csv_root=base/'source')

if __name__ == '__main__':
    unittest.main()
