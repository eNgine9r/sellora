from uuid import uuid4

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password


def test_argon2_password_hashing_round_trip() -> None:
    password_hash = hash_password("CorrectHorseBatteryStaple123!")

    assert password_hash.startswith("$argon2")
    assert verify_password("CorrectHorseBatteryStaple123!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_access_and_refresh_tokens_have_expected_subject_and_type() -> None:
    user_id = uuid4()

    access_payload = decode_token(create_access_token(user_id), "access")
    refresh_payload = decode_token(create_refresh_token(user_id), "refresh")

    assert access_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"
    assert refresh_payload["sub"] == str(user_id)
    assert refresh_payload["type"] == "refresh"

from types import SimpleNamespace

from app.services.auth_service import AuthService


def test_current_user_response_includes_workspace_memberships() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="owner@example.com",
        first_name="Owner",
        last_name="User",
        is_active=True,
        last_login_at=None,
        workspaces=[
            SimpleNamespace(
                workspace_id=workspace_id,
                workspace=SimpleNamespace(name="Demo Workspace", slug="demo", is_active=True),
                role=SimpleNamespace(name="OWNER"),
            )
        ],
    )

    response = AuthService.to_current_user_response(user)

    assert response.memberships[0].workspace_id == workspace_id
    assert response.memberships[0].workspace_name == "Demo Workspace"
    assert response.memberships[0].role == "OWNER"
