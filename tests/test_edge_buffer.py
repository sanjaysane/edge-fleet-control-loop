import pathlib, json
def test_spool_file_format():
    sample = {"device_id":"x","type":"sensor","payload":{"cpu_temp":42}}
    p = pathlib.Path("/tmp/test_spool.jsonl")
    p.write_text(json.dumps(sample)+"\n")
    assert p.exists()
    line = json.loads(p.read_text().strip())
    assert line["payload"]["cpu_temp"] == 42
    p.unlink()
