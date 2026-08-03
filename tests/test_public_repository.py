from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _run_script(script: str, database_path: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_PATH"] = str(database_path)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_documented_seed_commands_run_directly_and_are_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "public-setup.sqlite"
    for script in ("create_demo_accounts.py", "seed_demo_data.py"):
        first = _run_script(script, database_path)
        second = _run_script(script, database_path)
        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        assert first.stdout == second.stdout
    assert database_path.exists()
