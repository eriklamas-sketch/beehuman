#!/usr/bin/env bash
# Base LOCAL bhui para las pantallas de la etapa 1: Ola 1 + datos ficticios + migración etapa 1.
set -euo pipefail
cd "$(dirname "$0")"
# PostgREST se reinicia aparte (después de recrear la base)
(cd ../ola1 && ./montar_ui.sh >/dev/null)
P="psql -X -q -v ON_ERROR_STOP=1 -h /tmp -p 55432 -U postgres -d bhui"
$P -f semilla_ui_eventos.sql >/dev/null
for m in 20261104000000_eventos_laborales_idse 20261104000100_relacion_principal_con_rp 20261105000000_idse_bajas 20261105000100_idse_modificaciones 20261107000000_laboral_historial_tipo_email; do
  $P -f ../repo/beehuman-int/supabase/pendiente/$m.sql 2>&1 | grep -E "ERROR" || true
done
echo "bhui lista"
