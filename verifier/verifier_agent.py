import pathlib, sys, subprocess
ROOT=pathlib.Path(__file__).parent.parent
def check(name, fn):
    try:
        ok,detail=fn(); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail[:300]}"); return ok
    except Exception as e: print(f"[FAIL] {name}: {e}"); return False

def completeness():
    must=["README.md","docs/scaling.md","docs/debug_vs_data.md","k8s/control-plane-deployment.yaml","k8s/hpa.yaml","k8s/debug-processor.yaml","workflows/canary_deploy.py","debug_pipeline/analyzer.py","control_plane/app.py","scale_test/harness.py"]
    miss=[f for f in must if not (ROOT/f).exists()]
    return (len(miss)==0, f"all present" if not miss else f"missing {miss}")

def runnable():
    r=subprocess.run([sys.executable,"-m","pytest","tests/","-v"],cwd=ROOT,capture_output=True,text=True)
    (ROOT/"verifier"/"last_test_log.txt").write_text((r.stdout+r.stderr)[-8000:])
    return (r.returncode==0, r.stdout.splitlines()[-1] if r.stdout else "fail")

def debug_sep():
    app_txt=(ROOT/"control_plane"/"app.py").read_text()
    has_debug_endpoint="/api/v1/debug" in app_txt
    has_two_lakes="DEBUG_LAKE" in app_txt and "LAKE_DIR" in app_txt
    has_block="blocked" in app_txt
    return (has_debug_endpoint and has_two_lakes and has_block, f"debug ep {has_debug_endpoint} two lakes {has_two_lakes} blocked logic {has_block}")

def canary():
    txt=(ROOT/"workflows"/"canary_deploy.py").read_text() if (ROOT/"workflows"/"canary_deploy.py").exists() else ""
    return ("canary" in txt.lower() and "30%" in txt, "canary workflow present")

if __name__=="__main__":
    print("=== Quality Gate v3 - debug plane isolation ===")
    results=[]; results.append(check("repo_v3", completeness)); results.append(check("runnable", runnable)); results.append(check("debug_separation", debug_sep)); results.append(check("canary_deploy", canary))
    print(f"\nVERDICT {sum(results)}/{len(results)} -> {'PASS' if sum(results)>=3 else 'FAIL'}")
    sys.exit(0 if sum(results)>=3 else 1)
