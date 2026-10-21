# Nova Poshta status tracking: Raspberry timer

Scope: background shipment tracking only; **no TTN create, cancel or print**.
Run only after validated ARM64 deployment and database readiness.

Default opt-out: backend CLI requires `SELLORA_NP_TRACKING_SYNC_ENABLED=true`
unless `--dry-run` is supplied.

Suggested user-systemd timer using an existing Docker service:

```ini
# ~/.config/systemd/user/sellora-np-tracking.service
[Unit]
Description=Sellora Nova Poshta tracking reconciliation
[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec -e SELLORA_NP_TRACKING_SYNC_ENABLED=true sellora-rpi-backend-1 python -m app.services.nova_poshta_tracking_worker
TimeoutStartSec=240
```

```ini
# ~/.config/systemd/user/sellora-np-tracking.timer
[Unit]
Description=Periodic Nova Poshta tracking synchronization
[Timer]
OnBootSec=10min
OnUnitInactiveSec=30min
AccuracySec=3min
Persistent=false
Unit=sellora-np-tracking.service
[Install]
WantedBy=timers.target
```

`systemctl --user daemon-reload`, then `systemctl --user enable --now sellora-np-tracking.timer`.
Rollback: `systemctl --user disable --now sellora-np-tracking.timer`.
`--dry-run` should be run first. Watch service journal for failure counts, not customer data.
Each pass scans at most ten recent workspaces' active shipment records and uses a PostgreSQL
advisory lock to avoid overlapping invocations. A shipment is re-polled no sooner than
20 minutes after successful provider synchronization.

Finance rule: a delivered TTN updates delivery state/order shipment state; it
**never** sets PaymentStatus.PAID or assumes that NovaPay settled the receivable.
