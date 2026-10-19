#!/usr/bin/env python3
"""Exercise the release against a disposable PostgreSQL database, never the live DB."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy/raspberry/compose.yaml"


def run(*args, **kwargs):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Already built ARM64 release image")
    parser.add_argument("--expected-revision", required=True, help="Full commit baked into that image")
    args = parser.parse_args()
    image = json.loads(run("docker", "image", "inspect", args.image).stdout)[0]
    assert image["Architecture"] == "arm64", "Expected an ARM64 release"
    assert image["Config"]["User"] == "10001:10001", "Expected the unprivileged image user"
    assert image["Config"]["Labels"]["org.opencontainers.image.revision"] == args.expected_revision

    suffix = secrets.token_hex(4)
    project = "sellora-smoke-" + suffix
    network = project + "-isolated"
    database = project + "-db"
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    evidence = {"image_id": image["Id"], "revision": args.expected_revision, "architecture": "arm64"}
    with tempfile.TemporaryDirectory(prefix=project + "-") as temporary:
        folder = Path(temporary)
        password = secrets.token_hex(24)
        pg_env = folder / "postgres.env"
        pg_env.write_text("POSTGRES_USER=sellora_smoke\nPOSTGRES_DB=sellora_smoke\nPOSTGRES_PASSWORD=" + password + "\n")
        pg_env.chmod(0o600)
        backend_env = folder / "backend.env"
        backend_env.write_text(
            "DATABASE_URL=postgresql+psycopg://sellora_smoke:" + password + "@" + database + "/sellora_smoke\n"
            "SECRET_KEY=" + secrets.token_hex(32) + "\nJWT_SECRET=" + secrets.token_hex(32) + "\n"
            "RENDER_GIT_COMMIT=" + "b" * 40 + "\n"
            "META_INSTAGRAM_WEBHOOK_WORKER_ENABLED=false\n"
            "META_INSTAGRAM_SEND_ENABLED=false\nMETA_INSTAGRAM_AUTO_SEND_ENABLED=false\n"
            "META_INSTAGRAM_AUTO_ANALYSIS_ENABLED=false\nAI_FEATURE_ENABLED=false\n"
            "AI_CUSTOMER_DATA_EXTRACTION_ENABLED=false\n"
        )
        backend_env.chmod(0o600)
        override = folder / "network.yaml"
        override.write_text("networks:\n  default:\n    external: true\n    name: " + network + "\n")
        env = dict(os.environ, SELLORA_IMAGE=args.image, SELLORA_ENV_FILE=str(backend_env),
                   SELLORA_PORT=str(port), SELLORA_WORKER_ENABLED="false", SELLORA_SEND_ENABLED="false")
        compose = ["docker", "compose", "--project-name", project, "-f", str(COMPOSE), "-f", str(override)]

        def db_query(sql):
            return run("docker", "exec", database, "psql", "-U", "sellora_smoke", "-d",
                       "sellora_smoke", "-At", "-c", sql).stdout.strip()

        run("docker", "network", "create", network)
        try:
            run("docker", "run", "-d", "--name", database, "--network", network,
                "--memory", "256m", "--cpus", "0.5", "--pids-limit", "128",
                "--env-file", str(pg_env), "postgres:16-alpine")
            for _ in range(60):
                ready = subprocess.run(["docker", "exec", database, "pg_isready", "-U", "sellora_smoke",
                                        "-d", "sellora_smoke"], capture_output=True)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise AssertionError("Disposable PostgreSQL did not become ready")

            startup = subprocess.run(["docker", "run", "--rm", "--network", network,
                                      "--env-file", str(backend_env), args.image],
                                     text=True, capture_output=True, timeout=60)
            assert startup.returncode == 78, "Empty schema must block startup"
            assert "DATABASE_SCHEMA_MISMATCH" in startup.stderr
            table_count = db_query("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            assert table_count == "0", "Startup must not create tables or run migrations"
            evidence["empty_schema_blocked_without_writes"] = True
            print("PASS: empty database blocks API startup without creating tables", flush=True)

            run("docker", "run", "--rm", "--network", network, "--env-file", str(backend_env),
                "--entrypoint", "python", args.image, "-m", "alembic", "upgrade", "head", timeout=180)
            revision = db_query("SELECT version_num FROM alembic_version")
            evidence["database_revision"] = revision
            print("PASS: packaged migrations upgraded only the disposable database", flush=True)

            run(*compose, "config", "--quiet", env=env)
            run(*compose, "up", "-d", "--wait", "--wait-timeout", "120", "backend", env=env, timeout=150)
            base = "http://127.0.0.1:" + str(port)
            with urlopen(base + "/health", timeout=5) as response:
                health = json.load(response)
            assert health["status"] == "ok"
            assert health["runtime_commit"] == args.expected_revision, "Copied Render revision must not override image identity"
            assert not health["meta_webhook_worker_enabled"]
            assert not health["meta_webhook_worker_running"]
            with urlopen(base + "/docs", timeout=5) as response:
                assert response.status == 200
            with urlopen(base + "/api/v1/openapi.json", timeout=5) as response:
                schema = json.load(response)
                assert "/api/v1/onboarding/status" in schema["paths"]
            statuses = {}
            for path, headers in [
                ("/api/v1/auth/me", {}),
                ("/api/v1/onboarding/status", {"X-Workspace-ID": "00000000-0000-0000-0000-000000000001"}),
            ]:
                try:
                    urlopen(Request(base + path, headers=headers), timeout=5)
                except HTTPError as exc:
                    assert exc.code == 401
                    statuses[path] = exc.code
                else:
                    raise AssertionError("Anonymous protected endpoint was accessible")
            evidence["anonymous_protected_endpoint_statuses"] = statuses

            container = run(*compose, "ps", "-q", "backend", env=env).stdout.strip()
            state = json.loads(run("docker", "inspect", container).stdout)[0]
            assert state["State"]["Health"]["Status"] == "healthy"
            assert state["HostConfig"]["ReadonlyRootfs"]
            assert state["HostConfig"]["Memory"] == 768 * 1024 * 1024
            assert state["HostConfig"]["NanoCpus"] == 1_000_000_000
            assert state["HostConfig"]["PidsLimit"] == 128
            assert state["NetworkSettings"]["Ports"]["10000/tcp"][0]["HostIp"] == "127.0.0.1"
            run("docker", "exec", container, "python", "-c",
                "import os,tempfile; assert os.getuid()==10001; "
                "f=tempfile.TemporaryFile(dir='/app/storage/imports'); f.write(b'storage-probe'); f.close()")
            run("docker", "exec", container, "python", "-c",
                "from app.core.config import get_settings; s=get_settings(); "
                "assert not any([s.meta_instagram_send_enabled, s.meta_instagram_auto_send_enabled, "
                "s.meta_instagram_auto_analysis_enabled, s.ai_feature_enabled, s.ai_customer_data_extraction_enabled])")
            evidence.update(health=health, outbound_and_ai_disabled=True, read_only_root=True, storage_writable=True,
                            resource_limits_verified=True, loopback_binding=True)
            print("PASS: healthy non-root API, protected routes, storage, loopback and limits", flush=True)
            print(json.dumps(evidence, indent=2), flush=True)
        finally:
            subprocess.run(compose + ["down", "--volumes", "--remove-orphans"], env=env,
                           capture_output=True, timeout=90)
            subprocess.run(["docker", "rm", "-f", "-v", database], capture_output=True, timeout=30)
            subprocess.run(["docker", "network", "rm", network], capture_output=True, timeout=30)


if __name__ == "__main__":
    main()
