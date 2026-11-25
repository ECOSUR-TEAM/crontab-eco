#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$BASE/.env"
umask 077

sq() {
  python3 -c 'import shlex,sys; print(shlex.quote(sys.argv[1]))' "$1"
}

read_secret() {
  local prompt="$1" value=""
  printf '%s (no se mostrará): ' "$prompt" >&2
  if [ -t 0 ]; then
    stty -echo
    IFS= read -r value || true
    stty echo
  else
    IFS= read -r value || true
  fi
  printf '\n' >&2
  printf '%s' "$value"
}

read_value() {
  local prompt="$1" default="$2" value=""
  printf '%s [%s]: ' "$prompt" "$default" >&2
  IFS= read -r value || true
  if [ -n "$value" ]; then
    printf '%s' "$value"
  else
    printf '%s' "$default"
  fi
}

if [ -e "$ENV_FILE" ]; then
  printf 'Ya existe .env. ¿Sobrescribirlo? [s/N]: ' >&2
  IFS= read -r answer || true
  case "$answer" in
    s|S|si|SI|Si) ;;
    *) printf 'No se modificó nada.\n' >&2; exit 0 ;;
  esac
fi

database_url="$(read_secret 'DATABASE_URL del servidor de trabajo')"
if [ -z "$database_url" ]; then
  printf 'DATABASE_URL es obligatoria.\n' >&2
  exit 1
fi
api_key="$(read_secret 'RESEND_API_KEY')"
if [ -z "$api_key" ]; then
  printf 'RESEND_API_KEY es obligatoria.\n' >&2
  exit 1
fi
report_from="$(read_value 'REPORT_FROM' 'Eco <onboarding@resend.dev>')"
report_to="$(read_value 'REPORT_TO' 'delivered@resend.dev')"
timezone="$(read_value 'REPORT_TIMEZONE' 'America/Mexico_City')"

{
  printf 'DATABASE_URL=%s\n' "$(sq "$database_url")"
  printf 'RESEND_API_KEY=%s\n' "$(sq "$api_key")"
  printf 'REPORT_FROM=%s\n' "$(sq "$report_from")"
  printf 'REPORT_TO=%s\n' "$(sq "$report_to")"
  printf 'REPORT_TIMEZONE=%s\n' "$(sq "$timezone")"
  printf 'REPORT_MODE=%s\n' "$(sq 'production')"
  printf 'REPORT_PERIOD_TYPE=%s\n' "$(sq 'rolling_week')"
  printf 'REPORT_DEDUPE=%s\n' "$(sq '1')"
} > "$ENV_FILE"

chmod 600 "$ENV_FILE"
printf 'Configuración guardada en %s con permisos 600. No se imprimieron secretos.\n' "$ENV_FILE" >&2
