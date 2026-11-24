"""B-b · Pantalla del concentrado del periodo (Incidencias → Revisión → periodo → «Concentrado»), con datos FICTICIOS.
Base local bhui; peticiones atendidas por rest_local.py como el usuario (mismas RLS y permisos), no PostgREST real
(eso se valida en B-c). Cada verificación compara la pantalla contra lo que devuelve la base en ese momento.
  K1  La pestaña «Concentrado» abre el concentrado; estado «Preliminar» igual al de inc_concentrado_periodo.
  K2  Pendientes: «Impiden firmar y procesar» = inc_faltantes_bloqueantes; «Impiden solo procesar» = el resto de
      inc_faltantes_procesar. Ninguno se pierde ni se duplica.
  K3  Firma bloqueada: el botón está deshabilitado y explica por qué.
  K4  Hojas no incluidas: se avisan con el coordinador.
  K5  Totales: personas, días por código e importes por concepto y modalidad iguales a la base; nunca se mezcla
      bruto con neto; los importes por decidir se cuentan, no se suman. K5b repite con importes decididos.
  K6  Tabla: una fila por persona de la base, con y sin captura; alta a mitad del periodo con su fecha y días vigentes.
  K7  Filtros: búsqueda, solo con incidencias, con pendientes, con movimientos.
  K8  Detalle: importes por esquema (bruto y neto por separado), línea sin importe, descuento por decidir, informativo.
  K9  Avisos que no bloquean: líneas sin importe.
  K10 Otro usuario de Nómina ve el estado, sin botón.
  K11 Firmar desde el concentrado: firma vigente con la huella que se mostraba; 9 secciones «Sin cambios desde la firma».
  K12 Cambio después de firmar: «invalidada», las secciones marcadas = secciones_cambiadas de la base; historial.
  K13 Huella desactualizada: si el concentrado cambió mientras se veía, la firma se rechaza y no se registra.
  K14 Sin pendientes: estado «Listo para procesar», igual a la base.
  K15 Procesado: estado «Procesado», sin pendientes ni botón de firma; firma e historial visibles.
  K16 Cambio después de procesar: aviso con las secciones de avisos.cambio_posterior_procesado; el periodo NO se reabre.
  K17 Nunca se ofrece una firma de Nómina por hoja; las hojas muestran solo la firma de RH.
  K18 La pestaña «Hojas» sigue funcionando y muestra el mismo estado de firma.
  K19 Celular (390 px): sin desplazamiento horizontal; cada persona como tarjeta.
  K20 Sin errores de JavaScript.
  K21 (23-nov) Desde «Hojas» no se firma como Nómina aunque estaría permitido; el acceso lleva a «Concentrado».
  K23 (24-nov, B-c) Periodo procesado con la regla anterior (firma por hoja, sin huella): sin falsa alarma «Falta la firma».
  K22 (23-nov) En el código, inc_firmar_periodo se llama una sola vez y solo se conecta en el concentrado; la hoja solo
      construye la firma de RH.
  RED Registro de red: las peticiones a la dirección de beehuman-pruebas se responden en local y nada sale a internet.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_concentrado.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64, subprocess, datetime
from collections import Counter
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']; REF = 'sflvpgkmtaxzogpgetxn'
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', RL.DB]
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    if err: raise RuntimeError(err)
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET') and not l.startswith('{"sub"')]; return out[-1] if out else ''
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"

T = '1bb00000-0000-4000-8000-000000000001'
U = {k: f'1bb10000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'nomina2', 'coordA', 'coordB'], 1)}
RL.U.update(U)
E1, SEM = '1bb20000-0000-4000-8000-000000000001', '1bb30000-0000-4000-8000-000000000007'
CL_IMSS, CL_EFE, RPAT = '1bb40000-0000-4000-8000-000000000001', '1bb40000-0000-4000-8000-000000000002', '1bb40000-0000-4000-8000-000000000009'
NOMBRES = ['CA', 'CB', 'A1', 'A2', 'A3', 'A4', 'B1']
P = {k: f'1bb50000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOMBRES, 1)}
RLB = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
HE, BONO, CAP = '1bb60000-0000-4000-8000-000000000001', '1bb60000-0000-4000-8000-000000000002', '1bb60000-0000-4000-8000-000000000003'
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui (montar_bhui.sh).'); sys.exit(1)
L = datetime.date.fromisoformat(sql("select (date_trunc('week', public.hoy_mx() + 7))::date"))
d = lambda n: (L + datetime.timedelta(days=n)).isoformat()
nom = lambda k: f'PERSONA {k} CONC'
ingreso = {k: '2025-01-01' for k in NOMBRES}; ingreso['A3'] = d(2)
coord = {'A1': 'CA', 'A2': 'CA', 'A3': 'CA', 'A4': 'CA', 'B1': 'CB'}
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT UI CONCENTRADO');
insert into auth.users (id, email) select v, k||'.uicc@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA UI CONCENTRADO');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo) values ('{RPAT}','{E1}','{T}','UC12345678',true);
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL_IMSS}','{T}','IMSS'),('{CL_EFE}','{T}','EFECTIVO');
"""
for k in NOMBRES:
    co = f"'{P[coord[k]]}'" if k in coord else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id) values ('{P[k]}','{T}','{E1}','{nom(k)}','UC-{k}',{co});\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, registro_patronal_id, numero_interno) values "
             f"('{RLB[k]}','{T}','{P[k]}','{E1}','{ingreso[k]}','vigente','{RPAT}','N{k}');\n")
for i, (k, cl, su, mod) in enumerate([('A1', CL_IMSS, 3500, 'bruto'), ('A1', CL_EFE, 700, 'neto'), ('A2', CL_IMSS, 2800, 'bruto'),
                                      ('A3', CL_IMSS, 2800, 'bruto'), ('A4', CL_IMSS, 2800, 'bruto'), ('B1', CL_IMSS, 2800, 'bruto')]):
    seed += (f"insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values "
             f"('1bb70000-0000-4000-8000-{i:012d}','{T}','{P[k]}','{RLB[k]}','{E1}','{cl}','{SEM}',{su},'{mod}',7,'2025-01-01',true);\n")
seed += f"""insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['nomina2']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values ('{E1}','{T}','2025-01-01','{U['nomina']}','{U['admin']}');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'UI CONC' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{BONO}','{T}','{E1}','Bono','BON','importe','otro','tarifa',1,null,2),
 ('{CAP}','{T}','{E1}','Capacitación','CAP','horas','otro','sin_importe',null,null,3);
insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, causa, origen) values
 ('{T}','{P['A3']}','{RLB['A3']}','ingreso','{d(2)}',null,'pantalla');
"""
sql(seed, replica=True)
P1 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','{d(0)}','{d(6)}')", 'nomina')
def credito(datos):
    c = sql(f"select public.cred_guardar(null, {lit(datos)}, null)", 'nomina')
    if sql(f"select estado from public.cred_creditos where id='{c}'") != 'activo': sql(f"select public.cred_cambiar_estado('{c}','activo','{d(0)}','Alta UI')", 'nomina')
    return c
credito({'personal_id': P['A3'], 'tipo': 'fonacot', 'referencia': 'FN-A3', 'relacion_laboral_id': RLB['A3'], 'fecha_inicio': d(0), 'periodicidad_id': SEM, 'importe_periodo': 150})
credito({'personal_id': P['A2'], 'tipo': 'infonavit', 'referencia': 'INF-A2', 'relacion_laboral_id': RLB['A2'], 'fecha_inicio': '2025-01-01', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 900})
# Hoja de CA: se envía. Hoja de CB: se abre con captura y queda sin enviar.
HA = sql(f"select public.inc_abrir_hoja('{P1}')", 'coordA')
sql(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{HA}','{P['A2']}','{d(1)}','F'),('{HA}','{P['A2']}','{d(2)}','V');
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HA}','{P['A1']}','{d(0)}','{HE}',2),('{HA}','{P['A3']}','{d(3)}','{HE}',1)""", 'coordA')
sql(f"insert into public.inc_observaciones (hoja_id, personal_id, texto) values ('{HA}','{P['A1']}','Cubrió turno nocturno')", 'coordA')
VA = sql(f"select public.inc_enviar_hoja('{HA}')", 'coordA')
HB = sql(f"select public.inc_abrir_hoja('{P1}')", 'coordB')
sql(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HB}','{P['B1']}','{d(0)}','{BONO}',500),('{HB}','{P['B1']}','{d(1)}','{CAP}',3)", 'coordB')

conc = lambda: json.loads(sql(f"select public.inc_concentrado_periodo('{P1}')", 'nomina'))
# inc_faltantes_bloqueantes es interna (sin permiso EXECUTE a usuarios, diseño B-a): se lee como postgres con los claims de Nómina.
bloqueantes_db = lambda: Counter(x for x in sql(f"select set_config('request.jwt.claims', '{json.dumps({'sub': U['nomina']})}', true); select coalesce(string_agg(detalle, E'\\x1f' order by detalle), '') from public.inc_faltantes_bloqueantes('{P1}')").split('\x1f') if x)
eventos_firma = lambda: sql(f"select count(*) from public.inc_eventos where periodo_id = '{P1}' and tipo = 'firma_nomina' and hoja_id is null")

# PGRST=1: las peticiones /rest/v1 van al PostgREST LOCAL (127.0.0.1:3010, base bhui) con un JWT firmado con el secreto
# local de pruebas (el mismo que ui_b1.py). Sin PGRST: traductor rest_local.py (modo por omisión).
import hmac, hashlib
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
RED = []   # registro de red: cada petición del navegador y qué se hizo con ella (respondida en local, abortada o dejada pasar)
def ruta_para(quien):
    def ruta(route):
        req = route.request; u = urlparse(req.url)
        accion = ('local' if (u.netloc == f'{REF}.supabase.co' or ('cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url) or u.netloc == 'fonts.googleapis.com')
                  else 'abortada' if u.scheme in ('http', 'https') else 'archivo_local')
        RED.append((accion, u.scheme, u.netloc, req.method))
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path.startswith('/auth/v1/user'): return route.fulfill(json={'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}, headers=CORS)
            if u.path.startswith('/rest/v1/'):
                if PGRST:
                    destino = 'http://127.0.0.1:3010/' + u.path[len('/rest/v1/'):] + (('?' + u.query) if u.query else '')
                    r = route.fetch(url=destino); h = dict(r.headers); h.update(CORS)
                    return route.fulfill(status=r.status, headers=h, body=r.body())
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
def texto(pg, sel):
    el = pg.query_selector(sel); return el.inner_text().strip() if el else ''
def textos(pg, sel): return [e.inner_text().strip() for e in pg.query_selector_all(sel)]
def attrs(pg, sel, a): return [e.get_attribute(a) for e in pg.query_selector_all(sel)]

with sync_playwright() as p:
    b = p.chromium.launch()
    def abrir(quien, ancho=1440, alto=950):
        ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1)
        ses = {'access_token': jwt_local(U[quien]) if PGRST else b64({'alg': 'HS256'}) + '.' + b64({'sub': U[quien], 'role': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local',
               'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});")
        ctx.route('**/*', ruta_para(quien)); pg = ctx.new_page(); pg.errores = []
        pg.on('websocket', lambda ws: RED.append(('websocket', 'ws', ws.url, '')))
        pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda dl: dl.accept())
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
        return ctx, pg
    def concentrado(pg):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
        pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(900)
        pg.click(f'#inc-r-periodos [data-rev-per="{P1}"]'); pg.wait_for_timeout(1800)
        pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(800)
    def recargar(pg):   # vuelve a pedir el concentrado a la base (como al volver a la pestaña)
        pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(1200)
    def secciones(pg): return dict(zip(attrs(pg, '#inc-c-secciones [data-seccion]', 'data-seccion'), attrs(pg, '#inc-c-secciones [data-seccion]', 'data-sec-estado')))
    def persona(c, k): return next(x for x in c['personas'] if x['personal_id'] == P[k])
    errores = []

    # ============ Estado preliminar ============
    ctx, pg = abrir('nomina'); concentrado(pg); c = conc()
    print('== K1 · Abrir el concentrado ==')
    ok(pg.query_selector('#inc-c') is not None and 'activo' in (pg.get_attribute('#inc-r-pestanas [data-r-pest="concentrado"]', 'class') or ''),
       'K1 La pestaña «Concentrado» abre el concentrado del periodo')
    ok(c['estado'] == 'preliminar' and pg.get_attribute('#inc-c-estado', 'data-estado') == 'preliminar' and texto(pg, '#inc-c-estado') == 'Preliminar',
       'K1 Estado «Preliminar», igual a la base', f"{c['estado']} / {texto(pg, '#inc-c-estado')}")

    print('== K2 · Pendientes agrupados ==')
    # Cada línea de la pantalla lleva el texto de la base y cuántas veces viene (la pantalla agrupa textos idénticos).
    cuenta_ui = lambda sel: Counter({e.get_attribute('data-detalle'): int(e.get_attribute('data-n')) for e in pg.query_selector_all(sel)})
    ui_bloq, ui_solo = cuenta_ui('#inc-c-bloquean li[data-detalle]'), cuenta_ui('#inc-c-solo-procesar li[data-detalle]')
    db_falt = Counter(f['detalle'] for f in c['faltantes']); db_bloq = bloqueantes_db()
    ok(ui_bloq == db_bloq and sum(db_bloq.values()) > 0, 'K2 «Impiden firmar y procesar» = inc_faltantes_bloqueantes (misma lista, una por una, con repeticiones)', f'{sum(ui_bloq.values())} vs {sum(db_bloq.values())}')
    ok(ui_solo == db_falt - db_bloq and ui_solo and not (set(ui_bloq) & set(ui_solo)), 'K2 «Impiden solo procesar» = el resto de los faltantes (firmas), sin duplicar',
       ' | '.join(sorted(ui_solo))[:160])
    ok(ui_bloq + ui_solo == db_falt, 'K2 Ningún pendiente se pierde ni se duplica', f"{sum((ui_bloq + ui_solo).values())} de {len(c['faltantes'])}")
    rep_a1 = [e for e in pg.query_selector_all('#inc-c-bloquean li[data-n="2"]') if (e.get_attribute('data-detalle') or '').startswith('PERSONA A1 CONC')]
    ok(rep_a1 and '× 2' in rep_a1[0].inner_text() and 'esquema de pago' in rep_a1[0].inner_text(), 'K2 Dos líneas idénticas de la base (A1, dos esquemas) se agrupan «× 2» con su explicación',
       rep_a1[0].inner_text() if rep_a1 else '')
    ok(any('importe por decidir' in t for t in ui_bloq) and any(t.startswith('PERSONA A3 CONC') and 'FONACOT' in t.upper() for t in ui_bloq),
       'K2 Los bloqueantes explican el motivo (importe por decidir, descuento FONACOT de A3)')

    print('== K3 · K4 · Firma bloqueada y hojas no incluidas ==')
    ok(pg.is_disabled('#inc-c-firma #inc-r-firmar-per') and 'Primero resuelve los pendientes' in texto(pg, '#inc-c-firma')
       and pg.query_selector('#inc-c-firma [data-firma-estado="sin_firma"]') is not None, 'K3 Con bloqueantes: botón deshabilitado, «Falta la firma» y la explicación', texto(pg, '#inc-c-firma')[:120])
    ok(c['avisos']['hojas_no_incluidas'] and all(h in texto(pg, '#inc-c-no-incluidas') for h in c['avisos']['hojas_no_incluidas'])
       and 'PERSONA CB CONC' in texto(pg, '#inc-c-no-incluidas'),
       'K4 Hojas no incluidas: se avisan con el coordinador (CB sin enviar)', texto(pg, '#inc-c-no-incluidas')[:120])

    print('== K5 · Totales ==')
    T_ = c['totales']
    tot_imp_ui = set(attrs(pg, '#inc-c-tot-imp [data-tot-imp]', 'data-tot-imp'))
    tot_imp_db = {f'{cid}:{m}' for cid, mods in T_['importes'].items() for m in mods}
    ok(f"{T_['personas']} personas" in texto(pg, '#inc-c-totales') and f"{T_['con_incidencias']} con incidencias" in texto(pg, '#inc-c-totales'),
       'K5 Personas y personas con incidencias = base', f"{T_['personas']} / {T_['con_incidencias']}")
    ok({x: texto(pg, f'#inc-c-totales [data-tot-dia="{x}"]') for x in T_['dias']} == {x: f"{ {'F': 'Falta', 'V': 'Vacaciones'}.get(x, x)}: {n}" for x, n in T_['dias'].items()} and T_['dias'] == {'F': 1, 'V': 1},
       'K5 Días por código = base (F 1, V 1)', json.dumps(T_['dias']))
    ok(tot_imp_ui == tot_imp_db == set(), 'K5 Sin importes decididos todavía: la pantalla no muestra ninguna cifra de importes (igual a la base)', f'{sorted(tot_imp_ui)}')
    pend = texto(pg, '#inc-c-tot-imp [data-tot-imp-pend]')
    ok(T_['importes_por_decidir'] > 0 and pend.startswith(f"{T_['importes_por_decidir']} importe") and 'no se suma' in pend and '$' not in pend,
       'K5 Importes por decidir: se cuentan sin cifra y se aclara que no se suman', pend)
    pg.screenshot(path=f'{OUT}/K_escritorio_preliminar.png', full_page=True)

    print('== K6 · Tabla por persona ==')
    filas_ui = attrs(pg, '#inc-c-tabla tr.inc-c-fila', 'data-persona')
    ok(sorted(filas_ui) == sorted(x['personal_id'] for x in c['personas']) and len(filas_ui) == len(set(filas_ui)), 'K6 Una fila por persona de la base, sin repetir', str(len(filas_ui)))
    ok(P['A4'] in filas_ui and not persona(c, 'A4')['con_incidencias'], 'K6 Incluye a quien no tuvo captura (A4)')
    fa3 = texto(pg, f'#inc-c-tabla tr[data-persona="{P["A3"]}"]')
    ok('Ingreso' in fa3 and datetime.date.fromisoformat(d(2)).strftime('%d/%m') in fa3 and f"{persona(c, 'A3')['dias_vigentes']} de 7 días vigentes" in fa3,
       'K6 Alta a mitad del periodo (A3): ingreso con fecha y días vigentes de la base', fa3.replace('\n', ' ')[:150])
    fa1 = texto(pg, f'#inc-c-tabla tr[data-persona="{P["A1"]}"]')
    ok('UC-A1' in fa1 and 'NOI NA1' in fa1 and 'UC12345678' in fa1 and '2 h' in fa1, 'K6 Identificación (BEH, número interno, registro patronal) y cantidades por concepto', fa1.replace('\n', ' ')[:150])
    pd = persona(c, 'A1')['importes_por_decidir']
    ok(pd > 0 and f'por decidir ({pd})' in fa1, 'K6 Importes por decidir de la persona marcados, sin cifra', str(pd))

    print('== K7 · Filtros ==')
    pg.check('#inc-c-f-inc'); pg.wait_for_timeout(300)
    vis = set(attrs(pg, '#inc-c-tabla tr.inc-c-fila', 'data-persona'))
    ok(vis == {x['personal_id'] for x in c['personas'] if x['con_incidencias']}, 'K7 «Solo con incidencias» = personas con incidencias de la base', str(len(vis)))
    pg.uncheck('#inc-c-f-inc'); pg.check('#inc-c-f-mov'); pg.wait_for_timeout(300)
    ok(set(attrs(pg, '#inc-c-tabla tr.inc-c-fila', 'data-persona')) == {P['A3']}, 'K7 «Con movimientos»: solo A3')
    pg.uncheck('#inc-c-f-mov'); pg.check('#inc-c-f-pend'); pg.wait_for_timeout(300)
    ok(set(attrs(pg, '#inc-c-tabla tr.inc-c-fila', 'data-persona')) == {x['personal_id'] for x in c['personas'] if x['importes_por_decidir'] or x['descuentos_por_decidir']},
       'K7 «Con pendientes por decidir» = base')
    pg.uncheck('#inc-c-f-pend'); pg.fill('#inc-c-q', 'uc-a2'); pg.wait_for_timeout(300)
    ok(attrs(pg, '#inc-c-tabla tr.inc-c-fila', 'data-persona') == [P['A2']] and texto(pg, '#inc-c-cuenta').startswith('1 de '), 'K7 Búsqueda por número de empleado')
    pg.fill('#inc-c-q', ''); pg.wait_for_timeout(300)

    print('== K8 · Detalle ==')
    pg.click(f'[data-c-det="{P["A1"]}"]'); pg.wait_for_timeout(300)
    det = texto(pg, f'tr[data-detalle="{P["A1"]}"]')
    mods_a1 = {i['modalidad'] for i in persona(c, 'A1')['importes']}
    ok(mods_a1 == {'bruto', 'neto'} and 'IMSS' in det and 'EFECTIVO' in det and 'Bruto' in det and 'Neto' in det and 'Cubrió turno nocturno' in det,
       'K8 Detalle de A1: importes por esquema (IMSS bruto y EFECTIVO neto por separado) y observación', det.replace('\n', ' ')[:150])
    pg.click(f'[data-c-det="{P["A3"]}"]'); pg.click(f'[data-c-det="{P["A2"]}"]'); pg.wait_for_timeout(300)
    d3, d2 = texto(pg, f'tr[data-detalle="{P["A3"]}"]'), texto(pg, f'tr[data-detalle="{P["A2"]}"]')
    ok('FN-A3' in d3 or 'FONACOT' in d3, 'K8 Detalle de A3: el descuento FONACOT por decidir', d3.replace('\n', ' ')[:120])
    ok('informativos' in d2.lower() and 'INFONAVIT' in d2.upper() and 'Falta' in d2 and 'Vacaciones' in d2, 'K8 Detalle de A2: días con código y crédito informativo sin importe', d2.replace('\n', ' ')[:140])
    pg.screenshot(path=f'{OUT}/K_escritorio_detalle.png', full_page=True)
    errores += pg.errores; ctx.close()

    print('== K10 · Otro usuario de Nómina ==')
    ctx, pg = abrir('nomina2'); concentrado(pg)
    ok(pg.query_selector('#inc-r-firmar-per') is None and 'Solo el responsable designado' in texto(pg, '#inc-c-firma'), 'K10 Otro usuario de Nómina: ve el estado, sin botón')
    errores += pg.errores; ctx.close()

    # ============ Se envía la hoja de CB y se deciden importes y descuentos ============
    VB = sql(f"select public.inc_enviar_hoja('{HB}')", 'coordB')
    for v in (VA, VB): sql(f"select public.inc_aceptar_sugeridos('{v}')", 'nomina')
    sql(f"select public.cred_descuentos_periodo('{P1}')", 'nomina'); sql(f"select public.cred_aceptar_descuentos('{P1}')", 'nomina')
    ctx, pg = abrir('nomina'); concentrado(pg); c = conc()
    print('== K9 · Avisos que no bloquean ==')
    n_si = sum(1 for x in c['personas'] for i in x['importes'] if i['estado'] == 'sin_importe')
    ok(n_si >= 1 and pg.query_selector('#inc-c-avisos [data-aviso="sin_importe"]') is not None and texto(pg, '#inc-c-avisos [data-aviso="sin_importe"]').startswith(f'{n_si} línea'),
       'K9 Las líneas sin importe se avisan, sin bloquear', texto(pg, '#inc-c-avisos'))
    ok(not bloqueantes_db() and pg.query_selector('#inc-c-bloquean') is None, 'K9 Sin bloqueantes en la base ni en pantalla')

    print('== K11 · Firmar desde el concentrado ==')
    huella_vista = c['huella']['total']
    ok(not pg.is_disabled('#inc-c-firma #inc-r-firmar-per'), 'K11 Sin bloqueantes, el botón se habilita (la firma de RH no bloquea)')
    pg.click('#inc-c-firma #inc-r-firmar-per'); pg.wait_for_timeout(2000)
    fdb = json.loads(sql(f"select huella from public.inc_eventos where periodo_id='{P1}' and tipo='firma_nomina' order by creado_en desc limit 1"))
    ok(pg.query_selector('#inc-c-firma [data-firma-estado="vigente"]') is not None and eventos_firma() == '1' and fdb['total'] == huella_vista,
       'K11 Firma vigente; un evento; la huella firmada es la que mostraba la pantalla', huella_vista[:16])
    sec = secciones(pg)
    ok(list(sec) == ['hojas', 'personas', 'dias', 'cantidades', 'importes', 'esquemas', 'descuentos', 'informativos', 'movimientos'] and set(sec.values()) == {'igual'},
       'K11 Las 9 secciones de la huella, todas «Sin cambios desde la firma»', json.dumps(sec))
    ok('registrada' in texto(pg, '#inc-r-msg').lower(), 'K11 Mensaje de firma registrada', texto(pg, '#inc-r-msg'))
    pg.screenshot(path=f'{OUT}/K_escritorio_firmado.png', full_page=True)

    print('== K12 · Cambio después de firmar ==')
    linea = sql(f"select id from public.inc_importes where version_id = '{VA}' and personal_id = '{P['A3']}' limit 1")
    sql(f"select public.inc_decidir_importe('{linea}', 321, 'Ajuste UI concentrado')", 'nomina')
    recargar(pg); c = conc()
    sec = secciones(pg); camb = c['firma']['secciones_cambiadas']
    ok(c['firma']['estado'] == 'invalidada' and pg.query_selector('#inc-c-firma [data-firma-estado="invalidada"]') is not None
       and 'Volver a firmar el periodo' in texto(pg, '#inc-c-firma #inc-r-firmar-per'), 'K12 Firma «invalidada» y botón «Volver a firmar»')
    ok(sorted(k for k, v in sec.items() if v == 'cambio') == sorted(camb) and camb == ['importes'] and pg.get_attribute('#inc-c-secciones', 'open') is not None,
       'K12 Secciones marcadas = secciones_cambiadas de la base (importes); el panel se abre solo', json.dumps(sec))
    pg.click('#inc-c-firma #inc-r-firmas-hist summary'); pg.wait_for_timeout(200)
    ok(pg.query_selector('#inc-c-firma [data-firma-hist="invalidada"]') is not None and 'cambió: importes' in texto(pg, '#inc-c-firma #inc-r-firmas-hist'),
       'K12 El historial identifica la firma invalidada y qué cambió')
    pg.screenshot(path=f'{OUT}/K_escritorio_invalidada.png', full_page=True)

    print('== K21 · Desde «Hojas» no se firma como Nómina ==')
    pg.click('#inc-r-pestanas [data-r-pest="hojas"]'); pg.wait_for_selector('#inc-r-tablero', timeout=15000); pg.wait_for_timeout(800)
    ok(not bloqueantes_db() and pg.query_selector('#inc-r-firma-per [data-firma-estado="invalidada"]') is not None and pg.query_selector('#inc-r-firmar-per') is None
       and pg.query_selector('#inc-r-ir-conc') is not None, 'K21 Hojas, responsable de Nómina, sin bloqueantes y firma invalidada: no hay botón para firmar; solo el estado y el acceso al concentrado')
    pg.screenshot(path=f'{OUT}/K_escritorio_hojas_sin_firma.png', full_page=True)
    pg.click('#inc-r-ir-conc'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(1000)
    ok(pg.query_selector('#inc-c #inc-r-firmar-per') is not None and eventos_firma() == '1', 'K21 El acceso lleva a «Concentrado», donde sí está la firma; no se registró ninguna firma al navegar')
    cm, pm = abrir('nomina', 390, 844)
    pm.click('nav.tabs button[data-tab="incidencias"]'); pm.wait_for_timeout(900); pm.click('[data-inc-vista="revision"]'); pm.wait_for_timeout(900)
    pm.click(f'#inc-r-periodos [data-rev-per="{P1}"]'); pm.wait_for_selector('#inc-r-tablero', timeout=15000); pm.wait_for_timeout(1200)
    anch = pm.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    ok(pm.query_selector('#inc-r-firmar-per') is None and pm.is_visible('#inc-r-ir-conc') and anch[1] <= anch[0] + 1,
       'K21 Celular, pestaña «Hojas»: sin botón de firma de Nómina, el acceso al concentrado visible y sin desplazamiento horizontal', str(anch))
    pm.screenshot(path=f'{OUT}/K_celular_hojas_sin_firma.png', full_page=True)
    errores += pm.errores; cm.close()

    print('== K13 · Huella desactualizada ==')
    sql(f"select public.inc_decidir_importe('{linea}', 322, 'Cambio mientras se revisa')", 'nomina')   # cambia sin recargar la pantalla
    pg.click('#inc-c-firma #inc-r-firmar-per'); pg.wait_for_timeout(2000)
    ok('cambió mientras lo revisabas' in texto(pg, '#inc-r-msg') and eventos_firma() == '1', 'K13 Si cambió mientras se veía, la firma se rechaza y no se registra', texto(pg, '#inc-r-msg')[:110])

    print('== K14 · Listo para procesar ==')
    pg.click('#inc-c-firma #inc-r-firmar-per'); pg.wait_for_timeout(2000)
    for h in (HA, HB): sql(f"select public.inc_firmar_hoja('{h}','rh')", 'admin')
    recargar(pg); c = conc()
    ok(c['estado'] == 'listo' and texto(pg, '#inc-c-estado') == 'Listo para procesar' and pg.query_selector('#inc-c-sin-pendientes') is not None
       and pg.query_selector('[data-firma-hist="reemplazada"]') is not None, 'K14 Sin pendientes: «Listo para procesar», igual a la base; la firma anterior queda «reemplazada»', c['estado'])

    print('== K5b · Totales con importes decididos ==')
    num_mx = lambda t: float(t.split('$')[-1].replace(',', ''))
    chips = {e.get_attribute('data-tot-imp'): e for e in pg.query_selector_all('#inc-c-tot-imp [data-tot-imp]')}
    db_imp = {f'{cid}:{m}': float(v) for cid, mods in c['totales']['importes'].items() for m, v in mods.items()}
    ok(set(chips) == set(db_imp) and {k.split(':')[1] for k in db_imp} >= {'bruto', 'neto'}, 'K5b Un total por concepto y modalidad, los mismos de la base (hay bruto y neto)', str(sorted(db_imp)))
    ok(all(abs(num_mx(chips[k].inner_text()) - v) < 0.005 for k, v in db_imp.items()), 'K5b Cada cifra es la de la base', json.dumps(db_imp))
    ok(all(len(e.query_selector_all('.inc-mod')) == 1 for e in chips.values()) and pg.query_selector('#inc-c-tot-imp [data-tot-imp-pend]') is None,
       'K5b Ningún total mezcla modalidades (cada cifra lleva una sola); ya no hay importes por decidir')

    print('== K17 · Sin firma de Nómina por hoja ==')
    pg.click('#inc-c-hojas summary'); pg.wait_for_timeout(200)
    ok(pg.query_selector('#inc-c [data-firmar="nomina"]') is None and all(t in ('✓ RH',) for t in textos(pg, '#inc-c-hojas td[data-l="Firma RH"]'))
       and 'Nómina' not in texto(pg, '#inc-c-hojas table'), 'K17 Las hojas muestran solo la firma de RH; no hay firma de Nómina por hoja', str(textos(pg, '#inc-c-hojas td[data-l="Firma RH"]')))

    print('== K18 · Pestaña Hojas ==')
    pg.click('#inc-r-pestanas [data-r-pest="hojas"]'); pg.wait_for_timeout(1800)
    ok(pg.query_selector('#inc-r-tablero') is not None and pg.query_selector('#inc-r-firma-per [data-firma-estado="vigente"]') is not None and not pg.is_disabled('#inc-r-proc'),
       'K18 La pestaña «Hojas» muestra el tablero con la misma firma vigente y permite procesar')
    proc_antes = None
    pg.click('#inc-r-proc'); pg.wait_for_timeout(2000)
    proc_antes = sql(f"select procesado_en from public.inc_periodos where id='{P1}'")
    recargar(pg); c = conc()
    print('== K15 · Procesado ==')
    ok(c['estado'] == 'procesado' and texto(pg, '#inc-c-estado') == 'Procesado' and pg.query_selector('#inc-c-pendientes') is None
       and pg.query_selector('#inc-r-firmar-per') is None and pg.query_selector('#inc-c-firma [data-firma-estado="vigente"]') is not None
       and pg.query_selector('#inc-c-post') is None, 'K15 Procesado: sin pendientes ni botón; firma vigente visible; sin aviso de cambios', c['estado'])

    print('== K16 · Cambio después de procesar ==')
    sql(f"insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, causa, origen) values ('{T}','{P['A2']}','{RLB['A2']}','modificacion_salario','{d(4)}',null,'pantalla')", replica=True)
    recargar(pg); c = conc(); post = c['avisos']['cambio_posterior_procesado']
    ui_sec = (pg.get_attribute('#inc-c-post', 'data-secciones') or '').split(',')
    ok(post and ui_sec == post['secciones'] == ['movimientos'] and 'movimientos laborales' in texto(pg, '#inc-c-post'),
       'K16 Aviso de cambio después de procesar con las secciones de la base (movimientos)', texto(pg, '#inc-c-post').replace('\n', ' ')[:160])
    ok('no lo reabre' in texto(pg, '#inc-c-post') and c['estado'] == 'procesado' and texto(pg, '#inc-c-estado') == 'Procesado'
       and sql(f"select procesado_en from public.inc_periodos where id='{P1}'") == proc_antes and pg.query_selector('#inc-r-firmar-per') is None,
       'K16 El periodo NO se reabre: sigue procesado, misma fecha, sin botones')
    ok(c['firma']['estado'] == 'invalidada' and c['firma']['secciones_cambiadas'] == ['movimientos'] and pg.query_selector('#inc-c-firma [data-firma-estado="invalidada"][data-firma-procesado]') is not None
       and 'autorizó lo que se procesó' in texto(pg, '#inc-c-firma') and 'no se vuelve a firmar' in texto(pg, '#inc-c-firma'),
       'K16 La firma se muestra invalidada (movimientos), igual a la base, explicando que autorizó lo procesado y que no se vuelve a firmar', texto(pg, '#inc-c-firma')[:140])
    ok(secciones(pg).get('movimientos') == 'post' and sum(1 for v in secciones(pg).values() if v == 'post') == 1, 'K16 La sección marcada como «Cambió después de procesar» es solo movimientos')
    pg.screenshot(path=f'{OUT}/K_escritorio_post_procesado.png', full_page=True)
    errores += pg.errores; ctx.close()

    print('== K22 · El código solo firma desde el concentrado ==')
    fuente = open(os.path.join(os.path.dirname(os.path.abspath(HTML)), 'incidencias.js'), encoding='utf-8').read()
    import re as _re
    def cuerpo(nombre):   # texto de la función hasta la siguiente «async function»/«function» del mismo nivel
        i = fuente.index(f'async function {nombre}()'); j = _re.search(r'\n  (async )?function ', fuente[i + 10:]); return fuente[i: i + 10 + (j.start() if j else len(fuente))]
    ok(fuente.count("'inc_firmar_periodo'") == 1 and fuente.count('conectarFirmaPeriodo(') == 2 and 'conectarFirmaPeriodo(' in cuerpo('revConcentrado')
       and 'conectarFirmaPeriodo(' not in cuerpo('revPeriodo') and "'inc_firmar_periodo'" not in cuerpo('revPeriodo') and 'soloEstado: true' in cuerpo('revPeriodo'),
       'K22 Una sola llamada a inc_firmar_periodo, conectada solo en el concentrado; la pestaña «Hojas» usa el bloque en modo solo estado')
    ok("bloqueFirma('rh'" in fuente and "bloqueFirma('nomina'" not in fuente and 'data-firmar="nomina"' not in fuente and "'inc_firmar_hoja'" in fuente,
       'K22 La hoja solo construye el botón de firma de RH (inc_firmar_hoja); no existe botón de firma de Nómina por hoja')

    print('== K23 · Periodo procesado con la regla anterior (antes de B-a) ==')
    # Se simula exactamente el dato que hay en beehuman-pruebas: periodo procesado con firma de Nómina POR HOJA y
    # evento «procesado» sin huella (B-a aún no existía). Se crea con la regla anterior, en modo réplica.
    P0 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','{d(-7)}','{d(-1)}')", 'nomina')
    H0 = sql(f"select public.inc_abrir_hoja('{P0}')", 'coordA')
    V0 = sql(f"select public.inc_enviar_hoja('{H0}')", 'coordA')
    sql(f"""update public.inc_periodos set procesado_en = now() - interval '3 days', procesado_por = '{U['nomina']}' where id = '{P0}';
      update public.inc_hojas set estado = 'procesada' where id = '{H0}';
      insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre) values
        ('{T}','{H0}','{P0}','{V0}','firma_nomina','{U['nomina']}','nomina antigua por hoja');
      insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre) values ('{T}','{P0}','procesado','{U['nomina']}','nomina antigua')""", replica=True)
    c0 = json.loads(sql(f"select public.inc_concentrado_periodo('{P0}')", 'nomina'))
    ctx, pg = abrir('nomina')
    pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900); pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(900)
    pg.click(f'#inc-r-periodos [data-rev-per="{P0}"]'); pg.wait_for_selector('#inc-r-tablero', timeout=15000); pg.wait_for_timeout(1200)
    th = texto(pg, '#inc-r-firma-per')
    ok(c0['estado'] == 'procesado' and c0['firma']['estado'] == 'sin_firma' and pg.query_selector('#inc-r-firma-per [data-firma-regla-anterior]') is not None
       and 'Falta la firma' not in th and pg.query_selector('#inc-r-firma-per .inc-chip.alerta') is None and pg.query_selector('#inc-r-firmar-per') is None,
       'K23 Hojas: periodo procesado con la regla anterior; sin «Falta la firma», sin alerta roja y sin botón', th[:140])
    pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(1000)
    tc = texto(pg, '#inc-c-firma'); sec0 = secciones(pg)
    ok(pg.query_selector('#inc-c-firma [data-firma-regla-anterior]') is not None and 'Falta la firma' not in tc and pg.query_selector('#inc-c-firma .inc-chip.alerta') is None
       and texto(pg, '#inc-c-estado') == 'Procesado' and pg.query_selector('#inc-c-pendientes') is None and pg.query_selector('#inc-c-post') is None,
       'K23 Concentrado: «Procesado con la regla anterior», sin alerta, sin pendientes y sin aviso de cambios', tc[:140])
    ok(set(sec0.values()) == {'regla_anterior'} and len(sec0) == 9, 'K23 Las 9 secciones dicen «Procesado con la regla anterior (firma por hoja)», no «Sin firmar»', json.dumps(sec0))
    pg.click('#inc-c-firma #inc-r-firmas-hist summary'); pg.wait_for_timeout(200)
    ok('regla anterior, con la que se procesó' in texto(pg, '#inc-c-firma #inc-r-firmas-hist') and 'ya no autoriza' not in texto(pg, '#inc-c-firma #inc-r-firmas-hist'),
       'K23 El historial muestra la firma por hoja como la regla con la que se procesó', texto(pg, '#inc-c-firma #inc-r-firmas-hist')[:140])
    pg.screenshot(path=f'{OUT}/K_escritorio_procesado_regla_anterior.png', full_page=True)
    errores += pg.errores; ctx.close()

    print('== K19 · Celular ==')
    ctx, pg = abrir('nomina', 390, 844); concentrado(pg)
    pg.click(f'[data-c-det="{P["A1"]}"]'); pg.wait_for_timeout(300)
    med = pg.evaluate("""() => { const r = document.documentElement; const th = document.querySelector('#inc-c-tabla thead');
      const tr = document.querySelector('#inc-c-tabla tr.inc-c-fila'); const w = document.querySelector('#inc-c-tabla-cont .inc-tabla-wrap');
      return [r.clientWidth, r.scrollWidth, th ? getComputedStyle(th).display : null, tr ? getComputedStyle(tr).display : null, w ? [w.clientWidth, w.scrollWidth] : null]; }""")
    ok(med[1] <= med[0] + 1 and med[4] and med[4][1] <= med[4][0] + 1, 'K19 Celular: sin desplazamiento horizontal (página y tabla)', str(med))
    ok(med[2] == 'none' and med[3] == 'block', 'K19 Celular: cada persona se muestra como tarjeta (sin encabezados de tabla)', str(med[2:4]))
    est_db = conc()['firma']['estado']
    ok(pg.is_visible('#inc-c-post') and pg.is_visible(f'#inc-c-firma [data-firma-estado="{est_db}"]'), 'K19 Celular: aviso y estado de la firma visibles', est_db)
    pg.screenshot(path=f'{OUT}/K_celular_concentrado.png', full_page=True)
    errores += pg.errores; ctx.close()
    ok(not errores, 'K20 Sin errores de JavaScript', '; '.join(errores)[:200])
    b.close()

print('== Red: ninguna conexión fuera del equipo ==')
sb_local = [r for r in RED if r[2] == f'{REF}.supabase.co']
ok(sb_local and all(r[0] == 'local' for r in sb_local), f'RED Las {len(sb_local)} peticiones dirigidas a la dirección de beehuman-pruebas se respondieron en local (base bhui); ninguna salió', str(len(sb_local)))
ok(not [r for r in RED if r[0] not in ('local', 'abortada', 'archivo_local')], 'RED Ninguna petición ni websocket se dejó pasar a internet',
   str(sorted({(r[0], r[2]) for r in RED if r[0] not in ('local', 'archivo_local')}))[:200])
ok(all(r[1] == 'file' for r in RED if r[0] == 'archivo_local'), 'RED Lo que no se intercepta son solo archivos locales (file://)')
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
