from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from hashlib import sha256
import hmac
from html import escape
import secrets
import smtplib
import ssl
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.auth.session_service import SessionAuthenticationService, SessionTokens
from app.auth.social_oauth import Profile, Provider
from app.core.config import Settings
from app.repositories.auth_identity_repository import AuthEmailRepository, AuthIdentityRepository
from app.repositories.user_repository import UserRepository


class PublicAuthError(Exception):
    pass


class PublicAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.identities = AuthIdentityRepository(db)
        self.sessions = SessionAuthenticationService(db)

    def social_sign_in(self, provider: Provider, profile: Profile) -> SessionTokens:
        owner_id = self.identities.owner(provider, profile.subject)
        user = self.users.get_by_id(owner_id) if owner_id else None
        if user is None or not user.is_active:
            raise PublicAuthError("account_required")
        user.last_login_at = datetime.now(UTC)
        return self.sessions.create(user.id)

    def link(self, provider: Provider, profile: Profile, user_id: UUID, session_id: UUID, cookie: str | None) -> None:
        if not self.sessions.lock_active_refresh(cookie, user_id, session_id):
            raise PublicAuthError("session_required")
        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise PublicAuthError("session_required")
        owner = self.identities.owner(provider, profile.subject)
        if owner == user_id:
            self.db.commit()
            return
        if owner is not None:
            raise PublicAuthError("provider_in_use")
        try:
            self.identities.add(user_id, provider, profile.subject)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise PublicAuthError("provider_in_use") from None

    def register(self, email: str, first_name: str, last_name: str, *, password_hash: str | None = None,
                 provider: Provider | None = None, subject: str | None = None) -> SessionTokens:
        if self.users.email_exists(email):
            raise PublicAuthError("account_exists")
        try:
            user = self.users.create(email=email, password_hash=password_hash,
                                     first_name=first_name or email.split("@", 1)[0][:100], last_name=last_name)
            if provider is not None and subject is not None:
                self.identities.add(user.id, provider, subject)
            user.last_login_at = datetime.now(UTC)
            self.db.flush()
            return self.sessions.create(user.id, authenticated_with_password=password_hash is not None)
        except IntegrityError:
            self.db.rollback()
            raise PublicAuthError("account_exists") from None


def seal(settings: Settings, kind: str, claims: dict, minutes: int) -> str:
    return jwt.encode(
        {**claims, "purpose": f"sellora-public-auth:{kind}",
         "exp": datetime.now(UTC) + timedelta(minutes=minutes)},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )


def unseal(settings: Settings, kind: str, value: str | None) -> dict | None:
    if not value or len(value) > 3500:
        return None
    try:
        claims = jwt.decode(value, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                            options={"require_exp": True})
        return claims if claims.get("purpose") == f"sellora-public-auth:{kind}" else None
    except JWTError:
        return None


def email_enabled(settings: Settings) -> bool:
    return bool(settings.auth_registration_enabled and settings.auth_smtp_host and settings.auth_smtp_from
                and bool(settings.auth_smtp_user) == bool(settings.auth_smtp_password))


def _verification_email(sender: str, recipient: str, locale: str, code: str) -> EmailMessage:
    if locale == "uk":
        subject = "Код підтвердження Sellora"
        heading = "Підтвердьте свою email-адресу"
        instruction = "Введіть цей код на сторінці реєстрації Sellora."
        expiry = "Код дійсний 10 хвилин."
        unsolicited = "Якщо ви не запитували цей код, просто проігноруйте лист."
    else:
        subject = "Your Sellora verification code"
        heading = "Verify your email address"
        instruction = "Enter this code on the Sellora registration page."
        expiry = "The code expires in 10 minutes."
        unsolicited = "If you didn’t request this code, you can ignore this email."

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(f"{heading}\n\n{instruction}\n\n{code}\n\n{expiry}\n\n{unsolicited}")
    message.add_alternative(f"""\
<!doctype html>
<html lang="{'uk' if locale == 'uk' else 'en'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#f3f1fb;font-family:Arial,sans-serif;color:#101426;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f3f1fb;">
    <tr><td align="center" style="padding:32px 16px;">
      <!--[if mso]><table role="presentation" width="520" cellspacing="0" cellpadding="0"><tr><td><![endif]-->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;">
        <tr><td bgcolor="#13112b" style="padding:20px 28px;border-radius:18px 18px 0 0;
          border-top:4px solid #8b5cf6;background-color:#13112b;color:#f5f3ff;">
          <span style="font-size:24px;line-height:30px;font-weight:700;letter-spacing:-0.6px;">Sellora</span>
        </td></tr>
        <tr><td bgcolor="#ffffff" style="padding:28px;border:1px solid #e2dcef;border-top:0;
          background-color:#ffffff;color:#101426;border-radius:0 0 18px 18px;">
          <h1 style="margin:0 0 12px;font-size:25px;line-height:32px;font-weight:700;">{heading}</h1>
          <p style="margin:0 0 22px;font-size:16px;line-height:24px;color:#414a62;">{instruction}</p>
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr><td align="center" bgcolor="#f1ebff" style="padding:16px 8px;border:1px solid #dfd1ff;
              border-radius:12px;background-color:#f1ebff;color:#54239b;font-family:Consolas,'Courier New',monospace;
              font-size:34px;font-weight:700;letter-spacing:5px;line-height:42px;white-space:nowrap;">{escape(code)}</td></tr>
          </table>
          <p style="margin:12px 0 22px;font-size:14px;line-height:20px;color:#414a62;">{expiry}</p>
          <p style="margin:0;padding-top:16px;border-top:1px solid #e2dcef;font-size:13px;line-height:20px;
            color:#515a71;">{unsolicited}</p>
        </td></tr>
      </table>
      <!--[if mso]></td></tr></table><![endif]-->
    </td></tr>
  </table>
</body>
</html>
""", subtype="html")
    return message


class EmailRegistrationService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.repo = AuthEmailRepository(db)
        self.auth = PublicAuthService(db)

    def _hmac(self, value: str) -> str:
        return hmac.new(self.settings.jwt_secret.encode(), value.encode(), sha256).hexdigest()

    def send(self, email: str, locale: str, binding: str) -> None:
        key = self._hmac(f"sellora-email:{email}")
        code = f"{secrets.randbelow(1_000_000):06d}"
        digest = self._hmac(f"sellora-email-code:{key}:{binding}:{code}")
        now = datetime.now(UTC)
        if not self.repo.reserve(key, digest, now):
            return
        if self.auth.users.email_exists(email):
            return
        # Do not hold an application DB connection during mail delivery.
        self.db.rollback()
        try:
            self._deliver(email, locale, code)
        except (OSError, smtplib.SMTPException, ValueError):
            self.repo.clear_failed_delivery(key, digest, datetime.now(UTC))
            raise PublicAuthError("delivery_failed") from None

    def _deliver(self, email: str, locale: str, code: str) -> None:
        message = _verification_email(self.settings.auth_smtp_from, email, locale, code)
        with smtplib.SMTP_SSL(self.settings.auth_smtp_host, self.settings.auth_smtp_port,
                              context=ssl.create_default_context(), timeout=8) as client:
            if self.settings.auth_smtp_user and self.settings.auth_smtp_password:
                client.login(self.settings.auth_smtp_user, self.settings.auth_smtp_password.get_secret_value())
            client.send_message(message)

    def confirm(self, email: str, code: str, binding: str, *, first_name: str, last_name: str = "",
                password: str | None = None, provider: Provider | None = None,
                subject: str | None = None) -> SessionTokens:
        key = self._hmac(f"sellora-email:{email}")
        digest = self._hmac(f"sellora-email-code:{key}:{binding}:{code}")
        row = self.repo.lock(key)
        if row is None or row.digest is None or row.attempts >= 5 or row.expires_at <= datetime.now(UTC):
            raise PublicAuthError("invalid_code")
        if not hmac.compare_digest(row.digest, digest):
            row.attempts += 1
            self.db.commit()
            raise PublicAuthError("invalid_code")
        row.digest = None
        password_digest = hash_password(password) if password is not None else None
        return self.auth.register(email, first_name, last_name, password_hash=password_digest,
                                  provider=provider, subject=subject)
