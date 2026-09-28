-- Stage 6 / MIMIC-IV v3.1
-- 03_icu_concept_verification.sql
-- Verify official MIT-LCP urine-output/RRT anchors against live d_items.

WITH anchors AS (
  SELECT itemid, domain FROM UNNEST([
    STRUCT(226559 AS itemid, 'urine_output' AS domain),
    (226560, 'urine_output'), (226561, 'urine_output'), (226584, 'urine_output'),
    (226563, 'urine_output'), (226564, 'urine_output'), (226565, 'urine_output'),
    (226567, 'urine_output'), (226557, 'urine_output'), (226558, 'urine_output'),
    (227488, 'urine_output'), (227489, 'urine_output'),
    (227290, 'rrt_crrt'), (226499, 'rrt_crrt'), (225441, 'rrt_crrt'),
    (225802, 'rrt_crrt'), (225803, 'rrt_crrt'), (225805, 'rrt_crrt'),
    (225809, 'rrt_crrt'), (225955, 'rrt_crrt')
  ])
)
SELECT a.domain, d.itemid, d.label, d.abbreviation, d.category, d.unitname
FROM anchors a
LEFT JOIN `physionet-data.mimiciv_v3_1_icu.d_items` d USING (itemid)
ORDER BY a.domain, d.itemid;
