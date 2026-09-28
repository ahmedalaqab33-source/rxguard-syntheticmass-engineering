param(
    [ValidateSet("creatinine","renal-icu","vancomycin","all")]
    [string]$Phase = "creatinine"
)

$ErrorActionPreference = "Stop"

Write-Host "Stage 6 direct-file execution" -ForegroundColor Cyan
Write-Host "Restricted MIMIC-IV data will NOT be committed to Git." -ForegroundColor Yellow

python -m pip install -e .

if ($Phase -eq "creatinine" -or $Phase -eq "all") {
    python analysis/mimic_v3_1/direct_file_download.py --phase creatinine
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python analysis/mimic_v3_1/05_direct_creatinine_profile.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python analysis/mimic_v3_1/06_direct_creatinine_longitudinal.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Phase -eq "renal-icu" -or $Phase -eq "all") {
    python analysis/mimic_v3_1/direct_file_download.py --phase renal-icu
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Phase -eq "vancomycin" -or $Phase -eq "all") {
    python analysis/mimic_v3_1/direct_file_download.py --phase vancomycin
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Stage 6 direct-file requested phase completed." -ForegroundColor Green
