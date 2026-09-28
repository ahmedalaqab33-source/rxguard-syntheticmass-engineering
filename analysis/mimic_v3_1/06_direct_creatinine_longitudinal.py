#!/usr/bin/env python3
"""Aggregate-only longitudinal SCr readiness audit for MIMIC-IV v3.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATA = Path("../data_restricted/mimiciv_3_1").resolve()
OUT = REPO / "results" / "mimic_v3_1"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    p.add_argument("--temp-dir", type=Path, default=Path("../data_restricted/duckdb_tmp").resolve())
    args = p.parse_args()

    labs = args.data_root.resolve() / "hosp" / "labevents.csv.gz"
    if not labs.exists():
        raise SystemExit(f"Missing required file: {labs}")

    args.temp_dir.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"SET temp_directory='{str(args.temp_dir).replace(chr(39), chr(39)*2)}'")
    con.execute("SET preserve_insertion_order=false")

    # Restricted working view: never exported.
    con.execute(
        """
        CREATE TEMP TABLE creat AS
        SELECT
          subject_id,
          hadm_id,
          CAST(charttime AS TIMESTAMP) AS charttime,
          CAST(valuenum AS DOUBLE) AS creat
        FROM read_csv_auto(?, compression='gzip', header=true)
        WHERE itemid = 50912
          AND valuenum IS NOT NULL
          AND charttime IS NOT NULL
        """,
        [str(labs)],
    )

    # Collapse exact same-patient/same-time duplicates to mean, mirroring MIT-LCP logic.
    con.execute(
        """
        CREATE TEMP TABLE cr AS
        SELECT subject_id, hadm_id, charttime, avg(creat) AS creat
        FROM creat
        GROUP BY subject_id, hadm_id, charttime
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE patient_summary AS
        SELECT
          subject_id,
          count(*) AS n_measurements,
          min(creat) AS min_creat,
          max(creat) AS max_creat,
          max(creat)-min(creat) AS creat_range
        FROM cr
        GROUP BY subject_id
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE time_eval AS
        SELECT
          a.subject_id,
          a.charttime,
          a.creat,
          min(b.creat) FILTER (
            WHERE b.charttime < a.charttime
              AND b.charttime >= a.charttime - INTERVAL 48 HOUR
          ) AS low48,
          min(b.creat) FILTER (
            WHERE b.charttime < a.charttime
              AND b.charttime >= a.charttime - INTERVAL 7 DAY
          ) AS low7
        FROM cr a
        LEFT JOIN cr b
          ON a.subject_id = b.subject_id
         AND b.charttime < a.charttime
         AND b.charttime >= a.charttime - INTERVAL 7 DAY
        GROUP BY a.subject_id, a.charttime, a.creat
        """
    )

    overall = con.execute(
        """
        SELECT
          (SELECT count(DISTINCT subject_id) FROM cr) AS subjects_ge1,
          (SELECT count(*) FROM patient_summary WHERE n_measurements >= 2) AS subjects_ge2,
          (SELECT count(*) FROM patient_summary WHERE n_measurements >= 3) AS subjects_ge3,
          (SELECT median(n_measurements) FROM patient_summary) AS measurements_per_subject_median,
          (SELECT quantile_cont(n_measurements, 0.25) FROM patient_summary) AS measurements_per_subject_q25,
          (SELECT quantile_cont(n_measurements, 0.75) FROM patient_summary) AS measurements_per_subject_q75,
          (SELECT count(*) FROM patient_summary WHERE creat_range > 0) AS subjects_any_change,
          (SELECT count(*) FROM patient_summary WHERE n_measurements >= 2 AND creat_range = 0) AS repeated_subjects_zero_variation,
          (SELECT median(creat_range) FROM patient_summary WHERE n_measurements >= 2) AS range_median,
          (SELECT quantile_cont(creat_range, 0.25) FROM patient_summary WHERE n_measurements >= 2) AS range_q25,
          (SELECT quantile_cont(creat_range, 0.75) FROM patient_summary WHERE n_measurements >= 2) AS range_q75,
          (SELECT count(DISTINCT subject_id) FROM time_eval WHERE low48 IS NOT NULL) AS subjects_48h_evaluable,
          (SELECT count(DISTINCT subject_id) FROM time_eval WHERE low7 IS NOT NULL) AS subjects_7d_evaluable,
          (SELECT count(DISTINCT subject_id) FROM time_eval WHERE low48 IS NOT NULL OR low7 IS NOT NULL) AS subjects_kdigo_creat_evaluable,
          (SELECT count(DISTINCT subject_id) FROM time_eval WHERE low48 IS NOT NULL AND creat >= low48 + 0.3) AS subjects_meet_abs_48h,
          (SELECT count(DISTINCT subject_id) FROM time_eval WHERE low7 IS NOT NULL AND creat >= low7 * 1.5) AS subjects_meet_rel_7d
        """
    ).fetchone()

    names = [
        "subjects_ge1","subjects_ge2","subjects_ge3",
        "measurements_per_subject_median","measurements_per_subject_q25","measurements_per_subject_q75",
        "subjects_any_change","repeated_subjects_zero_variation",
        "range_median","range_q25","range_q75",
        "subjects_48h_evaluable","subjects_7d_evaluable","subjects_kdigo_creat_evaluable",
        "subjects_meet_abs_48h","subjects_meet_rel_7d"
    ]
    metrics = dict(zip(names, overall))
    metrics["mimic_version"] = "3.1"
    metrics["itemid"] = 50912
    metrics["method"] = "time-respecting prior 48h and prior 7d minima; exact-time duplicates averaged"

    repeated = metrics["subjects_ge2"] or 0
    any_change = metrics["subjects_any_change"] or 0
    kdigo_eval = metrics["subjects_kdigo_creat_evaluable"] or 0
    qc = {
        "repeated_measurement_gate": "PASS" if repeated > 0 else "NO-GO",
        "biological_variability_gate": "PASS" if any_change > 0 else "NO-GO",
        "temporal_kdigo_evaluability_gate": "PASS" if kdigo_eval > 0 else "NO-GO",
        "overall_creatinine_readiness": (
            "GO" if repeated > 0 and any_change > 0 and kdigo_eval > 0 else "NO-GO"
        ),
        "claim_boundary": "This establishes readiness to apply the prespecified SCr phenotype, not clinical validation.",
    }

    (OUT / "creatinine_longitudinal_readiness.json").write_text(
        json.dumps(metrics, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (OUT / "creatinine_longitudinal_qc.json").write_text(
        json.dumps(qc, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"metrics": metrics, "qc": qc}, indent=2, default=str))
    return 0 if qc["overall_creatinine_readiness"] == "GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
