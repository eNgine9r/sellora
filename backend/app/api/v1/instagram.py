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
from app.integrations.meta_instagram.config import WEBHOOK_SUBSCRIPTIONS

router = APIRouter(prefix="/integrations/instagram", tags=["Instagram Messaging"])

def _raise(exc: MetaInstagramError):
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})

@router.post("/connect", response_model=InstagramConnectResponse)
def connect_instagram(workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        url, expires_at = InstagramConnectionService(db).start_connect(workspace_id, user.id); db.commit(); return InstagramConnectResponse(authorization_url=url, expires_at=expires_at)
    except MetaInstagramError as exc: _raise(exc)


def _status_response(workspace_id: UUID, c) -> InstagramConnectionStatusResponse:
    settings = get_settings()
    confirmed = list(c.subscribed_webhook_fields or []) if c else []
    missing = [field for field in WEBHOOK_SUBSCRIPTIONS if field not in set(confirmed)]
    required_confirmed = not missing
    webhook_active = bool(c and c.status == "CONNECTED" and required_confirmed)
    return InstagramConnectionStatusResponse(
        workspace_id=workspace_id,
        status=c.status if c else "DISCONNECTED",
        instagram_username=c.instagram_username if c else None,
        instagram_account_type=c.instagram_account_type if c else None,
        granted_permissions=c.granted_permissions if c else [],
        subscribed_webhook_fields=confirmed,
        confirmed_webhook_fields=confirmed,
        missing_webhook_fields=missing,
        token_expires_at=c.token_expires_at if c else None,
        connected_at=c.connected_at if c else None,
        disconnected_at=c.disconnected_at if c else None,
        last_webhook_at=c.last_webhook_at if c else None,
        last_message_received_at=c.last_message_received_at if c else None,
        last_message_sent_at=c.last_message_sent_at if c else None,
        token_present=bool(c and c.access_token_ciphertext),
        send_enabled=bool(settings.meta_instagram_send_enabled),
        auto_send_enabled=bool(settings.meta_instagram_auto_send_enabled),
        webhook_active=webhook_active,
        callback_configured=bool(settings.meta_oauth_redirect_uri),
        verify_token_configured=bool(settings.meta_webhook_verify_token),
        account_subscription_active=webhook_active,
        required_fields_confirmed=required_confirmed,
        webhook_processing_enabled=bool(settings.meta_instagram_webhook_processing_enabled),
        last_error_code=c.last_error_code if c else None,
        last_error_message=c.last_error_message if c else None,
    )

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
        if c.status == "WEBHOOK_INACTIVE":
            return _oauth_frontend_redirect("webhook_inactive")
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
            "META_WEBHOOK_SUBSCRIPTION_FAILED": "webhook_inactive",
            "META_WEBHOOK_SUBSCRIPTION_INCOMPLETE": "webhook_inactive",
        }
        return _oauth_frontend_redirect(status_map.get(exc.code, "failed"))

@router.get("/status", response_model=InstagramConnectionStatusResponse)
def instagram_status(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.ANALYST)), db: Session = Depends(get_db)):
    c = InstagramConnectionService(db).status(workspace_id)
    return _status_response(workspace_id, c)

@router.post("/validate", response_model=InstagramValidateResponse)
async def validate_instagram(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    c, ok = await InstagramConnectionService(db).validate(workspace_id); db.commit()
    return InstagramValidateResponse(status=c.status if c else "DISCONNECTED", permission_ok=ok, token_present=bool(c and c.access_token_ciphertext))

@router.post("/disconnect", response_model=InstagramDisconnectResponse)
async def disconnect_instagram(workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        c = await InstagramConnectionService(db).disconnect(workspace_id, user.id); db.commit(); return InstagramDisconnectResponse(status=c.status, disconnected=True)
    except MetaInstagramError as exc: _raise(exc)

@router.post("/webhooks/subscribe", response_model=InstagramConnectionStatusResponse)
async def subscribe_instagram_webhooks(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        c = await InstagramConnectionService(db).subscribe_webhooks(workspace_id); db.commit(); return _status_response(workspace_id, c)
    except MetaInstagramError as exc: _raise(exc)

@router.get("/webhooks/status", response_model=InstagramConnectionStatusResponse)
async def instagram_webhook_status(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        c = await InstagramConnectionService(db).refresh_webhook_status(workspace_id); db.commit(); return _status_response(workspace_id, c)
    except MetaInstagramError as exc: _raise(exc)

@router.post("/webhooks/unsubscribe", response_model=InstagramConnectionStatusResponse)
async def unsubscribe_instagram_webhooks(workspace_id: UUID = Depends(get_workspace_id), _: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    try:
        c = await InstagramConnectionService(db).unsubscribe_webhooks(workspace_id); db.commit(); return _status_response(workspace_id, c)
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
async def delete_instagram_data(confirm: bool = Query(False), workspace_id: UUID = Depends(get_workspace_id), user: User = Depends(require_min_role(RoleName.OWNER)), db: Session = Depends(get_db)):
    if not confirm: raise HTTPException(400, detail={"code": "META_CONFIRMATION_REQUIRED", "message": "Confirmation is required."})
    try:
        c = await InstagramConnectionService(db).disconnect(workspace_id, user.id); db.commit(); return {"status": c.status, "token_deleted": True}
    except MetaInstagramError as exc: _raise(exc)
