"""B-c · Navegación «Periodos» → «Revisión» con el MISMO caso que hay en beehuman-pruebas (datos ficticios).
Semilla: las cuentas de prueba de pruebas (admin-prueba, nomina-prueba, coord-prueba, consulta-prueba) en un tenant
«PILOTO SINTETICO 500» local, y luego caso_vista_previa_b_c.sql tal cual (EMPRESA SINTETICA BC VISTA PREVIA, PV1–PV4).
  N1 «Periodos»: cada periodo de la empresa sintética tiene «Revisar», con el id de su propia fila (los de la base).
  N2 «Periodos» → «Revisar» de PV1, PV2, PV3 y PV4: abre «Revisión» en ESE periodo (fechas del encabezado), con el estado
     de firma de la base, y su «Concentrado» muestra el estado de la base para ese mismo periodo.
  N3 «Revisión» → «Revisar» de cada PV: abre el periodo correcto.
  N4 «← Periodos» regresa a la lista de revisión.
  N5 Administrador: también puede abrir desde «Periodos».
  N6 Coordinador y Consulta no tienen la pestaña «Periodos».
  N7 Celular: «Revisar» visible y funcional en «Periodos» y en «Revisión», sin desplazamiento horizontal (filas como tarjetas).
  N8 Sin errores de JavaScript · RED: nada sale a internet.
Uso: [PGRST=1] SUPABASE_JS=<supabase.js umd> python3 ui_periodos_navegacion.py <index.html> <carpeta_capturas>"""
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

U = {'admin': 'a0000000-0000-4000-8000-000000000001', 'nomina': 'a0000000-0000-4000-8000-000000000002', 'coord': 'a0000000-0000-4000-8000-000000000003',
     'consulta': 'a0000000-0000-4000-8000-000000000004'}
RL.U.update(U)
T = '19ef5c93-692e-54d8-b2a5-4268f3b7780f'
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui.'); sys.exit(1)
sql(f"""
insert into public.tenants (id, nombre) values ('{T}','PILOTO SINTETICO 500');
insert into auth.users (id, email) values ('{U['admin']}','admin-prueba@beehuman.invalid'),('{U['nomina']}','nomina-prueba@beehuman.invalid'),
 ('{U['coord']}','coord-prueba@beehuman.invalid'),('{U['consulta']}','consulta-prueba@beehuman.invalid');
insert into public.empresas (id, tenant_id, nombre) values ('e0000000-0000-4000-8000-000000000001','{T}','EMPRESA PILOTO A');
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id) values ('c0000000-0000-4000-8000-000000000001','{T}','e0000000-0000-4000-8000-000000000001','PERSONA PILOTO AABG','BEH-AABG');
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coord']}','{T}','coordinador','c0000000-0000-4000-8000-000000000001'),('{U['consulta']}','{T}','consulta',null)""", replica=True)
# La base local trae personas sembradas en modo réplica con números BEH-…: se alinea el contador (solo en la base local).
sql("select setval('personal_empleado_id_seq', greatest((select max(substr(empleado_id, 5)::int) from public.personal where empleado_id ~ '^BEH-[0-9]+$'), 1))")
# El mismo script con el que se creó el caso en beehuman-pruebas
r = subprocess.run(PSQL[:-2] + ['-d', RL.DB, '-f', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'caso_vista_previa_b_c.sql')], capture_output=True, text=True)
if 'CASO_VISTA_PREVIA_OK' not in r.stdout + r.stderr: print('No se pudo crear el caso:', (r.stderr or r.stdout)[-500:]); sys.exit(1)
PV = sql("""select string_agg(p.id::text || '|' || to_char(p.inicio,'DD/MM/YYYY') || '|' || to_char(p.fin,'DD/MM/YYYY'), ';' order by p.inicio) from public.inc_periodos p
            join public.empresas e on e.id = p.empresa_id where e.nombre = 'EMPRESA SINTETICA BC VISTA PREVIA'""")
PV = [dict(zip(('id', 'ini', 'fin'), x.split('|'))) for x in PV.split(';')]
conc = lambda pid: json.loads(sql(f"select public.inc_concentrado_periodo('{pid}')", 'nomina'))
for i, p in enumerate(PV, 1): c = conc(p['id']); p['n'] = f'PV{i}'; p['estado'] = c['estado']; p['firma'] = c['firma']['estado']
print('Caso:', ' · '.join(f"{p['n']} {p['ini']} {p['estado']}/{p['firma']}" for p in PV))

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
    errores = []
    def incidencias(pg, vista):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
        pg.click(f'[data-inc-vista="{vista}"]'); pg.wait_for_timeout(1200)
    def verificar_periodo(pg, pv, origen):
        pg.wait_for_selector('#inc-r-tablero', timeout=15000); pg.wait_for_timeout(600)
        cab = texto(pg, '.inc-cab h2'); activo = pg.get_attribute('[data-inc-vista="revision"]', 'class') or ''
        firma_ui = pg.get_attribute('#inc-r-firma-per [data-firma-estado]', 'data-firma-estado')
        ok('activo' in activo and f"{pv['ini']} – {pv['fin']}" in cab and 'EMPRESA SINTETICA BC VISTA PREVIA' in cab and firma_ui == pv['firma'],
           f"{origen} {pv['n']}: abre «Revisión» en su periodo ({pv['ini']}) con la firma de la base ({pv['firma']})", f'{cab} · {firma_ui}')
        pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(800)
        ok(pg.get_attribute('#inc-c-estado', 'data-estado') == pv['estado'] and f"{pv['ini']} – {pv['fin']}" in texto(pg, '#inc-c .inc-cab h2'),
           f"{origen} {pv['n']}: su «Concentrado» es el del mismo periodo, estado {pv['estado']}", texto(pg, '#inc-c-estado'))

    print('== N1 · «Periodos» con «Revisar» por fila ==')
    ctx, pg = abrir('nomina'); incidencias(pg, 'periodos'); pg.wait_for_selector('#inc-p-periodos', timeout=15000)
    filas = {e.get_attribute('data-periodo'): e.query_selector('[data-p-rev]') for e in pg.query_selector_all('#inc-p-periodos tbody tr')}
    ok(all(p['id'] in filas and filas[p['id']] is not None and filas[p['id']].get_attribute('data-p-rev') == p['id'] and filas[p['id']].is_visible() for p in PV),
       'N1 Cada periodo de la empresa sintética tiene «Revisar» con el id de su propia fila', f'{len(filas)} filas')
    ok(all(f is not None for f in filas.values()), 'N1 Todas las filas de «Periodos» tienen «Revisar»', str(len(filas)))
    pg.screenshot(path=f'{OUT}/N_escritorio_periodos.png', full_page=True)

    print('== N2 · «Periodos» → «Revisar» abre el periodo correcto ==')
    for pv in PV:
        incidencias(pg, 'periodos'); pg.wait_for_selector('#inc-p-periodos', timeout=15000)
        pg.click(f'#inc-p-periodos [data-p-rev="{pv["id"]}"]'); verificar_periodo(pg, pv, 'N2 Periodos →')
        if pv['n'] == 'PV2': pg.screenshot(path=f'{OUT}/N_escritorio_PV2_desde_periodos.png', full_page=True)

    print('== N3 · N4 · «Revisión» → «Revisar» y regreso ==')
    for pv in PV:
        incidencias(pg, 'revision'); pg.wait_for_selector('#inc-r-periodos', timeout=15000)
        pg.click(f'#inc-r-periodos [data-rev-per="{pv["id"]}"]'); verificar_periodo(pg, pv, 'N3 Revisión →')
    pg.click('#inc-r-volver'); pg.wait_for_timeout(1200)
    ok(pg.query_selector('#inc-r-periodos') is not None, 'N4 «← Periodos» regresa a la lista de revisión')
    errores += pg.errores; ctx.close()

    print('== N5 · Administrador ==')
    ctx, pg = abrir('admin'); incidencias(pg, 'periodos'); pg.wait_for_selector('#inc-p-periodos', timeout=15000)
    pg.click(f'#inc-p-periodos [data-p-rev="{PV[1]["id"]}"]'); verificar_periodo(pg, PV[1], 'N5 Administrador, Periodos →')
    errores += pg.errores; ctx.close()

    print('== N6 · Coordinador y Consulta ==')
    for quien in ('coord', 'consulta'):
        ctx, pg = abrir(quien)
        tab = pg.query_selector('nav.tabs button[data-tab="incidencias"]')
        if tab and tab.is_visible(): tab.click(); pg.wait_for_timeout(1200)
        ok(pg.query_selector('[data-inc-vista="periodos"]') is None and pg.query_selector('[data-p-rev]') is None, f'N6 {quien}: sin pestaña «Periodos» ni «Revisar»')
        errores += pg.errores; ctx.close()

    print('== N7 · Celular ==')
    ctx, pg = abrir('nomina', 390, 844); incidencias(pg, 'periodos'); pg.wait_for_selector('#inc-p-periodos', timeout=15000)
    anch = pg.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    pg.screenshot(path=f'{OUT}/N_celular_periodos.png', full_page=True)
    bt = pg.query_selector(f'#inc-p-periodos [data-p-rev="{PV[1]["id"]}"]'); bt.scroll_into_view_if_needed()
    ok(bt.is_visible() and anch[1] <= anch[0] + 1, 'N7 Celular: «Revisar» visible y sin desplazamiento horizontal de la página', str(anch))
    bt.click(); verificar_periodo(pg, PV[1], 'N7 Celular, Periodos →')
    incidencias(pg, 'revision'); pg.wait_for_selector('#inc-r-periodos', timeout=15000)
    anch2 = pg.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    pg.screenshot(path=f'{OUT}/N_celular_revision.png', full_page=True)
    ok(anch2[1] <= anch2[0] + 1 and pg.is_visible(f'#inc-r-periodos [data-rev-per="{PV[2]["id"]}"]'), 'N7 Celular: lista de «Revisión» sin desplazamiento horizontal, con «Revisar» visible', str(anch2))
    pg.click(f'#inc-r-periodos [data-rev-per="{PV[2]["id"]}"]'); verificar_periodo(pg, PV[2], 'N7 Celular, Revisión →')
    errores += pg.errores; ctx.close()
    ok(not errores, 'N8 Sin errores de JavaScript', '; '.join(errores)[:200])
    b.close()

sb_local = [r for r in RED if r[2] == f'{REF}.supabase.co']
ok(sb_local and all(r[0] == 'local' for r in sb_local), f'RED Las {len(sb_local)} peticiones a la dirección de beehuman-pruebas se respondieron en local', str(len(sb_local)))
ok(not [r for r in RED if r[0] not in ('local', 'abortada', 'archivo_local')], 'RED Nada sale a internet')
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
