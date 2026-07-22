from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

EXPECTED_REVISION = os.getenv("EXPECTED_ALEMBIC_REVISION", "202607220034")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "alembic.ini"

    if not config_path.is_file():
        print(f"Alembic verification failed: missing {config_path}", file=sys.stderr)
        return 1

    config = Config(str(config_path))
    script = ScriptDirectory.from_config(config)
    revision = script.get_revision(EXPECTED_REVISION)

    if revision is None:
        known_heads = ", ".join(script.get_heads()) or "<none>"
        print(
            "Alembic verification failed: "
            f"revision {EXPECTED_REVISION} is absent from the packaged revision map. "
            f"Known heads: {known_heads}",
            file=sys.stderr,
        )
        return 1

    heads = ", ".join(script.get_heads()) or "<none>"
    print(f"Alembic revision verified: {revision.revision}")
    print(f"Alembic packaged heads: {heads}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
