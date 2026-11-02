#!/usr/bin/env python3
"""One-command release: test, bump version, build, upload to GitHub, update version.json.

Usage:
  python tools/release.py --dry-run                 # build and show the plan; changes nothing
  python tools/release.py                           # next patch version (1.0.2 -> 1.0.3)
  python tools/release.py 1.1.0 --notes "What changed" --notes "Another change"

Needs: branch main, clean tree, GitHub CLI logged in (gh auth login).
The manifest (version.json) is pushed last, only after the uploaded installer is verified.
"""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.app_updater import parse_version  # noqa: E402
from app.version import UPDATE_MANIFEST_URL  # noqa: E402

REPO = "ManavSurani/YOuTUbE"
# Tests that are already red for reasons outside a release (see plan 22, R9)
KNOWN_RED_TESTS = {"tests/test_check_scope.py::test_scope_checker_final"}
INSTALLER_NAME = "YOuTUbE_Setup.exe"

VERSION_PY = ROOT / "app" / "version.py"
SETUP_ISS = ROOT / "installer" / "setup.iss"
MANIFEST = ROOT / "version.json"
INSTALLER = ROOT / "Output" / INSTALLER_NAME

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def bump(version: str) -> str:
    """Return the next patch version."""
    major, minor, patch = (int(p) for p in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def validate_new_version(new: str, current: str) -> str:
    """Return new if it is X.Y.Z and higher than current, else raise ValueError."""
    if not _VERSION_RE.match(new or ""):
        raise ValueError(f"Version must look like 1.0.3, got {new!r}")
    if parse_version(new) <= parse_version(current):
        raise ValueError(f"Version {new} must be higher than current {current}")
    return new


def _replace_one(text: str, pattern: str, replacement: str, what: str) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Could not find the version line in {what}")
    return out


def set_version_py(text: str, version: str) -> str:
    return _replace_one(text, r'^APP_VERSION = "[^"\r\n]*"', f'APP_VERSION = "{version}"', "app/version.py")


def set_setup_iss(text: str, version: str) -> str:
    return _replace_one(text, r'^#define MyAppVersion "[^"\r\n]*"', f'#define MyAppVersion "{version}"', "setup.iss")


def installer_url(version: str) -> str:
    return f"https://github.com/{REPO}/releases/download/v{version}/{INSTALLER_NAME}"


def build_manifest(old: Dict[str, Any], version: str, sha256: str, date: str, notes: List[str]) -> Dict[str, Any]:
    """New manifest dict; keeps every other key (min_supported_version, force_update, android) as is."""
    new = dict(old)
    url = installer_url(version)
    new.update({
        "latest_version": version,
        "version": version,
        "installer_url": url,
        "download_url": url,
        "sha256": sha256,
        "release_date": date,
        "notes": list(notes),
    })
    return new


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def current_version() -> str:
    m = re.search(r'^APP_VERSION = "([^"]*)"', VERSION_PY.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run one external command in the repo root; raise on failure when check is True."""
    print(f"$ {' '.join(cmd)}", flush=True)
    try:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        if check:
            raise RuntimeError(f"'{cmd[0]}' is not installed or not on PATH")
        return subprocess.CompletedProcess(cmd, 127, "", f"{cmd[0]} not installed")
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\n{(res.stdout + res.stderr)[-2000:]}")
    return res


def download_sha256(url: str) -> str:
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "YOuTUbE-release"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        for chunk in iter(lambda: resp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wait_live(version: str, timeout_s: int = 600, every_s: int = 30) -> bool:
    """Poll the raw manifest until it shows version (GitHub raw cache can take minutes)."""
    deadline = time.time() + timeout_s
    while True:
        try:
            req = urllib.request.Request(f"{UPDATE_MANIFEST_URL}?t={int(time.time())}", headers={"User-Agent": "YOuTUbE-release"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if json.loads(resp.read().decode("utf-8")).get("latest_version") == version:
                    return True
        except Exception:
            pass
        if time.time() >= deadline:
            return False
        time.sleep(every_s)


def failed_tests(output: str) -> List[str]:
    return [line.split()[1] for line in output.splitlines() if line.startswith(("FAILED ", "ERROR ")) and len(line.split()) > 1]


def preflight(version: str, dry_run: bool) -> None:
    def problem(msg: str) -> None:
        if not dry_run:
            raise RuntimeError(msg)
        print(f"WARNING (dry run): {msg}")

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if branch != "main":
        problem(f"Releases are made from branch main, current branch is {branch}")
    if run(["git", "status", "--porcelain"]).stdout.strip():
        problem("Working tree has uncommitted changes")
    if run(["git", "fetch", "origin", "main", "--tags"], check=False).returncode != 0:
        problem("Could not fetch origin/main")
    if run(["git", "rev-parse", "HEAD"]).stdout.strip() != run(["git", "rev-parse", "origin/main"]).stdout.strip():
        problem("Local main is not the same as origin/main (pull or push first)")
    if run(["git", "ls-remote", "--tags", "origin", f"v{version}"]).stdout.strip():
        raise RuntimeError(f"Tag v{version} already exists on GitHub")
    if run(["gh", "auth", "status"], check=False).returncode != 0:
        problem("GitHub CLI is not logged in (run: gh auth login)")


def run_tests() -> None:
    res = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], check=False)
    bad = [t for t in failed_tests(res.stdout) if t not in KNOWN_RED_TESTS]
    if bad or (res.returncode != 0 and not failed_tests(res.stdout)):
        raise RuntimeError("Tests failed:\n  " + "\n  ".join(bad or ["(see pytest output)"]))
    print("Tests OK")


def release(version: str, notes: List[str], dry_run: bool) -> int:
    notes = notes or [f"YOuTUbE {version}"]
    originals = {p: p.read_bytes() for p in (VERSION_PY, SETUP_ISS)}
    bumped = False
    try:
        preflight(version, dry_run)                                   # 1
        run_tests()                                                   # 2
        if not dry_run:                                               # 3 (bytes keep line endings)
            bumped = True
            VERSION_PY.write_bytes(set_version_py(originals[VERSION_PY].decode("utf-8"), version).encode("utf-8"))
            SETUP_ISS.write_bytes(set_setup_iss(originals[SETUP_ISS].decode("utf-8"), version).encode("utf-8"))
        run(["cmd", "/c", r"build\build_installer.bat"])              # 4
        if not INSTALLER.is_file():
            raise RuntimeError(f"Installer not found: {INSTALLER}")
        sha = sha256_file(INSTALLER)
        old_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        new_manifest = build_manifest(old_manifest, version, sha, datetime.date.today().isoformat(), notes)

        if dry_run:
            print(f"\nDRY RUN: would release {version}")
            print(f"  installer: {INSTALLER} ({INSTALLER.stat().st_size} bytes)")
            print(f"  sha256:    {sha}")
            print(f"  url:       {installer_url(version)}")
            for key in sorted(new_manifest):
                if new_manifest[key] != old_manifest.get(key):
                    print(f"  version.json {key}: {old_manifest.get(key)!r} -> {new_manifest[key]!r}")
            print("Nothing was changed, committed, pushed or uploaded.")
            return 0

        run(["git", "add", str(VERSION_PY), str(SETUP_ISS)])          # 5
        run(["git", "commit", "-m", f"release: v{version}"])
        bumped = False  # committed: keep the files
        run(["git", "push", "origin", "main"])

        run(["gh", "release", "create", f"v{version}", str(INSTALLER), "--repo", REPO,   # 6
             "--target", "main", "--title", f"YOuTUbE {version}", "--notes", "\n".join(notes)])

        remote_sha = download_sha256(installer_url(version))          # 7
        if remote_sha != sha:
            raise RuntimeError(f"Uploaded installer hash {remote_sha} does not match local {sha}; version.json NOT updated")

        eol = "\r\n" if b"\r\n" in MANIFEST.read_bytes() else "\n"                          # 8
        MANIFEST.write_bytes((json.dumps(new_manifest, indent=2, ensure_ascii=False) + "\n").replace("\n", eol).encode("utf-8"))
        run(["git", "add", str(MANIFEST)])
        run(["git", "commit", "-m", f"release: v{version} manifest"])
        run(["git", "push", "origin", "main"])

        if wait_live(version):                                        # 9
            print(f"Live: apps will now see version {version}.")
        else:
            print("WARNING: version.json is pushed but the raw URL does not show it yet (GitHub cache). It will appear soon.")
        return 0
    except Exception as exc:
        if bumped:
            for path, data in originals.items():
                path.write_bytes(data)
        print(f"\nRELEASE STOPPED: {exc}", file=sys.stderr)
        print("version.json was not changed unless the line above says it was pushed.", file=sys.stderr)
        return 1


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Release a new YOuTUbE version to GitHub.")
    p.add_argument("version", nargs="?", help="new version X.Y.Z (default: next patch)")
    p.add_argument("--notes", action="append", default=[], help="release note line (repeatable)")
    p.add_argument("--dry-run", action="store_true", help="build and show the plan; change nothing")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    current = current_version()
    try:
        version = validate_new_version(args.version or bump(current), current)
    except ValueError as exc:
        print(f"RELEASE STOPPED: {exc}", file=sys.stderr)
        return 1
    return release(version, args.notes, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
