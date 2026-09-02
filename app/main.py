from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import SessionLocal
from app.seed.sources_seed import seed_sources
from app.web.routes_api import router as api_router
from app.web.routes_ui import router as ui_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = SessionLocal()
    try:
        created, updated = seed_sources(db)
        logger.info("Šaltinių registras įkeltas: sukurta %d, atnaujinta %d.", created, updated)
    except Exception:
        logger.exception("Nepavyko įkelti šaltinių registro paleidimo metu.")
    finally:
        db.close()
    if not settings.admin_password_hash and settings.app_env == "production":
        logger.warning(
            "ADMIN_PASSWORD_HASH nenustatytas produkcinėje aplinkoje — administravimo "
            "veiksmai (žymos, tikrinimo paleidimas) NEAPSAUGOTI slaptažodžiu."
        )
    yield


app = FastAPI(title="Mostai galimybių radaras", lifespan=lifespan)
app.include_router(api_router)
app.include_router(ui_router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
