"""Paprasta HTTP Basic autentifikacija vienam administratoriui.

MVP skirtas vienam vartotojui. Jei ADMIN_PASSWORD_HASH nenustatytas (.env),
autentifikacija IŠJUNGTA (tinka tik lokaliam vystymui). Produkcijoje (kai
programa pasiekiama ne tik localhost) būtina nustatyti ADMIN_PASSWORD_HASH.

Naudojamas `bcrypt` paketas tiesiogiai (ne per `passlib`) — `passlib` 1.7.4
(paskutinis leidimas) yra nesuderinamas su `bcrypt` >= 4.1 (pašalintas
`__about__` atributas, kurio passlib tikisi), todėl per passlib visada
mesdavo `ValueError`. Tiesioginis `bcrypt` naudojimas paprastesnis ir be šios
suderinamumo problemos.
"""

from __future__ import annotations

import secrets

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings

_security = HTTPBasic(auto_error=False)


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Netinkamas/sugadintas hash formatas .env faile.
        return False


def require_admin(
    credentials: HTTPBasicCredentials | None = Depends(_security),
    settings: Settings = Depends(get_settings),
) -> str:
    if not settings.admin_password_hash:
        # Autentifikacija neįjungta (lokalus vystymas be .env slaptažodžio).
        return settings.admin_username

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reikalinga autentifikacija",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    password_ok = verify_password(credentials.password, settings.admin_password_hash)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neteisingas prisijungimo vardas arba slaptažodis",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
