"""Plan 23 Phase 0: nothing secret or generated is tracked by git."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def _tracked():
    return _git("ls-files").stdout.splitlines()


def test_no_keystore_tracked():
    bad = [f for f in _tracked() if f.lower().endswith((".keystore", ".jks"))]
    assert bad == []


def test_no_signing_password_in_tracked_files():
    pattern = re.compile(r'(store|key)Password\s*=\s*"[^"]+"')
    hits = []
    for f in _tracked():
        if f.endswith((".kts", ".gradle", ".properties")):
            if pattern.search((ROOT / f).read_text(encoding="utf-8", errors="replace")):
                hits.append(f)
    assert hits == []


@pytest.mark.parametrize("path", [
    "android/.kotlin/x",
    "docs/ui_audit/x.png",
    ".vscode/settings.json",
    "video.mp4.part",
    "android/keystore.properties",
    "android/app/new.jks",
])
def test_gitignore_covers_generated_paths(path):
    assert _git("check-ignore", "-q", "--no-index", path).returncode == 0, f"{path} is not ignored"
