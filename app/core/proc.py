"""Hidden external process runner.

This is THE ONLY module in the entire application permitted to import subprocess.
All processes are launched with CREATE_NO_WINDOW and SW_HIDE to guarantee
the user never sees a terminal window.
"""

import os
import subprocess
from typing import Any, Sequence, Tuple
from app.core.logger import get_logger
from app.core.paths import BIN_DIR

CREATE_NO_WINDOW = 0x08000000


def get_hidden_startupinfo() -> subprocess.STARTUPINFO:
    """Return STARTUPINFO configured with SW_HIDE."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo


def start_hidden(cmd: Sequence[str] | str, **kwargs: Any) -> subprocess.Popen:
    """Start an external process completely hidden with no console window."""
    flags = kwargs.pop("creationflags", 0) | CREATE_NO_WINDOW
    startupinfo = kwargs.pop("startupinfo", None) or get_hidden_startupinfo()

    env = kwargs.pop("env", None)
    if env is None:
        env = os.environ.copy()
    else:
        env = dict(env)

    bin_str = str(BIN_DIR)
    path_val = env.get("PATH", "")
    if bin_str not in path_val:
        env["PATH"] = f"{bin_str};{path_val}" if path_val else bin_str

    return subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
        startupinfo=startupinfo,
        env=env,
        **kwargs,
    )


def run_hidden(
    cmd: Sequence[str] | str, timeout: float | None = None, **kwargs: Any
) -> Tuple[int, str]:
    """Run an external command hidden to completion and return (exit_code, output)."""
    proc = start_hidden(cmd, **kwargs)
    try:
        output, _ = proc.communicate(timeout=timeout)
        return proc.returncode, output or ""
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        output, _ = proc.communicate()
        return -1, output or ""


def kill_tree(proc: subprocess.Popen | int) -> None:
    """Terminate the process and all of its child processes."""
    pid = proc.pid if isinstance(proc, subprocess.Popen) else proc
    if pid is None:
        return

    try:
        startupinfo = get_hidden_startupinfo()
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            check=False,
        )
    except Exception as exc:
        get_logger().debug(f"taskkill failed for pid {pid}: {exc}")

    if isinstance(proc, subprocess.Popen):
        try:
            proc.kill()
        except Exception as exc:
            get_logger().debug(f"proc.kill failed: {exc}")
