from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meta_ad_connection import MetaAdConnection


class MetaAdsConnectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_current(self, workspace_id: UUID) -> MetaAdConnection | None:
        statement = (
            select(MetaAdConnection)
            .where(
                MetaAdConnection.workspace_id == workspace_id,
                MetaAdConnection.provider == "meta_ads",
                MetaAdConnection.deleted_at.is_(None),
            )
            .order_by(MetaAdConnection.created_at.desc())
        )
        return self.db.execute(statement).scalars().first()

    def add(self, connection: MetaAdConnection) -> MetaAdConnection:
        self.db.add(connection)
        self.db.flush()
        return connection

    def get_or_create(self, workspace_id: UUID) -> MetaAdConnection:
        connection = self.get_current(workspace_id)
        if connection is not None:
            return connection
        return self.add(MetaAdConnection(workspace_id=workspace_id, provider="meta_ads"))
