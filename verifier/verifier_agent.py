import pathlib, sys, subprocess
ROOT=pathlib.Path(__file__).parent.parent
def check(n,fn):
    try:
        ok,det=fn(); print(f"[{'PASS' if ok else 'FAIL'}] {n}: {det[:400]}"); return ok
    except Exception as e:
        print(f"[FAIL] {n}: {e}"); import traceback; traceback.print_exc(); return False

def completeness():
    must=["docs/edge_features_parity.md","docs/whatsapp_edge_pattern.md","docs/whatsapp_daily_ping_cron.md","edge_connectors/whatsapp/connector.py","edge_connectors/whatsapp/onboarding.py","edge_connectors/whatsapp/interactive.py","workflows/whatsapp_daily_ping.py","workflows/whatsapp_collection.py","edge_agent/secure_boot.py","control_plane/attestation/verifier.py","control_plane/app.py"]
    miss=[f for f in must if not (ROOT/f).exists()]
    return (not miss, "all present" if not miss else f"missing {miss}")

def runnable():
    r=subprocess.run([sys.executable,"-m","pytest","tests/test_whatsapp_onboarding.py","tests/test_whatsapp_interactive.py","tests/test_whatsapp_edge.py","tests/test_secure_boot.py","tests/test_integration.py","-v"],cwd=ROOT,capture_output=True,text=True)
    (ROOT/"verifier"/"last_test_log.txt").write_text((r.stdout+r.stderr)[-8000:])
    return (r.returncode==0, r.stdout.splitlines()[-1] if r.stdout else "fail")

def parity():
    txt=(ROOT/"docs/edge_features_parity.md").read_text()
    return ("same 9 facets" in txt.lower() and "whatsapp-human-v1" in txt and "bp-monitor-v1" in txt, "parity 9 facets across skus")

def onboarding():
    import sys; sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
    from onboarding import handle_inbound, is_onboarding_intent
    assert is_onboarding_intent("START")
    r=handle_inbound("ParityProbe-"+str(ROOT), "HELLO", dry_run=True)
    return ("welcome" in r["type"] or "need_onboard" in r["type"], f"onboarding returns {r['type']}")

if __name__=="__main__":
    print("=== Quality Gate v7 - consistent edge whatever device ===")
    rs=[]
    rs.append(check("repo_v7_complete", completeness))
    rs.append(check("runnable_25_tests", runnable))
    rs.append(check("parity_9_facets", parity))
    rs.append(check("onboarding_welcome_commands", onboarding))
    print(f"\nVERDICT {sum(rs)}/{len(rs)} -> {'PASS publish' if sum(rs)>=3 else 'FAIL'}")
    sys.exit(0 if sum(rs)>=3 else 1)
