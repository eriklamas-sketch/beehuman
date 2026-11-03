#!/usr/bin/env bash
# Base LOCAL desechable con el estado de beehuman-pruebas: V1 + V2.0 + permisos + Ola 1 + periodicidades.
set -euo pipefail
cd "$(dirname "$0")"
O=../ola1; S=../repo/beehuman-int/supabase
P="psql -X -q -v ON_ERROR_STOP=1 -h /tmp -p 55432 -U postgres"
$P -d postgres -c "drop database if exists bhev with (force)" -c "create database bhev" >/dev/null
$P -d bhev -f $S/verificacion/shim_supabase_local.sql >/dev/null 2>&1
$P -d bhev -f $O/base_local.sql 2>&1 | grep -v NOTICE || true
$P -d bhev -f $O/v20_local.sql 2>&1 | grep -v NOTICE || true
$P -d bhev -f $O/espejo_permisos_pruebas.sql
$P -d bhev -f $S/pendiente/20261028000000_ola1_hoja_coordinador.sql 2>&1 | grep -v NOTICE || true
$P -d bhev -f $S/pendiente/20261030000000_normalizar_periodicidades.sql 2>&1 | grep -v NOTICE || true
$P -d bhev -f $S/pendiente/20261030000100_mensual_30_dias.sql 2>&1 | grep -v NOTICE || true
echo "base bhev lista"
