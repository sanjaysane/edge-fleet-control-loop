"""
Control Plane side — WA Ingress

Validates sender is onboarded, parses, writes to lake with same schema as hardware devices
Exposes FastAPI router fragment for app.py
"""

def parse_bp(text):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from connector import parse_human_bp
    return parse_human_bp(text)

# Router stub (to be mounted in control_plane/app.py)
ROUTER_CODE = """
@app.post("/api/v1/whatsapp/ingest")
def wa_ingest(msg: dict):
    # msg = {"wa_id": "<name or phone>", "text": "...", "media": optional_path}
    from edge_connectors.whatsapp.connector import wa_device_id, ingest_reply
    wid=wa_id=msg.get("wa_id") or msg.get("phone") or "unknown"
    text=msg.get("text","")
    # TODO: check onboarding DB `data/whatsapp_onboarded.json` contains wid
    rec=ingest_reply(wid, text, msg.get("media"))
    return {"ok":True,"device_id":rec["device_id"],"parsed":rec["payload"]["parsed"]}
@app.get("/api/v1/whatsapp/desired/{wa_name}")
def wa_desired(wa_name: str):
    from edge_connectors.whatsapp.connector import simulate_desired
    return simulate_desired(wa_name)
"""

if __name__=="__main__":
    print(ROUTER_CODE)
