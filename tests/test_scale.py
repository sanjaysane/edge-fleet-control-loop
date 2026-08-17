import subprocess, sys, pathlib
def test_scale_smoke():
    # scale harness is validated by import + --help, not full run (no server in CI)
    r = subprocess.run([sys.executable, "scale_test/harness.py","--help"], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    assert "devices" in r.stdout
