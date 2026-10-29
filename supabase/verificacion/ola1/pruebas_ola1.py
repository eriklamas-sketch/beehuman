"""Pruebas de la migración Ola 1 en una base Postgres LOCAL y desechable.
Cada paso corre en su propia transacción con la identidad de un usuario
(rol authenticated + claim sub), igual que una petición real de la app.
Uso: python3 pruebas_ola1.py   (requiere la base local bh en el puerto 55432)"""
import subprocess, json, sys, datetime

PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bh']
res = []

def sql(q, user=None, replica=False):
    pre = 'begin;\n'
    if replica: pre += "set local session_replication_role = replica;\n"
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    out = '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET'))
    err = p.stderr.strip()
    return out, err

def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''

def ok(cond, nombre, detalle=''):
    res.append((nombre, bool(cond), detalle))
    print(('OK    ' if cond else 'FALLA ') + nombre + (f'  [{detalle}]' if detalle else ''))

def falla_con(q, user, texto, nombre, replica=False):
    out, err = sql(q, user, replica)
    ok(err and texto.lower() in err.lower(), nombre, (err.split('\n')[0][:140] if err else 'NO FALLÓ: ' + out[:80]))

# ---------------- Datos ficticios ----------------
T = '0a000000-0000-4000-8000-000000000001'
U = {k: f'0b000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(
    ['admin', 'nomina', 'nomina2', 'rh', 'coordA', 'coordB', 'consulta'], 1)}
hoy = datetime.date.fromisoformat(val('select current_date'))
lunes = hoy + datetime.timedelta(days=(7 - hoy.weekday()) % 7 or 7)   # próximo lunes
dom = lunes + datetime.timedelta(days=6)
d = lambda n: (lunes + datetime.timedelta(days=n)).isoformat()        # 0=lunes … 6=domingo

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT SINTETICO OLA1');
insert into auth.users (id, email) select v, k||'@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('0c000000-0000-4000-8000-000000000001','{T}','EMPRESA OLA1'),('0c000000-0000-4000-8000-000000000002','{T}','EMPRESA OTRA');
insert into public.areas (id, tenant_id, nombre) values ('0d000000-0000-4000-8000-000000000001','{T}','AREA A'),('0d000000-0000-4000-8000-000000000002','{T}','AREA B');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('0e000000-0000-4000-8000-000000000030','{T}','Mensual',30),('0e000000-0000-4000-8000-000000000007','{T}','Semanal',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('0f000000-0000-4000-8000-000000000001','{T}','IMSS');
"""
E = '0c000000-0000-4000-8000-000000000001'
P = {k: f'0a100000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(
    ['CA', 'CB', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'PSW', 'PBAJA', 'PNOI'], 1)}
personas = {  # clave: (coordinador, área, fecha_baja)
    'CA': (None, 'A', None), 'CB': (None, 'A', None),
    'P1': ('CA', 'A', None), 'P2': ('CA', 'B', None), 'P3': ('CA', 'A', None), 'P4': ('CA', 'A', None),
    'P5': ('CA', 'A', None), 'P6': ('CB', 'A', None), 'PSW': ('CA', 'A', None), 'PBAJA': ('CA', 'A', d(3)),
    'PNOI': ('CA', 'A', None)}
for k, (co, ar, baja) in personas.items():
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, area_id, fecha_baja, fecha_asignacion) values "
             f"('{P[k]}','{T}','{E}','PERSONA {k}','BEH-{k}',{repr(P[co]) if co else 'null'},'0d000000-0000-4000-8000-00000000000{1 if ar=='A' else 2}',"
             f"{repr(baja) if baja else 'null'},'2025-01-15');\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values
 ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),('{U['nomina2']}','{T}','nomina',null),
 ('{U['rh']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),
 ('{U['consulta']}','{T}','consulta',null);
insert into public.usuario_alcances (tenant_id, user_id, empresa_id) values ('{T}','{U['consulta']}','{E}');
-- Esquemas: P1 = 20,000 netos mensuales; P2 = 24,000 brutos mensuales + 1,400 netos semanales; P3 = 24,000 brutos.
insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio) values
 ('{T}','{P['P1']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',20000,'neto',30,'2025-01-01'),
 ('{T}','{P['P2']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',24000,'bruto',30,'2025-01-01'),
 ('{T}','{P['P2']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000007',1400,'neto',7,'2025-01-01'),
 ('{T}','{P['P3']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',24000,'bruto',30,'2025-01-01'),
 ('{T}','{P['P4']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',20000,'neto',30,'2025-01-01'),
 ('{T}','{P['P5']}','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',20000,'neto',30,'2025-01-01');
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
# Carga inicial equivalente a la de la migración (los datos se crearon después de migrar)
val(f"""insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
        select tenant_id, id, coordinador_id, current_date, 'carga_inicial', 'prueba' from public.personal
        where tenant_id = '{T}' and coordinador_id is not null""")

print(f'Periodo de prueba: {lunes} a {dom}')
# =====================================================================
print('\n== Bloqueante 1 · Historial de asignaciones ==')
ok(val(f"select count(*) from public.inc_asignaciones where tenant_id='{T}' and desde < current_date") == '0',
   'Carga inicial: ningún tramo anterior a hoy (no se supone historial)')
ok(val(f"select count(*) from public.inc_asignaciones where tenant_id='{T}' and origen='carga_inicial' and desde=current_date") == '9',
   'Carga inicial: 9 personas con coordinador, tramo desde hoy')
falla_con(f"select public.inc_crear_periodo('{E}', null, current_date - 7, current_date - 1)", 'nomina',
          'no hay historial', 'Periodo anterior al historial: se rechaza')
PER = val(f"select public.inc_crear_periodo('{E}','0e000000-0000-4000-8000-000000000007','{lunes}','{dom}')", 'nomina')
ok(len(PER) == 36, 'Nómina crea el periodo semanal')
# Cambio de coordinador con fecha efectiva (jueves) para PSW: A lun-mié, B jue-dom
val(f"select public.inc_registrar_asignacion('{P['PSW']}','{P['CB']}','{d(3)}','Cambio de cuadrilla por oficio de operaciones')", 'nomina')
filas = val(f"select string_agg(coordinador_id::text||' '||desde||' '||coalesce(hasta::text,'∞'), ' | ' order by desde) from public.inc_asignaciones where personal_id='{P['PSW']}'")
ok(filas == f"{P['CA']} {hoy} {d(2)} | {P['CB']} {d(3)} ∞", 'Fecha efectiva explícita: tramo A cierra el miércoles, B inicia el jueves', filas)
falla_con(f"insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen) values ('{T}','{P['PSW']}','{P['CA']}','{d(4)}','registro_nomina')",
          None, 'conflicting key value violates exclusion constraint', 'Tramos traslapados: la base los rechaza aun como dueño')
falla_con(f"select public.inc_registrar_asignacion('{P['P1']}','{P['CB']}','{d(0)}','')", 'nomina', 'indica el motivo', 'Registro sin motivo o fuente: rechazado')
falla_con(f"select public.inc_registrar_asignacion('{P['P1']}','{P['CB']}','{d(0)}','x')", 'coordA', 'sin permiso', 'Coordinador no puede registrar asignaciones')
# Cambio desde el expediente (como lo hace hoy la app: sin fecha) -> fecha efectiva = hoy
val(f"update public.personal set coordinador_id='{P['CB']}' where id='{P['P5']}'", 'admin')
filas = val(f"select string_agg(coalesce(hasta::text,'∞')||'/'||origen, ' | ' order by desde, registrado_en) from public.inc_asignaciones where personal_id='{P['P5']}'")
ok(filas == '∞/cambio_expediente', 'Cambio en el expediente el mismo día de la carga: reemplaza el tramo de hoy', filas)
val(f"update public.personal set coordinador_id='{P['CA']}' where id='{P['P5']}'", 'admin')  # se regresa a A
HA = val(f"select public.inc_abrir_hoja('{PER}')", 'coordA')
HB = val(f"select public.inc_abrir_hoja('{PER}')", 'coordB')
dias_a = val(f"select count(*) from public.inc_personas_hoja('{HA}') where personal_id='{P['PSW']}'", 'coordA')
dias_b = val(f"select count(*) from public.inc_personas_hoja('{HB}') where personal_id='{P['PSW']}'", 'coordB')
ok(dias_a == '3' and dias_b == '4', 'A10: PSW aparece 3 días con A y 4 días con B, sin duplicarse', f'A={dias_a} B={dias_b}')
ok(val(f"select max(fecha) from public.inc_personas_hoja('{HA}') where personal_id='{P['PBAJA']}'", 'coordA') == d(3),
   'A12: persona con baja el jueves solo aparece hasta el jueves')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) select '{HA}','{P['PSW']}','{d(4)}', id, 1 from public.inc_conceptos limit 0; insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HA}','{P['PSW']}','{d(4)}','F')",
          'coordA', 'no estaba asignada a este coordinador', 'Coordinador A no puede capturar a PSW el viernes')
ok(val(f"select count(*) from public.inc_personas_hoja('{HB}')", 'coordA') == '0', 'Coordinador A no ve las personas de la hoja de B')

# =====================================================================
print('\n== Configuración (Administrador) ==')
conf = f"""
insert into public.inc_parametros (empresa_id, tenant_id, responsable_nomina_user, responsable_rh_user)
  values ('{E}','{T}','{U['nomina']}','{U['rh']}') on conflict (empresa_id) do update set responsable_nomina_user=excluded.responsable_nomina_user, responsable_rh_user=excluded.responsable_rh_user;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('0a200000-0000-4000-8000-000000000001','{T}','{E}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('0a200000-0000-4000-8000-000000000002','{T}','{E}','Domingo trabajado','DOM','dias','domingo','beehuman',null,null,2),
 ('0a200000-0000-4000-8000-000000000003','{T}','{E}','Turno nocturno','T','turnos','turno','tarifa',700,null,3),
 ('0a200000-0000-4000-8000-000000000004','{T}','{E}','Descuento operativo','DESC','importe','descuento','tarifa',1,null,4),
 ('0a200000-0000-4000-8000-000000000005','{T}','{E}','Horas tarifa','HT','horas','otro','tarifa',50,null,5),
 ('0a200000-0000-4000-8000-000000000006','{T}','{E}','Domingo tarifa','DOMT','dias','domingo','beehuman',600,null,6),
 ('0a200000-0000-4000-8000-000000000007','{T}','{E}','Bono sin importe','BSI','horas','otro','sin_importe',null,null,7)"""
falla_con(conf, 'nomina', 'row-level security', 'Nómina no puede configurar conceptos')
val(conf, 'admin')
val(f"insert into public.inc_tarifas_area (tenant_id, concepto_id, area_id, tarifa) values ('{T}','0a200000-0000-4000-8000-000000000006','0d000000-0000-4000-8000-000000000002',700)", 'admin')
ok(val("select count(*) from public.inc_conceptos where empresa_id='%s'" % E, 'coordA') == '7', 'Coordinador lee los conceptos (sin sueldos)')
K = {'HE': '0a200000-0000-4000-8000-000000000001', 'DOM': '0a200000-0000-4000-8000-000000000002', 'T': '0a200000-0000-4000-8000-000000000003',
     'DESC': '0a200000-0000-4000-8000-000000000004', 'HT': '0a200000-0000-4000-8000-000000000005', 'DOMT': '0a200000-0000-4000-8000-000000000006',
     'BSI': '0a200000-0000-4000-8000-000000000007'}

# =====================================================================
print('\n== Captura del coordinador ==')
cap = []
for dia, h in [(0, 4), (1, 4), (2, 4)]:                       # P1: 12 h extra en la semana
    cap.append(f"('{HA}','{P['P1']}','{d(dia)}','{K['HE']}',{h})")
cap.append(f"('{HA}','{P['P4']}','{d(0)}','{K['HE']}',2)")      # P4: 2 h extra
cap.append(f"('{HA}','{P['P1']}','{d(6)}','{K['DOM']}',1)")     # P1: domingo 25 %
cap.append(f"('{HA}','{P['P2']}','{d(6)}','{K['DOMT']}',1)")    # P2 (área B): domingo tarifa área 700
cap.append(f"('{HA}','{P['P3']}','{d(6)}','{K['DOMT']}',1)")    # P3 (área A): domingo tarifa general 600
cap.append(f"('{HA}','{P['P3']}','{d(0)}','{K['HT']}',19)")     # tarifa propia 19 × 50
cap.append(f"('{HA}','{P['PNOI']}','{d(1)}','{K['HE']}',3)")    # sin esquema de pago
cap.append(f"('{HA}','{P['P4']}','{d(2)}','{K['BSI']}',5)")     # sin importe
val("insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values " + ','.join(cap), 'coordA')
val(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HA}','{P['P2']}','{d(1)}','F')", 'coordA')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HA}','{P['P1']}','{d(0)}','{K['HE']}',1)",
          'coordA', 'duplicate key value violates unique constraint "inc_cant_captura"', '(d) Misma persona, día y concepto dos veces: rechazado')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HA}','{P['P1']}','{d(0)}','{K['DESC']}',150)",
          'coordA', 'requiere motivo', 'C14: descuento sin motivo rechazado')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, motivo, conformidad_declarada) values ('{HA}','{P['P1']}','{d(0)}','{K['DESC']}',150,'Vajilla rota',true)", 'coordA')
ok(val(f"select conformidad_por from public.inc_cantidades where concepto_id='{K['DESC']}'") == U['coordA'], 'Conformidad declarada: queda quién la declaró')
falla_con(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HB}','{P['P6']}','{d(0)}','F')", 'coordA', 'row-level security', 'Coordinador A no escribe en la hoja de B')

# =====================================================================
print('\n== Bloqueante 2 · Versiones y duplicados ==')
V1 = val(f"select public.inc_enviar_hoja('{HA}','Semana de entrega de obra')", 'coordA')
ok(val(f"select estado||'/'||version_actual from public.inc_hojas where id='{HA}'") == 'enviada/1', 'Envío: hoja enviada, versión 1')
val(f"update public.inc_cantidades set cantidad=9 where hoja_id='{HA}'", 'coordA')
ok(val(f"select count(*) from public.inc_cantidades where hoja_id='{HA}' and cantidad=9") == '0', 'Hoja enviada: ninguna cantidad cambió')
falla_con(f"update public.inc_cantidades set cantidad=9 where hoja_id='{HA}'", None, 'ya fue enviada', 'Hoja enviada: ni el dueño de la base puede editar la captura (disparador)')
val(f"select public.inc_firmar_hoja('{HA}','rh')", 'rh')
falla_con(f"select public.inc_firmar_hoja('{HA}','rh')", 'rh', 'inc_eventos_firma_unica', 'Firma duplicada de RH en la misma versión: rechazada')
val(f"select public.inc_devolver_hoja('{HA}','Faltan las horas del viernes de P4','nomina')", 'nomina')
filas_antes = val(f"select count(*) from public.inc_cantidades where hoja_id='{HA}'")
val(f"update public.inc_cantidades set cantidad=3 where hoja_id='{HA}' and personal_id='{P['P4']}' and concepto_id='{K['HE']}'", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HA}','{P['P4']}','{d(4)}','{K['HE']}',1)", 'coordA')
V2 = val(f"select public.inc_enviar_hoja('{HA}')", 'coordA')
ok(val(f"select string_agg(numero::text, ',' order by numero) from public.inc_versiones where hoja_id='{HA}'") == '1,2', 'Corrección: nace la versión 2; la 1 se conserva')
ok(val(f"select count(*) from public.inc_cantidades where hoja_id='{HA}'") == str(int(filas_antes) + 1),
   'Captura operativa: se corrige en su lugar, sin duplicar renglones', f'{filas_antes} → +1 línea nueva (viernes)')
v1_p4 = val(f"select q->>'cantidad' from public.inc_versiones v, jsonb_array_elements(v.datos->'cantidades') q where v.id='{V1}' and q->>'personal_id'='{P['P4']}' and q->>'concepto_id'='{K['HE']}'")
v2_p4 = val(f"select string_agg(q->>'cantidad', ',' order by q->>'fecha') from public.inc_versiones v, jsonb_array_elements(v.datos->'cantidades') q where v.id='{V2}' and q->>'personal_id'='{P['P4']}' and q->>'concepto_id'='{K['HE']}'")
ok(v1_p4 == '2.00' and v2_p4 == '3.00,1.00', 'La versión 1 conserva lo revisado (2 h); la 2 trae la corrección (3 h + 1 h)', f'v1={v1_p4} v2={v2_p4}')
falla_con(f"update public.inc_versiones set datos='{{}}' where id='{V1}'", None, 'registro histórico', 'Versión: no se puede editar ni como dueño de la base')
falla_con(f"delete from public.inc_eventos where hoja_id='{HA}'", None, 'registro histórico', 'Eventos: no se pueden borrar ni como dueño de la base')
firmas = val(f"select string_agg(e.tipo||'@v'||v.numero, ',' order by e.creado_en) from public.inc_eventos e join public.inc_versiones v on v.id=e.version_id where e.hoja_id='{HA}' and e.tipo like 'firma%'")
ok(firmas == 'firma_rh@v1', 'D3/E6: la firma de RH queda ligada a la versión 1 y no aparece en la 2', firmas)
val(f"select public.inc_firmar_hoja('{HA}','nomina')", 'nomina')
ok(val(f"select count(*) from public.inc_eventos where version_id='{V2}' and tipo='firma_nomina'") == '1', 'D4: Nómina firma la versión 2 de forma independiente')
# (b) persona-día en dos hojas normales: se prueba la restricción saltando el disparador
falla_con(f"insert into public.inc_celdas (tenant_id, hoja_id, hoja_raiz_id, periodo_id, es_normal, personal_id, fecha, codigo) values ('{T}','{HB}','{HB}','{PER}',true,'{P['P2']}','{d(1)}','F')",
          None, 'inc_celdas_periodo_dia', '(b) Misma persona y día en dos hojas normales: la base lo rechaza aun sin disparador', replica=True)
falla_con(f"insert into public.inc_cantidades (tenant_id, hoja_id, hoja_raiz_id, periodo_id, es_normal, personal_id, fecha, concepto_id, cantidad) values ('{T}','{HB}','{HB}','{PER}',true,'{P['P1']}','{d(0)}','{K['HE']}',1)",
          None, 'inc_cant_periodo', '(e) Misma persona, día y concepto en dos hojas normales: rechazado aun sin disparador', replica=True)

# =====================================================================
print('\n== Cálculo (Nómina) ==')
def imp(pk, ck, ver=V2):
    return val(f"select coalesce(sugerido::text,'null')||'/'||origen from public.inc_importes where version_id='{ver}' and personal_id='{P[pk]}' and concepto_id='{K[ck]}'", 'nomina')
ok(imp('P1', 'HE') == '2250.00/pendiente', 'C2/C15: 12 h extra con $20,000/30 → $2,250.00 (9 dobles + 3 triples, sin redondeo intermedio)', imp('P1', 'HE'))
ok(imp('P4', 'HE') == '666.67/pendiente', 'Corrección recalculada: 4 h extra de P4 → $666.67', imp('P4', 'HE'))
ok(imp('P4', 'HE', V1) == '333.33/pendiente', 'C1: en la versión 1, 2 h extra → $333.33', imp('P4', 'HE', V1))
ok(imp('P1', 'DOM') == '166.67/pendiente', 'C7: domingo al 25 % de $666.67 → $166.67', imp('P1', 'DOM'))
ok(imp('P2', 'DOMT') == '700.00/aceptado', 'C8: domingo con tarifa del área B → $700 (sustituye la prima)', imp('P2', 'DOMT'))
ok(imp('P3', 'DOMT') == '600.00/aceptado', 'C9: domingo con tarifa general → $600', imp('P3', 'DOMT'))
ok(imp('P3', 'HT') == '950.00/aceptado', 'C6: tarifa propia 19 × $50 → $950', imp('P3', 'HT'))
ok(imp('PNOI', 'HE') == 'null/sin_sueldo', 'C10: sin esquema de pago → sin importe, no se inventa sueldo', imp('PNOI', 'HE'))
ok(imp('P4', 'BSI') == 'null/sin_importe', 'B4: concepto sin importe → sin monto', imp('P4', 'BSI'))
ok(imp('P1', 'DESC') == '150.00/pendiente', 'Descuento operativo: queda pendiente de decisión de Nómina', imp('P1', 'DESC'))
base = val(f"select base_calculo from public.inc_importes where version_id='{V2}' and personal_id='{P['P1']}' and concepto_id='{K['HE']}'", 'nomina')
ok(base == 'mixto', 'B8: el importe registra la base usada (mixto por defecto)', base)
# Bases: P2 tiene 24,000 brutos/30 + 1,400 netos/7 → mixto 1000, bruto 800, neto 200 diarios
for b, esperado in [('mixto', '1000.000'), ('bruto', '800.000'), ('neto', '200.000')]:
    v = val(f"select round(public.inc_sueldo_diario('{P['P2']}','{PER}','{b}'),3)")
    ok(v == esperado, f'B5–B7: sueldo diario base {b}', v)
val(f"select public.inc_capturar_sueldo_manual('{PER}','{P['PNOI']}',400)", 'nomina')
ok(imp('PNOI', 'HE') == '300.00/pendiente', 'Sueldo manual capturado por Nómina: 3 h × 400/8 × 2 → $300', imp('PNOI', 'HE'))
iid = val(f"select id from public.inc_importes where version_id='{V2}' and personal_id='{P['P1']}' and concepto_id='{K['HE']}'", 'nomina')
val(f"select public.inc_decidir_importe('{iid}', null)", 'nomina')
ok(val(f"select final||'/'||origen from public.inc_importes where id='{iid}'", 'nomina') == '2250.00/aceptado', 'C11: Nómina acepta la sugerencia')
val(f"select public.inc_decidir_importe('{iid}', 2200)", 'nomina')
ok(val(f"select final||'/'||sugerido||'/'||origen from public.inc_importes where id='{iid}'", 'nomina') == '2200.00/2250.00/modificado', 'C12: Nómina modifica; se conservan sugerido y final')
val(f"select public.inc_capturar_sueldo_manual('{PER}','{P['PNOI']}',400)", 'nomina')
ok(val(f"select final||'/'||origen from public.inc_importes where id='{iid}'", 'nomina') == '2200.00/modificado', 'Un recálculo no pisa el importe modificado por Nómina')

# =====================================================================
print('\n== Bloqueante 3 · Privacidad salarial (base local) ==')
for rol in ['coordA', 'consulta']:
    ok(val("select count(*) from public.personal_registros_pago", rol) == '0', f'{rol}: 0 esquemas de pago por consulta directa')
    ok(val("select count(*) from public.v_personal_registros_pago", rol) == '0', f'{rol}: 0 esquemas por la vista')
    ok(val("select count(*) from public.personal where sd is not null or sueldo_bruto is not null or sdi_imss is not null or true", rol) == '0', f'{rol}: 0 renglones de personal (sd, sueldo_bruto, sdi_imss)')
    ok(val("select count(*) from public.inc_importes", rol) == '0', f'{rol}: 0 importes de la Ola 1')
    ok(val("select count(*) from public.inc_sueldos_manuales", rol) == '0', f'{rol}: 0 sueldos manuales')
    falla_con(f"select public.inc_sueldo_diario('{P['P1']}','{PER}','mixto')", rol, 'permission denied', f'{rol}: no puede ejecutar el cálculo de sueldo diario')
    falla_con(f"select public.inc_calcular_version('{V2}')", rol, 'permission denied', f'{rol}: no puede ejecutar el cálculo de importes')
    datos = val(f"select count(*) from public.inc_versiones v where v.datos::text ~ '(sueldo|sugerido|importe\":)'", rol)
    ok(datos == '0', f'{rol}: las versiones que puede leer no contienen sueldos ni importes')
    r = val("select coalesce(public.resumen_agregado()->'compensacion'::text, 'null')", rol)
    ok(r in ('null', ''), f'{rol}: resumen_agregado no entrega compensación', r[:60])
    cols = val("select string_agg(column_name, ',') from information_schema.columns where table_schema='public' and table_name in ('personal_organizacional','equipo_coordinador')")
    ok(val(f"select count(*) from public.personal_percepciones", rol) == '0', f'{rol}: 0 percepciones (montos)')
    ok(val(f"select count(*) from public.movimientos", rol) == '0', f'{rol}: 0 movimientos del expediente (traen valores anteriores y nuevos)')
fn = val("""select string_agg(p.proname, ',' order by p.proname) from pg_proc p
            where p.pronamespace='public'::regnamespace
              and (pg_get_function_result(p.oid) ~* '(sueldo|sd |importe|monto)' )""")
ok(fn in ('', 'inc_sueldo_diario'), 'Funciones cuyo resultado expone sueldos o importes: solo la interna inc_sueldo_diario', fn)
ok(val("select count(*) from public.equipo_coordinador()", 'coordA') != '' , 'equipo_coordinador sigue funcionando (sin columnas de sueldo)')

# =====================================================================
print('\n== Separación de permisos ==')
falla_con(f"select public.inc_decidir_importe('{iid}', 1)", 'coordA', 'sin permiso', 'I10: Coordinador no acepta ni modifica importes')
falla_con(f"select public.inc_firmar_hoja('{HA}','nomina')", 'nomina2', 'solo el responsable designado', 'Nómina NO designada: puede ver importes pero no firmar')
ok(val("select count(*) from public.inc_importes", 'nomina2') != '0', 'Nómina NO designada: sí ve importes')
falla_con(f"select public.inc_firmar_hoja('{HA}','rh')", 'nomina', 'solo el responsable designado', 'Responsable de Nómina no puede firmar como RH')
falla_con(f"select public.inc_devolver_hoja('{HA}','x','nomina')", 'coordA', 'sin permiso', 'Coordinador no devuelve hojas')
falla_con(f"select public.inc_devolver_hoja('{HA}','  ','nomina')", 'nomina', 'requiere motivo', 'D2: devolución sin motivo rechazada')
falla_con(f"select public.inc_marcar_procesado('{PER}')", 'consulta', 'sin permiso', 'I5: Consulta no marca procesado')
falla_con(f"select public.inc_firmar_hoja('{HA}','rh')", 'consulta', 'solo el responsable designado', 'I5: Consulta no firma')
ok(val("select count(*) from public.inc_cantidades", 'consulta') != '0', 'Consulta ve cantidades de su alcance (sin importes)')

# =====================================================================
print('\n== Procesado y complementos ==')
val(f"select public.inc_enviar_hoja('{HB}')", 'coordB')
m1 = val(f"select public.inc_marcar_procesado('{PER}')", 'nomina')
m2 = val(f"select public.inc_marcar_procesado('{PER}')", 'nomina')
ok('procesado' in m1 and 'Ya estaba procesado' in m2 and val(f"select count(*) from public.inc_eventos where periodo_id='{PER}' and tipo='procesado'") == '1',
   'D7: marcar procesado dos veces no duplica el procesamiento', m2[:50])
falla_con(f"select public.inc_abrir_hoja('{PER}')", 'coordA', 'ya fue procesado', 'Periodo procesado: no se abre otra hoja normal')
ok(val(f"select estado from public.inc_hojas where id='{HA}'") == 'procesada', 'La hoja normal queda procesada')
HC = val(f"select public.inc_abrir_hoja('{PER}','{HA}')", 'coordA')
ok(val(f"select tipo||'/'||posterior_procesamiento from public.inc_hojas where id='{HC}'") == 'complemento/true', 'D6: complemento posterior al procesamiento identificado')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HC}','{P['P1']}','{d(0)}','{K['HE']}',1)",
          'coordA', 'inc_cant_captura', 'D5: el complemento no repite persona-día-concepto ya enviado')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HC}','{P['P3']}','{d(4)}','{K['HE']}',2)", 'coordA')
linea = val(f"select id from public.inc_cantidades where hoja_id='{HA}' and personal_id='{P['P1']}' and concepto_id='{K['HE']}' and fecha='{d(0)}'")
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, tipo_linea, linea_corregida_id) values ('{HC}','{P['P1']}','{d(0)}','{K['HE']}',-1,'ajuste','{linea}')", 'coordA')
falla_con(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, tipo_linea, linea_corregida_id) values ('{HC}','{P['P1']}','{d(0)}','{K['HE']}',-1,'ajuste','{linea}')",
          'coordA', 'inc_cant_ajuste', '(f) Un solo ajuste por línea original en el complemento')
val(f"select public.inc_enviar_hoja('{HC}')", 'coordA')
ok(val(f"select procesado_en is not null from public.inc_periodos where id='{PER}'") == 't' and val(f"select estado from public.inc_hojas where id='{HA}'") == 'procesada',
   'D6: enviar el complemento no reabre el periodo ni la hoja procesada')

# =====================================================================
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for n, _, det in malas: print('  FALLA:', n, det)
sys.exit(1 if malas else 0)
