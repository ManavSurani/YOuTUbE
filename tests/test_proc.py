import sys
import time
from app.core.proc import run_hidden, start_hidden, kill_tree


def test_run_hidden_output():
    code, output = run_hidden([sys.executable, "-c", "print('hi')"])
    assert code == 0
    assert output.strip() == "hi"


def test_run_hidden_timeout():
    code, output = run_hidden(
        [sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5
    )
    assert code == -1


def test_kill_tree():
    proc = start_hidden(
        [sys.executable, "-c", "import time; time.sleep(10)"]
    )
    time.sleep(0.2)
    assert proc.poll() is None
    kill_tree(proc)
    time.sleep(0.5)
    assert proc.poll() is not None
