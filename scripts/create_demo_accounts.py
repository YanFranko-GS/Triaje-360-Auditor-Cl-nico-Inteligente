from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth_service import DEMO_ACCOUNT_PASSWORDS, seed_demo_accounts


if __name__ == "__main__":
    count = seed_demo_accounts()
    print(f"Cuentas profesionales creadas o verificadas: {count}")
    print("Paciente: identificador 76543210 · segundo dato 1999-01-01")
    for username, (_user_id, password, facility) in DEMO_ACCOUNT_PASSWORDS.items():
        print(f"{username} | {password} | {facility}")
