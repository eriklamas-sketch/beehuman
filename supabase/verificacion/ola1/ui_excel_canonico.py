"""Excel canónico V1 y reporte preliminar · pantalla del Concentrado (datos ficticios, base local bhui; con PGRST=1 contra PostgREST local).
Semilla propia (tenant «TENANT UI XL»). Descarga los archivos reales que arma la pantalla con ExcelJS y los abre con openpyxl.
  X1  En «preliminar»: solo «Descargar reporte preliminar» (+ texto de B08); nunca los dos botones.
  X2  Archivo preliminar: nombre PRELIMINAR_…, hojas «PRELIM …», aviso en la primera fila del Resumen, encabezado de impresión y propiedades.
  X3  Importes por decidir con importe vacío, estado y sugerido; lo por decidir no se suma.
  X4  En «listo»: solo «Exportar Excel oficial».
  X5  Archivo oficial: 10 hojas en orden, encabezados = contrato del servidor, nota en cada encabezado.
  X6  Tipos de celda: texto explícito (también «=…»), fecha de Excel dd/mm/yyyy, importe #,##0.00, booleano, ids como texto, vacío ≠ cero.
  X7  Celdas = filas del servidor (huella_archivo recalculada en Python sobre lo leído del .xlsx) y totales de Importes = Resumen.
  X8  B06 en pantalla: si el contenido no coincide con huella_archivo, no se descarga nada.
  X9  Procesado que cambió después: explicación B07 y botón deshabilitado.
  X10 Eventos: una exportación por descarga, con su modalidad; firma, huella y estado intactos.
  X11 500 personas: de clic a archivo descargado (CA16) · X12 sin errores de JavaScript · RED: nada sale a internet.
Uso: [PGRST=1] SUPABASE_JS=<supabase.js umd> EXCELJS=<exceljs.min.js> python3 ui_excel_canonico.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64, subprocess, datetime, hmac, hashlib, unicodedata
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
import openpyxl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']; EXCELJS = os.environ['EXCELJS']; REF = 'sflvpgkmtaxzogpgetxn'
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', RL.DB]
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    if err: raise RuntimeError(err)
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET') and not l.startswith('{"sub"')]; return out[-1] if out else ''
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T = 'e3000000-0000-4000-8000-000000000001'
U = {k: f'e3100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA', 'coordG'], 1)}
RL.U.update(U)
EA, EG = 'e3200000-0000-4000-8000-000000000001', 'e3200000-0000-4000-8000-000000000002'
SEM, IM, EF, PRJ = ('e3300000-0000-4000-8000-000000000001', 'e3400000-0000-4000-8000-000000000001',
                    'e3400000-0000-4000-8000-000000000002', 'e3500000-0000-4000-8000-000000000001')
HE, BONO, HEG = 'e3600000-0000-4000-8000-000000000001', 'e3600000-0000-4000-8000-000000000002', 'e3600000-0000-4000-8000-000000000003'
NOM = ['CA', 'CG', 'X', 'Y', 'Z']
P = {k: f'e3700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOM, 1)}
RLB = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
EMP = {'CA': EA, 'CG': EG, 'X': EA, 'Y': EA, 'Z': EA}; COORD = {'X': 'CA', 'Y': 'CA', 'Z': 'CA'}
NOMBRE = {k: f'PERSONA {k} UI XL' for k in NOM}; NOMBRE['Z'] = '=HOLA()+1 JOSÉ'
N500 = 500
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui.'); sys.exit(1)
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT UI XL');
insert into auth.users (id, email) select v, k||'-xl@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA ÁGUILA UI XL'),('{EG}','{T}','EMPRESA GRANDE UI XL');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS'),('{EF}','{T}','EFECTIVO');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ}','OBRA UI XL','{T}');
"""
for k in NOM:
    co = f"'{P[COORD[k]]}'" if k in COORD else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id, rfc) values "
             f"('{P[k]}','{T}','{EMP[k]}',{lit(NOMBRE[k])}::jsonb #>> '{{}}','UXL-{k}',{co},'{PRJ}','RFC{k}0101XXX');\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values "
             f"('{RLB[k]}','{T}','{P[k]}','{EMP[k]}','2025-01-01','vigente','{'00' + str(len(k)) if k != 'Y' else '0042'}');\n"
             f"insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
             f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{T}','{P[k]}','{RLB[k]}','{EMP[k]}','{IM}','{SEM}',3500,'bruto',7,'2025-01-01',true);\n")
seed += (f"insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
         f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{T}','{P['X']}','{RLB['X']}','{EA}','{EF}','{SEM}',700,'neto',7,'2025-01-01',true);\n")
# 500 personas en la empresa grande, todas con el coordinador CG (CA16).
seed += f"""
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id, rfc, curp, nss)
  select ('e3800000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{T}', '{EG}', 'PERSONA GRANDE ' || g, 'UXLG-' || g, '{P['CG']}', '{PRJ}',
         'RFCG' || lpad(g::text, 6, '0') || 'XX', 'CURPG' || lpad(g::text, 6, '0') || 'HDFXXX01', lpad(g::text, 11, '0')
  from generate_series(1, {N500}) g;
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno)
  select ('e3900000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{T}', ('e3800000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{EG}', '2025-01-01', 'vigente', 'G' || g
  from generate_series(1, {N500}) g;
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  select '{T}', ('e3800000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, ('e3900000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{EG}', '{IM}', '{SEM}', 2100 + g, 'bruto', 7, '2025-01-01', true
  from generate_series(1, {N500}) g;
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),
 ('{U['nomina']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordG']}','{T}','coordinador','{P['CG']}');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values
 ('{EA}','{T}','2025-01-01','{U['nomina']}','{U['admin']}'),('{EG}','{T}','2025-01-01','{U['nomina']}','{U['admin']}');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'UXL' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{BONO}','{T}','{EA}','Bono','BON','importe','otro','tarifa',1,null,2),
 ('{HEG}','{T}','{EG}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1);
"""
sql(seed, replica=True)

L = datetime.date.fromisoformat(sql("select (date_trunc('week', public.hoy_mx() + 7))::date")) + datetime.timedelta(days=7 * 80)
dd = lambda n, k=0: (L + datetime.timedelta(days=7 * n + k)).isoformat()
semana = [0]
def periodo(emp=EA):
    semana[0] += 1; n = semana[0]
    return sql(f"select public.inc_crear_periodo('{emp}','{SEM}','{dd(n)}','{dd(n, 6)}')", 'nomina'), n
def hoja_a(per, n):
    H = sql(f"select public.inc_abrir_hoja('{per}')", 'coordA')
    sql(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H}','{P['X']}','{dd(n)}','F');
            insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values
              ('{H}','{P['X']}','{dd(n,1)}','{HE}',2),('{H}','{P['X']}','{dd(n,2)}','{BONO}',150),('{H}','{P['Y']}','{dd(n,1)}','{HE}',1),('{H}','{P['Z']}','{dd(n,2)}','{HE}',1.5)""", 'coordA')
    return H, sql(f"select public.inc_enviar_hoja('{H}')", 'coordA')
def resolver(per, versiones):
    for V in versiones:
        sql(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
        for iid in sql(f"select coalesce(string_agg(id::text, ' '), '') from public.inc_importes where version_id='{V}' and origen='por_asignar'").split():
            rp = sql(f"select r.id from public.personal_registros_pago r join public.inc_importes i on i.personal_id = r.personal_id where i.id='{iid}' and r.modalidad_sueldo='bruto' limit 1")
            sql(f"select public.inc_asignar_esquema('{iid}','{rp}','Esquema UXL')", 'nomina'); sql(f"select public.inc_decidir_importe('{iid}', null)", 'nomina')
    sql(f"select public.cred_descuentos_periodo('{per}')", 'nomina'); sql(f"select public.cred_aceptar_descuentos('{per}')", 'nomina')
def firmar(per):
    h = json.loads(sql(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))['huella_actual']['total']
    return sql(f"select public.inc_firmar_periodo('{per}','{h}')", 'nomina')
def foto(per):
    c = json.loads(sql(f"select public.inc_concentrado_periodo('{per}')", 'nomina'))
    return (c['estado'], c['huella']['total'], c['firma']['estado'], sql(f"select coalesce(procesado_en::text,'-') from public.inc_periodos where id='{per}'"),
            sql(f"select count(*) from public.inc_eventos where periodo_id='{per}' and tipo <> 'exportacion'"))
evs = lambda per: json.loads(sql(f"select coalesce(jsonb_agg(huella order by creado_en),'[]') from public.inc_eventos where periodo_id='{per}' and tipo='exportacion'"))

P1, n1 = periodo(); H1, V1 = hoja_a(P1, n1)                          # preliminar con importes por decidir
P2, n2 = periodo(); H2, V2 = hoja_a(P2, n2); resolver(P2, [V2]); firmar(P2)
sql(f"select public.inc_firmar_hoja('{H2}','rh')", 'admin')            # listo
P3, n3 = periodo(); H3, V3 = hoja_a(P3, n3); resolver(P3, [V3]); firmar(P3)
sql(f"select public.inc_firmar_hoja('{H3}','rh')", 'admin'); sql(f"select public.inc_marcar_procesado('{P3}')", 'nomina')
PG_, nG = periodo(EG)
HG = sql(f"select public.inc_abrir_hoja('{PG_}')", 'coordG')
sql(f"""insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
        select '{HG}', ('e3800000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{dd(nG, 1)}'::date + (g % 5), '{HEG}', 1 + (g % 3)
        from generate_series(1, {N500}) g""", 'coordG')
VG = sql(f"select public.inc_enviar_hoja('{HG}')", 'coordG'); resolver(PG_, [VG]); firmar(PG_); sql(f"select public.inc_firmar_hoja('{HG}','rh')", 'admin')
PG2, nG2 = periodo(EG)                                                   # 500 personas en preliminar (CA16, modalidad preliminar)
HG2 = sql(f"select public.inc_abrir_hoja('{PG2}')", 'coordG')
sql(f"""insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
        select '{HG2}', ('e3800000-0000-4000-8000-' || lpad(g::text, 12, '0'))::uuid, '{dd(nG2, 1)}'::date + (g % 5), '{HEG}', 1 + (g % 3)
        from generate_series(1, {N500}) g""", 'coordG')
sql(f"select public.inc_enviar_hoja('{HG2}')", 'coordG')
P4, n4 = periodo(); H4, V4 = hoja_a(P4, n4); resolver(P4, [V4]); sql(f"select public.inc_firmar_hoja('{H4}','rh')", 'admin')   # solo falta la firma de Nómina
print('Estados:', [json.loads(sql(f"select public.inc_concentrado_periodo('{x}')", 'nomina'))['estado'] for x in (P1, P2, P3, PG_, PG2, P4)])

PGRST = os.environ.get('PGRST') == '1'
SECRETO_LOCAL = b"beehuman-local-solo-pruebas-secreto-de-32-caracteres-o-mas"
def _b64b(d): return base64.urlsafe_b64encode(d).rstrip(b'=')
def jwt_local(sub):
    h = _b64b(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p_ = _b64b(json.dumps({"sub": sub, "role": "authenticated", "aud": "authenticated", "exp": int(time.time()) + 86400}).encode())
    return (h + b'.' + p_ + b'.' + _b64b(hmac.new(SECRETO_LOCAL, h + b'.' + p_, hashlib.sha256).digest())).decode()
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}
def b64(x): return base64.urlsafe_b64encode(json.dumps(x).encode()).rstrip(b'=').decode()
RED = []; ALTERAR = [False]; RESPUESTAS = {}
def ruta_para(quien):
    def ruta(route):
        req = route.request; u = urlparse(req.url)
        es_xl = 'cdn.jsdelivr.net' in req.url and 'exceljs@4.4.0/dist/exceljs.min.js' in req.url
        accion = ('local' if (u.netloc == f'{REF}.supabase.co' or ('cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url) or es_xl or u.netloc == 'fonts.googleapis.com')
                  else 'abortada' if u.scheme in ('http', 'https') else 'archivo_local')
        RED.append((accion, u.scheme, u.netloc, req.method))
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
        if es_xl: return route.fulfill(path=EXCELJS, content_type='application/javascript', headers={'access-control-allow-origin': '*'})
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path.startswith('/auth/v1/user'): return route.fulfill(json={'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}, headers=CORS)
            if u.path.startswith('/rest/v1/'):
                if PGRST:
                    destino = 'http://127.0.0.1:3010/' + u.path[len('/rest/v1/'):] + (('?' + u.query) if u.query else '')
                    r = route.fetch(url=destino); h = dict(r.headers); h.update(CORS); body = r.body()
                    if u.path.endswith('/rpc/inc_exportacion_canonica') or u.path.endswith('/rpc/inc_exportacion_preliminar'):
                        RESPUESTAS[u.path.rsplit('/', 1)[1]] = json.loads(body)
                        if ALTERAR[0] and u.path.endswith('canonica') and r.status == 200:      # B06: una celda alterada en tránsito
                            x = json.loads(body); x['hojas'][0]['filas'][0][1] = 'ALTERADO'; body = json.dumps(x).encode(); h.pop('content-length', None)
                    return route.fulfill(status=r.status, headers=h, body=body)
                tabla = u.path[len('/rest/v1/'):]; cuerpo = json.loads(req.post_data) if req.post_data else None
                try: st, res_, extra = RL.ejecutar(quien, req.method, tabla, parse_qsl(u.query, keep_blank_values=True), cuerpo, {k.lower(): v for k, v in req.headers.items()})
                except Exception as e: st, res_, extra = 400, {'code': 'LOCAL', 'message': str(e)}, {}
                h = dict(CORS); h.update(extra)
                if st == 204: return route.fulfill(status=204, headers=h, body='')
                return route.fulfill(status=st, headers=h, body=json.dumps(res_), content_type='application/json')
            return route.fulfill(json={}, headers=CORS)
        if u.scheme in ('http', 'https'): return route.abort()
        return route.continue_()
    return ruta

res = []
def ok(c, n, det=''):
    res.append((n, bool(c), det)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{det}]' if det else ''))
def vis(pg, sel): el = pg.query_selector(sel); return bool(el and el.is_visible())
def texto(pg, sel): el = pg.query_selector(sel); return el.inner_text().strip() if el else ''

# ---- lectura independiente del .xlsx ----
def valor_canon(v, fmt):
    if v is None: return None
    if isinstance(v, bool): return v
    if isinstance(v, datetime.datetime): return v.date().isoformat()
    if isinstance(v, (int, float)):
        if fmt == '#,##0.00': return f'{v:.2f}'
        s = repr(float(v)); s = s[:-2] if s.endswith('.0') else s; return s
    return v
def hojas_xlsx(ruta):
    wb = openpyxl.load_workbook(ruta)
    out = []
    for ws in wb.worksheets:
        filas = list(ws.iter_rows())
        cab = [c.value for c in filas[0]] if filas else []
        out.append({'nombre': ws.title, 'cab': cab, 'notas': [c.comment.text if c.comment else None for c in filas[0]] if filas else [],
                    'filas': [[valor_canon(c.value, c.number_format) for c in r[:len(cab)]] + [None] * (len(cab) - len(r)) for r in filas[1:]],
                    'celdas': filas[1:], 'ws': ws})
    return wb, out
def linea(a): return '[' + ','.join(json.dumps(unicodedata.normalize('NFC', v) if isinstance(v, str) else v, ensure_ascii=False) for v in a) + ']'
def huella_de_xlsx(hs, formato='beehuman.canonico'):
    ls = [linea([formato, '1.0'])]
    for h in hs[1:-1]: ls += [linea(['#hoja', h['nombre']]), linea(h['cab'])] + [linea(r) for r in h['filas']]
    return hashlib.sha256(('\n'.join(ls) + '\n').encode('utf-8')).hexdigest()
def norm_srv(v, t):
    if v is None: return None
    if t == 'booleano': return v in (True, 'true')
    if t in ('numero', 'entero'):
        s = repr(float(v)); return s[:-2] if s.endswith('.0') else s
    return v

ORDEN = ['Resumen', 'Personas', 'Esquemas', 'Incidencias', 'Cantidades', 'Importes', 'Descuentos', 'Movimientos', 'Catálogos', 'Validaciones']
with sync_playwright() as p:
    b = p.chromium.launch()
    def abrir(quien, ancho=1440, alto=950):
        ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1, accept_downloads=True)
        ses = {'access_token': jwt_local(U[quien]) if PGRST else b64({'alg': 'HS256'}) + '.' + b64({'sub': U[quien], 'role': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local',
               'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});")
        ctx.route('**/*', ruta_para(quien)); pg = ctx.new_page(); pg.errores = []
        pg.on('websocket', lambda ws: RED.append(('websocket', 'ws', ws.url, '')))
        pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda dl: dl.accept())
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(2000)
        return ctx, pg
    def concentrado(pg, per, primera=True):
        if primera:
            pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(1200)
        pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(1200)
        pg.click(f'#inc-r-periodos [data-rev-per="{per}"]'); pg.wait_for_timeout(1800)
        pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=30000); pg.wait_for_timeout(1000)
    def descargar(pg, boton, nombre):
        t0 = time.time()
        with pg.expect_download(timeout=120000) as dl: pg.click(boton)
        d = dl.value; ruta = os.path.join(OUT, d.suggested_filename); d.save_as(ruta)
        return ruta, d.suggested_filename, time.time() - t0
    errores = []

    print('== X1–X3 · Preliminar ==')
    ctx, pg = abrir('nomina'); concentrado(pg, P1)
    f1 = foto(P1)
    ok(vis(pg, '#inc-c-exp-pre') and pg.query_selector('#inc-c-exp-of') is None and 'sigue en preparación' in texto(pg, '#inc-c-exp-b08'),
       'X1 En preliminar: solo «Descargar reporte preliminar», con el texto de B08')
    pg.query_selector('#inc-c-exportar').screenshot(path=f'{OUT}/X1_panel_preliminar.png')
    ruta, nom, _ = descargar(pg, '#inc-c-exp-pre', 'pre')
    pg.wait_for_timeout(500)
    wb, hs = hojas_xlsx(ruta)
    ok(nom.startswith('PRELIMINAR_BeeHuman_EMPRESA-AGUILA-UI-XL_' + dd(n1) + '_' + dd(n1, 6) + '_') and nom.endswith('.xlsx'), 'X2 Nombre PRELIMINAR_BeeHuman_…_AAAAMMDD-HHMM.xlsx', nom)
    ok([h['nombre'] for h in hs] == ['PRELIM ' + n for n in ORDEN[:-1]] + ['PRELIM Faltantes'], 'X2 Hojas «PRELIM …» y «PRELIM Faltantes»', str([h['nombre'] for h in hs]))
    rs = hs[0]
    ok(rs['filas'][0][0] == 'aviso' and 'PRELIMINAR — NO AUTORIZADO' in rs['filas'][0][4], 'X2 Primera fila del Resumen: aviso PRELIMINAR — NO AUTORIZADO')
    ws0 = hs[1]['ws']
    ok('PRELIMINAR' in (ws0.oddHeader.center.text or '') and wb.properties.title == 'PRELIMINAR — NO AUTORIZADO' and (ws0.sheet_properties.tabColor.rgb or '').endswith('F79009'),
       'X2 Encabezado de impresión, título del documento y color de pestaña de preliminar', f'{ws0.oddHeader.center.text!r}')
    imp = next(h for h in hs if h['nombre'] == 'PRELIM Importes'); ci = {n: i for i, n in enumerate(imp['cab'])}
    pend = [r for r in imp['filas'] if r[ci['estado']] == 'por_decidir']
    ok(pend and all(r[ci['importe']] is None and r[ci['motivo_pendiente']] for r in pend) and any(r[ci['importe_sugerido']] for r in pend),
       'X3 Por decidir: importe vacío, estado, motivo y sugerido', f'{len(pend)} filas')
    ok(not any(r[0] == 'total_importes' for r in rs['filas']), 'X3 Lo por decidir no se suma en el Resumen')
    ok(foto(P1) == f1 and len(evs(P1)) == 1 and evs(P1)[0]['modalidad'] == 'preliminar', 'X10 Preliminar: un evento «preliminar»; firma, huella y estado intactos')
    ok('PERSONA CA UI XL' not in json.dumps(evs(P1)) and 'RFC' not in json.dumps(evs(P1)), '+X10b El evento no guarda nombres ni RFC')
    errores += pg.errores

    print('== X4–X8 · Oficial en listo ==')
    concentrado(pg, P2, primera=False)
    f2 = foto(P2)
    ok(f2[0] == 'listo' and vis(pg, '#inc-c-exp-of') and pg.query_selector('#inc-c-exp-pre') is None and not pg.query_selector('#inc-c-exp-of').is_disabled(),
       'X4 En listo: solo «Exportar Excel oficial»', f2[0])
    pg.query_selector('#inc-c-exportar').screenshot(path=f'{OUT}/X4_panel_oficial.png')
    ruta, nom, _ = descargar(pg, '#inc-c-exp-of', 'of'); pg.wait_for_timeout(500)
    srv = RESPUESTAS['inc_exportacion_canonica']
    wb, hs = hojas_xlsx(ruta)
    ok(nom == f'BeeHuman_EMPRESA-AGUILA-UI-XL_{dd(n2)}_{dd(n2, 6)}_exp-1.xlsx' and 'Exportación número 1' in texto(pg, '#inc-c-exp-msg'), 'X5 Nombre BeeHuman_…_exp-1.xlsx y mensaje', nom)
    ok([h['nombre'] for h in hs] == ORDEN, 'X5 Las 10 hojas en el orden del diseño', str([h['nombre'] for h in hs]))
    cont = [srv['resumen']] + srv['hojas'] + [srv['validaciones']]
    ok(all(h['cab'] == [c['n'] for c in s['columnas']] for h, s in zip(hs, cont)), 'X5 Encabezados = contrato del servidor en todas las hojas')
    ok(all(all(n for n in h['notas']) for h in hs), 'X5 Cada encabezado lleva su nota (descripción)')
    per = hs[1]; cp = {n: i for i, n in enumerate(per['cab'])}
    fz = next(r for r in per['celdas'] if r[cp['persona_id']].value == P['Z'])
    ok(fz[cp['nombre_completo']].data_type == 's' and fz[cp['nombre_completo']].value == unicodedata.normalize('NFC', NOMBRE['Z']),
       'X6 Texto que empieza con «=»: celda de texto (no fórmula), en NFC', repr(fz[cp['nombre_completo']].value))
    ok(fz[cp['numero_interno']].data_type == 's' and fz[cp['persona_id']].data_type == 's', 'X6 Número interno e identificadores como texto')
    fy = next(r for r in per['celdas'] if r[cp['persona_id']].value == P['Y'])
    ok(fy[cp['numero_interno']].value == '0042', 'X6 Número interno «0042» conserva los ceros a la izquierda')
    ok(isinstance(fz[cp['fecha_ingreso']].value, datetime.datetime) and fz[cp['fecha_ingreso']].number_format == 'dd/mm/yyyy', 'X6 Fecha como fecha de Excel dd/mm/yyyy')
    ok(fz[cp['con_incidencias']].data_type == 'b' and fz[cp['fecha_baja']].value is None, 'X6 Booleano lógico y fecha vacía = celda vacía')
    imp = hs[5]; ci = {n: i for i, n in enumerate(imp['cab'])}
    ok(all(isinstance(r[ci['importe']].value, (int, float)) and r[ci['importe']].number_format == '#,##0.00' for r in imp['celdas']), 'X6 Importes numéricos con formato #,##0.00')
    can = hs[4]; cc = {n: i for i, n in enumerate(can['cab'])}
    ok(any(r[cc['cantidad']].value == 1.5 and r[cc['cantidad']].number_format == '0.####' for r in can['celdas']), 'X6 Cantidad 1.5 numérica con formato 0.####')
    ok(all(all(c.data_type != 'f' for c in r) for h in hs for r in h['celdas']), 'X6 Ninguna fórmula en todo el archivo')
    ok(huella_de_xlsx(hs) == srv['huella_archivo'] and next(r[4] for r in hs[0]['filas'] if r[1] == 'huella_archivo') == srv['huella_archivo'],
       'X7 huella_archivo recalculada en Python sobre lo leído del .xlsx = la del servidor (= la del Resumen)')
    ok(all([norm_srv(v, s['columnas'][i]['t']) for i, v in enumerate(fila)] == h['filas'][j] for h, s in zip(hs[1:-1], srv['hojas']) for j, fila in enumerate(s['filas'])),
       'X7 Cada celda de las 8 hojas de datos = la fila del servidor')
    tot = {}
    for r in imp['filas']: tot[(r[ci['concepto_id']], r[ci['modalidad']])] = round(tot.get((r[ci['concepto_id']], r[ci['modalidad']]), 0) + float(r[ci['importe']]), 2)
    rt = {(r[2], r[3]): float(r[4]) for r in hs[0]['filas'] if r[0] == 'total_importes'}
    ok(tot == rt and len(rt) >= 2, 'X7 Suma de Importes por concepto y modalidad = totales del Resumen (bruto y neto separados)', str(rt))
    ok(foto(P2) == f2 and [e['modalidad'] for e in evs(P2)] == ['oficial'], 'X10 Oficial: un evento «oficial»; firma, huella y estado intactos')
    sql(f"update public.personal set rfc = 'RFCX0101YYY' where id = '{P['X']}'", replica=True)   # cambio descriptivo (§4.4)
    ruta2, nom2, _ = descargar(pg, '#inc-c-exp-of', 'of2'); pg.wait_for_timeout(500)
    ok(nom2.endswith('_exp-2.xlsx') and 'Los datos descriptivos cambiaron desde la exportación 1' in texto(pg, '#inc-c-exp-msg') and foto(P2)[2] == 'vigente',
       'X7b Cambia solo el RFC: firma vigente, exp-2 y aviso «Los datos descriptivos cambiaron desde la exportación 1»', texto(pg, '#inc-c-exp-msg'))
    ALTERAR[0] = True
    n_desc = len([f for f in os.listdir(OUT) if f.endswith('.xlsx')])
    pg.click('#inc-c-exp-of'); pg.wait_for_timeout(3000)
    ok('(B06)' in texto(pg, '#inc-c-exp-msg') and len([f for f in os.listdir(OUT) if f.endswith('.xlsx')]) == n_desc, 'X8 Celda alterada en tránsito: B06 y no se descarga', texto(pg, '#inc-c-exp-msg'))
    ALTERAR[0] = False
    pg.screenshot(path=f'{OUT}/X8_b06.png')
    errores += pg.errores

    print('== X9 · Procesado que cambió después ==')
    sql(f"update public.personal_registros_pago set sueldo = 3900 where personal_id = '{P['Y']}'", replica=True)   # cambio después del procesado → B07 (P2 ya se exportó)
    concentrado(pg, P3, primera=False)
    ok(vis(pg, '#inc-c-exp-b07') and pg.query_selector('#inc-c-exp-of').is_disabled() and pg.query_selector('#inc-c-exp-pre') is None,
       'X9 Procesado con cambio posterior: explicación B07 y botón deshabilitado')
    ok('B07' in (lambda: (lambda r: r)(subprocess.run(PSQL, input=f"begin; select set_config('request.jwt.claims','{json.dumps({'sub': U['nomina']})}',true); set local role authenticated; select public.inc_exportacion_canonica('{P3}'); rollback;", capture_output=True, text=True).stderr))(),
       '+X9b …y la base también lo bloquea (B07)')
    pg.query_selector('#inc-c-exportar').screenshot(path=f'{OUT}/X9_b07.png')
    errores += pg.errores; ctx.close()

    print('== X11 · 500 personas (CA16) ==')
    ctx, pg = abrir('nomina'); concentrado(pg, PG_)
    ruta, nom, seg = descargar(pg, '#inc-c-exp-of', 'g')
    wb, hs = hojas_xlsx(ruta)
    t_db = sql(f"""select round(extract(epoch from clock_timestamp() - t) * 1000) from (select clock_timestamp() t) a,
                   lateral (select public.inc__exportacion_datos('{PG_}', 'oficial')) b""").strip() if False else None
    ok(len(hs[1]['filas']) == N500 + 1 and len(hs[4]['filas']) == N500 and huella_de_xlsx(hs) == RESPUESTAS['inc_exportacion_canonica']['huella_archivo'],
       'X11 500 personas (+ su coordinador, empleado de la empresa): 501 filas en Personas, 500 en Cantidades; huella_archivo coincide')
    ok(seg < 5, f'CA16 Oficial · de clic a archivo descargado con 500 personas: {seg:.1f} s (límite 5 s)', f'{os.path.getsize(ruta) // 1024} KB')
    concentrado(pg, PG2, primera=False)
    ruta, nom, seg = descargar(pg, '#inc-c-exp-pre', 'g2'); wb, hs = hojas_xlsx(ruta)
    ok(seg < 5 and len(hs[5]['filas']) == N500, f'CA16 Preliminar · de clic a archivo descargado con 500 personas: {seg:.1f} s (límite 5 s); 500 importes por decidir', f'{os.path.getsize(ruta) // 1024} KB')
    print('== X13 · Sin cambios desde el preliminar (CA27) ==')
    sql(f"select public.inc_exportacion_preliminar('{P4}')", 'nomina'); firmar(P4)
    concentrado(pg, P4, primera=False)
    ok(foto(P4)[0] == 'listo' and vis(pg, '#inc-c-exp-sin-cambios') and 'Sin cambios desde el preliminar' in texto(pg, '#inc-c-exp-sin-cambios'),
       'CA27 Firmado con la misma huella del último preliminar: «Sin cambios desde el preliminar del …»', texto(pg, '#inc-c-exp-sin-cambios'))
    concentrado(pg, P2, primera=False)
    ok(pg.query_selector('#inc-c-exp-sin-cambios') is None, 'CA27 Sin preliminar previo: no se muestra la nota')
    errores += pg.errores; ctx.close()
    b.close()

ok(not errores, 'X12 Sin errores de JavaScript', '; '.join(errores)[:300])
ext = [r for r in RED if r[0] == 'abortada' or r[0] == 'websocket']
ok(not ext, 'RED Nada sale a internet (Supabase, supabase-js y ExcelJS servidos localmente)', str(ext[:5]))
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for n, _, d in malas: print('  FALLA:', n, d)
sys.exit(1 if malas else 0)
