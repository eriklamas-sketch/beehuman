"""B5 · Pruebas de aceptación en pantalla de créditos y descuentos, contra la base LOCAL
(Postgres + PostgREST en :3010) con Ola 1 + fase 1 + B2 + B1 + B1.1(a,b) + B5 y datos FICTICIOS.
  F1 Ficha → «Prestaciones y créditos»: sin el campo anterior «No. FONACOT»; lista de créditos.
  F2 Registrar FONACOT (retención por periodo; sin ella, mensaje claro) y préstamo; INFONAVIT informativo.
  F3 Editar exige motivo; la historia lo muestra. Suspender con motivo.
  P1 Revisión → periodo → «Descuentos del periodo»: líneas por decidir, informativos sin importe, faltantes.
  P2 Modificar sin motivo se rechaza; con motivo queda en la bitácora; «Aceptar los N».
  S  Periodo siguiente: muestra el saldo disponible y no deja modificar por encima.
  E1 Coordinador y Consulta: no abren la ficha ni piden datos de créditos.
  Alta sin el campo FONACOT (con aviso), celular sin desbordes y sin errores de JavaScript.
Uso: python3 ui_b5.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, hmac, hashlib, base64, subprocess
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
V21 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'v21')
REF = 'sflvpgkmtaxzogpgetxn'
SECRETO = b"beehuman-local-solo-pruebas-secreto-de-32-caracteres-o-mas"
T = '0a000000-0000-4000-8000-000000000001'; E1 = '0c000000-0000-4000-8000-000000000001'
U = {'admin': '0b000000-0000-4000-8000-000000000001', 'nomina': '0b000000-0000-4000-8000-000000000002',
     'coord': '0b000000-0000-4000-8000-000000000003', 'consulta': '0b000000-0000-4000-8000-000000000004',
     'rh': '0b000000-0000-4000-8000-000000000005', 'eder': '0b000000-0000-4000-8000-000000000006'}
P = {'ADELA': '0a100000-0000-4000-8000-000000000011', 'BENITO': '0a100000-0000-4000-8000-000000000012',
     'CESAR': '0a100000-0000-4000-8000-000000000013', 'FABIOLA': '0a100000-0000-4000-8000-000000000016'}
b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b'=')
def jwt(sub):
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64(json.dumps({"sub": sub, "role": "authenticated", "aud": "authenticated", "exp": int(time.time()) + 86400}).encode())
    return (h + b'.' + p + b'.' + b64(hmac.new(SECRETO, h + b'.' + p, hashlib.sha256).digest())).decode()
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ('set local session_replication_role = replica;\n' if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    r = subprocess.run(['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui'],
                       input=pre + q + ';\ncommit;', capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr)
    out = [l for l in r.stdout.splitlines() if l not in ('', 'SET')]
    return out[-1] if out else ''

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

# ---------------- preparación (datos ficticios) ----------------
import datetime
SEM = '0e000000-0000-4000-8000-000000000007'
RL = {k: sql(f"select id from public.relaciones_laborales where personal_id = '{P[k]}'") for k in ('ADELA', 'BENITO', 'CESAR')}
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"
CP = sql(f"select public.cred_guardar(null, {lit({'personal_id': P['BENITO'], 'tipo': 'prestamo', 'referencia': 'PR-77', 'relacion_laboral_id': RL['BENITO'], 'fecha_inicio': '2026-11-01', 'periodicidad_id': SEM, 'importe_periodo': 1500, 'monto_total': 10000})})", 'nomina')
sql(f"select public.cred_guardar(null, {lit({'personal_id': P['ADELA'], 'tipo': 'infonavit', 'referencia': '1234567890', 'relacion_laboral_id': RL['ADELA'], 'fecha_inicio': '2026-11-01', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 1850, 'infonavit_fecha_aviso': '2026-10-20'})})", 'nomina')
sql(f"update public.inc_parametros set responsable_nomina_user = '{U['nomina']}' where empresa_id = '{E1}'", replica=True)
PER = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-02','2026-11-08')", 'nomina')

CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}
peticiones = {k: [] for k in U}
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
                peticiones[quien].append(req.method + ' ' + u.path)
                destino = 'http://localhost:3010/' + u.path[len('/rest/v1/'):] + (('?' + u.query) if u.query else '')
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
    pg.goto('file://' + os.path.abspath(HTML))
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    return ctx, pg

def incidencias(pg):
    pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
def subvistas(pg):
    return pg.eval_on_selector_all('#inc-raiz [data-inc-vista]', 'els => els.map(e => e.textContent.trim())')
def espera(pg, ms=900): pg.wait_for_timeout(ms)
def texto(pg, sel):
    el = pg.query_selector(sel); return el.inner_text().strip() if el else ''
def abrir_hoja_revision(pg):
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg)
    pg.click('#inc-r-periodos [data-rev-per]'); espera(pg)
    pg.click('#inc-r-tablero [data-rev-hoja]'); espera(pg, 1200)
def linea(pg, persona, cat=None):
    return pg.evaluate("""([pid, cat]) => {
      const filas = [...document.querySelectorAll('#inc-r-importes tr')]; let actual = null; const out = [];
      for (const tr of filas) { if (tr.dataset.persona) { actual = tr.dataset.persona; continue; }
        if (tr.dataset.linea && actual === pid && (!cat || tr.dataset.cat === cat)) out.push({id: tr.dataset.linea, origen: tr.dataset.origen, cat: tr.dataset.cat, txt: tr.innerText.replace(/\\s+/g,' ').trim()}); }
      return out; }""", [P[persona], cat])

def abrir_ficha(pg, nombre):
    pg.click('nav.tabs button[data-tab="lista"]'); espera(pg, 700)
    pg.fill('#buscar-personal', nombre); espera(pg, 400)
    pg.click(f'#tabla-personal a:has-text("{nombre}")'); espera(pg, 1500)
    pg.click('[data-detail-tab="prestaciones"]'); espera(pg, 900)
def fila_cred(pg, ref):
    return pg.evaluate("ref => { const tr = [...document.querySelectorAll('#cred-lista tr[data-cred]')].find(t => t.innerText.includes(ref)); return tr ? {id: tr.dataset.cred, estado: tr.dataset.estado, txt: tr.innerText.replace(/\\s+/g,' ').trim()} : null; }", ref)

with sync_playwright() as p:
    b = p.chromium.launch()
    # ============ Administrador: ficha de CESAR ============
    ctx, pg = abrir(b, 'admin')
    abrir_ficha(pg, 'CESAR DELGADILLO HINOJOSA')
    ok(not pg.is_visible('#d-fonacot') and pg.is_visible('#cred-ficha'), 'F1 La ficha ya no muestra el campo anterior «No. FONACOT»; muestra el módulo de créditos')
    ok(pg.is_visible('#cred-lista-vacia') and 'Registrar un crédito no es descontarlo' in texto(pg, '#cred-ficha'), 'F1 Sin créditos: lo dice y explica crédito ≠ descuento')
    pg.click('#cred-nuevo'); espera(pg, 400)
    pg.select_option('#cred-tipo', 'fonacot'); espera(pg, 400)
    ok('sin prorratear' in texto(pg, '#cred-form') or 'no la prorratea' in texto(pg, '#cred-form'), 'F2 FONACOT: el formulario indica capturar la retención por periodo, sin prorrateo')
    pg.select_option('#cred-rel', RL['CESAR']); pg.fill('#cred-ref', 'FON-555'); pg.fill('#cred-ini', '2026-11-01')
    pg.click('#cred-guardar'); espera(pg, 1000)
    ok('retención de la cédula' in texto(pg, '#cred-msg'), 'F2 Sin retención por periodo: mensaje claro de la base', texto(pg, '#cred-msg'))
    pg.select_option('#cred-per', SEM); pg.fill('#cred-imp', '300'); pg.click('#cred-guardar'); espera(pg, 1300)
    f = fila_cred(pg, 'FON-555')
    ok(f and f['estado'] == 'activo' and '$300.00' in f['txt'] and 'CONSTRUCTORA ALTIPLANO DEMO' in f['txt'], 'F2 FONACOT registrado: activo, $300 por periodo, ligado a la relación (empresa)', f['txt'][:120] if f else '')
    pg.click(f'[data-cred-editar="{f["id"]}"]'); espera(pg, 400)
    pg.fill('#cred-imp', '350'); pg.click('#cred-guardar'); espera(pg, 800)
    ok('motivo' in texto(pg, '#cred-msg').lower(), 'F3 Editar sin motivo: se rechaza', texto(pg, '#cred-msg'))
    pg.fill('#cred-motivo', 'Nueva cédula'); pg.click('#cred-guardar'); espera(pg, 1300)
    pg.click(f'[data-cred-hist="{f["id"]}"]'); espera(pg, 500)
    ok('Nueva cédula' in texto(pg, '#cred-lista') and 'Alta' in texto(pg, '#cred-lista') and '$350.00' in fila_cred(pg, 'FON-555')['txt'], 'F3 La historia muestra el alta y el cambio con su motivo')
    pg.screenshot(path=f'{OUT}/b5_01_ficha.png', full_page=True)
    pg.click(f'[data-cred-estado="{f["id"]}"][data-a="suspendido"]'); espera(pg, 400)
    pg.click(f'[data-est-ok="{f["id"]}"]'); espera(pg, 600)
    ok('motivo' in texto(pg, '#cred-msg').lower(), 'F3 Suspender sin motivo: se rechaza')
    pg.fill('[data-est-motivo]', 'Suspensión por aviso'); pg.click(f'[data-est-ok="{f["id"]}"]'); espera(pg, 1300)
    ok(fila_cred(pg, 'FON-555')['estado'] == 'suspendido', 'F3 Suspendido con motivo')
    pg.click(f'[data-cred-estado="{f["id"]}"][data-a="activo"]'); espera(pg, 400)
    pg.fill('[data-est-motivo]', 'Reactivación'); pg.click(f'[data-est-ok="{f["id"]}"]'); espera(pg, 1300)
    pg.click('.detail-head-actions > button'); espera(pg, 600)
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN')
    fi = fila_cred(pg, '1234567890')
    ok(fi and 'Informativo para NOI' in fi['txt'] and fi['txt'].count('$') == 0, 'F2 INFONAVIT: informativo para NOI, sin importe por periodo', fi['txt'][:110] if fi else '')
    ok(not pg.errores, 'Administrador: sin errores de JavaScript', str(pg.errores[:2]))
    pg.click('.detail-head-actions > button'); espera(pg, 500)
    pg.click('nav.tabs button[data-tab="alta"]'); espera(pg, 600)
    ok(not pg.is_visible('#f-fonacot') and pg.is_visible('#f-creditos-aviso'), 'Alta: sin el campo FONACOT; aviso de dónde se registran los créditos')
    ctx.close()

    # ============ Nómina: descuentos del periodo ============
    ctx, pg = abrir(b, 'nomina')
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg)
    pg.click('#inc-r-periodos [data-rev-per]'); espera(pg, 1500)
    filas = pg.eval_on_selector_all('#cred-p-lineas tr[data-desc]', 'els => els.map(e => ({id: e.dataset.desc, origen: e.dataset.origen, txt: e.innerText.replace(/\\s+/g," ").trim()}))')
    lp = next((x for x in filas if 'PR-77' in x['txt']), None); lf = next((x for x in filas if 'FON-555' in x['txt']), None)
    ok(lp and lf and lp['origen'] == 'pendiente' and '$1,500.00' in lp['txt'] and '$10,000.00' in lp['txt'] and '$350.00' in lf['txt'],
       'P1 Préstamo ($1,500, saldo $10,000) y FONACOT ($350) por decidir', ' | '.join(x['txt'][:70] for x in filas))
    info = texto(pg, '#cred-p-info')
    ok('1234567890' in info and 'Cuota fija' in info and not any('1234567890' in x['txt'] for x in filas), 'P1 INFONAVIT aparece como informativo (datos para NOI), sin línea de descuento')
    ok('descuento por decidir' in texto(pg, '#inc-r-faltantes') and pg.is_disabled('#inc-r-proc'), 'P1 Faltantes incluyen los descuentos por decidir; procesar bloqueado')
    pg.fill(f'[data-final="{lp["id"]}"]', '1200'); pg.click(f'[data-guardar="{lp["id"]}"]'); espera(pg, 700)
    ok('motivo' in texto(pg, '#cred-p-msg').lower(), 'P2 Modificar sin motivo: se rechaza', texto(pg, '#cred-p-msg'))
    pg.fill(f'[data-final="{lp["id"]}"]', '1200'); pg.fill(f'[data-motivo="{lp["id"]}"]', 'Acuerdo con el trabajador'); pg.click(f'[data-guardar="{lp["id"]}"]'); espera(pg, 1500)
    t = pg.evaluate("id => document.querySelector(`#cred-p-lineas tr[data-desc='${id}']`).innerText.replace(/\\s+/g,' ')", lp['id'])
    ok('Modificado' in t and '1 ajuste' in t and 'Acuerdo con el trabajador' in t, 'P2 Con motivo: modificado y visible en la bitácora', t[:140])
    pg.click('#cred-p-aceptar-todos'); espera(pg, 1500)
    est = pg.eval_on_selector_all('#cred-p-lineas tr[data-desc]', 'els => els.map(e => e.dataset.origen)')
    ok(est and 'pendiente' not in est and not any('descuento' in x for x in pg.eval_on_selector_all('#inc-r-faltantes li', 'els => els.map(e => e.innerText)')),
       'P2 «Aceptar los N»: ya no quedan descuentos en los faltantes', str(est))
    ok(sql(f"select public.cred_saldo_actual('{CP}')") == '10000.00', 'P2 Decidir no toca el saldo (baja solo al procesar)')
    pg.screenshot(path=f'{OUT}/b5_02_periodo.png', full_page=True)
    ok(not pg.errores, 'Nómina: sin errores de JavaScript', str(pg.errores[:2]))
    ctx.close()
    ctx, pg = abrir(b, 'nomina', 390, 844)
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg); pg.click('#inc-r-periodos [data-rev-per]'); espera(pg, 1500)
    ancho = pg.evaluate('document.documentElement.scrollWidth')
    ok(ancho <= 392, 'Celular: el panel no desborda la página', f'scrollWidth={ancho}')
    pg.screenshot(path=f'{OUT}/b5_03_celular.png', full_page=True); ctx.close()

    # ============ Saldo disponible con dos periodos abiertos (revisión 13-nov 14:03) ============
    PER2 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-09','2026-11-15')", 'nomina')
    ctx, pg = abrir(b, 'nomina')
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg)
    pg.click(f'#inc-r-periodos [data-rev-per="{PER2}"]'); espera(pg, 1500)
    fila2 = pg.evaluate("() => { const r = [...document.querySelectorAll('#cred-p-lineas tr[data-desc]')].find(e => e.innerText.includes('PR-77')); return r ? {id: r.dataset.desc, txt: r.innerText.replace(/\\s+/g,' ')} : null }")
    ok(fila2 and 'Disponible $8,800.00' in fila2['txt'] and '$1,200.00 comprometido en otros periodos abiertos' in fila2['txt'],
       'S Periodo siguiente: la línea muestra el saldo disponible ($10,000 − $1,200 comprometidos en el anterior)', fila2['txt'][:160] if fila2 else '')
    pg.fill(f'[data-final="{fila2["id"]}"]', '9000'); pg.fill(f'[data-motivo="{fila2["id"]}"]', 'Intento de exceder'); pg.click(f'[data-guardar="{fila2["id"]}"]'); espera(pg, 1200)
    m = texto(pg, '#cred-p-msg')
    ok('saldo disponible' in m and '$8,800.00' in m, 'S Modificar por encima del disponible: mensaje claro y no se guarda', m[:150])
    ok(sql(f"select origen from public.cred_descuentos where id = '{fila2['id']}'") == 'pendiente', 'S … la línea sigue por decidir')
    pg.screenshot(path=f'{OUT}/b5_04_disponible.png', full_page=True)
    ok(not pg.errores, 'Nómina (periodo siguiente): sin errores de JavaScript', str(pg.errores[:2]))
    ctx.close()

    # ============ Coordinador y Consulta ============
    for quien in ('coord', 'consulta'):
        ctx, pg = abrir(b, quien)
        ok(not pg.evaluate("typeof window.credFicha === 'function' ? !!document.querySelector('#cred-lista, #cred-nuevo') : false"), f'E1 {quien}: no ve el módulo de créditos')
        ok(not pg.errores, f'E1 {quien}: sin errores de JavaScript', str(pg.errores[:2]))
        ctx.close()
    b.close()

for quien in ('coord', 'consulta'):
    malas = [x for x in peticiones[quien] if 'cred_' in x]
    ok(not malas, f'E1 {quien}: nunca pidió datos de créditos', str(malas[:3]))
total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
for n, _, d in malos: print('  FALLA:', n, d)
sys.exit(1 if malos else 0)
