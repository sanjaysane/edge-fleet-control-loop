# Edge Parity — whatever the edge is, same 9 facets

You asked to keep it consistent across hardware BP monitor vs WhatsApp human vs future Wi-Fi router sku.

| Facet you built | bp-monitor-v1 (HW) | whatsapp-human-v1 (People) | wifi-router-v1 (future) | Same code? |
|---|---|---|---|---|
| Onboarding / Identity | `workflows/device_onboarding.py` QR claim, mTLS | `edge_connectors/whatsapp/onboarding.py` START -> hello+welcome, wa_id hash is device_id, stored in `whatsapp_onboarded.json` same shape as `devices.json` | MAC + cert claim same file shape | Yes — both write `{"device_id","wa_name/device_sku","onboarded_at","sku"}` |
| Desired-state / OTA (prompt rollout) | `{"fw_version":"v3"}` pushed via `/desired/{id}`, progressive 5%->30%->100% | `{"prompt_version":"prompt-v2-marathi"}` same endpoint `/whatsapp/desired/{wa_name}`, same progressive gating via canary 5% of contacts | config idem | Same rollout engine `canary_deploy.py` works for both — swap version string |
| Secure boot chain | Ed25519 sig of binary, burned pubkey | Verified sender: only accept messages from onboarded `wa_id`, optional HMAC of media photo, future: WA-verified badge as root of trust | same TPM | Same verifier gate `attester.verify_attest()` / quarantine.json |
| QoS lanes | `critical` lane halo data <200ms | same middleware `qos/lanes.py` — human edge is `bulk` by default, but STATUS command upgraded to `default` lane so personal dashboard stays snappy even during debug flood | same | One file |
| Data lake | `data/lake/bp-*.jsonl` | `data/lake/wa:*.jsonl` same schema plus `source=whatsapp`, same dedupe + 1h late + 90d TTL pipeline `data_pipeline/processor.py` | same | One processor |
| Debug vs Data | `/debug` isolated | `/whatsapp/ingest` isolated same way, `undeliverable` goes to debug_lake not data lake | same | Two-rivers pattern holds |
| Dashboard personal vs fleet | Global fleet health | Personal: `wa_status` (your own), `wa_global` (anon cohort), `wa/dash` (HTML), Global: `fleet/health` same merged view — humans counted as devices so 501 hw + 12 wa = 513 total | same merge | One dashboard summary `dashboard/api/full` + per-user `wa_personal` |
| Alert / On-call | Canary crash >5x => page | Canary prompt confusion >50% "don't understand" => same `alert_manager.py` rule "debug drop >50% -> blind" maps to human prompt blind | same | One `alert_manager.py` |
| Interactivity | device pull loop | human pull `STATUS/GLOBAL/DASH/HELP` + push daily ping 8:30 AM PDT + photo import pipeline you flagged for future `photo -> OCR -> 120/80` — same `interactive.py` | pull loop | One `interactive.py` |

So hello/welcome/commands/pull vs push collection/summary view are not WhatsApp-only — they are edge-generic.

**Pull vs Push list you asked:**

- Pull: person types any command anytime (STATUS) -> `handle_whatsapp_command()` in `interactive.py`, returns inline, no cron needed (same as `GET /desired`)
- Push: daily ping `workflows/whatsapp_daily_ping.py` cron `30 15 * * * UTC`, progressive via canary first 5% for new prompt phrasing `સાધારણ 170 km`-style test

- Data collection both ways:
  - Push collection: we push "What's your BP?" they reply "120/80" -> goes to `wa_physicist` lake
  - Pull collection: they spontaneously send "आज १२२/७८" — same ingest

**Welcome trampoline:**

`onboarding.py` sends after first START:

> नमस्कार! ... Commands: STATUS / GLOBAL / DASH / HELP ... Daily 8:30 AM ...

Same as device onboarding sends desired fw v1 first config.

All 9 facets keep moving if you change sku name tomorrow.
