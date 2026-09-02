"""Sugeneruoja bcrypt hash administratoriaus slaptažodžiui (.env ADMIN_PASSWORD_HASH).

Naudojimas: python -m app.scripts.hash_password
"""

from __future__ import annotations

import getpass

from app.web.auth import hash_password


def main() -> None:
    password = getpass.getpass("Įveskite naują administratoriaus slaptažodį: ")
    confirm = getpass.getpass("Pakartokite slaptažodį: ")
    if password != confirm:
        print("Slaptažodžiai nesutampa.")
        raise SystemExit(1)
    if len(password) < 8:
        print("Slaptažodis turi būti bent 8 simbolių.")
        raise SystemExit(1)
    print("\nĮrašykite šią eilutę į .env failą:\n")
    print(f"ADMIN_PASSWORD_HASH={hash_password(password)}")


if __name__ == "__main__":
    main()
