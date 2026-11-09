"""Migración 20261109000000_fechas_hora_mexico y corrección de fecha_asignacion,
en una base Postgres LOCAL y desechable (bhev, puerto 55432). Nunca toca Supabase.
Uso: ./montar.sh && python3 pruebas_fechas_mx.py
Montar y correr antes de las 18:00 de México: la semilla base se crea con now() y, de noche,
también quedaría «adelantada» (que es justamente el defecto que corrige esta migración)."""
import subprocess, json, sys, hashlib, os, re

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
PREVIAS = ['20261104000000_eventos_laborales_idse', '20261104000100_relacion_principal_con_rp', '20261105000000_idse_bajas',
           '20261105000100_idse_modificaciones', '20261107000000_laboral_historial_tipo_email', '20261108000200_modificacion_salario_reglas']
MIG = os.path.join(S, 'pendiente', '20261109000000_fechas_hora_mexico.sql')
REV = os.path.join(S, 'reversion', '20261109000000_reversion_fechas_hora_mexico.sql')
DAT = os.path.join(S, 'datos', '20261109000100_corregir_fecha_asignacion_utc.sql')
DREV = os.path.join(S, 'datos', '20261109000100_reversion_corregir_fecha_asignacion_utc.sql')
HUELLA = os.path.join(S, 'verificacion', 'huella_esquema.sql')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhev']
ENV = dict(os.environ, PGOPTIONS='-c TimeZone=UTC')   # como Supabase
res = []

def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True, env=ENV)
    return '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET')), p.stderr.strip()
def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if 'ERROR' in err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def texto(f, cambios=()):
    t = open(f, encoding='utf-8').read()
    for a, b in cambios: t = t.replace(a, b)
    return t
def archivo(f, cambios=()):
    p = subprocess.run(PSQL, input=texto(f, cambios), capture_output=True, text=True, env=ENV); return p.stdout + p.stderr
def huella():
    return hashlib.sha256(subprocess.run(PSQL + ['-f', HUELLA], capture_output=True, text=True, env=ENV).stdout.encode()).hexdigest()[:16]
def defaults():
    return val("select string_agg(table_name||'.'||column_name||'='||column_default, ' ; ' order by 1) from information_schema.columns "
               "where table_schema='public' and table_name||'.'||column_name in ('personal.fecha_asignacion','personal_registros_pago.fecha_inicio','inc_parametros.inicio_historial')")

T = 'ca100000-0000-4000-8000-000000000001'
U = {'admin': 'cb100000-0000-4000-8000-000000000001'}
E, RP = 'cc100000-0000-4000-8000-000000000001', 'cd100000-0000-4000-8000-000000000001'
# 4 personas dadas de alta después de las 18:00 de México (UTC ya es «mañana») y 1 de control a las 17:00.
TARDE = {f'T{i}': (f'ce100000-0000-4000-8000-00000000000{i}', f'2026-11-0{7 + (i % 2)} 0{1 + i}:15:00+00') for i in range(1, 5)}
CONTROL = ('ce100000-0000-4000-8000-000000000009', '2026-11-07 23:00:00+00')   # 17:00 de México del 07
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT FECHAS');
insert into auth.users (id, email) values ('{U['admin']}','admin.fechas@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U['admin']}','{T}','administrador');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA FECHAS');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RP}','{E}','{T}','Y5555555201');
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('cf100000-0000-4000-8000-000000000001','{T}','NOMINA FECHAS');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('cf100000-0000-4000-8000-000000000002','{T}','QUINCENAL FECHAS', 15);
""" + ''.join(
    f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, empresa_id, created_at, fecha_asignacion) "
    f"values ('{pid}','{T}','FMX-{k}','PERSONA FECHAS {k}','PERSONA','FECHAS {k}','{E}','{ts}', ('{ts}'::timestamptz at time zone 'UTC')::date);\n"
    for k, (pid, ts) in {**TARDE, 'C': CONTROL}.items())

o, e = sql(seed, replica=True)
if 'ERROR' in e: sys.exit(e)
for m in PREVIAS:
    s = archivo(os.path.join(S, 'pendiente', m + '.sql'))
    if 'ERROR' in s: sys.exit(m + ': ' + s[s.find('ERROR'):][:300])
PA, PC = TARDE['T1'][0], CONTROL[0]
REL = val(f"select public.laboral_registrar_ingreso('{PA}','{E}','{RP}','2026-10-01', null, 500)", 'admin')
REL = val(f"select id from public.relaciones_laborales where personal_id = '{PA}'")
# Bitácora «histórica»: dos acontecimientos capturados de noche (fecha UTC) y uno de tarde (correcto), como en pruebas.
EVS = {'noche1': ('correccion_datos', 'pantalla', '2026-11-08 01:16:38+00', '2026-11-08'),
       'noche2': ('cambio_esquema_pago', 'automatico', '2026-11-08 03:06:52+00', '2026-11-08'),
       'tarde': ('cambio_esquema_pago', 'automatico', '2026-11-07 22:00:00+00', '2026-11-07'),
       'capturada': ('cambio_esquema_pago', 'automatico', '2026-11-08 02:00:00+00', '2026-12-01')}   # fecha escrita por el usuario
for k, (tipo, origen, ts, f) in EVS.items():
    sql(f"insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, valores_anteriores, valores_nuevos, origen, registrado_en, motivo) "
        f"values ('{T}','{PA}','{REL}','{tipo}','{f}','{{}}','{{\"nota\": \"{k}\"}}','{origen}','{ts}','{k}')", replica=True)

huella_ev = lambda: val("select md5(coalesce(string_agg(to_jsonb(e)::text, '' order by id),'')) from public.eventos_laborales e")
H0, EV0, DEF0 = huella(), huella_ev(), defaults()

print('--- Migración')
s = archivo(MIG)
ok('ERROR' not in s, 'aplica sin errores', s[s.find('ERROR'):][:220])
ok(val("select count(*) from pg_proc p where p.pronamespace='public'::regnamespace and p.prokind='f' and pg_get_functiondef(p.oid) ~* '\\mcurrent_date\\M'") == '0',
   'guarda: ninguna función usa current_date')
ok(val("select string_agg(p.proname, ',' order by 1) from pg_proc p where p.pronamespace='public'::regnamespace and pg_get_functiondef(p.oid) ~ 'public.hoy_mx\\(\\)' and p.proname <> 'hoy_mx'")
   == 'idse_validar,inc_asignacion_desde_expediente,laboral_corregir_datos,laboral_evento_por_ficha,laboral_evento_por_registro_pago',
   'las 5 funciones del inventario usan public.hoy_mx()', val("select string_agg(p.proname, ',' order by 1) from pg_proc p where p.pronamespace='public'::regnamespace and pg_get_functiondef(p.oid) ~ 'public.hoy_mx\\(\\)' and p.proname <> 'hoy_mx'"))
d = defaults()
ok(d.count('hoy_mx()') == 3 and 'current_date' not in d.lower(), 'los 3 valores por omisión usan hoy_mx()', d)
ok(val("select count(*) from respaldo.fechas_hora_mexico_20261109") == '8', 'respaldo con las 8 definiciones originales (5 funciones + 3 valores)')
ok('ya está aplicada' in archivo(MIG), 'una segunda aplicación se rechaza')
H1 = huella()

print('--- Límites del día (hora de México, servidor en UTC)')
casos = [('2026-11-08 05:59:59+00', '2026-11-07', '23:59:59 del 07 en México'), ('2026-11-08 06:00:00+00', '2026-11-08', '00:00 del 08 en México'),
         ('2026-11-08 01:20:00+00', '2026-11-07', '19:20 del 07 (el caso de la incidencia)'), ('2026-11-07 23:59:00+00', '2026-11-07', '17:59 del 07'),
         ('2026-12-31 23:30:00+00', '2026-12-31', '17:30 del 31 de diciembre'), ('2027-01-01 05:59:00+00', '2026-12-31', 'fin de año: 23:59 del 31 en México'),
         ('2026-03-01 05:30:00+00', '2026-02-28', 'cambio de mes')]
for ts, esperada, n in casos:
    r = val(f"select public.fecha_mx('{ts}')")
    ok(r == esperada, f'fecha_mx {ts} → {esperada} ({n})', r)
ok(val("select public.hoy_mx() = public.fecha_mx(now())") == 't', 'hoy_mx() = fecha de México de este momento')
ok(val("set local timezone = 'Asia/Tokyo'; select public.fecha_mx('2026-11-08 01:20:00+00')") == '2026-11-07',
   'no depende de la zona de la sesión (Tokio da el mismo resultado)')

print('--- Las funciones toman la fecha de México')
# Se fija hoy_mx() en una fecha distinta a current_date dentro de una transacción
# que se revierte: el evento debe llevar esa fecha, no la del servidor.
fijar = "create or replace function public.hoy_mx() returns date language sql stable set search_path to '' as $f$ select date '2026-11-05' $f$;"
sql(f"insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, fecha_inicio, activo, empresa_id, registro_patronal_id, relacion_laboral_id) "
    f"values ('{T}','{PA}','cf100000-0000-4000-8000-000000000001','cf100000-0000-4000-8000-000000000002', 1000, 'bruto', '2026-10-01', true, '{E}', '{RP}', '{REL}')", replica=True)
out, err = sql(fijar + f"""update public.personal_registros_pago set sueldo = sueldo + 1 where personal_id = '{PA}' and activo;
  select string_agg(fecha_efectiva::text, ',') from public.eventos_laborales where personal_id = '{PA}' and tipo = 'cambio_esquema_pago' and registrado_en > now() - interval '1 minute';
  rollback; begin""")
ok('2026-11-05' in out, 'cambio de sueldo: el acontecimiento automático lleva hoy_mx(), no current_date', (out or err)[:120])
out, err = sql(fijar + f"""select set_config('request.jwt.claims', '{json.dumps({'sub': U['admin']})}', true); set local role authenticated;
  select public.laboral_corregir_datos('{REL}', '{{"umf":"045"}}'::jsonb, 'Prueba de fecha');
  select fecha_efectiva from public.eventos_laborales where relacion_laboral_id = '{REL}' and tipo = 'correccion_datos' and motivo = 'Prueba de fecha';
  rollback; begin""")
ok(out.strip().endswith('2026-11-05'), 'corrección de datos: la fecha del acontecimiento es hoy_mx()', (out or err)[-80:])
out, err = sql(fijar + f"""insert into public.personal (tenant_id, empleado_id, nombre_completo, nombres, primer_apellido) values ('{T}','FMX-N','PERSONA NUEVA','PERSONA','NUEVA');
  select fecha_asignacion from public.personal where empleado_id = 'FMX-N'; rollback; begin""", replica=True)
ok(out.strip().endswith('2026-11-05'), 'alta de persona: fecha_asignacion por omisión = hoy_mx()', (out or err)[-80:])

print('--- Auditoría: se documenta, no se modifica')
ok(huella_ev() == EV0, 'la bitácora queda intacta (misma huella antes y después)')
aud = val("select string_agg(tabla||':'||coalesce((select motivo from public.eventos_laborales e where e.id = registro_id), 'persona')||':'||fecha_guardada||'→'||fecha_correcta, ' | ' order by tabla, fecha_guardada, registro_id) from auditoria.fechas_utc_20261109")
print('    auditoría:', aud)
ok(val("select count(*) from auditoria.fechas_utc_20261109 where tabla = 'eventos_laborales'") == '2'
   and 'noche1' in aud and 'noche2' in aud and 'tarde' not in aud and 'capturada' not in aud,
   'se registran solo los 2 acontecimientos nocturnos (no el de la tarde ni la fecha escrita por el usuario)')
ok(val("select count(*) from auditoria.fechas_utc_20261109 where tabla = 'eventos_laborales' and fecha_correcta = fecha_guardada - 1") == '2', 'su fecha correcta es la del día anterior')
n_tarde = val(f"select count(*) from public.personal p where p.tenant_id = '{T}' and p.fecha_asignacion = (p.created_at at time zone 'UTC')::date and p.fecha_asignacion = (p.created_at at time zone 'America/Mexico_City')::date + 1")
ok(val("select count(*) from auditoria.fechas_utc_20261109 where tabla = 'personal'") == n_tarde == '4', 'se registran las 4 fechas de asignación adelantadas (no la de control)', n_tarde)
ok(val("select has_schema_privilege('authenticated','auditoria','usage')::text || has_schema_privilege('anon','auditoria','usage')::text") == 'falsefalse',
   'la auditoría no es accesible desde la aplicación (ni authenticated ni anon)')

print('--- Corrección de fecha_asignacion (script de datos)')
asig = lambda: val(f"select string_agg(empleado_id||'='||fecha_asignacion, ',' order by empleado_id) from public.personal where tenant_id = '{T}' and empleado_id like 'FMX-%'")
A0 = asig()
s = archivo(DAT)
ok('se esperaban 6' in s and asig() == A0, 'con un conteo distinto al esperado (4 ≠ 6) no cambia nada', s[s.find('ERROR'):][:120])
s = archivo(DAT, [('v_esperado constant int := 6', 'v_esperado constant int := 4')])
A1 = asig()
ok('ERROR' not in s and n_tarde != val("select count(*) from public.personal p where p.fecha_asignacion = (p.created_at at time zone 'UTC')::date and p.fecha_asignacion = (p.created_at at time zone 'America/Mexico_City')::date + 1"),
   'con el conteo correcto corrige las 4', s[s.find('ERROR'):][:150])
ok(all(val(f"select fecha_asignacion = (created_at at time zone 'America/Mexico_City')::date from public.personal where id = '{pid}'") == 't' for pid, _ in TARDE.values()),
   'cada fecha queda en el día de México del alta', A1)
ok(val(f"select fecha_asignacion from public.personal where id = '{PC}'") == '2026-11-07', 'la persona de control (17:00) no cambia')
ok(val("select count(*) from public.movimientos where usuario = 'sistema · corrección zona horaria UTC 20261109' and campo = 'fecha_asignacion' and valor_nuevo::date = valor_anterior::date - 1") == '4',
   'cada cambio queda en Movimientos con valor anterior y nuevo, como «sistema»')
ok('ya se aplicó' in archivo(DAT, [('v_esperado constant int := 6', 'v_esperado constant int := 4')]), 'una segunda ejecución se rechaza')
ok(huella_ev() == EV0, 'la bitácora sigue intacta')
s = archivo(DREV)
ok('ERROR' not in s and asig() == A0, 'reversión del script: las fechas vuelven a su valor anterior', s[s.find('ERROR'):][:150])
ok(val("select count(*) from public.movimientos where usuario like 'sistema · %20261109'") == '8', 'la reversión deja constancia en Movimientos y no borra la traza')

print('--- Reversión de la migración')
n_ev = val("select count(*) from public.eventos_laborales")
s = archivo(REV)
ok('ERROR' not in s, 'la reversión se aplica sin errores', s[s.find('ERROR'):][:200])
ok(huella() == H0, 'el esquema vuelve a ser idéntico al de antes de la migración')
ok(defaults() == DEF0, 'los valores por omisión vuelven a current_date', defaults())
ok(huella_ev() == EV0 and val("select count(*) from public.eventos_laborales") == n_ev, 'la bitácora no cambia')
ok(val("select count(*) from pg_tables where schemaname = 'auditoria' and tablename like 'fechas_utc_20261109_revertida_%'") == '1', 'la auditoría se conserva renombrada (traza)')
s = archivo(MIG)
ok('ERROR' not in s and huella() == H1, 'se puede volver a aplicar y queda igual', s[s.find('ERROR'):][:150])
sql("create or replace function public.laboral_evento_por_ficha() returns trigger language plpgsql as $f$ begin return new; end $f$", replica=True)
s = archivo(REV)
ok('cambió después de la migración' in s and huella() != H0, 'guarda: si una función cambió después, la reversión no se ejecuta')

ok(all(b for _, b in res), f'TOTAL: {sum(1 for _, b in res if b)}/{len(res)} pruebas OK')
sys.exit(0 if all(b for _, b in res) else 1)
