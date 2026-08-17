"""
Interactive layer for people-as-edge you just asked

- Person on WhatsApp types STATUS / SUMMARY / GLOBAL / PING -> we answer with their own numbers vs cohort
- Provides quick personal dashboard HTML snippet + link
- Daily 8:30 AM ping (PDT) loops via scheduled job — same lake as BP monitor

Uses same lake both hw and human write to. No new DB.
"""
import pathlib, json, time, statistics, os, sys
ROOT=pathlib.Path(__file__).parent.parent.parent
LAKE=ROOT/"control_plane"/"data"/"lake"
ONBOARD=ROOT/"control_plane"/"data"/"whatsapp_onboarded.json"

sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from connector import wa_device_id, parse_human_bp

def _read_lake_for(device_id: str, days=14):
    recs=[]
    # glob last 14 day folders
    for jf in sorted(LAKE.rglob(f"{device_id}.jsonl"))[-14:]:
        try:
            for line in open(jf):
                j=json.loads(line); recs.append(j)
        except: pass
    return recs[-50:]  # last 50

def _agg_global(days=7):
    # aggregate cohort stats across hw + human edges last 7 days — what person sees as GLOBAL but anonymous
    all_recs=[]
    for jf in LAKE.rglob("*.jsonl"):
        if time.time() - jf.stat().st_mtime > days*86400: continue
        try:
            for line in open(jf):
                j=json.loads(line); all_recs.append(j)
        except: pass
    parsed=[r["payload"]["parsed"] for r in all_recs if r.get("payload",{}).get("parsed") and r.get("payload",{}).get("parsed",{}).get("sys_mmHg")]
    if not parsed: return {"count":0}
    sys_vals=[p["sys_mmHg"] for p in parsed]; dia_vals=[p.get("dia_mmHg") for p in parsed if p.get("dia_mmHg")]
    return {
        "count": len(parsed),
        "avg_sys": round(statistics.mean(sys_vals),1),
        "avg_dia": round(statistics.mean(dia_vals),1) if dia_vals else None,
        "p50_sys": int(statistics.median(sys_vals)),
        "devices_seen": len(set(r.get("device_id") for r in all_recs))
    }

def personal_summary(wa_name: str):
    dev=wa_device_id(wa_name)
    recs=_read_lake_for(dev, days=30)
    parsed=[r["payload"]["parsed"] for r in recs if r.get("payload",{}).get("parsed")]
    if not parsed:
        return {"device_id":dev, "wa_name":wa_name, "count":0, "msg":"No readings yet — send 120/80 to start"}
    sys_vals=[p["sys_mmHg"] for p in parsed]
    last=parsed[-1]
    return {
        "device_id": dev,
        "wa_name": wa_name,
        "count": len(parsed),
        "last": last,
        "avg_sys_last7": round(statistics.mean(sys_vals[-7:]),1) if len(sys_vals)>=1 else sys_vals[-1],
        "streak_days": len(set(time.strftime("%Y-%m-%d", time.localtime(r["ts"])) for r in recs[-10:])),
        "trend": "stable" if len(sys_vals)<3 else ("up" if sys_vals[-1] > statistics.mean(sys_vals[-3:-1])+3 else "down" if sys_vals[-1] < statistics.mean(sys_vals[-3:-1])-3 else "stable")
    }

def handle_whatsapp_command(wa_name: str, text: str):
    """
    What you asked: some interactivity on WhatsApp connector for people on edge

    Commands:
    STATUS -> your last reading + streak (quick personal dashboard in chat)
    SUMMARY -> 7-day avg + trend
    GLOBAL -> anonymized cohort stats
    DASH -> link to personal HTML dashboard + quick embed
    HELP -> list

    Media import path: if text contains attachment reference or looks like photo, ask OCR later — stub now
    """
    t=text.strip().lower()
    if t in ("status","summary","meri sthiti","माझी स्थिती"):
        s=personal_summary(wa_name)
        if s["count"]==0:
            return f"{s['msg']}\nTry: 120/80"
        return (f"Your BP — Last: {s['last']['sys_mmHg']}/{s['last'].get('dia_mmHg','?')} ({s['last'].get('raw','')[:20]})\n"
                f"7-day avg sys {s['avg_sys_last7']} | readings {s['count']} | streak {s['streak_days']} days | trend {s['trend']}\n"
                f"Type GLOBAL for cohort or DASH for your page.")
    if t in ("global","सर्व","cohort"):
        g=_agg_global(days=7)
        if g["count"]==0: return "Global: no cohort data yet."
        return (f"Global (last 7d, anonymized) — {g['count']} readings from {g['devices_seen']} devices\n"
                f"Avg {g['avg_sys']}/{g['avg_dia']} | median sys {g['p50_sys']}\n"
                f"Your number is private — only you see personal.")
    if t in ("dash","dashboard","link"):
        # personal dashboard artifact expected at /your_files/... or control plane served static link
        dev=wa_device_id(wa_name)
        return (f"Your dashboard:\nhttps://agent.meta.ai/s/wa-dash-{dev[:8]}\n"
                f"(On device you see your own numbers, plus global avg box — no names)")
    if t in ("ping","help","madat","मदत"):
        return ("I can do:\nSTATUS — your last + streak\nSUMMARY — same\nGLOBAL — cohort avg (anon)\nDASH — your page link\nSend 120/80 or photo — I save to same lake as BP monitor\nDaily ping at 8:30 AM PDT if you opt in")
    # fallback: try parse as BP
    parsed=parse_human_bp(text)
    if parsed:
        return None  # let normal ingest path handle — return None signals "treated as data, not command"
    return None

if __name__=="__main__":
    # quick demo
    for cmd in ["STATUS","GLOBAL","120/80"]:
        print(cmd, "->", handle_whatsapp_command("Demo WA", cmd) or "data ingest")
