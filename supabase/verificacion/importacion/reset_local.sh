#!/usr/bin/env bash
# bhui nueva (esquema de pruebas) + migración de importación v2 + catálogos ficticios + PostgREST local.
set -e
pkill -x postgrest 2>/dev/null || true
bash /home/claude/herramientas_prueba_bh/montar_bhui.sh >/dev/null 2>&1
P="psql -X -q -h /tmp -p 55432 -U postgres -d bhui -v ON_ERROR_STOP=1"
[ "$($P -At -c "select count(*) from pg_proc where proname = 'imp_alta_personas'")" = "0" ] && $P -f /home/claude/imp_masiva/sql/20261126000000_importacion_masiva_v2.sql
$P -v ten=0a000000-0000-4000-8000-000000000001 -f /home/claude/imp_masiva/pruebas/semilla_imp.sql
psql -X -q -h /tmp -p 55432 -U postgres -d bhui -c "alter role authenticated set statement_timeout = '8s'"
bash /home/claude/herramientas_prueba_bh/pgrst/iniciar.sh
