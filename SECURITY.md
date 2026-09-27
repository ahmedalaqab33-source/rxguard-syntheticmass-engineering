# Security and data-governance policy

## Supported version

The current `main` branch and the latest published release are supported for security and data-governance fixes.

## Reporting a problem

For potential credential exposure, restricted-data exposure, privacy concerns, or repository-safety defects, do not post sensitive material in a public issue. Contact the repository owner privately through the contact route available on the GitHub profile.

## Repository boundaries

This public repository must not contain:
- credentials or API keys,
- raw or patient-level health records,
- restricted MIMIC-IV data,
- local databases or Parquet datasets,
- private logs,
- personal documents,
- record-level synthetic identifiers or addresses unless explicitly reviewed and justified.

The automated publication audit is a defense-in-depth control, not a substitute for manual review.

## Dependency and workflow security

Dependencies are intentionally minimal. GitHub Actions uses read-only repository contents permissions. New dependencies should be justified, pinned where appropriate, and reviewed for maintenance and security implications.
