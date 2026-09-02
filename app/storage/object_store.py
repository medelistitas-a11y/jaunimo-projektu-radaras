"""Pasirenkama S3 suderinama objektų saugykla originaliems dokumentams.

SVARBU (produkcinio patikimumo reikalavimas): web ir cron servisai NEBĖRA
priklausomi nuo bendro lokalaus disko. Jei originalų saugoti nereikia
(numatytoji būsena — `S3_ENABLED` neįjungtas), originalas po teksto
ištraukimo tiesiog saugiai pašalinamas (žr. app/crawler/runner.py) — DB
lieka vienintelis šaltinis tiesai (ištrauktas tekstas, hash, metaduomenys).
Jei originalų reikia, ĮJUNKITE šį modulį (S3/MinIO/R2/Spaces ir pan., bet
kuri S3 API suderinama saugykla per `endpoint_url`), o NE bendrą Render/
Docker diską tarp servisų.
"""

from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger("app.storage.object_store")


def is_configured(settings: Settings) -> bool:
    return bool(
        settings.s3_enabled
        and settings.s3_bucket
        and settings.s3_access_key_id
        and settings.s3_secret_access_key
    )


def _get_client(settings: Settings):
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region or None,
    )


def upload_document(content: bytes, key: str, settings: Settings) -> str | None:
    """Įkelia originalų dokumentą į S3 suderinamą saugyklą. Grąžina
    ``s3://<bucket>/<key>`` identifikatorių arba None, jei neįjungta/nepavyko
    (klaida NIEKADA nesustabdo crawl — originalas tiesiog nebus išsaugotas).
    """
    if not is_configured(settings):
        return None
    try:
        client = _get_client(settings)
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content)
        return f"s3://{settings.s3_bucket}/{key}"
    except Exception as exc:  # noqa: BLE001 - niekada nesustabdo crawl dėl saugyklos klaidos
        logger.warning("Nepavyko įkelti dokumento į S3 (%s): %s", key, exc)
        return None


def generate_download_url(
    storage_uri: str, settings: Settings, expires_seconds: int = 3600
) -> str | None:
    """Sugeneruoja laikiną (presigned) atsisiuntimo nuorodą web sąsajai —
    web servisas NIEKADA neturi tiesioginės failų sistemos prieigos prie
    originalo, tik šią URL per S3 API.
    """
    if not storage_uri.startswith("s3://") or not is_configured(settings):
        return None
    try:
        _, _, rest = storage_uri.partition("s3://")
        bucket, _, key = rest.partition("/")
        client = _get_client(settings)
        return client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_seconds
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nepavyko sugeneruoti atsisiuntimo nuorodos (%s): %s", storage_uri, exc)
        return None


def delete_document(storage_uri: str, settings: Settings) -> bool:
    if not storage_uri.startswith("s3://") or not is_configured(settings):
        return False
    try:
        _, _, rest = storage_uri.partition("s3://")
        bucket, _, key = rest.partition("/")
        client = _get_client(settings)
        client.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nepavyko ištrinti dokumento (%s): %s", storage_uri, exc)
        return False
