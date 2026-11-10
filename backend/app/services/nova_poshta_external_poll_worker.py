"""Production-safe workspace-scoped NP inbox polling (sender API is read-only)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.workspace import Workspace
from app.services.nova_poshta_external_inbox_service import NovaPoshtaExternalInboxService

def main() -> int:
    now=datetime.now(ZoneInfo("Europe/Kyiv"))
    # Today on 3 of 4 polls. On the fourth, rotate across prior 6 days,
    # so late-created waybills are discovered without 7-day API bursts.
    quarter=((now.hour*4)+(now.minute//15))%24
    days_old=(quarter//4)+1 if quarter%4==3 else 0
    target=(now.date()-timedelta(days=days_old))
    with SessionLocal() as db:
        ws=db.scalar(select(Workspace).where(
            Workspace.slug=="sellora",
            Workspace.name=="Your Jewelry",
            Workspace.is_active.is_(True)
        ))
        if ws is None:
            print("NP_EXTERNAL_NO_TARGET_WORKSPACE")
            return 4
        if "--dry-run" in sys.argv:
            print("NP_EXTERNAL_POLL_PREVIEW",target.isoformat(),"workspace_ready=1")
            return 0
        try:
            summary=NovaPoshtaExternalInboxService(db).collect(ws.id,target,target)
        except Exception as exc:
            db.rollback()
            code=str(getattr(exc,"code","UNKNOWN"))[:120]
            print("NP_EXTERNAL_PROVIDER_FAILURE","type="+type(exc).__name__,"code="+code)
            return 75 if "many requests" in code.lower() else 2
    print("NP_EXTERNAL_POLL_OK",
        "day="+target.isoformat(),
        "scanned="+str(summary["scanned"]),
        "linked="+str(summary["linked"]),
        "unmatched="+str(summary["unmatched"]),
        "conflicts="+str(summary["conflicts"]),
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
