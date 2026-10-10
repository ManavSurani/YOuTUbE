"""Unit tests for the scope checker tool."""

import subprocess
import sys


def test_scope_checker_clean():
    res = subprocess.run(
        [sys.executable, "tools/check_scope.py", "--baseline", "62c8db1", "--phase", "11"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Scope Check PASS" in res.stdout


def test_scope_checker_final():
    res = subprocess.run(
        [sys.executable, "tools/check_scope.py", "--baseline", "62c8db1", "--final"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Scope Check PASS (--final)" in res.stdout
