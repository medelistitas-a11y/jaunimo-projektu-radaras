#!/usr/bin/env bash
# Sukuria PostgreSQL duomenų bazės atsarginę kopiją per docker compose.
# Naudojimas: ./scripts/backup.sh [failo_pavadinimas.sql.gz]
set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backups"
mkdir -p "$BACKUP_DIR"

FILENAME="${1:-mostai_$(date +%Y%m%d_%H%M%S).sql.gz}"
OUT_PATH="$BACKUP_DIR/$FILENAME"

echo "Kuriama atsarginė kopija: $OUT_PATH"
docker compose exec -T db pg_dump -U mostai -d mostai | gzip > "$OUT_PATH"
echo "Baigta: $OUT_PATH ($(du -h "$OUT_PATH" | cut -f1))"
