from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nova_poshta_operation import NovaPoshtaOperation, NovaPoshtaOperationType


class NovaPoshtaOperationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_update(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        operation_type: str = NovaPoshtaOperationType.CREATE_TTN.value,
    ) -> NovaPoshtaOperation | None:
        stmt = (
            select(NovaPoshtaOperation)
            .where(
                NovaPoshtaOperation.workspace_id == workspace_id,
                NovaPoshtaOperation.shipment_id == shipment_id,
                NovaPoshtaOperation.operation_type == operation_type,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        workspace_id: UUID,
        shipment_id: UUID,
        operation_type: str = NovaPoshtaOperationType.CREATE_TTN.value,
    ) -> NovaPoshtaOperation | None:
        stmt = select(NovaPoshtaOperation).where(
            NovaPoshtaOperation.workspace_id == workspace_id,
            NovaPoshtaOperation.shipment_id == shipment_id,
            NovaPoshtaOperation.operation_type == operation_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, operation: NovaPoshtaOperation) -> NovaPoshtaOperation:
        self.db.add(operation)
        self.db.flush()
        return operation
