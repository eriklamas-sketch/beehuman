#!/usr/bin/env bash
# Base LOCAL desechable: esquema V1 + V2.0 + permisos de pruebas + Ola 1 + pruebas,
# luego reversión + huella, y Ola 1 otra vez + pruebas. Nunca se conecta a Supabase.
set -euo pipefail
cd "$(dirname "$0")"
S=../repo/beehuman/supabase
P="psql -X -q -v ON_ERROR_STOP=1 -h /tmp -p 55432 -U postgres"
huella() { $P -d bh -At -f $S/verificacion/huella_esquema.sql | awk -F'|' '{print $NF}'; }
$P -d postgres -c "drop database if exists bh" -c "create database bh"
$P -d bh -f $S/verificacion/shim_supabase_local.sql >/dev/null 2>&1
$P -d bh -f base_local.sql 2>&1 | grep -v NOTICE || true
$P -d bh -f v20_local.sql 2>&1 | grep -v NOTICE || true
$P -d bh -f espejo_permisos_pruebas.sql
$P -d bh -c "create extension if not exists btree_gist with schema extensions" >/dev/null
H0=$(huella); echo "Huella antes de la Ola 1: $H0"
$P -d bh -f 20261028000000_ola1_hoja_coordinador.sql 2>&1 | grep -v NOTICE || true
echo "--- Ronda 1 de pruebas"; python3 pruebas_ola1.py | tail -3
$P -d bh -f 20261028000000_reversion_ola1.sql 2>&1 | grep -v NOTICE || true
$P -d bh -c "delete from public.usuario_alcances where tenant_id='0a000000-0000-4000-8000-000000000001'" >/dev/null
H1=$(huella); echo "Huella tras la reversión: $H1"
[ "$H0" = "$H1" ] && echo "OK  la reversión deja el esquema idéntico" || echo "FALLA la reversión no regresa el esquema"
