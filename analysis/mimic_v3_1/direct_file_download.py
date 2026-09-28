#!/usr/bin/env python3
"""Credential-safe targeted downloader for authorized MIMIC-IV v3.1 access."""

from __future__ import annotations

import argparse
import getpass
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://physionet.org/files/mimiciv/3.1/"
DEFAULT_ROOT = Path("../data_restricted/mimiciv_3_1").resolve()

PHASES = {
    "creatinine": [
        "hosp/d_labitems.csv.gz",
        "hosp/labevents.csv.gz",
    ],
    "renal-icu": [
        "icu/d_items.csv.gz",
        "icu/icustays.csv.gz",
        "icu/outputevents.csv.gz",
        "icu/inputevents.csv.gz",
        "icu/chartevents.csv.gz",
        "icu/procedureevents.csv.gz",
    ],
    "vancomycin": [
        "hosp/emar.csv.gz",
        "hosp/emar_detail.csv.gz",
        "hosp/prescriptions.csv.gz",
        "hosp/pharmacy.csv.gz",
        "icu/d_items.csv.gz",
        "icu/inputevents.csv.gz",
    ],
}


def repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]


def git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root(), text=True
        ).strip()
    except Exception:
        return None


def build_opener(username: str, password: str):
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, BASE_URL, username, password)
    return urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))


def download(opener, rel: str, dest: Path) -> None:
    url = BASE_URL + rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "rxguard-stage6/1.0"})
    try:
        with opener.open(req) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
    except urllib.error.HTTPError as exc:
        partial.unlink(missing_ok=True)
        raise SystemExit(f"Download failed for {rel}: HTTP {exc.code}") from exc
    partial.replace(dest)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def gzip_ok(path: Path) -> bool:
    if not path.name.endswith(".gz"):
        return True
    try:
        with gzip.open(path, "rb") as f:
            while f.read(8 * 1024 * 1024):
                pass
        return True
    except (OSError, EOFError):
        return False


def parse_checksums(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            out[parts[-1].lstrip("*")] = parts[0].lower()
    return out


def ensure_outside_repo(root: Path) -> None:
    rr = repo_root().resolve()
    try:
        root.resolve().relative_to(rr)
    except ValueError:
        return
    raise SystemExit(
        f"Refusing restricted-data destination inside Git worktree: {root}\n"
        "Choose --data-root outside the repository."
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=PHASES, required=True)
    p.add_argument("--data-root", type=Path, default=DEFAULT_ROOT)
    args = p.parse_args()

    root = args.data_root.resolve()
    ensure_outside_repo(root)
    root.mkdir(parents=True, exist_ok=True)

    username = input("PhysioNet username: ").strip()
    password = getpass.getpass("PhysioNet password (not stored): ")
    if not username or not password:
        raise SystemExit("Username/password required.")

    opener = build_opener(username, password)

    checksum_path = root / "SHA256SUMS.txt"
    download(opener, "SHA256SUMS.txt", checksum_path)
    checksum_text = checksum_path.read_text(encoding="utf-8", errors="replace")
    checksums = parse_checksums(checksum_text)

    manifest = {
        "mimic_version": "3.1",
        "source": BASE_URL,
        "phase": args.phase,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_sha(),
        "files": [],
    }

    for rel in PHASES[args.phase]:
        dest = root / rel
        if not dest.exists():
            print(f"Downloading {rel} ...")
            download(opener, rel, dest)
        else:
            print(f"Using existing file: {dest}")

        actual = sha256(dest)
        expected = checksums.get(rel) or checksums.get("./" + rel) or checksums.get(Path(rel).name)
        gz_ok = gzip_ok(dest)
        checksum_ok = None if expected is None else actual == expected
        status = "PASS" if gz_ok and checksum_ok is not False else "FAIL"

        entry = {
            "relative_path": rel,
            "size_bytes": dest.stat().st_size,
            "sha256": actual,
            "official_sha256": expected,
            "checksum_verified": checksum_ok,
            "gzip_integrity": gz_ok,
            "status": status,
        }
        manifest["files"].append(entry)
        print(json.dumps(entry, indent=2))

        if status != "PASS":
            raise SystemExit(f"Integrity check failed: {rel}")

    out_dir = repo_root() / "results" / "mimic_v3_1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "data_access_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metadata manifest: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
