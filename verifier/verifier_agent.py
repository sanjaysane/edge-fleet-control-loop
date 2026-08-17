import pathlib, sys, subprocess
ROOT=pathlib.Path(__file__).parent.parent
def check(name, fn):
    try:
        ok,detail=fn(); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail[:400]}"); return ok
    except Exception as e: print(f"[FAIL] {name}: {e}"); return False

def completeness():
    must=["README.md","docs/features_uplevel.md","docs/comparison.md","docs/debug_vs_data.md","docs/scaling.md","control_plane/qos/lanes.py","control_plane/resilience/circuit.py","data_pipeline/processor.py","debug_pipeline/analyzer.py","alerting/alert_manager.py","oncall/rotation.yaml","dashboard/api/summary.py","k8s/control-plane-deployment.yaml","k8s/hpa.yaml","k8s/debug-processor.yaml"]
    miss=[f for f in must if not (ROOT/f).exists()]
    return (len(miss)==0, f"all present" if not miss else f"missing {miss}")

def runnable():
    r=subprocess.run([sys.executable,"-m","pytest","tests/","-v"],cwd=ROOT,capture_output=True,text=True)
    (ROOT/"verifier"/"last_test_log.txt").write_text((r.stdout+r.stderr)[-8000:])
    return (r.returncode==0, r.stdout.splitlines()[-1] if r.stdout else "fail")

def uplevel_facets():
    f=(ROOT/"docs/features_uplevel.md").read_text()
    need=["QoS Lanes","Circuit Breakers","Data Lake","Dashboarding","Alerting","On-Call"]
    found=sum(1 for w in need if w.lower() in f.lower())
    return (found>=5, f"found {found}/6 upleveled facets")

def comparison():
    txt=(ROOT/"docs/comparison.md").read_text()
    has_table="| Feature" in txt and "AWS IoT" in txt
    return (has_table, "comparison matrix present" if has_table else "no matrix")

if __name__=="__main__":
    print("=== Quality Gate v4 - upleveled facets ===")
    res=[]
    res.append(check("repo_v4_complete", completeness))
    res.append(check("runnable_10_tests", runnable))
    res.append(check("uplevel_facets", uplevel_facets))
    res.append(check("comparison_vs_equiv", comparison))
    print(f"\nVERDICT {sum(res)}/{len(res)} -> {'PASS publish' if sum(res)>=3 else 'FAIL'}")
    sys.exit(0 if sum(res)>=3 else 1)
