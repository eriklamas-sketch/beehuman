"""B5 · Regresión del FONACOT convertido de «No. FONACOT» (revisión manual de Erik, 17-nov-2026),
contra la base LOCAL desechable (puerto 55432) con todas las migraciones de integracion/app y datos FICTICIOS.
  C1 El convertido nace «incompleto» y la ficha dice qué le falta (misma validación que «Activar»).
  C2 Guardar los datos requeridos (sin importe total) no cambia el estado solo: queda «completo, falta activar».
  C3 Mientras está incompleto no propone descuentos ni genera pendientes (es informativo).
  C4 Activar con datos incompletos se rechaza con mensaje claro; con datos completos se activa con historia.
  C5 Ya activo, propone su retención por periodo «por decidir»; el importe total sigue opcional.
  C6 Permisos: la función nueva es interna; Coordinador no ve créditos.
  S  Ficha y alta sin «Salud»: el campo no se muestra ni se envía; la columna sigue en la base.
     La conservación del valor al guardar la ficha se prueba con la pantalla real en ui_b5_fonacot_salud.py.
Uso: DB=bh python3 pruebas_b5_fonacot.py"""
import subprocess, json, sys, os

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'app')
res = []
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    return '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET')), p.stderr.strip()
def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def falla_con(q, user, texto, n):
    out, err = sql(q, user); ok(err and texto.lower() in err.lower(), n, (err.split('\n')[0][:170] if err else 'NO FALLÓ'))
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T = '7f000000-0000-4000-8000-000000000001'
U = {'admin': '7f000000-0000-4000-8000-0000000000a1', 'nomina': '7f000000-0000-4000-8000-0000000000a2', 'coord': '7f000000-0000-4000-8000-0000000000a3'}
EA, EB, SEM = '7f000000-0000-4000-8000-0000000000e1', '7f000000-0000-4000-8000-0000000000e2', '7f000000-0000-4000-8000-0000000000f7'
P1, P2, PC = '7f000000-0000-4000-8000-000000000011', '7f000000-0000-4000-8000-000000000012', '7f000000-0000-4000-8000-000000000013'
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT FONACOT CONVERTIDO');
insert into auth.users (id, email) values ('{U['admin']}','admin.fc@beehuman.invalid'),('{U['nomina']}','nomina.fc@beehuman.invalid'),('{U['coord']}','coord.fc@beehuman.invalid');
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA FONACOT FC'),('{EB}','{T}','EMPRESA FONACOT FC DOS');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, no_fonacot) values
 ('{P1}','{T}','{EA}','PERSONA FONACOT LIGADO FC','FC-1','FON-FC-1'),
 ('{P2}','{T}','{EA}','PERSONA FONACOT SIN RELACION FC','FC-2','FON-FC-2'),
 ('{PC}','{T}','{EA}','COORDINADOR FC','FC-C',null);
insert into public.relaciones_laborales (tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values
 ('{T}','{P1}','{EA}','2025-01-01','vigente'),('{T}','{P2}','{EA}','2025-01-01','vigente'),('{T}','{P2}','{EB}','2025-06-01','vigente');
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values
 ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),('{U['coord']}','{T}','coordinador','{PC}');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial) values ('{EA}','{T}','2025-01-01');
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
RL1 = val(f"select id from public.relaciones_laborales where personal_id='{P1}'")
RL2 = val(f"select min(id::text) from public.relaciones_laborales where personal_id='{P2}'")

# Conversión: la MISMA sentencia de la sección 8 de la migración B5, limitada a estas personas.
conv = f"""
with origen as (
  select p.id personal_id, p.tenant_id, trim(p.no_fonacot) referencia,
         (select case when count(*) = 1 then min(rl.id::text)::uuid end from public.relaciones_laborales rl
           where rl.personal_id = p.id and rl.estado = 'vigente' and rl.fecha_baja is null) relacion
    from public.personal p where coalesce(trim(p.no_fonacot), '') <> '' and p.tenant_id = '{T}'
), nuevos as (
  insert into public.cred_creditos (tenant_id, personal_id, relacion_laboral_id, tipo, referencia, estado, origen, notas)
  select o.tenant_id, o.personal_id, o.relacion, 'fonacot', o.referencia, 'incompleto', 'conversion_no_fonacot',
         'Convertido del campo «No. FONACOT» del expediente. Completa relación, periodicidad y retención de la cédula para activarlo.'
    from origen o
  returning *
)
insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, motivo, nombre)
select n.tenant_id, n.id, 'conversion', jsonb_build_object('personal.no_fonacot', n.referencia), to_jsonb(n),
       'Conversión del campo No. FONACOT del expediente (B5).', 'BeeHuman (migración B5)' from nuevos n"""
val(conv)
C1 = val(f"select id from public.cred_creditos where personal_id='{P1}'")
C2 = val(f"select id from public.cred_creditos where personal_id='{P2}'")
def ficha(persona, cred):
    arr = json.loads(val(f"select public.cred_creditos_persona('{persona}')", 'nomina'))
    return next(x for x in arr if x['credito']['id'] == cred)
def estado(cred): return val(f"select estado from public.cred_creditos where id='{cred}'")

print('== C1 Convertido: incompleto y la ficha dice qué falta ==')
x1, x2 = ficha(P1, C1), ficha(P2, C2)
ok(x1['credito']['estado'] == 'incompleto' and x1['credito']['relacion_laboral_id'] == RL1, 'C1 Con una sola relación: nace incompleto y ligado a su relación')
ok(x1['falta_para_activar'] and 'fecha de inicio' in x1['falta_para_activar'], 'C1 La ficha indica lo primero que falta (fecha de inicio)', x1['falta_para_activar'])
ok(x2['credito']['relacion_laboral_id'] is None and 'relación laboral' in (x2['falta_para_activar'] or ''), 'C1 Con dos relaciones: sin relación; la ficha pide elegirla', x2['falta_para_activar'])
ok(json.loads(val(f"select public.cred_creditos_persona('{P1}')", 'nomina')) and all(
   ('falta_para_activar' not in y) or y['credito']['estado'] == 'incompleto' or y['falta_para_activar'] is None
   for y in json.loads(val(f"select public.cred_creditos_persona('{P1}')", 'nomina'))), 'C1 El dato solo se calcula para incompletos')

print('== C2 Guardar los datos requeridos (sin importe total) ==')
v = val(f"select public.cred_guardar('{C1}', {lit({'fecha_inicio': '2026-11-16', 'periodicidad_id': SEM})}, 'Completar datos (parcial)')", 'nomina')
x1 = ficha(P1, C1)
ok(x1['credito']['estado'] == 'incompleto' and 'descuento por periodo' in (x1['falta_para_activar'] or ''), 'C2 Parcial (sin retención): sigue incompleto y ahora pide la retención por periodo', x1['falta_para_activar'])
v = val(f"select public.cred_guardar('{C1}', {lit({'referencia': 'FON-FC-1', 'importe_periodo': 250})}, 'Completar retención de la cédula')", 'nomina')
x1 = ficha(P1, C1)
ok(x1['credito']['estado'] == 'incompleto', 'C2 Con los datos completos el estado NO cambia solo (activar es explícito)')
ok(x1['falta_para_activar'] is None, 'C2 … y la ficha lo reporta como «completo, falta activar» (sin faltantes)')
ok(x1['credito']['monto_total'] is None and float(x1['credito']['importe_periodo']) == 250, 'C2 Importe total vacío (opcional); retención $250')
ok(val(f"select string_agg(evento, ',' order by creado_en) from public.cred_historia where credito_id='{C1}'") == 'conversion,cambio,cambio', 'C2 Historia: conversión y los dos cambios con motivo')

print('== C3 Incompleto: no propone descuentos ni genera pendientes ==')
PER = val(f"select public.inc_crear_periodo('{EA}','{SEM}','2026-11-16','2026-11-22')", 'nomina')
pan = json.loads(val(f"select public.cred_descuentos_periodo('{PER}')", 'nomina'))
ok(not any(l['credito_id'] in (C1, C2) for l in pan['lineas']), 'C3 Sin líneas de descuento para los incompletos')
ok(sum(1 for i in pan['informativos'] if i['referencia'] in ('FON-FC-1', 'FON-FC-2')) == 2, 'C3 Aparecen como informativos')
ok(val(f"select count(*) from public.inc_faltantes_procesar('{PER}') where tipo='descuento'", 'nomina') == '0', 'C3 Sin pendientes de descuento')

print('== C4 Activar ==')
falla_con(f"select public.cred_cambiar_estado('{C2}', 'activo', '2026-11-16', 'Intento sin datos')", 'nomina', 'relación laboral', 'C4 Con datos incompletos: «Activar» se rechaza con el faltante')
ok(estado(C2) == 'incompleto', 'C4 … y sigue incompleto')
falla_con(f"select public.cred_cambiar_estado('{C1}', 'activo', '2026-11-16', null)", 'nomina', 'motivo', 'C4 Activar exige motivo')
val(f"select public.cred_cambiar_estado('{C1}', 'activo', '2026-11-16', 'Cédula FONACOT recibida')", 'nomina')
ok(estado(C1) == 'activo', 'C4 Con datos completos: se activa')
h = val(f"select evento||'|'||fecha_efectiva||'|'||motivo from public.cred_historia where credito_id='{C1}' order by creado_en desc limit 1")
ok(h == 'activacion|2026-11-16|Cédula FONACOT recibida', 'C4 Historia «activación» con fecha efectiva y motivo', h)
ok('falta_para_activar' not in ficha(P1, C1) or ficha(P1, C1)['falta_para_activar'] is None, 'C4 Ya activo: sin aviso de faltantes')

print('== C5 Activo: propone su retención por decidir; importe total opcional ==')
pan = json.loads(val(f"select public.cred_descuentos_periodo('{PER}')", 'nomina'))
lin = next((l for l in pan['lineas'] if l['credito_id'] == C1), None)
ok(lin and float(lin['sugerido']) == 250 and lin['origen'] == 'pendiente', 'C5 Propone $250 «por decidir»', str(lin and (lin['sugerido'], lin['origen'])))
ok(lin and lin['saldo'] is None and lin.get('disponible') is None, 'C5 Sin importe total: no controla saldo (sigue siendo opcional)')
ok(val(f"select count(*) from public.inc_faltantes_procesar('{PER}') where tipo='descuento'", 'nomina') == '1', 'C5 Su descuento aparece como pendiente de decidir')

print('== C6 Permisos ==')
out, err = sql(f"select public.cred_falta_para_activar(c) from public.cred_creditos c limit 1", 'nomina')
ok('permission denied' in err, 'C6 cred_falta_para_activar es interna (no expuesta a la aplicación)')
falla_con(f"select public.cred_creditos_persona('{P1}')", 'coord', 'sin permiso', 'C6 Coordinador no consulta créditos')

print('== S Sin «Salud» en la ficha ni en el alta; el dato existente se conserva ==')
html = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
def objeto_enviado(n):
    """Texto del n-ésimo `const nuevo = {…};` (0 = alta, 1 = ficha): lo que la pantalla envía a la base."""
    pos = -1
    for _ in range(n + 1): pos = html.index('const nuevo = {', pos + 1)
    return html[pos:html.index('\n  };', pos)]
alta, fic = objeto_enviado(0), objeto_enviado(1)
ok('contacto_emergencia_nombre' in alta and 'f-emerg-nombre' in alta, 'S  (control) Se identificó el objeto que envía el alta')
ok('contacto_emergencia_nombre' in fic and 'd-emerg-nombre' in fic, 'S  (control) Se identificó el objeto que envía la ficha')
i2 = html.find('data-detail-section="prestaciones"'); j2 = html.find('</section>', i2)
ok(i2 > 0 and 'Salud' not in html[i2:j2] and 'd-restricciones' not in html, 'S  Ficha: sin la sección «Salud» ni el campo «Restricciones de salud»')
ok('f-restricciones' not in html and 'alta-subtitle">Salud' not in html and 'restricciones de salud.' not in html, 'S  Alta: sin «Salud», sin el campo y sin la mención en el subtítulo de la tarjeta')
ok('restricciones_salud' not in fic, 'S  La ficha no envía restricciones_salud al guardar')
ok('restricciones_salud' not in alta, 'S  El alta no envía restricciones_salud')
ok(val("select count(*) from information_schema.columns where table_schema='public' and table_name='personal' and column_name='restricciones_salud'") == '1',
   'S  La columna restricciones_salud sigue existiendo en la base')
# La conservación de un valor existente al guardar la ficha NO se simula aquí con SQL: se comprueba con la
# pantalla real (abrir ficha, cambiar otro campo, «Guardar cambios», consultar la base) en ui_b5_fonacot_salud.py.

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
sys.exit(1 if malas else 0)
