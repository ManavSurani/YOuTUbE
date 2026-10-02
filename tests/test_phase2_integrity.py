import ast
from pathlib import Path


def test_no_bare_except_pass_in_core():
    """R9 rule: Scan all Python files in app/core/ to ensure no bare 'except: pass' without logging exists."""
    core_dir = Path(__file__).parent.parent / "app" / "core"
    violations = []

    for py_file in core_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Check if body consists ONLY of 'pass' without any logging or other statements
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    violations.append(f"{py_file.name}:{node.lineno}")

    assert violations == [], f"Bare 'except: pass' found without logging in: {violations}"


def test_no_subprocess_outside_proc():
    """R1 rule: app/core/proc.py is strictly the ONLY module permitted to import subprocess."""
    app_dir = Path(__file__).parent.parent / "app"
    violations = []

    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "proc.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        violations.append(str(py_file.relative_to(app_dir)))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "subprocess":
                    violations.append(str(py_file.relative_to(app_dir)))

    assert violations == [], f"subprocess imported outside proc.py in: {violations}"
