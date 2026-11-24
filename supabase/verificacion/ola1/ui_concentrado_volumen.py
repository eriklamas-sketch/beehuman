"""B-c · Rendimiento de la pantalla del concentrado con 500 personas (datos FICTICIOS, base local bhui; rest_local.py o, con PGRST=1, PostgREST local real).
  V1 La pestaña «Concentrado» con 500 personas queda dibujada (500 filas) en menos de 3 s (criterio C15 de B3).
  V2 Búsqueda y filtros responden en menos de 1 s con 500 personas.
  V3 Abrir el detalle de una persona responde en menos de 1 s.
  V4 Celular (390 px): 500 tarjetas en menos de 3 s, sin desplazamiento horizontal.
  V5 Sin errores de JavaScript.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_concentrado_volumen.py <index.html> <carpeta_capturas>"""
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

T = '1bd00000-0000-4000-8000-000000000001'
U = {k: f'1bd10000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'coordA'], 1)}
RL.U.update(U)
E1, SEM, CL, RPAT, HE = ('1bd20000-0000-4000-8000-000000000001', '1bd30000-0000-4000-8000-000000000007', '1bd40000-0000-4000-8000-000000000001',
                         '1bd40000-0000-4000-8000-000000000009', '1bd60000-0000-4000-8000-000000000001')
CO = '1bd50000-0000-4000-8000-000000000000'
N = 500
pid = lambda i: f'1bd5{i:04d}-0000-4000-8000-000000000001'
rid = lambda i: f'1bd7{i:04d}-0000-4000-8000-000000000001'
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui.'); sys.exit(1)
L = datetime.date.fromisoformat(sql("select (date_trunc('week', public.hoy_mx() + 7))::date"))
d = lambda n: (L + datetime.timedelta(days=n)).isoformat()
sql(f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT UI VOLUMEN');
insert into auth.users (id, email) select v, k||'.uivol@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA UI VOLUMEN');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo) values ('{RPAT}','{E1}','{T}','B9876543210',true);
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL}','{T}','IMSS');
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id) values ('{CO}','{T}','{E1}','COORDINADOR VOLUMEN','UV-CO');
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id)
  select ('1bd5' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{T}', '{E1}', 'PERSONA VOLUMEN ' || lpad(i::text, 3, '0'), 'UV-' || i, '{CO}' from generate_series(1, {N}) i;
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, registro_patronal_id, numero_interno)
  select ('1bd7' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{T}', ('1bd5' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{E1}', '2025-01-01', 'vigente', '{RPAT}', 'V' || i
    from generate_series(1, {N}) i;
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  select '{T}', ('1bd5' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, ('1bd7' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{E1}', '{CL}', '{SEM}', 2800 + i, 'bruto', 7, '2025-01-01', true
    from generate_series(1, {N}) i;
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),('{U['coordA']}','{T}','coordinador','{CO}');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user) values ('{E1}','{T}','2025-01-01','{U['nomina']}');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'UI VOL' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values ('{HE}','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1);
""", replica=True)
P1 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','{d(0)}','{d(6)}')", 'nomina')
H1 = sql(f"select public.inc_abrir_hoja('{P1}')", 'coordA')
sql(f"""insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) select '{H1}', ('1bd5' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{d(0)}'::date + (i % 5), case when i % 2 = 0 then 'F' else 'V' end from generate_series(1, {N}, 5) i;
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) select '{H1}', ('1bd5' || lpad(i::text, 4, '0') || '-0000-4000-8000-000000000001')::uuid, '{d(0)}', '{HE}', 1 + (i % 3) from generate_series(1, {N}) i""", 'coordA')
V1 = sql(f"select public.inc_enviar_hoja('{H1}')", 'coordA')
sql(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina')

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
    def medir_concentrado(pg):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
        pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(900)
        pg.click(f'#inc-r-periodos [data-rev-per="{P1}"]'); pg.wait_for_selector('#inc-r-tablero', timeout=30000); pg.wait_for_timeout(500)
        t0 = time.time(); pg.click('#inc-r-pestanas [data-r-pest="concentrado"]')
        pg.wait_for_function(f"document.querySelectorAll('#inc-c-tabla tr.inc-c-fila').length === {N}", timeout=30000)
        return time.time() - t0
    ctx, pg = abrir('nomina')
    tiempos = [medir_concentrado(pg)]
    for _ in range(2):
        pg.click('#inc-r-pestanas [data-r-pest="hojas"]'); pg.wait_for_selector('#inc-r-tablero', timeout=30000); pg.wait_for_timeout(300)
        t0 = time.time(); pg.click('#inc-r-pestanas [data-r-pest="concentrado"]')
        pg.wait_for_function(f"document.querySelectorAll('#inc-c-tabla tr.inc-c-fila').length === {N}", timeout=30000); tiempos.append(time.time() - t0)
    ok(max(tiempos) < 3, f'V1 Escritorio: {N} personas dibujadas en menos de 3 s', ' / '.join(f'{t:.2f} s' for t in tiempos))
    t0 = time.time(); pg.fill('#inc-c-q', 'VOLUMEN 250'); pg.wait_for_function("document.querySelectorAll('#inc-c-tabla tr.inc-c-fila').length === 1", timeout=10000); tb = time.time() - t0
    t0 = time.time(); pg.fill('#inc-c-q', ''); pg.wait_for_function(f"document.querySelectorAll('#inc-c-tabla tr.inc-c-fila').length === {N}", timeout=10000); tl = time.time() - t0
    t0 = time.time(); pg.check('#inc-c-f-inc'); pg.wait_for_timeout(50); pg.wait_for_function("document.querySelector('#inc-c-cuenta').textContent.length > 0"); tf = time.time() - t0
    pg.uncheck('#inc-c-f-inc')
    ok(max(tb, tl, tf) < 1, 'V2 Búsqueda, limpiar búsqueda y filtro responden en menos de 1 s', f'buscar {tb:.2f} s · limpiar {tl:.2f} s · filtro {tf:.2f} s')
    pg.wait_for_timeout(300)
    t0 = time.time(); pg.click(f'[data-c-det="{pid(1)}"]'); pg.wait_for_selector(f'tr[data-detalle="{pid(1)}"]', timeout=10000); td = time.time() - t0
    ok(td < 1, 'V3 Abrir el detalle de una persona en menos de 1 s', f'{td:.2f} s')
    pg.screenshot(path=f'{OUT}/V_escritorio_500.png', full_page=False)
    errores += pg.errores; ctx.close()
    ctx, pg = abrir('nomina', 390, 844)
    tm = medir_concentrado(pg)
    anch = pg.evaluate("() => [document.documentElement.clientWidth, document.documentElement.scrollWidth]")
    ok(tm < 3 and anch[1] <= anch[0] + 1, f'V4 Celular: {N} tarjetas en menos de 3 s, sin desplazamiento horizontal', f'{tm:.2f} s · {anch}')
    pg.screenshot(path=f'{OUT}/V_celular_500.png', full_page=False)
    errores += pg.errores; ctx.close()
    ok(not errores, 'V5 Sin errores de JavaScript', '; '.join(errores)[:200])
    b.close()

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
