from __future__ import annotations

import os
import subprocess
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)


def alembic(*args: str) -> str:
    result = subprocess.run(["alembic", *args], cwd=os.path.dirname(os.path.dirname(__file__)), check=True, text=True, capture_output=True)
    return result.stdout + result.stderr


def reset_schema() -> None:
    with engine.begin() as connection:
        connection.execute(text('DROP SCHEMA public CASCADE'))
        connection.execute(text('CREATE SCHEMA public'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))


def seed_previous_head_records() -> dict[str, str]:
    workspace_id = str(uuid4())
    customer_id = str(uuid4())
    local_customer_id = str(uuid4())
    intl_customer_id = str(uuid4())
    invalid_customer_id = str(uuid4())
    address_one = str(uuid4())
    address_two = str(uuid4())
    connection_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO workspaces (id, name, slug, subscription_plan, is_active)
                VALUES (:id, 'Sprint 8F Migration', :slug, 'FREE', true)
            """),
            {"id": workspace_id, "slug": f"sprint-8f-{workspace_id[:8]}"},
        )
        for customer, name, phone in (
            (customer_id, "Default customer", "0671234567"),
            (local_customer_id, "Local phone", "067 123 45 67"),
            (intl_customer_id, "International phone", "+380671234567"),
            (invalid_customer_id, "Historical invalid phone", "legacy-phone"),
        ):
            connection.execute(
                text("""
                    INSERT INTO customers (id, workspace_id, name, phone, total_orders, total_spent)
                    VALUES (:id, :workspace_id, :name, :phone, 0, 0)
                """),
                {"id": customer, "workspace_id": workspace_id, "name": name, "phone": phone},
            )
        # Older installs had a stricter default-address index. Drop it in this
        # isolated migration gate to simulate duplicate production drift and
        # prove the 202607160023 repair CTE runs before the new partial index.
        connection.execute(text("DROP INDEX IF EXISTS uq_customer_addresses_one_default"))
        connection.execute(
            text("""
                INSERT INTO customer_addresses (id, workspace_id, customer_id, address_line1, phone, is_default, created_at, updated_at)
                VALUES
                  (:first, :workspace_id, :customer_id, 'Old warehouse', '0671234567', true, now() - interval '2 days', now() - interval '2 days'),
                  (:second, :workspace_id, :customer_id, 'New warehouse', '+380671234567', true, now() - interval '1 day', now() - interval '1 day')
            """),
            {"first": address_one, "second": address_two, "workspace_id": workspace_id, "customer_id": customer_id},
        )
        connection.execute(
            text("""
                INSERT INTO integration_connections (id, workspace_id, provider, connection_name, status, settings)
                VALUES (:id, :workspace_id, 'NOVA_POSHTA', 'Nova Poshta', 'CONNECTED', '{}')
            """),
            {"id": connection_id, "workspace_id": workspace_id},
        )
    return {
        "workspace_id": workspace_id,
        "customer_id": customer_id,
        "local_customer_id": local_customer_id,
        "intl_customer_id": intl_customer_id,
        "invalid_customer_id": invalid_customer_id,
        "connection_id": connection_id,
    }


def assert_previous_head_upgrade(ids: dict[str, str]) -> None:
    with engine.begin() as connection:
        phones = dict(
            connection.execute(
                text("SELECT name, phone FROM customers WHERE id IN (:local_id, :intl_id, :invalid_id)"),
                {"local_id": ids["local_customer_id"], "intl_id": ids["intl_customer_id"], "invalid_id": ids["invalid_customer_id"]},
            ).all()
        )
        assert phones["Local phone"] == "+380671234567"
        assert phones["International phone"] == "+380671234567"
        assert phones["Historical invalid phone"] == "legacy-phone"
        default_count = connection.execute(
            text("SELECT count(*) FROM customer_addresses WHERE workspace_id = :workspace_id AND customer_id = :customer_id AND is_default = true AND deleted_at IS NULL"),
            ids,
        ).scalar_one()
        assert default_count == 1
        index_exists = connection.execute(text("SELECT to_regclass('public.uq_customer_addresses_one_active_default') IS NOT NULL")).scalar_one()
        assert index_exists is True
        gate = connection.execute(
            text("SELECT provider_writes_allowed, provider_connection_verified_at FROM integration_connections WHERE id = :connection_id"),
            ids,
        ).one()
        assert gate.provider_writes_allowed is False
        assert gate.provider_connection_verified_at is None


def assert_partial_unique_index_enforced(ids: dict[str, str]) -> None:
    duplicate_id = str(uuid4())
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO customer_addresses (
                        id,
                        workspace_id,
                        customer_id,
                        address_line1,
                        is_default
                    )
                    VALUES (
                        :duplicate_id,
                        :workspace_id,
                        :customer_id,
                        'Duplicate default',
                        true
                    )
                """),
                {
                    "duplicate_id": duplicate_id,
                    "workspace_id": ids["workspace_id"],
                    "customer_id": ids["customer_id"],
                },
            )
    except IntegrityError as exc:
        database_error = str(exc.orig)
        assert "uq_customer_addresses_one_active_default" in database_error, database_error
    else:
        raise AssertionError("uq_customer_addresses_one_active_default allowed a second active default address")

    with engine.begin() as connection:
        default_count = connection.execute(
            text("""
                SELECT count(*)
                FROM customer_addresses
                WHERE workspace_id = :workspace_id
                  AND customer_id = :customer_id
                  AND is_default = true
                  AND deleted_at IS NULL
            """),
            ids,
        ).scalar_one()
        assert default_count == 1


def assert_current_revision(expected_revision: str) -> None:
    output = alembic("current")
    assert expected_revision in output, output


def assert_current_head() -> None:
    current_revision = alembic("current").split()[0]
    head_revision = alembic("heads").split()[0]
    assert current_revision == head_revision, (current_revision, head_revision)


def main() -> None:
    reset_schema()
    alembic("upgrade", "head")
    assert_current_head()

    reset_schema()
    alembic("upgrade", "202607150022")
    ids = seed_previous_head_records()
    alembic("upgrade", "202607160023")
    assert_previous_head_upgrade(ids)
    assert_partial_unique_index_enforced(ids)

    alembic("downgrade", "202607150022")
    alembic("upgrade", "202607160023")
    assert_current_revision("202607160023")


if __name__ == "__main__":
    main()
