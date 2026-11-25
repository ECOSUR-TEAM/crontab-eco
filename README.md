# Reporte de reservas Eco (cron + PostgreSQL + Resend)

Consulta `reservas_sala` con `psql` (sólo `SELECT`), genera HTML con Python (biblioteca estándar) y lo envía por Resend. Todo vive en esta carpeta; no modifica el proyecto Eco.

## Requisitos

- `psql`, `python3` y `crontab` disponibles para el mismo usuario que ejecutará el cron.
- Un `.env` con credenciales de producción. No se instalan dependencias del proyecto Eco.

## Esquema real usado

Fuente: `../eco-bot/schema.sql` y `../eco-bot/src/features/reservas/infrastructure/adapters/postgres.go`.

| Columna | Tipo | Uso |
| --- | --- | --- |
| `id` | `BIGSERIAL` | identificador |
| `inicio` | `TIMESTAMPTZ NOT NULL` | filtro de periodo y columna `Inicio` |
| `fin` | `TIMESTAMPTZ NOT NULL` | columna `Fin` |
| `motivo` | `TEXT NOT NULL DEFAULT 'Reunión'` | columna `Motivo` |
| `estado` | `TEXT NOT NULL DEFAULT 'approved'` | columna `Estado` |

Estados vigentes: `approved` y `rejected`. Se incluyen todas las reservas del periodo, mostrando su estado real.

## Configuración

```bash
cd /ruta/a/crontab-weekly
cp .env.example .env
chmod 600 .env
```

Editar `.env`:

```env
DATABASE_URL=postgres://USUARIO:CONTRASENA@HOST:5432/NOMBRE_BASE?sslmode=require
RESEND_API_KEY=re_CAMBIAR_AQUI
REPORT_FROM="Eco <onboarding@resend.dev>"
REPORT_TO=destinatario@dominio-verificado.com
REPORT_TIMEZONE=America/Mexico_City
REPORT_PERIOD_TYPE=rolling_week
REPORT_DEDUPE=1
```

- El usuario de `DATABASE_URL` sólo necesita `SELECT` sobre `reservas_sala`.
- Con `onboarding@resend.dev`, Resend sólo permite enviar al correo de la cuenta o a direcciones `delivered@resend.dev`; para otros destinatarios hay que verificar un dominio.
- Alternativa interactiva para crear `.env`: `scripts/configure-env.sh`.
- Nunca versionar `.env`: ya está excluido por `.gitignore`.

## Periodos definidos

| `--period-type` | Periodo | Programación |
| --- | --- | --- |
| `rolling_week` | `ahora - 7 días` → `ahora` (segundos a cero) | viernes 06:00 |
| `calendar_month` | día 1 00:00 → día 1 del mes siguiente | 23:59 del último día |
| `previous_calendar_month` | mes natural anterior | alternativa si el cron no soporta `L` |

El tipo se fija en `.env` con `REPORT_PERIOD_TYPE` o se pasa por ejecución con `--period-type` (tiene prioridad). Todo se calcula en `REPORT_TIMEZONE`, sin fechas hardcodeadas.

## Ejecución manual (una sola vez)

```bash
./run-weekly-report.sh --period-type rolling_week
./run-weekly-report.sh --period-type calendar_month
```

Cada comando ejecuta la SQL, genera el HTML y envía **un único** correo. **No instala ni activa el cron.** El script valida `.env`, usa variables `:'...'` en `psql` con `ON_ERROR_STOP=1`, escapa el HTML y termina con error si falla SQL, HTML o Resend. El lock por directorio evita solapes.

## Activación del cron (queda permanente)

Editar `scheduler/crontab.production`: sustituir `/RUTA/crontab-weekly` por la ruta real y ajustar `PATH` según dónde estén `psql` y `python3`. Instalar una sola vez:

```bash
chmod +x run-weekly-report.sh scripts/*.sh
./run-weekly-report.sh --period-type rolling_week
tail -n 5 logs/weekly-report.log
(crontab -l 2>/dev/null; cat scheduler/crontab.production) | crontab -
crontab -l
```

La ejecución manual previa es sólo comprobación; el envío automático empieza con `crontab -`. Resultado:

```cron
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
0 6 * * 5 /ruta/a/crontab-weekly/run-weekly-report.sh --period-type rolling_week >> /ruta/a/crontab-weekly/logs/cron.out 2>&1
59 23 L * * /ruta/a/crontab-weekly/run-weekly-report.sh --period-type calendar_month >> /ruta/a/crontab-weekly/logs/cron.out 2>&1
```

Si el cron no soporta `L`, usar la línea comentada en `scheduler/crontab.production`:

```cron
0 0 1 * * /ruta/a/crontab-weekly/run-weekly-report.sh --period-type previous_calendar_month >> /ruta/a/crontab-weekly/logs/cron.out 2>&1
```

El cron corre con el mismo usuario dueño de `.env` y requiere el demonio `cron`/`crond` activo. Para desactivarlo: `crontab -l | grep -v 'run-weekly-report.sh' | crontab -`.

## Deduplicación y logs

`REPORT_DEDUPE=1` registra el periodo enviado en `state/sent-periods.log` (local, ignorado por Git); un reintento del mismo periodo no duplica correos. **No crea ni modifica tablas en Eco.** Conservar ese archivo en el servidor.

```bash
tail -n 50 logs/weekly-report.log
tail -n 20 logs/cron.out 2>/dev/null || true
```

Los logs omiten API keys, contraseñas y headers `Authorization`. Con `KEEP_ARTIFACTS=1` se guardan `out/last-report.csv` y `out/last-report.html`.

## Verificación del cálculo de periodos

```bash
python3 -m unittest discover -s python -p 'test_*.py' -v
```

## Arquitectura y responsabilidades

Flujo de una ejecución: cron → `run-weekly-report.sh` → `python/prepare_config.py` (periodo y validación) → `psql` con `sql/weekly-report.sql` → `python/generate_report.py` (HTML) → `python/send_report.py` (Resend) → registro en `state/sent-periods.log` y `logs/weekly-report.log`.

### Raíz

- `.env`: configuración privada (credenciales y parámetros); ignorado por Git.
- `.env.example`: plantilla con las variables obligatorias y opcionales.
- `.gitignore`: excluye secretos, logs, artefactos, estado y locks.
- `README.md`: única documentación operativa.
- `run-weekly-report.sh`: orquestador único; toma lock, calcula periodo, ejecuta SQL, genera HTML, envía correo y registra dedupe/resultado.

### `python/`

- `prepare_config.py`: valida `.env` y `DATABASE_URL`, calcula los tres periodos en `REPORT_TIMEZONE` y exporta la configuración al orquestador.
- `generate_report.py`: convierte el CSV de `psql` en HTML escapado, sin dependencias.
- `send_report.py`: envía el HTML por la API de Resend y oculta la API key en errores.
- `load_env.py`: parser de `.env` sin ejecutar shell; útil para inspeccionar variables.
- `test_prepare_config.py` / `test_generate_report.py`: verificaciones unitarias de periodos, URL y HTML.

### `scheduler/`

- `crontab.production`: las dos líneas de cron definitivas (viernes y fin de mes) y la alternativa sin soporte de `L`.

### `scripts/`

- `configure-env.sh`: crea `.env` de forma interactiva ocultando secretos.
- `verify-repo-safe.sh`: comprueba permisos, ignorados y ausencia de API keys antes de subir a repo.

### `sql/`

- `weekly-report.sql`: única consulta; filtra por `inicio` con parámetros `:'period_start'` / `:'period_end'` y convierte fechas con `:'report_tz'`.

