#!/usr/bin/env python3
"""Aggregate-only creatinine concept verification for MIMIC-IV v3.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATA = Path("../data_restricted/mimiciv_3_1").resolve()
OUT = REPO / "results" / "mimic_v3_1"


def dump(name: str, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    args = p.parse_args()
    d = args.data_root.resolve()
    labdict = d / "hosp" / "d_labitems.csv.gz"
    labs = d / "hosp" / "labevents.csv.gz"
    for path in (labdict, labs):
        if not path.exists():
            raise SystemExit(f"Missing required file: {path}")

    con = duckdb.connect()
    concepts = con.execute(
        """
        SELECT itemid, label, fluid, category
        FROM read_csv_auto(?, compression='gzip', header=true)
        WHERE lower(label) LIKE '%creatinine%'
        ORDER BY itemid
        """,
        [str(labdict)],
    ).fetchall()
    cols = ["itemid", "label", "fluid", "category"]
    concept_rows = [dict(zip(cols, row)) for row in concepts]

    anchor = [r for r in concept_rows if int(r["itemid"]) == 50912]
    anchor_ok = bool(anchor) and "creatinine" in str(anchor[0]["label"]).lower()

    profile_row = con.execute(
        """
        SELECT
          50912 AS itemid,
          count(*) AS n_rows,
          count(DISTINCT subject_id) AS n_subjects,
          count(DISTINCT hadm_id) FILTER (WHERE hadm_id IS NOT NULL) AS n_hadm,
          count(*) FILTER (WHERE valuenum IS NULL) AS n_missing_numeric,
          count(DISTINCT valueuom) AS n_units,
          min(valuenum) AS min_value,
          quantile_cont(valuenum, 0.25) AS q25,
          median(valuenum) AS median,
          quantile_cont(valuenum, 0.75) AS q75,
          max(valuenum) AS max_value
        FROM read_csv_auto(?, compression='gzip', header=true)
        WHERE itemid = 50912
        """,
        [str(labs)],
    ).fetchone()
    pcols = [
        "itemid","n_rows","n_subjects","n_hadm","n_missing_numeric",
        "n_units","min_value","q25","median","q75","max_value"
    ]
    profile = dict(zip(pcols, profile_row))

    unit_rows = con.execute(
        """
        SELECT valueuom, count(*) AS n_rows
        FROM read_csv_auto(?, compression='gzip', header=true)
        WHERE itemid = 50912
        GROUP BY valueuom
        ORDER BY n_rows DESC
        """,
        [str(labs)],
    ).fetchall()
    units = [{"valueuom": r[0], "n_rows": r[1]} for r in unit_rows]

    qc = {
        "mimic_version": "3.1",
        "anchor_itemid": 50912,
        "anchor_confirmed": anchor_ok,
        "creatinine_related_dictionary_rows": len(concept_rows),
        "numeric_rows_present": profile["n_rows"] > profile["n_missing_numeric"],
        "units_profiled": profile["n_units"] > 0,
        "status": "PASS" if anchor_ok and profile["n_rows"] > 0 else "FAIL",
        "note": "Aggregate profile only; longitudinal readiness is not inferred here.",
    }

    dump("creatinine_dictionary_concepts.json", concept_rows)
    dump("creatinine_concept_profile.json", profile)
    dump("creatinine_units.json", units)
    dump("creatinine_concept_qc.json", qc)

    print(json.dumps({"profile": profile, "units": units, "qc": qc}, indent=2, default=str))
    if qc["status"] != "PASS":
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
