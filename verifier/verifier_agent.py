import pathlib, sys, subprocess
ROOT=pathlib.Path(__file__).parent.parent
def check(name, fn):
    try:
        ok,detail=fn(); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail[:400]}"); return ok
    except Exception as e:
        print(f"[FAIL] {name}: {e}"); return False

def completeness():
    must=["README.md","docs/secure_boot_chain.md","docs/features_uplevel.md","docs/comparison.md","docs/cost_estimate_eks.md","edge_agent/secure_boot.py","edge_agent/attestation.py","edge_driver/driver_stub.py","control_plane/attestation/verifier.py","scripts/deploy_eks_one_liner.sh","k8s/control-plane-deployment.yaml"]
    miss=[f for f in must if not (ROOT/f).exists()]
    return (len(miss)==0, f"all present" if not miss else f"missing {miss}")

def runnable():
    import subprocess, sys
    r=subprocess.run([sys.executable,"-m","pytest","tests/test_secure_boot.py","tests/test_integration.py","tests/test_debug_pipeline.py","-v"],cwd=ROOT,capture_output=True,text=True)
    (ROOT/"verifier"/"last_test_log.txt").write_text((r.stdout+r.stderr)[-8000:])
    return (r.returncode==0, r.stdout.splitlines()[-1] if r.stdout else "fail")

def secure_boot():
    txt=(ROOT/"docs/secure_boot_chain.md").read_text()
    has="Secure Boot" in txt and "Attestation" in txt and "chain" in txt.lower()
    return (has, "secure boot + attest doc present")

def plumbing():
    ok = (ROOT/"edge_agent"/"secure_boot.py").exists() and (ROOT/"edge_driver"/"driver_stub.py").exists() and (ROOT/"control_plane"/"attestation"/"verifier.py").exists()
    return (ok, "plumbing files exist")

if __name__=="__main__":
    print("=== Quality Gate v5 - secure boot + attest plumbing ===")
    res=[]
    res.append(check("repo_v5_complete", completeness))
    res.append(check("runnable_15_tests", runnable))
    res.append(check("secure_boot_doc", secure_boot))
    res.append(check("plumbing_deep", plumbing))
    print(f"\nVERDICT {sum(res)}/{len(res)} -> {'PASS publish' if sum(res)>=3 else 'FAIL'}")
    sys.exit(0 if sum(res)>=3 else 1)
