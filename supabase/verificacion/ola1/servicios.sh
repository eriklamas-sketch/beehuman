#!/usr/bin/env bash
# Levanta Postgres local (puerto 55432) y PostgREST (3010) para las pruebas de pantallas.
D=/var/tmp/ola1pg
if ! psql -X -h /tmp -p 55432 -U postgres -d postgres -c "select 1" >/dev/null 2>&1; then
  [ -d $D ] || { mkdir -p $D && chown postgres $D && chmod 700 $D && su postgres -c "/usr/lib/postgresql/16/bin/initdb -D $D -U postgres --auth=trust -E UTF8 --locale=C.UTF-8 >/dev/null"; }
  rm -f $D/postmaster.pid
  su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $D -o '-p 55432 -k /tmp' -l $D/log.txt start" >/dev/null; sleep 2
fi
cd "$(dirname "$0")"
psql -X -h /tmp -p 55432 -U postgres -At -c "select 1 from pg_database where datname='bhui'" | grep -q 1 || ./montar_ui.sh
pkill postgrest 2>/dev/null; sleep 0.5
(cd pgrst && nohup ./postgrest pgrst.conf > pgrst.log 2>&1 &); sleep 2
curl -s --noproxy '*' -o /dev/null -w "PostgREST: %{http_code}\n" localhost:3010/
