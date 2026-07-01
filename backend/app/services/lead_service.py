from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.repositories.advertising_repository import AdCampaignRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.lead_source_repository import LeadSourceRepository
from app.schemas.lead import LeadAssignRequest, LeadCreate, LeadMarkLostRequest, LeadUpdate
from app.services.business_utils import snapshot


class LeadServiceError(ValueError):
    pass


class LeadService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.lead_sources = LeadSourceRepository(db)
        self.customers = CustomerRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.campaigns = AdCampaignRepository(db)

    def list(self, workspace_id: UUID, search: str | None = None, status: LeadStatus | None = None, lead_source_id: UUID | None = None) -> list[Lead]:
        return self.leads.list_for_workspace(workspace_id, search, status.value if status else None, lead_source_id)

    def get(self, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        return self.leads.get(workspace_id, lead_id)

    def create(self, workspace_id: UUID, payload: LeadCreate, actor_user_id: UUID | None) -> Lead:
        self._validate_lead_source(workspace_id, payload.lead_source_id)
        self._validate_assigned_user(workspace_id, payload.assigned_user_id)
        self._validate_campaign(workspace_id, payload.campaign_id)
        lead = self.leads.create(Lead(workspace_id=workspace_id, status=LeadStatus.NEW.value, **payload.model_dump()))
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="CREATE",
            new_value=snapshot(lead),
        )
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update(self, workspace_id: UUID, lead_id: UUID, payload: LeadUpdate, actor_user_id: UUID | None) -> Lead | None:
        lead = self.get(workspace_id, lead_id)
        if lead is None:
            return None
        update_values = payload.model_dump(exclude_unset=True)
        if "lead_source_id" in update_values:
            self._validate_lead_source(workspace_id, update_values["lead_source_id"])
        if "assigned_user_id" in update_values:
            self._validate_assigned_user(workspace_id, update_values["assigned_user_id"])
        if "campaign_id" in update_values:
            self._validate_campaign(workspace_id, update_values["campaign_id"])
        if update_values.get("status") == LeadStatus.LOST and not update_values.get("loss_reason") and not lead.loss_reason:
            raise LeadServiceError("loss_reason is required when status is LOST")
        old_value = snapshot(lead)
        for field, value in update_values.items():
            setattr(lead, field, value.value if isinstance(value, LeadStatus) else value)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_UPDATE",
            old_value=old_value,
            new_value=snapshot(lead),
        )
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete(self, workspace_id: UUID, lead_id: UUID, actor_user_id: UUID | None) -> bool:
        lead = self.get(workspace_id, lead_id)
        if lead is None:
            return False
        old_value = snapshot(lead)
        self.leads.soft_delete(lead, actor_user_id)
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="LEAD_ARCHIVE",
            old_value=old_value,
            new_value=snapshot(lead),
        )
        self.db.commit()
        return True

    def assign(self, workspace_id: UUID, lead_id: UUID, payload: LeadAssignRequest, actor_user_id: UUID | None) -> Lead | None:
        lead = self.get(workspace_id, lead_id)
        if lead is None:
            return None
        self._validate_assigned_user(workspace_id, payload.assigned_user_id)
        old_value = snapshot(lead)
        lead.assigned_user_id = payload.assigned_user_id
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="ASSIGN",
            old_value=old_value,
            new_value=snapshot(lead),
        )
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def convert_lead_to_customer(self, workspace_id: UUID, lead_id: UUID, actor_user_id: UUID | None) -> Customer | None:
        lead = self.get(workspace_id, lead_id)
        if lead is None:
            return None
        if lead.status == LeadStatus.CONVERTED.value:
            raise LeadServiceError("Lead is already converted")
        old_value = snapshot(lead)
        customer = self.customers.create(
            Customer(
                workspace_id=workspace_id,
                name=lead.name,
                phone=lead.phone,
                instagram_username=lead.instagram_username,
            )
        )
        lead.status = LeadStatus.CONVERTED.value
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="CONVERT",
            old_value=old_value,
            new_value={"lead": snapshot(lead), "customer": snapshot(customer)},
        )
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Customer",
            entity_id=customer.id,
            action="CREATE_FROM_LEAD",
            new_value=snapshot(customer),
        )
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def mark_lost(self, workspace_id: UUID, lead_id: UUID, payload: LeadMarkLostRequest, actor_user_id: UUID | None) -> Lead | None:
        lead = self.get(workspace_id, lead_id)
        if lead is None:
            return None
        old_value = snapshot(lead)
        lead.status = LeadStatus.LOST.value
        lead.loss_reason = payload.loss_reason
        self.audit_logs.create(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            entity_type="Lead",
            entity_id=lead.id,
            action="MARK_LOST",
            old_value=old_value,
            new_value=snapshot(lead),
        )
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def _validate_lead_source(self, workspace_id: UUID, lead_source_id: UUID | None) -> None:
        if lead_source_id and self.lead_sources.get(workspace_id, lead_source_id) is None:
            raise LeadServiceError("Lead source does not exist in this workspace")

    def _validate_assigned_user(self, workspace_id: UUID, assigned_user_id: UUID | None) -> None:
        if assigned_user_id is None:
            return
        user = self.db.get(User, assigned_user_id)
        if user is None or not any(membership.workspace_id == workspace_id for membership in user.workspaces):
            raise LeadServiceError("Assigned user does not belong to this workspace")

    def _validate_campaign(self, workspace_id: UUID, campaign_id: UUID | None) -> None:
        if campaign_id and self.campaigns.get(workspace_id, campaign_id) is None:
            raise LeadServiceError("Campaign does not exist in this workspace")
