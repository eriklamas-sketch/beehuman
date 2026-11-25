"""Excel canónico V1 (oficial) y reporte preliminar de acumulado: pruebas de base en una base LOCAL desechable (puerto 55432).
Datos ficticios (tenant «TENANT EXCEL»). Diseño: claude/Excel-canonico-V1-diseno-funcional-24nov.md.
Recalcula las huellas con una implementación independiente en Python (serialización §4.1) y las compara con el servidor.
Uso: DB=bh python3 pruebas_excel_canonico.py"""
import subprocess, json, sys, os, datetime, hashlib, unicodedata

DB = os.environ.get('DB', 'bh')
BASE = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
res = []
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
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T, T2 = 'e1000000-0000-4000-8000-000000000001', 'e1000000-0000-4000-8000-000000000002'
U = {k: f'e1100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta', 'otro'], 1)}
EA, EC = 'e1200000-0000-4000-8000-000000000001', 'e1200000-0000-4000-8000-000000000003'
SEM, IM, EF = 'e1300000-0000-4000-8000-000000000001', 'e1400000-0000-4000-8000-000000000001', 'e1400000-0000-4000-8000-000000000002'
RPAT = 'e1450000-0000-4000-8000-000000000001'
PRJ = 'e1500000-0000-4000-8000-000000000001'
HE, CAP, BONO, DESC, MAL = (f'e1600000-0000-4000-8000-00000000000{i}' for i in (1, 2, 3, 4, 5))
NOM = ['CA', 'CB', 'CC', 'X', 'Y', 'W', 'S', 'Z', 'Q', 'R']
P = {k: f'e1700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOM, 1)}
RL = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
EMP = {k: EA for k in NOM}; EMP.update({'CC': EC, 'R': EC})
COORD = {'X': 'CA', 'Y': 'CA', 'W': 'CA', 'S': 'CA', 'Z': 'CA', 'Q': 'CB', 'R': 'CC'}
NOMBRE = {k: f'PERSONA {k} EXCEL' for k in NOM}
NOMBRE['Z'] = '=SUMA(1;2) JOSÉ'                 # texto que empieza con «=» y una «é» descompuesta (NFD)
NUMINT = {k: f'N-{k}' for k in NOM}; NUMINT['W'] = None
L = datetime.date.fromisoformat(val("select (date_trunc('week', public.hoy_mx() + 7))::date")) + datetime.timedelta(days=7 * 60)
dd = lambda n, k=0: (L + datetime.timedelta(days=7 * n + k)).isoformat()

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT EXCEL'),('{T2}','TENANT EXCEL OTRO');
insert into auth.users (id, email) select v, k||'.xl@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA ÁNGEL EXCEL'),('{EC}','{T}','EMPRESA C EXCEL');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RPAT}','{EA}','{T}','Y1234567890');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS'),('{EF}','{T}','EFECTIVO');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ}','OBRA EXCEL','{T}');
"""
for k in NOM:
    co = f"'{P[COORD[k]]}'" if k in COORD else 'null'
    ni = f"'{NUMINT[k]}'" if NUMINT[k] else 'null'
    rp = f"'{RPAT}'" if k in ('X', 'Y') else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id, rfc, curp, nss) values "
             f"('{P[k]}','{T}','{EMP[k]}',{lit(NOMBRE[k])}::jsonb #>> '{{}}','XL-{k}',{co},'{PRJ}','RFC{k}0101AAA','CURP{k}0101HDFAAA01','1234567890{len(k)}');\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno, registro_patronal_id) values "
             f"('{RL[k]}','{T}','{P[k]}','{EMP[k]}','2025-01-01','vigente',{ni},{rp});\n")
RP = {}
for k, cl, su, mod in [('X', IM, 3500, 'bruto'), ('X', EF, 700, 'neto'), ('Y', IM, 2800, 'bruto'), ('W', IM, 2100, 'bruto'), ('Z', IM, 2100, 'bruto'),
                       ('Q', IM, 2100, 'bruto'), ('R', IM, 2100, 'bruto'), ('CA', IM, 7000, 'bruto'), ('CB', IM, 7000, 'bruto'), ('CC', IM, 7000, 'bruto')]:
    rid = f"e1800000-0000-4000-8000-{len(RP):012d}"; RP[f'{k}-{mod}'] = rid
    seed += (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
             f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{rid}','{T}','{P[k]}','{RL[k]}','{EMP[k]}','{cl}','{SEM}',{su},'{mod}',7,'2025-01-01',true);\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),
 ('{U['nomina']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),
 ('{U['consulta']}','{T}','consulta',null),('{U['otro']}','{T2}','nomina',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values
 ('{EA}','{T}','2025-01-01','{U['nomina']}','{U['admin']}'),('{EC}','{T}','2025-01-01','{U['nomina']}',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'XL' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{CAP}','{T}','{EA}','Capacitación','CAP','horas','otro','sin_importe',null,null,2),
 ('{BONO}','{T}','{EA}','Bono','BON','importe','otro','tarifa',1,null,3),
 ('{DESC}','{T}','{EA}','Descuento de herramienta','DES','importe','descuento','tarifa',1,null,4),
 ('{MAL}','{T}','{EC}','Viáticos','VIA','importe','otro','sin_importe',null,null,1);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
ok(val(f"select nombre_completo from public.personal where id='{P['Z']}'") == NOMBRE['Z'], '+S0 Semilla: el nombre de Z tiene la «é» descompuesta (NFD)')

def credito(datos):
    c = val(f"select public.cred_guardar(null, {lit(datos)}, null)", 'nomina')
    if val(f"select estado from public.cred_creditos where id='{c}'") != 'activo':
        val(f"select public.cred_cambiar_estado('{c}','activo','{dd(0)}','Alta XL')", 'nomina')
    return c
try:
    CR_X = credito({'personal_id': P['X'], 'tipo': 'fonacot', 'referencia': 'FON-X-001', 'relacion_laboral_id': RL['X'], 'fecha_inicio': dd(0),
                    'periodicidad_id': SEM, 'importe_periodo': 300, 'monto_total': 100000})
    TIPO_X = 'fonacot'
except RuntimeError as ex:
    print('   (FONACOT no se pudo crear con estos campos; se usa préstamo):', str(ex)[:120])
    CR_X = credito({'personal_id': P['X'], 'tipo': 'prestamo', 'referencia': 'PR-X-001', 'relacion_laboral_id': RL['X'], 'fecha_inicio': dd(0),
                    'periodicidad_id': SEM, 'importe_periodo': 300, 'monto_total': 100000}); TIPO_X = 'prestamo'
CR_Y = credito({'personal_id': P['Y'], 'tipo': 'infonavit', 'referencia': 'INF-Y-001', 'relacion_laboral_id': RL['Y'], 'fecha_inicio': '2025-01-01',
                'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 900})

semana = [0]
def periodo(emp=EA):
    semana[0] += 1; n = semana[0]
    return val(f"select public.inc_crear_periodo('{emp}','{SEM}','{dd(n)}','{dd(n, 6)}')", 'nomina'), n
def hoja_ea(per, n):
    H = val(f"select public.inc_abrir_hoja('{per}')", 'coordA')
    val(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H}','{P['X']}','{dd(n)}','F'),('{H}','{P['Y']}','{dd(n,3)}','V');
            insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values
              ('{H}','{P['X']}','{dd(n,1)}','{HE}',2),('{H}','{P['X']}','{dd(n,2)}','{CAP}',3),('{H}','{P['X']}','{dd(n,2)}','{BONO}',150),
              ('{H}','{P['W']}','{dd(n,1)}','{HE}',1),('{H}','{P['Z']}','{dd(n,1)}','{HE}',1.5),
              ('{H}','{P['S']}','{dd(n,1)}','{CAP}',2);
            insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, motivo) values ('{H}','{P['X']}','{dd(n,4)}','{DESC}',50,'Herramienta XL'),
              ('{H}','{P['S']}','{dd(n,4)}','{DESC}',30,'Herramienta S sin esquema');
            insert into public.inc_observaciones (hoja_id, personal_id, texto) values ('{H}','{P['X']}','Observación XL')""", 'coordA')
    return H, val(f"select public.inc_enviar_hoja('{H}')", 'coordA')
def exp(per, mod='canonica', user='nomina'): return json.loads(val(f"select public.inc_exportacion_{mod}('{per}')", user))
def conc(per): return json.loads(val(f"select public.inc_concentrado_periodo('{per}')", 'nomina'))
def estado_firma(per): return json.loads(val(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))
def firmar(per): return val(f"select public.inc_firmar_periodo('{per}','{estado_firma(per)['huella_actual']['total']}')", 'nomina')
def foto(per):
    c = conc(per)
    return (c['estado'], c['huella']['total'], c['firma']['estado'], val(f"select coalesce(procesado_en::text,'-') from public.inc_periodos where id='{per}'"),
            val(f"select md5(string_agg(h::text, '|' order by h.id)) from public.inc_hojas h where h.periodo_id='{per}'"),
            val(f"select count(*) from public.inc_eventos where periodo_id='{per}' and tipo <> 'exportacion'"),
            val("select public.inc_envios_pendientes()::text", 'nomina'), val("select count(*)||':'||md5(coalesce(string_agg(s::text,'|' order by evento_id),'')) from public.inc_envio_seguimiento s"))
def hoja(x, entidad): return next(h for h in x['hojas'] if h['entidad'] == entidad)
def cols(h): return [c['n'] for c in h['columnas']]
def filas_dict(h): n = cols(h); return [dict(zip(n, r)) for r in h['filas']]
def rsm(x): return {(r[0], r[1], r[2], r[3]): r[4] for r in x['resumen']['filas']}
def evs(per): return json.loads(val(f"select coalesce(jsonb_agg(huella order by creado_en),'[]') from public.inc_eventos where periodo_id='{per}' and tipo='exportacion'"))

# ---- Implementación independiente de la serialización (§4.1) ----
def linea(a): return '[' + ','.join(json.dumps(unicodedata.normalize('NFC', v) if isinstance(v, str) else v, ensure_ascii=False) for v in a) + ']'
def ser_datos(x, ref):
    ls = [linea([x['formato'], '1.0']), linea(['periodo', x['periodo_id'], ref])]
    for h in x['hojas']:
        keep = [i for i, c in enumerate(h['columnas']) if not c.get('ro')]
        ls += [linea(['#entidad', h['entidad']]), linea([h['columnas'][i]['n'] for i in keep])] + [linea([r[i] for i in keep]) for r in h['filas']]
    return hashlib.sha256(('\n'.join(ls) + '\n').encode('utf-8')).hexdigest()
def ser_archivo(x):
    ls = [linea([x['formato'], '1.0'])]
    for h in x['hojas']: ls += [linea(['#hoja', h['nombre']]), linea(cols(h))] + [linea(r) for r in h['filas']]
    return hashlib.sha256(('\n'.join(ls) + '\n').encode('utf-8')).hexdigest()

ORDEN_OF = ['Personas', 'Esquemas', 'Incidencias', 'Cantidades', 'Importes', 'Descuentos', 'Movimientos', 'Catálogos']
COLS = {
 'Personas': 'numero_interno nombre_completo rfc curp nss registro_patronal fecha_ingreso fecha_baja alta_en_periodo baja_en_periodo dias_vigentes relaciones_en_periodo esquemas_en_periodo proyecto coordinadores con_incidencias persona_id relacion_laboral_id',
 'Esquemas': 'numero_interno nombre_completo clasificacion modalidad sueldo dias_periodo fecha_inicio fecha_fin activo registro_patronal persona_id registro_pago_id relacion_laboral_id',
 'Incidencias': 'numero_interno nombre_completo fecha codigo codigo_nombre proyecto centro_costo hoja_tipo version_hoja persona_id hoja_id periodo_origen_id',
 'Cantidades': 'numero_interno nombre_completo fecha concepto_clave unidad cantidad tipo_linea hoja_tipo version_hoja persona_id concepto_id hoja_id periodo_origen_id',
 'Importes': 'numero_interno nombre_completo concepto_clave naturaleza clasificacion modalidad importe hoja_tipo version_hoja persona_id concepto_id hoja_id relacion_laboral_id registro_pago_id periodo_origen_id',
 'Descuentos': 'clase numero_interno nombre_completo tipo_credito etiqueta referencia_credito importe infonavit_tipo infonavit_valor pension_forma pension_valor persona_id credito_id descuento_id',
 'Movimientos': 'numero_interno nombre_completo tipo fecha_efectiva causa persona_id evento_id',
 'Catálogos': 'catalogo clave_beehuman abreviatura nombre tipo unidad modo naturaleza sistema_externo clave_externa'}

# ======================================================================
print('== P · Reporte preliminar ==')
P1, n1 = periodo()
H1, V1 = hoja_ea(P1, n1)
HB = val(f"select public.inc_abrir_hoja('{P1}')", 'coordB')           # hoja de CB en borrador: faltante
val(f"select public.cred_descuentos_periodo('{P1}')", 'nomina')
f0 = foto(P1)
ok(f0[0] == 'preliminar' and f0[2] == 'sin_firma', '+P0 Periodo en preliminar y sin firma', f'{f0[0]} {f0[2]}')
pr = exp(P1, 'preliminar')
ok(pr['formato'] == 'beehuman.preliminar' and pr['nombre_archivo'].startswith('PRELIMINAR_BeeHuman_EMPRESA-ANGEL-EXCEL_') and pr['huella_archivo'] is None,
   'CA19/CA22 Preliminar sin firma: se genera, formato beehuman.preliminar, nombre PRELIMINAR_…, sin huella_archivo', pr['nombre_archivo'])
ok([h['nombre'] for h in pr['hojas']] == ['PRELIM ' + n for n in ORDEN_OF] and pr['resumen']['nombre'] == 'PRELIM Resumen' and pr['validaciones']['nombre'] == 'PRELIM Faltantes',
   'CA22 Hojas con prefijo «PRELIM » y hoja final «PRELIM Faltantes»')
r0 = pr['resumen']['filas'][0]
ok(r0[0] == 'aviso' and 'PRELIMINAR — NO AUTORIZADO' in r0[4], 'CA22 Primera fila del Resumen: aviso «PRELIMINAR — NO AUTORIZADO»', r0[4][:40])
rp = rsm(pr)
ok(('firma', 'huella_firma', None, None) not in rp and rp[('firma', 'huella_concentrado_actual', None, None)] == f0[1] and rp[('firma', 'firma_estado', None, None)] == 'sin_firma',
   'P1 Resumen preliminar: sin huella_firma; huella_concentrado_actual = huella actual; firma_estado informativo')
imp = filas_dict(hoja(pr, 'Importes'))
pend = [x for x in imp if x['estado'] == 'por_decidir']
ok(cols(hoja(pr, 'Importes'))[-3:] == ['estado', 'motivo_pendiente', 'importe_sugerido'] and pend and all(x['importe'] is None and x['motivo_pendiente'] for x in pend)
   and any(x['importe_sugerido'] for x in pend), 'CA23 Importes por decidir: importe vacío, estado, motivo e importe sugerido', f'{len(pend)} por decidir')
des = filas_dict(hoja(pr, 'Descuentos'))
ok(any(x['clase'] == 'descuento' and x['estado'] == 'por_decidir' and x['importe'] is None and x['importe_sugerido'] == '300.00' for x in des),
   'CA23 Descuento pendiente: importe vacío, estado y sugerido 300.00')
ok(rp[('conteo', 'importes_por_decidir', None, None)] == str(len(pend)) and not any(k[0] == 'total_importes' for k in rp),
   'CA23 Lo por decidir no se suma: sin totales de importes mientras nada está decidido')
falt = filas_dict(pr['validaciones'])
tipos = {x['tipo'] for x in falt}
ok({'hoja', 'importe', 'descuento', 'firma'} <= tipos, 'P2 Faltantes: hoja sin enviar, importes, descuentos y firma (tipos del concentrado)', str(sorted(tipos)))
ok(all(x['persona_id'] and x['nombre_completo'] for x in falt if x['tipo'] in ('importe', 'descuento', 'hoja'))
   and all(x['persona_id'] is None for x in falt if x['tipo'] == 'firma' and 'Nómina del periodo' in x['mensaje'])
   and any(x['tipo'] == 'importe' and x['persona_id'] == P['X'] and x['numero_interno'] == 'N-X' for x in falt),
   '25N-F Faltantes con nombre, persona_id y número interno (la firma de Nómina del periodo, sin persona)')
fx = [x['mensaje'] for x in falt if x['tipo'] == 'importe' and x['persona_id'] == P['X'] and 'Horas extra' in x['mensaje']]
ok(len(fx) == 2 and len(set(fx)) == 2 and any('IMSS / bruto' in m for m in fx) and any('EFECTIVO / neto' in m for m in fx),
   '25N-F2 Dos importes de la misma persona y concepto se distinguen por esquema (IMSS / bruto y EFECTIVO / neto)', ' | '.join(fx))
ok(len([x for x in falt if x['tipo'] == 'importe']) == len(pend), '25N-F2 Un faltante de importe por línea por decidir (mismo número que el concentrado)')
ok(cols(pr['validaciones']) == ['tipo', 'codigo', 'numero_interno', 'nombre_completo', 'persona_id', 'referencia_id', 'mensaje'], '25N-F Columnas de PRELIM Faltantes')
ok(any(x['tipo'] == 'hoja' and 'PERSONA CB EXCEL' in (x['mensaje'] or '') for x in falt), '+P2b El faltante de hoja nombra al coordinador con la hoja pendiente', str([x['mensaje'] for x in falt if x['tipo'] == 'hoja']))
ok('B08' in error_de(f"select public.inc_exportacion_canonica('{P1}')", 'nomina'), 'CA2 Oficial en preliminar → B08')
ok(foto(P1) == f0, 'CA12 Preliminar no cambia firma, huella, estado, hojas, eventos ni la bandeja B6')
e1 = evs(P1)
ok(len(e1) == 1 and e1[0]['modalidad'] == 'preliminar' and e1[0]['huella_concentrado'] == f0[1] and e1[0]['huella_datos_exportados'] == pr['huella_datos_exportados']
   and 'huella_firma' not in e1[0] and 'huella_archivo' not in e1[0] and e1[0]['exportacion_numero'] == 1,
   'CA25 Evento preliminar: modalidad, huella_concentrado y huella_datos_exportados; sin huella_firma ni huella_archivo')
ok(set(e1[0].keys()) <= {'modalidad', 'formato', 'version_formato', 'estado_periodo', 'firma_estado', 'huella_concentrado', 'huella_datos_exportados', 'exportacion_numero', 'filas', 'por_decidir'}
   and 'RFC' not in json.dumps(e1[0]), 'P3 El evento no guarda RFC, CURP, NSS ni nombres')
pr2 = exp(P1, 'preliminar')
ok(pr2['huella_datos_exportados'] == pr['huella_datos_exportados'] and pr2['exportacion_numero'] == 2, 'CA26 Dos preliminares sin cambios: misma huella; número 2')
pr_d = dict(pr, periodo_id=P1)
ok(ser_datos(pr_d, f0[1]) == pr['huella_datos_exportados'], 'P4 huella_datos_exportados del preliminar reproducida con otra implementación (Python)')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HB}','{P['Q']}','{dd(n1,2)}','{HE}',1)", 'coordB')
VB = val(f"select public.inc_enviar_hoja('{HB}')", 'coordB')
pr3 = exp(P1, 'preliminar')
ok(pr3['huella_datos_exportados'] != pr['huella_datos_exportados'], 'CA26 Después de que un coordinador envía una hoja, la huella del preliminar cambia')
for u in ('coordA', 'consulta'):
    ok('sin permiso' in error_de(f"select public.inc_exportacion_preliminar('{P1}')", u) and 'sin permiso' in error_de(f"select public.inc_exportacion_canonica('{P1}')", u),
       f'CA13/BP1/B05 {u}: no exporta ninguna modalidad')
ok(all('permission denied' in error_de(f"select public.inc_exportacion_{m}('{P1}')", anon=True) for m in ('preliminar', 'canonica')), 'CA13 anon: sin acceso')
ok(all('no encontrado' in error_de(f"select public.inc_exportacion_{m}('{P1}')", 'otro') for m in ('preliminar', 'canonica')), 'CA13 Otro tenant: «periodo no encontrado»')
ok(all('permission denied' in error_de(q, 'nomina') for q in (f"select public.inc__exportacion_datos('{P1}','oficial')", "select public.inc__exportacion_registrar('{}'::jsonb)",
       "select public.inc__exp_linea('[]')")), 'CA13 Funciones internas no expuestas a authenticated')

print('== R · Firma vigente con RH pendiente ==')
for V in (V1, VB): val(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
for iid in val(f"select coalesce(string_agg(id::text, ' '), '') from public.inc_importes where version_id='{V1}' and origen='por_asignar'").split():
    val(f"select public.inc_asignar_esquema('{iid}','{RP['X-bruto']}','Esquema XL')", 'nomina')
    val(f"select public.inc_decidir_importe('{iid}', null)", 'nomina')
val(f"select public.cred_aceptar_descuentos('{P1}')", 'nomina')
imp_x = val(f"select id from public.inc_importes where version_id='{V1}' and concepto_id='{HE}' and personal_id='{P['W']}' limit 1")
val(f"select public.inc_decidir_importe('{imp_x}', 0, 'Prueba de cero XL')", 'nomina')       # importe decidido en 0
ok(firmar(P1) == 'Firma de Nómina del periodo registrada.', '+R0 Nómina firma el periodo')
c1 = conc(P1)
ok(c1['estado'] == 'preliminar' and c1['firma']['estado'] == 'vigente', '+R1 Firma vigente y RH pendiente: sigue en preliminar', str([x['tipo'] for x in c1['faltantes']]))
ok('B08' in error_de(f"select public.inc_exportacion_canonica('{P1}')", 'nomina'), 'CA20 Oficial con firma vigente y RH pendiente → B08')
pr4 = exp(P1, 'preliminar')
ok(rsm(pr4)[('firma', 'firma_estado', None, None)] == 'vigente' and any(x['tipo'] == 'firma' for x in filas_dict(pr4['validaciones'])),
   'CA20 Preliminar disponible; informa la firma vigente y lista la firma de RH pendiente')

print('== O · Excel oficial ==')
for H in (H1, HB): val(f"select public.inc_firmar_hoja('{H}','rh')", 'admin')
ok(conc(P1)['estado'] == 'listo', '+O0 Con las firmas de RH el periodo queda listo')
ok('BP2' in error_de(f"select public.inc_exportacion_preliminar('{P1}')", 'nomina'), 'CA21 Preliminar en listo → BP2 (remite al oficial)')
fo = foto(P1)
of = exp(P1)
ok(of['formato'] == 'beehuman.canonico' and of['nombre_archivo'] == 'BeeHuman_EMPRESA-ANGEL-EXCEL_' + dd(n1) + '_' + dd(n1, 6) + '_exp-1.xlsx',
   'CA1 Oficial en listo: formato beehuman.canonico y nombre BeeHuman_…_exp-1.xlsx', of['nombre_archivo'])
ok([h['nombre'] for h in of['hojas']] == ORDEN_OF and of['resumen']['nombre'] == 'Resumen' and of['validaciones']['nombre'] == 'Validaciones'
   and all(cols(hoja(of, 'Catalogos' if n == 'Catálogos' else n)) == COLS[n].split() for n in ORDEN_OF),
   'CA1 Las 10 hojas en orden, con las columnas exactas del diseño')
ro = rsm(of)
ok(ro[('firma', 'huella_concentrado', None, None)] == ro[('firma', 'huella_firma', None, None)] == fo[1] and ro[('periodo', 'estado', None, None)] == 'listo',
   'CA4 huella_concentrado = huella_firma = huella actual', fo[1][:16])
of_d = dict(of, periodo_id=P1)
ok(ser_archivo(of) == of['huella_archivo'] and ser_datos(of_d, fo[1]) == of['huella_datos_exportados'],
   'CA11/CA15 huella_archivo y huella_datos_exportados reproducidas con otra implementación (serialización determinista)')
per_f = filas_dict(hoja(of, 'Personas')); byp = {x['persona_id']: x for x in per_f}
ok(byp[P['Z']]['nombre_completo'] == unicodedata.normalize('NFC', NOMBRE['Z']) and byp[P['Z']]['nombre_completo'].startswith('='),
   'CA17 Texto que empieza con «=» se entrega como texto, normalizado a NFC', byp[P['Z']]['nombre_completo'])
ok(byp[P['X']]['rfc'] == 'RFCX0101AAA' and byp[P['X']]['numero_interno'] == 'N-X' and byp[P['X']]['registro_patronal'] == 'Y1234567890'
   and byp[P['X']]['fecha_ingreso'] == '2025-01-01' and byp[P['X']]['relacion_laboral_id'] == RL['X'] and byp[P['X']]['esquemas_en_periodo'] == '2',
   'V-1 Relación principal: número interno, registro patronal, fecha de ingreso y relación (regla rel_pri)')
ok(all(byp[p]['numero_interno'] == (next(y for y in c1['personas'] if y['personal_id'] == p)['numero_interno']) for p in byp), '+V-1b numero_interno igual al del concentrado para todas las personas')
esq = filas_dict(hoja(of, 'Esquemas'))
ok(len([x for x in esq if x['persona_id'] == P['X']]) == 2 and len([x for x in per_f if x['persona_id'] == P['X']]) == 1,
   'CA9 Persona con 2 esquemas: 1 fila en Personas y 2 en Esquemas')
ok(any(x['persona_id'] == P['W'] and x['registro_patronal'] is None for x in esq), 'CA15 Esquema sin registro patronal: vacío (null), no cero')
imp_o = filas_dict(hoja(of, 'Importes'))
hx = [x for x in imp_o if x['persona_id'] == P['X'] and x['concepto_id'] == HE]
ok(sorted(x['modalidad'] for x in hx) == ['bruto', 'neto'] and len({x['registro_pago_id'] for x in hx}) == 2, 'CA9 Una línea de importe por esquema (bruto y neto)')
ok(any(x['persona_id'] == P['W'] and x['importe'] == '0.00' for x in imp_o), 'CA15 Importe decidido en 0 = «0.00» (distinto de vacío)')
ok(all(x['importe'] is not None for x in imp_o) and 'estado' not in cols(hoja(of, 'Importes')), '+O1 El oficial solo trae importes decididos, sin columnas de estado')
ok(any(x['concepto_id'] == DESC and x['naturaleza'] == 'deduccion' for x in imp_o) and any(x['concepto_id'] == BONO and x['naturaleza'] == 'percepcion' for x in imp_o),
   'O2 Concepto de descuento = deducción; bono = percepción')
can = filas_dict(hoja(of, 'Cantidades'))
ok({x['concepto_id'] for x in can} == {HE, CAP} and 'importe' not in cols(hoja(of, 'Cantidades')), 'CA7 Cantidades sin dinero: sin BON ni DES (unidad importe) y sin columna de importe')
ok(not any(c in cols(hoja(of, 'Importes')) for c in ('cantidad',)), 'CA7 Importes sin cantidades')
mods = {}
for x in imp_o: mods.setdefault((x['concepto_id'], x['modalidad'] or 'sin_modalidad'), 0); mods[(x['concepto_id'], x['modalidad'] or 'sin_modalidad')] += float(x['importe'])
tot = {(k[2], k[3]): float(v) for k, v in ro.items() if k[0] == 'total_importes'}
ok(all(abs(mods[k] - tot[k]) < 0.005 for k in tot) and set(mods) == set(tot), 'CA5/CA6 Total de importes por concepto y modalidad (bruto y neto separados) igual al concentrado')
desc_o = filas_dict(hoja(of, 'Descuentos'))
ok(len([x for x in desc_o if x['clase'] == 'descuento' and x['credito_id'] == CR_X]) == 1 and len([x for x in desc_o if x['clase'] == 'informativo' and x['credito_id'] == CR_Y]) == 1
   and next(x for x in desc_o if x['credito_id'] == CR_Y)['importe'] is None and next(x for x in desc_o if x['credito_id'] == CR_X)['referencia_credito'].endswith('X-001'),
   f'CA10 {TIPO_X.upper()} = 1 fila descuento con referencia; INFONAVIT = 1 fila informativa sin importe')
def llaves_unicas(x):
    for h, k in (('Personas', ['persona_id']), ('Esquemas', ['registro_pago_id']), ('Incidencias', ['persona_id', 'fecha', 'hoja_id']),
                 ('Cantidades', ['hoja_id', 'persona_id', 'fecha', 'concepto_id', 'tipo_linea']),
                 ('Importes', ['persona_id', 'hoja_id', 'concepto_id', 'relacion_laboral_id', 'registro_pago_id']),
                 ('Descuentos', ['clase', 'descuento_id', 'credito_id']), ('Movimientos', ['evento_id']), ('Catalogos', ['catalogo', 'clave_beehuman'])):
        fs = filas_dict(hoja(x, h)); ks = [tuple(f[c] for c in k) for f in fs]
        if len(ks) != len(set(ks)): return h
    return None
ok(llaves_unicas(of) is None, 'CA10 Ninguna llave se repite en ninguna hoja', str(llaves_unicas(of)))
cat = filas_dict(hoja(of, 'Catalogos'))
ok(all(x['clave_externa'] is None and x['sistema_externo'] is None for x in cat) and {'concepto', 'codigo_dia', 'tipo_credito', 'clasificacion'} <= {x['catalogo'] for x in cat},
   'CA14 Catálogos con los valores usados y clave_externa vacía')
val_o = filas_dict(of['validaciones'])
cod = {x['codigo'] for x in val_o}
b07 = next(x for x in val_o if x['codigo'] == 'B07')
ok(all(x['resultado'] == 'superada' for x in val_o if x['nivel'] == 'bloqueo' and x['codigo'] != 'B07') and {f'B0{i}' for i in range(1, 9)} <= cod
   and b07['resultado'] == 'no_aplica' and b07['mensaje'] == 'No aplica: el periodo aún no ha sido procesado.',
   'O3 Validaciones en listo: B01–B08 superadas, salvo B07 «no_aplica: el periodo aún no ha sido procesado»')
a05 = [x for x in val_o if x['codigo'] == 'A05' and x['persona_id'] == P['W']]
ok(a05 and a05[0]['mensaje'].startswith('PERSONA W EXCEL — sin número interno') and a05[0]['nombre_completo'] == 'PERSONA W EXCEL', '25N-A05 A05 con el nombre de la persona', a05 and a05[0]['mensaje'])
a07 = [x for x in val_o if x['codigo'] == 'A07']
ok(a07 and all('sin esquema' not in x['mensaje'] for x in a07 if x['persona_id'] in (P['X'], P['S']))
   and any(x['persona_id'] == P['X'] and 'esquema neto' in x['mensaje'] for x in a07)
   and not any(x['persona_id'] == P['S'] for x in a07), '25N-A07 A07 solo por percepciones fuera de bruto; la deducción sin esquema no es A07', str([x['mensaje'] for x in a07]))
ok(any(x['codigo'] == 'A11' and x['persona_id'] == P['S'] and '0 esquemas fiscales' in x['mensaje'] for x in val_o)
   and not any(x['codigo'] == 'A11' and x['persona_id'] == P['X'] for x in val_o),
   '25N-A11 Deducción sin esquema: A11 si la persona no tiene exactamente un esquema bruto (S: 0); X (1 bruto): sin aviso')
niv = [x['nivel'] for x in val_o]
ok(niv[-8:] == ['bloqueo'] * 8 and 'bloqueo' not in niv[:-8] and niv.index('informativo') > max(i for i, n in enumerate(niv) if n == 'advertencia'),
   '25N-V Validaciones: advertencias, informativos y al final los 8 bloqueos superados')
ok(all(x['nombre_completo'] == byp[x['persona_id']]['nombre_completo'] for x in val_o if x['persona_id']), '25N-V Validaciones con nombre_completo de la persona')
ok({'A05', 'A06', 'A07', 'A08', 'A02', 'I01', 'I02'} <= cod, 'O4 Advertencias A02, A05, A06, A07, A08 e informativos I01, I02', str(sorted(cod)))
ok(foto(P1) == fo, 'CA12 Exportar el oficial no cambia firma, huella, estado, hojas, eventos ni B6')
of2 = exp(P1)
ok(of2['huella_datos_exportados'] == of['huella_datos_exportados'] and of2['huella_archivo'] == of['huella_archivo'] and of2['exportacion_numero'] == 2
   and of2['huella_datos_exportados_anterior'] == of['huella_datos_exportados'], 'CA11 Misma firma y mismos datos: mismas huellas; número 2 y huella anterior')
val(f"update public.personal set rfc = 'RFCX0101BBB' where id = '{P['X']}'", replica=True)
of3 = exp(P1)
ok(estado_firma(P1)['estado'] == 'vigente' and of3['huella_datos_exportados'] != of['huella_datos_exportados'] and of3['huella_archivo'] != of['huella_archivo']
   and of3['exportacion_numero'] == 3 and rsm(of3)[('firma', 'huella_firma', None, None)] == fo[1],
   'CA11 Cambia solo el RFC: la firma sigue vigente, cambian las dos huellas de datos y sube el número')
ev = [x for x in evs(P1) if x['modalidad'] == 'oficial']
ok(len(ev) == 3 and all(x['huella_firma'] == fo[1] and x.get('huella_archivo') and x['version_formato'] == '1.0' for x in ev) and len([x for x in evs(P1) if x['modalidad'] == 'preliminar']) == 4,
   'O5 Eventos: 3 oficiales con huella_firma y huella_archivo; los 4 preliminares contados aparte')

print('== C · Ciclo: cambio material → preliminar → nueva firma (CA3) ==')
val(f"update public.personal_registros_pago set sueldo = 3600 where id = '{RP['X-bruto']}'", replica=True)
c2 = conc(P1)
ok(c2['firma']['estado'] == 'invalidada' and c2['estado'] == 'preliminar', 'CA3 Cambio material: la firma se invalida y el periodo vuelve a preliminar')
ok('B08' in error_de(f"select public.inc_exportacion_canonica('{P1}')", 'nomina') and exp(P1, 'preliminar')['formato'] == 'beehuman.preliminar',
   'CA3 Oficial bloqueado (B08) y preliminar disponible')
firmar(P1)
of4 = exp(P1)
ok(of4['huella_datos_exportados'] != of3['huella_datos_exportados'] and rsm(of4)[('firma', 'huella_firma', None, None)] != fo[1] and of4['exportacion_numero'] == 1,
   'CA3 Nueva firma: el oficial vuelve a funcionar con huellas nuevas (número 1 de la nueva firma)')

print('== K · Complementos y procesado ==')
C1 = val(f"select public.inc_abrir_hoja('{P1}','{H1}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{C1}','{P['Y']}','{dd(n1,4)}','{HE}',1)", 'coordA')
VC1 = val(f"select public.inc_enviar_hoja('{C1}')", 'coordA'); val(f"select public.inc_aceptar_sugeridos('{VC1}')", 'nomina')
val(f"select public.inc_firmar_hoja('{C1}','rh')", 'admin'); firmar(P1)
of5 = exp(P1)
ok(any(x['hoja_id'] == C1 and x['hoja_tipo'] == 'complemento' for x in filas_dict(hoja(of5, 'Cantidades'))), 'CA8 Complemento anterior al procesamiento: incluido')
ok(val(f"select public.inc_marcar_procesado('{P1}')", 'nomina') == 'Periodo marcado como procesado.', '+K0 Periodo procesado')
C2 = val(f"select public.inc_abrir_hoja('{P1}','{H1}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{C2}','{P['Y']}','{dd(n1,5)}','{HE}',2)", 'coordA')
val(f"select public.inc_enviar_hoja('{C2}')", 'coordA')
of6 = exp(P1)
ok(rsm(of6)[('periodo', 'estado', None, None)] == 'procesado' and not any(x['hoja_id'] == C2 for x in filas_dict(hoja(of6, 'Cantidades')))
   and any(x['codigo'] == 'A01' and x['referencia_id'] == C2 for x in filas_dict(of6['validaciones'])),
   'CA8 Procesado con complemento posterior: oficial disponible, sin sus líneas y con A01')
ok('BP2' in error_de(f"select public.inc_exportacion_preliminar('{P1}')", 'nomina'), 'BP2 Preliminar en procesado → BP2')
b07p = next(x for x in filas_dict(of6['validaciones']) if x['codigo'] == 'B07')
ok(b07p['resultado'] == 'superada' and b07p['mensaje'] == 'Sin cambios después del procesamiento.', 'O3b Validaciones en procesado: B07 superada «Sin cambios después del procesamiento.»')
val(f"update public.personal_registros_pago set sueldo = 3700 where id = '{RP['X-bruto']}'", replica=True)
ok('B07' in error_de(f"select public.inc_exportacion_canonica('{P1}')", 'nomina'), 'CA18 Procesado que cambió después → B07')
ok('BP2' in error_de(f"select public.inc_exportacion_preliminar('{P1}')", 'nomina') and 'después cambió' in error_de(f"select public.inc_exportacion_preliminar('{P1}')", 'nomina'),
   'CA18 Preliminar tampoco disponible (BP2, mensaje de cambio posterior)')

print('== L · Procesado con la regla anterior (sin firma de periodo) → B01 ==')
P2, n2 = periodo()
H2, V2 = hoja_ea(P2, n2)
val(f"""update public.inc_periodos set procesado_en = now(), procesado_por = '{U['nomina']}' where id = '{P2}';
        update public.inc_hojas set estado = 'procesada' where id = '{H2}';
        insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre) values ('{T}','{P2}','procesado','{U['nomina']}','legado')""", replica=True)
ok('B01' in error_de(f"select public.inc_exportacion_canonica('{P2}')", 'nomina'), 'CA2/B01 Periodo procesado sin firma de periodo (regla anterior) → B01')
ok('BP2' in error_de(f"select public.inc_exportacion_preliminar('{P2}')", 'nomina'), '+L1 …y el preliminar → BP2')

print('== V · Concepto «importe» + «sin importe» (V-3) → B06 en el oficial; aviso en el preliminar ==')
P3, n3 = periodo(EC)
val(f"update public.usuarios_tenant set personal_id = '{P['CC']}' where user_id = '{U['coordB']}'", replica=True)
H3 = val(f"select public.inc_abrir_hoja('{P3}')", 'coordB')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H3}','{P['R']}','{dd(n3,1)}','{MAL}',420)", 'coordB')
V3 = val(f"select public.inc_enviar_hoja('{H3}')", 'coordB')
pr5 = exp(P3, 'preliminar')
ok(any(x['tipo'] == 'configuracion' and 'Viáticos' in x['mensaje'] for x in filas_dict(pr5['validaciones'])), 'V-3 Preliminar: lo lista en Faltantes como «configuracion»')
val(f"select public.cred_descuentos_periodo('{P3}')", 'nomina'); val(f"select public.cred_aceptar_descuentos('{P3}')", 'nomina'); firmar(P3)
ok(conc(P3)['estado'] == 'listo' and 'B06' in error_de(f"select public.inc_exportacion_canonica('{P3}')", 'nomina'), 'V-3 Oficial bloqueado con B06 (su dinero no llegaría al archivo)')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, d_ in malas: print('  FALLA:', nn, d_)
sys.exit(1 if malas else 0)
