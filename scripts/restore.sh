#!/usr/bin/env bash
# Atkuria PostgreSQL duomenų bazę iš backup.sh sukurtos .sql.gz kopijos.
# ĮSPĖJIMAS: ištrina esamus duomenis paskirties duomenų bazėje.
# Naudojimas: ./scripts/restore.sh backups/mostai_20260101_120000.sql.gz
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Naudojimas: $0 <backup_failas.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Failas nerastas: $BACKUP_FILE"
  exit 1
fi

read -r -p "Tai IŠTRINS esamus duomenis 'mostai' duomenų bazėje. Tęsti? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Atšaukta."
  exit 0
fi

echo "Atkuriama iš: $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U mostai -d mostai
echo "Atkūrimas baigtas."
