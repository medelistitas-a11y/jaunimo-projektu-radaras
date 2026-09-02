"""Integracinis testas: web ir worker veikia ATSKIRUOSE Docker konteineriuose
BE bendro tomo (volume) dokumentams.

Šis testas realiai paleidžia `docker compose` (db + web + worker), tada:
1. Patikrina per `docker inspect`, kad web ir worker konteineriai NETURI
   jokio bendro pavadinto tomo (išskyrus tai, kad abu turi TIK savo atskirą
   build image failų sistemą — jokio `documents_data` ar panašaus tomo nėra).
2. Įrašo Document eilutę per web konteinerį (simuliuojant tai, ką daro
   crawler po teksto ištraukimo) ir patikrina, kad worker konteineris mato
   TĄ PATĮ ištrauktą tekstą TIK per PostgreSQL — jokio failo tarp jų
   nekeliauja.
3. Patikrina, kad nė viename konteineryje NĖRA dokumentų failų kataloge
   (nes S3_ENABLED=false numatytoje .env.example konfigūracijoje —
   originalai apskritai nesaugomi jokiame diske).

Šis testas NĖRA paleidžiamas įprastu `pytest` (CI/greitu) prieigos būdu —
jam reikia Docker ir jis užtrunka (image build). Paleisti rankiniu būdu:

    make test-storage-decoupling

arba tiesiogiai:

    python -m pytest tests/test_storage_decoupling.py -v -m docker
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid

import pytest

pytestmark = pytest.mark.docker

COMPOSE_PROJECT = "mostai-storage-decoupling-test"

# MOSTAI_DOCKERTEST_OVERRIDE: skirta TIK šio testo paleidimui izoliuotoje
# sandbox aplinkoje, kur `docker build` negali tiesiogiai pasiekti PyPI per
# standartinę tinklo prieigą (žr. Dockerfile.dockertest). Realioje hostingo
# aplinkoje (Render, bet koks serveris su normalia tinklo prieiga) šis
# kintamasis NĖRA nustatytas ir naudojamas tikras `docker-compose.yml` su
# tikru `Dockerfile` be jokių pakeitimų.
_OVERRIDE_FILE = os.environ.get("MOSTAI_DOCKERTEST_OVERRIDE")
_COMPOSE_FILES = ["-f", "docker-compose.yml"]
if _OVERRIDE_FILE:
    _COMPOSE_FILES += ["-f", _OVERRIDE_FILE]


def _compose(*args: str, check: bool = True, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *_COMPOSE_FILES, "-p", COMPOSE_PROJECT, *args],
        cwd=None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def _docker_inspect_mounts(container: str) -> list[dict]:
    result = subprocess.run(
        ["docker", "inspect", container],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data[0]["Mounts"]


@pytest.fixture(scope="module")
def compose_stack():
    """Pakelia db+web+worker per docker compose šiam testui skirtu projekto
    vardu (nesikerta su bet kokiu jau veikiančiu `docker compose up` dev
    aplinkoje) ir garantuotai nuleidžia stack'ą testo pabaigoje."""
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True, timeout=10)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Docker nepasiekiamas šioje aplinkoje: {exc}")

    _compose("build", timeout=1800)
    _compose("up", "-d", timeout=300)
    try:
        _wait_healthy()
        yield
    finally:
        _compose("down", "-v", check=False, timeout=120)


def _wait_healthy(max_wait_seconds: int = 120) -> None:
    deadline = time.time() + max_wait_seconds
    last_error = None
    while time.time() < deadline:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-p",
                    COMPOSE_PROJECT,
                    "exec",
                    "-T",
                    "web",
                    "python",
                    "-c",
                    "import app.db",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return
            last_error = result.stderr
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(3)
    pytest.fail(f"web konteineris neatsakė per {max_wait_seconds}s: {last_error}")


def test_web_and_worker_share_no_volume(compose_stack):
    web_container = f"{COMPOSE_PROJECT}-web-1"
    worker_container = f"{COMPOSE_PROJECT}-worker-1"

    web_mounts = _docker_inspect_mounts(web_container)
    worker_mounts = _docker_inspect_mounts(worker_container)

    web_named_volumes = {m["Name"] for m in web_mounts if m.get("Type") == "volume"}
    worker_named_volumes = {m["Name"] for m in worker_mounts if m.get("Type") == "volume"}

    shared = web_named_volumes & worker_named_volumes
    assert (
        shared == set()
    ), f"web ir worker konteineriai neturėtų dalintis JOKIU tomu, bet rasta bendrų: {shared}"
    assert (
        web_named_volumes == set()
    ), f"web neturėtų turėti jokio pavadinto tomo: {web_named_volumes}"
    assert (
        worker_named_volumes == set()
    ), f"worker neturėtų turėti jokio pavadinto tomo: {worker_named_volumes}"


def test_document_written_by_one_service_visible_to_other_via_db_only(compose_stack):
    marker = uuid.uuid4().hex
    extracted_text = f"integraciniam testui skirtas tekstas {marker}"

    write_script = f"""
import datetime as dt
from app.db import SessionLocal
from app.models.document import Document

db = SessionLocal()
db.add(Document(
    source_url="https://example.lt/integraciniam-testui.pdf",
    file_type="pdf",
    content_hash="{marker}",
    downloaded_at=dt.datetime.now(dt.UTC),
    storage_path=None,
    extraction_method="text",
    extracted_text={extracted_text!r},
    extraction_status="ok",
))
db.commit()
db.close()
print("OK")
"""
    result = _compose("exec", "-T", "worker", "python", "-c", write_script, check=False, timeout=30)
    assert result.returncode == 0, f"worker nepavyko įrašyti Document: {result.stderr}"
    assert "OK" in result.stdout

    read_script = f"""
from app.db import SessionLocal
from app.models.document import Document

db = SessionLocal()
doc = db.query(Document).filter(Document.content_hash == "{marker}").one()
assert doc.extracted_text == {extracted_text!r}, doc.extracted_text
assert doc.storage_path is None
print("MATOMA_PER_DB")
db.close()
"""
    result = _compose("exec", "-T", "web", "python", "-c", read_script, check=False, timeout=30)
    assert result.returncode == 0, f"web nepavyko perskaityti Document per DB: {result.stderr}"
    assert "MATOMA_PER_DB" in result.stdout


def test_no_document_files_on_either_container_filesystem(compose_stack):
    """Patikrina, kad crawler'io ATSISIŲSTI dokumentai (S3_ENABLED=false) neliko
    diske. Repo viduje esantys testų fixture failai (`tests/fixtures/*.pdf`)
    ir bibliotekų šablonai (pvz. python-docx `default.docx`) yra image DALIS
    (COPY iš git repo per build), NE crawler'io atsisiųsti dokumentai — jie
    NEINDIKUOJA nutekėjimo, todėl aiškiai neįtraukiami į paiešką."""
    exclude_dirs = ["/usr", "/srv/tests", "/srv/.venv", "/srv/node_modules"]
    exclude_expr = " ".join(f"-path {d} -prune -o" for d in exclude_dirs)
    for service in ("web", "worker"):
        result = _compose(
            "exec",
            "-T",
            service,
            "sh",
            "-c",
            f"find / -xdev {exclude_expr} "
            "\\( -iname '*.pdf' -o -iname '*.docx' \\) -print 2>/dev/null | head -5",
            check=False,
            timeout=30,
        )
        leftover = result.stdout.strip()
        assert leftover == "", (
            f"{service} konteineryje rasta dokumentų failų diske (neturėtų būti, nes "
            f"S3_ENABLED=false ir originalai saugiai pašalinami po teksto ištraukimo): "
            f"{leftover}"
        )
