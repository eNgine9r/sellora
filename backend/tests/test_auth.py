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
