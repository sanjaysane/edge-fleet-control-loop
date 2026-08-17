import pathlib, sys
ROOT=pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT/"edge_connectors"/"whatsapp"))
from interactive import personal_summary, handle_whatsapp_command, _agg_global

def test_command_status_returns_text():
    out=handle_whatsapp_command("Test Interactive", "STATUS")
    assert out and ("Your BP" in out or "No readings" in out)

def test_global_anonymized():
    out=handle_whatsapp_command("Test Interactive", "GLOBAL")
    assert "Global" in out or "global" in out.lower() or "no cohort" in out.lower()

def test_help_lists():
    out=handle_whatsapp_command("Anyone", "HELP")
    assert "STATUS" in out

def test_bp_parse_is_not_command():
    out=handle_whatsapp_command("Anyone", "120/80 today")
    assert out is None  # treated as data, not command

def test_personal_summary_shape():
    s=personal_summary("Test Interactive")
    assert "count" in s and "device_id" in s
