-- Stage 6 / MIMIC-IV v3.1
-- 04_vancomycin_dictionary_discovery.sql
-- Aggregate vocabulary discovery only; this is NOT the final exposure phenotype.

-- A. eMAR medication vocabulary.
SELECT
  LOWER(TRIM(medication)) AS medication_norm,
  COUNT(*) AS n_rows,
  COUNT(DISTINCT subject_id) AS n_subjects
FROM `physionet-data.mimiciv_v3_1_hosp.emar`
WHERE REGEXP_CONTAINS(LOWER(medication), r'vancomycin|vanco')
GROUP BY medication_norm
ORDER BY n_rows DESC;

-- B. Prescription vocabulary.
SELECT
  LOWER(TRIM(drug)) AS drug_norm,
  COUNT(*) AS n_rows,
  COUNT(DISTINCT subject_id) AS n_subjects
FROM `physionet-data.mimiciv_v3_1_hosp.prescriptions`
WHERE REGEXP_CONTAINS(LOWER(drug), r'vancomycin|vanco')
GROUP BY drug_norm
ORDER BY n_rows DESC;

-- C. ICU d_items vocabulary: identifies IV/inputevents concepts.
SELECT itemid, label, abbreviation, category, unitname
FROM `physionet-data.mimiciv_v3_1_icu.d_items`
WHERE REGEXP_CONTAINS(LOWER(label), r'vancomycin|vanco')
   OR REGEXP_CONTAINS(LOWER(abbreviation), r'vancomycin|vanco')
ORDER BY itemid;

-- IMPORTANT:
-- These searches are DISCOVERY ONLY.
-- The final phenotype must reconcile identifiers, administrations, details,
-- route/dose/timing, and false-positive/near-match QC.
