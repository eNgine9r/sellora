from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from datetime import date

from app.models.ad_campaign import AdCampaign
from app.models.ad_metric import AdMetric
from app.models.customer import Customer
from app.models.import_job import ImportJob
from app.models.import_job_log import ImportJobLog
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant


class ImportJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: ImportJob) -> ImportJob:
        self.db.add(job); self.db.flush(); return job

    def get(self, workspace_id: UUID, job_id: UUID) -> ImportJob | None:
        stmt = select(ImportJob).where(ImportJob.workspace_id == workspace_id, ImportJob.id == job_id, ImportJob.deleted_at.is_(None))
        return self.db.execute(stmt).scalar_one_or_none()


class ImportJobLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, log: ImportJobLog) -> ImportJobLog:
        self.db.add(log); self.db.flush(); return log

    def list(self, workspace_id: UUID, import_job_id: UUID, status: str | None = None) -> list[ImportJobLog]:
        stmt: Select[tuple[ImportJobLog]] = select(ImportJobLog).where(ImportJobLog.workspace_id == workspace_id, ImportJobLog.import_job_id == import_job_id)
        if status:
            stmt = stmt.where(ImportJobLog.status == status)
        return list(self.db.execute(stmt.order_by(ImportJobLog.row_number.asc().nulls_last(), ImportJobLog.created_at.asc())).scalars())


class ImportEntityLookupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_customer(self, workspace_id: UUID, phone: str | None = None, instagram_username: str | None = None) -> Customer | None:
        conditions = []
        if phone:
            conditions.append(Customer.phone == phone)
        if instagram_username:
            conditions.append(Customer.instagram_username == instagram_username)
        if not conditions:
            return None
        return self.db.execute(select(Customer).where(Customer.workspace_id == workspace_id, Customer.deleted_at.is_(None), or_(*conditions))).scalar_one_or_none()

    def find_product_by_sku(self, workspace_id: UUID, sku: str | None) -> Product | None:
        if not sku:
            return None
        return self.db.execute(select(Product).where(Product.workspace_id == workspace_id, Product.sku == sku, Product.deleted_at.is_(None))).scalar_one_or_none()

    def find_product_by_name_or_sku(self, workspace_id: UUID, name: str | None, sku: str | None) -> Product | None:
        conditions = []
        if sku:
            conditions.append(Product.sku == sku)
        if name:
            conditions.append(Product.name == name)
        if not conditions:
            return None
        return self.db.execute(select(Product).where(Product.workspace_id == workspace_id, Product.deleted_at.is_(None), or_(*conditions))).scalar_one_or_none()

    def find_variant(self, workspace_id: UUID, sku: str | None = None, product_id: UUID | None = None, color: str | None = None, size: str | None = None) -> ProductVariant | None:
        stmt = select(ProductVariant).where(ProductVariant.workspace_id == workspace_id, ProductVariant.deleted_at.is_(None))
        if sku:
            return self.db.execute(stmt.where(ProductVariant.sku == sku)).scalar_one_or_none()
        if product_id:
            return self.db.execute(stmt.where(ProductVariant.product_id == product_id, ProductVariant.color == color, ProductVariant.size == size)).scalar_one_or_none()
        return None

    def inventory_by_variant(self, workspace_id: UUID, variant_id: UUID) -> Inventory | None:
        return self.db.execute(select(Inventory).where(Inventory.workspace_id == workspace_id, Inventory.product_variant_id == variant_id, Inventory.deleted_at.is_(None))).scalar_one_or_none()

    def similar_order_exists(self, workspace_id: UUID, customer_id: UUID | None, revenue, created_at) -> bool:
        if customer_id is None or created_at is None:
            return False
        stmt = select(Order).where(Order.workspace_id == workspace_id, Order.customer_id == customer_id, Order.revenue == revenue, Order.created_at >= created_at)
        return self.db.execute(stmt).first() is not None


    def find_ad_campaign_by_name(self, workspace_id: UUID, name: str | None) -> AdCampaign | None:
        if not name:
            return None
        return self.db.execute(select(AdCampaign).where(AdCampaign.workspace_id == workspace_id, AdCampaign.name == name, AdCampaign.deleted_at.is_(None))).scalar_one_or_none()

    def find_ad_campaign_by_id(self, workspace_id: UUID, campaign_id: UUID | str | None) -> AdCampaign | None:
        if not campaign_id:
            return None
        return self.db.execute(select(AdCampaign).where(AdCampaign.workspace_id == workspace_id, AdCampaign.id == campaign_id, AdCampaign.deleted_at.is_(None))).scalar_one_or_none()

    def find_ad_metric_by_campaign_date(self, workspace_id: UUID, campaign_id: UUID, metric_date: date) -> AdMetric | None:
        return self.db.execute(select(AdMetric).where(AdMetric.workspace_id == workspace_id, AdMetric.campaign_id == campaign_id, AdMetric.metric_date == metric_date, AdMetric.deleted_at.is_(None))).scalar_one_or_none()
