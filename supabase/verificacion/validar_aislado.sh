#!/usr/bin/env bash
# =====================================================================
# BeeHuman · Validación en una base PostgreSQL AISLADA (Docker)
# Archivo: supabase/verificacion/validar_aislado.sh
# NO se conecta a Supabase. Crea un contenedor desechable postgres:17.6,
# reconstruye el esquema de producción y encadena V2.0 / reversión / V2.0,
# luego corre la prueba de compatibilidad v5 con datos sintéticos.
# Uso (desde la raíz del repositorio):  bash supabase/verificacion/validar_aislado.sh
# Requisitos: Docker. Nada más.
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")/.."            # carpeta supabase/
C=bh-aislado
IMG=postgres:17.6

docker rm -f "$C" >/dev/null 2>&1 || true
docker run -d --name "$C" -e POSTGRES_HOST_AUTH_METHOD=trust "$IMG" >/dev/null
until docker exec "$C" pg_isready -U postgres -q; do sleep 1; done
docker exec "$C" createdb -U postgres bh

psql_f() { docker exec -i "$C" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d bh -f - ; }
huella()  { docker exec -i "$C" psql -X -At -U postgres -d bh -f - < verificacion/huella_esquema.sql | awk -F'|' '{print $NF}'; }
sin_bloques_prod() {
  sed -e '/-- @@CANDADO_PROD_INICIO/,/-- @@CANDADO_PROD_FIN/d' \
      -e '/-- @@ASIGNACIONES_PROD_INICIO/,/-- @@ASIGNACIONES_PROD_FIN/d' "$1"
}
esperar() { [ "$1" = "$2" ] && echo "   OK  $3 = $1" || { echo "   FALLA $3: $1 (esperado $2)"; exit 1; }; }

V1=03e98353d5e19d32ad52fd84b464f608
V2=ebcd0aad4284c492ae7b44b379d6e208

echo "0. Shim Supabase + base V1"
psql_f < verificacion/shim_supabase_local.sql
psql_f < migrations/20261001173928_base_v1_esquema_reconstruido.sql
esperar "$(huella)" "$V1" "huella tras base V1"

echo "1. V1 -> V2.0 (sin candado ni asignaciones de producción)"
sin_bloques_prod migrations/20261018000000_beehuman_v2_0_roles_m1_m2.sql | psql_f
esperar "$(huella)" "$V2" "huella tras V2.0"

echo "2. V2.0 -> V1 (reversión)"
sin_bloques_prod reversion/20261018000000_reversion_v2_0.sql | psql_f
esperar "$(huella)" "$V1" "huella tras reversión"

echo "3. V1 -> V2.0 otra vez"
sin_bloques_prod migrations/20261018000000_beehuman_v2_0_roles_m1_m2.sql | psql_f
esperar "$(huella)" "$V2" "huella tras V2.0 (2ª vez)"

echo "4. Semilla sintética + prueba de compatibilidad v5"
psql_f < verificacion/semilla_sintetica_local.sql
docker exec -i "$C" psql -X -At -U postgres -d bh -f - < verificacion/verificacion_huellas_pruebas.sql > /tmp/bh_antes.txt
RES=$(docker exec -i "$C" psql -X -q -U postgres -d bh -f - < verificacion/prueba_compatibilidad_beehuman-pruebas.sql 2>&1 || true)
docker exec -i "$C" psql -X -At -U postgres -d bh -f - < verificacion/verificacion_huellas_pruebas.sql > /tmp/bh_despues.txt
echo "$RES" | grep -o 'PRUEBA_[A-Z_]*.*' | head -1
echo "$RES" | grep -q 'PRUEBA_COMPLETA_OK' || { echo "   FALLA: la prueba no devolvió PRUEBA_COMPLETA_OK"; exit 1; }
diff /tmp/bh_antes.txt /tmp/bh_despues.txt >/dev/null && echo "   OK  huellas antes == después" || { echo "   FALLA: cambiaron las huellas"; exit 1; }

docker rm -f "$C" >/dev/null
echo "VALIDACIÓN AISLADA COMPLETA"
