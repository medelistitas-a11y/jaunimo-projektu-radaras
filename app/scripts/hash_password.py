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
    raw_hash = hash_password(password)
    # Docker Compose interpoliuoja "$" ženklus .env faile (taip pat kaip "environment:"
    # reikšmėse) — todėl kiekvienas "$" turi būti padvigubintas į "$$", kitaip bcrypt hash
    # bus sugadintas (žr. .env.example komentarą). Render/kitų platformų aplinkos kintamųjų
    # UI paprastai TOKIOS interpoliacijos nedaro, todėl ten reikia NEPADVIGUBINTO originalo.
    escaped_hash = raw_hash.replace("$", "$$")
    print("\n--- .env failui (Docker Compose lokaliai) ---")
    print(f"ADMIN_PASSWORD_HASH={escaped_hash}")
    print("\n--- Render / kitos hostingo aplinkos kintamųjų UI (be dvigubinimo) ---")
    print(f"ADMIN_PASSWORD_HASH={raw_hash}")


if __name__ == "__main__":
    main()
