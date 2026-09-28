# Stage 6 — Reproducible Analysis Build & MIMIC-IV External Test

Status: **ACTIVE — protocol/SAP frozen; external-test implementation started**

## Purpose

Stage 6 implements the frozen pre-model clinical-signal readiness framework against MIMIC-IV as the external real-world comparator. SyntheticMass remains the motivating/development case; MIMIC-IV is the external test. No dataset-specific relaxation of frozen rules is permitted after comparator inspection without a documented protocol amendment.

## Execution sequence

1. **Access and version verification**
   - Confirm MIMIC-IV version used for analysis.
   - Record access route and run date privately; do not commit credentials or restricted data.
2. **Schema inventory**
   - Verify availability and exact columns for patients, admissions, labevents/d_labitems, prescriptions, pharmacy, eMAR/eMAR detail, ICU stays, inputevents, outputevents, procedure events, and renal replacement therapy concepts.
   - Record only schema metadata and aggregate counts in the public repository.
3. **Concept mapping**
   - Serum creatinine: verify concept identifier(s), units, reference metadata, and source table.
   - Vancomycin: build a hierarchical identifier/name mapping and distinguish orders from administrations.
   - Urine output, body weight, and RRT/CRRT: verify source concepts before use.
4. **Cohort extraction**
   - Construct renal-readiness, vancomycin-exposed, temporally linkable renal+exposure, and optional TDM subsets.
5. **Locked readiness gates**
   - Apply the frozen gate order exactly: ingestion → linkage → SCr availability → units → timestamps → repeated measurements → within-patient variability → 48 h/7 d evaluability → AKI identifiability → vancomycin exposure → administration timing → exposure–renal linkage.
6. **Sensitivity analyses**
   - Execute only the prespecified sensitivity analyses from SAP v1.0.
7. **QC and provenance**
   - Record patient/row counts before and after each transformation, missingness, unit frequencies, duplicate/null identifiers, timestamp anomalies, concept mappings, and gate decisions.
8. **Aggregate outputs**
   - Produce publication-safe aggregate JSON/CSV tables and figures only. Restricted patient-level MIMIC-IV data must never be committed.

## Primary analysis rule

The primary outcome is the **clinical-analysis readiness profile** (GO / CONDITIONAL / NO-GO by gate and overall), not AKI incidence and not predictive-model performance.

## Claim boundary

Passing the framework means **ready to proceed for the prespecified analysis**. It does not establish clinical validity, causal validity, general-purpose dataset superiority, or vancomycin-induced nephrotoxicity.

## Amendment rule

Any post-freeze change must be logged with:
- amendment ID,
- date,
- original rule,
- revised rule,
- rationale,
- whether comparator outcomes had already been inspected,
- expected analytic impact.

## Data governance

- No MIMIC-IV patient-level data, credentials, access tokens, query exports containing row-level information, or restricted extracts may enter this repository.
- Public artifacts are limited to code, schema/concept metadata, aggregate counts, QC summaries, and publication outputs permitted by the data-use agreement.
