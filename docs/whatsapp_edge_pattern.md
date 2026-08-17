# WhatsApp as Edge — People are the Device

You nailed it: same pattern works for hardware *or* humans.

- BP monitor in a home -> `edge_agent` pulls config, sends vitals
- WhatsApp contact (person) -> `whatsapp_connector` pulls prompt, sends reply

Both are "edge nodes with flaky connectivity and low trust." Same control plane handles both.

## Mapping

| Same Pattern For | HW Edge (what you asked first) | WhatsApp Human Edge (what you just asked) |
|---|---|---|
| Edge node id | `device_id: bp-abc-001` | `wa: +91-XXX-...` or contact name hash |
| Onboarding | `device_onboarding.py` claim with QR | `wa_onboard` : person says "START" in WhatsApp, we create `wa_device` |
| Desired state | `{"fw":"v3","cfg":{"sample_hz":10}}` | `{"prompt_version":"v2","campaign":"bp-check","lang":"marathi"}` |
| Rollout / canary | push new firmware to 5% of devices | push new questionnaire text to 5% of people, watch reply-rate |
| Telemetry | sensor JSON | chat reply parsed JSON: `{"sys":120,"dia":80}` from "120/80" |
| Sleep / offline | device offline -> spool to disk | person offline -> no reply -> retry with backoff |
| Debug logs | crash @ main.c | undeliverable / "didn't understand" / media fail |
| Data lake | `data/lake/bp-*.jsonl` | `data/lake/wa-*.jsonl` same schema, just `source=whatsapp` |
| Verified boot | Ed25519 sig of binary | verified sender: only accept from onboarded WA id, optional HMAC of media |
| Attestation | TPM hash of driver | "person attestation": is this reply from the onboarded phone? WA id is root of trust (plus optional OTP if you need proof) |

Same cost table, same HPA scaling, same quarantine.

## 3 Loops Stay Same

- Deploy Loop: Control Plane -> Edge -> `You get new prompt`
- Data Loop: Edge -> Control Plane -> Lake -> `Thanks, got your 122/78`
- Learning Loop: Lake -> Model -> Control Plane -> `Push new nudges based on cohort`

Thats why its worth keeping one repo: change the connector, not the brain.

## What this unblocks for you

1. **Ask for imports**: "Send photo of BP cuff reading" -> media -> OCR -> lake. You wanted "ask for imports from user".
2. **Collect baseline health**: daily ping at 8:30-9:30 AM (your yoga window) — fits HA streak habit
3. **Last-mile edge you said**: healthcare workers on WhatsApp are edge workers — same dashboard sees both device uploads and human-uploaded values
4. **Gradual deployment of prompts**: new Marathi phrasing `साधारण १७० किमी`-style test on 5% first, watch confusion rate
5. **On-call same**: human edge storm (50% "don't understand") alerts same as debug drop rate >50%

No separate system.

## Lossless to existing

You keep BP monitor as primary. WhatsApp is second sku:

```
sku=bp-monitor-v1 : hardware edge_agent
sku=whatsapp-human-v1 : whatsapp_connector
```

Both report to `/api/v1/telemetry` with `device_id` prefix.

