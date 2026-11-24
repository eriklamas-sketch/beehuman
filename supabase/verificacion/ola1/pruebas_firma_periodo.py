"""Pruebas de la firma única de Nómina por periodo (opción B, diseño v3.1) en la base LOCAL desechable (puerto 55432).
Datos ficticios. Sustituye a pruebas_b1_2.py. Requiere 20261123000000_b3_concentrado_firma_periodo.sql aplicada.
Cada comprobación del diseño (§7.1) lleva su identificador; los 47 escenarios dan 56 comprobaciones
(P1 = P1a…P1i; I15 + I15b). Las verificaciones de apoyo llevan el prefijo «+».
Uso: DB=bh python3 pruebas_firma_periodo.py"""
import subprocess, json, sys, os, datetime, time, re

DB = os.environ.get('DB', 'bh')
BASE = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
res = []
def sql(q, user=None, replica=False, como_postgres=False):
    """user: corre como ese usuario (rol authenticated, salvo como_postgres=True: claims sin cambiar de rol, para funciones internas)."""
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\n"
        if not como_postgres: pre += "set local role authenticated;\n"
    p = subprocess.run(BASE, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET') and not l.startswith('{"sub"')]
    return '\n'.join(out), err
def val(q, user=None, replica=False, como_postgres=False):
    out, err = sql(q, user, replica, como_postgres)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def error_de(q, user):
    out, err = sql(q, user); return err.split('\n')[0] if err else 'NO FALLÓ'
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T = 'b0000000-0000-4000-8000-000000000001'
U = {k: f'b0100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'nomina2', 'coordA', 'coordB', 'consulta'], 1)}
EA, EB, EC = (f'b0200000-0000-4000-8000-00000000000{i}' for i in (1, 2, 3))
SEM, IM, EF = 'b0300000-0000-4000-8000-000000000001', 'b0400000-0000-4000-8000-000000000001', 'b0400000-0000-4000-8000-000000000002'
PRJ1, PRJ2 = 'b0500000-0000-4000-8000-000000000001', 'b0500000-0000-4000-8000-000000000002'
HE, CAP, BONO = (f'b0600000-0000-4000-8000-00000000000{i}' for i in (1, 2, 3))
NOM = ['CA', 'CB', 'X', 'Y', 'X2', 'S', 'Z', 'Z3', 'Q', 'B1', 'C1', 'C2']
P = {k: f'b0700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOM, 1)}
RL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
EMP = {k: EA for k in NOM}; EMP.update({'B1': EB, 'C1': EC, 'C2': EC})
COORD = {'X': 'CA', 'Y': 'CA', 'X2': 'CA', 'S': 'CA'}
L = datetime.date.fromisoformat(val("select (date_trunc('week', public.hoy_mx() + 7))::date"))
dd = lambda n, k=0: (L + datetime.timedelta(days=7 * n + k)).isoformat()

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT FIRMA B');
insert into auth.users (id, email) select v, k||'.fb@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A FB'),('{EB}','{T}','EMPRESA B FB'),('{EC}','{T}','EMPRESA C FB');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS'),('{EF}','{T}','EFECTIVO');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ1}','OBRA 1 FB','{T}'),('{PRJ2}','OBRA 2 FB','{T}');
"""
for k in NOM:
    co = f"'{P[COORD[k]]}'" if k in COORD else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id) values "
             f"('{P[k]}','{T}','{EMP[k]}','PERSONA {k} FB','FB-{k}',{co},'{PRJ1}');\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values "
             f"('{RL[k]}','{T}','{P[k]}','{EMP[k]}','2025-01-01','vigente','N-{k}');\n")
RP = {}
for k, cl, su, mod in [('X', IM, 3500, 'bruto'), ('Y', IM, 2800, 'bruto'), ('X2', IM, 2800, 'bruto'), ('X2', EF, 700, 'neto'),
                       ('CA', IM, 7000, 'bruto'), ('CB', IM, 7000, 'bruto'), ('Z', IM, 2100, 'bruto'), ('Z3', IM, 2100, 'bruto'), ('Q', IM, 2100, 'bruto')]:
    rid = f"b0800000-0000-4000-8000-{len(RP):012d}"; RP[f'{k}-{mod}'] = rid
    seed += (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
             f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{rid}','{T}','{P[k]}','{RL[k]}','{EMP[k]}','{cl}','{SEM}',{su},'{mod}',7,'2025-01-01',true);\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),
 ('{U['nomina']}','{T}','nomina',null),('{U['nomina2']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),
 ('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values
 ('{EA}','{T}','2025-01-01','{U['nomina']}','{U['admin']}'),('{EB}','{T}','2025-01-01',null,null),('{EC}','{T}','2025-01-01','{U['nomina']}',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'FB' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{CAP}','{T}','{EA}','Capacitación','CAP','horas','otro','sin_importe',null,null,2),
 ('{BONO}','{T}','{EA}','Bono','BON','importe','otro','tarifa',1,null,3);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)

def credito(datos):
    c = val(f"select public.cred_guardar(null, {lit(datos)}, null)", 'nomina')
    if val(f"select estado from public.cred_creditos where id='{c}'") != 'activo':
        val(f"select public.cred_cambiar_estado('{c}','activo','{dd(0)}','Alta FB')", 'nomina')
    return c
CR_X = credito({'personal_id': P['X'], 'tipo': 'prestamo', 'referencia': 'PR-X', 'relacion_laboral_id': RL['X'], 'fecha_inicio': dd(0), 'periodicidad_id': SEM, 'importe_periodo': 300, 'monto_total': 100000})
CR_INF = credito({'personal_id': P['Y'], 'tipo': 'infonavit', 'referencia': 'INF-Y', 'relacion_laboral_id': RL['Y'], 'fecha_inicio': '2025-01-01', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 900})
CR_PEN = credito({'personal_id': P['Y'], 'tipo': 'pension', 'referencia': 'PEN-Y', 'relacion_laboral_id': RL['Y'], 'fecha_inicio': '2025-01-01', 'pension_forma': 'porcentaje', 'pension_valor': 30, 'pension_beneficiario': 'BENEFICIARIA FB'})
CR_C1 = credito({'personal_id': P['C1'], 'tipo': 'prestamo', 'referencia': 'PR-C1', 'relacion_laboral_id': RL['C1'], 'fecha_inicio': dd(0), 'periodicidad_id': SEM, 'importe_periodo': 200, 'monto_total': 100000})

# ---------------- utilidades ----------------
semana = [0]
def nueva_semana(): semana[0] += 1; return semana[0]
def periodo(emp=EA, n=None):
    n = nueva_semana() if n is None else n
    return val(f"select public.inc_crear_periodo('{emp}','{SEM}','{dd(n)}','{dd(n, 6)}')", 'nomina'), n
def estado(per): return json.loads(val(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))
def huella(per): return estado(per)['huella_actual']
def firmar(per, h=None, user='nomina'):
    h = huella(per)['total'] if h is None else h
    return val(f"select public.inc_firmar_periodo('{per}', '{h}')", user)
def falt(per): return val(f"select coalesce(string_agg(detalle, ' | ' order by detalle), 'ninguno') from public.inc_faltantes_procesar('{per}')", 'nomina')
def bloq(per): return val(f"select coalesce(string_agg(detalle, ' | ' order by detalle), 'ninguno') from public.inc_faltantes_bloqueantes('{per}')", 'nomina', como_postgres=True)
def conc(per): return json.loads(val(f"select public.inc_concentrado_periodo('{per}')", 'nomina'))
def canon(per): return json.loads(val(f"select public.inc__concentrado_base('{per}')->'canonico'", 'nomina', como_postgres=True))
def sync_aceptar(per): val(f"select public.cred_descuentos_periodo('{per}')", 'nomina'); val(f"select public.cred_aceptar_descuentos('{per}')", 'nomina')
def armar(capturas=True, enviar=True, aceptar=True, descuentos=True, firma=True, extra_cant=()):
    """Periodo base en la empresa A: hoja de CA con X (F el lunes, 2 h extra, 4 h de capacitación) y Y (V el jueves)."""
    per, n = periodo()
    H = val(f"select public.inc_abrir_hoja('{per}')", 'coordA')
    if capturas:
        val(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H}','{P['X']}','{dd(n)}','F'),('{H}','{P['Y']}','{dd(n,3)}','V');
                insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values
                  ('{H}','{P['X']}','{dd(n,1)}','{HE}',2),('{H}','{P['X']}','{dd(n,2)}','{CAP}',4)
                  {''.join(f",('{H}','{P[p]}','{dd(n,k)}','{c}',{q})" for p, k, c, q in extra_cant)};
                insert into public.inc_observaciones (hoja_id, personal_id, texto) values ('{H}','{P['X']}','Observación FB')""", 'coordA')
    V = None
    if enviar:
        V = val(f"select public.inc_enviar_hoja('{H}')", 'coordA')
        if aceptar: val(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
    if descuentos: sync_aceptar(per)
    if firma: assert firmar(per) == 'Firma de Nómina del periodo registrada.', falt(per)
    return per, n, H, V
def secciones(per): e = estado(per); return e['estado'], e['secciones_cambiadas']
def caso_invalida(cid, desc, per, esperadas):
    est, sec = secciones(per)
    ok(est == 'invalidada' and sec == esperadas, f'{cid} {desc} → invalida; secciones exactamente {esperadas}', f'{est} {sec}')
def caso_no_invalida(cid, desc, per):
    est, sec = secciones(per)
    ok(est == 'vigente' and sec == [], f'{cid} {desc} → NO invalida', f'{est} {sec}')
def reenviar(per, H, cambio_sql=None):
    val(f"select public.inc_devolver_hoja('{H}','Revisión FB','nomina')", 'nomina')
    if cambio_sql: val(cambio_sql, 'coordA')
    V = val(f"select public.inc_enviar_hoja('{H}')", 'coordA')
    val(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
    return V
def linea_he(V): return val(f"select id from public.inc_importes where version_id='{V}' and concepto_id='{HE}' and origen <> 'descartado'")

# ======================================================================
print('== F · Reglas de firma ==')
PB, _ = periodo(EB)
ok('Designa al responsable de Nómina' in falt(PB) and 'solo el responsable designado' in error_de(f"select public.inc_firmar_periodo('{PB}','x')", 'nomina'),
   'F1 Sin responsable de Nómina: faltante «Designa al responsable» y nadie firma', falt(PB))
per2, *_ = armar(firma=False)
f = falt(per2)
ok(f.count('Falta la firma de Nómina del periodo') == 1 and estado(per2)['estado'] == 'sin_firma', 'F2 Con responsable y sin firma: «Falta la firma de Nómina del periodo»', f)
f4 = falt(per2)
ok('Falta la firma de Nómina del periodo' in f4 and 'falta la firma de RH (versión 1)' in f4 and 'falta la firma de Nómina (versión' not in f4,
   'F4 Con hojas enviadas: firma de Nómina del periodo y de RH por hoja; ya no la de Nómina por hoja', f4)
per3, n3, H3, V3 = armar()
f = falt(per3); c3 = conc(per3)
listo = None
if 'firma de Nómina del periodo' not in f and 'falta la firma de RH' in f and c3['estado'] == 'preliminar':
    val(f"select public.inc_firmar_hoja('{H3}','rh')", 'admin'); listo = conc(per3)['estado']
ok(listo == 'listo' and estado(per3)['estado'] == 'vigente', 'F3 Firma sin pendientes: vigente; RH pendiente deja «preliminar» y al firmar RH queda «listo»', f'{f} → {listo}')
PC, _ = periodo(EC)
f5a = falt(PC); sync_aceptar(PC); f5b = falt(PC); r = firmar(PC); f5c = falt(PC)
ok('Falta la firma de Nómina del periodo' in f5b and r == 'Firma de Nómina del periodo registrada.' and f5c == 'ninguno'
   and val(f"select public.inc_marcar_procesado('{PC}')", 'nomina') == 'Periodo marcado como procesado.',
   'F5 Solo descuentos: pide la firma del periodo; con ella se procesa', f'{f5b} → {f5c}')
per6, *_ = armar(firma=False)
h6 = huella(per6)['total']
rech = {u: error_de(f"select public.inc_firmar_periodo('{per6}','{h6}')", u) for u in ('coordA', 'consulta', 'admin', 'nomina2')}
anon = subprocess.run(BASE, input=f"begin; set local role anon; select public.inc_firmar_periodo('{per6}','{h6}'); commit;", capture_output=True, text=True).stderr
hoja6 = val(f"select id from public.inc_hojas where periodo_id='{per6}'")
porhoja = error_de(f"select public.inc_firmar_hoja('{hoja6}','nomina')", 'nomina')
ok(all('solo el responsable designado' in v for v in rech.values()) and 'permission denied' in anon and 'firma el periodo completo' in porhoja
   and val(f"select count(*) from public.inc_eventos where periodo_id='{per6}' and tipo='firma_nomina'") == '0',
   'F6 Solo firma el responsable: Coordinador, Consulta, Administrador, otro Nómina, anon y la firma por hoja se rechazan', json.dumps({**rech, 'hoja': porhoja})[:180])

print('== Conservación de la cobertura de pruebas_b1_2 (20-nov) ==')
ok('Designa al responsable de Nómina' in error_de(f"select public.inc_marcar_procesado('{PB}')", 'nomina'), '+CONS1 Sin responsable de Nómina: no se procesa')
val(f"update public.inc_parametros set responsable_rh_user = '{U['admin']}' where empresa_id = '{EC}'", 'admin')
PC2, _ = periodo(EC); sync_aceptar(PC2)
f_c = falt(PC2)
ok(f_c == 'Falta la firma de Nómina del periodo', '+CONS2 Periodo sin hojas con RH designado: falta solo la firma de Nómina (RH no firma el periodo; con el descuento aceptado no falta nada más)', f_c)
e_c = error_de(f"select public.inc_marcar_procesado('{PC2}')", 'nomina')
mov = val(f"select count(*) from public.cred_movimientos where periodo_id = '{PC2}'")
ok('Falta la firma de Nómina del periodo' in e_c and mov == '0' and val(f"select procesado_en is null from public.inc_periodos where id='{PC2}'") == 't',
   '+CONS3 Sin firma: no se procesa y el saldo no baja (sin movimientos)', f'{e_c[:70]} · movimientos {mov}')
firmar(PC2)
ev = val(f"select (hoja_id is null and version_id is null and huella ? 'total' and huella ? 'secciones' and (huella->>'v')::int = 1)::text from public.inc_eventos where periodo_id='{PC2}' and tipo='firma_nomina'")
ok(ev == 'true' and falt(PC2) == 'ninguno', '+CONS4 El evento de firma del periodo no lleva hoja ni versión y guarda la huella (v1, total y secciones); ya no falta nada', ev)
internas = ['inc__concentrado_base(uuid)', 'inc__huella_de(jsonb)', 'inc_concentrado_huella(uuid)', 'inc__faltantes_base(uuid)',
            'inc_faltantes_bloqueantes(uuid)', 'inc__faltantes_con_firma(uuid,jsonb)']
expuestas = [f for f in internas if val(f"select has_function_privilege('authenticated', 'public.{f}', 'execute') or has_function_privilege('anon', 'public.{f}', 'execute')") == 't']
neg = error_de(f"select public.inc__concentrado_base('{PC2}')", 'nomina')
ok(not expuestas and 'permission denied' in neg, '+CONS5 Las 6 funciones internas no se exponen a usuarios ni a anon', f'{expuestas} · {neg[:60]}')

print('== P · Pendientes que bloquean ==')
def p1(cid, desc, per, texto):
    b = bloq(per); e = error_de(f"select public.inc_firmar_periodo('{per}','{huella(per)['total']}')", 'nomina')
    ok(texto in b and 'no se puede firmar el periodo' in e and texto in e, f'{cid} {desc}: bloquea la firma y se lista', b[:150])
perA, nA, HA, _ = armar(enviar=False, descuentos=True, firma=False)
p1('P1a', 'B1 hoja sin enviar (borrador)', perA, 'no ha enviado su hoja')
perB, nB, HBb, _ = armar(firma=False)
val(f"select public.inc_devolver_hoja('{HBb}','Corrige','nomina')", 'nomina')
p1('P1b', 'B2 hoja devuelta sin reenviar', perB, 'devuelta y no la ha reenviado')
perC, nC, HC, _ = armar(firma=False)
val(f"select public.inc_abrir_hoja('{perC}','{HC}')", 'coordA')
p1('P1c', 'B3 complemento sin enviar', perC, 'tiene un complemento sin enviar')
perD, *_ = armar(aceptar=False, firma=False)
p1('P1d', 'B4 importe por decidir', perD, 'importe por decidir')
perE, nE, HE_, VE = armar(firma=False, extra_cant=[('X2', 4, BONO, 150)])
p1('P1e', 'B5 esquema de pago por asignar', perE, 'esquema de pago por asignar')
perF, *_ = armar(descuentos=False, firma=False)
val(f"select public.cred_descuentos_periodo('{perF}')", 'nomina')
p1('P1f', 'B6 descuento por decidir', perF, 'descuento por decidir')
perG, *_ = armar(descuentos=False, firma=False)
p1('P1g', 'B7 descuento sin revisar (sin sincronizar)', perG, 'descuento del periodo sin revisar')
b8 = bloq(PB)
ok('Designa al responsable de Nómina' in b8 and 'solo el responsable designado' in error_de(f"select public.inc_firmar_periodo('{PB}','{huella(PB)['total']}')", 'nomina'),
   'P1h B8 sin responsable de Nómina: está entre los bloqueantes y nadie firma', b8)
perI, nI, HI, VI = armar(firma=False)
fI = falt(perI); rI = firmar(perI)
ok('falta la firma de RH' in fI and rI == 'Firma de Nómina del periodo registrada.' and 'falta la firma de RH' in falt(perI),
   'P1i Solo la firma de RH pendiente: Nómina sí firma y RH sigue como faltante para procesar', falt(perI))
# + Condición adicional encontrada en el código: descuento decidido que excede el saldo (tipo «descuento»).
PCx, _ = periodo(EC)
CR_C2 = credito({'personal_id': P['C2'], 'tipo': 'prestamo', 'referencia': 'PR-C2', 'relacion_laboral_id': RL['C2'], 'fecha_inicio': dd(0), 'periodicidad_id': SEM, 'importe_periodo': 300, 'monto_total': 400})
sync_aceptar(PCx)
# Se simula que otro periodo ya aplicó $200 de este préstamo (saldo 200 < 300 decididos aquí).
dx = val(f"select id from public.cred_descuentos where periodo_id='{PCx}' and credito_id='{CR_C2}'")
val(f"insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo) values ('{T}','{CR_C2}','{PC}','{dx}',200,400,200)", replica=True)
bx = bloq(PCx); ex = error_de(f"select public.inc_firmar_periodo('{PCx}','{huella(PCx)['total']}')", 'nomina')
ok('excede el saldo disponible' in bx and 'excede el saldo disponible' in ex, 'P1j B6b descuento decidido que excede el saldo disponible: bloquea la firma y se lista', bx[:150])
perP, nP, HP, VP = armar()
val(f"select public.inc_firmar_hoja('{HP}','rh')", 'admin')
val(f"select public.inc_marcar_procesado('{perP}')", 'nomina')
ok('ya está procesado' in error_de(f"select public.inc_firmar_periodo('{perP}','{huella(perP)['total']}')", 'nomina'), 'P2 Un periodo procesado no se firma')

print('== I · Cambios que invalidan (sección exacta) ==')
per, n, H, V = armar(); val(f"select public.inc_decidir_importe('{linea_he(V)}', 777, 'Ajuste FB')", 'nomina')
caso_invalida('I1', 'Modificar un importe', per, ['importes'])
PER_I1 = per
# I2: ajustado (diseño §7.1 vs. regla D3): con una línea por asignar la firma está bloqueada, así que la asignación no puede ocurrir
# después de firmar. Se prueba que la huella captura la asignación (sección importes) y que firmar con la huella previa se rechaza.
h0 = huella(perE)
asg = val(f"select a.linea_id || '/' || a.registro_pago_id from public.inc_esquemas_asignables('{VE}') a order by a.clasificacion limit 1", 'nomina')
val(f"select public.inc_asignar_esquema('{asg.split('/')[0]}','{asg.split('/')[1]}')", 'nomina')
h1 = huella(perE)
cambio = [s for s in h0['secciones'] if h0['secciones'][s] != h1['secciones'][s]]
val(f"select public.inc_aceptar_sugeridos('{VE}')", 'nomina')
pend = val(f"select coalesce(string_agg(id::text, ','), '') from public.inc_importes where version_id='{VE}' and origen in ('pendiente','por_asignar','sin_sueldo')")
for x in [x for x in pend.split(',') if x]: val(f"select public.inc_decidir_importe('{x}', 150, 'Bono FB')", 'nomina')
e2 = error_de(f"select public.inc_firmar_periodo('{perE}','{h0['total']}')", 'nomina')
ok(cambio == ['importes'] and 'cambió mientras lo revisabas' in e2, 'I2 Asignar un esquema cambia la huella en «importes»; firmar con la huella previa se rechaza', f'{cambio} / {e2[:80]}')
per, n, H, V = armar(firma=False, extra_cant=[('S', 3, HE, 1)])
val(f"select public.inc_capturar_sueldo_manual('{per}','{P['S']}',300)", 'nomina'); val(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
firmar(per); val(f"select public.inc_capturar_sueldo_manual('{per}','{P['S']}',350)", 'nomina')
caso_invalida('I3', 'Capturar otro sueldo manual (recalcula)', per, ['importes'])
per, *_ = armar(); d = val(f"select id from public.cred_descuentos where periodo_id='{per}' and credito_id='{CR_X}'")
val(f"select public.cred_decidir_descuento('{d}', 250, 'Ajuste FB')", 'nomina')
caso_invalida('I4', 'Cambiar un descuento con hojas enviadas', per, ['descuentos'])
per, n, H, V = armar()
val(f"insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, hasta, origen, nota) values ('{T}','{P['Q']}','{P['CB']}','{dd(n)}','{dd(n,6)}','carga_inicial','FB I5')", replica=True)
HB5 = val(f"select public.inc_abrir_hoja('{per}')", 'coordB'); val(f"select public.inc_enviar_hoja('{HB5}')", 'coordB')
caso_invalida('I5', 'Se envía la hoja de otro coordinador (sin capturas)', per, ['hojas'])
per, n, H, V = armar()
HC6 = val(f"select public.inc_abrir_hoja('{per}','{H}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HC6}','{P['X']}','{dd(n,4)}','{CAP}',1)", 'coordA')
val(f"select public.inc_enviar_hoja('{HC6}')", 'coordA')
caso_invalida('I6', 'Se envía un complemento antes de procesar (1 h de capacitación)', per, ['hojas', 'cantidades'])
per, n, H, V = armar()
reenviar(per, H, f"update public.inc_observaciones set texto = 'Otra observación FB' where hoja_id = '{H}'")
caso_invalida('I7', 'Devolución y reenvío (solo cambia una observación, excluida)', per, ['hojas'])
per, n, H, V = armar()
W = 'b0700000-0000-4000-8000-000000000099'
val(f"""insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id) values ('{W}','{T}','{EA}','PERSONA W FB','FB-W');
        insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values ('{W[:-3]}999','{T}','{W}','{EA}','{dd(n,2)}','vigente','N-W');
        insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, origen) values ('{T}','{W}','{W[:-3]}999','ingreso','{dd(n,2)}','pantalla')""", replica=True)
caso_invalida('I8', 'Alta con fecha dentro del periodo', per, ['personas', 'movimientos'])
per, n, H, V = armar()
val(f"""update public.relaciones_laborales set estado='baja', fecha_baja='{dd(n,3)}', causa_baja='2' where id='{RL['Z']}';
        insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, causa, origen) values ('{T}','{P['Z']}','{RL['Z']}','baja','{dd(n,3)}','2','pantalla')""", replica=True)
caso_invalida('I9', 'Baja con fecha dentro del periodo', per, ['personas', 'movimientos'])
per, n, H, V = armar()
val(f"""insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, origen) values ('{T}','{P['Y']}','{RL['Y']}','modificacion_salario','{dd(n,4)}','pantalla');
        update public.personal_registros_pago set sueldo = 2900 where id = '{RP['Y-bruto']}'""", replica=True)
caso_invalida('I10', 'Modificación salarial dentro del periodo', per, ['esquemas', 'movimientos'])
per, *_ = armar()
val(f"update public.personal_registros_pago set sueldo = 3000 where id = '{RP['Y-bruto']}'", replica=True)
caso_invalida('I11', 'Cambio del esquema vigente (sin recalcular importes)', per, ['esquemas'])
per, n, H, V = armar()
val(f"update public.relaciones_laborales set fecha_ingreso = '{dd(n,3)}' where id = '{RL['Z3']}'", replica=True)
caso_invalida('I12', 'Corrección retroactiva del ingreso que cambia los días', per, ['personas'])
per, *_ = armar()
val(f"update public.relaciones_laborales set numero_interno = 'N-X-NUEVO' where id = '{RL['X']}'", replica=True)
caso_invalida('I13', 'Cambio del número interno', per, ['personas'])
per, n, H, V = armar()
reenviar(per, H, f"update public.inc_celdas set codigo = 'I' where hoja_id = '{H}' and personal_id = '{P['X']}' and fecha = '{dd(n)}'")
caso_invalida('I14', 'Código de día, directo (F → I y reenvío)', per, ['hojas', 'dias'])
per, n, H, V = armar()
reenviar(per, H, f"update public.inc_cantidades set cantidad = 5 where hoja_id = '{H}' and concepto_id = '{CAP}'")
caso_invalida('I15', 'Cantidad sin importe, directa (capacitación 4 → 5 h)', per, ['hojas', 'cantidades'])
per, n, H, V = armar()
reenviar(per, H, f"update public.inc_cantidades set cantidad = 3 where hoja_id = '{H}' and concepto_id = '{HE}'")
caso_invalida('I15b', 'Cantidad con importe (horas extra 2 → 3)', per, ['hojas', 'cantidades', 'importes'])
per, *_ = armar(); val(f"select public.cred_guardar('{CR_INF}', {lit({'infonavit_valor': 950})}, 'Aviso FB')", 'nomina')
caso_invalida('I16', 'INFONAVIT: cambio de valor (900 → 950)', per, ['informativos'])
per, *_ = armar(); val(f"select public.cred_guardar('{CR_PEN}', {lit({'pension_valor': 25})}, 'Oficio FB')", 'nomina')
caso_invalida('I17', 'Pensión porcentual: 30 → 25', per, ['informativos'])
per, *_ = armar()
credito({'personal_id': P['Q'], 'tipo': 'infonavit', 'referencia': 'INF-Q', 'relacion_laboral_id': RL['Q'], 'fecha_inicio': '2025-01-01', 'infonavit_tipo': 'porcentaje', 'infonavit_valor': 20})
caso_invalida('I18', 'Alta de un crédito INFONAVIT vigente para otra persona', per, ['informativos'])

print('== N · Cambios que NO invalidan ==')
per, n, *_ = armar()
val(f"insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, origen) values ('{T}','{P['Y']}','{RL['Y']}','modificacion_salario','{dd(n+20)}','pantalla')", replica=True)
caso_no_invalida('N1', 'Evento con fecha posterior al periodo', per)
per, *_ = armar(); val(f"update public.personal set nombre_completo = 'PERSONA X CORREGIDA FB', empleado_id = 'FB-X-2' where id = '{P['X']}'", replica=True)
caso_no_invalida('N2', 'Corrección de nombre y número BEH', per)
per, *_ = armar(); val(f"update public.personal set proyecto_id = '{PRJ2}' where id = '{P['X']}'", replica=True)
caso_no_invalida('N3', 'Cambio del proyecto de la ficha', per)
per, n, H, V = armar(); val(f"select public.inc_firmar_hoja('{H}','rh')", 'admin')
caso_no_invalida('N4', 'RH firma después de Nómina', per)
# N5 (definición aprobada 23-nov): volver a decidir el MISMO monto en una línea ya modificada, con otro motivo.
per, n, H, V = armar(firma=False); lh = linea_he(V)
val(f"select public.inc_decidir_importe('{lh}', 555, 'Primer ajuste FB')", 'nomina'); firmar(per)
antes = val(f"select origen || '/' || final from public.inc_importes where id='{lh}'")
val(f"select public.inc_decidir_importe('{lh}', 555, 'Otro motivo, misma cifra FB')", 'nomina')
despues = val(f"select origen || '/' || final from public.inc_importes where id='{lh}'")
est, sec = secciones(per)
ok(antes == despues == 'modificado/555.00' and est == 'vigente' and sec == [],
   'N5 Volver a decidir el mismo monto en una línea ya modificada, con otro motivo → NO invalida', f'{antes} → {despues} · {est} {sec}')
per, *_ = armar(); val(f"update public.relaciones_laborales set fecha_ingreso = '2024-06-01' where id = '{RL['X']}'", replica=True)
caso_no_invalida('N6', 'Ingreso corregido fuera del periodo (mismos días)', per)
per, n, H, V = armar(); reenviar(per, H); PER_N7 = per
caso_invalida('N7', 'Reenvío sin ningún cambio: solo «hojas» (la huella no depende de los ids de línea)', per, ['hojas'])
per, *_ = armar(); val(f"select public.cred_guardar('{CR_INF}', {lit({'referencia': 'INF-Y-2'})}, 'Folio FB')", 'nomina')
caso_no_invalida('N8', 'Cambio de la referencia (folio) del INFONAVIT', per)

print('== Identidad de las líneas de importe (sin colisiones) ==')
tot = val(f"""select count(*) || '/' || count(distinct (i.personal_id, h.id, i.concepto_id, coalesce(i.relacion_laboral_id::text,''), coalesce(i.registro_pago_id::text,'')))
              from public.inc_importes i join public.inc_versiones v on v.id = i.version_id join public.inc_hojas h on h.id = v.hoja_id and v.numero = h.version_actual
             where i.tenant_id = '{T}' and i.origen <> 'descartado'""")
ok(tot.split('/')[0] == tot.split('/')[1], '+ID1 Ninguna colisión: cada línea vigente tiene una identidad lógica única', tot)
def lineas_vigentes(per):
    return int(val(f"""select count(*) from public.inc_importes i join public.inc_versiones v on v.id=i.version_id
        join public.inc_hojas h on h.id=v.hoja_id and v.numero=h.version_actual
        where h.periodo_id='{per}' and i.origen not in ('descartado','sin_importe') and not h.posterior_procesamiento"""))
def claves(c_): return {(x['personal_id'], x['hoja_id'], x['concepto_id'], x['relacion_laboral_id'], x['registro_pago_id']) for x in c_['importes']}
c_ = canon(PER_N7)
ok(len(c_['importes']) == lineas_vigentes(PER_N7) == len(claves(c_)) and len(c_['importes']) > 0,
   '+ID2 Periodo con reenvío: la huella toma solo la versión vigente y conserva todas sus líneas (ninguna se colapsa)', f'{len(c_["importes"])} / {lineas_vigentes(PER_N7)} / {len(claves(c_))}')
idx = val("select pg_get_indexdef('public.inc_importes_linea_uq'::regclass)")
ok('UNIQUE' in idx and 'COALESCE(relacion_laboral_id' in idx and 'COALESCE(registro_pago_id' in idx and 'version_id, personal_id, concepto_id' in idx,
   '+ID3 La llave única real es (versión, persona, concepto, COALESCE(relación), COALESCE(esquema)): un NULL cuenta como un valor', idx[-150:])
# ID4–ID6: la base, sin disparadores (session_replication_role = replica), decide sola qué combinaciones con NULL admite.
perU, nU, HU, VU = armar(firma=False, extra_cant=[('X2', 4, BONO, 150)])     # X2: dos esquemas → línea «por asignar» (esquema NULL)
nulo = val(f"select id || '|' || coalesce(relacion_laboral_id::text,'NULL') || '|' || coalesce(registro_pago_id::text,'NULL') from public.inc_importes where version_id='{VU}' and personal_id='{P['X2']}' and concepto_id='{BONO}'")
lid, rel_, rp_ = nulo.split('|')
dup = lambda rel, rp: sql(f"""insert into public.inc_importes (tenant_id, version_id, personal_id, concepto_id, cantidad, origen, usa_sueldo, relacion_laboral_id, registro_pago_id)
                             values ('{T}','{VU}','{P['X2']}','{BONO}',150,'pendiente',false,{rel},{rp})""", replica=True)[1]
e4 = dup(f"'{rel_}'" if rel_ != 'NULL' else 'null', 'null')
ok(rp_ == 'NULL' and 'inc_importes_linea_uq' in e4, '+ID4 Esquema NULL: otra línea igual (misma relación, esquema NULL) la rechaza la base', f'esquema={rp_} · {e4[:90]}')
e6 = dup('null', 'null'); e6b = dup('null', 'null')
ok(e6 == '' and 'inc_importes_linea_uq' in e6b, '+ID6 Relación y esquema NULL a la vez: se admite una sola línea; la segunda la rechaza la base', f'1ª: {e6 or "aceptada"} · 2ª: {e6b[:70]}')
otra_rel = 'b0700000-0000-4000-8000-000000000998'
val(f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values ('{otra_rel}','{T}','{P['X2']}','{EA}','2025-01-01','anulada','NX2A')", replica=True)
e5 = dup(f"'{otra_rel}'", 'null')
cU = canon(perU)
lin_x2 = [x for x in cU['importes'] if x['personal_id'] == P['X2'] and x['concepto_id'] == BONO]
ok(e5 == '' and len(lin_x2) == 3 and len(claves(cU)) == len(cU['importes']) == lineas_vigentes(perU),
   '+ID5 Esquema NULL con relaciones distintas: la base las admite y la huella las conserva como 3 líneas distintas (no colapsan)', f'{e5 or "aceptada"} · {len(lin_x2)} líneas X2/BONO')
cero = val("select count(*) from public.personal_registros_pago where id = '00000000-0000-0000-0000-000000000000'") + '/' + val("select count(*) from public.relaciones_laborales where id = '00000000-0000-0000-0000-000000000000'")
ok(cero == '0/0' and 'gen_random_uuid' in val("select column_default from information_schema.columns where table_name='personal_registros_pago' and column_name='id'") + val("select column_default from information_schema.columns where table_name='relaciones_laborales' and column_name='id'"),
   '+ID7 El valor que usa COALESCE (uuid cero) no existe como esquema ni relación real: un NULL no puede chocar con un id real', cero)

print('== H · Determinismo e instantánea ==')
per, *_ = armar()
a, b = huella(per), huella(per)
ok(a == b and len(a['total']) == 64, 'H1 Dos cálculos seguidos dan la misma huella (SHA-256)', a['total'][:16])
subprocess.run(BASE, input="vacuum full public.inc_importes; vacuum full public.cred_descuentos; vacuum full public.relaciones_laborales; vacuum full public.personal_registros_pago;", capture_output=True, text=True)
val(f"update public.personal set nombre_completo = nombre_completo where tenant_id = '{T}'; update public.relaciones_laborales set numero_interno = numero_interno where tenant_id = '{T}'", replica=True)
ok(huella(per) == a, 'H2 Reescritura física (VACUUM FULL y actualizaciones sin cambio) no cambia la huella')
txt = val(f"select (public.inc__concentrado_base('{per}')->'canonico')::text", 'nomina', como_postgres=True)
ok(re.search(r'\d\.\d*0[,}\]]', txt) is None and '"cantidad": 2,' in txt and val("select trim_scale(250.00)::text || '|' || trim_scale(250::numeric)::text") == '250|250',
   'H3 Números normalizados: 2.00 → 2 y 250.00 = 250; ningún decimal con ceros al final en el documento')
def concurrente(cuerpo_a, cuerpo_b, retraso=1.0):
    a = subprocess.Popen(BASE, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    a.stdin.write(cuerpo_a); a.stdin.close()
    time.sleep(retraso)
    b = subprocess.run(BASE, input=cuerpo_b, capture_output=True, text=True)
    sa = a.stdout.read(); ea = a.stderr.read(); a.wait()
    return sa, ea, b.stdout, b.stderr
claims = f"select set_config('request.jwt.claims', '{json.dumps({'sub': U['nomina']})}', false);"
per4, n4, *_ = armar()
for vol in ('stable', 'volatile'):
    cuerpo_a = f"""{claims}
create function pg_temp.dos_huellas(p uuid) returns jsonb language plpgsql {vol} as $f$
declare h1 jsonb; h2 jsonb; begin
  h1 := public.inc_concentrado_huella(p); perform pg_sleep(3); h2 := public.inc_concentrado_huella(p);
  return jsonb_build_array(h1->>'total', h2->>'total'); end $f$;
select pg_temp.dos_huellas('{per4}');"""
    nuevo = 3100 if vol == 'stable' else 3200
    cuerpo_b = f"begin; set local session_replication_role = replica; update public.personal_registros_pago set sueldo = {nuevo} where id = '{RP['Y-bruto']}'; commit;"
    sa, ea, sb_, eb = concurrente(cuerpo_a, cuerpo_b)
    par = json.loads([l for l in sa.splitlines() if l.startswith('[')][-1]) if '[' in sa else None
    despues = huella(per4)['total']
    if vol == 'stable':
        ok(par and par[0] == par[1] and despues != par[0] and not eb.strip(),
           'H4 Instantánea: dentro de una consulta STABLE las dos huellas son iguales aunque otra sesión confirme un cambio a mitad', f'{par} → después {despues[:12]} {ea[:80]}')
    else:
        ok(par and par[0] != par[1], 'H5 Control: con VOLATILE las dos huellas difieren (el cambio sí entró a mitad del cálculo)', str(par))

print('== K · Concurrencia ==')
per, nK, HK, VK = armar(firma=False)
h = huella(per)['total']
e = error_de(f"select public.inc_firmar_periodo('{per}','{'0' * 64}')", 'nomina')
ok('cambió mientras lo revisabas' in e, 'K1 Huella revisada distinta de la actual: se rechaza', e[:90])
firmar(per, h); val(f"select public.inc_decidir_importe('{linea_he(VK)}', 123, 'Carrera FB')", 'nomina')
e_k2 = estado(per)
ok(e_k2['estado'] == 'invalidada' and val(f"select count(*) from public.inc_eventos where periodo_id='{per}' and tipo='firma_nomina'") == '1',
   'K2 Cambio confirmado después de firmar: la firma queda invalidada, sin error y conservada en el historial', e_k2['estado'])
per, *_ = armar(firma=False)
h = huella(per)['total']
cuerpo = f"begin; {claims} set local role authenticated; select public.inc_firmar_periodo('{per}','{h}'); select pg_sleep(2); commit;"
cuerpo_b = f"begin; {claims} set local role authenticated; select public.inc_firmar_periodo('{per}','{h}'); commit;"
sa, ea, sb_, eb = concurrente(cuerpo, cuerpo_b, 0.5)
ok('registrada' in sa and 'ya tiene la firma de Nómina vigente' in sb_ and val(f"select count(*) from public.inc_eventos where periodo_id='{per}' and tipo='firma_nomina'") == '1',
   'K3 Dos firmas simultáneas: se serializan y queda una sola firma vigente', f'A={sa.strip()[-45:]} B={sb_.strip()[-45:]} {ea[:60]}{eb[:60]}')
per, n, H, V = armar()
val(f"select public.inc_firmar_hoja('{H}','rh')", 'admin')
hf = val(f"select huella->>'total' from public.inc_eventos where periodo_id='{per}' and tipo='firma_nomina'")
cuerpo = f"begin; {claims} set local role authenticated; select public.inc_marcar_procesado('{per}'); select pg_sleep(3); commit;"
cuerpo_b = f"begin; set local session_replication_role = replica; update public.personal_registros_pago set sueldo = sueldo + 1 where id = '{RP['Y-bruto']}'; commit;"
sa, ea, sb_, eb = concurrente(cuerpo, cuerpo_b, 1.0)
hp = val(f"select huella->>'total' from public.inc_eventos where periodo_id='{per}' and tipo='procesado'")
av = conc(per)['avisos']['cambio_posterior_procesado']
ok('procesado' in sa and hp == hf and av and av['secciones'] == ['esquemas'],
   'K4 Procesar con un cambio concurrente: se guarda la huella validada (= la firmada) y aparece el aviso «cambió después (esquemas)»', f'{hp == hf} {av} {ea[:60]}')

print('== R · Refirma, procesado y aviso posterior ==')
r1 = firmar(PER_I1)
hist = val(f"select count(*) from public.inc_eventos where periodo_id='{PER_I1}' and tipo='firma_nomina' and hoja_id is null")
ok(r1 == 'Firma de Nómina del periodo registrada.' and estado(PER_I1)['estado'] == 'vigente' and hist == '2', 'R1 Volver a firmar tras invalidar: vigente; quedan las 2 firmas en el historial', hist)
per, n, H, V = armar(); val(f"select public.inc_firmar_hoja('{H}','rh')", 'admin')
val(f"select public.inc_decidir_importe('{linea_he(V)}', 111, 'Ajuste FB')", 'nomina')
e = error_de(f"select public.inc_marcar_procesado('{per}')", 'nomina')
ok('ya no es vigente' in e and 'cambió: importes' in e, 'R2 Procesar con la firma invalidada se rechaza y dice qué cambió', e[:150])
per, n, H, V = armar(); val(f"select public.inc_firmar_hoja('{H}','rh')", 'admin')
val(f"select public.inc_marcar_procesado('{per}')", 'nomina'); val(f"select public.cred_descuentos_periodo('{per}')", 'nomina')
r0 = conc(per)['avisos']['cambio_posterior_procesado']
ok(r0 is None, '+R0 Justo después de procesar (y de volver a abrir descuentos) no hay aviso', str(r0))
val(f"update public.relaciones_laborales set fecha_ingreso = '{dd(n,2)}' where id = '{RL['Q']}'", replica=True)
c = conc(per)
ok(c['estado'] == 'procesado' and c['avisos']['cambio_posterior_procesado'] and c['avisos']['cambio_posterior_procesado']['secciones'] == ['personas'],
   'R3 Corrección de historia laboral después de procesar: sigue procesado y avisa «cambió después de procesarse (personas)»', str(c['avisos']['cambio_posterior_procesado']))

print('== D6 · Firma antigua de Nómina por hoja ==')
per, n, H, V = armar(firma=False)
val(f"insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre) values ('{T}','{H}','{per}','{V}','firma_nomina','{U['nomina']}','firma antigua por hoja')", replica=True)
ok(estado(per)['estado'] == 'sin_firma' and 'Falta la firma de Nómina del periodo' in falt(per), 'D6 Una firma antigua de Nómina por hoja queda como historial y no autoriza el periodo')

total = len(res); malas = [r for r in res if not r[1]]
ids = [r[0].split()[0] for r in res if not r[0].startswith('+')]
print(f'\nComprobaciones del diseño: {len(ids)} ({len(set(ids))} distintas); de apoyo: {total - len(ids)}')
print(f'RESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd_ in malas: print('  FALLA:', nn, dd_)
sys.exit(1 if malas else 0)
