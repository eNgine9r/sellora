from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.lead_sources import router as lead_sources_router
from app.api.v1.leads import router as leads_router
from app.api.v1.products import router as products_router
from app.api.v1.inventory import router as inventory_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(lead_sources_router)
api_router.include_router(leads_router)
api_router.include_router(customers_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
