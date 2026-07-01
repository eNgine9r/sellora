from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.integration_connection import IntegrationConnection
from app.models.integration_credential import IntegrationCredential


class IntegrationConnectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_provider(self, workspace_id: UUID, provider: str) -> IntegrationConnection | None:
        stmt = select(IntegrationConnection).where(IntegrationConnection.workspace_id == workspace_id, IntegrationConnection.provider == provider, IntegrationConnection.deleted_at.is_(None)).options(selectinload(IntegrationConnection.credentials))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, connection: IntegrationConnection) -> IntegrationConnection:
        self.db.add(connection)
        self.db.flush()
        return connection


class IntegrationCredentialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_for_connection(self, workspace_id: UUID, connection_id: UUID) -> IntegrationCredential | None:
        stmt = select(IntegrationCredential).where(IntegrationCredential.workspace_id == workspace_id, IntegrationCredential.connection_id == connection_id, IntegrationCredential.deleted_at.is_(None)).order_by(IntegrationCredential.created_at.desc())
        return self.db.execute(stmt).scalars().first()

    def create(self, credential: IntegrationCredential) -> IntegrationCredential:
        self.db.add(credential)
        self.db.flush()
        return credential
