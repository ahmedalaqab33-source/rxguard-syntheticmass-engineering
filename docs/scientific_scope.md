# Scientific scope and stop decision

SyntheticMass completed its engineering/product-validation purpose: large-scale ingestion, schema handling, columnar storage, DuckDB analytics, joins, canonical identifier construction, linkage restrictions, integrity checks, and feasibility kill-testing.

The renal feasibility result is negative and valuable. All 1,913,439 selected numeric creatinine observations equal 1.0 mg/dL. Of 389,788 represented patients, 361,193 have at least two measurements; none vary. Medication descriptions contain zero case-insensitive substring matches for vancomycin. These measurements are independently reproduced in the current audit.

The user's project record describes this as a prespecified kill-test. The preserved script establishes its exact implemented thresholds; independent preregistration or a timestamped prespecification record was not recovered. Do not claim external preregistration.

The original logic requires all of the following for further phenotype testing: at least 10 unique values, fewer than 80% of numeric rows equal to 1.0, at least 20% of multi-measurement patients showing variation, and positive median within-patient population SD. Two or more failure reasons lead to `ENGINEERING_ONLY_SYNTHETICMASS`; otherwise the result is inconclusive. Failure reasons include <=3 unique values, >=90% equal to 1.0, >=90% constant multi-measurement patients, and median SD zero or unavailable. These are inherited engineering thresholds, not validated clinical criteria. Missing median SD is grouped with zero in the historical reason text; empty/non-numeric datasets require explicit review.

No AKI diagnoses, sensitivity/specificity, causal effects, drug nephrotoxicity estimates, or clinical safety claims arise from this release. The string search does not constitute a comprehensive terminology-based exposure phenotype.

The clinical-validation pathway pivoted to MIMIC-IV, as specified in the project owner's record. This release does not demonstrate completed MIMIC-IV access, analysis, or validation. Future work needs a separate protocol, governed access, exposure/phenotype definitions, temporal checks, cohort audit, and clinical evaluation. [MIMIC access requirements](https://mimic.mit.edu/docs/faq/how-to-get-access.html) describe the training and data-use agreement requirements; these are not fulfilled by downloading this software.
