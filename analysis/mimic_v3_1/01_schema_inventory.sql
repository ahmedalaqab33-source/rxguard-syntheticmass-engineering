-- Stage 6 / MIMIC-IV v3.1
-- 01_schema_inventory.sql
-- Purpose: verify live BigQuery schema WITHOUT returning patient-level data.

-- A. List available tables in the version-locked datasets.
SELECT 'hosp' AS module, table_name
FROM `physionet-data.mimiciv_v3_1_hosp.INFORMATION_SCHEMA.TABLES`
UNION ALL
SELECT 'icu' AS module, table_name
FROM `physionet-data.mimiciv_v3_1_icu.INFORMATION_SCHEMA.TABLES`
ORDER BY module, table_name;

-- B. Inventory columns for the tables required by the frozen SAP.
WITH wanted AS (
  SELECT 'hosp' module, table_name FROM UNNEST([
    'patients','admissions','transfers','d_labitems','labevents',
    'emar','emar_detail','prescriptions','pharmacy'
  ]) table_name
  UNION ALL
  SELECT 'icu' module, table_name FROM UNNEST([
    'icustays','d_items','chartevents','inputevents',
    'outputevents','procedureevents'
  ]) table_name
),
hosp_cols AS (
  SELECT 'hosp' module, table_name, column_name, data_type, ordinal_position
  FROM `physionet-data.mimiciv_v3_1_hosp.INFORMATION_SCHEMA.COLUMNS`
),
icu_cols AS (
  SELECT 'icu' module, table_name, column_name, data_type, ordinal_position
  FROM `physionet-data.mimiciv_v3_1_icu.INFORMATION_SCHEMA.COLUMNS`
),
all_cols AS (
  SELECT * FROM hosp_cols
  UNION ALL
  SELECT * FROM icu_cols
)
SELECT c.module, c.table_name, c.ordinal_position, c.column_name, c.data_type
FROM all_cols c
JOIN wanted w USING (module, table_name)
ORDER BY c.module, c.table_name, c.ordinal_position;
