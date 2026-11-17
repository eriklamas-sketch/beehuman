"""Pruebas de base de la corrección «Mis hojas» del coordinador (D1, D2, D3) en la base LOCAL
desechable (puerto 55432) con Ola 1 + fase 1 + B2 + B1 + B1.1 + B1.1a + B1.1b + B5 + esta corrección.
Datos ficticios. Diseño aprobado por Erik (16-nov 18:15):
claude/Mis-hojas-coordinador-diseno-correccion-16nov.md
Uso: DB=bh python3 pruebas_mis_hojas.py"""
import subprocess, json, sys, os, datetime

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
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
    out, err = sql(q, user); ok(err and texto.lower() in err.lower(), n, (err.split('\n')[0][:160] if err else 'NO FALLÓ'))

T, T2 = '6a000000-0000-4000-8000-000000000001', '6a000000-0000-4000-8000-000000000002'
ROLES = ['admin', 'nomina', 'consulta', 'c1', 'c2', 'c3', 'c4', 'c5', 'cx', 'nominax']
U = {k: f'6b000000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(ROLES, 1)}
EA, EB, EC, EX = (f'6c000000-0000-4000-8000-00000000000{n}' for n in (1, 2, 3, 9))
SEM, SEMX = '6e000000-0000-4000-8000-000000000007', '6e000000-0000-4000-8000-000000000009'
# Personas: coordinadores C1..C5 y CX; trabajadores W1..W5 y WX
PER = {k: f'6d000000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['C1', 'C2', 'C3', 'C4', 'C5', 'CX', 'W1', 'W2', 'W3', 'W4', 'W5', 'WX', 'WC'], 1)}
lunes = val("select (date_trunc('week', public.hoy_mx() + 7))::date")
L = datetime.date.fromisoformat(lunes)
sem = lambda n: ((L + datetime.timedelta(days=7 * n)).isoformat(), (L + datetime.timedelta(days=7 * n + 6)).isoformat())

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT MIS HOJAS'),('{T2}','OTRO TENANT MIS HOJAS');
insert into auth.users (id, email) select v, k||'.mh@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A MH'),('{EB}','{T}','EMPRESA B MH'),('{EC}','{T}','EMPRESA C MH'),('{EX}','{T2}','EMPRESA OTRO TENANT MH');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7),('{SEMX}','{T2}','SEMANAL',7);
"""
emp = {'C1': EA, 'C2': EA, 'C3': EA, 'C4': EA, 'C5': EA, 'CX': EX, 'W1': EA, 'W2': EB, 'W3': EA, 'W4': EA, 'W5': EA, 'WX': EX, 'WC': EC}
for k, pid in PER.items():
    tn = T2 if emp[k] == EX else T
    seed += f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id) values ('{pid}','{tn}','{emp[k]}','PERSONA {k} MH','MH-{k}');\n"
    if k.startswith('W'):
        seed += f"insert into public.relaciones_laborales (tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values ('{tn}','{pid}','{emp[k]}','2025-01-01','vigente');\n"
seed += f"""insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values
 ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),('{U['consulta']}','{T}','consulta',null),
 ('{U['c1']}','{T}','coordinador','{PER['C1']}'),('{U['c2']}','{T}','coordinador','{PER['C2']}'),('{U['c3']}','{T}','coordinador','{PER['C3']}'),
 ('{U['c4']}','{T}','coordinador','{PER['C4']}'),('{U['c5']}','{T}','coordinador','{PER['C5']}'),
 ('{U['cx']}','{T2}','coordinador','{PER['CX']}'),('{U['nominax']}','{T2}','nomina',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial) values ('{EA}','{T}','2025-01-01'),('{EB}','{T}','2025-01-01'),('{EC}','{T}','2025-01-01'),('{EX}','{T2}','2025-01-01');
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)

def periodo(n, e_, user='nomina', per=SEM):
    a, b = sem(n)
    return val(f"select public.inc_crear_periodo('{e_}','{per}','{a}','{b}')", user)
PA0, PA1, PA2 = periodo(-3, EA), periodo(1, EA), periodo(2, EA)
PB1 = periodo(1, EB)
PC1, PC2, PC3, PC4 = periodo(1, EC), periodo(2, EC), periodo(3, EC), periodo(4, EC)
PX1 = periodo(1, EX, 'nominax', SEMX)
a0, f0 = sem(-3)
asig = f"""insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, hasta, origen) values
 ('{T}','{PER['W1']}','{PER['C1']}','2025-01-01',null,'carga_inicial'),
 ('{T}','{PER['W2']}','{PER['C2']}','2025-01-01',null,'carga_inicial'),
 ('{T}','{PER['W3']}','{PER['C3']}','2025-01-01','{f0}','carga_inicial'),
 ('{T}','{PER['W4']}','{PER['C4']}','2025-01-01',null,'carga_inicial'),
 ('{T}','{PER['W5']}','{PER['C5']}','{(datetime.date.fromisoformat(sem(1)[0]) + datetime.timedelta(days=3)).isoformat()}',null,'carga_inicial'),
 ('{T2}','{PER['WX']}','{PER['CX']}','2025-01-01',null,'carga_inicial')"""
o, e = sql(asig, replica=True)
if e: print(e); sys.exit(1)

def visibles(user):
    return set((val(f"select coalesce(string_agg(id::text, ','), '') from public.inc_periodos", user) or '').split(',')) - {''}
def abrir(user, per):
    return val(f"select public.inc_abrir_hoja('{per}')", user)
def faltantes(per):
    return val(f"select coalesce(string_agg(tipo||': '||detalle, ' | ' order by detalle), 'ninguno') from public.inc_faltantes_procesar('{per}')", 'nomina')
def hoja_vacia_historica(coord, per):
    """Hoja creada como las dos de B5 (antes de la corrección): insert directo, sin pasar por inc_abrir_hoja."""
    hid = val("select gen_random_uuid()")
    val(f"insert into public.inc_hojas (id, tenant_id, periodo_id, coordinador_id, tipo, hoja_raiz_id) values ('{hid}','{T}','{per}','{PER[coord]}','normal','{hid}')")
    return hid

print('== Preparación: C4 abre su hoja en PA1 y después pierde la asignación ==')
H4 = abrir('c4', PA1)
val(f"update public.inc_asignaciones set hasta = '{f0}' where personal_id = '{PER['W4']}' and coordinador_id = '{PER['C4']}'")
ok(H4 and val(f"select estado from public.inc_hojas where id='{H4}'") == 'borrador', 'C4 tiene una hoja en PA1; su asignación ahora termina antes de PA1')

print('== 1 y 2 · Visibilidad de periodos (D1) ==')
v1 = visibles('c1')
ok({PA0, PA1, PA2} <= v1, '1  Coordinador con personal en la empresa: ve sus periodos (PA0, PA1, PA2)')
ok(not (v1 & {PB1, PC1, PC2, PC3, PC4, PX1}), '2  … y no ve los de empresas donde no tiene personal (B, C) ni de otro tenant')
v3 = visibles('c3')
ok(v3 == {PA0}, '1b Asignación ya terminada: ve el periodo pasado en que estuvo vigente (PA0) y no los posteriores', str(len(v3)))
v4 = visibles('c4')
ok(PA1 in v4 and PA0 in v4 and PA2 not in v4, '1c Perdió la asignación: conserva el periodo con su hoja (PA1) y el pasado (PA0); no ve PA2')
v2 = visibles('c2')
ok(v2 == {PB1}, '2  Coordinador sin personal en A ni en C: solo ve el periodo de B', str(len(v2)))
ok(val(f"select count(*) from public.inc_periodos where id = '{PA1}'", 'c2') == '0', '2  … ni siquiera consultando el periodo ajeno por su id')
vx = visibles('cx')
ok(vx == {PX1}, '9  Otro tenant: el coordinador solo ve su periodo')
ok(len(visibles('nomina')) == 8 and len(visibles('admin')) == 8 and len(visibles('consulta')) == 8, 'Administrador, Nómina y Consulta: siguen viendo todos los periodos del tenant (8)')
ok(PX1 not in visibles('nomina') and visibles('nominax') == {PX1}, '9  Nómina de un tenant no ve periodos del otro')

print('== 3 y 4 · Abrir hoja (D2) ==')
H1 = abrir('c1', PA1)
ok(H1 and val(f"select coordinador_id from public.inc_hojas where id='{H1}'") == PER['C1'], '3  Con asignación vigente en el periodo: abre su hoja')
H5 = abrir('c5', PA1)
ok(H5 and val(f"select count(*) from public.inc_personas_hoja('{H5}')", 'c5') == '4', '3b Asignación que empieza a mitad del periodo: abre y ve los 4 días que le tocan')
falla_con(f"select public.inc_abrir_hoja('{PA1}')", 'c2', 'no tienes personas asignadas en EMPRESA A MH', '4  Sin asignaciones en la empresa: se rechaza y el mensaje nombra la empresa')
ok(val(f"select count(*) from public.inc_hojas where periodo_id='{PA1}' and coordinador_id='{PER['C2']}'") == '0', '4  … y no se crea ninguna hoja')
falla_con(f"select public.inc_abrir_hoja('{PA2}')", 'c4', 'no tienes personas asignadas', '4b Perdió la asignación: no puede abrir un periodo nuevo (PA2)')
falla_con(f"select public.inc_abrir_hoja('{PX1}')", 'c1', 'periodo no encontrado', '9  No puede abrir una hoja en un periodo de otro tenant')
ok(abrir('c4', PA1) == H4, '1c Su hoja existente se sigue abriendo (devuelve la misma hoja)')

print('== 5 · Hoja con personal y sin incidencias se envía ==')
H2 = abrir('c2', PB1)
v = val(f"select public.inc_enviar_hoja('{H2}')", 'c2')
ok(v and val(f"select estado||' v'||version_actual from public.inc_hojas where id='{H2}'") == 'enviada v1', '5  Sin capturas, con personal asignado: se envía (versión 1)')

print('== 6 y 10 · Hoja vacía sin personal (como las de B5) ==')
HV1 = hoja_vacia_historica('C2', PC1)
ok(PC1 in visibles('c2'), '6  El coordinador conserva la vista del periodo de su hoja vacía (C)')
ok(abrir('c2', PC1) == HV1, '6  Abrirla devuelve la hoja existente (no se crea otra)')
falla_con(f"select public.inc_enviar_hoja('{HV1}')", 'c2', 'no tienes personas asignadas', '10 Enviar la hoja vacía sin personal: se rechaza')
ok(val(f"select estado||' v'||version_actual||' '||(select count(*) from public.inc_versiones where hoja_id='{HV1}') from public.inc_hojas where id='{HV1}'") == 'borrador v0 0', '10 … y sigue en borrador, sin versiones')
tb = val(f"select string_agg(coordinador||':'||personas||':'||estado, ',') from public.inc_tablero_periodo('{PC1}')", 'nomina')
ok(tb == 'PERSONA C2 MH:0:borrador', '6  Nómina la sigue viendo en el tablero (0 personas, borrador)', tb)
f1 = faltantes(PC1)
ok(f1 == 'ninguno', '6  No aparece en faltantes', f1)
ok(val(f"select public.inc_marcar_procesado('{PC1}')", 'nomina') == 'Periodo marcado como procesado.', '6  El periodo se procesa')
ok(val(f"select estado||' v'||version_actual from public.inc_hojas where id='{HV1}'") == 'borrador v0', '6  La hoja vacía se conserva tal cual (no se borra ni se altera)')

print('== 6b · Con cualquier captura u observación, bloquea como hoy ==')
HV2 = hoja_vacia_historica('C2', PC2)
val(f"insert into public.inc_observaciones (tenant_id, hoja_id, personal_id, texto) values ('{T}','{HV2}','{PER['WC']}','Observación de prueba')")
f2 = faltantes(PC2)
ok('PERSONA C2 MH: no ha enviado su hoja' in f2, '6b Sin personal pero con una observación por persona: bloquea', f2)
HV3 = hoja_vacia_historica('C2', PC3)
val(f"update public.inc_hojas set observacion_general = 'Nota general' where id = '{HV3}'")
f3 = faltantes(PC3)
ok('PERSONA C2 MH: no ha enviado su hoja' in f3, '6b Sin personal pero con observación general: bloquea', f3)
falla_con(f"select public.inc_marcar_procesado('{PC3}')", 'nomina', 'no se puede procesar', '6b … y el procesado se rechaza')
HV4 = hoja_vacia_historica('C2', PC4)
v = val(f"select public.inc_enviar_hoja('{HV4}', 'Aviso: sin gente esta semana')", 'c2')
ok(v and val(f"select estado from public.inc_hojas where id='{HV4}'") == 'enviada', '10b Sin personal pero con observación general al enviar: se envía (comportamiento normal)')

print('== 7 · Hojas con personal sin enviar bloquean ==')
f4 = faltantes(PA1)
ok('PERSONA C1 MH: no ha enviado su hoja' in f4 and 'PERSONA C5 MH: no ha enviado su hoja' in f4, '7  Hojas con personal en borrador: bloquean', f4[:140])
ok('PERSONA C4 MH' not in f4 and val(f"select public.inc_coordinador_tiene_personal('{PER['C4']}','{PA1}')") == 'f',
   '6c La hoja de C4 (perdió la asignación, sin capturas) es una hoja vacía sin personal: no bloquea')
val(f"select public.inc_devolver_hoja('{H2}', 'Revisar faltas', 'nomina')", 'nomina')
f5 = faltantes(PB1)
ok('PERSONA C2 MH: su hoja está devuelta' in f5, '7b Hoja devuelta: bloquea igual que hoy', f5)

print('== 8 y 9 · Nombre de empresa sin ampliar permisos (D3) ==')
ev = lambda u: val("select coalesce(string_agg(nombre, ',' order by nombre), '') from public.inc_empresas_visibles()", u)
ok(ev('c1') == 'EMPRESA A MH', '8  C1 obtiene solo el nombre de su empresa', ev('c1'))
ok(ev('c2') == 'EMPRESA B MH,EMPRESA C MH', '8  C2: su empresa y la de sus hojas (B y C), no A', ev('c2'))
ok(val("select count(*) from public.empresas", 'c1') == '0', '8  La tabla empresas sigue sin filas para el coordinador (permisos sin cambio)')
ok(val("select policyname||'|'||qual from pg_policies where tablename='empresas' and cmd='SELECT'") ==
   "empresas_select|((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text]))", '8  La política de empresas no cambió')
ok(ev('cx') == 'EMPRESA OTRO TENANT MH', '9  Otro tenant: solo su empresa', ev('cx'))
ok('EMPRESA OTRO TENANT MH' not in ev('nomina'), '9  Nómina no obtiene empresas de otro tenant')

print('== E · Funciones internas ==')
for q in ["public.inc_coordinador_tiene_personal(null, null)", "public.inc_hoja_vacia_sin_personal(null)"]:
    out, err = sql(f"select {q}", 'c1')
    ok('permission denied' in err, 'E  Interna no expuesta a la aplicación', q.split('(')[0])
out, err = sql(f"select public.inc_periodo_visible('{PB1}')", 'c1')
ok(not err and out.splitlines()[-1] == 'f', 'E  inc_periodo_visible solo responde verdadero/falso para quien llama (la política la necesita)')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
sys.exit(1 if malas else 0)
