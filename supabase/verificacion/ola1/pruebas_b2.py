"""Pruebas de aceptación de B2 (incidencias ↔ relación laboral ↔ esquemas de pago)
en una base Postgres LOCAL y desechable (puerto 55432, base bh), con Ola 1, fase 1 y B2.
Cada paso corre en su propia transacción con la identidad de un usuario (rol
authenticated + claim sub), igual que una petición real de la app.
Uso: python3 pruebas_b2.py"""
import subprocess, json, sys, datetime, os

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
res = []

def sql(q, user=None, replica=False):
    pre = 'begin;\n'
    if replica: pre += "set local session_replication_role = replica;\n"
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    out = '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET'))
    return out, p.stderr.strip()

def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''

def ok(cond, nombre, detalle=''):
    res.append((nombre, bool(cond), detalle))
    print(('OK    ' if cond else 'FALLA ') + nombre + (f'  [{detalle}]' if detalle else ''))

def falla_con(q, user, texto, nombre):
    out, err = sql(q, user)
    ok(err and texto.lower() in err.lower(), nombre, (err.split('\n')[0][:150] if err else 'NO FALLÓ: ' + out[:80]))

# ---------------- Datos ficticios ----------------
T = '1a000000-0000-4000-8000-000000000001'
U = {k: f'1b000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta'], 1)}
E1, E2 = '1c000000-0000-4000-8000-000000000001', '1c000000-0000-4000-8000-000000000002'
RP1 = '1c100000-0000-4000-8000-000000000001'
SEM, MEN = '1e000000-0000-4000-8000-000000000007', '1e000000-0000-4000-8000-000000000030'
CL = {'IMSS': '1f000000-0000-4000-8000-000000000001', 'EFECTIVO': '1f000000-0000-4000-8000-000000000002',
      'TRANSFERENCIA': '1f000000-0000-4000-8000-000000000003'}
P = {k: f'1a100000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['CA', 'CB', 'MULTI', 'VARIOS', 'BAJA', 'SINREL', 'NOENL'], 1)}
R = {k: f'1a200000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(
    ['CA', 'CB', 'MULTI_E1', 'MULTI_E2', 'VARIOS_RP', 'VARIOS_SINRP', 'BAJA', 'SINREL_E2', 'NOENL'], 1)}
RG = {k: f'1a300000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(
    ['MULTI_IMSS', 'MULTI_EFE', 'VARIOS_IMSS', 'VARIOS_EFE', 'VARIOS_TRA', 'BAJA_IMSS', 'NOENL_IMSS'], 1)}
hoy = datetime.date.fromisoformat(val('select public.hoy_mx()'))
lunes = hoy + datetime.timedelta(days=(7 - hoy.weekday()) % 7 or 7)
dom = lunes + datetime.timedelta(days=6)
d = lambda n: (lunes + datetime.timedelta(days=n)).isoformat()

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT SINTETICO B2');
insert into auth.users (id, email) select v, k||'.b2@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA UNO'),('{E2}','{T}','EMPRESA DOS');
insert into public.empresas_registros_patronales (id, tenant_id, empresa_id, registro_patronal) values ('{RP1}','{T}','{E1}','Y1234567100');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{MEN}','{T}','MENSUAL',30),('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values {','.join(f"('{v}','{T}','{k}')" for k, v in CL.items())};
"""
fichas = {  # empresa que dice la ficha (B2 ya no la usa para decidir)
    'CA': E1, 'CB': E1, 'MULTI': E1, 'VARIOS': E1, 'BAJA': E1, 'SINREL': E1, 'NOENL': E1}
for k, emp in fichas.items():
    co = 'null' if k in ('CA', 'CB') else f"'{P['CA']}'"
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id) values "
             f"('{P[k]}','{T}','{emp}','PERSONA {k}','B2-{k}',{co});\n")
rels = [  # (clave, persona, empresa, RP, estado, baja)
    ('CA', 'CA', E1, None, 'vigente', None), ('CB', 'CB', E1, None, 'vigente', None),
    ('MULTI_E1', 'MULTI', E1, RP1, 'vigente', None), ('MULTI_E2', 'MULTI', E2, None, 'vigente', None),
    ('VARIOS_RP', 'VARIOS', E1, RP1, 'vigente', None), ('VARIOS_SINRP', 'VARIOS', E1, None, 'vigente', None),
    ('BAJA', 'BAJA', E1, RP1, 'baja', d(2)), ('SINREL_E2', 'SINREL', E2, None, 'vigente', None),
    ('NOENL', 'NOENL', E1, RP1, 'vigente', None)]
for k, pk, emp, rp, est, baja in rels:
    seed += (f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, registro_patronal_id, fecha_ingreso, estado, fecha_baja, causa_baja) values "
             f"('{R[k]}','{T}','{P[pk]}','{emp}',{repr(rp) if rp else 'null'},'2025-01-01','{est}',{repr(baja) if baja else 'null'},{repr('2') if baja else 'null'});\n")
esq = [  # (clave, persona, relación o None, empresa, RP, clasificación, periodicidad, sueldo, modalidad, días, activo, fin)
    ('MULTI_IMSS', 'MULTI', 'MULTI_E1', E1, RP1, 'IMSS', MEN, 30000, 'bruto', 30, True, None),           # 1,000 diarios bruto
    ('MULTI_EFE', 'MULTI', 'MULTI_E2', E2, None, 'EFECTIVO', SEM, 1400, 'neto', 7, True, None),          # 200 diarios neto (otra empresa)
    ('VARIOS_IMSS', 'VARIOS', 'VARIOS_RP', E1, RP1, 'IMSS', MEN, 24000, 'bruto', 30, True, None),        # 800 bruto
    ('VARIOS_EFE', 'VARIOS', 'VARIOS_SINRP', E1, None, 'EFECTIVO', SEM, 700, 'neto', 7, True, None),     # 100 neto
    ('VARIOS_TRA', 'VARIOS', 'VARIOS_SINRP', E1, None, 'TRANSFERENCIA', MEN, 3000, 'neto', 30, True, None),  # 100 neto
    ('BAJA_IMSS', 'BAJA', 'BAJA', E1, RP1, 'IMSS', MEN, 9000, 'bruto', 30, False, d(2)),                 # 300 bruto, cerrado con la baja
    ('NOENL_IMSS', 'NOENL', None, E1, RP1, 'IMSS', MEN, 15000, 'bruto', 30, True, None)]                 # sin enlazar a la relación
for k, pk, rk, emp, rp, cl, per, su, mo, di, act, fin in esq:
    seed += (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, registro_patronal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo, fecha_fin) values "
             f"('{RG[k]}','{T}','{P[pk]}',{repr(R[rk]) if rk else 'null'},'{emp}',{repr(rp) if rp else 'null'},'{CL[cl]}','{per}',{su},'{mo}',{di},'2025-01-01',{str(act).lower()},{repr(fin) if fin else 'null'});\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values
 ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null);
insert into public.usuario_alcances (tenant_id, user_id, empresa_id) values ('{T}','{U['consulta']}','{E1}');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, public.hoy_mx(), 'carga_inicial', 'prueba B2' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('1d000000-0000-4000-8000-000000000001','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('1d000000-0000-4000-8000-000000000002','{T}','{E1}','Turno nocturno','T','turnos','turno','tarifa',700,null,2),
 ('1d000000-0000-4000-8000-000000000003','{T}','{E1}','Domingo trabajado','DOM','dias','domingo','beehuman',null,null,3),
 ('1d000000-0000-4000-8000-000000000004','{T}','{E2}','Horas extra','HE2','horas','horas_extra','beehuman',null,2,1);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
K = {'HE': '1d000000-0000-4000-8000-000000000001', 'T': '1d000000-0000-4000-8000-000000000002',
     'DOM': '1d000000-0000-4000-8000-000000000003', 'HE2': '1d000000-0000-4000-8000-000000000004'}
print(f'Semana de prueba: {lunes} a {dom}')

# =====================================================================
print('\n== A. Quién entra a la hoja y con qué relación ==')
PER1 = val(f"select public.inc_crear_periodo('{E1}','{SEM}','{lunes}','{dom}')", 'nomina')
PER2 = val(f"select public.inc_crear_periodo('{E2}','{SEM}','{lunes}','{dom}')", 'nomina')
H1 = val(f"select public.inc_abrir_hoja('{PER1}')", 'coordA')
H2 = val(f"select public.inc_abrir_hoja('{PER2}')", 'coordA')
def dias_rel(hoja, pk):
    return val(f"select count(*)||' '||coalesce(string_agg(distinct relacion_laboral_id::text, ','),'-') from public.inc_personas_hoja('{hoja}') where personal_id='{P[pk]}'", 'coordA')
ok(dias_rel(H1, 'MULTI') == f"7 {R['MULTI_E1']}" and dias_rel(H2, 'MULTI') == f"7 {R['MULTI_E2']}",
   'A1 Dos empresas: aparece en la hoja de cada empresa, cada una con su propia relación', f"E1={dias_rel(H1,'MULTI')[:12]} E2={dias_rel(H2,'MULTI')[:12]}")
ok(dias_rel(H1, 'VARIOS') == f"7 {R['VARIOS_RP']}", 'A2 Dos relaciones en la misma empresa: la hoja usa la que tiene registro patronal', dias_rel(H1, 'VARIOS')[:12])
ok(val(f"select count(*)||' '||max(fecha) from public.inc_personas_hoja('{H1}') where personal_id='{P['BAJA']}'", 'coordA') == f'3 {d(2)}',
   'A3 Relación dada de baja el miércoles: aparece lunes a miércoles')
ok(dias_rel(H1, 'SINREL') == '0 -' and dias_rel(H2, 'SINREL').startswith('7 '),
   'A4 Sin relación con la empresa del periodo: no aparece en su hoja aunque la ficha diga esa empresa; sí en la de su empresa real')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H1}','{P['SINREL']}','{d(0)}','{K['HE']}',2)",
          'coordA', 'no tiene relación laboral vigente', 'A5 Captura a persona sin relación vigente en la empresa: rechazada')
falla_con(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H1}','{P['BAJA']}','{d(3)}','F')",
          'coordA', 'no tiene relación laboral vigente', 'A6 Captura después de la baja: rechazada')

# Captura
cap1 = [("MULTI", 0, 'HE', 2), ("VARIOS", 0, 'HE', 2), ("BAJA", 1, 'HE', 2), ("NOENL", 0, 'HE', 2), ("VARIOS", 1, 'T', 1), ("VARIOS", 6, 'DOM', 1)]
val("insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values " +
    ','.join(f"('{H1}','{P[p]}','{d(n)}','{K[c]}',{q})" for p, n, c, q in cap1), 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H2}','{P['MULTI']}','{d(0)}','{K['HE2']}',2)", 'coordA')
guard = val(f"select string_agg(q.personal_id::text||'>'||q.relacion_laboral_id::text, ',' order by pe.empresa_id) from public.inc_cantidades q join public.inc_periodos pe on pe.id=q.periodo_id where q.personal_id='{P['MULTI']}'")
ok(guard == f"{P['MULTI']}>{R['MULTI_E1']},{P['MULTI']}>{R['MULTI_E2']}", 'A7 Cada renglón capturado guarda la relación de su empresa')

# =====================================================================
print('\n== B. Importes por empresa, relación y esquema ==')
V1 = val(f"select public.inc_enviar_hoja('{H1}')", 'coordA')
V2 = val(f"select public.inc_enviar_hoja('{H2}')", 'coordA')
def lineas(ver, pk, ck):
    return val(f"""select coalesce(string_agg(coalesce(c.nombre,'-')||'|'||coalesce(i.modalidad,'-')||'|'||coalesce(i.sugerido::text,'null')||'|'||i.origen
                   ||'|'||case i.relacion_laboral_id {' '.join(f"when '{v}' then '{k}'" for k, v in R.items())} else '-' end, ' ; '
                   order by coalesce(i.modalidad,''), coalesce(c.nombre,'')), 'ninguna')
                   from public.inc_importes i left join public.personal_registros_pago r on r.id = i.registro_pago_id
                   left join public.clasificaciones_personal c on c.id = r.clasificacion_id
                   where i.version_id='{ver}' and i.personal_id='{P[pk]}' and i.concepto_id='{K[ck]}' and i.origen <> 'descartado'""", 'nomina')
x = lineas(V1, 'MULTI', 'HE')
ok(x == 'IMSS|bruto|500.00|pendiente|MULTI_E1', 'B1 Dos empresas, periodo de la empresa 1: solo el esquema IMSS de esa relación (2 h × 1,000/8 × 2)', x)
x = lineas(V2, 'MULTI', 'HE2')
ok(x == 'EFECTIVO|neto|100.00|pendiente|MULTI_E2', 'B2 Dos empresas, periodo de la empresa 2: solo el efectivo de esa relación (2 h × 200/8 × 2)', x)
x = lineas(V1, 'VARIOS', 'HE')
ok(x == 'IMSS|bruto|400.00|pendiente|VARIOS_RP ; EFECTIVO|neto|50.00|pendiente|VARIOS_SINRP ; TRANSFERENCIA|neto|50.00|pendiente|VARIOS_SINRP',
   'B3 Varios esquemas: una línea por esquema (IMSS bruto, efectivo neto, transferencia neto), cada una con su relación', x)
tot = val(f"select string_agg(modalidad||'='||s, ' ' order by modalidad) from (select modalidad, sum(sugerido) s from public.inc_importes where version_id='{V1}' and personal_id='{P['VARIOS']}' and concepto_id='{K['HE']}' group by 1) z", 'nomina')
ok(tot == 'bruto=400.00 neto=100.00', 'B4 Bruto y neto quedan separados; nunca se suman en un solo sueldo', tot)
x = lineas(V1, 'VARIOS', 'DOM')
ok(x == 'IMSS|bruto|200.00|pendiente|VARIOS_RP ; EFECTIVO|neto|25.00|pendiente|VARIOS_SINRP ; TRANSFERENCIA|neto|25.00|pendiente|VARIOS_SINRP',
   'B5 Prima dominical por esquema (25 % de 800, 100 y 100)', x)
x = lineas(V1, 'VARIOS', 'T')
# B1.1: con varios esquemas vigentes y sin esquema preferido, la línea por tarifa queda «por asignar» (antes: aceptada sin esquema)
ok(x == '-|-|700.00|por_asignar|VARIOS_RP', 'B6 Concepto por tarifa: una línea, ligada a la relación; con varios esquemas queda por asignar (B1.1)', x)
x = lineas(V1, 'BAJA', 'HE')
ok(x == 'IMSS|bruto|150.00|pendiente|BAJA', 'B7 Relación dada de baja: el día anterior a la baja se paga con su esquema ya cerrado (2 h × 300/8 × 2)', x)
x = lineas(V1, 'NOENL', 'HE')
ok(x == '-|-|null|sin_sueldo|NOENL', 'B8 Esquema no enlazado a la relación: no se usa; queda «sin sueldo» (no se inventa)', x)
mot = val(f"select detalle->>'motivo' from public.inc_importes where version_id='{V1}' and personal_id='{P['NOENL']}'", 'nomina')
ok('Sin esquema de pago enlazado' in (mot or ''), 'B8b La línea explica por qué no tiene sueldo', mot)
e2 = val(f"select count(*) from public.inc_importes i join public.personal_registros_pago r on r.id=i.registro_pago_id where i.version_id='{V1}' and r.empresa_id <> '{E1}'", 'nomina')
ok(e2 == '0', 'B9 Ningún importe del periodo de la empresa 1 sale de un esquema de otra empresa', e2)
# Base neto: Nómina devuelve, el Administrador cambia la base, el coordinador reenvía → versión 2
val(f"select public.inc_devolver_hoja('{H1}','Revisión de base','nomina')", 'nomina')
val(f"update public.inc_parametros set base_calculo='neto' where empresa_id='{E1}'", 'admin')
V1b = val(f"select public.inc_enviar_hoja('{H1}')", 'coordA')
x = lineas(V1b, 'VARIOS', 'HE')
ok(x == 'EFECTIVO|neto|50.00|pendiente|VARIOS_SINRP ; TRANSFERENCIA|neto|50.00|pendiente|VARIOS_SINRP', 'B10 Base «neto»: solo esquemas netos; el bruto no entra', x)
x = lineas(V1b, 'MULTI', 'HE')
ok(x == '-|-|null|sin_sueldo|MULTI_E1', 'B11 Base «neto» y la relación solo tiene IMSS bruto: sin sueldo (no toma el neto de la otra empresa)', x)
ok(lineas(V1, 'VARIOS', 'HE').count(';') == 2, 'B12 La versión 1 conserva sus líneas calculadas con base mixta')
# Sueldo manual y recálculo
val(f"select public.inc_capturar_sueldo_manual('{PER1}','{P['NOENL']}',400)", 'nomina')
x = lineas(V1b, 'NOENL', 'HE')
ok(x == '-|manual|200.00|pendiente|NOENL', 'B13 Sueldo manual de Nómina: misma línea, ahora con importe (2 h × 400/8 × 2)', x)
# Un esquema deja de aplicar → su línea queda «descartado», no se borra
val(f"update public.personal_registros_pago set activo=false, fecha_fin='{(lunes - datetime.timedelta(days=1)).isoformat()}' where id='{RG['VARIOS_TRA']}'", 'admin')
val(f"select public.inc_capturar_sueldo_manual('{PER1}','{P['NOENL']}',400)", 'nomina')
x = lineas(V1b, 'VARIOS', 'HE')
dsc = val(f"select count(*) from public.inc_importes where version_id='{V1b}' and personal_id='{P['VARIOS']}' and registro_pago_id='{RG['VARIOS_TRA']}' and concepto_id='{K['HE']}' and origen='descartado' and final is null", 'nomina')
ok(x == 'EFECTIVO|neto|50.00|pendiente|VARIOS_SINRP' and dsc == '1', 'B14 Esquema cerrado antes del periodo: su línea queda «descartado» (los importes no se borran)', x)
iid = val(f"select id from public.inc_importes where version_id='{V1b}' and registro_pago_id='{RG['VARIOS_EFE']}' and concepto_id='{K['HE']}'", 'nomina')
val(f"select public.inc_decidir_importe('{iid}', 60, 'B1.1: motivo obligatorio')", 'nomina')
val(f"select public.inc_capturar_sueldo_manual('{PER1}','{P['NOENL']}',400)", 'nomina')
ok(val(f"select final||'/'||origen from public.inc_importes where id='{iid}'", 'nomina') == '60.00/modificado', 'B15 Un recálculo no pisa la línea que Nómina modificó')

# =====================================================================
print('\n== C. Borrado de capturas según permisos ==')
ok(val("select count(*) from information_schema.role_table_grants where grantee='authenticated' and privilege_type='DELETE' and table_name in ('inc_celdas','inc_cantidades','inc_observaciones','inc_tarifas_area')") == '4',
   'C0 authenticated tiene DELETE en las 4 tablas de captura y tarifas')
# Hoja 1 está enviada: abrir otra semana para capturas en borrador
lunes2 = lunes + datetime.timedelta(days=7); d2 = lambda n: (lunes2 + datetime.timedelta(days=n)).isoformat()
PER3 = val(f"select public.inc_crear_periodo('{E1}','{SEM}','{lunes2}','{(lunes2 + datetime.timedelta(days=6)).isoformat()}')", 'nomina')
H4 = val(f"select public.inc_abrir_hoja('{PER3}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H4}','{P['VARIOS']}','{d2(0)}','{K['HE']}',1),('{H4}','{P['VARIOS']}','{d2(1)}','{K['HE']}',1)", 'coordA')
val(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H4}','{P['VARIOS']}','{d2(2)}','F')", 'coordA')
val(f"insert into public.inc_observaciones (hoja_id, personal_id, texto) values ('{H4}','{P['VARIOS']}','nota')", 'coordA')
cnt = lambda t: val(f"select count(*) from public.{t} where hoja_id='{H4}'")
val(f"delete from public.inc_cantidades where hoja_id='{H4}' and fecha='{d2(1)}'", 'coordB')
ok(cnt('inc_cantidades') == '2', 'C1 Otro coordinador no puede borrar la captura ajena (no se borra nada)')
val(f"delete from public.inc_cantidades where hoja_id='{H4}'", 'consulta')
val(f"delete from public.inc_cantidades where hoja_id='{H4}'", 'nomina')
ok(cnt('inc_cantidades') == '2', 'C2 Consulta y Nómina no borran capturas del coordinador')
val(f"delete from public.inc_cantidades where hoja_id='{H4}' and fecha='{d2(1)}'", 'coordA')
val(f"delete from public.inc_celdas where hoja_id='{H4}'", 'coordA')
val(f"delete from public.inc_observaciones where hoja_id='{H4}'", 'coordA')
ok(cnt('inc_cantidades') == '1' and cnt('inc_celdas') == '0' and cnt('inc_observaciones') == '0',
   'C3 El coordinador dueño borra su captura en borrador (cantidad, día y observación)')
val(f"select public.inc_enviar_hoja('{H4}')", 'coordA')
val(f"delete from public.inc_cantidades where hoja_id='{H4}'", 'coordA')
falla_con(f"delete from public.inc_cantidades where hoja_id='{H4}'", None, 'ya fue enviada', 'C4 Hoja enviada: nadie borra la captura (ni el dueño de la base)')
ok(cnt('inc_cantidades') == '1', 'C4b Hoja enviada: el coordinador tampoco la borra')
val(f"insert into public.areas (id, tenant_id, nombre) values ('1d100000-0000-4000-8000-000000000001','{T}','AREA B2')", replica=True)
val(f"insert into public.inc_tarifas_area (tenant_id, concepto_id, area_id, tarifa) values ('{T}','{K['T']}','1d100000-0000-4000-8000-000000000001',800)", 'admin')
val(f"delete from public.inc_tarifas_area where concepto_id='{K['T']}'", 'nomina')
ok(val(f"select count(*) from public.inc_tarifas_area where concepto_id='{K['T']}'") == '1', 'C5 Nómina no borra tarifas por área')
val(f"delete from public.inc_tarifas_area where concepto_id='{K['T']}'", 'admin')
ok(val(f"select count(*) from public.inc_tarifas_area where concepto_id='{K['T']}'") == '0', 'C6 El Administrador sí borra una tarifa por área')

# =====================================================================
print('\n== D. Privacidad ==')
for rol in ['coordA', 'consulta']:
    ok(val("select count(*) from public.inc_importes", rol) == '0', f'D1 {rol}: no ve importes')
    falla_con(f"select * from public.inc_esquemas_dia('{P['VARIOS']}','{E1}','{d(0)}','mixto')", rol, 'permission denied', f'D2 {rol}: no ejecuta el sueldo por esquema')
    falla_con(f"select public.inc_relacion_en('{P['VARIOS']}','{E1}','{d(0)}')", rol, 'permission denied', f'D3 {rol}: no ejecuta la búsqueda interna de relación')
cols = val("select string_agg(name, ',') from (select unnest(proargnames) name from pg_proc where proname='inc_personas_hoja') x")
ok(not any(w in cols for w in ('sueldo', 'importe', 'sd')), 'D4 La lista de personas de la hoja no trae sueldos', cols)
falla_con(f"delete from public.inc_importes where version_id='{V1}'", None, 'registro histórico', 'D5 Los importes no se borran (ni el dueño de la base)')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for n, _, det in malas: print('  FALLA:', n, det)
sys.exit(1 if malas else 0)
