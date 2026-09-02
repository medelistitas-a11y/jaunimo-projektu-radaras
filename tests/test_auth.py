"""Regresijos testas: passlib+bcrypt>=4.1 nesuderinamumo klaida (rasta rankiniu
patikrinimu — `make admin-password` mesdavo ValueError) neturi pasikartoti.
"""

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.web.auth import hash_password, require_admin, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("labai-slaptas-zodis-123")
    assert verify_password("labai-slaptas-zodis-123", hashed) is True


def test_verify_rejects_wrong_password():
    hashed = hash_password("teisingas")
    assert verify_password("neteisingas", hashed) is False


def test_verify_handles_garbage_hash_gracefully():
    assert verify_password("bet-koks", "ne-bcrypt-hash") is False


def test_require_admin_open_when_no_password_configured():
    settings = Settings(admin_password_hash="")
    result = require_admin(credentials=None, settings=settings)
    assert result == settings.admin_username


def test_require_admin_rejects_missing_credentials_when_configured():
    settings = Settings(admin_password_hash=hash_password("x"))
    with pytest.raises(HTTPException) as exc_info:
        require_admin(credentials=None, settings=settings)
    assert exc_info.value.status_code == 401


def test_require_admin_accepts_correct_credentials():
    from fastapi.security import HTTPBasicCredentials

    settings = Settings(admin_username="admin", admin_password_hash=hash_password("tikras"))
    creds = HTTPBasicCredentials(username="admin", password="tikras")
    assert require_admin(credentials=creds, settings=settings) == "admin"


def test_require_admin_rejects_wrong_password():
    from fastapi.security import HTTPBasicCredentials

    settings = Settings(admin_username="admin", admin_password_hash=hash_password("tikras"))
    creds = HTTPBasicCredentials(username="admin", password="neteisingas")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(credentials=creds, settings=settings)
    assert exc_info.value.status_code == 401
