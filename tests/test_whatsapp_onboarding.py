import pathlib, sys, json
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from onboarding import is_onboarding_intent, onboard_contact, handle_inbound, wa_device_id
from pathlib import Path
# use temp file monkeypatch via env? easiest: clean onboard file for test id
ONB=ROOT/"control_plane"/"data"/"whatsapp_onboarded.json"

def test_intent():
    assert is_onboarding_intent("START") is True
    assert is_onboarding_intent("नमस्कार") is True
    assert is_onboarding_intent("120/80") is False

def test_onboard_welcome_then_status():
    who="WA-Parity-Test-"+str(Path.cwd())[-4:]
    # ensure fresh
    # remove if exists
    if ONB.exists():
        db=json.loads(ONB.read_text())
        did=wa_device_id(who)
        if did in db:
            del db[did]; ONB.write_text(json.dumps(db,indent=2))
    r1=handle_inbound(who,"HELLO",dry_run=True)
    assert r1["type"]=="welcome" and "Commands" in r1["reply"]
    r2=handle_inbound(who,"STATUS",dry_run=True)
    assert r2["type"] in ("command","data")
    r3=handle_inbound(who,"१२०/८०",dry_run=True)
    assert r3["type"] in ("data","command")

def test_parity_doc():
    assert (ROOT/"docs"/"edge_features_parity.md").exists()
    txt=(ROOT/"docs"/"edge_features_parity.md").read_text()
    assert "same 9 facets" in txt.lower()

def test_onboarding_file_shape():
    who="ShapeTest-"+str(time.time())[-4:] if 'time' in globals() else "ShapeTest"
    import time
    who="ShapeTest-"+str(int(time.time())%10000)
    onboard_contact(who)
    db=json.loads(ONB.read_text())
    did=wa_device_id(who)
    assert did in db and "sku" in db[did] and db[did]["sku"]=="whatsapp-human-v1"
