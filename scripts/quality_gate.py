# thin wrapper alias for CI
import subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).parent.parent
r = subprocess.run([sys.executable, "verifier/verifier_agent.py"], cwd=ROOT)
sys.exit(r.returncode)
