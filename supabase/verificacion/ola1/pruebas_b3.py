"""Pruebas de B3 (concentrado de prenómina, inc_concentrado_periodo) en la base LOCAL desechable
(puerto 55432) con todo pendiente/ aplicado (incluye B-1 y B3). Datos ficticios.
Alcance: claude/B3-concentrado-incidencias-alcance-19nov.md · Autorización de Erik 20-nov 14:39 (etapa 2, solo local).
Cada cifra del concentrado se compara contra un cálculo independiente sobre las tablas base.
  C1  Todas las personas con relación vigente en la empresa durante el periodo, con o sin captura; ninguna de otra empresa.
  C2  Solo hojas enviadas o procesadas, versión vigente; borradores y devueltas no suman y se avisan.
  C3  Complemento enviado: se suma una vez y muestra su origen. Complemento posterior al procesamiento: aparte.
  C4  Cantidad ajustada: valor vigente (captura + ajuste), sin duplicar.
  C5  Importes por decidir no se suman y se identifican.
  C6  Totales de importes separados por modalidad; ningún total mezcla modalidades.
  C7  Días por código cuadran con las celdas de las hojas incluidas.
  C8  Descuentos de crédito cuadran con cred_descuentos del periodo; informativos sin importe.
  C9  Movimientos del periodo con fecha efectiva; alta o baja a mitad del periodo muestra los días vigentes.
  C10 Estado preliminar / listo / procesado, coherente con inc_faltantes_procesar.
  C14 Solo Administrador y Nómina; Coordinador, Consulta, anon y otro tenant no consultan.
  (C15, 500 personas, en pruebas_b3_volumen.py)
Uso: DB=bh python3 pruebas_b3.py"""
import subprocess, json, sys, os, datetime
from decimal import Decimal as D

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
res = []
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    return '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET')), err
def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def falla_con(q, user, texto, n):
    out, err = sql(q, user); ok(err and texto.lower() in err.lower(), n, (err.split('\n')[0][:150] if err else 'NO FALLÓ'))
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T, T2 = '3b000000-0000-4000-8000-000000000001', '3b000000-0000-4000-8000-000000000002'
U = {k: f'3b100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta', 'rh', 'nominaT2'], 1)}
EA, EB, EX = '3b200000-0000-4000-8000-000000000001', '3b200000-0000-4000-8000-000000000002', '3b200000-0000-4000-8000-000000000003'
SEM, SEM2 = '3b300000-0000-4000-8000-000000000007', '3b300000-0000-4000-8000-000000000099'
CL_IMSS, CL_EFE = '3b400000-0000-4000-8000-000000000001', '3b400000-0000-4000-8000-000000000002'
PRJ1, PRJ2 = '3b500000-0000-4000-8000-000000000001', '3b500000-0000-4000-8000-000000000002'
RPA = '3b600000-0000-4000-8000-000000000001'
NOMBRES = ['CA', 'CB', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'M', 'XB']
P = {k: f'3b700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOMBRES, 1)}
RL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
RL['M_EB'] = '3b700000-0000-4000-8000-000000000999'
HE, BONO, CAP = '3b800000-0000-4000-8000-000000000001', '3b800000-0000-4000-8000-000000000002', '3b800000-0000-4000-8000-000000000003'
L = datetime.date.fromisoformat(val("select (date_trunc('week', public.hoy_mx() + 7))::date"))
d = lambda n: (L + datetime.timedelta(days=n)).isoformat()
nom = lambda k: f'PERSONA {k} B3'

# ---------------- semilla ----------------
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B3'),('{T2}','OTRO TENANT B3');
insert into auth.users (id, email) select v, k||'.b3@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A B3'),('{EB}','{T}','EMPRESA B B3'),('{EX}','{T2}','EMPRESA OTRA B3');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo) values ('{RPA}','{EA}','{T}','B3A1234567',true);
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7),('{SEM2}','{T2}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL_IMSS}','{T}','IMSS'),('{CL_EFE}','{T}','EFECTIVO');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ1}','OBRA NORTE B3','{T}'),('{PRJ2}','OBRA SUR B3','{T}');
"""
# relaciones: (empresa, ingreso, baja)
REL = {'CA': (EA, '2025-01-01', None), 'CB': (EA, '2025-01-01', None), 'A1': (EA, '2025-01-01', None), 'A2': (EA, '2025-01-01', None),
       'A3': (EA, d(2), None), 'A4': (EA, '2025-01-01', d(3)), 'A5': (EA, '2025-01-01', d(-3)), 'A6': (EA, '2025-01-01', None),
       'A7': (EA, '2025-01-01', None), 'M': (EA, '2025-01-01', None), 'XB': (EB, '2025-01-01', None)}
for k in NOMBRES:
    emp, ing, baja = REL[k]
    co = 'null' if k in ('CA', 'CB') else (f"'{P['CB']}'" if k == 'A6' else (f"'{P['CA']}'" if k != 'XB' else 'null'))
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id, fecha_baja) values "
             f"('{P[k]}','{T}','{emp}','{nom(k)}','B3-{k}',{co},'{PRJ1}',{f"'{baja}'" if baja else 'null'});\n")
    est = 'baja' if baja else 'vigente'
    seed += (f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, fecha_baja, causa_baja, registro_patronal_id, numero_interno) values "
             f"('{RL[k]}','{T}','{P[k]}','{emp}','{ing}','{est}',{f"'{baja}'" if baja else 'null'},{"'2'" if baja else 'null'},{f"'{RPA}'" if emp == EA else 'null'},'N{k}');\n")
seed += f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values ('{RL['M_EB']}','{T}','{P['M']}','{EB}','2025-01-01','vigente');\n"
RP = {}
for k, cl, su, mod in [('A1', CL_IMSS, 3500, 'bruto'), ('A1', CL_EFE, 700, 'neto'), ('A2', CL_IMSS, 2800, 'bruto'), ('A3', CL_IMSS, 2800, 'bruto'),
                       ('A4', CL_IMSS, 2800, 'bruto'), ('A6', CL_IMSS, 2800, 'bruto'), ('M', CL_IMSS, 2100, 'bruto'), ('CA', CL_IMSS, 7000, 'bruto'), ('CB', CL_IMSS, 7000, 'bruto')]:
    rid = f"3b900000-0000-4000-8000-{len(RP):012d}"; RP[f'{k}-{mod}'] = rid
    seed += (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values "
             f"('{rid}','{T}','{P[k]}','{RL[k]}','{EA}','{cl}','{SEM}',{su},'{mod}',7,'2025-01-01',true);\n")
seed += f"""insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null),
 ('{U['rh']}','{T}','administrador',null),('{U['nominaT2']}','{T2}','nomina',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial) values ('{EA}','{T}','2025-01-01'),('{EB}','{T}','2025-01-01');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'B3' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{BONO}','{T}','{EA}','Bono','BON','importe','otro','tarifa',1,null,2),
 ('{CAP}','{T}','{EA}','Capacitación','CAP','horas','otro','sin_importe',null,null,3);
-- Movimientos laborales del periodo (fecha efectiva dentro) y uno fuera
insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, causa, origen) values
 ('{T}','{P['A3']}','{RL['A3']}','ingreso','{d(2)}',null,'pantalla'),
 ('{T}','{P['A4']}','{RL['A4']}','baja','{d(3)}','2','pantalla'),
 ('{T}','{P['A1']}','{RL['A1']}','modificacion_salario','{d(4)}',null,'pantalla'),
 ('{T}','{P['A1']}','{RL['A1']}','cambio_puesto','{d(-10)}',null,'pantalla'),
 ('{T}','{P['M']}','{RL['M_EB']}','modificacion_salario','{d(1)}',null,'pantalla');
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)

PER = val(f"select public.inc_crear_periodo('{EA}','{SEM}','{d(0)}','{d(6)}')", 'nomina')
PEB = val(f"select public.inc_crear_periodo('{EB}','{SEM}','{d(0)}','{d(6)}')", 'nomina')
conc = lambda per=PER, u='nomina': json.loads(val(f"select public.inc_concentrado_periodo('{per}')", u))
persona = lambda c, k: next((x for x in c['personas'] if x['personal_id'] == P[k]), None)
num = lambda x: D(str(x)) if x is not None else None

# Créditos: préstamo de A1 (se decide), FONACOT de A3 (queda por decidir), INFONAVIT de A2 (informativo),
# préstamo de M en la empresa B (no debe aparecer en A).
def guardar(datos): return val(f"select public.cred_guardar(null, {lit(datos)}, null)", 'nomina')
CR_A1 = guardar({'personal_id': P['A1'], 'tipo': 'prestamo', 'referencia': 'PR-A1', 'relacion_laboral_id': RL['A1'], 'fecha_inicio': d(0), 'periodicidad_id': SEM, 'importe_periodo': 300, 'monto_total': 900})
CR_A3 = guardar({'personal_id': P['A3'], 'tipo': 'fonacot', 'referencia': 'FN-A3', 'relacion_laboral_id': RL['A3'], 'fecha_inicio': d(0), 'periodicidad_id': SEM, 'importe_periodo': 150})
CR_A2 = guardar({'personal_id': P['A2'], 'tipo': 'infonavit', 'referencia': 'INF-A2', 'relacion_laboral_id': RL['A2'], 'fecha_inicio': '2025-01-01', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 900})
CR_M = guardar({'personal_id': P['M'], 'tipo': 'prestamo', 'referencia': 'PR-M-B', 'relacion_laboral_id': RL['M_EB'], 'fecha_inicio': d(0), 'periodicidad_id': SEM, 'importe_periodo': 200, 'monto_total': 1000})
for c in (CR_A1, CR_A3, CR_A2, CR_M):
    if val(f"select estado from public.cred_creditos where id='{c}'") != 'activo':
        val(f"select public.cred_cambiar_estado('{c}','activo','{d(0)}','Alta B3')", 'nomina')

# ---------------- Hoja normal de CA (se envía) ----------------
HA = val(f"select public.inc_abrir_hoja('{PER}')", 'coordA')
val(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo, proyecto_id) values
 ('{HA}','{P['A1']}','{d(0)}','F',null),('{HA}','{P['A1']}','{d(1)}','I',null),
 ('{HA}','{P['A1']}','{d(2)}',null,'{PRJ2}'),('{HA}','{P['A1']}','{d(3)}',null,'{PRJ2}'),('{HA}','{P['A1']}','{d(4)}',null,'{PRJ2}'),('{HA}','{P['A1']}','{d(5)}',null,'{PRJ2}'),
 ('{HA}','{P['A3']}','{d(6)}','D',null),('{HA}','{P['A4']}','{d(0)}','F',null)""", 'coordA')
val(f"""insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, motivo) values
 ('{HA}','{P['A1']}','{d(2)}','{HE}',2,null),('{HA}','{P['A1']}','{d(3)}','{BONO}',100,null),('{HA}','{P['A1']}','{d(3)}','{CAP}',4,null),
 ('{HA}','{P['A3']}','{d(3)}','{HE}',1,null),('{HA}','{P['M']}','{d(1)}','{HE}',3,null),('{HA}','{P['A7']}','{d(1)}','{HE}',2,null)""", 'coordA')
val(f"insert into public.inc_observaciones (hoja_id, personal_id, texto) values ('{HA}','{P['A1']}','Cubrió turno de A4')", 'coordA')
V1 = val(f"select public.inc_enviar_hoja('{HA}')", 'coordA')
# ---------------- Hoja de CB (borrador con captura: no debe sumar) ----------------
HB = val(f"select public.inc_abrir_hoja('{PER}')", 'coordB')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HB}','{P['A6']}','{d(0)}','{HE}',5)", 'coordB')
val(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HB}','{P['A6']}','{d(1)}','F')", 'coordB')
val(f"select public.cred_descuentos_periodo('{PER}')", 'nomina')

print('== C1 · Personas ==')
c = conc()
esperadas = set(val(f"""select string_agg(distinct rl.personal_id::text, ',') from public.relaciones_laborales rl
  where rl.empresa_id = '{EA}' and rl.estado <> 'anulada' and coalesce(rl.fecha_ingreso,'-infinity') <= '{d(6)}'
    and ((rl.estado = 'vigente' and rl.fecha_baja is null) or rl.fecha_baja >= '{d(0)}')""").split(','))
dadas = {x['personal_id'] for x in c['personas']}
ok(dadas == esperadas and len(dadas) == 9, 'C1 Las personas son exactamente las de relación en la empresa A durante el periodo (9)', f'{len(dadas)} vs {len(esperadas)}')
ok(P['A2'] in dadas and persona(c, 'A2')['con_incidencias'] is False, 'C1 Aparece quien no tuvo captura (A2), marcado sin incidencias')
ok(P['XB'] not in dadas and P['A5'] not in dadas, 'C1 No aparecen: persona solo de la empresa B (XB) ni la baja anterior al periodo (A5)')
ok(P['A3'] in dadas and P['A4'] in dadas, 'C1 Aparecen el alta y la baja de mitad de periodo (A3, A4)')
m = persona(c, 'M')
ok(m and not any(l['tipo'] == 'prestamo' for l in m['descuentos']) and not m['movimientos'], 'C1 Persona multiempresa (M): en A sin el préstamo ni el movimiento de su relación en B', json.dumps(m['descuentos'] + m['movimientos'])[:120])
cb = conc(PEB)
ok({x['personal_id'] for x in cb['personas']} == {P['XB'], P['M']}, 'C1 El concentrado de la empresa B tiene solo a XB y M')
ok(persona(c, 'A1')['registro_patronal'] == 'B3A1234567' and persona(c, 'A1')['numero_interno'] == 'NA1' and persona(c, 'A1')['empleado_id'] == 'B3-A1',
   'C1 Identificación: número BEH, número interno y registro patronal de la relación')

print('== C2 · Hojas incluidas ==')
ok([h['hoja_id'] for h in c['hojas']] == [HA], 'C2 Solo cuenta la hoja enviada de CA (no el borrador de CB)', str([h['coordinador'] for h in c['hojas']]))
a6 = persona(c, 'A6')
ok(a6['cantidades'] == {} and a6['dias'] == {} and a6['con_incidencias'] is False, 'C2 Lo capturado en el borrador (A6: 5 h y una F) no suma')
ok(any('PERSONA CB B3: no ha enviado su hoja' in a for a in c['avisos']['hojas_no_incluidas']), 'C2 Se avisa la hoja sin enviar', str(c['avisos']['hojas_no_incluidas']))

print('== C5 · Importes por decidir (antes de decidir nada) ==')
imp_a1 = persona(c, 'A1')['importes']
ok(c['totales']['importes'] == {} and c['totales']['importes_por_modalidad'] == {}, 'C5 Nada decidido todavía: ningún importe suma', json.dumps(c['totales']['importes']))
pd_sql = int(val(f"select count(*) from public.inc_importes where version_id = '{V1}' and origen in ('pendiente','sin_sueldo','por_asignar')"))
ok(c['totales']['importes_por_decidir'] == pd_sql and pd_sql > 0, f'C5 Por decidir = {pd_sql}, igual que en la base', str(c['totales']['importes_por_decidir']))
ok(all(l['final'] is None for l in imp_a1 if l['estado'] == 'por_decidir'), 'C5 Las líneas por decidir no traen cifra final')
a7 = persona(c, 'A7')
ok(a7['importes'] and a7['importes'][0]['origen'] == 'sin_sueldo' and a7['importes'][0]['estado'] == 'por_decidir' and a7['importes_por_decidir'] == 1,
   'C5 Sin esquema de pago (A7): «sin_sueldo», contado como por decidir', json.dumps(a7['importes'])[:100])
cap = [l for l in imp_a1 if l['concepto_id'] == CAP]
ok(cap and cap[0]['estado'] == 'sin_importe' and cap[0]['final'] is None and persona(c, 'A1')['cantidades'][CAP] == 4, 'C5 Concepto sin importe: solo cantidad (4 h de capacitación)')

print('== C6 · Modalidades ==')
val(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina')
he_neto = val(f"select id from public.inc_importes where version_id='{V1}' and personal_id='{P['A1']}' and concepto_id='{HE}' and modalidad='neto'")
val(f"select public.inc_decidir_importe('{he_neto}', 55.5, 'Ajuste B3')", 'nomina')
c = conc()
mods = {r.split('|')[0]: D(r.split('|')[1]) for r in val(f"""select string_agg(coalesce(modalidad,'sin_modalidad')||'|'||sum, ';') from (select modalidad, sum(final) from public.inc_importes
         where version_id = '{V1}' and origen in ('aceptado','modificado') group by 1) x""").split(';')}
dado = {k: num(v) for k, v in c['totales']['importes_por_modalidad'].items()}
ok(dado == mods and 'bruto' in dado and 'neto' in dado, 'C6 Totales por modalidad = suma de la base, bruto y neto por separado', str(dado))
a1 = persona(c, 'A1')
ok(set(a1['importes_decididos'][HE]) == {'bruto', 'neto'} and num(a1['importes_decididos'][HE]['neto']) == D('55.5'),
   'C6 A1 · Horas extra: una cifra bruta y una neta (modificada a $55.50), nunca sumadas', json.dumps(a1['importes_decididos'][HE]))
he_tot = c['totales']['importes'][HE]
ok(all(isinstance(v, (int, float)) for v in he_tot.values()) and set(he_tot) <= {'bruto', 'neto', 'manual', 'sin_modalidad'}, 'C6 Total por concepto desglosado por modalidad (no hay un total mezclado)', json.dumps(he_tot))
ok(len([l for l in a1['importes'] if l['concepto_id'] == HE]) == 2 and {l['clasificacion'] for l in a1['importes'] if l['concepto_id'] == HE} == {'IMSS', 'EFECTIVO'},
   'C6 Detalle por esquema: dos líneas de horas extra (IMSS y EFECTIVO)')

print('== C3 / C4 · Complemento enviado y ajuste ==')
HC = val(f"select public.inc_abrir_hoja('{PER}','{HA}')", 'coordA')
linea = val(f"select id from public.inc_cantidades where hoja_id='{HA}' and personal_id='{P['A1']}' and concepto_id='{HE}' and fecha='{d(2)}'")
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, tipo_linea, linea_corregida_id) values ('{HC}','{P['A1']}','{d(2)}','{HE}',-1,'ajuste','{linea}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HC}','{P['A2']}','{d(4)}','{HE}',2)", 'coordA')
val(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HC}','{P['A2']}','{d(3)}','V')", 'coordA')
VC = val(f"select public.inc_enviar_hoja('{HC}')", 'coordA')
c = conc()
ok({h['hoja_id'] for h in c['hojas']} == {HA, HC} and next(h for h in c['hojas'] if h['hoja_id'] == HC)['tipo'] == 'complemento', 'C3 El complemento enviado se incluye, como complemento')
a1, a2 = persona(c, 'A1'), persona(c, 'A2')
ok(num(a1['cantidades'][HE]) == D('1'), 'C4 Horas extra de A1: 2 capturadas − 1 de ajuste = 1 (valor vigente)', str(a1['cantidades'][HE]))
ok(sum(num(x['cantidad']) for x in a1['cantidades_detalle'] if x['concepto_id'] == HE and x['fecha'] == d(2)) == 1, 'C4 El detalle por día suma el valor vigente (sin duplicar la línea original)')
ok(num(a2['cantidades'][HE]) == D('2') and a2['dias'] == {'V': 1} and any(o['tipo'] == 'complemento' for o in a2['origen']), 'C3 Lo del complemento se suma una vez y muestra su origen (A2: 2 h y una V)', json.dumps(a2['origen'])[:120])
tot_he = D(val(f"""select sum((q->>'cantidad')::numeric) from public.inc_hojas h join public.inc_versiones v on v.hoja_id=h.id and v.numero=h.version_actual
   cross join lateral jsonb_array_elements(v.datos->'cantidades') q where h.periodo_id='{PER}' and h.estado in ('enviada','procesada') and (q->>'concepto_id')::uuid='{HE}'"""))
ok(num(c['totales']['cantidades'][HE]) == tot_he, f'C4 Total de horas extra = captura + ajustes de las hojas incluidas ({tot_he})', str(c['totales']['cantidades'][HE]))
ok(c['totales']['importes_por_decidir'] == int(val(f"select count(*) from public.inc_importes where version_id in ('{V1}','{VC}') and origen in ('pendiente','sin_sueldo','por_asignar')")),
   'C5 Los importes del complemento por decidir también se cuentan sin sumar')

print('== C7 · Días por código ==')
dias_sql = dict(r.split('|') for r in val(f"""select string_agg(codigo||'|'||n, ';') from (select c.codigo, count(*) n from public.inc_celdas c join public.inc_hojas h on h.id=c.hoja_id
   where h.periodo_id='{PER}' and h.estado in ('enviada','procesada') and c.codigo is not null group by 1) x""").split(';'))
ok({k: str(v) for k, v in c['totales']['dias'].items()} == dias_sql, 'C7 Totales de días por código = celdas de las hojas incluidas', f"{c['totales']['dias']} vs {dias_sql}")
ok(a1['dias'] == {'F': 1, 'I': 1} and persona(c, 'A3')['dias'] == {'D': 1}, 'C7 Por persona: A1 F=1 I=1, A3 D=1')
ok(a1['proyecto'] == 'OBRA SUR B3' and persona(c, 'A2')['proyecto'] == 'OBRA NORTE B3', 'C7 Proyecto predominante: A1 con 4 de 7 días en OBRA SUR; A2 el de su ficha')

print('== C8 · Descuentos ==')
d_a1 = val(f"select id from public.cred_descuentos where periodo_id='{PER}' and credito_id='{CR_A1}'")
val(f"select public.cred_decidir_descuento('{d_a1}', 250, 'B3')", 'nomina')
c = conc()
dsql = dict(r.split('|') for r in val(f"""select string_agg(c.tipo||'|'||sum, ';') from (select c.tipo, sum(d.final) from public.cred_descuentos d join public.cred_creditos c on c.id=d.credito_id
   where d.periodo_id='{PER}' and d.origen in ('aceptado','modificado') group by 1) c""").split(';'))
ok({k: num(v) for k, v in c['totales']['descuentos'].items()} == {k: D(v) for k, v in dsql.items()} and dsql == {'prestamo': '250.00'},
   'C8 Total decidido por tipo = cred_descuentos (préstamo $250)', json.dumps(c['totales']['descuentos']))
a3 = persona(c, 'A3')
ok(a3['descuentos'] and a3['descuentos'][0]['estado'] == 'por_decidir' and a3['descuentos'][0]['final'] is None and a3['descuentos_por_decidir'] == 1
   and c['totales']['descuentos_por_decidir'] == 1 and 'fonacot' not in c['totales']['descuentos'], 'C8 FONACOT por decidir: identificado, sin sumar')
a2 = persona(c, 'A2')
ok(a2['informativos'] and a2['informativos'][0]['tipo'] == 'infonavit' and 'final' not in a2['informativos'][0] and c['totales']['informativos'] == 1,
   'C8 INFONAVIT: informativo, sin importe', json.dumps(a2['informativos'])[:120])
ok(num(persona(c, 'A1')['descuentos_decididos']) == D('250'), 'C8 Por persona: A1 $250 decididos')

print('== C9 · Movimientos y días vigentes ==')
a3, a4, a1 = persona(c, 'A3'), persona(c, 'A4'), persona(c, 'A1')
ok(a3['dias_vigentes'] == 5 and a3['alta'] == d(2) and [m['tipo'] for m in a3['movimientos']] == ['ingreso'] and a3['movimientos'][0]['fecha'] == d(2),
   'C9 Alta a mitad del periodo (A3): ingreso con fecha y 5 días vigentes', f"{a3['dias_vigentes']} {a3['movimientos']}")
ok(a4['dias_vigentes'] == 4 and a4['baja'] == d(3) and a4['movimientos'][0]['tipo'] == 'baja' and a4['movimientos'][0]['causa'] == '2',
   'C9 Baja a mitad del periodo (A4): baja con fecha y 4 días vigentes', f"{a4['dias_vigentes']} {a4['movimientos']}")
ok([m['tipo'] for m in a1['movimientos']] == ['modificacion_salario'] and a1['dias_vigentes'] == 7, 'C9 Modificación de salario dentro del periodo; el cambio de puesto anterior no aparece')
ok(c['totales']['movimientos'] == {'ingreso': 1, 'baja': 1, 'modificacion_salario': 1}, 'C9 Totales de movimientos del periodo', json.dumps(c['totales']['movimientos']))

print('== C10 · Estado ==')
nf = int(val(f"select count(*) from public.inc_faltantes_procesar('{PER}')", 'nomina'))
ok(c['estado'] == 'preliminar' and len(c['faltantes']) == nf and nf > 0, f'C10 Con {nf} faltantes: preliminar (igual que inc_faltantes_procesar)', c['estado'])
# completar: CB envía, se decide todo, sueldo manual de A7, responsable y firmas
VB = val(f"select public.inc_enviar_hoja('{HB}')", 'coordB')
c = conc()
ok(num(persona(c, 'A6')['cantidades'][HE]) == D('5') and HB in {h['hoja_id'] for h in c['hojas']}, 'C2 Al enviarse, la hoja de CB ya suma (A6: 5 h)')
val(f"select public.inc_capturar_sueldo_manual('{PER}','{P['A7']}',300)", 'nomina')
for v in (V1, VC, VB): val(f"select public.inc_aceptar_sugeridos('{v}')", 'nomina')
for v in (V1, VC, VB):  # B1.1: Nómina asigna el esquema de las líneas por asignar (el primero que ofrece BeeHuman)
    for x in (val(f"select coalesce(string_agg(a.linea_id::text||'/'||a.registro_pago_id, ','), '-') from (select distinct on (linea_id) linea_id, registro_pago_id from public.inc_esquemas_asignables('{v}') order by linea_id) a", 'nomina') or '').split(','):
        if x != '-': val(f"select public.inc_asignar_esquema('{x.split('/')[0]}','{x.split('/')[1]}')", 'nomina')
for x in val(f"select string_agg(i.id::text, ',') from public.inc_importes i where i.version_id in ('{V1}','{VC}','{VB}') and i.origen in ('pendiente','sin_sueldo','por_asignar')").split(','):
    if x: val(f"select public.inc_decidir_importe('{x}', 10, 'B3 cierre')", 'nomina')
val(f"select public.cred_aceptar_descuentos('{PER}')", 'nomina')
val(f"update public.inc_parametros set responsable_nomina_user = '{U['nomina']}' where empresa_id = '{EA}'", 'admin')
val(f"select public.inc_firmar_periodo('{PER}', public.inc_firma_periodo_estado('{PER}')->'huella_actual'->>'total')", 'nomina')   # opción B: firma única del periodo
c = conc()
nf = int(val(f"select count(*) from public.inc_faltantes_procesar('{PER}')", 'nomina'))
ok(c['estado'] == 'listo' and nf == 0 and c['faltantes'] == [], 'C10 Sin faltantes: listo', f"{c['estado']} / {nf} / {c['faltantes'][:1]}")
a7 = persona(c, 'A7')
ok(a7['importes'] and a7['importes'][0]['modalidad'] == 'manual' and 'manual' in c['totales']['importes_por_modalidad'], 'C6 Sueldo manual: modalidad «manual», en su propio total', json.dumps(c['totales']['importes_por_modalidad']))
ok(val(f"select public.inc_marcar_procesado('{PER}')", 'nomina') == 'Periodo marcado como procesado.', 'C10 Se procesa el periodo')
c = conc()
ok(c['estado'] == 'procesado' and c['periodo']['procesado_en'] and all(h['estado'] == 'procesada' for h in c['hojas']), 'C10 Procesado: estado «procesado» y hojas procesadas incluidas')
antes = json.dumps(c['totales'], sort_keys=True)

print('== C3 · Complemento posterior al procesamiento ==')
HP = val(f"select public.inc_abrir_hoja('{PER}','{HA}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HP}','{P['A2']}','{d(5)}','{HE}',4)", 'coordA')
val(f"select public.inc_enviar_hoja('{HP}')", 'coordA')
c = conc()
ok(json.dumps(c['totales'], sort_keys=True) == antes, 'C3 El complemento posterior no altera los totales del periodo procesado')
ok(c['avisos']['complementos_posteriores'] == 1 and any(h['posterior'] for h in c['hojas']), 'C3 Se avisa y se identifica como complemento posterior')
a2 = persona(c, 'A2')
post = [x for x in a2['cantidades_detalle'] if x['posterior']]
ok(num(a2['cantidades'][HE]) == D('2') and post and num(post[0]['cantidad']) == D('4') and any(l['posterior'] for l in a2['importes']),
   'C3 A2: sus 4 h posteriores se muestran aparte, marcadas, fuera del total vigente (2 h)')

print('== C14 · Permisos ==')
for u in ('coordA', 'consulta'):
    falla_con(f"select public.inc_concentrado_periodo('{PER}')", u, 'sin permiso', f'C14 {u}: no consulta el concentrado')
ok(conc(PER, 'admin')['estado'] == 'procesado', 'C14 Administrador sí consulta')
falla_con(f"select public.inc_concentrado_periodo('{PER}')", 'nominaT2', 'periodo no encontrado', 'C14 Nómina de otro tenant: no ve el periodo')
anon = subprocess.run(PSQL, input=f"begin; set local role anon; select public.inc_concentrado_periodo('{PER}'); commit;", capture_output=True, text=True).stderr
ok('permission denied' in anon, 'C14 anon no ejecuta la función', anon.split('\n')[0][:90])
ok(val(f"select count(*) from information_schema.routine_privileges where routine_name='inc_concentrado_periodo' and grantee in ('anon','PUBLIC')") == '0', 'C14 Sin permisos a anon ni PUBLIC')

print('== C16 · C17 · Esquemas y huella (opción B) ==')
c = conc()
esq = persona(c, 'A1')['esquemas']
ok(len(esq) == 2 and {e['modalidad'] for e in esq} == {'bruto', 'neto'} and {e['clasificacion'] for e in esq} == {'IMSS', 'EFECTIVO'},
   'C16 El concentrado muestra los esquemas de pago vigentes de la persona (A1: IMSS bruto y EFECTIVO neto)', json.dumps(esq)[:140])
h_antes = val(f"select public.inc_firma_periodo_estado('{PER}')->'huella_actual'->>'total'", 'nomina')
val(f"update public.personal set nombre_completo = 'PERSONA A1 RENOMBRADA B3', proyecto_id = '{PRJ2}' where id = '{P['A1']}'", replica=True)
h_desp = val(f"select public.inc_firma_periodo_estado('{PER}')->'huella_actual'->>'total'", 'nomina')
ok(h_antes == h_desp and len(h_antes) == 64, 'C17 La huella no cambia por nombre ni por proyecto de la ficha', h_antes[:16])

print('== Solo lectura ==')
vol = val("select provolatile from pg_proc where proname = 'inc_concentrado_periodo'")
ok(vol == 's', 'La función es STABLE (no puede escribir)', vol)

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
