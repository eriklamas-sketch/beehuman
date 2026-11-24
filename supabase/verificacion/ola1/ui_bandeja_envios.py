"""B6 · Pantalla «Envíos» y aviso en el botón «Incidencias» (datos ficticios, base local bhui; con PGRST=1 contra PostgREST local).
Semilla propia (tenant «TENANT UI B6»): P1 original nuevo con importe por decidir · P2 devuelto y reenviado (v1 reemplazada, v2 nueva) ·
P3 procesado con complemento posterior · P4 en la empresa B · P5 original procesada con atención automática de la carga inicial.
  U1  Aviso en el botón «Incidencias» al entrar, sin abrir la sección, igual a la base.
  U2  «Envíos» es la primera pestaña de Nómina, con el número; grupos Nuevos / En revisión / Atendidos y cerrados iguales a la base.
  U3  Cada fila: empresa, periodo, coordinador, tipo de envío, versión y fecha/hora.
  U4  Situación: «n importes por decidir» / «Importes resueltos», reemplazado, cerrado al procesar, atendido automático.
  U5  «Abrir» lleva a ESA hoja (por id) y la deja «En revisión» SIN atenderla; el aviso no baja.
  U6  «Marcar como atendido» con nota: la base guarda quién, cuándo y la nota; la fila pasa a cerrados y el aviso baja.
  U7  Complemento posterior: «Abrir» lleva al complemento, no a la original procesada.
  U8  Firmas y periodos intactos tras abrir y atender desde la pantalla.
  U9  Filtro por empresa · U10 Administrador sí; Coordinador y Consulta sin aviso ni pestaña.
  U11 Un envío nuevo aparece en el aviso al volver a la pestaña del navegador, sin recargar.
  U12 Celular sin desplazamiento horizontal · U13 sin errores de JavaScript · RED nada sale a internet.
Uso: [PGRST=1] SUPABASE_JS=<supabase.js umd> python3 ui_bandeja_envios.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64, subprocess, datetime, hmac, hashlib
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']; REF = 'sflvpgkmtaxzogpgetxn'
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', RL.DB]
def sql(q, user=None, replica=False, como_postgres=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\n"
        if not como_postgres: pre += "set local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    if err: raise RuntimeError(err)
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET') and not l.startswith('{"sub"')]; return out[-1] if out else ''

T = 'b7000000-0000-4000-8000-000000000001'
U = {k: f'b7100000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta'], 1)}
RL.U.update(U)
EA, EB = 'b7200000-0000-4000-8000-000000000001', 'b7200000-0000-4000-8000-000000000002'
SEM, IM, PRJ = 'b7300000-0000-4000-8000-000000000001', 'b7400000-0000-4000-8000-000000000001', 'b7500000-0000-4000-8000-000000000001'
HE, HEB = 'b7600000-0000-4000-8000-000000000001', 'b7600000-0000-4000-8000-000000000002'
NOM = ['CA', 'CB', 'X', 'Y', 'Z']
P = {k: f'b7700000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(NOM, 1)}
RLB = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
EMP = {'CA': EA, 'CB': EB, 'X': EA, 'Y': EA, 'Z': EB}; COORD = {'X': 'CA', 'Y': 'CA', 'Z': 'CB'}
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui.'); sys.exit(1)
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT UI B6');
insert into auth.users (id, email) select v, k||'-b6@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{EA}','{T}','EMPRESA A UI B6'),('{EB}','{T}','EMPRESA B UI B6');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS');
insert into public.proyectos (id, nombre, tenant_id) values ('{PRJ}','OBRA UI B6','{T}');
"""
for k in NOM:
    co = f"'{P[COORD[k]]}'" if k in COORD else 'null'
    seed += (f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id, proyecto_id) values "
             f"('{P[k]}','{T}','{EMP[k]}','PERSONA {k} UI B6','UB6-{k}',{co},'{PRJ}');\n"
             f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno) values "
             f"('{RLB[k]}','{T}','{P[k]}','{EMP[k]}','2025-01-01','vigente','U-{k}');\n"
             f"insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, "
             f"sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values ('{T}','{P[k]}','{RLB[k]}','{EMP[k]}','{IM}','{SEM}',3500,'bruto',7,'2025-01-01',true);\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),
 ('{U['nomina']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),
 ('{U['consulta']}','{T}','consulta',null);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values
 ('{EA}','{T}','2025-01-01','{U['nomina']}','{U['admin']}'),('{EB}','{T}','2025-01-01','{U['nomina']}',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'UB6' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{EA}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),('{HEB}','{T}','{EB}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1);
"""
sql(seed, replica=True)

L = datetime.date.fromisoformat(sql("select (date_trunc('week', public.hoy_mx() + 7))::date")) + datetime.timedelta(days=7 * 40)
dd = lambda n, k=0: (L + datetime.timedelta(days=7 * n + k)).isoformat()
fl = lambda s: f'{s[8:10]}/{s[5:7]}/{s[:4]}'
semana = [0]
def periodo(emp=EA):
    semana[0] += 1; n = semana[0]
    return sql(f"select public.inc_crear_periodo('{emp}','{SEM}','{dd(n)}','{dd(n, 6)}')", 'nomina'), n
def enviar(per, n, coord='coordA', persona='X', k=1, comp_de=None):
    H = sql(f"select public.inc_abrir_hoja('{per}'{(',' + repr(comp_de)) if comp_de else ''})", coord)
    sql(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H}','{P[persona]}','{dd(n,k)}','{HEB if persona == 'Z' else HE}',2)", coord)
    return H, sql(f"select public.inc_enviar_hoja('{H}')", coord)
def procesar(per, versiones):
    for V in versiones: sql(f"select public.inc_aceptar_sugeridos('{V}')", 'nomina')
    sql(f"select public.cred_descuentos_periodo('{per}')", 'nomina'); sql(f"select public.cred_aceptar_descuentos('{per}')", 'nomina')
    h = json.loads(sql(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))['huella_actual']['total']
    sql(f"select public.inc_firmar_periodo('{per}','{h}')", 'nomina')
    for V in versiones: sql(f"select public.inc_firmar_hoja((select hoja_id from public.inc_versiones where id='{V}'),'rh')", 'admin')
    return sql(f"select public.inc_marcar_procesado('{per}')", 'nomina')
ev = lambda V: sql(f"select id from public.inc_eventos where version_id='{V}' and tipo in ('envio','complemento')")
P1, n1 = periodo(); H1, V1 = enviar(P1, n1)                                   # nuevo, 1 importe por decidir
P2, n2 = periodo(); H2, V2a = enviar(P2, n2)
sql(f"select public.inc_devolver_hoja('{H2}','Corrige UB6','nomina')", 'nomina'); V2b = sql(f"select public.inc_enviar_hoja('{H2}')", 'coordA')
sql(f"select public.inc_aceptar_sugeridos('{V2b}')", 'nomina')                 # v2 con importes resueltos
P3, n3 = periodo(); H3, V3 = enviar(P3, n3); procesar(P3, [V3])
C3, VC3 = enviar(P3, n3, persona='Y', k=3, comp_de=H3)                          # complemento posterior
P4, n4 = periodo(EB); H4, V4 = enviar(P4, n4, 'coordB', 'Z')
P5, n5 = periodo(); H5, V5 = enviar(P5, n5); procesar(P5, [V5])
# Lo mismo que hace la carga inicial de la migración con un original de un periodo procesado antes de activar B6.
sql(f"insert into public.inc_envio_seguimiento (evento_id, tenant_id, atendida_en, atencion_tipo, motivo_atencion) values ('{ev(V5)}','{T}',now(),'automatica','Periodo procesado antes de activar B6')")
pend = lambda: json.loads(sql("select public.inc_envios_pendientes()", 'nomina'))
estado_db = lambda V: json.loads(sql(f"select b from public.inc_bandeja_envios() b where b->>'evento_id' = '{ev(V)}'", 'nomina'))
def foto(per):
    e = json.loads(sql(f"select public.inc_firma_periodo_estado('{per}')", 'nomina'))
    return (e['estado'], e['secciones_cambiadas'], (e.get('firma') or {}).get('creado_en'),
            sql(f"select coalesce(procesado_en::text,'-') from public.inc_periodos where id='{per}'"),
            sql(f"select string_agg(estado||version_actual, ',' order by id) from public.inc_hojas where periodo_id='{per}'"),
            sql(f"select public.inc_concentrado_huella('{per}')->>'total'", 'nomina', como_postgres=True))
P1b_firma = None
print('Caso:', pend())

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
RED = []
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
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(2500)
        return ctx, pg
    def aviso(pg):
        a = pg.query_selector('nav.tabs button[data-tab="incidencias"] .inc-aviso')
        return None if (a is None or not a.is_visible()) else a.inner_text().strip()
    def envios(pg):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(1200); pg.wait_for_selector('[data-inc-vista="envios"]', timeout=15000)
        pg.click('[data-inc-vista="envios"]'); pg.wait_for_selector('#inc-e-lista table, #inc-e-vacio-nuevos', timeout=15000); pg.wait_for_timeout(800)
    def fila(pg, V): return pg.query_selector(f'#inc-e-lista tr[data-evento="{ev(V)}"]')
    def grupo_de(pg, V):
        f = fila(pg, V); return f and f.evaluate("e => e.closest('table').id")
    errores = []

    print('== U1–U4 · Nómina: aviso, pestaña y filas ==')
    ctx, pg = abrir('nomina')
    pe = pend()
    ok(aviso(pg) == str(pe['total']) and pe['total'] == 4, 'U1 Aviso en el botón «Incidencias» al entrar, sin abrir la sección, igual a la base', f"{aviso(pg)} / {pe}")
    pg.screenshot(path=f'{OUT}/U1_aviso_menu.png')
    envios(pg)
    act = pg.get_attribute('[data-inc-vista="envios"]', 'class') or ''
    primera = pg.evaluate("() => document.querySelector('#inc-raiz .inc-sub button').dataset.incVista")
    ok('activo' in act and primera == 'envios' and texto(pg, '[data-inc-vista="envios"] [data-e-cuenta]') == str(pe['total']),
       'U2 «Envíos» es la primera pestaña (activa al entrar) y muestra el número', texto(pg, '[data-inc-vista="envios"]'))
    nuevos = {e.get_attribute('data-evento') for e in pg.query_selector_all('#inc-e-nuevos tbody tr')}
    cerrados = {e.get_attribute('data-evento') for e in pg.query_selector_all('#inc-e-cerrados tbody tr')}
    ok(nuevos == {ev(V1), ev(V2b), ev(VC3), ev(V4)} and pg.query_selector('#inc-e-revision') is None and {ev(V2a), ev(V3), ev(V5)} <= cerrados,
       'U2 Grupos iguales a la base: 4 nuevos, ninguno en revisión; v1 reemplazada, original procesada y atendida automática en cerrados', f'{len(nuevos)} nuevos · {len(cerrados)} cerrados')
    t1 = fila(pg, V1).inner_text()
    ok('EMPRESA A UI B6' in t1 and f'{fl(dd(n1))} – {fl(dd(n1, 6))}' in t1 and 'PERSONA CA UI B6' in t1 and 'Hoja original' in t1 and 'v1' in t1
       and estado_db(V1)['enviado_en'][:4] in t1, 'U3 Fila con empresa, periodo, coordinador, tipo, versión y fecha/hora', t1.replace('\n', ' | ')[:160])
    ok('1 importe por decidir' in t1, 'U4 Indicador «1 importe por decidir»')
    ok('Reenvío v2 (tras devolución)' in fila(pg, V2b).inner_text() and 'Importes resueltos' in fila(pg, V2b).inner_text(),
       'U4 Reenvío v2 con «Importes resueltos» (no «Revisado»)', fila(pg, V2b).inner_text().replace('\n', ' | ')[:140])
    ok('Reemplazado por la versión 2' in fila(pg, V2a).inner_text(), 'U4 Versión sustituida: «Reemplazado por la versión 2»')
    ok('Complemento posterior al procesamiento' in fila(pg, VC3).inner_text(), 'U4 Complemento posterior identificado como tal')
    ok('Cerrado al procesar el periodo' in fila(pg, V3).inner_text(), 'U4 Original procesada: «Cerrado al procesar el periodo»')
    ok('Atendido automáticamente · Periodo procesado antes de activar B6' in fila(pg, V5).inner_text() and fila(pg, V5).query_selector('[data-e-abrir]') is None,
       'U4 Carga inicial: «Atendido automáticamente · Periodo procesado antes de activar B6», sin usuario ni botón «Abrir»')
    ok(pg.query_selector_all('text=Revisado') == [], '+U4 La palabra «Revisado» no aparece como indicador')
    pg.screenshot(path=f'{OUT}/U2_envios_escritorio.png', full_page=True)

    print('== U5 · Abrir no atiende ==')
    f3a, f1a = foto(P3), foto(P1)
    pg.click(f'#inc-e-nuevos [data-e-abrir="{ev(V1)}"]'); pg.wait_for_selector('#inc-r-estado', timeout=15000); pg.wait_for_timeout(800)
    d = estado_db(V1)
    ok(pg.get_attribute('#inc-r-estado', 'data-hoja') == H1 and pg.get_attribute('#inc-r-estado', 'data-version') == '1' and 'activo' in (pg.get_attribute('[data-inc-vista="revision"]', 'class') or ''),
       'U5 «Abrir» lleva a esa hoja (mismo id) y versión, en «Revisión»', pg.get_attribute('#inc-r-estado', 'data-hoja'))
    ok(d['estado'] == 'en_revision' and d['atendida_en'] is None and d['abierta_por'], 'U5 En la base queda «En revisión» y NO atendido', f"{d['estado']} · {d['abierta_por']}")
    ok(aviso(pg) == str(pe['total']), 'U5 El aviso no baja al abrir', aviso(pg))
    pg.screenshot(path=f'{OUT}/U5_hoja_abierta.png', full_page=True)
    envios(pg)
    ok(grupo_de(pg, V1) == 'inc-e-revision' and 'Abierto por' in fila(pg, V1).inner_text(), 'U5 Al volver, la fila está en «En revisión» con quién la abrió')

    print('== U6 · Marcar como atendido ==')
    pg.click(f'#inc-e-revision [data-e-atender="{ev(V1)}"]'); pg.wait_for_selector('#inc-e-nota', timeout=5000)
    pg.fill('#inc-e-nota', 'Revisado con CA por teléfono'); pg.screenshot(path=f'{OUT}/U6_nota.png', full_page=True)
    pg.click('#inc-e-si'); pg.wait_for_timeout(1500)
    d = estado_db(V1); quien = sql(f"select atendida_por from public.inc_envio_seguimiento where evento_id='{ev(V1)}'")
    ok(d['estado'] == 'atendido' and d['atencion_tipo'] == 'manual' and quien == U['nomina'] and d['atendida_en'] and d['nota_atencion'] == 'Revisado con CA por teléfono',
       'U6 La base guarda quién (usuario real), cuándo y la nota', f"{d['atendida_por']} · {d['nota_atencion']}")
    ok(grupo_de(pg, V1) == 'inc-e-cerrados' and 'Atendido por' in fila(pg, V1).inner_text() and 'Nota: Revisado con CA' in fila(pg, V1).inner_text(),
       'U6 La fila pasa a «Atendidos y cerrados» con quién, cuándo y la nota')
    ok(aviso(pg) == str(pe['total'] - 1) == str(pend()['total']) and texto(pg, '[data-inc-vista="envios"] [data-e-cuenta]') == str(pe['total'] - 1),
       'U6 El aviso del menú y el de la pestaña bajan en uno', f'{aviso(pg)}')
    ok(foto(P1) == f1a, 'U8 P1: abrir y atender no cambian firma, hojas, procesado ni huella')

    print('== U7 · Complemento posterior ==')
    pg.click(f'#inc-e-nuevos [data-e-abrir="{ev(VC3)}"]'); pg.wait_for_selector('#inc-r-estado', timeout=15000); pg.wait_for_timeout(800)
    ok(pg.get_attribute('#inc-r-estado', 'data-hoja') == C3 and '· complemento' in texto(pg, '.inc-cab h2'), 'U7 «Abrir» del complemento lleva al complemento, no a la original', texto(pg, '.inc-cab h2'))
    ok(estado_db(VC3)['estado'] == 'en_revision' and estado_db(V3)['estado'] == 'cerrado_procesado', 'U7 El complemento queda en revisión; la original procesada no cambia')
    envios(pg); pg.click(f'#inc-e-revision [data-e-atender="{ev(VC3)}"]'); pg.wait_for_selector('#inc-e-nota'); pg.click('#inc-e-si'); pg.wait_for_timeout(1500)
    ok(estado_db(VC3)['estado'] == 'atendido' and estado_db(VC3)['nota_atencion'] is None, 'U7 Atender sin nota: atendido, nota vacía')
    ok(foto(P3) == f3a and f3a[3] != '-', 'U8 P3 procesado: sigue procesado; firma, hojas y huella idénticas tras abrir y atender el complemento', f3a[0])

    print('== U9 · Filtro por empresa ==')
    pg.select_option('#inc-e-emp', EB); pg.wait_for_timeout(1200)
    filas = [e.inner_text() for e in pg.query_selector_all('#inc-e-lista tbody tr')]
    ok(filas and all('EMPRESA B UI B6' in t for t in filas), 'U9 Filtro por empresa: solo la empresa B', str(len(filas)))
    errores += pg.errores

    print('== U11 · Aviso al volver a la pestaña ==')
    P6, n6 = periodo(); H6, V6 = enviar(P6, n6)
    antes = aviso(pg)
    pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(1500)
    ok(antes == str(pe['total'] - 2) and aviso(pg) == str(pe['total'] - 1) == str(pend()['total']), 'U11 Un envío nuevo aparece en el aviso al volver a la pestaña, sin recargar', f'{antes} → {aviso(pg)}')
    errores += pg.errores; ctx.close()

    print('== U10 · Roles ==')
    ctx, pg = abrir('admin')
    ok(aviso(pg) == str(pend()['total']), 'U10 Administrador: ve el aviso', aviso(pg))
    envios(pg); ok(fila(pg, V6) is not None, 'U10 Administrador: ve la bandeja')
    errores += pg.errores; ctx.close()
    for quien in ('coordA', 'consulta'):
        ctx, pg = abrir(quien)
        tab = pg.query_selector('nav.tabs button[data-tab="incidencias"]')
        sin_aviso = aviso(pg) is None
        if tab and tab.is_visible(): tab.click(); pg.wait_for_timeout(1200)
        ok(sin_aviso and pg.query_selector('[data-inc-vista="envios"]') is None and pg.query_selector('#inc-e-lista') is None, f'U10 {quien}: sin aviso ni pestaña «Envíos»')
        errores += pg.errores; ctx.close()

    print('== U12 · Celular ==')
    ctx, pg = abrir('nomina', 390, 844); envios(pg)
    anch = pg.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    pg.screenshot(path=f'{OUT}/U12_envios_celular.png', full_page=True)
    bt = pg.query_selector(f'#inc-e-nuevos [data-e-abrir="{ev(V6)}"]'); bt.scroll_into_view_if_needed()
    ok(bt.is_visible() and anch[1] <= anch[0] + 1, 'U12 Celular: filas como tarjetas, «Abrir» visible y sin desplazamiento horizontal', str(anch))
    pg.click(f'#inc-e-nuevos [data-e-atender="{ev(V6)}"]'); pg.wait_for_selector('#inc-e-nota')
    anch2 = pg.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    ok(anch2[1] <= anch2[0] + 1 and pg.is_visible('#inc-e-si'), 'U12 Celular: la nota y «Confirmar atendido» caben sin desplazamiento', str(anch2))
    pg.screenshot(path=f'{OUT}/U12_nota_celular.png', full_page=True)
    errores += pg.errores; ctx.close()
    ok(not errores, 'U13 Sin errores de JavaScript', '; '.join(errores)[:200])
    b.close()

sb_local = [r for r in RED if r[2] == f'{REF}.supabase.co']
ok(sb_local and all(r[0] == 'local' for r in sb_local), f'RED Las {len(sb_local)} peticiones a la dirección de beehuman-pruebas se respondieron en local', str(len(sb_local)))
ok(not [r for r in RED if r[0] not in ('local', 'abortada', 'archivo_local')], 'RED Nada sale a internet')
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd_ in malas: print('  FALLA:', nn, dd_)
sys.exit(1 if malas else 0)
