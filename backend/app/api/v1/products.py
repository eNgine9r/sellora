from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.schemas.product import ProductCreate, ProductImageCreate, ProductImageResponse, ProductResponse, ProductUpdate, ProductVariantCreate, ProductVariantResponse, ProductVariantUpdate
from app.services.product_service import ProductService, ProductServiceError

router = APIRouter(prefix="/products", tags=["Products"])


def _bad_request(exc: ProductServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[ProductResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_products(workspace_id: UUID = Depends(get_workspace_id), search: str | None = Query(default=None), category: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[ProductResponse]:
    return ProductService(db).list_products(workspace_id, search, category)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ProductResponse:
    return ProductService(db).create_product(workspace_id, payload, current_user.id)


@router.get("/variants", response_model=list[ProductVariantResponse], dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def list_variants(workspace_id: UUID = Depends(get_workspace_id), product_id: UUID | None = Query(default=None), db: Session = Depends(get_db)) -> list[ProductVariantResponse]:
    return ProductService(db).list_variants(workspace_id, product_id)


@router.post("/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
def create_variant(payload: ProductVariantCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ProductVariantResponse:
    try:
        return ProductService(db).create_variant(workspace_id, payload, current_user.id)
    except ProductServiceError as exc:
        raise _bad_request(exc)


@router.put("/variants/{variant_id}", response_model=ProductVariantResponse)
def update_variant(variant_id: UUID, payload: ProductVariantUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ProductVariantResponse:
    try:
        variant = ProductService(db).update_variant(workspace_id, variant_id, payload, current_user.id)
    except ProductServiceError as exc:
        raise _bad_request(exc)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")
    return variant


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(variant_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> Response:
    deleted = ProductService(db).delete_variant(workspace_id, variant_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{product_id}", response_model=ProductResponse, dependencies=[Depends(require_min_role(RoleName.ANALYST))])
def get_product(product_id: UUID, workspace_id: UUID = Depends(get_workspace_id), db: Session = Depends(get_db)) -> ProductResponse:
    product = ProductService(db).get_product(workspace_id, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: UUID, payload: ProductUpdate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ProductResponse:
    product = ProductService(db).update_product(workspace_id, product_id, payload, current_user.id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> Response:
    deleted = ProductService(db).delete_product(workspace_id, product_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{product_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
def add_product_image(product_id: UUID, payload: ProductImageCreate, workspace_id: UUID = Depends(get_workspace_id), current_user: User = Depends(require_min_role(RoleName.MANAGER)), db: Session = Depends(get_db)) -> ProductImageResponse:
    image = ProductService(db).add_product_image(workspace_id, product_id, payload, current_user.id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return image
