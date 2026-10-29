"""Prueba de las pantallas de la Ola 1 contra la base LOCAL real (Postgres + PostgREST),
con los permisos y funciones de beehuman-pruebas. La app se abre desde el archivo;
sus llamadas a Supabase se redirigen a PostgREST local. Nada sale a Internet.
Uso: python3 ui_ola1.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, hmac, hashlib, base64, subprocess
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
V21 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'v21')
REF = 'sflvpgkmtaxzogpgetxn'
SECRETO = b"beehuman-local-solo-pruebas-secreto-de-32-caracteres-o-mas"
U = {'admin': '0b000000-0000-4000-8000-000000000001', 'nomina': '0b000000-0000-4000-8000-000000000002',
     'coord': '0b000000-0000-4000-8000-000000000003', 'consulta': '0b000000-0000-4000-8000-000000000004'}
b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b'=')
def jwt(sub):
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64(json.dumps({"sub": sub, "role": "authenticated", "aud": "authenticated", "exp": int(time.time()) + 86400}).encode())
    return (h + b'.' + p + b'.' + b64(hmac.new(SECRETO, h + b'.' + p, hashlib.sha256).digest())).decode()
def sql(q):
    return subprocess.run(['psql', '-X', '-At', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui', '-c', q], capture_output=True, text=True).stdout.strip()

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}
escrituras_coord = []
def ruta_para(quien):
    def manejar(route):
        req = route.request; u = urlparse(req.url)
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url:
            return route.fulfill(path=f'{V21}/node_modules/@supabase/supabase-js/dist/umd/supabase.js', content_type='application/javascript')
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path.startswith('/auth/v1/user'):
                return route.fulfill(json={'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated', 'email': quien + '@demo.invalid'}, headers=CORS)
            if u.path.startswith('/rest/v1/'):
                destino = 'http://localhost:3010/' + u.path[len('/rest/v1/'):] + (('?' + u.query) if u.query else '')
                if quien == 'coord' and req.method != 'GET': escrituras_coord.append(req.method + ' ' + u.path)
                r = route.fetch(url=destino)
                h = dict(r.headers); h.update(CORS)
                return route.fulfill(status=r.status, headers=h, body=r.body())
            return route.fulfill(json={}, headers=CORS)
        if u.scheme in ('http', 'https'): return route.abort()
        return route.continue_()
    return manejar

def abrir(b, quien, ancho=1440, alto=950):
    ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 800 else 2)
    sesion = {'access_token': jwt(U[quien]), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
              'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
    ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});")
    ctx.route('**/*', ruta_para(quien))
    pg = ctx.new_page(); pg.errores = []
    pg.on('pageerror', lambda e: pg.errores.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + os.path.abspath(HTML))
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    return ctx, pg

def ir_incidencias(pg):
    pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)

with sync_playwright() as p:
    b = p.chromium.launch()
    # ================= Administrador: configuración =================
    ctx, pg = abrir(b, 'admin')
    ok(pg.is_visible('nav.tabs button[data-tab="incidencias"]'), 'Administrador ve «Incidencias» en el menú')
    ir_incidencias(pg)
    pg.click('[data-inc-vista="config"]'); pg.wait_for_timeout(900)
    for plantilla in ['he', 'dom', 'tn', 'desc']:
        pg.click(f'[data-inc-plantilla="{plantilla}"]'); pg.wait_for_timeout(200)
        pg.click('#inc-k-guardar'); pg.wait_for_timeout(700)
    ok(sql("select string_agg(abreviatura||'/'||modo, ',' order by orden) from inc_conceptos") == 'HE/beehuman,DOM/beehuman,T/tarifa,DESC/tarifa',
       'Administrador agrega 4 conceptos con «Agregar rápido»', sql("select string_agg(abreviatura, ',') from inc_conceptos"))
    pg.select_option('#inc-c-base', 'bruto'); pg.click('#inc-c-guardar-prm'); pg.wait_for_timeout(700)
    ok(sql("select base_calculo from inc_parametros where empresa_id='0c000000-0000-4000-8000-000000000001'") == 'bruto', 'Parámetros guardados (base: solo bruto)')
    pg.click('[data-inc-resp="responsable_rh_user"]'); pg.wait_for_timeout(700)
    ok(sql("select responsable_rh_user from inc_parametros where empresa_id='0c000000-0000-4000-8000-000000000001'") == U['admin'], 'Administrador se designa responsable de RH')
    # tarifa por área para el turno nocturno (ACABADOS = 900)
    tid = sql("select id from inc_conceptos where abreviatura='T'")
    pg.click(f'[data-inc-editar="{tid}"]'); pg.wait_for_timeout(500)
    pg.select_option('#inc-t-area', '0d000000-0000-4000-8000-000000000002'); pg.fill('#inc-t-monto', '900'); pg.click('#inc-t-agregar'); pg.wait_for_timeout(700)
    ok(sql("select tarifa from inc_tarifas_area") == '900.00', 'Tarifa por área agregada (turno nocturno en ACABADOS: $900)')
    pg.click(f'[data-inc-editar="{tid}"]'); pg.wait_for_timeout(500)
    pg.screenshot(path=f'{OUT}/1-admin-configuracion.png', full_page=True)
    ok(not pg.errores, 'Administrador: sin errores de JavaScript', str(pg.errores[:2])); ctx.close()

    # ================= Nómina: periodo =================
    ctx, pg = abrir(b, 'nomina'); ir_incidencias(pg)
    ok(not pg.is_visible('[data-inc-vista="config"]'), 'Nómina no ve la configuración')
    pg.fill('#inc-p-ini', '2026-10-19'); pg.dispatch_event('#inc-p-ini', 'change'); pg.click('#inc-p-crear'); pg.wait_for_timeout(700)
    ok('no hay historial' in pg.inner_text('#inc-p-msg'), 'Periodo anterior al historial: la pantalla muestra el rechazo', pg.inner_text('#inc-p-msg')[:80])
    pg.fill('#inc-p-ini', '2026-10-26'); pg.dispatch_event('#inc-p-ini', 'change')
    ok(pg.input_value('#inc-p-fin') == '2026-11-01', 'El fin se calcula con los 7 días de la periodicidad semanal')
    pg.click('#inc-p-crear'); pg.wait_for_timeout(900)
    ok(sql("select inicio||'..'||fin from inc_periodos") == '2026-10-26..2026-11-01', 'Nómina crea el periodo 26-oct a 1-nov')
    pg.screenshot(path=f'{OUT}/2-nomina-periodos.png', full_page=True)
    ok(not pg.errores, 'Nómina: sin errores de JavaScript', str(pg.errores[:2])); ctx.close()

    # ================= Consulta: no ve la sección =================
    ctx, pg = abrir(b, 'consulta')
    ok(not pg.is_visible('nav.tabs button[data-tab="incidencias"]'), 'Consulta no ve «Incidencias»'); ctx.close()

    # ================= Coordinador: hoja =================
    ctx, pg = abrir(b, 'coord')
    ok(pg.is_visible('nav.tabs button[data-tab="incidencias"]') and pg.is_visible('nav.tabs button[data-tab="equipo"]'), 'Coordinador ve «Mi equipo» e «Incidencias»')
    ir_incidencias(pg)
    pg.click('[data-inc-abrir]'); pg.wait_for_timeout(1500)
    filas = pg.locator('.inc-tabla tbody tr').count()
    ok(filas == 6, 'La hoja trae precargadas las 6 personas del coordinador', str(filas))
    P = {'ADELA': '0a100000-0000-4000-8000-000000000011', 'BENITO': '0a100000-0000-4000-8000-000000000012', 'CESAR': '0a100000-0000-4000-8000-000000000013',
         'DIANA': '0a100000-0000-4000-8000-000000000014', 'EDGAR': '0a100000-0000-4000-8000-000000000015', 'FABIOLA': '0a100000-0000-4000-8000-000000000016'}
    K = {r.split('|')[0]: r.split('|')[1] for r in sql("select abreviatura||'|'||id from inc_conceptos").splitlines()}
    def poner(sel, valor, es_select=False):
        el = pg.locator(sel)
        (el.select_option(valor) if es_select else el.fill(str(valor))); el.dispatch_event('change'); pg.wait_for_timeout(150)
    poner(f'select[data-k="{P["BENITO"]}|2026-10-27"]', 'F', True)
    poner(f'select[data-k="{P["CESAR"]}|2026-11-01"]', 'D', True)
    poner(f'input[data-obs="{P["BENITO"]}"]', 'Faltó sin aviso')
    pg.click(f'[data-inc-v="{K["HE"]}"]'); pg.wait_for_timeout(300)
    for d in ['2026-10-26', '2026-10-27', '2026-10-28']: poner(f'input[data-k="{P["ADELA"]}|{d}|{K["HE"]}"]', 4)
    poner(f'input[data-k="{P["FABIOLA"]}|2026-10-27|{K["HE"]}"]', 3)
    avisos = pg.locator('.inc-aviso').count()
    ok(avisos >= 1, 'Aviso visible: ADELA con más de 3 h extra al día', str(avisos))
    pg.screenshot(path=f'{OUT}/3-coord-horas-extra.png', full_page=True)
    pg.click(f'[data-inc-v="{K["DOM"]}"]'); pg.wait_for_timeout(300); poner(f'input[data-k="{P["ADELA"]}|2026-11-01|{K["DOM"]}"]', 1)
    pg.click(f'[data-inc-v="{K["T"]}"]'); pg.wait_for_timeout(300)
    poner(f'input[data-k="{P["CESAR"]}|2026-10-29|{K["T"]}"]', 2); poner(f'input[data-k="{P["BENITO"]}|2026-10-29|{K["T"]}"]', 1)
    pg.click(f'[data-inc-v="{K["DESC"]}"]'); pg.wait_for_timeout(300)
    poner(f'input[data-k="{P["DIANA"]}|2026-10-30|{K["DESC"]}"]', 150)
    poner(f'input[data-desc-motivo="{P["DIANA"]}"]', 'Herramienta extraviada')
    el = pg.locator(f'input[data-desc-conf="{P["DIANA"]}"]'); el.check(); el.dispatch_event('change')
    ok(pg.locator('[data-inc-v="proyecto"]').count() == 0 and pg.is_visible('#inc-nota-proyecto'), 'Proyecto por día: oculto con aviso (el coordinador no lee el catálogo de proyectos)')
    pg.fill('#inc-obs-gral', 'Semana de colado de losa en Jardines'); pg.dispatch_event('#inc-obs-gral', 'change')
    pg.click('#inc-guardar'); pg.wait_for_timeout(1500)
    ok('Borrador guardado' in pg.inner_text('#inc-msg'), 'Guardar borrador', pg.inner_text('#inc-msg')[:80])
    ok(sql("select count(*) from inc_cantidades") == '8' and sql("select count(*) from inc_celdas") == '2' and sql("select count(*) from inc_observaciones") == '1',
       'Se guardaron 8 cantidades, 2 celdas (F y D) y 1 observación',
       f"{sql('select count(*) from inc_cantidades')}/{sql('select count(*) from inc_celdas')}/{sql('select count(*) from inc_observaciones')}")
    ok(sql("select motivo||'/'||conformidad_declarada||'/'||(conformidad_por is not null) from inc_cantidades where concepto_id='%s'" % K['DESC']) == 'Herramienta extraviada/true/true',
       'Descuento con motivo y conformidad declarada (queda quién la declaró)')
    # Totales visibles para el coordinador: tarifa sí, sueldo no
    pg.click('[data-inc-v="asistencia"]'); pg.wait_for_timeout(400)
    tabla = pg.inner_text('.inc-tabla')
    ok('$1,400.00' in tabla and '$900.00' in tabla, 'Coordinador ve importes de tarifa propia: CESAR 2 × $700; BENITO 1 × $900 (tarifa de su área)')
    ok('2,250' not in pg.content() and '$0.00' not in tabla, 'Coordinador no ve importes calculados con sueldo')
    pg.screenshot(path=f'{OUT}/4-coord-asistencia.png', full_page=True)
    # Corrección en borrador: quitar una hora extra y regresar a asistencia normal
    pg.click(f'[data-inc-v="{K["HE"]}"]'); pg.wait_for_timeout(300)
    poner(f'input[data-k="{P["FABIOLA"]}|2026-10-27|{K["HE"]}"]', '')
    pg.click('#inc-guardar'); pg.wait_for_timeout(1200)
    ok(sql("select count(*) from inc_cantidades") == '7', 'Borrar una cantidad en borrador la elimina (7 restantes)')
    # Envío con confirmación
    pg.click('#inc-enviar'); pg.wait_for_timeout(300)
    ok('Confirmar' in pg.inner_text('#inc-enviar'), 'El envío pide confirmación')
    pg.click('#inc-enviar'); pg.wait_for_timeout(2000)
    ok(sql("select estado||'/'||version_actual from inc_hojas where tipo='normal'") == 'enviada/1', 'Hoja enviada: versión 1')
    ok(pg.locator('.inc-tabla input:not([disabled]), .inc-tabla select:not([disabled])').count() == 0, 'Hoja enviada: la cuadrícula queda de solo lectura')
    ok(sql("select datos->>'observacion_general' from inc_versiones") == 'Semana de colado de losa en Jardines', 'La observación general escrita antes de guardar viaja en la versión enviada')
    imp = sql(f"select sugerido from inc_importes where personal_id='{P['ADELA']}' and concepto_id='{K['HE']}'")
    ok(imp == '2250.00', 'Importe calculado en el servidor (base bruto 20,000/30; 12 h → 9 dobles + 3 triples = $2,250.00)', imp)
    pg.screenshot(path=f'{OUT}/5-coord-enviada.png', full_page=True)
    # Complemento
    pg.click('#inc-complemento'); pg.wait_for_timeout(1500)
    ok('Complemento' in pg.inner_text('#inc-vista h2'), 'Abre el complemento')
    pg.click(f'[data-inc-v="{K["HE"]}"]'); pg.wait_for_timeout(300)
    fijo = pg.locator(f'td[title="Ya enviado en la hoja original"]').count()
    ok(fijo == 3, 'En el complemento, lo ya enviado aparece fijo y no editable', str(fijo))
    poner(f'input[data-k="{P["EDGAR"]}|2026-10-30|{K["HE"]}"]', 2)
    pg.click('#inc-guardar'); pg.wait_for_timeout(1200)
    ok(sql("select count(*) from inc_cantidades c join inc_hojas h on h.id=c.hoja_id where h.tipo='complemento'") == '1', 'El complemento guarda solo lo omitido')
    ok(not pg.errores, 'Coordinador: sin errores de JavaScript', str(pg.errores[:2]))
    ok(not any('importes' in w or 'sueldos' in w for w in escrituras_coord), 'El coordinador nunca escribió importes ni sueldos', str(escrituras_coord[:3]))
    ctx.close()

    # ================= Celular =================
    ctx, pg = abrir(b, 'coord', 390, 844); ir_incidencias(pg)
    pg.click('[data-inc-hoja]'); pg.wait_for_timeout(1500)
    ancho = pg.evaluate('document.documentElement.scrollWidth')
    ok(ancho <= 392, 'Celular (390 px): la página no se desborda; la cuadrícula se desplaza dentro de su recuadro', str(ancho))
    pg.screenshot(path=f'{OUT}/6-celular-hoja.png', full_page=True)
    ctx.close(); b.close()

malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {len(res) - len(malas)} de {len(res)} OK')
for n, _, d in malas: print('  FALLA:', n, d)
