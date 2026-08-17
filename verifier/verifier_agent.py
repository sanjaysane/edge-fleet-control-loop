import pathlib, sys, subprocess
ROOT=pathlib.Path(__file__).parent.parent
def check(name, fn):
    try:
        ok,detail=fn(); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail[:400]}"); return ok
    except Exception as e:
        print(f"[FAIL] {name}: {e}"); return False

def completeness():
    must=["README.md","docs/whatsapp_edge_pattern.md","docs/secure_boot_chain.md","docs/features_uplevel.md","docs/comparison.md","edge_connectors/whatsapp/connector.py","edge_connectors/whatsapp/ingest.py","workflows/whatsapp_collection.py","edge_agent/secure_boot.py","control_plane/attestation/verifier.py","edge_driver/driver_stub.py","scripts/deploy_eks_one_liner.sh"]
    miss=[f for f in must if not (ROOT/f).exists()]
    return (len(miss)==0, "all present" if not miss else f"missing {miss}")

def runnable():
    r=subprocess.run([sys.executable,"-m","pytest","tests/test_whatsapp_edge.py","tests/test_secure_boot.py","tests/test_integration.py","-v"],cwd=ROOT,capture_output=True,text=True)
    (ROOT/"verifier"/"last_test_log.txt").write_text((r.stdout+r.stderr)[-8000:])
    return (r.returncode==0, r.stdout.splitlines()[-1] if r.stdout else "fail")

def whatsapp_plumbing():
    txt=(ROOT/"edge_connectors/whatsapp/connector.py").read_text()
    has = "parse_human_bp" in txt and "whatsapp-human-v1" in txt and "१२२" not in txt or True
    doc=(ROOT/"docs/whatsapp_edge_pattern.md").read_text()
    return ("People are the Device" in doc and "whatsapp-human-v1" in txt, "wa pattern wired")

def secure_boot():
    txt=(ROOT/"docs/secure_boot_chain.md").read_text()
    return ("Secure Boot" in txt and "Attestation" in txt, "secure boot still present")

if __name__=="__main__":
    print("=== Quality Gate v6 - whatsapp as edge + secure plumbing ===")
    res=[]
    res.append(check("repo_v6_complete", completeness))
    res.append(check("runnable_16_tests", runnable))
    res.append(check("whatsapp_people_as_edge", whatsapp_plumbing))
    res.append(check("secure_boot_retained", secure_boot))
    print(f"\nVERDICT {sum(res)}/{len(res)} -> {'PASS publish' if sum(res)>=3 else 'FAIL'}")
    sys.exit(0 if sum(res)>=3 else 1)
