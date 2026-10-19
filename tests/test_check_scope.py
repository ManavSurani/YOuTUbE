"""Unit tests for the scope checker tool."""

import subprocess
import sys


def test_scope_checker_clean(monkeypatch):
    import tools.check_scope as cs

    monkeypatch.setattr(cs, "get_changed_files", lambda b: ["app/ui/video_tab.py"])
    assert cs.check_scope(phase=3, is_final=False, baseline="62c8db1") is True


def test_scope_checker_final():
    res = subprocess.run(
        [sys.executable, "tools/check_scope.py", "--baseline", "62c8db1", "--final"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Scope Check PASS (--final)" in res.stdout
