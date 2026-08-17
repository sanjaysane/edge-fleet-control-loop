# WhatsApp Edge Connector — People as Edge Devices

Treats each onboarded WhatsApp contact as an edge device id `wa:<hash>`.

## Files
- `connector.py` — the edge_agent equivalent for humans: pulls desired prompt from control plane, sends WhatsApp message, parses reply, pushes telemetry
- `ingest.py` — control plane side: validates WA sender is onboarded, parses natural reply to structured JSON, writes to same lake dir (`source=whatsapp`)
- `driver/` is the prompt set : v1 asks "120/80 ?", v2 asks in Marathi. That's your "firmware" for humans.

## How it runs (since Companion is currently offline disconnected)

If Companion connected:
```
hatch_wai_cli chats list -> find contact already existing
connector pulls /desired/wa:<id> => {"prompt":"...","version":"v2"}
hatch_wai_cli send --chat <id> --text "<prompt>"
incoming reply -> ingest maps "१२०/८०" or "120/80" -> {"sys":120,"dia":80}
POST to control_plane /api/v1/telemetry with device_id=wa:<id>, type=human_vitals, payload=parsed
```
If offline (current status `connected:false`, `registered:false`): connector runs in sim mode printing what it would send and writing `data/lake/sim_wa_*.jsonl` so dashboard still sees it. Reconnect via `hatch_wai_cli auth` to go live.

## Permissions you already set (from MEMORY.md)
- Companion is read/write capable on +16505057306, HITL approval required for send. We respect that: every real send goes under one HITL approval. Your family chat +16505057306 and other existing chats only.
- We cannot cold-message unknown numbers — same limit as before ("Chat not found" error). Onboarding flow therefore asks person to message you first ("START").

## Reconnect steps if you want live now
```
hatch_wai_cli auth --help
# follow QR / link-code flow, then:
hatch_wai_cli status
# should say connected:true registered:true
```
Then rerun this connector.

