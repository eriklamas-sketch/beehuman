#!/usr/bin/env bash
# Base LOCAL para probar las pantallas: V1 + V2.0 + permisos de pruebas + Ola 1 + datos sintéticos.
set -euo pipefail
cd "$(dirname "$0")"
S=../repo/beehuman/supabase
P="psql -X -q -v ON_ERROR_STOP=1 -h /tmp -p 55432 -U postgres"
$P -d postgres -c "drop database if exists bhui with (force)" -c "create database bhui" >/dev/null
$P -d bhui -f $S/verificacion/shim_supabase_local.sql >/dev/null 2>&1
$P -d bhui -f base_local.sql 2>&1 | grep -v NOTICE || true
$P -d bhui -f v20_local.sql 2>&1 | grep -v NOTICE || true
$P -d bhui -f espejo_permisos_pruebas.sql
$P -d bhui -f 20261028000000_ola1_hoja_coordinador.sql 2>&1 | grep -v NOTICE || true
$P -d bhui -f semilla_ui.sql
echo "base bhui lista"
