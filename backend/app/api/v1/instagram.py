from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from app.core.config import get_settings
from app.database.session import get_db
from app.dependencies.rbac import get_workspace_id, require_min_role
from app.models.role import RoleName
from app.models.user import User
from app.integrations.meta_instagram.exceptions import MetaInstagramError
from app.integrations.meta_instagram.schemas import InstagramConnectResponse, InstagramConnectionStatusResponse, InstagramDisconnectResponse, InstagramValidateResponse
from app.integrations.meta_instagram.services.connection_service import InstagramConnectionService
from app.integrations.meta_instagram.services.webhook_service import InstagramWebhookService
from app.integrations.meta_instagram.services.outbound_message_service import InstagramOutboundMessageService

router = APIRouter(prefix="/integrations/instagram", tags=["Instagram Messaging"])

def _raise(exc: MetaInstagramError):
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})

@router.post("/connect", response_model=InstagramConnectResponse)
def connect_instagram(workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        url, expires_at = InstagramConnectionService(db).start_connect(workspace_id, user.id); db.commit(); return InstagramConnectResponse(authorization_url=url, expires_at=expires_at)
    except MetaInstagramError as exc: _raise(exc)

def _oauth_frontend_redirect(status: str) -> RedirectResponse:
    target = get_settings().meta_oauth_frontend_callback_url or "/settings/integrations/instagram/callback"
    separator = "&" if "?" in target else "?"
    return RedirectResponse(f"{target}{separator}status={status}", status_code=303)

@router.get("/oauth/callback")
async def instagram_oauth_callback(state: str = Query(...), code: str = Query(...), db: Session = Depends(get_db)):
    try:
        c = await InstagramConnectionService(db).complete_callback(state, code); db.commit()
        if c.status == "CONNECTED":
            return _oauth_frontend_redirect("success")
        if c.status == "PERMISSION_MISSING":
            return _oauth_frontend_redirect("permission_missing")
        return _oauth_frontend_redirect("failed")
    except MetaInstagramError as exc:
        db.commit()
        status_map = {
            "META_ACCOUNT_PROFILE_VALIDATION_FAILED": "profile_failed",
            "META_ACCOUNT_IDENTITY_MISSING": "profile_failed",
            "META_ACCOUNT_NOT_PROFESSIONAL": "account_not_professional",
            "META_ACCOUNT_TYPE_UNVERIFIED": "account_type_unverified",
            "META_PERMISSION_MISSING": "permission_missing",
            "META_PERMISSION_VALIDATION_FAILED": "permission_failed",
            "META_OAUTH_STATE_ALREADY_USED": "invalid_state",
            "META_OAUTH_STATE_EXPIRED": "invalid_state",
            "META_OAUTH_STATE_INVALID": "invalid_state",
        }
        return _oauth_frontend_redirect(status_map.get(exc.code, "failed"))

@router.get("/status", response_model=InstagramConnectionStatusResponse)
def instagram_status(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)):
    c = InstagramConnectionService(db).status(workspace_id)
    if not c:
        return InstagramConnectionStatusResponse(workspace_id=workspace_id, status="DISCONNECTED")
    return InstagramConnectionStatusResponse(workspace_id=workspace_id, status=c.status, instagram_username=c.instagram_username, instagram_account_type=c.instagram_account_type, granted_permissions=c.granted_permissions, subscribed_webhook_fields=c.subscribed_webhook_fields, token_expires_at=c.token_expires_at, connected_at=c.connected_at, disconnected_at=c.disconnected_at, last_webhook_at=c.last_webhook_at, last_message_received_at=c.last_message_received_at, last_message_sent_at=c.last_message_sent_at, token_present=bool(c.access_token_ciphertext))

@router.post("/validate", response_model=InstagramValidateResponse)
async def validate_instagram(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    c, ok = await InstagramConnectionService(db).validate(workspace_id); db.commit()
    return InstagramValidateResponse(status=c.status if c else "DISCONNECTED", permission_ok=ok, token_present=bool(c and c.access_token_ciphertext))

@router.post("/disconnect", response_model=InstagramDisconnectResponse)
def disconnect_instagram(workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        c = InstagramConnectionService(db).disconnect(workspace_id, user.id); db.commit(); return InstagramDisconnectResponse(status=c.status, disconnected=True)
    except MetaInstagramError as exc: _raise(exc)

@router.get("/webhook")
def verify_webhook(hub_mode: str | None = Query(default=None, alias="hub.mode"), hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"), hub_challenge: str | None = Query(default=None, alias="hub.challenge"), db: Session = Depends(get_db)):
    try: return Response(content=InstagramWebhookService(db).verify_challenge(hub_mode, hub_verify_token, hub_challenge), media_type="text/plain")
    except MetaInstagramError as exc: _raise(exc)

@router.post("/webhook")
async def receive_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"), db: Session = Depends(get_db)):
    service = InstagramWebhookService(db)
    body = await request.body()
    try:
        service.validate_signature(body, x_hub_signature_256); payload = service.parse_body(body); event = service.persist_verified_event(body, payload); db.commit(); return {"accepted": True, "event_id": str(event.id), "status": event.status}
    except MetaInstagramError as exc: db.rollback(); _raise(exc)

@router.delete("/data")
def delete_instagram_data(confirm: bool = Query(False), workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    if not confirm: raise HTTPException(400, detail={"code": "META_CONFIRMATION_REQUIRED", "message": "Confirmation is required."})
    try:
        c = InstagramConnectionService(db).disconnect(workspace_id, user.id); db.commit(); return {"status": c.status, "token_deleted": True}
    except MetaInstagramError as exc: _raise(exc)
