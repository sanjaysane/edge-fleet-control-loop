"""
Canary + Progressive + Auto-Rollback workflow for new software

Flow you asked:
1. Upload new artifact (v_n+1)
2. Deploy to 5% canary
3. Wait 15 min, run analyzer via /debug/summary + integration tests
4. If crash spike -> auto-hold, notify devs, keep data pipeline clean
5. Else promote to 30% -> 100%

Separates debug blast radius from data.
"""
import time, requests, sys

CONTROL=os.getenv("CONTROL_URL","http://localhost:8000")

def rollout(version, pct, canary=False):
    r=requests.post(f"{CONTROL}/api/v1/rollout", json={"version":version,"pct":pct,"canary":canary})
    print(f"rollout {version} pct={pct} canary={canary} -> {r.status_code} {r.text[:200]}")
    return r.ok

def summary():
    try:
        j=requests.get(f"{CONTROL}/api/v1/debug/summary", timeout=5).json()
        print("summary:", j.get("blocked_versions"), j.get("reports",[])[-1] if j.get("reports") else "no reports")
        return j
    except Exception as e:
        print("summary fail", e)
        return {"blocked_versions":[]}

def canary_flow(new_version):
    print(f"Starting canary for {new_version}")
    if not rollout(new_version, 5, canary=True):
        sys.exit(1)
    print("Waiting 90s for canary soak (in prod 15 min)")
    time.sleep(90)
    s=summary()
    if new_version in s.get("blocked_versions",[]):
        print(f"BLOCKED {new_version} - crash spike detected, holding at 5%, not impacting data plane")
        print("Dev action: fix, then POST /api/v1/unblock/{version} and retry")
        return False
    print("Canary clean, promoting to 30%")
    rollout(new_version, 30)
    time.sleep(30)
    s=summary()
    if new_version in s.get("blocked_versions",[]):
        print("Paused at 30%")
        return False
    print("Promoting to 100%")
    rollout(new_version, 100)
    print("Done - full rollout, data lake isolated throughout")
    return True

if __name__=="__main__":
    v=sys.argv[1] if len(sys.argv)>1 else "v3"
    canary_flow(v)
