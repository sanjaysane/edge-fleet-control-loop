"""
WhatsApp Edge Connector — mirrors edge_agent/agent.py but for humans

The same 3 verbs: heartbeat (person is reachable), fetch desired (prompt version), report telemetry (parsed reply)

Can run offline = sim mode (prints what would send, writes to local lake)
"""
import pathlib, json, time, hashlib, re, sys, os
ROOT=pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT/"control_plane"))
LAKE=ROOT/"control_plane"/"data"/"lake"
LAKE.mkdir(parents=True, exist_ok=True)

def wa_device_id(phone_or_name: str) -> str:
    return "wa:" + hashlib.sha256(phone_or_name.encode()).hexdigest()[:12]

def parse_human_bp(text: str):
    """
    Handles you-asked imports: "120/80", "१२०/८०" Marathi numerals, "120 80", "my bp is 122 over 78"
    Returns dict or None
    """
    if not text: return None
    # normalize Marathi numerals ०१२३४५६७८९ -> 0123456789
    mar = "०१२३४५६७८९"
    eng = "0123456789"
    t = text.strip()
    for m,e in zip(mar, eng):
        t=t.replace(m,e)
    # look for sys/dia
    m = re.search(r'(\d{2,3})\s*[/,|x\s]+\s*(\d{2,3})', t)
    if m:
        return {"sys_mmHg": int(m.group(1)), "dia_mmHg": int(m.group(2)), "raw": text, "parsed_from":"bp_pattern"}
    # single number sys only
    m2 = re.search(r'\b(\d{2,3})\b', t)
    if m2 and ("bp" in t.lower() or "रक्तदाब" in t.lower()):
        return {"sys_mmHg": int(m2.group(1)), "raw": text, "parsed_from":"single"}
    return None

def simulate_desired(phone_or_name: str):
    # pull from control plane desired? for MVP local fallback
    dev_id=wa_device_id(phone_or_name)
    # In real use fetch GET /api/v1/desired/{dev_id}
    return {
        "device_id": dev_id,
        "version": "prompt-v2-marathi",
        "prompt": "नमस्कार! आजचा रक्तदाब काय आहे? उदाहरण: 120/80 असं टाका. फोटो असेल तर पाठवा.",
        "prompt_en": "Hi! What's your BP today? Reply like 120/80, or send a photo of cuff.",
        "campaign": "bp-check"
    }

def send_whatsapp(phone_or_name: str, text: str, dry_run=True):
    dev_id=wa_device_id(phone_or_name)
    if dry_run:
        print(f"[SIM SEND] to {phone_or_name[:4]}** ({dev_id}): {text[:120]}")
        return {"mode":"sim","to":dev_id}
    # live: use hatch_wai_cli send — requires HITL approval per your setting
    import subprocess
    try:
        # You need chat id: we try name search via chats, but simplest is direct send if companion supports name
        res=subprocess.run(["hatch_wai_cli","send","--chat", phone_or_name, "--text", text], capture_output=True, text=True, timeout=30)
        return {"mode":"live","stdout":res.stdout,"stderr":res.stderr,"code":res.returncode}
    except Exception as e:
        return {"error":str(e),"mode":"live-failed"}

def ingest_reply(phone_or_name: str, reply_text: str, media_path: str=None):
    """
    What you asked: pipeline that can "ask for imports" and collect that data we have been collecting via WA channel
    """
    parsed=parse_human_bp(reply_text)
    dev_id=wa_device_id(phone_or_name)
    lake_file=LAKE / f"{time.strftime('%Y/%m/%d')}" / f"{dev_id}.jsonl"
    lake_file.parent.mkdir(parents=True, exist_ok=True)
    rec={
        "device_id": dev_id,
        "ts": time.time(),
        "type": "human_vitals",
        "payload": {
            "sku": "whatsapp-human-v1",
            "source": "whatsapp",
            "reply_raw": reply_text,
            "parsed": parsed,
            "media": media_path,
            "wa_name": phone_or_name
        }
    }
    with open(lake_file,"a") as f:
        f.write(json.dumps(rec)+"\n")
    return rec

if __name__=="__main__":
    # example loop — you can import these funcs in workflows/whatsapp_collection.py
    who="Sanjay Test"
    d=simulate_desired(who)
    send_whatsapp(who, d["prompt_en"]+" / "+d["prompt"], dry_run=True)
    # simulate a reply
    r=ingest_reply(who, "आज १२२/७८ आहे")
    print("ingested:", json.dumps(r, ensure_ascii=False, indent=2))
