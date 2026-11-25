#!/usr/bin/env bash
set -euo pipefail
umask 077
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/libpq/bin:/usr/bin:/bin:/usr/sbin:/sbin"

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"

PERIOD_TYPE_ARG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --period-type|-p)
      if [ "$#" -lt 2 ]; then
        printf 'Falta el valor de --period-type\n' >&2
        exit 2
      fi
      PERIOD_TYPE_ARG="$2"
      shift 2
      ;;
    *)
      printf 'Argumento no reconocido: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

ENV_FILE="$BASE/.env"
LOG_FILE="$BASE/logs/weekly-report.log"
LOCK_DIR="$BASE/.run.lock"
STATE_FILE="$BASE/state/sent-periods.log"
mkdir -p "$BASE/logs" "$BASE/out" "$BASE/state"

log() {
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$1" "$2" >> "$LOG_FILE"
}

fail() {
  log ERROR "$1"
  exit 1
}

lock_age() {
  local stamp
  stamp="$(stat -f %m "$LOCK_DIR/owner" 2>/dev/null || stat -c %Y "$LOCK_DIR/owner" 2>/dev/null || printf '0')"
  printf '%s' "$(( $(date +%s) - stamp ))"
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  if [ -f "$LOCK_DIR/owner" ] && [ "$(lock_age)" -gt 300 ]; then
    log WARN "bloqueo obsoleto eliminado"
    rm -rf "$LOCK_DIR"
    mkdir "$LOCK_DIR" 2>/dev/null || { log WARN "otra ejecución en curso; se omite"; exit 0; }
  else
    log WARN "otra ejecución en curso; se omite"
    exit 0
  fi
fi
printf '%s pid=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$$" > "$LOCK_DIR/owner"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/eco-weekly-run.XXXXXX")"
cleanup() {
  rm -rf "$TMP_DIR"
  rm -rf "$LOCK_DIR"
}
trap cleanup EXIT INT TERM

if [ ! -f "$ENV_FILE" ]; then
  fail "falta el archivo .env privado"
fi

CONFIG_FILE="$TMP_DIR/config.sh"
CONFIG_ARGS=(--env "$ENV_FILE")
if [ -n "$PERIOD_TYPE_ARG" ]; then
  CONFIG_ARGS+=(--period-type "$PERIOD_TYPE_ARG")
fi
if ! python3 "$BASE/python/prepare_config.py" "${CONFIG_ARGS[@]}" > "$CONFIG_FILE"; then
  fail "configuración inválida"
fi
chmod 600 "$CONFIG_FILE"
. "$CONFIG_FILE"

log INFO "inicio tipo=$REPORT_PERIOD_TYPE periodo=$REPORT_PERIOD_LABEL"

DEDUPE_KEY="$REPORT_PERIOD_TYPE|$REPORT_PERIOD_START|$REPORT_PERIOD_END"
if [ "$REPORT_DEDUPE" = "1" ]; then
  if [ -f "$STATE_FILE" ] && awk -v key="$DEDUPE_KEY" '$2 == key { found = 1 } END { exit !found }' "$STATE_FILE"; then
    log INFO "periodo ya enviado; se omite"
    exit 0
  fi
fi

CSV_FILE="$TMP_DIR/report.csv"
if ! psql -X --csv -v ON_ERROR_STOP=1 \
  -v period_start="$REPORT_PERIOD_START" \
  -v period_end="$REPORT_PERIOD_END" \
  -v report_tz="$REPORT_TIMEZONE" \
  -f "$BASE/sql/weekly-report.sql" \
  "$DATABASE_URL" > "$CSV_FILE"; then
  fail "falló la consulta SQL"
fi
ROWS="$(awk 'NR > 1 { n++ } END { print n + 0 }' "$CSV_FILE")"
log INFO "SQL correcto filas=$ROWS"

HTML_FILE="$TMP_DIR/report.html"
if ! python3 "$BASE/python/generate_report.py" \
  --csv "$CSV_FILE" \
  --html "$HTML_FILE" \
  --period-label "$REPORT_PERIOD_LABEL" \
  --timezone "$REPORT_TIMEZONE"; then
  fail "falló la generación del HTML"
fi
log INFO "HTML generado filas=$ROWS"

SUBJECT="Eco - Reporte semanal de reservas"
case "$REPORT_PERIOD_TYPE" in
  calendar_month|previous_calendar_month)
    SUBJECT="Eco - Reporte mensual de reservas"
    ;;
esac

if ! python3 "$BASE/python/send_report.py" \
  --html "$HTML_FILE" \
  --subject "$SUBJECT"; then
  fail "falló el envío mediante Resend"
fi
log INFO "Resend aceptó el correo"

if [ "$REPORT_DEDUPE" = "1" ]; then
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$DEDUPE_KEY" >> "$STATE_FILE"
fi

if [ "${KEEP_ARTIFACTS:-0}" = "1" ]; then
  cp "$CSV_FILE" "$BASE/out/last-report.csv"
  cp "$HTML_FILE" "$BASE/out/last-report.html"
fi

log INFO "reporte completado correctamente"
