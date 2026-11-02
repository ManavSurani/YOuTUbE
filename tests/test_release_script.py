"""Tests for the one-command release script (Plan 22)."""

import hashlib
import json
from pathlib import Path

import pytest

import tools.release as rel
from app.core.app_updater import check_manifest_dict

ROOT = Path(__file__).resolve().parent.parent
# Next patch after the repo's current version, so these tests keep working after each release
NEXT = rel.bump(rel.current_version())


# ---------------------------------------------------------------------------
# Phase 1: pure functions
# ---------------------------------------------------------------------------

def test_bump_patch():
    assert rel.bump("1.0.2") == "1.0.3"
    assert rel.bump("1.0.9") == "1.0.10"


def test_validate_new_version():
    assert rel.validate_new_version("1.0.3", "1.0.2") == "1.0.3"
    for bad in ("1.0.2", "1.0.1", "1.0", "v1.0.3x", ""):
        with pytest.raises(ValueError):
            rel.validate_new_version(bad, "1.0.2")


def test_set_version_py():
    text = (ROOT / "app" / "version.py").read_text(encoding="utf-8")
    out = rel.set_version_py(text, NEXT)
    assert f'APP_VERSION = "{NEXT}"' in out
    old_lines, new_lines = text.splitlines(), out.splitlines()
    assert len(old_lines) == len(new_lines)
    changed = [(a, b) for a, b in zip(old_lines, new_lines) if a != b]
    assert len(changed) == 1 and changed[0][0].startswith("APP_VERSION")


def test_set_setup_iss():
    text = (ROOT / "installer" / "setup.iss").read_text(encoding="utf-8")
    out = rel.set_setup_iss(text, NEXT)
    assert f'#define MyAppVersion "{NEXT}"' in out
    changed = [(a, b) for a, b in zip(text.splitlines(), out.splitlines()) if a != b]
    assert len(changed) == 1 and changed[0][0].startswith("#define MyAppVersion")
    assert out.count("\n") == text.count("\n")


def _old_manifest():
    return json.loads((ROOT / "version.json").read_text(encoding="utf-8"))


def test_build_manifest():
    old = _old_manifest()
    new = rel.build_manifest(old, NEXT, "a" * 64, "2026-11-02", ["One", "Two"])
    url = rel.installer_url(NEXT)
    assert new["latest_version"] == new["version"] == NEXT
    assert new["installer_url"] == new["download_url"] == url
    assert new["sha256"] == "a" * 64
    assert new["release_date"] == "2026-11-02"
    assert new["notes"] == ["One", "Two"]
    for key in ("min_supported_version", "force_update", "android"):
        assert new[key] == old[key]
    assert old["latest_version"] != NEXT  # input not mutated


def test_manifest_passes_app_updater():
    new = rel.build_manifest(_old_manifest(), "1.0.3", "b" * 64, "2026-11-02", ["x"])
    assert check_manifest_dict(new, current_version="1.0.2").status == "available"


def test_installer_url_pattern():
    assert rel.installer_url("1.0.3") == (
        "https://github.com/ManavSurani/YOuTUbE/releases/download/v1.0.3/YOuTUbE_Setup.exe"
    )


def test_sha256_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello world" * 1000)
    assert rel.sha256_file(f) == hashlib.sha256(f.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Phase 2: release flow (all external commands mocked)
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


class FakeRunner:
    """Records commands; answers like a clean main branch unless told to fail."""

    def __init__(self, dirty=False, fail_on=None, tests_out="10 passed\n", branch="main"):
        self.calls = []
        self.dirty = dirty
        self.fail_on = fail_on
        self.tests_out = tests_out
        self.branch = branch

    def __call__(self, cmd, check=True):
        self.calls.append(list(cmd))
        joined = " ".join(cmd)
        if self.fail_on and self.fail_on in joined:
            if check:
                raise RuntimeError(f"failed: {joined}")
            return FakeResult(1, "")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return FakeResult(0, self.branch + "\n")
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return FakeResult(0, " M x.py\n" if self.dirty else "")
        if cmd[:2] == ["git", "rev-parse"]:
            return FakeResult(0, "abc123\n")
        if cmd[:2] == ["git", "ls-remote"]:
            return FakeResult(0, "")
        if "pytest" in joined:
            return FakeResult(0 if "failed" not in self.tests_out else 1, self.tests_out)
        if "build_installer.bat" in joined:
            rel.INSTALLER.parent.mkdir(parents=True, exist_ok=True)
            rel.INSTALLER.write_bytes(b"installer-bytes")
        return FakeResult(0, "")

    def index(self, needle):
        for i, c in enumerate(self.calls):
            if needle in " ".join(c):
                return i
        return -1


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for name, src in (("VERSION_PY", ROOT / "app" / "version.py"),
                      ("SETUP_ISS", ROOT / "installer" / "setup.iss"),
                      ("MANIFEST", ROOT / "version.json")):
        dst = tmp_path / src.name
        dst.write_bytes(src.read_bytes())
        monkeypatch.setattr(rel, name, dst)
    monkeypatch.setattr(rel, "INSTALLER", tmp_path / "Output" / "YOuTUbE_Setup.exe")
    monkeypatch.setattr(rel, "download_sha256", lambda url: hashlib.sha256(b"installer-bytes").hexdigest())
    monkeypatch.setattr(rel, "wait_live", lambda version: True)
    originals = {n: getattr(rel, n).read_bytes() for n in ("VERSION_PY", "SETUP_ISS", "MANIFEST")}
    return originals


def _unchanged(originals):
    return all(getattr(rel, n).read_bytes() == data for n, data in originals.items())


def test_flow_order(repo, monkeypatch):
    runner = FakeRunner()
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", ["Note"], dry_run=False) == 0

    order = [runner.index(s) for s in (
        "status --porcelain", "pytest", "build_installer.bat",
        "commit -m release: v1.0.3", "gh release create v1.0.3", "commit -m release: v1.0.3 manifest",
    )]
    assert all(i >= 0 for i in order), order
    assert order == sorted(order)
    assert 'APP_VERSION = "1.0.3"' in rel.VERSION_PY.read_text(encoding="utf-8")
    manifest = json.loads(rel.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["latest_version"] == "1.0.3"
    assert manifest["sha256"] == hashlib.sha256(b"installer-bytes").hexdigest()


def test_stops_on_dirty_tree(repo, monkeypatch):
    runner = FakeRunner(dirty=True)
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert runner.index("build_installer.bat") == -1
    assert runner.index("gh release") == -1
    assert _unchanged(repo)


def test_stops_on_wrong_branch(repo, monkeypatch):
    runner = FakeRunner(branch="fix/ui-pass")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert runner.index("build_installer.bat") == -1
    assert _unchanged(repo)


def test_stops_on_failed_tests(repo, monkeypatch):
    runner = FakeRunner(tests_out="FAILED tests/test_x.py::test_y - boom\n1 failed, 9 passed\n")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert runner.index("build_installer.bat") == -1
    assert _unchanged(repo)


def test_known_red_test_is_allowed(repo, monkeypatch):
    runner = FakeRunner(tests_out="FAILED tests/test_check_scope.py::test_scope_checker_final - x\n1 failed\n")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) == 0


def test_build_failure_restores_files(repo, monkeypatch):
    runner = FakeRunner(fail_on="build_installer.bat")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert _unchanged(repo)
    assert runner.index("git commit") == -1


def test_upload_failure_keeps_manifest(repo, monkeypatch):
    runner = FakeRunner(fail_on="gh release create")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert rel.MANIFEST.read_bytes() == repo["MANIFEST"]


def test_hash_mismatch_keeps_manifest(repo, monkeypatch):
    runner = FakeRunner()
    monkeypatch.setattr(rel, "run", runner)
    monkeypatch.setattr(rel, "download_sha256", lambda url: "0" * 64)
    assert rel.release("1.0.3", [], dry_run=False) != 0
    assert rel.MANIFEST.read_bytes() == repo["MANIFEST"]
    assert runner.index("manifest") == -1


def test_dry_run_changes_nothing(repo, monkeypatch, capsys):
    runner = FakeRunner(dirty=True, branch="fix/ui-pass")
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", ["Note"], dry_run=True) == 0
    assert _unchanged(repo)
    assert runner.index("git commit") == -1
    assert runner.index("git push") == -1
    assert runner.index("gh release") == -1
    out = capsys.readouterr().out
    assert "1.0.3" in out and hashlib.sha256(b"installer-bytes").hexdigest() in out


def test_bump_keeps_line_endings(repo, monkeypatch):
    runner = FakeRunner()
    monkeypatch.setattr(rel, "run", runner)
    assert rel.release("1.0.3", [], dry_run=False) == 0
    for name in ("VERSION_PY", "SETUP_ISS", "MANIFEST"):
        before, after = repo[name], getattr(rel, name).read_bytes()
        crlf = b"\r\n" in before
        assert (after.count(b"\r\n") == after.count(b"\n")) if crlf else (b"\r\n" not in after)


def test_missing_command_is_reported_not_crash(monkeypatch):
    def boom(*a, **kw):
        raise FileNotFoundError(2, "not found")
    monkeypatch.setattr(rel.subprocess, "run", boom)
    assert rel.run(["gh", "auth", "status"], check=False).returncode != 0
    with pytest.raises(RuntimeError, match="not installed"):
        rel.run(["gh", "auth", "status"])


# ---------------------------------------------------------------------------
# Phase 3: installer reopens the app after a silent update
# ---------------------------------------------------------------------------

def test_setup_iss_relaunches_after_silent_install():
    text = (ROOT / "installer" / "setup.iss").read_text(encoding="utf-8")
    run_section = text.split("[Run]", 1)[1]
    line = next(l for l in run_section.splitlines() if "{#MyAppExe}" in l)
    assert "postinstall" in line
    assert "skipifsilent" not in line
