#!/bin/sh
# Requires an explicit opt-in. The provider API calls are read only.
while true; do
  if [ "${SELLORA_NP_EXTERNAL_SYNC_ENABLED:-false}" = "true" ]; then
    python -m app.services.nova_poshta_inbox_worker || echo 'NP external scan failed'
  fi
  if [ "${SELLORA_NP_TRACKING_SYNC_ENABLED:-false}" = "true" ]; then
    python -m app.services.nova_poshta_tracking_worker || echo 'NP status sync failed'
  fi
  sleep 900
done
