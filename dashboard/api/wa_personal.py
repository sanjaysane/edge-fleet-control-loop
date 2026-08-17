"""
Personal status API + HTML dashboard fragment for WhatsApp humans

/persona route returns JSON personal vs global so WhatsApp quick DASH command can point to static page

Served via same FastAPI app as control plane for reuse.
"""

def router_code():
    return """
@app.get("/api/v1/whatsapp/status/{wa_name}")
def wa_status(wa_name: str):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import personal_summary
    return personal_summary(wa_name)

@app.get("/api/v1/whatsapp/global")
def wa_global():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import _agg_global
    return _agg_global(days=7)

@app.post("/api/v1/whatsapp/command")
def wa_command(body: dict):
    # body {"wa_name": "...", "text": "STATUS"}
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import handle_whatsapp_command
    from connector import ingest_reply
    wa=body.get("wa_name") or body.get("phone") or "unknown"
    txt=body.get("text","")
    cmd_res=handle_whatsapp_command(wa, txt)
    if cmd_res:
        return {"type":"command","reply":cmd_res}
    else:
        rec=ingest_reply(wa, txt, body.get("media"))
        return {"type":"data","ok":True,"device_id":rec["device_id"],"parsed":rec["payload"]["parsed"]}

@app.get("/wa/{wa_name}/dash")
def wa_dash_page(wa_name: str):
    # tiny server-rendered HTML for quick personal dashboard — people-as-edge you asked: own status + global snippet
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "edge_connectors" / "whatsapp"))
    from interactive import personal_summary, _agg_global
    s=personal_summary(wa_name)
    g=_agg_global()
    html = f'''
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{wa_name} — BP</title>
    <style>body{{font-family:system-ui;padding:16px;max-width:520px;margin:auto}} .card{{border:1px solid #ddd;border-radius:12px;padding:12px;margin:8px 0}} .k{{color:#666;font-size:12px}} .big{{font-size:24px;font-weight:700}}</style>
    </head><body>
    <h2>{wa_name} — personal</h2>
    <div class="card"><div class=k>last</div><div class=big>{s.get("last",{{}}).get("sys_mmHg","—")}/{s.get("last",{{}}).get("dia_mmHg","—")}</div><div>{s.get("count",0)} readings • streak {s.get("streak_days",0)}d • trend {s.get("trend","—")}</div></div>
    <div class="card"><div class=k>7-day avg sys</div><div class=big>{s.get("avg_sys_last7","—")}</div></div>
    <div class="card"><div class=k>global last 7d (anon)</div>{g.get("count",0)} readings, avg {g.get("avg_sys","—")}/{g.get("avg_dia","—")}, from {g.get("devices_seen",0)} devices</div>
    <div class=k>type STATUS/GLOBAL in WhatsApp for refresh — same lake as hardware fleet</div>
    </body></html>'''
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
"""

if __name__=="__main__":
    print(router_code())
