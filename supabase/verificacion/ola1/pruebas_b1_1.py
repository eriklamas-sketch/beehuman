"""Pruebas de base de B1.1 (valor por hora configurable) en la base LOCAL desechable
(puerto 55432) con Ola 1 + fase 1 + B2 + B1 + B1.1.
Criterios: claude/B1-1-valor-hora-criterios-aceptacion-12nov.md y precisiones de Erik (12-nov 10:47):
  1 umbral semanal acumulado entre días (A3)
  2 esquema preferido solo si está vigente en la fecha (B7, B7b)
  3 asignación manual válida se conserva al recalcular (B5) y deja de usarse si deja de ser válida (B5b)
  4 bitácora inalterable en la base (D4)
  5 periodo procesado protegido también desde el servidor (D3)
Uso: DB=bh python3 pruebas_b1_1.py"""
import subprocess, json, sys, datetime, os

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
    out, err = sql(q, user); ok(err and texto.lower() in err.lower(), n, (err.split('\n')[0][:150] if err else 'NO FALLÓ'))

i = iter(range(1, 99)); uid = lambda p: f'{p}-0000-4000-8000-0000000000{next(i):02d}'
T, T2 = '3a000000-0000-4000-8000-000000000001', '3a000000-0000-4000-8000-000000000002'
U = {k: f'3b000000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta', 'nomina2'], 1)}
EA, EB, EX = '3c000000-0000-4000-8000-000000000001', '3c000000-0000-4000-8000-000000000002', '3c000000-0000-4000-8000-000000000003'
SEM, MEN = '3e000000-0000-4000-8000-000000000007', '3e000000-0000-4000-8000-000000000030'
IMSS, EFE = '3f000000-0000-4000-8000-000000000001', '3f000000-0000-4000-8000-000000000002'
P = {k: f'3a100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['CA', 'CB', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'PB', 'Q'], 1)}
REL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
K = {k: f'3d000000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['HE-S', 'HE-T', 'HE-TE', 'HS-T', 'HS-S', 'B-HE-T'], 1)}
hoy = datetime.date.fromisoformat(val('select public.hoy_mx()'))
lunes = hoy + datetime.timedelta(days=(7 - hoy.weekday()) % 7 or 7)
semana = lambda n: lunes + datetime.timedelta(days=7 * n)
fecha = lambda n, d=0: (semana(n) + datetime.timedelta(days=d)).isoformat()
RP = {}
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B11'),('{T2}','OTRO TENANT B11');
insert into auth.users (id, email) select v, k||'.b11@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A'),('{EB}','{T}','EMPRESA B'),('{EX}','{T2}','EMPRESA OTRA');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7),('{MEN}','{T}','MENSUAL',30);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IMSS}','{T}','IMSS'),('{EFE}','{T}','EFECTIVO');
insert into public.inc_parametros (empresa_id, tenant_id, jornada_horas, umbral_triples_semana, factor_doble, factor_triple, responsable_nomina_user)
  values ('{EA}','{T}',8,9,2,3,'{U['nomina']}'),('{EB}','{T}',8,null,2,3,'{U['nomina']}');
"""
for k in P:
    emp = EB if k == 'PB' else EA
    co = 'null' if k in ('CA', 'CB') else (f"'{P['CB']}'" if k == 'PB' else f"'{P['CA']}'")
    seed += f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id) values ('{P[k]}','{T}','{emp}','PERSONA {k}','B11-{k}',{co});\n"
    if k not in ('CA', 'CB'):
        seed += f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values ('{REL[k]}','{T}','{P[k]}','{emp}','2025-01-01','vigente');\n"
def esquema(nombre, per, cl, per_id, sueldo, modal, dias, rel=True, ini='2025-01-01', fin=None, activo=True, emp=EA):
    RP[nombre] = uid('3a200000')
    return (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, fecha_fin, activo) values "
            f"('{RP[nombre]}','{T}','{P[per]}',{f"'{REL[per]}'" if rel else 'null'},'{emp}','{cl}','{per_id}',{sueldo},'{modal}',{dias},'{ini}',{f"'{fin}'" if fin else 'null'},{str(activo).lower()});\n")
seed += esquema('P1-IMSS', 'P1', IMSS, MEN, 20000, 'bruto', 30)
seed += esquema('P2-IMSS', 'P2', IMSS, MEN, 24000, 'bruto', 30)
seed += esquema('P2-EFE', 'P2', EFE, SEM, 700, 'neto', 7)
seed += esquema('P2-VIEJO', 'P2', EFE, SEM, 500, 'neto', 7, ini='2025-01-01', fin='2025-06-30', activo=False)
seed += esquema('P3-SUELTO', 'P3', IMSS, MEN, 15000, 'bruto', 30, rel=False)
seed += esquema('P5-IMSS', 'P5', IMSS, MEN, 15000, 'bruto', 30)
seed += esquema('P5-EFE', 'P5', EFE, SEM, 700, 'neto', 7)
seed += esquema('P6-IMSS', 'P6', IMSS, MEN, 15000, 'bruto', 30)
seed += esquema('P6-EFE', 'P6', EFE, SEM, 700, 'neto', 7, ini=fecha(20, 3))   # EFECTIVO empieza a mitad de la semana 20
seed += esquema('PB-IMSS', 'PB', IMSS, MEN, 20000, 'bruto', 30, emp=EB)
seed += esquema('Q-IMSS', 'Q', IMSS, MEN, 20000, 'bruto', 30)
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null),('{U['nomina2']}','{T2}','nomina',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, public.hoy_mx(), 'carga_inicial', 'B11' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, clasificacion_pago_id, orden) values
 ('{K['HE-S']}','{T}','{EA}','Horas extra sueldo','HES','horas','horas_extra','beehuman',null,null,null,1),
 ('{K['HE-T']}','{T}','{EA}','Horas extra tarifa','HET','horas','horas_extra','tarifa',50,null,null,2),
 ('{K['HE-TE']}','{T}','{EA}','Horas extra efectivo','HETE','horas','horas_extra','tarifa',50,null,'{EFE}',3),
 ('{K['HS-T']}','{T}','{EA}','Horas sencillas tarifa','HST','horas','horas','tarifa',50,null,null,4),
 ('{K['HS-S']}','{T}','{EA}','Horas sencillas sueldo','HSS','horas','horas','beehuman',null,null,null,5),
 ('{K['B-HE-T']}','{T}','{EB}','Horas extra tarifa B','HET','horas','horas_extra','tarifa',60,null,null,1);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)

PERIODOS = {}
def caso(n, capturas, emp=EA, coord='coordA', dias=7):
    """Periodo propio (semana n), hoja del coordinador, captura y envío. Devuelve (periodo, hoja, versión)."""
    per = val(f"select public.inc_crear_periodo('{emp}','{SEM}','{fecha(n)}','{fecha(n, dias - 1)}')", 'nomina')
    h = val(f"select public.inc_abrir_hoja('{per}')", coord)
    filas = ','.join(f"('{h}','{P[p]}','{fecha(n, d)}','{K[c]}',{q})" for p, d, c, q in capturas)
    val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values {filas}", coord)
    v = val(f"select public.inc_enviar_hoja('{h}')", coord)
    PERIODOS[n] = (per, h, v)
    return per, h, v
def lineas(v, persona=None, concepto=None):
    w = f"version_id='{v}'" + (f" and personal_id='{P[persona]}'" if persona else '') + (f" and concepto_id='{K[concepto]}'" if concepto else '')
    out = val(f"select coalesce(json_agg(json_build_object('id',id,'rp',registro_pago_id,'mod',modalidad,'sug',sugerido,'final',final,'origen',origen,'det',detalle,'asig',esquema_asignado_por) order by modalidad nulls last, sugerido),'[]') from public.inc_importes where {w} and origen <> 'descartado'", 'nomina')
    return json.loads(out)
fmt = lambda ls: '; '.join(f"{l['mod']}:{l['sug']}:{l['origen']}" for l in ls)

print('== A Cálculo ==')
_, _, v = caso(1, [('P1', 0, 'HE-S', 1)]); l = lineas(v, 'P1')
ok(len(l) == 1 and l[0]['sug'] == 166.67 and l[0]['mod'] == 'bruto' and l[0]['rp'] == RP['P1-IMSS'] and abs(l[0]['det']['valor_hora'] - 83.3333) < 1e-4 and l[0]['det']['origen_valor'] == 'sueldo',
   'A1 HE del sueldo, 1 h: 1 × 83.33 × 2 = 166.67 (valor por hora 83.33, IMSS bruto)', fmt(l) + f" vh={l[0]['det'].get('valor_hora')}")
_, _, v = caso(2, [('P1', 0, 'HE-S', 14)]); l = lineas(v, 'P1')
ok(len(l) == 1 and l[0]['sug'] == 2750.00 and l[0]['det']['horas_dobles'] == 9 and l[0]['det']['horas_triples'] == 5, 'A2 HE del sueldo, 14 h en un día: 9 dobles + 5 triples = 2,750.00', fmt(l))
_, _, v = caso(3, [('P1', 0, 'HE-S', 6), ('P1', 1, 'HE-S', 8)]); l = lineas(v, 'P1')
ok(len(l) == 1 and l[0]['sug'] == 2750.00 and l[0]['det']['horas_dobles'] == 9 and l[0]['det']['horas_triples'] == 5,
   'A3 Umbral semanal acumulado entre días: lunes 6 + martes 8 = 9 dobles + 5 triples = 2,750.00', fmt(l) + f" d={l[0]['det'].get('horas_dobles')} t={l[0]['det'].get('horas_triples')}")
_, _, v = caso(4, [('P1', 0, 'HE-S', 6), ('P1', 7, 'HE-S', 8)], dias=14); l = lineas(v, 'P1')
ok(len(l) == 1 and l[0]['sug'] == 2333.33 and l[0]['det']['horas_triples'] == 0, 'A3b El umbral se reinicia cada semana: 6 h y 8 h en semanas distintas = 14 dobles = 2,333.33', fmt(l))
_, _, v = caso(6, [('P1', 0, 'HE-S', 6), ('P1', 1, 'HE-T', 5)])
ls, lt = lineas(v, 'P1', 'HE-S'), lineas(v, 'P1', 'HE-T')
ok(ls[0]['sug'] == 1000.00 and lt[0]['sug'] == 600.00 and lt[0]['det']['horas_dobles'] == 3 and lt[0]['det']['horas_triples'] == 2,
   'A3c El umbral es de la persona en la semana: 6 h HE-S (1,000.00) + 5 h HE-T → 3 dobles + 2 triples (600.00)', f'{fmt(ls)} | {fmt(lt)}')
_, _, v = caso(7, [('P1', 0, 'HE-T', 1)]); l = lineas(v, 'P1')
ok(len(l) == 1 and l[0]['sug'] == 100.00, 'A4 HE tarifa $50, 1 h: 1 × 50 × 2 = 100.00', fmt(l))
_, _, v = caso(8, [('P1', 0, 'HE-T', 14)]); l = lineas(v, 'P1'); A5 = l
ok(len(l) == 1 and l[0]['sug'] == 1650.00 and l[0]['det']['valor_hora'] == 50 and l[0]['det']['origen_valor'] == 'tarifa', 'A5 HE tarifa $50, 14 h: 9 × 50 × 2 + 5 × 50 × 3 = 1,650.00', fmt(l))
ok(l[0]['rp'] == RP['P1-IMSS'] and l[0]['origen'] == 'aceptado' and l[0]['det'].get('asignacion') == 'unico', 'B1 Un solo esquema vigente: se asigna automáticamente (IMSS)', f"{l[0]['rp'] == RP['P1-IMSS']} {l[0]['origen']} {l[0]['det'].get('asignacion')}")
_, _, v = caso(9, [('P1', 0, 'HS-T', 1)]); l1 = lineas(v, 'P1')
_, _, v = caso(10, [('P1', 0, 'HS-T', 14)]); l2 = lineas(v, 'P1')
ok(l1[0]['sug'] == 50.00 and l2[0]['sug'] == 700.00 and 'horas_dobles' not in l2[0]['det'], 'A6 Horas sencillas tarifa: 1 h = 50.00 y 14 h = 700.00 (sin dobles ni triples)', f'{fmt(l1)} | {fmt(l2)}')
_, _, v = caso(11, [('P1', 0, 'HS-S', 2)]); l = lineas(v, 'P1')
ok(l[0]['sug'] == 166.67 and l[0]['det']['regla'] == 'horas_sueldo', 'A7 Horas sencillas del sueldo: 2 × 83.33 = 166.67 (antes 2 × 666.67)', fmt(l))
_, _, v = caso(12, [('P2', 0, 'HE-S', 2)]); l = lineas(v, 'P2')
ok(fmt(l) == 'bruto:400.0:pendiente; neto:50.0:pendiente', 'A8 Dos esquemas: IMSS bruto 2 × 100 × 2 = 400.00 y EFECTIVO neto 2 × 12.50 × 2 = 50.00, separadas', fmt(l))
_, _, v = caso(13, [('PB', 0, 'B-HE-T', 14)], emp=EB, coord='coordB'); l = lineas(v, 'PB')
ok(len(l) == 1 and l[0]['sug'] == 1680.00 and l[0]['det']['horas_triples'] == 0, 'A9 Empresa B sin triples (umbral vacío), tarifa $60, 14 h: 14 × 60 × 2 = 1,680.00', fmt(l))
_, _, v = caso(14, [('P1', 0, 'HE-T', 14)]); l = lineas(v, 'P1')
ok(l[0]['sug'] == 1650.00, 'A10 La configuración de la Empresa B no altera la Empresa A: 1,650.00', fmt(l))
_, _, v = caso(15, [('P3', 0, 'HE-S', 2)]); l = lineas(v, 'P3')
ok(len(l) == 1 and l[0]['origen'] == 'sin_sueldo' and 'Sin esquema' in l[0]['det'].get('motivo', ''), 'A11 Esquema sin enlazar a la relación: «Sin sueldo» con motivo (como B2)', fmt(l))

print('== B Esquema de pago ==')
PER16, H16, V16 = caso(16, [('P2', 0, 'HE-T', 2), ('P5', 0, 'HE-TE', 2), ('P1', 0, 'HE-TE', 2), ('P4', 0, 'HE-T', 2)])
b2 = lineas(V16, 'P2')
ok(len(b2) == 1 and b2[0]['sug'] == 200.00 and b2[0]['origen'] == 'por_asignar' and b2[0]['rp'] is None and b2[0]['mod'] is None and 'Nómina elige' in b2[0]['det'].get('motivo', ''),
   'B2 Dos esquemas sin preferido: 200.00 calculado, «por asignar», sin esquema ni modalidad', fmt(b2) + ' ' + b2[0]['det'].get('motivo', ''))
b6 = lineas(V16, 'P5')
ok(b6[0]['rp'] == RP['P5-EFE'] and b6[0]['mod'] == 'neto' and b6[0]['det'].get('asignacion') == 'preferido', 'B6 Preferido EFECTIVO y tiene exactamente uno vigente: se asigna EFECTIVO', fmt(b6))
b7 = lineas(V16, 'P1')
ok(b7[0]['origen'] == 'por_asignar' and b7[0]['rp'] is None and 'clasificación preferida' in b7[0]['det'].get('motivo', ''), 'B7 Preferido EFECTIVO y no lo tiene: por asignar (no se usa IMSS por suposición)', fmt(b7))
b8 = lineas(V16, 'P4')
ok(b8[0]['origen'] == 'por_asignar' and 'no tiene esquemas' in b8[0]['det'].get('motivo', ''), 'B8 Sin esquemas: por asignar con aviso', b8[0]['det'].get('motivo', ''))
_, _, v = caso(20, [('P6', 1, 'HE-TE', 2)]); l = lineas(v, 'P6')
ok(l[0]['origen'] == 'por_asignar', 'B7b Preferido EFECTIVO que aún no está vigente ese día (inicia el jueves): por asignar', fmt(l))
_, _, v = caso(21, [('P6', 1, 'HE-TE', 2)]); l = lineas(v, 'P6')
ok(l[0]['rp'] == RP['P6-EFE'], 'B7b … y la semana siguiente, ya vigente, se asigna EFECTIVO', fmt(l))
ok(sorted(val(f"select string_agg(registro_pago_id::text, ',') from public.inc_esquemas_asignables('{V16}') where linea_id='{b2[0]['id']}'", 'nomina').split(',')) == sorted([RP['P2-IMSS'], RP['P2-EFE']]),
   'C3 Opciones para asignar: solo los esquemas vigentes de esa persona (no el vencido)')
b2id = b2[0]['id']
falla_con(f"select public.inc_asignar_esquema('{b2id}','{RP['P5-EFE']}')", 'nomina', 'no es de esta persona', 'B4 Rechaza un esquema de otra persona')
falla_con(f"select public.inc_asignar_esquema('{b2id}','{RP['P2-VIEJO']}')", 'nomina', 'no está vigente', 'B4 Rechaza un esquema no vigente en esas fechas')
falla_con(f"select public.inc_asignar_esquema('{b2id}','{RP['PB-IMSS']}')", 'nomina', 'no es de esta persona', 'B4 Rechaza un esquema de otra empresa')
falla_con(f"select public.inc_decidir_importe('{b2id}', null)", 'nomina', 'asigna primero el esquema', 'B2 Una línea por asignar no se acepta sin esquema')
val(f"select public.inc_asignar_esquema('{b2id}','{RP['P2-EFE']}')", 'nomina')
l = lineas(V16, 'P2')
ok(l[0]['rp'] == RP['P2-EFE'] and l[0]['mod'] == 'neto' and l[0]['origen'] == 'pendiente' and l[0]['asig'] == U['nomina'], 'B3 Nómina asigna EFECTIVO: neto, por decidir, con quién asignó', fmt(l))
ok(val(f"select tipo||':'||coalesce(esquema_anterior::text,'-')||':'||esquema_nuevo||':'||(nombre is not null) from public.inc_importes_ajustes where importe_id='{b2id}'", 'nomina') == f"esquema:-:{RP['P2-EFE']}:true", 'B3 La asignación queda en la bitácora')
val(f"select public.inc_capturar_sueldo_manual('{PER16}','{P['P4']}',300)", 'nomina')
l = lineas(V16, 'P2')
ok(len(l) == 1 and l[0]['rp'] == RP['P2-EFE'] and l[0]['origen'] == 'pendiente', 'B5 Recalcular conserva la asignación manual (sigue EFECTIVO)', fmt(l))
val(f"select public.inc_decidir_importe('{b2id}', null)", 'nomina')
val(f"select public.inc_capturar_sueldo_manual('{PER16}','{P['P4']}',310)", 'nomina')
ok(lineas(V16, 'P2')[0]['origen'] == 'aceptado', 'B5 … y si Nómina ya la aceptó, sigue aceptada después de recalcular')
f = val(f"select string_agg(detalle, ' | ') from public.inc_faltantes_procesar('{PER16}')", 'nomina')
ok('PERSONA P1 · Horas extra efectivo: esquema de pago por asignar — hoja de PERSONA CA' in f, 'B9 El detalle dice persona, concepto y hoja', f[:180])
falla_con(f"select public.inc_marcar_procesado('{PER16}')", 'nomina', 'esquema de pago por asignar', 'B9 No se procesa con líneas por asignar')
# B5b: el esquema asignado deja de ser válido -> vuelve a por asignar
val(f"update public.personal_registros_pago set fecha_fin = '{fecha(15, 6)}', activo = false where id = '{RP['P2-EFE']}'", replica=True)
val(f"select public.inc_capturar_sueldo_manual('{PER16}','{P['P4']}',320)", 'nomina')
l = lineas(V16, 'P2')
desc = val(f"select origen from public.inc_importes where id='{b2id}'", 'nomina')
ok(len(l) == 1 and l[0]['rp'] == RP['P2-IMSS'] and l[0]['det'].get('asignacion') == 'unico' and desc == 'descartado',
   'B5b Si el esquema asignado deja de ser vigente ya no se usa: la línea asignada queda descartada y se aplica la regla (aquí IMSS, único vigente)', fmt(l) + ' / ' + desc)
val(f"update public.personal_registros_pago set fecha_fin = null, activo = true where id = '{RP['P2-EFE']}'", replica=True)

print('== C Revisión (servidor): motivo y ajustes ==')
_, H22, V22 = caso(22, [('P1', 0, 'HE-T', 14)])
lid = lineas(V22, 'P1')[0]['id']
falla_con(f"select public.inc_decidir_importe('{lid}', 1600)", 'nomina', 'motivo', 'C4 Modificar sin motivo no se permite')
val(f"select public.inc_decidir_importe('{lid}', 1600, 'Se pagan 13 h, no 14')", 'nomina')
val(f"select public.inc_decidir_importe('{lid}', 1620, 'Ajuste acordado con el coordinador')", 'nomina')
r = val(f"select sugerido||':'||final||':'||origen from public.inc_importes where id='{lid}'", 'nomina')
aj = val(f"select string_agg(anterior||'>'||nuevo||':'||motivo||':'||(usuario_id = '{U['nomina']}'), ' | ' order by creado_en, nuevo) from public.inc_importes_ajustes where importe_id='{lid}'", 'nomina')
ok(r == '1650.00:1620.00:modificado' and aj == '1650.00>1600.00:Se pagan 13 h, no 14:true | 1600.00>1620.00:Ajuste acordado con el coordinador:true',
   'C5 Sugerido intacto (1,650), final 1,620 y dos ajustes con anterior, nuevo, motivo y usuario', f'{r} / {aj}')
out, err = sql(f"update public.inc_importes set final = 1, origen = 'modificado' where id = '{lid}'")
ok('bitácora' in err, 'C5 Ni el dueño de la base cambia un importe sin registro en la bitácora', err.split('\n')[0][:120])

print('== D Histórico y protección ==')
PER23, H23, V23 = caso(23, [('P1', 0, 'HE-T', 14)])
val(f"update public.inc_conceptos set tarifa = 70 where id = '{K['HE-T']}'", 'admin')
val(f"update public.inc_parametros set factor_doble = 2.5 where empresa_id = '{EA}'", 'admin')
val(f"select public.inc_capturar_sueldo_manual('{PER23}','{P['P4']}',300)", 'nomina')
l = lineas(V23, 'P1')
ok(l[0]['sug'] == 1650.00 and l[0]['det']['tarifa'] == 50 and l[0]['det']['factor_doble'] == 2, 'D1 Versión enviada con $50 × 2: al recalcular sigue en 1,650.00', fmt(l))
_, _, v = caso(24, [('P1', 0, 'HE-T', 14)]); l = lineas(v, 'P1')
ok(l[0]['sug'] == 2625.00, 'D2 Periodo nuevo usa $70 y × 2.5: 9 × 70 × 2.5 + 5 × 70 × 3 = 2,625.00', fmt(l))
val(f"update public.inc_conceptos set tarifa = 50 where id = '{K['HE-T']}'", 'admin')
val(f"update public.inc_parametros set factor_doble = 2 where empresa_id = '{EA}'", 'admin')
# D3: procesar el periodo 23 y comprobar que nada lo toca
val(f"select public.inc_aceptar_sugeridos('{V23}')", 'nomina'); val(f"select public.inc_firmar_hoja('{H23}','nomina')", 'nomina')
ok(val(f"select public.inc_marcar_procesado('{PER23}')", 'nomina') == 'Periodo marcado como procesado.', 'D3 Periodo completo: se procesa')
antes = val(f"select string_agg(id::text||sugerido||coalesce(final::text,'')||origen||detalle::text, '|' order by id) from public.inc_importes where version_id='{V23}'", 'nomina')
val(f"update public.personal_registros_pago set sueldo = 99999 where id = '{RP['P1-IMSS']}'", replica=True)
val(f"select public.inc_capturar_sueldo_manual('{PER23}','{P['P1']}',999)", 'nomina')
despues = val(f"select string_agg(id::text||sugerido||coalesce(final::text,'')||origen||detalle::text, '|' order by id) from public.inc_importes where version_id='{V23}'", 'nomina')
ok(antes == despues, 'D3 Procesado: cambiar el sueldo y capturar sueldo manual no altera sus importes')
out, err = sql(f"select public.inc_calcular_version('{V23}')")
ok('ya se procesó' in err, 'D3 El recálculo directo en el servidor (dueño de la base) se rechaza', err.split('\n')[0][:110])
out, err = sql(f"update public.inc_importes set sugerido = 1 where version_id = '{V23}'")
ok('ya se procesó' in err, 'D3 Un UPDATE directo del dueño de la base sobre importes procesados se rechaza', err.split('\n')[0][:110])
out, err = sql(f"insert into public.inc_importes (tenant_id, version_id, personal_id, concepto_id, cantidad, sugerido, origen, usa_sueldo) values ('{T}','{V23}','{P['P2']}','{K['HE-T']}',1,1,'pendiente',false)")
ok('ya se procesó' in err, 'D3 Tampoco se insertan importes en una hoja procesada', err.split('\n')[0][:110])
lid23 = lineas(V23, 'P1')[0]['id']
falla_con(f"select public.inc_decidir_importe('{lid23}', 1, 'x')", 'nomina', 'versión vigente', 'D3 Nómina no decide importes de un periodo procesado')
val(f"update public.personal_registros_pago set sueldo = 20000 where id = '{RP['P1-IMSS']}'", replica=True)
for q, n in [(f"update public.inc_importes_ajustes set motivo = 'x'", 'UPDATE'), (f"delete from public.inc_importes_ajustes", 'DELETE'), ("truncate public.inc_importes_ajustes", 'TRUNCATE')]:
    out, err = sql(q); ok('registro histórico' in err, f'D4 Bitácora: {n} del dueño de la base se rechaza', err.split('\n')[0][:100])
out, err = sql(f"insert into public.inc_importes_ajustes (tenant_id, importe_id, tipo, motivo, usuario_id) values ('{T}','{lid}','importe','falso','{U['nomina']}')", 'nomina')
ok('permission denied' in err, 'D4 Nadie inserta en la bitácora fuera de las funciones', err.split('\n')[0][:100])

print('== E Permisos ==')
val(f"update public.inc_parametros set umbral_triples_semana = null where empresa_id = '{EA}'", 'admin')
ok(val(f"select coalesce(umbral_triples_semana::text,'vacío') from public.inc_parametros where empresa_id='{EA}'", 'admin') == 'vacío', 'E1 El Administrador deja el umbral vacío (sin triples)')
val(f"update public.inc_parametros set umbral_triples_semana = 9 where empresa_id = '{EA}'", 'admin')
val(f"update public.inc_parametros set factor_doble = 5 where empresa_id = '{EA}'", 'nomina')
ok(val(f"select factor_doble from public.inc_parametros where empresa_id='{EA}'", 'nomina') == '2.000', 'E2 Nómina lee la configuración pero no la cambia')
out, err = sql(f"insert into public.inc_conceptos (tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa) values ('{T}','{EA}','X','XX','horas','horas','tarifa',1)", 'nomina')
ok('row-level security' in err, 'E2 Nómina no crea conceptos', err.split('\n')[0][:90])
for r in ('coordA', 'consulta'):
    ok(val("select count(*) from public.inc_importes_ajustes", r) == '0', f'E3 {r}: no ve la bitácora')
    falla_con(f"select public.inc_asignar_esquema('{b2id}','{RP['P2-EFE']}')", r, 'sin permiso', f'E3 {r}: no asigna esquemas')
    falla_con(f"select * from public.inc_esquemas_asignables('{V16}')", r, 'sin permiso', f'E3 {r}: no ve los esquemas asignables')
ok(val("select count(*) from public.inc_importes_ajustes", 'nomina2') == '0', 'E4 Otra organización: no ve la bitácora')
falla_con(f"select public.inc_asignar_esquema('{b2id}','{RP['P2-EFE']}')", 'nomina2', 'no encontrado', 'E4 Otra organización: no asigna esquemas')
falla_con(f"select public.inc_decidir_importe('{lid}', 5, 'x')", 'nomina2', 'no encontrado', 'E4 Otra organización: no modifica importes')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
