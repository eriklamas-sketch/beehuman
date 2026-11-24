"""B6 · Bandeja de envíos para Nómina: pruebas en una base LOCAL desechable (puerto 55432). Datos ficticios.
Arma la base HASTA B3 (sin B6), crea datos «de antes» (periodo procesado con original y complementos, periodo abierto),
aplica la migración B6 y comprueba la carga inicial; después prueba estados, reenvío, devolución, complementos,
firmas y periodos intactos, permisos y aislamiento; al final revierte y reaplica comparando la huella del esquema.
Uso: python3 pruebas_bandeja_envios.py   (usa la base b6ci; la reconstruye)"""
import subprocess, json, sys, os, datetime

R = '/home/claude/beehuman/supabase'
DB = 'b6ci'
MIG = f'{R}/pendiente/20261124000000_b6_bandeja_envios.sql'
REV = f'{R}/reversion/20261124000000_reversion_b6_bandeja_envios.sql'
PSQL = ['psql', '-X', '-q', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
BASE = PSQL[:2] + ['-At', '-v', 'ON_ERROR_STOP=1'] + PSQL[2:]
res = []

r = subprocess.run(['bash', '/home/claude/herramientas_prueba_bh/env/montar.sh', '20261123000000'], env={**os.environ, 'DB': DB}, capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[:500])

def sql(q, user=None, replica=False, como_postgres=False, anon=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\n"
        if not como_postgres: pre += "set local role authenticated;\n"
    if anon: pre += "set local role anon;\n"
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
def error_de(q, user=None, anon=False):
    out, err = sql(q, user, anon=anon); return err.split('\n')[0] if err else 'NO FALLÓ'
def huella_esquema():
    p = subprocess.run(BASE + ['-f', f'{R}/verificacion/huella_esquema.sql'], capture_output=True, text=True)
    return p.stdout.strip()

T, T2 = 'b6000000-0000-4000-8000-000000000001', 'b6000000-0000-4000-8000-000000000002'
U = {k: f'b6100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'nomina2', 'coordA', 'coordB', 'consulta', 'otro'], 1)}
EA, EB = 'b6200000-0000-4000-8000-000000000001', 'b6200000-0000-4000-8000-000000000002'
SEM, IM = 'b6300000-0000-4000-8000-000000000001', 'b6400000-0000-4000-8000-000000000001'
PRJ, HE, HEB = 'b6500000-0000-4000-8000-000000000001', 'b6600000-0000-4000-8000-000000000001', 'b6600000-0000-4000-8000-000000000002'
NOM = ['CA', 'CB', 'X', 'Y', 'Z']
P = {k: f'b6700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOM, 1)}
RL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
EMP = {'CA': EA, 'CB': EB, 'X': EA, 'Y': EA, 'Z': EB}
COORD = {'X': 'CA', 'Y': 'CA', 'Z': 'CB'}
L = datetime.date.fromisoformat(val("select (date_trunc('week', public.hoy_mx() + 7))::date"))
dd = lambda n, k=0: (L + datetime.timedelta(days=7 * n + k)).isoformat()

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B6'),('{T2}','TENANT B6 OTRO');
insert into auth.users (id, email) select v, k||'.b6@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A B6'),('{EB}','{T}','EMPRESA B B6');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ}','OBRA B6','{T}');
"""
for k in NOM:
    co = f"'{P[COORD[k]]}'" if k in COORD else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id) values "
             f"('{P[k]}','{T}','{EMP[k]}','PERSONA {k} B6','B6-{k}',{co},'{PRJ}');\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values "
             f"('{RL[k]}','{T}','{P[k]}','{EMP[k]}','2025-01-01','vigente','N-{k}');\n"
             f"insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
             f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{T}','{P[k]}','{RL[k]}','{EMP[k]}','{IM}','{SEM}',3500,'bruto',7,'2025-01-01',true);\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),
 ('{U['nomina']}','{T}','nomina',null),('{U['nomina2']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),
 ('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null),('{U['otro']}','{T2}','nomina',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values
 ('{EA}','{T}','2025-01-01','{U['nomina']}','{U['admin']}'),('{EB}','{T}','2025-01-01','{U['nomina']}',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'B6' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{HEB}','{T}','{EB}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)

semana = [0]
def periodo(emp=EA):
    semana[0] += 1; n = semana[0]
    return val(f"select public.inc_crear_periodo('{emp}','{SEM}','{dd(n)}','{dd(n, 6)}')", 'nomina'), n
def hoja_enviada(per, n, coord='coordA', persona='X', k=1, horas=2):
    H = val(f"select public.inc_abrir_hoja('{per}')", coord)
    val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H}','{P[persona]}','{dd(n,k)}','{HEB if persona == 'Z' else HE}',{horas})", coord)
    return H, val(f"select public.inc_enviar_hoja('{H}')", coord)
def complemento(per, n, H, k):
    C = val(f"select public.inc_abrir_hoja('{per}','{H}')", 'coordA')
    val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{C}','{P['Y']}','{dd(n,k)}','{HE}',1)", 'coordA')
    return C, val(f"select public.inc_enviar_hoja('{C}')", 'coordA')
def firmar(per): return val(f"select public.inc_firmar_periodo('{per}', '{json.loads(val(f'select public.inc_firma_periodo_estado(%s)' % repr(per), 'nomina'))['huella_actual']['total']}')", 'nomina')
def procesar(per, hojas_v):
    for V in hojas_v: val(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
    val(f"select public.cred_descuentos_periodo('{per}')", 'nomina'); val(f"select public.cred_aceptar_descuentos('{per}')", 'nomina')
    assert firmar(per) == 'Firma de Nómina del periodo registrada.'
    for V in hojas_v:
        h = val(f"select hoja_id from public.inc_versiones where id='{V}'")
        val(f"select public.inc_firmar_hoja('{h}','rh')", 'admin')
    return val(f"select public.inc_marcar_procesado('{per}')", 'nomina')
def evento(V): return val(f"select id from public.inc_eventos where version_id='{V}' and tipo in ('envio','complemento')")

# ======================================================================
print('== A · Datos anteriores a B6 (base hasta B3) ==')
PA, nA = periodo()
HA, VA1 = hoja_enviada(PA, nA)
val(f"select public.inc_devolver_hoja('{HA}','Corrige B6','nomina')", 'nomina')
VA2 = val(f"select public.inc_enviar_hoja('{HA}')", 'coordA')
CApre, VCpre = complemento(PA, nA, HA, 2)                    # complemento enviado ANTES de procesar
print('   procesado PA:', procesar(PA, [VA2, VCpre]))
CApos, VCpos = complemento(PA, nA, HA, 3)                    # complemento POSTERIOR al procesamiento
PO, nO = periodo()
HO, VO = hoja_enviada(PO, nO)                                # periodo abierto con envío pendiente
eventos_antes = val("select count(*) from public.inc_eventos")
F0 = huella_esquema()

p = subprocess.run(BASE + ['-f', MIG], capture_output=True, text=True)
ok(p.returncode == 0, '+A0 La migración B6 se aplica sobre la base hasta B3', (p.stderr or '').strip()[:300])
aviso = [l for l in p.stderr.splitlines() if 'B6:' in l]
F1 = huella_esquema()

def fila(V, user='nomina'):
    ev = evento(V)
    for x in bandeja(user):
        if x['evento_id'] == ev: return x
    return None
def bandeja(user='nomina', emp=None, dias=30):
    out = val(f"select coalesce(jsonb_agg(b), '[]') from public.inc_bandeja_envios({'null' if emp is None else repr(emp)}, {dias}) b", user)
    return json.loads(out)
def pend(user='nomina'): return json.loads(val("select public.inc_envios_pendientes()", user))

def seg(V): return val(f"select coalesce(atencion_tipo,'-')||'|'||coalesce(motivo_atencion,'-')||'|'||coalesce(atendida_por::text,'-')||'|'||coalesce(atendida_por_nombre,'-') from public.inc_envio_seguimiento where evento_id='{evento(V)}'") or 'sin fila'
ok(seg(VA1) == seg(VA2) == 'automatica|Periodo procesado antes de activar B6|-|-',
   'A1 Original de periodo procesado (v1 y v2): atendido automático, motivo «Periodo procesado antes de activar B6», sin usuario', seg(VA2))
ok(fila(VA2)['estado'] == 'atendido' and fila(VA2)['atencion_tipo'] == 'automatica', '+A1b En la bandeja la original aparece como atendida (automática)')
ok(seg(VCpos) == 'sin fila' and fila(VCpos)['estado'] == 'nuevo' and fila(VCpos)['posterior_procesamiento'] is True,
   'A2 Complemento posterior al procesamiento: sin atención automática; aparece como nuevo', fila(VCpos)['estado'])
ok(seg(VCpre) == 'automatica|Periodo procesado antes de activar B6|-|-' and fila(VCpre)['estado'] == 'atendido',
   'A3 Complemento enviado antes de procesar: atendido automático con el mismo motivo, sin usuario', seg(VCpre))
ok(seg(VO) == 'sin fila' and fila(VO)['estado'] == 'nuevo', 'A4 Envío de un periodo abierto: queda nuevo')
ok(aviso and ' 3 envíos' in aviso[0], '+A5 La migración informa cuántos envíos atendió de forma automática', aviso[0] if aviso else 'sin aviso')
ok(val("select count(*) from public.inc_eventos") == eventos_antes, 'A6 La migración no crea ni cambia eventos')

# ======================================================================
print('== E · Estados: nuevo → en revisión → atendido ==')
P1, n1 = periodo()
H1, V1 = hoja_enviada(P1, n1)
f = fila(V1)
ok(f and f['estado'] == 'nuevo' and f['tipo_evento'] == 'envio' and f['version_numero'] == 1 and f['empresa'] == 'EMPRESA A B6'
   and f['coordinador'] == 'PERSONA CA B6' and f['enviado_en'] and f['periodo_inicio'] == dd(n1),
   'E1 Envío nuevo con empresa, periodo, coordinador, tipo, versión y fecha/hora', json.dumps({k: f[k] for k in ('estado', 'tipo_evento', 'version_numero', 'empresa', 'coordinador')}, ensure_ascii=False) if f else 'sin fila')
pe0 = pend()
ok(f['lineas_por_decidir'] > 0, 'E2 Indicador: importes por decidir antes de resolver', str(f['lineas_por_decidir']))
val(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina')
ok(fila(V1)['lineas_por_decidir'] == 0 and fila(V1)['estado'] == 'nuevo', 'E3 Resolver los importes da «Importes resueltos» pero NO cambia el estado (sigue nuevo)')
ev1 = evento(V1)
r_ab = val(f"select public.inc_envio_abrir('{ev1}')", 'nomina')
f = fila(V1)
ok(r_ab == 'en_revision' and f['estado'] == 'en_revision' and f['abierta_por'] and f['atendida_en'] is None,
   'E4 Abrir lo deja «En revisión» y NO lo marca como atendido', f"{r_ab} / atendida_en={f['atendida_en']}")
pe1 = pend()
ok(pe1['total'] == pe0['total'] and pe1['en_revision'] == pe0['en_revision'] + 1 and pe1['nuevos'] == pe0['nuevos'] - 1,
   'E5 El aviso sigue contando el envío abierto (pasa de nuevos a en revisión)', f'{pe0} → {pe1}')
quien = f['abierta_por']; cuando = f['abierta_en']
val(f"select public.inc_envio_abrir('{ev1}')", 'nomina2')
ok(fila(V1)['abierta_por'] == quien and fila(V1)['abierta_en'] == cuando, 'E6 Abrir otra vez (otro usuario) conserva la primera apertura')
r_at = val(f"select public.inc_envio_atender('{ev1}', '  Revisado con el coordinador  ')", 'nomina2')
f = fila(V1)
ok(r_at == 'Envío marcado como atendido.' and f['estado'] == 'atendido' and f['atencion_tipo'] == 'manual'
   and f['atendida_por'] and f['atendida_en'] and f['nota_atencion'] == 'Revisado con el coordinador' and f['abierta_por'] == quien,
   'E7 Atender registra quién, cuándo y la nota (sin espacios sobrantes); la apertura queda', f"{f['atendida_por']} · {f['nota_atencion']}")
ok(val(f"select atendida_por from public.inc_envio_seguimiento where evento_id='{ev1}'") == U['nomina2'], '+E7b La atención queda a nombre de quien la hizo (usuario real)')
ok(pend()['total'] == pe0['total'] - 1, 'E8 Atender descuenta del aviso', str(pend()))
r2 = val(f"select public.inc_envio_atender('{ev1}', 'otra nota')", 'nomina')
ok(r2.startswith('Ya estaba atendido') and fila(V1)['nota_atencion'] == 'Revisado con el coordinador' and fila(V1)['atendida_por'] == f['atendida_por'],
   'E9 Atender dos veces no cambia nada', r2)
P1b, n1b = periodo(EB)
HZ, VZ = hoja_enviada(P1b, n1b, 'coordB', 'Z')
evz = evento(VZ)
val(f"select public.inc_envio_atender('{evz}', '')", 'nomina')
ok(fila(VZ)['estado'] == 'atendido' and fila(VZ)['nota_atencion'] is None and fila(VZ)['abierta_en'] is None,
   'E10 Se puede atender sin abrir; nota vacía queda vacía y la apertura no se inventa')
ok('500 caracteres' in error_de(f"select public.inc_envio_atender('{evento(VO)}', repeat('x', 501))", 'nomina'), 'E11 Nota de más de 500 caracteres se rechaza')
fe = val(f"select id from public.inc_eventos where tipo='procesado' and periodo_id='{PA}'")
ok('no encontrado' in error_de(f"select public.inc_envio_abrir('{fe}')", 'nomina') and 'no encontrado' in error_de(f"select public.inc_envio_atender('{fe}')", 'nomina'),
   'E12 Un evento que no es envío no se abre ni se atiende')

print('== H · El seguimiento no se edita ni se borra ==')
ok('no se modifican' in error_de(f"update public.inc_envio_seguimiento set nota_atencion='x' where evento_id='{ev1}'"), 'H1 Cambiar una atención registrada se rechaza (incluso el dueño de la base)')
ok('no se modifican' in error_de(f"update public.inc_envio_seguimiento set abierta_en=now() where evento_id='{ev1}'"), 'H2 Cambiar la apertura registrada se rechaza')
ok('no se borra' in error_de(f"delete from public.inc_envio_seguimiento where evento_id='{ev1}'"), 'H3 Borrar el seguimiento se rechaza')
ok('solo aplica a envíos' in error_de(f"insert into public.inc_envio_seguimiento (evento_id, tenant_id) values ('{fe}','{T}')"), 'H4 No se puede crear seguimiento de un evento que no es envío')

# ======================================================================
print('== R · Devolución y reenvío ==')
P2, n2 = periodo()
H2, V2a = hoja_enviada(P2, n2)
ev2a = evento(V2a)
val(f"select public.inc_envio_abrir('{ev2a}')", 'nomina')
val(f"select public.inc_devolver_hoja('{H2}','Falta un día','nomina')", 'nomina')
ok(fila(V2a)['estado'] == 'devuelto', 'R1 Envío devuelto: cerrado como «devuelto», en espera de reenvío (no cuenta en el aviso)')
ok('se devolvió' in error_de(f"select public.inc_envio_atender('{ev2a}')", 'nomina'), 'R2 Un envío devuelto no se atiende (no hay nada que atender)')
pe_r = pend()
V2b = val(f"select public.inc_enviar_hoja('{H2}')", 'coordA')
fa, fb = fila(V2a), fila(V2b)
ok(fa['estado'] == 'reemplazado' and fa['version_actual'] == 2 and fa['abierta_por'] and fa['abierta_en'],
   'R3 El reenvío cierra la versión sustituida («reemplazado») y conserva su historial (apertura)', f"{fa['estado']} · abierta por {fa['abierta_por']}")
ok(fb['estado'] == 'nuevo' and fb['version_numero'] == 2 and pend()['total'] == pe_r['total'] + 1,
   'R4 La versión nueva aparece como nuevo envío (v2) y solo ella cuenta en el aviso', f"{pe_r} → {pend()}")
ok(val(f"select count(*) from public.inc_envio_seguimiento where evento_id='{ev2a}'") == '1', '+R5 El seguimiento de la versión 1 sigue registrado')
ok('llegó la versión 2' in error_de(f"select public.inc_envio_atender('{ev2a}')", 'nomina'), 'R6 La versión reemplazada ya no se atiende')
val(f"select public.inc_envio_abrir('{evento(V2b)}')", 'nomina'); val(f"select public.inc_envio_atender('{evento(V2b)}','ok v2')", 'nomina')
val(f"select public.inc_devolver_hoja('{H2}','Otra corrección','nomina')", 'nomina')
ok(fila(V2b)['estado'] == 'atendido', '+R7 Una versión ya atendida conserva su atención aunque después se devuelva')

# ======================================================================
print('== C · Complementos independientes y firmas/periodos intactos ==')
P3, n3 = periodo()
H3, V3 = hoja_enviada(P3, n3)
ev3 = evento(V3)
val(f"select public.inc_envio_abrir('{ev3}')", 'nomina')
print('   procesado P3:', procesar(P3, [V3]))
ok(fila(V3)['estado'] == 'cerrado_procesado', 'C1 Original abierta y luego procesada (ya con B6): se cierra por el procesamiento, sin atribuirlo a nadie',
   fila(V3)['estado'])
ok(val(f"select count(*) from public.inc_envio_seguimiento where evento_id='{ev3}' and atendida_en is not null") == '0', '+C1b El cierre por procesamiento no escribe una atención falsa')
def foto(per):
    e = json.loads(val(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))
    pr = val(f"select coalesce(procesado_en::text,'-')||'|'||coalesce(procesado_por::text,'-') from public.inc_periodos where id='{per}'")
    hj = val(f"select string_agg(id||':'||estado||':'||version_actual, ',' order by id) from public.inc_hojas where periodo_id='{per}'")
    ev = val(f"select count(*)||'|'||max(creado_en) from public.inc_eventos where periodo_id='{per}'")
    hu = val(f"select public.inc_concentrado_huella('{per}')->>'total'", 'nomina', como_postgres=True)
    return {'estado': e['estado'], 'secc': e['secciones_cambiadas'], 'firma': (e.get('firma') or {}).get('creado_en'), 'proc': pr, 'hojas': hj, 'ev': ev, 'huella': hu}
antes3 = foto(P3)
C3, VC3 = complemento(P3, n3, H3, 4)
fc = fila(VC3)
ok(fc['tipo_evento'] == 'complemento' and fc['posterior_procesamiento'] is True and fc['estado'] == 'nuevo' and fc['hoja_id'] != H3,
   'C2 Complemento posterior: su propio envío y su propio seguimiento, «nuevo»', fc['estado'])
evc3 = evento(VC3)
val(f"select public.inc_envio_abrir('{evc3}')", 'nomina')
ok(fila(VC3)['estado'] == 'en_revision' and fila(V3)['estado'] == 'cerrado_procesado', 'C3 Abrir el complemento lo pone en revisión; la original procesada no cambia')
medio3 = foto(P3)
val(f"select public.inc_envio_atender('{evc3}','Complemento revisado')", 'nomina')
despues3 = foto(P3)
ok(fila(VC3)['estado'] == 'atendido', 'C4 Atender el complemento lo cierra')
ok(medio3 == despues3, 'C5 Abrir y atender el complemento no cambia el periodo procesado (procesado, hojas, eventos, firma y huella idénticos)')
ok(despues3['proc'] == antes3['proc'] and despues3['proc'] != '-|-', 'C6 El periodo procesado no se reabre (misma fecha y usuario de procesado)', despues3['proc'][:30])
P4, n4 = periodo()
H4, V4 = hoja_enviada(P4, n4)
val(f"select public.inc_aceptar_sugeridos('{V4}')", 'nomina')
val(f"select public.cred_descuentos_periodo('{P4}')", 'nomina'); val(f"select public.cred_aceptar_descuentos('{P4}')", 'nomina')
firmar(P4)
a4 = foto(P4)
ev4 = evento(V4)
val(f"select public.inc_envio_abrir('{ev4}')", 'nomina2'); val(f"select public.inc_envio_atender('{ev4}','ok')", 'nomina2')
b4 = foto(P4)
ok(a4['estado'] == 'vigente' and b4 == a4 and b4['secc'] == [],
   'C7 Firma vigente sigue vigente después de abrir y atender (misma huella, sin secciones cambiadas)', f"{b4['estado']} {b4['secc']} {b4['huella'][:12]}")
val(f"select public.inc_firmar_hoja('{H4}','rh')", 'admin')
ok(val(f"select public.inc_marcar_procesado('{P4}')", 'nomina') == 'Periodo marcado como procesado.',
   'C8 Después de abrir y atender, el periodo se procesa con la misma firma (no hubo que volver a firmar)')
P5, n5 = periodo()
H5, V5 = hoja_enviada(P5, n5)
C5, VC5 = complemento(P5, n5, H5, 4)
procesar(P5, [V5, VC5])
ok(fila(V5)['estado'] == 'cerrado_procesado' and fila(VC5)['estado'] == 'cerrado_procesado' and fila(VCpos)['estado'] == 'nuevo',
   'C9 Al procesar se cierran la original y el complemento enviado antes; el complemento posterior sigue pendiente')

# ======================================================================
print('== F · Filtros y ventana ==')
ok(all(x['empresa_id'] == EB for x in bandeja(emp=EB)) and any(x['evento_id'] == evz for x in bandeja(emp=EB)) and not any(x['empresa_id'] == EB for x in bandeja(emp=EA)),
   'F1 Filtro por empresa')
b0 = bandeja(dias=0)
ok(not any(x['evento_id'] == ev1 for x in b0) and any(x['evento_id'] == evento(VO) for x in b0),
   'F2 Ventana de atendidos: con 0 días se ocultan los atendidos y siguen todos los pendientes')
ok(sum(1 for x in bandeja() if x['estado'] in ('nuevo', 'en_revision')) == pend()['total'], 'F3 El aviso coincide con los pendientes de la bandeja', str(pend()))
ok(len({x['evento_id'] for x in bandeja()}) == len(bandeja()), 'F4 Sin duplicados: un renglón por envío')

# ======================================================================
print('== S · Permisos y aislamiento ==')
for u in ('coordA', 'consulta'):
    ok(all('sin permiso' in error_de(q, u) for q in ("select public.inc_bandeja_envios()", "select public.inc_envios_pendientes()",
                                                     f"select public.inc_envio_abrir('{evento(VO)}')", f"select public.inc_envio_atender('{evento(VO)}')")),
       f'S1 {u}: no ve la bandeja ni el aviso, no abre ni atiende')
ok(val("select public.inc_envios_pendientes()", 'admin') == val("select public.inc_envios_pendientes()", 'nomina'), 'S2 Administrador ve lo mismo que Nómina')
ok(all('permission denied' in error_de(q, anon=True) for q in ("select public.inc_bandeja_envios()", "select public.inc_envios_pendientes()",
                                                               f"select public.inc_envio_atender('{evento(VO)}')")), 'S3 anon: sin acceso a las funciones')
ok('permission denied' in error_de("select * from public.inc_envio_seguimiento", 'nomina') and
   'permission denied' in error_de(f"insert into public.inc_envio_seguimiento (evento_id, tenant_id) values ('{evento(VO)}','{T}')", 'nomina'),
   'S4 La tabla no se lee ni se escribe directamente (solo por las funciones)')
ok('permission denied' in error_de("select * from public.inc__envios_base(null)", 'nomina'), 'S5 La función interna no está expuesta')
ok(bandeja('otro') == [] and pend('otro')['total'] == 0, 'S6 Otro tenant no ve envíos ajenos')
ok('no encontrado' in error_de(f"select public.inc_envio_abrir('{evento(VO)}')", 'otro') and 'no encontrado' in error_de(f"select public.inc_envio_atender('{evento(VO)}')", 'otro'),
   'S7 Otro tenant no abre ni atiende envíos ajenos')
ok(fila(VO)['estado'] == 'nuevo', '+S8 Tras los intentos rechazados el envío sigue nuevo')
ok(val(f"select count(*) from public.inc_envio_seguimiento where evento_id='{evento(VO)}'") == '0', '+S9 Y sin seguimiento escrito')

# ======================================================================
print('== V · Reversión y reaplicación ==')
p = subprocess.run(BASE + ['-f', REV], capture_output=True, text=True)
F2 = huella_esquema()
ok(p.returncode == 0 and F2 == F0, 'V1 La reversión deja el esquema idéntico al anterior a B6', (p.stderr or '').strip()[:200] or F2.splitlines()[-1][-32:])
ok(val("select count(*) from public.inc_eventos where tipo='procesado'") != '0' and json.loads(val(f"select public.inc_firma_periodo_estado('{P4}')", 'nomina'))['estado'] == 'vigente',
   '+V2 Tras revertir, eventos y firmas siguen intactos')
p = subprocess.run(BASE + ['-f', MIG], capture_output=True, text=True)
F3 = huella_esquema()
ok(p.returncode == 0 and F3 == F1, 'V3 Reaplicar da exactamente el mismo esquema', (p.stderr or '').strip()[:200])
p = subprocess.run(BASE + ['-f', MIG], capture_output=True, text=True)
ok(p.returncode != 0 and 'ya está aplicada' in p.stderr, 'V4 Aplicar dos veces se rechaza sin cambios')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nHuella de esquema: antes {F0.splitlines()[-1][-32:]} · con B6 {F1.splitlines()[-1][-32:]}')
print(f'RESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, d_ in malas: print('  FALLA:', nn, d_)
sys.exit(1 if malas else 0)
