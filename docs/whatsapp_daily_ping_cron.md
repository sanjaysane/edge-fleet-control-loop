# Daily 8:30 AM PDT Ping — same as your HA Build Yoga slot

You asked: daily ask for imports from user, drop into same lake as BP monitor

- Cron: `30 15 * * *` UTC ( = 8:30 AM PDT )
- Script: `workflows/whatsapp_daily_ping.py` (dry_run=False goes live when Companion connected)

Why sim by default: Companion currently `connected:false`. When you run `hatch_wai_cli auth` and get `connected:true`, change line `ping_all(dry_run=False)` or set env `WA_LIVE=1`.

What it sends: Marathi prompt + English fallback you already saw in `simulate_desired()`:
```
नमस्कार! आजचा रक्तदाब काय आहे? उदाहरण: 120/80 असं टाका. फोटो असेल तर पाठवा.
```

Log: `control_plane/data/wa_ping_log.jsonl` so dashboard can show ping delivery + reply-rate (same as fw rollout gate — if reply-rate <20% after canary 5%, we warn same as debug drop >50%).

To run manually now (sim):
```
python3 workflows/whatsapp_daily_ping.py
```
To go live (after auth):
```
WA_LIVE=1 python3 -c "from workflows.whatsapp_daily_ping import ping_all; ping_all(dry_run=False)"
```
