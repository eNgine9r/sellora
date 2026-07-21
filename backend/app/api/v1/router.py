from app.api.v1.advertising import router as advertising_router
from fastapi import APIRouter
from app.api.v1.ai import router as ai_router
from app.api.v1.direct import router as direct_router
from app.api.v1.direct_customer_automation import router as direct_customer_automation_router
from app.api.v1.direct_customer_extraction import router as direct_customer_extraction_router
from app.api.v1.direct_live import router as direct_live_router
from app.api.v1.direct_sync import router as direct_sync_router

from app.api.v1.analytics import router as analytics_router
from app.api.v1.attachments import router as attachments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.finance import router as finance_router
from app.api.v1.lead_sources import router as lead_sources_router
from app.api.v1.leads import router as leads_router
from app.api.v1.meta_ads import router as meta_ads_router
from app.api.v1.meta_ads_mock import router as meta_ads_mock_router
from app.api.v1.nova_poshta import router as nova_poshta_router
from app.api.v1.products import router as products_router
from app.api.v1.tags import router as tags_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.orders import router as orders_router
from app.api.v1.order_fulfillments import router as order_fulfillments_router
from app.api.v1.order_fulfillment_operations import router as order_fulfillment_operations_router
from app.api.v1.shipments import router as shipments_router
from app.api.v1.import_center import router as import_center_router
from app.api.v1.instagram import router as instagram_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.workspace_users import router as workspace_users_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(direct_router)
api_router.include_router(direct_customer_automation_router)
api_router.include_router(direct_customer_extraction_router)
api_router.include_router(direct_live_router)
api_router.include_router(direct_sync_router)
api_router.include_router(advertising_router)
api_router.include_router(analytics_router)
api_router.include_router(auth_router)
api_router.include_router(lead_sources_router)
api_router.include_router(leads_router)
api_router.include_router(customers_router)
api_router.include_router(feedback_router)
api_router.include_router(finance_router)
api_router.include_router(products_router)
api_router.include_router(import_center_router)
api_router.include_router(instagram_router)
api_router.include_router(inventory_router)
api_router.include_router(onboarding_router)
api_router.include_router(orders_router)
api_router.include_router(order_fulfillments_router)
api_router.include_router(order_fulfillment_operations_router)
api_router.include_router(meta_ads_router)
api_router.include_router(meta_ads_mock_router)
api_router.include_router(nova_poshta_router)
api_router.include_router(shipments_router)
api_router.include_router(tags_router)
api_router.include_router(attachments_router)
api_router.include_router(workspaces_router)
api_router.include_router(workspace_users_router)
