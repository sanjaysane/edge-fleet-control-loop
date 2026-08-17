import subprocess, sys, os, time, random
n = int(sys.argv[sys.argv.index("--n")+1]) if "--n" in sys.argv else 3
for i in range(n):
    dev_id = f"sim_{i}_{random.randint(100,999)}"
    env = os.environ.copy()
    env["DEVICE_ID"]=dev_id
    subprocess.Popen([sys.executable, "edge_agent/agent.py"], env=env)
    print(f"spawned {dev_id}")
    time.sleep(0.3)
print("fleet running - Ctrl+C to kill parent (children persist as separate procs in this MVP)")
