"""Incremental Meta Ads read-only provider sync for Your Jewelry.

Writes provider-backed campaign/advertising metrics only; never sales or payment.
"""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.workspace import Workspace
from app.models.meta_ad_connection import MetaAdConnection
from app.services.meta_ads_live_sync_service import MetaAdsLiveSyncService

def main()->int:
    today=datetime.now(ZoneInfo("Europe/Kyiv")).date()
    start=today-timedelta(days=2)
    with SessionLocal() as db:
        ws=db.scalar(select(Workspace).where(
            Workspace.slug=="sellora",Workspace.name=="Your Jewelry",Workspace.is_active.is_(True)))
        if ws is None:
            print("ADS_SYNC_NO_WORKSPACE"); return 4
        conn=db.scalar(select(MetaAdConnection).where(
            MetaAdConnection.workspace_id==ws.id,
            MetaAdConnection.deleted_at.is_(None)))
        if conn is None or not conn.connected_by_user_id:
            print("ADS_SYNC_NO_AUTHORIZED_ACTOR"); return 4
        try:
            report=MetaAdsLiveSyncService(db).sync(ws.id,conn.connected_by_user_id,start,today)
        except Exception as exc:
            db.rollback()
            print("META_ADS_INCREMENTAL_FAILED","error_type="+type(exc).__name__,
                  "code="+str(getattr(exc,"code","UNKNOWN"))[:90])
            return 2
    print("META_ADS_INCREMENTAL_OK",
          "from="+start.isoformat(),
          "to="+today.isoformat(),
          "status="+str(report.get("status")),
          "currency="+str(report.get("spend_currency")),
          "rate="+str(report.get("exchange_rate_source")))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
