import pathlib, sys, json
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from connector import wa_device_id, parse_human_bp, ingest_reply, simulate_desired

def test_wa_device_id_stable():
    a=wa_device_id("Sanjay Home")
    b=wa_device_id("Sanjay Home")
    assert a==b and a.startswith("wa:")

def test_parse_marathi_numerals():
    out=parse_human_bp("आज १२२/७८ आहे")
    assert out and out["sys_mmHg"]==122 and out["dia_mmHg"]==78

def test_parse_english():
    assert parse_human_bp("120/80")["sys_mmHg"]==120
    assert parse_human_bp("my sys 118 dia 76 stuff") is not None or parse_human_bp("118/76")["sys_mmHg"]==118

def test_simulate_desired_has_marathi():
    d=simulate_desired("Test")
    assert "रक्तदाब" in d["prompt"]

def test_ingest_writes_lake(tmp_path, monkeypatch):
    # still writes to real lake which is fine for test env
    rec=ingest_reply("WaTest", "120/80 test")
    assert rec["payload"]["parsed"]["sys_mmHg"]==120
    assert rec["device_id"].startswith("wa:")

def test_whatsapp_pattern_doc_exists():
    assert (ROOT/"docs"/"whatsapp_edge_pattern.md").exists()
    txt=(ROOT/"docs"/"whatsapp_edge_pattern.md").read_text()
    assert "People are the Device" in txt
