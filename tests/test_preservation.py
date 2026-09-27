"""Verify recovered provenance metadata and analytically minimal adapters."""
import ast
import json
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PreservationTests(unittest.TestCase):
    def test_provenance_manifest_and_archives(self):
        entries=json.loads((ROOT/'docs/source_manifest.json').read_text())
        self.assertGreaterEqual(len(entries),3)
        for entry in entries:
            self.assertRegex(entry['original_sha256'],r'^[0-9a-f]{64}$')
            path=ROOT/entry['archived_as']
            self.assertTrue(path.is_file(),path)
            ast.parse(path.read_text(encoding='utf-8-sig'))
            if 'decoded_original_sha256' in entry:
                self.assertRegex(entry['decoded_original_sha256'],r'^[0-9a-f]{64}$')

    def test_repair_and_registry_are_minimal_adapters(self):
        pairs={
            'patient_repair':'Run_RxGuard_VAKI_3C_REPAIR.py',
            'registry':'Run_RxGuard_VAKI_3C2_Reconcile.py',
        }
        for stage,original in pairs.items():
            expected=(ROOT/'legacy'/original).read_text(encoding='utf-8-sig')
            expected=expected.replace('from pathlib import Path','from pathlib import Path\nimport os')
            expected=expected.replace('Path(r"D:\\DRxGuard_Data\\RxGuard_Analytics")','Path(os.environ["RXGUARD_WORK"])')
            expected=expected.replace('Path(r"D:\\DRxGuard_Data\\RxGuard_CSV_Batches")','Path(os.environ["RXGUARD_CSV_ROOT"])')
            expected=expected.replace('shutil.rmtree(backup)','raise FileExistsError("Refusing to replace an existing patient backup")')
            actual=(ROOT/'src/rxguard/stages'/f'{stage}.py').read_text(encoding='utf-8')
            self.assertEqual(ast.dump(ast.parse(actual)),ast.dump(ast.parse(expected)),stage)

if __name__ == '__main__':
    unittest.main()
