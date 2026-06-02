from types import SimpleNamespace
from uuid import uuid4

from app.models.customer import Customer
from app.models.lead import Lead, LeadStatus
from app.schemas.customer import CustomerCreate
from app.schemas.lead import LeadAssignRequest, LeadCreate, LeadMarkLostRequest
from app.services.customer_service import CustomerService
from app.services.lead_service import LeadService


class FakeDb:
    def commit(self) -> None:
        pass

    def refresh(self, model) -> None:
        pass

    def get(self, model, model_id):
        return None


class FakeAuditLogs:
    def __init__(self) -> None:
        self.records = []

    def create(self, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeLeadSources:
    def get(self, workspace_id, lead_source_id):
        return None


class FakeLeadRepository:
    def __init__(self, leads: list[Lead] | None = None) -> None:
        self.leads = {lead.id: lead for lead in leads or []}

    def get(self, workspace_id, lead_id):
        lead = self.leads.get(lead_id)
        if lead and lead.workspace_id == workspace_id and lead.deleted_at is None:
            return lead
        return None

    def create(self, lead: Lead) -> Lead:
        lead.id = lead.id or uuid4()
        self.leads[lead.id] = lead
        return lead

    def soft_delete(self, lead: Lead, deleted_by):
        lead.deleted_by = deleted_by
        return lead


class FakeCustomerRepository:
    def __init__(self) -> None:
        self.customers = {}

    def create(self, customer: Customer) -> Customer:
        customer.id = customer.id or uuid4()
        self.customers[customer.id] = customer
        return customer


class FakeCustomerServiceRepository(FakeCustomerRepository):
    def list(self, workspace_id, search=None):
        return [customer for customer in self.customers.values() if customer.workspace_id == workspace_id]

    def get(self, workspace_id, customer_id):
        customer = self.customers.get(customer_id)
        if customer and customer.workspace_id == workspace_id:
            return customer
        return None


def _lead_service(leads: list[Lead] | None = None) -> LeadService:
    service = LeadService.__new__(LeadService)
    service.db = FakeDb()
    service.leads = FakeLeadRepository(leads)
    service.lead_sources = FakeLeadSources()
    service.customers = FakeCustomerRepository()
    service.audit_logs = FakeAuditLogs()
    return service


def test_lead_creation_defaults_to_new_and_writes_audit_log() -> None:
    workspace_id = uuid4()
    service = _lead_service()

    lead = service.create(workspace_id, LeadCreate(name="New lead", phone="555"), actor_user_id=uuid4())

    assert lead.status == LeadStatus.NEW.value
    assert lead.workspace_id == workspace_id
    assert service.audit_logs.records[-1]["action"] == "CREATE"


def test_lead_assignment_sets_assigned_user_and_writes_audit_log() -> None:
    workspace_id = uuid4()
    assignee_id = uuid4()
    lead = Lead(id=uuid4(), workspace_id=workspace_id, name="Assigned lead", status=LeadStatus.NEW.value)
    service = _lead_service([lead])
    service._validate_assigned_user = lambda workspace_id, assigned_user_id: None

    updated = service.assign(workspace_id, lead.id, LeadAssignRequest(assigned_user_id=assignee_id), actor_user_id=uuid4())

    assert updated.assigned_user_id == assignee_id
    assert service.audit_logs.records[-1]["action"] == "ASSIGN"


def test_lead_conversion_creates_customer_and_keeps_converted_lead() -> None:
    workspace_id = uuid4()
    lead = Lead(id=uuid4(), workspace_id=workspace_id, name="Convert Me", phone="555", instagram_username="sellora", status=LeadStatus.NEW.value)
    service = _lead_service([lead])

    customer = service.convert_lead_to_customer(workspace_id, lead.id, actor_user_id=uuid4())

    assert customer.name == lead.name
    assert customer.phone == lead.phone
    assert customer.instagram_username == lead.instagram_username
    assert lead.status == LeadStatus.CONVERTED.value
    assert any(record["action"] == "CONVERT" for record in service.audit_logs.records)


def test_lead_lost_requires_reason_and_writes_audit_log() -> None:
    workspace_id = uuid4()
    lead = Lead(id=uuid4(), workspace_id=workspace_id, name="Lost lead", status=LeadStatus.NEW.value)
    service = _lead_service([lead])

    updated = service.mark_lost(workspace_id, lead.id, LeadMarkLostRequest(loss_reason="No budget"), actor_user_id=uuid4())

    assert updated.status == LeadStatus.LOST.value
    assert updated.loss_reason == "No budget"
    assert service.audit_logs.records[-1]["action"] == "MARK_LOST"


def test_customer_creation_writes_customer_audit_log() -> None:
    service = CustomerService.__new__(CustomerService)
    service.db = FakeDb()
    service.customers = FakeCustomerServiceRepository()
    service.audit_logs = FakeAuditLogs()
    workspace_id = uuid4()

    customer = service.create(workspace_id, CustomerCreate(name="Customer", phone="555"), actor_user_id=uuid4())

    assert customer.workspace_id == workspace_id
    assert service.audit_logs.records[-1]["entity_type"] == "Customer"
    assert service.audit_logs.records[-1]["action"] == "CREATE"


def test_workspace_isolation_returns_no_lead_from_other_workspace() -> None:
    lead = Lead(id=uuid4(), workspace_id=uuid4(), name="Other workspace", status=LeadStatus.NEW.value)
    service = _lead_service([lead])

    assert service.get(uuid4(), lead.id) is None
