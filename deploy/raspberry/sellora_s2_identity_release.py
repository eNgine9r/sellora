#!/usr/bin/env python3
"""Guarded S2 release on btc-radar; keeps a rollback copy of both configs."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import urllib.request

OLD_ID = "sha256:a3e3d3b596077f3f3abc2bdc871548e68a93c91abf191dc966b8d20b17919549"
NEW_ID = "sha256:33be76916fd87821a3f02addb900e188047308407189a78eaa3a8c72b3d5580f"
OLD_TAG = "sellora-backend:cost-confirmation-candidate-8dabf7a"
NEW_TAG = "sellora-backend:s2-identity-candidate-df3dcd2"
REVISION = "df3dcd29de48de0b5e1292d1087b431490e720a4"
ENV_FILE = Path("/home/btcradar/.config/sellora/deployment.env")
PLAN_FILE = Path("/home/btcradar/.local/state/sellora/api-watchdog.json")
COMPOSE_DIR = Path("/home/btcradar/commander-workspaces/sellora-migration/repo/deploy/raspberry")
CONTAINER = "sellora-rpi-backend-1"
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("SELLORA_", "COMPOSE_"))}
COMPOSE = ["docker", "compose", "--project-name", "sellora-rpi", "--project-directory", str(COMPOSE_DIR),
           "--env-file", str(ENV_FILE), "-f", str(COMPOSE_DIR / "compose.yaml"),
           "-f", str(COMPOSE_DIR / "no-memcg.yaml")]


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, env=ENV, timeout=120)
    if result.returncode:
        raise RuntimeError("Команда завершилася помилкою: " + " ".join(args[:2]))
    return result.stdout


def inspect_container():
    return json.loads(run("docker", "inspect", CONTAINER))[0]


def ready():
    try:
        with urllib.request.urlopen("http://127.0.0.1:18000/health/ready", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def atomic_write(path, data):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Неочікуваний тип конфігураційного файлу")
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, name = tempfile.mkstemp(prefix=".sellora-s2-update-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def backup(path, data):
    fd, name = tempfile.mkstemp(prefix=".sellora-s2-backup-", dir=path.parent)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return name


def compose_config():
    return json.loads(run(*COMPOSE, "config", "--format", "json"))["services"]["backend"]


def assert_same_environment(service, container):
    live = dict(item.split("=", 1) for item in container["Config"]["Env"] if "=" in item)
    if any(str(value) != live.get(key) for key, value in service["environment"].items()):
        raise RuntimeError("Параметри Compose не збігаються з поточним сервером")


def wait_for(image):
    for _ in range(100):
        try:
            current = inspect_container()
            if current["Image"] == image and current["State"].get("Health", {}).get("Status") == "healthy" and ready():
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if os.getuid() != ENV_FILE.stat().st_uid:
        raise RuntimeError("Запустіть під власником конфігурації btcradar")
    if ENV_FILE.is_symlink() or PLAN_FILE.is_symlink():
        raise RuntimeError("Символічні посилання конфігурації не підтримуються")
    lock_path = PLAN_FILE.with_suffix(".lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old_env = ENV_FILE.read_bytes()
        old_plan = PLAN_FILE.read_bytes()
        decoded = old_env.decode("utf-8")
        pattern = r"(?m)^SELLORA_IMAGE=" + re.escape(OLD_TAG) + r"[ \t]*$"
        if len(re.findall(pattern, decoded)) != 1:
            raise RuntimeError("Конфігурація образу змінилася; зупинено")
        plan = json.loads(old_plan)
        if plan.get("expected_image") != OLD_ID or plan.get("readiness_required") is not True:
            raise RuntimeError("Конфігурація watchdog змінилася; зупинено")
        current = inspect_container()
        if current["Image"] != OLD_ID or not ready():
            raise RuntimeError("Поточний сервер не відповідає очікуваному стану")
        candidate = json.loads(run("docker", "image", "inspect", NEW_TAG))[0]
        if candidate["Id"] != NEW_ID or candidate["Config"].get("Labels", {}).get("org.opencontainers.image.revision") != REVISION:
            raise RuntimeError("Кандидатний образ або його ревізія змінилися")
        before = compose_config()
        if before["image"] != OLD_TAG:
            raise RuntimeError("Compose вказує на інший образ")
        assert_same_environment(before, current)
        if not args.execute:
            print("ПЕРЕВІРКА УСПІШНА: сервер, образ і конфігурація готові. Змін не внесено.")
            return
        new_env = re.sub(pattern, "SELLORA_IMAGE=" + NEW_TAG, decoded).encode("utf-8")
        plan["expected_image"] = NEW_ID
        new_plan = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        backup(ENV_FILE, old_env)
        backup(PLAN_FILE, old_plan)
        changed = False
        try:
            atomic_write(ENV_FILE, new_env)
            changed = True
            updated = compose_config()
            if updated["image"] != NEW_TAG:
                raise RuntimeError("Compose не вибрав перевірений образ")
            assert_same_environment(updated, current)
            run(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "--pull", "never", "backend")
            if not wait_for(NEW_ID):
                raise RuntimeError("Новий сервер не пройшов перевірку готовності")
            atomic_write(PLAN_FILE, new_plan)
            print("ГОТОВО: новий backend працює, readiness і watchdog узгоджені.")
        except BaseException:
            if changed:
                atomic_write(ENV_FILE, old_env)
                atomic_write(PLAN_FILE, old_plan)
                try:
                    run(*COMPOSE, "up", "-d", "--no-deps", "--force-recreate", "--pull", "never", "backend")
                    if wait_for(OLD_ID):
                        print("ВІДКАТ: попередній backend і конфігурацію відновлено.")
                    else:
                        print("УВАГА: перевірка відновленого backend не пройшла.")
                except Exception:
                    print("УВАГА: автоматичний відкат backend не завершився; потрібна перевірка.")
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("СТОП:", str(exc))
        raise SystemExit(1)
