SELECT
    id,
    to_char(inicio AT TIME ZONE :'report_tz', 'YYYY-MM-DD HH24:MI') AS inicio_local,
    to_char(fin AT TIME ZONE :'report_tz', 'YYYY-MM-DD HH24:MI') AS fin_local,
    motivo,
    estado
FROM reservas_sala
WHERE inicio >= :'period_start'::timestamptz
  AND inicio < :'period_end'::timestamptz
ORDER BY inicio, id;
