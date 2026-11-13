from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from hashlib import sha256
import hmac
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
        message = EmailMessage()
        message["From"] = self.settings.auth_smtp_from
        message["To"] = email
        message["Subject"] = "Код підтвердження Sellora" if locale == "uk" else "Your Sellora verification code"
        message.set_content(
            f"Ваш код підтвердження Sellora: {code}. Він дійсний 10 хвилин.\n"
            "Якщо ви не реєструвалися в Sellora, проігноруйте цей лист."
            if locale == "uk" else
            f"Your Sellora verification code is {code}. It expires in 10 minutes.\n"
            "If you did not sign up for Sellora, you can ignore this email."
        )
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
