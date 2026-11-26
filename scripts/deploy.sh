#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

echo "==> Deploy en $BASE"
git fetch origin main
git reset --hard origin/main
chmod +x run-weekly-report.sh scripts/*.sh

if [ ! -f "$BASE/.env" ]; then
  echo "AVISO: falta .env; el cron fallará hasta configurarlo" >&2
fi

echo "Deploy OK: $(git rev-parse --short HEAD) $(git log -1 --pretty=%s)"
