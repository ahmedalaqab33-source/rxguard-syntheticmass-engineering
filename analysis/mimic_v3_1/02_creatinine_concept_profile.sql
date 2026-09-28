-- Stage 6 / MIMIC-IV v3.1
-- 02_creatinine_concept_profile.sql
-- Aggregate/concept-level verification only.

-- A. Verify creatinine dictionary concepts.
SELECT itemid, label, fluid, category
FROM `physionet-data.mimiciv_v3_1_hosp.d_labitems`
WHERE LOWER(label) LIKE '%creatinine%'
ORDER BY itemid;

-- B. Profile the frozen primary creatinine concept (official MIT-LCP anchor: 50912).
SELECT
  itemid,
  COUNT(*) AS n_rows,
  COUNT(DISTINCT subject_id) AS n_subjects,
  COUNT(DISTINCT hadm_id) AS n_hadm,
  COUNTIF(valuenum IS NULL) AS n_missing_numeric,
  COUNT(DISTINCT valueuom) AS n_units,
  MIN(valuenum) AS min_value,
  APPROX_QUANTILES(valuenum, 100)[OFFSET(25)] AS q25,
  APPROX_QUANTILES(valuenum, 100)[OFFSET(50)] AS median,
  APPROX_QUANTILES(valuenum, 100)[OFFSET(75)] AS q75,
  MAX(valuenum) AS max_value
FROM `physionet-data.mimiciv_v3_1_hosp.labevents`
WHERE itemid = 50912
GROUP BY itemid;

-- C. Unit frequencies; still aggregate and publication-safe.
SELECT valueuom, COUNT(*) AS n_rows
FROM `physionet-data.mimiciv_v3_1_hosp.labevents`
WHERE itemid = 50912
GROUP BY valueuom
ORDER BY n_rows DESC;
