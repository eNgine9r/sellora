"""Transfer the existing Sellora environment encrypted to one migration recipient.

Runs only in the existing staging Actions environment. No plaintext config, signing
key, provider token or canary password is written to logs or uploaded as an artifact.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.render.com/v1"

def get(path: str):
    request = Request(API + path, headers={
        "Accept": "application/json",
        "Authorization": "Bearer " + os.environ["RENDER_API_KEY"],
    })
    with urlopen(request, timeout=45) as response:
        return json.load(response)

def pages(path: str):
    cursor = None
    for _ in range(30):
        query = {"limit": 100}
        if cursor:
            query["cursor"] = cursor
        result = get(path + ("&" if "?" in path else "?") + urlencode(query))
        if not isinstance(result, list):
            raise RuntimeError("Unexpected Render pagination response")
        yield from result
        if len(result) < 100:
            return
        next_cursor = result[-1].get("cursor")
        if not next_cursor or next_cursor == cursor:
            raise RuntimeError("Missing Render pagination cursor")
        cursor = next_cursor
    raise RuntimeError("Render pagination exceeded bounded limit")

def variables(items):
    result = {}
    for item in items:
        value = item.get("envVar", item)
        key = value.get("key")
        if not isinstance(key, str) or not isinstance(value.get("value"), str):
            raise RuntimeError("Unexpected environment variable shape")
        result[key] = value["value"]
    return result

def main() -> None:
    services = [x.get("service", x) for x in pages(
        "/services?name=sellora-api-staging&type=web_service")]
    services = [x for x in services if x.get("name") == "sellora-api-staging"]
    if len(services) != 1:
        raise RuntimeError("Expected exactly one Sellora staging service")
    service = services[0]
    sid = service["id"]
    direct = variables(pages("/services/" + sid + "/env-vars"))
    merged = {}
    linked = []
    for item in pages("/env-groups?ownerId=" + service["ownerId"]):
        group = item.get("envGroup", item)
        if sid not in group.get("serviceIds", []):
            continue
        full = get("/env-groups/" + group["id"])
        full = full.get("envGroup", full)
        if full.get("secretFiles"):
            raise RuntimeError("Linked secret files require a separate migration inventory")
        values = variables(full.get("envVars", []))
        for key, value in values.items():
            if key in merged and merged[key] != value and key not in direct:
                raise RuntimeError("Conflicting linked group configuration")
            merged[key] = value
        linked.append(group["id"])
    merged.update(direct)
    for key in ("DATABASE_URL", "SECRET_KEY", "JWT_SECRET"):
        if not merged.get(key):
            raise RuntimeError("Required backend configuration missing: " + key)
    deploys = get("/services/" + sid + "/deploys?limit=1")
    latest = deploys[0].get("deploy", deploys[0]) if deploys else {}
    bundle = {
        "format": 1,
        "target": "btc-radar",
        "source": {
            "service_id": sid, "service_name": service["name"],
            "latest_deploy_id": latest.get("id"),
            "latest_deploy_status": latest.get("status"),
            "latest_deploy_commit": latest.get("commit", {}).get("id"),
            "linked_environment_group_count": len(linked),
        },
        "environment": merged,
    }
    recipient = os.environ["MIGRATION_RECIPIENT_CERT"]
    with tempfile.TemporaryDirectory(prefix="sellora-transfer-") as temporary:
        cert = Path(temporary) / "recipient.pem"
        cert.write_text(recipient)
        cert.chmod(0o600)
        # AES-GCM CMS authenticates ciphertext; RSA-OAEP wraps the content key.
        encrypted = subprocess.run([
            "openssl", "cms", "-encrypt", "-aes-256-gcm", "-binary",
            "-outform", "DER", "-recip", str(cert),
            "-keyopt", "rsa_padding_mode:oaep",
        ], input=json.dumps(bundle).encode(), capture_output=True)
        if encrypted.returncode:
            raise RuntimeError("Recipient encryption failed")
        output = Path("migration-encrypted")
        output.mkdir(mode=0o700)
        destination = output / "sellora-config.cms"
        destination.write_bytes(encrypted.stdout)
        destination.chmod(0o600)
    print(json.dumps({
        "encrypted": True, "target": "btc-radar",
        "environment_variable_count": len(merged),
        "linked_environment_group_count": len(linked),
        "source_commit": bundle["source"]["latest_deploy_commit"],
        "source_deploy_status": bundle["source"]["latest_deploy_status"],
        "ciphertext_sha256": hashlib.sha256(encrypted.stdout).hexdigest(),
    }))

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Do not print provider bodies or exceptions containing request data.
        raise SystemExit("Encrypted migration export failed: " + type(error).__name__)
