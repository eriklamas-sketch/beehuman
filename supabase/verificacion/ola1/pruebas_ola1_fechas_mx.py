"""D2 · Corrección de fechas de Ola 1 en el orden de PRODUCCIÓN (20261124000100_ola1_fechas_hora_mexico.sql).
Bases LOCALES desechables (puerto 55432), datos ficticios:
  bhprod  orden de producción: V1 + V2.0 + fase 1 → Ola 1 → … → B6, con los permisos por omisión amplios de producción
          (herramientas_prueba_bh/env/ensayo_orden_produccion.sh, NO_REVERTIR=1; no incluye D2).
  bh      orden de pruebas (montar.sh con todo pendiente/, que ya incluye D2).
  bhsin   orden de pruebas hasta B6, sin D2 (para demostrar que en pruebas D2 no cambia nada).
La diferencia entre la fecha UTC y la de México solo existe de 18:00 a 23:59 (hora de México). Para verla a cualquier hora,
las pruebas de comportamiento fijan la zona de la sesión en Pacific/Kiritimati (UTC+14): current_date sigue la zona de la
sesión, igual que en Supabase sigue UTC; public.hoy_mx() siempre da la fecha de México.
Uso: python3 pruebas_ola1_fechas_mx.py"""
import subprocess, sys, os, json

R = '/home/claude/beehuman/supabase'; E = '/home/claude/herramientas_prueba_bh/env'
MIG = f'{R}/pendiente/20261124000100_ola1_fechas_hora_mexico.sql'
REV = f'{R}/reversion/20261124000100_reversion_ola1_fechas_hora_mexico.sql'
res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def psql(db, q=None, f=None):
    cmd = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', db]
    p = subprocess.run(cmd + (['-f', f] if f else []), input=q, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()
def val(db, q):
    rc, o, e = psql(db, q)
    if rc: raise RuntimeError(e)
    return o.splitlines()[-1] if o else ''
def huella(db): return psql(db, f=f'{R}/verificacion/huella_esquema.sql')[1].split('|')[-1]
def objetos(db):
    return (psql(db, "select p.proname||'('||pg_get_function_identity_arguments(p.oid)||') '||md5(pg_get_functiondef(p.oid)) from pg_proc p "
                     "where p.pronamespace='public'::regnamespace and (p.proname like 'inc%' or p.proname like 'cred%') order by 1")[1],
            psql(db, "select table_name||'.'||column_name||' '||coalesce(column_default,'') from information_schema.columns "
                     "where table_schema='public' and (table_name like 'inc%' or table_name like 'cred%') order by 1")[1])
def con_current_date(db):
    return val(db, "select coalesce(string_agg(x, ', ' order by x), 'ninguno') from ("
                   "select p.proname x from pg_proc p where p.pronamespace='public'::regnamespace and p.prokind='f' and pg_get_functiondef(p.oid) ~* '\\mcurrent_date\\M' "
                   "union all select table_name||'.'||column_name from information_schema.columns where table_schema='public' and column_default ~* '\\mcurrent_date\\M') t")

# Escenario: alta de parámetros sin inicio_historial y cambio de coordinador desde la ficha. Devuelve las dos fechas y hoy_mx.
T = 'd2000000-0000-4000-8000-000000000001'; EM = 'd2000000-0000-4000-8000-000000000002'
CO, PE = 'd2000000-0000-4000-8000-000000000003', 'd2000000-0000-4000-8000-000000000004'
def escenario(db):
    q = f"""begin;
set local session_replication_role = replica;
insert into public.tenants (id, nombre) values ('{T}','TENANT D2');
insert into public.empresas (id, tenant_id, nombre) values ('{EM}','{T}','EMPRESA D2');
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id) values ('{CO}','{T}','{EM}','COORD D2','D2-C'),('{PE}','{T}','{EM}','PERSONA D2','D2-P');
set local session_replication_role = origin;
set local timezone = 'Pacific/Kiritimati';
insert into public.inc_parametros (empresa_id, tenant_id) values ('{EM}','{T}');
update public.personal set coordinador_id = '{CO}' where id = '{PE}';
select json_build_object('inicio_historial', (select inicio_historial from public.inc_parametros where empresa_id='{EM}'),
  'asignacion_desde', (select desde from public.inc_asignaciones where personal_id='{PE}'),
  'hoy_mx', public.hoy_mx(), 'current_date_sesion', current_date);
rollback;"""
    rc, o, e = psql(db, q)
    if rc: raise RuntimeError(e)
    return json.loads(o.splitlines()[-1])

print('== Preparación de bases ==')
r = subprocess.run(['bash', f'{E}/ensayo_orden_produccion.sh'], env={**os.environ, 'NO_REVERTIR': '1', 'DB': 'bhprod'}, capture_output=True, text=True)
ok('huella_activada' in r.stdout and '!!' not in r.stdout, '+P1 Base en orden de producción armada (fase 1 → Ola 1 → … → B6, sin D2)', [l for l in r.stdout.splitlines() if l.startswith('huella')][-1])
r = subprocess.run(['bash', f'{E}/montar.sh'], env={**os.environ, 'DB': 'bh'}, capture_output=True, text=True)
r2 = subprocess.run(['bash', f'{E}/montar.sh', '20261124000000'], env={**os.environ, 'DB': 'bhsin'}, capture_output=True, text=True)
ok('lista' in r.stdout and 'lista' in r2.stdout, '+P2 Bases en orden de pruebas: con D2 (bh) y sin D2 (bhsin)')

print('== A · El defecto existe en el orden de producción ==')
ok(con_current_date('bhprod') == 'inc_asignacion_desde_expediente, inc_parametros.inicio_historial',
   'A1 Sin D2, en orden de producción quedan exactamente 2 objetos de Ola 1 con current_date', con_current_date('bhprod'))
a = escenario('bhprod')
ok(a['current_date_sesion'] != a['hoy_mx'] and a['inicio_historial'] == a['current_date_sesion'] and a['asignacion_desde'] == a['current_date_sesion'],
   'A2 Sin D2, con la fecha de la sesión adelantada, parámetros y asignación toman la fecha de la sesión, no la de México', json.dumps(a))

print('== B · D2 corrige el orden de producción ==')
antes = huella('bhprod')
rc, o, e = psql('bhprod', f=MIG)
ok(rc == 0 and '2 objeto(s)' in e, 'B1 D2 se aplica y corrige 2 objetos', e.splitlines()[-1] if e else o)
ok(con_current_date('bhprod') == 'ninguno', 'B2 Ya no queda current_date en funciones ni valores por omisión de public')
b = escenario('bhprod')
ok(b['inicio_historial'] == b['hoy_mx'] and b['asignacion_desde'] == b['hoy_mx'] and b['current_date_sesion'] != b['hoy_mx'],
   'B3 Con D2, parámetros y asignación toman la fecha de México aunque la sesión tenga otra fecha', json.dumps(b))
ok(val('bhprod', "select count(*) from respaldo.ola1_fechas_hora_mexico_20261124") == '2', '+B4 El original textual de los 2 objetos queda respaldado')
ok(val('bhprod', "select has_function_privilege('anon','public.inc_asignacion_desde_expediente()','execute')::text||has_table_privilege('anon','public.inc_parametros','select')::text") ==
   'falsefalse', 'B5 Permisos sin cambio: anon sigue sin acceso a la función y a la tabla')
fp, fb = objetos('bhprod'), objetos('bh')
ok(fp == fb, 'B6 Con D2, funciones y valores por omisión de Ola 1/fase B/B-a/B6 quedan idénticos en orden de producción y en orden de pruebas',
   'idénticos' if fp == fb else 'DIFERENTES')
despues = huella('bhprod')

print('== C · En el orden de pruebas D2 no cambia nada ==')
ok(huella('bh') == huella('bhsin'), 'C1 Base en orden de pruebas con D2 = sin D2 (misma huella de esquema)', huella('bh')[:12])
ok(val('bh', "select count(*) from respaldo.ola1_fechas_hora_mexico_20261124") == '0', 'C2 En orden de pruebas D2 no respalda nada (no había nada que corregir)')
h0 = huella('bh'); rc, o, e = psql('bh', f=REV)
ok(rc == 0 and huella('bh') == h0 and val('bh', "select to_regclass('respaldo.ola1_fechas_hora_mexico_20261124')") == '',
   'C3 Revertir en orden de pruebas: huella igual y sin tabla de respaldo')

print('== D · Reversión y reaplicación en orden de producción ==')
rc, o, e = psql('bhprod', f=REV)
ok(rc == 0 and huella('bhprod') == antes and con_current_date('bhprod') == 'inc_asignacion_desde_expediente, inc_parametros.inicio_historial',
   'D1 Revertir deja exactamente el estado anterior a D2', e[:200])
rc, o, e = psql('bhprod', f=MIG)
ok(rc == 0 and huella('bhprod') == despues, 'D2 Reaplicar da exactamente el mismo esquema')
rc, o, e = psql('bhprod', f=MIG)
ok(rc != 0 and 'ya está aplicada' in e, 'D3 Aplicar dos veces se rechaza')
psql('bhprod', "create or replace function public.inc_asignacion_desde_expediente() returns trigger language plpgsql security definer set search_path to '' as $$ begin return new; end $$")
rc, o, e = psql('bhprod', f=REV)
ok(rc != 0 and 'cambió después de la corrección' in e, 'D4 La reversión se niega si la función se modificó después de D2')

total = len(res); malas = [x for x in res if not x[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, d in malas: print('  FALLA:', nn, d)
sys.exit(1 if malas else 0)
