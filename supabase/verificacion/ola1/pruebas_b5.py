"""Pruebas de base de B5 (créditos y descuentos) en la base LOCAL desechable (puerto 55432)
con Ola 1 + fase 1 + B2 + B1 + B1.1 + B1.1a + B1.1b + B5. Datos ficticios.
Diseño: claude/B5-creditos-descuentos-diseno-tecnico-13nov.md, con las precisiones de Erik (13-nov 13:42).
Uso: DB=bh python3 pruebas_b5.py"""
import subprocess, json, sys, os

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
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T, T2 = '5a000000-0000-4000-8000-000000000001', '5a000000-0000-4000-8000-000000000002'
U = {k: f'5b000000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coord', 'consulta', 'nomina2'], 1)}
EA, EB, EX = '5c000000-0000-4000-8000-000000000001', '5c000000-0000-4000-8000-000000000002', '5c000000-0000-4000-8000-000000000003'
SEM, QUI, SEM2 = '5e000000-0000-4000-8000-000000000007', '5e000000-0000-4000-8000-000000000015', '5e000000-0000-4000-8000-000000000099'
CL = '5f000000-0000-4000-8000-000000000001'
P = {k: f'5a100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['CO', 'PF', 'PP', 'PD', 'PI', 'PS', 'PB', 'PN', 'PN2', 'PX'], 1)}
RL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
RL['PD_B'] = '5a100000-0000-4000-8000-000000000990'
RL['PB_BAJA'] = RL['PB']
lunes = val("select (date_trunc('week', public.hoy_mx() + 7))::date")
import datetime
L = datetime.date.fromisoformat(lunes)
sem = lambda n: ((L + datetime.timedelta(days=7 * n)).isoformat(), (L + datetime.timedelta(days=7 * n + 6)).isoformat())

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B5'),('{T2}','OTRO TENANT B5');
insert into auth.users (id, email) select v, k||'.b5@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A B5'),('{EB}','{T}','EMPRESA B B5'),('{EX}','{T2}','EMPRESA OTRA B5');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7),('{QUI}','{T}','QUINCENAL',15),('{SEM2}','{T2}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL}','{T}','EFECTIVO');
"""
for k in P:
    emp = EB if k == 'PX' else EA
    fon = "'FON-123'" if k == 'PN' else ("'FON-456'" if k == 'PN2' else 'null')
    seed += f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, no_fonacot) values ('{P[k]}','{T}','{emp}','PERSONA {k}','B5-{k}',{fon});\n"
    if k not in ('CO', 'PN2'):
        baja = f"'baja', '{(L - datetime.timedelta(days=1)).isoformat()}'" if k == 'PB' else "'vigente', null"
        seed += f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, fecha_baja) values ('{RL[k]}','{T}','{P[k]}','{emp}','2025-01-01',{baja});\n"
seed += f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values ('{RL['PD_B']}','{T}','{P['PD']}','{EB}','2025-01-01','vigente');\n"
seed += f"""insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coord']}','{T}','coordinador','{P['CO']}'),('{U['consulta']}','{T}','consulta',null),('{U['nomina2']}','{T2}','nomina',null);
insert into public.inc_parametros (empresa_id, tenant_id) values ('{EA}','{T}'),('{EB}','{T}');
update public.inc_parametros set inicio_historial = '2025-01-01' where empresa_id in ('{EA}','{T}','{EB}');
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
# Conversión de no_fonacot: se ejecuta la parte 8 de la migración sobre estas personas (la base ya tenía B5).
mig = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pendiente', '20261113000000_b5_creditos_descuentos.sql')).read()
conv = mig[mig.index('with origen as ('):mig.rindex('commit;')]
val(conv.replace("from public.personal p where coalesce(trim(p.no_fonacot), '') <> ''",
                 f"from public.personal p where coalesce(trim(p.no_fonacot), '') <> '' and p.tenant_id = '{T}'").rstrip().rstrip(';'))

def guardar(datos, user='nomina', cid=None, motivo=None):
    return val(f"select public.cred_guardar({('null' if cid is None else repr(cid))}, {lit(datos)}, {('null' if motivo is None else repr(motivo))})", user)
def periodo(n, emp=EA, per=SEM, dias=7):
    ini = (L + datetime.timedelta(days=7 * n)).isoformat(); fin = (L + datetime.timedelta(days=7 * n + dias - 1)).isoformat()
    return val(f"select public.inc_crear_periodo('{emp}','{per}','{ini}','{fin}')", 'nomina')
def panel(per, user='nomina'):
    return json.loads(val(f"select public.cred_descuentos_periodo('{per}')", user))
def linea(pn, cred):
    return next((l for l in pn['lineas'] if l['credito_id'] == cred and l['origen'] != 'descartado'), None)
def saldo(cred): return float(val(f"select public.cred_saldo_actual('{cred}')"))
ini0 = L.isoformat()

print('== R Registro ==')
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PF'], 'tipo': 'fonacot', 'referencia': 'F-1', 'relacion_laboral_id': RL['PF'], 'fecha_inicio': ini0})})", 'nomina', 'retención de la cédula', 'R1 FONACOT sin retención por periodo: se rechaza (sin prorrateo)')
CF = guardar({'personal_id': P['PF'], 'tipo': 'fonacot', 'referencia': 'F-1', 'relacion_laboral_id': RL['PF'], 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 300})
CP = guardar({'personal_id': P['PP'], 'tipo': 'prestamo', 'referencia': 'PR-1', 'relacion_laboral_id': RL['PP'], 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 1500, 'monto_total': 10000})
CD = guardar({'personal_id': P['PD'], 'tipo': 'otro', 'concepto': 'Caja de ahorro', 'relacion_laboral_id': RL['PD'], 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 200})
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PI'], 'tipo': 'infonavit', 'referencia': 'INF-9', 'relacion_laboral_id': RL['PI'], 'fecha_inicio': ini0})})", 'nomina', 'tipo de descuento y valor', 'R1 INFONAVIT sin tipo de descuento ni valor: se rechaza')
CI = guardar({'personal_id': P['PI'], 'tipo': 'infonavit', 'referencia': 'INF-9', 'relacion_laboral_id': RL['PI'], 'fecha_inicio': ini0, 'infonavit_tipo': 'porcentaje', 'infonavit_valor': 20, 'infonavit_fecha_aviso': ini0})
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PI'], 'tipo': 'infonavit', 'referencia': 'INF-8', 'relacion_laboral_id': RL['PI'], 'fecha_inicio': ini0, 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 900, 'importe_periodo': 225, 'periodicidad_id': SEM})})", 'nomina', 'no genera descuento', 'R1 INFONAVIT no admite importe por periodo (el cálculo es B6)')
CPP = guardar({'personal_id': P['PI'], 'tipo': 'pension', 'referencia': 'OF-77', 'relacion_laboral_id': RL['PI'], 'fecha_inicio': ini0, 'pension_forma': 'porcentaje', 'pension_valor': 20, 'pension_beneficiario': 'BENEFICIARIA FICTICIA'})
CPF = guardar({'personal_id': P['PS'], 'tipo': 'pension', 'referencia': 'OF-78', 'relacion_laboral_id': RL['PS'], 'fecha_inicio': ini0, 'pension_forma': 'fijo', 'importe_periodo': 400, 'periodicidad_id': SEM})
CS = guardar({'personal_id': P['PS'], 'tipo': 'prestamo', 'referencia': 'PR-2', 'relacion_laboral_id': RL['PS'], 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 1500, 'monto_total': 2000})
CB = guardar({'personal_id': P['PB'], 'tipo': 'anticipo', 'referencia': 'AN-1', 'relacion_laboral_id': RL['PB'], 'fecha_inicio': '2025-06-01', 'periodicidad_id': SEM, 'importe_periodo': 100, 'monto_total': 500})
ok(val(f"select string_agg(tipo||':'||public.cred_es_calculable(c)::text, ',' order by tipo, referencia) from public.cred_creditos c where tenant_id='{T}' and origen='captura'") ==
   'anticipo:true,fonacot:true,infonavit:false,otro:true,pension:false,pension:true,prestamo:true,prestamo:true',
   'R1 Calculables: FONACOT, préstamo, anticipo, otro y pensión fija; informativos: INFONAVIT y pensión porcentual')
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PF'], 'tipo': 'otro', 'concepto': 'X', 'relacion_laboral_id': RL['PP'], 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 10})})", 'nomina', 'no es de esta persona', 'R2 Relación de otra persona: se rechaza')
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PF'], 'tipo': 'otro', 'concepto': 'X', 'fecha_inicio': ini0, 'periodicidad_id': SEM, 'importe_periodo': 10})})", 'nomina', 'relación laboral', 'R2 Sin relación laboral (y no incompleto): se rechaza')
falla_con(f"select public.cred_guardar(null, {lit({'personal_id': P['PF'], 'tipo': 'otro', 'concepto': 'X', 'relacion_laboral_id': RL['PF'], 'fecha_inicio': ini0, 'periodicidad_id': SEM2, 'importe_periodo': 10})})", 'nomina', 'fuera de tu organización', 'R2 Periodicidad de otra organización: se rechaza')
falla_con(f"select public.cred_guardar('{CF}', {lit({'importe_periodo': 350})})", 'nomina', 'motivo', 'R3 Editar sin motivo: se rechaza')
guardar({'importe_periodo': 350}, cid=CF, motivo='Nueva cédula FONACOT')
guardar({'importe_periodo': 300}, cid=CF, motivo='Corrección de captura')
h = val(f"select string_agg(evento||':'||coalesce(antes->>'importe_periodo','-')||'>'||coalesce(despues->>'importe_periodo','-')||':'||coalesce(motivo,''), ' | ' order by creado_en) from public.cred_historia where credito_id='{CF}'", 'nomina')
ok(h == 'alta:->300.00: | cambio:300.00>350.00:Nueva cédula FONACOT | cambio:350.00>300.00:Corrección de captura', 'R3 La historia guarda alta y cambios con antes, después y motivo', h)
for q, n in [("update public.cred_historia set motivo = 'x'", 'UPDATE'), ("delete from public.cred_historia where true", 'DELETE'), ("truncate public.cred_historia", 'TRUNCATE')]:
    out, err = sql(q); ok('registro histórico' in err, f'R3 Historia: {n} del dueño de la base se rechaza', err.split('\n')[0][:90])
out, err = sql(f"delete from public.cred_creditos where id = '{CF}'"); ok('registro histórico' in err, 'R3 Un crédito no se borra (se termina)', err.split('\n')[0][:90])

print('== P Propuesta por periodo ==')
W0 = periodo(0)
pn = panel(W0)
lf = linea(pn, CF)
ok(lf and lf['sugerido'] == 300 and lf['origen'] == 'pendiente', 'P1 FONACOT $300 semanal en periodo semanal de su empresa: 1 línea de $300 por decidir', str(lf and (lf['sugerido'], lf['origen'])))
ok(linea(pn, CP)['sugerido'] == 1500 and linea(pn, CPF)['sugerido'] == 400, 'P1 Préstamo $1,500 y pensión fija $400 por decidir')
Q = periodo(6, per=QUI, dias=14)
pq = panel(Q)
ok(not [l for l in pq['lineas'] if l['origen'] != 'descartado'] and any('periodicidad' in a['aviso'] for a in pq['avisos']), 'P2 Periodo quincenal de la misma empresa: no se propone (periodicidad distinta) y hay aviso', str(len(pq['lineas'])))
WB = periodo(0, emp=EB)
pb = panel(WB)
ok(not [l for l in pb['lineas'] if l['origen'] != 'descartado'], 'P2/P3 Periodo de la empresa B: ningún crédito ligado a la empresa A se propone ahí', str([l['tipo'] for l in pb['lineas']]))
ok(linea(pn, CD) and val(f"select count(*) from public.cred_descuentos where credito_id = '{CD}' and origen <> 'descartado'") == '1',
   'P3 Persona con relaciones en A y B, crédito ligado a A: una sola línea, solo en A (C1, C2)')
panel(W0); panel(W0)
ok(val(f"select count(*) from public.cred_descuentos where periodo_id = '{W0}'") == val(f"select count(distinct credito_id) from public.cred_descuentos where periodo_id = '{W0}'"),
   'P4 Sincronizar varias veces no duplica: una línea por crédito y periodo')
out, err = sql(f"insert into public.cred_descuentos (tenant_id, periodo_id, credito_id, personal_id, sugerido) values ('{T}','{W0}','{CF}','{P['PF']}',1)")
ok('duplicate key' in err or 'unique' in err.lower(), 'P4 Ni el dueño de la base inserta un segundo descuento del mismo crédito y periodo', err.split('\n')[0][:90])
ok(not linea(pn, CI) and not linea(pn, CPP) and {i['tipo'] for i in pn['informativos']} >= {'infonavit', 'pension'},
   'P5 INFONAVIT y pensión del 20 %: 0 líneas; aparecen como informativos (C3)', str([(i['tipo'], i['referencia']) for i in pn['informativos']]))
ok(not linea(pn, CB) and any(a['referencia'] == 'AN-1' and 'terminó' in a['aviso'] for a in pn['avisos']), 'P6 Relación dada de baja antes del periodo: no se propone y avisa «relación terminada»', str(pn['avisos'][:2]))
CN = val(f"select id from public.cred_creditos where personal_id = '{P['PN']}'")
CN2 = val(f"select id from public.cred_creditos where personal_id = '{P['PN2']}'")
ok(not linea(pn, CN) and any(i['referencia'] == 'FON-123' and i['estado'] == 'incompleto' for i in pn['informativos']), 'P7 FONACOT incompleto convertido: informativo, sin línea ni pendiente', '')
val(f"select public.cred_cambiar_estado('{CD}', 'suspendido', '{ini0}', 'Suspensión por solicitud')", 'nomina')
pn = panel(W0)
ok(not linea(pn, CD) and val(f"select origen from public.cred_descuentos where credito_id = '{CD}' and periodo_id = '{W0}'") == 'descartado', 'P6 Crédito suspendido: su línea se descarta (no se borra)')
val(f"select public.cred_cambiar_estado('{CD}', 'activo', '{ini0}', 'Reactivación')", 'nomina')
ok(linea(panel(W0), CD)['origen'] == 'pendiente', 'P6 Al reactivarlo vuelve a proponerse por decidir')

print('== N Conversión no_fonacot ==')
r = val(f"select relacion_laboral_id||'|'||estado||'|'||referencia||'|'||origen||'|'||coalesce(importe_periodo::text,'-') from public.cred_creditos where id='{CN}'")
ok(r == f"{RL['PN']}|incompleto|FON-123|conversion_no_fonacot|-", 'N1 Con una sola relación vigente: FONACOT incompleto, ligado, sin importe', r)
r = val(f"select coalesce(relacion_laboral_id::text,'sin relación')||'|'||estado from public.cred_creditos where id='{CN2}'")
ok(r == 'sin relación|incompleto', 'N1 Sin relación vigente: incompleto y sin relación (no se adivina)', r)
ok(val(f"select no_fonacot from public.personal where id='{P['PN']}'") == 'FON-123' and val(f"select evento||':'||(antes->>'personal.no_fonacot') from public.cred_historia where credito_id='{CN}'") == 'conversion:FON-123',
   'N1 El campo original se conserva y la conversión queda en la historia (trazabilidad)')
falla_con(f"select public.cred_cambiar_estado('{CN}', 'activo', '{ini0}', 'Completar')", 'nomina', 'captura', 'N2 Activar el incompleto sin completar sus datos (fecha, retención): se rechaza')
ok(val(f"select estado from public.cred_creditos where id='{CN}'") == 'incompleto', 'N2 … y sigue incompleto')
guardar({'periodicidad_id': SEM, 'importe_periodo': 250, 'fecha_inicio': ini0}, cid=CN, motivo='Datos de la cédula FONACOT')
val(f"select public.cred_cambiar_estado('{CN}', 'activo', '{ini0}', 'Datos completos')", 'nomina')
ok(linea(panel(W0), CN)['sugerido'] == 250, 'N2 Completado y activado por Nómina: ya propone $250')

print('== D Decisiones ==')
lp = linea(panel(W0), CP)['id']
falla_con(f"select public.cred_decidir_descuento('{lp}', 1200)", 'nomina', 'motivo', 'D1 Modificar sin motivo: se rechaza')
val(f"select public.cred_decidir_descuento('{lp}', 1200, 'Acuerdo con el trabajador')", 'nomina')
ok(val(f"select count(*)||':'||max(motivo) from public.cred_descuentos_ajustes where descuento_id='{lp}'", 'nomina') == '1:Acuerdo con el trabajador', 'D1 Modificar con motivo queda en la bitácora')
out, err = sql(f"update public.cred_descuentos set final = 1, origen='modificado' where id = '{lp}'")
ok('bitácora' in err, 'D1 Ni el dueño de la base cambia un descuento sin bitácora', err.split('\n')[0][:90])
falla_con(f"select public.cred_decidir_descuento('{lp}', 20000, 'x')", 'nomina', 'exceder el saldo', 'D1 No se modifica por encima del saldo')
f = val(f"select string_agg(detalle, ' | ') from public.inc_faltantes_procesar('{W0}')", 'nomina')
ok('descuento por decidir' in f and 'FONACOT F-1' in f, 'D2 Faltantes nombran persona, tipo y referencia de los descuentos por decidir', f[:160])
falla_con(f"select public.inc_marcar_procesado('{W0}')", 'nomina', 'descuento por decidir', 'D2 No se procesa con descuentos por decidir')
ok(saldo(CP) == 10000, 'S3 Antes de procesar el saldo no cambia ($10,000)')
n = val(f"select public.cred_aceptar_descuentos('{W0}')", 'nomina')
panel(W0)
ok(linea(panel(W0), CF)['origen'] == 'aceptado', 'D4 Sincronizar después de aceptar con el mismo sugerido: sigue aceptado', f'aceptados={n}')

print('== S Saldo y procesado ==')
W1 = periodo(1)
p1 = panel(W1)
ok(linea(p1, CS)['sugerido'] == 500, 'S5 Préstamo $2,000 con dos periodos abiertos: el segundo propone solo $500 (saldo proyectado)', str(linea(p1, CS)['sugerido']))
# S7: error a mitad del procesado -> nada a medias (se fuerza con un disparador temporal en movimientos)
sql("create function public._b5_falla() returns trigger language plpgsql as $f$ begin raise exception 'falla simulada'; end $f$; create trigger _b5_falla before insert on public.cred_movimientos for each row execute function public._b5_falla()")
falla_con(f"select public.inc_marcar_procesado('{W0}')", 'nomina', 'falla simulada', 'S7 Error a mitad del procesado: se rechaza')
ok(val(f"select coalesce(procesado_en::text,'abierto') from public.inc_periodos where id='{W0}'") == 'abierto' and val(f"select count(*) from public.cred_movimientos where periodo_id='{W0}'") == '0',
   'S7 … y no queda nada a medias: periodo abierto, sin movimientos')
sql("drop trigger _b5_falla on public.cred_movimientos; drop function public._b5_falla()")
ok(val(f"select public.inc_marcar_procesado('{W0}')", 'nomina') == 'Periodo marcado como procesado.', 'S1 Se procesa el periodo con todo decidido')
ok(saldo(CP) == 8800 and val(f"select importe||':'||saldo_anterior||':'||saldo_nuevo from public.cred_movimientos where credito_id='{CP}'") == '1200.00:10000.00:8800.00',
   'S6 El saldo baja por el final modificado ($1,200), no por el sugerido: $10,000 → $8,800', str(saldo(CP)))
ok(saldo(CS) == 500, 'S1 Préstamo de $2,000: tras $1,500 queda $500')
ok(val(f"select count(*) from public.cred_movimientos where credito_id='{CF}'") == '0', 'S1 FONACOT sin monto total: no genera movimientos de saldo')
ok(val(f"select public.inc_marcar_procesado('{W0}')", 'nomina').startswith('Ya estaba procesado'), 'S2 Procesar otra vez: «ya estaba procesado»')
ok(saldo(CP) == 8800 and val(f"select count(*) from public.cred_movimientos where credito_id='{CP}'") == '1', 'S2 … y el saldo solo bajó una vez ($8,800, 1 movimiento)')
out, err = sql(f"insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo) values ('{T}','{CP}','{W0}','{lp}',1200,8800,7600)")
ok('duplicate key' in err or 'unique' in err.lower(), 'S2 Un segundo movimiento del mismo crédito y periodo se rechaza (índice único), aun del dueño de la base', err.split('\n')[0][:90])
for q, n in [(f"update public.cred_movimientos set importe = 1 where credito_id = '{CP}'", 'UPDATE'), (f"delete from public.cred_movimientos where credito_id = '{CP}'", 'DELETE')]:
    out, err = sql(q); ok('registro histórico' in err, f'S2 Movimientos: {n} se rechaza', err.split('\n')[0][:80])
falla_con(f"select public.cred_decidir_descuento('{lp}', null)", 'nomina', 'ya se procesó', 'D3 Periodo procesado: no se decide')
out, err = sql(f"update public.cred_descuentos set sugerido = 1 where periodo_id = '{W0}'")
ok('ya se procesó' in err, 'D3 Periodo procesado: ni el dueño de la base modifica sus descuentos', err.split('\n')[0][:80])
antes = val(f"select string_agg(id::text||origen||coalesce(final::text,''), ',' order by id) from public.cred_descuentos where periodo_id='{W0}'")
panel(W0)
ok(antes == val(f"select string_agg(id::text||origen||coalesce(final::text,''), ',' order by id) from public.cred_descuentos where periodo_id='{W0}'"), 'D3 Periodo procesado: la sincronización no recalcula nada')
# S4 y orden de procesado (precisión 2): W1 propuso $500 para CS; ahora el saldo real es $500
W2 = periodo(3)
p2 = panel(W2)
ok(not linea(p2, CS), 'S5 Con saldo comprometido por completo en un periodo abierto anterior, el siguiente no propone')
p1 = panel(W1)
ls = linea(p1, CS)
ok(ls['sugerido'] == 500, 'S4 Saldo $500 y descuento de $1,500: sugerido $500', str(ls['sugerido']))
val(f"select public.cred_aceptar_descuentos('{W1}')", 'nomina')
ok(val(f"select public.inc_marcar_procesado('{W1}')", 'nomina') == 'Periodo marcado como procesado.', 'S4 Se procesa')
ok(saldo(CS) == 0 and val(f"select estado from public.cred_creditos where id='{CS}'") == 'terminado' and
   val(f"select count(*) from public.cred_historia where credito_id='{CS}' and evento='terminacion_saldo'") == '1',
   'S4 Saldo $0: el préstamo se termina en la misma transacción, con su historia')
ok(not linea(panel(W2), CS), 'S4 Un préstamo terminado no propone en periodos siguientes')
# Saldo disponible = saldo real − lo comprometido en otros periodos abiertos (anteriores: propuesto o
# decidido; posteriores: solo decidido). Revisión de Erik 13-nov 14:03.
def anticipo(ref, semana, importe, monto):
    return guardar({'personal_id': P['PF'], 'tipo': 'anticipo', 'referencia': ref, 'relacion_laboral_id': RL['PF'],
                    'fecha_inicio': sem(semana)[0], 'fecha_fin': sem(semana + 1)[1], 'periodicidad_id': SEM,
                    'importe_periodo': importe, 'monto_total': monto})
def procesar(per):
    val(f"select public.cred_aceptar_descuentos('{per}')", 'nomina')
    return val(f"select public.inc_marcar_procesado('{per}')", 'nomina')
def movs(cred): return val(f"select coalesce(sum(importe),0)||'|'||count(*)||'|'||coalesce(min(saldo_nuevo),0) from public.cred_movimientos where credito_id='{cred}'")

print('== S8 Modificar por encima del saldo proyectado (ejemplo de la revisión) ==')
X1 = anticipo('AN-S8', 4, 1500, 2000)
W4, W5 = periodo(4), periodo(5)
a4, a5 = linea(panel(W4), X1), linea(panel(W5), X1)
ok(a4['sugerido'] == 1500 and a5['sugerido'] == 500, 'S8 Saldo $2,000: periodo A abierto con $1,500 comprometidos; B propone $500', f"{a4['sugerido']} / {a5['sugerido']}")
ok(a5['disponible'] == 500 and a5['saldo'] == 2000, 'S8 La línea de B muestra saldo $2,000 y disponible $500', f"saldo {a5['saldo']} disponible {a5['disponible']}")
falla_con(f"select public.cred_decidir_descuento('{a5['id']}', 900, 'Se adelanta el cobro')", 'nomina', 'saldo disponible', 'S8 Nómina modifica B a $900: se rechaza (disponible $500)')
out, err = sql(f"select public.cred_decidir_descuento('{a5['id']}', 900, 'Se adelanta el cobro')", 'nomina')
ok('$500.00' in err and '$2,000.00' in err and '$1,500.00' in err, 'S8 El mensaje explica: disponible $500 = saldo $2,000 − $1,500 comprometidos', err.split('\n')[0][:160])
ok(val(f"select origen||':'||coalesce(final::text,'-')||':'||(select count(*) from public.cred_descuentos_ajustes where descuento_id='{a5['id']}') from public.cred_descuentos where id='{a5['id']}'") == 'pendiente:-:0',
   'S8 … y nada cambia: B sigue por decidir, sin bitácora')
val(f"select public.cred_decidir_descuento('{a5['id']}', 400, 'Acuerdo con el trabajador')", 'nomina')
ok(linea(panel(W5), X1)['final'] == 400, 'S8 Modificar B por debajo del disponible ($400): se permite')

print('== S9 Procesar primero el periodo anterior ==')
ok(procesar(W4) == 'Periodo marcado como procesado.' and saldo(X1) == 500, 'S9 Se procesa A ($1,500): saldo $500')
b = linea(panel(W5), X1)
ok(b['final'] == 400 and b['origen'] == 'modificado' and b['disponible'] == 500, 'S9 B conserva su decisión ($400) y el disponible es el saldo real ($500)', f"{b['final']} {b['origen']} {b['disponible']}")
falla_con(f"select public.cred_decidir_descuento('{b['id']}', 600, 'x')", 'nomina', 'saldo disponible', 'S9 B no puede subir por encima del saldo real ($600 > $500)')
val(f"select public.cred_decidir_descuento('{b['id']}', 500, 'Liquidar')", 'nomina')
ok(procesar(W5) == 'Periodo marcado como procesado.' and saldo(X1) == 0 and val(f"select estado from public.cred_creditos where id='{X1}'") == 'terminado',
   'S9 Se procesa B ($500): saldo $0 y el anticipo se termina')
ok(movs(X1) == '2000.00|2|0.00', 'S9 Total descontado $2,000 en 2 movimientos; el saldo nunca fue negativo', movs(X1))

print('== S10 Procesar primero el periodo posterior ==')
X2 = anticipo('AN-S10', 8, 1500, 2000)
W8, W9 = periodo(8), periodo(9)
a8, a9 = linea(panel(W8), X2), linea(panel(W9), X2)
ok(a8['sugerido'] == 1500 and a9['sugerido'] == 500, 'S10 Saldo $2,000: A propone $1,500 y B $500', f"{a8['sugerido']} / {a9['sugerido']}")
falla_con(f"select public.cred_decidir_descuento('{a9['id']}', 1500, 'Se adelanta el cobro')", 'nomina', 'saldo disponible', 'S10 B no puede tomar lo que A tiene comprometido ($1,500 > $500)')
ok(procesar(W9) == 'Periodo marcado como procesado.' and saldo(X2) == 1500, 'S10 Se procesa primero B ($500): saldo $1,500')
a8b = linea(panel(W8), X2)
ok(a8b['sugerido'] == 1500 and a8b['disponible'] == 1500 and a8b['id'] == a8['id'],
   'S10 A no necesita ajustarse: su propuesta ($1,500) sigue cabiendo en el saldo real ($1,500)', f"{a8b['sugerido']} disp {a8b['disponible']}")
ok(procesar(W8) == 'Periodo marcado como procesado.' and saldo(X2) == 0 and val(f"select estado from public.cred_creditos where id='{X2}'") == 'terminado',
   'S10 Se procesa A ($1,500): saldo $0 y el anticipo se termina')
ok(movs(X2) == '2000.00|2|0.00', 'S10 Total descontado $2,000; nunca negativo', movs(X2))

print('== S11 Modificar descuentos en ambos periodos ==')
X3 = anticipo('AN-S11', 10, 1000, 2000)
W10, W11 = periodo(10), periodo(11)
a10, a11 = linea(panel(W10), X3), linea(panel(W11), X3)
ok(a10['sugerido'] == 1000 and a11['sugerido'] == 1000, 'S11 Saldo $2,000, $1,000 por periodo: A $1,000 y B $1,000')
val(f"select public.cred_decidir_descuento('{a10['id']}', 1200, 'Acuerdo: más en A')", 'nomina')
b11 = linea(panel(W11), X3)
ok(b11['sugerido'] == 800 and b11['origen'] == 'pendiente', 'S11 A modificado a $1,200: la propuesta de B se recalcula a $800, por decidir', f"{b11['sugerido']} {b11['origen']}")
falla_con(f"select public.cred_decidir_descuento('{a11['id']}', 900, 'x')", 'nomina', 'saldo disponible', 'S11 B a $900 se rechaza (disponible $800)')
val(f"select public.cred_decidir_descuento('{a11['id']}', 700, 'Acuerdo: menos en B')", 'nomina')
falla_con(f"select public.cred_decidir_descuento('{a10['id']}', 1400, 'x')", 'nomina', 'saldo disponible', 'S11 A a $1,400 se rechaza: B ya decidió $700 (disponible de A $1,300)')
val(f"select public.cred_decidir_descuento('{a10['id']}', 1300, 'Ajuste final')", 'nomina')
ok(val(f"select sum(final) from public.cred_descuentos where credito_id='{X3}' and origen <> 'descartado'") == '2000.00', 'S11 Lo decidido en ambos periodos ($1,300 + $700) no excede el saldo ($2,000)')
f11 = val(f"select coalesce(string_agg(detalle, ' | '),'ninguna') from public.inc_faltantes_procesar('{W10}') where detalle like '%AN-S11%'", 'nomina')
ok(f11 == 'ninguna', 'S11 Faltantes: ninguna línea del crédito excede el disponible', f11)
ok(procesar(W11) == 'Periodo marcado como procesado.' and procesar(W10) == 'Periodo marcado como procesado.' and saldo(X3) == 0
   and val(f"select estado from public.cred_creditos where id='{X3}'") == 'terminado', 'S11 Se procesan ambos (en orden inverso): saldo $0 y terminado')
ok(movs(X3) == '2000.00|2|0.00', 'S11 Total descontado $2,000; nunca negativo', movs(X3))

print('== S12 Dos operaciones concurrentes sobre el mismo crédito ==')
import time
X4 = anticipo('AN-S12', 12, 1000, 2000)
W12, W13 = periodo(12), periodo(13)
a12, a13 = linea(panel(W12), X4), linea(panel(W13), X4)
ok(a12['sugerido'] == 1000 and a13['sugerido'] == 1000, 'S12 Saldo $2,000: A $1,000 y B $1,000 (por separado, cada decisión cabe)')
def sesion(q, espera=0):
    claims = json.dumps({'sub': U['nomina']})
    txt = (f"begin;\nselect set_config('request.jwt.claims', '{claims}', true);\nset local role authenticated;\n"
           f"select public.cred_decidir_descuento({q});\nselect pg_sleep({espera});\ncommit;")
    return subprocess.Popen(PSQL, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), txt
p1, t1 = sesion(f"'{a12['id']}', 1500, 'Sesión 1: más en A'", espera=2)
p2, t2 = sesion(f"'{a13['id']}', null")
t0 = time.time(); p1.stdin.write(t1); p1.stdin.close()
time.sleep(0.5)
p2.stdin.write(t2); p2.stdin.close()
e2 = p2.communicate()[1]; dt = time.time() - t0
e1 = p1.communicate()[1]
ok(not e1.strip(), 'S12 Sesión 1 (modifica A a $1,500, retiene la transacción 2 s): confirma sin error', e1.strip()[:100])
ok(dt >= 1.8, 'S12 Sesión 2 (acepta B $1,000) espera el bloqueo del crédito hasta que la sesión 1 confirma', f'{dt:.1f} s')
ok('saldo disponible' in e2 and '$500' in e2, 'S12 … y al continuar ve lo comprometido por la sesión 1: se rechaza (disponible $500)', e2.strip().split('\n')[0][:150])
ok(val(f"select coalesce(sum(final),0) from public.cred_descuentos where credito_id='{X4}' and origen in ('aceptado','modificado')") == '1500.00',
   'S12 Lo decidido nunca excede el saldo: solo $1,500 de A')
b13 = linea(panel(W13), X4)
ok(b13['sugerido'] == 500 and b13['origen'] == 'pendiente', 'S12 B se recalcula a $500, por decidir', f"{b13['sugerido']} {b13['origen']}")
# misma carrera al revés: la sesión que llega segunda es la que modifica A
p1, t1 = sesion(f"'{b13['id']}', null", espera=2)
p2, t2 = sesion(f"'{a12['id']}', 1800, 'Sesión 2: aún más en A'")
t0 = time.time(); p1.stdin.write(t1); p1.stdin.close()
time.sleep(0.5)
p2.stdin.write(t2); p2.stdin.close()
e2 = p2.communicate()[1]; dt = time.time() - t0
e1 = p1.communicate()[1]
ok(not e1.strip() and dt >= 1.8 and 'saldo disponible' in e2 and '$1,500.00' in e2,
   'S12 Al revés: B acepta $500 primero; A a $1,800 espera y se rechaza (disponible $1,500)', f'{dt:.1f} s · ' + e2.strip().split('\n')[0][:110])
ok(val(f"select sum(final) from public.cred_descuentos where credito_id='{X4}' and origen in ('aceptado','modificado')") == '2000.00',
   'S12 Total decidido $2,000 = saldo')

print('== E Permisos ==')
for r in ('coord', 'consulta'):
    cuentas = val("select (select count(*) from public.cred_creditos)||','||(select count(*) from public.cred_historia)||','||(select count(*) from public.cred_descuentos)||','||(select count(*) from public.cred_descuentos_ajustes)||','||(select count(*) from public.cred_movimientos)", r)
    ok(cuentas == '0,0,0,0,0', f'E1 {r}: SELECT directo a las 5 tablas cred_* devuelve 0 filas', cuentas)
    for q in (f"select public.cred_creditos_persona('{P['PP']}')", f"select public.cred_descuentos_periodo('{W4}')", f"select public.cred_guardar(null, {lit({'personal_id': P['PF'], 'tipo': 'otro'})})",
              f"select public.cred_cambiar_estado('{CF}','suspendido','{ini0}','x')", f"select public.cred_decidir_descuento('{lp}', 1, 'x')", f"select public.cred_aceptar_descuentos('{W4}')"):
        out, err = sql(q, r)
        if 'sin permiso' not in err: ok(False, f'E1 {r}: función sin rechazo', q[:60]); break
    else: ok(True, f'E1 {r}: las 6 funciones responden «sin permiso»')
    out, err = sql(f"insert into public.cred_creditos (tenant_id, personal_id, tipo) values ('{T}','{P['PF']}','otro')", r)
    ok('permission denied' in err, f'E1 {r}: no inserta directo', err.split('\n')[0][:70])
for q in ("select public.cred_saldo_actual(null)", f"select public.cred_sincronizar_periodo('{W4}')"):
    out, err = sql(q, 'nomina'); ok('permission denied' in err, 'E1 Funciones internas no expuestas a la aplicación', q[:45])
out, err = sql("select public.cred_disponible(null, null)", 'nomina'); ok('permission denied' in err, 'E1 cred_disponible (interna) no expuesta a la aplicación')
out, err = sql(f"update public.cred_creditos set importe_periodo = 1 where id = '{CF}'", 'nomina')
ok('permission denied' in err, 'E3 Ni Nómina escribe directo en las tablas (solo por funciones)', err.split('\n')[0][:70])
ok(val("select count(*) from public.cred_creditos", 'nomina2') == '0', 'E2 Otra organización: no ve créditos')
falla_con(f"select public.cred_guardar('{CF}', {lit({'importe_periodo': 1})}, 'x')", 'nomina2', 'no encontrado', 'E2 Otra organización: no modifica créditos')
falla_con(f"select public.cred_decidir_descuento('{a4['id']}', 1, 'x')", 'nomina2', 'no encontrado', 'E2 Otra organización: no decide descuentos')
ok(val(f"select jsonb_array_length(public.cred_creditos_persona('{P['PP']}'))", 'admin') == '1', 'E3 Administrador ve los créditos de la persona')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
