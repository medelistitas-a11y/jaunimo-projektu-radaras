"""Paprasta HTTP Basic autentifikacija vienam administratoriui.

MVP skirtas vienam vartotojui. Jei ADMIN_PASSWORD_HASH nenustatytas (.env),
autentifikacija IŠJUNGTA (tinka tik lokaliam vystymui). Produkcijoje (kai
programa pasiekiama ne tik localhost) būtina nustatyti ADMIN_PASSWORD_HASH.
"""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

from app.config import Settings, get_settings

_security = HTTPBasic(auto_error=False)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    password_ok = _pwd_context.verify(credentials.password, settings.admin_password_hash)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neteisingas prisijungimo vardas arba slaptažodis",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)
