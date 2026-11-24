"""Corrección «Mis hojas» (D1, D2, D3) · pruebas de pantalla contra la base LOCAL (PostgREST :3010)
con Ola 1 + fase 1 + B2 + B1 + B1.1(a,b) + B5 + la corrección, y datos FICTICIOS.
  M1 «Mis hojas» del coordinador: columna Empresa con nombre; no aparece el periodo de una empresa ajena.
  M2 Hoja vacía sin personas (como las de B5): aviso con la empresa; sin «Enviar», «Guardar» ni complemento.
  M3 Periodo con personal: «Abrir hoja» funciona y el encabezado muestra la empresa.
  M4 Nómina → Revisión del periodo con la hoja vacía: «sin personas · no bloquea», sin «Falta por enviar»,
     mensaje «No hay pendientes que bloqueen…» sin contar la hoja como no enviada; el periodo se procesa.
     Opción B (23-nov): la empresa tiene responsable de Nómina y Nómina firma el periodo en «Concentrado» antes de procesar.
  M1 también: la hoja vacía ofrece «Ver hoja», no «Capturar».
  Sin errores de JavaScript; el coordinador nunca lee la tabla empresas.
Uso: python3 ui_mis_hojas.py <index.html> <carpeta_capturas>"""
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


# ---------------- preparación (datos ficticios) ----------------
SEM = '0e000000-0000-4000-8000-000000000007'
E2, E3 = '0c000000-0000-4000-8000-0000000000e2', '0c000000-0000-4000-8000-0000000000e3'
COORD = sql(f"select personal_id from public.usuarios_tenant where user_id = '{U['coord']}'")
sql(f"""insert into public.empresas (id, tenant_id, nombre) values ('{E2}','{T}','EMPRESA AJENA UI'),('{E3}','{T}','EMPRESA HOJA VACIA UI');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial) values ('{E2}','{T}','2025-01-01');
-- Opción B (23-nov): designar al responsable de Nómina es obligatorio siempre; Nómina firma el periodo, aunque no tenga hojas enviadas.
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user) values ('{E3}','{T}','2025-01-01','{U['nomina']}')""", replica=True)
PER1 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-02','2026-11-08')", 'nomina')
PER2 = sql(f"select public.inc_crear_periodo('{E2}','{SEM}','2026-11-02','2026-11-08')", 'nomina')
PER3 = sql(f"select public.inc_crear_periodo('{E3}','{SEM}','2026-11-02','2026-11-08')", 'nomina')
HV = sql("select gen_random_uuid()")
sql(f"insert into public.inc_hojas (id, tenant_id, periodo_id, coordinador_id, tipo, hoja_raiz_id) values ('{HV}','{T}','{PER3}','{COORD}','normal','{HV}')")

def filas_mis_hojas(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#inc-h-lista tbody tr')].map(tr => [...tr.cells].map(c => c.innerText.trim()))")

with sync_playwright() as p:
    b = p.chromium.launch()
    # ============ Coordinador ============
    ctx, pg = abrir(b, 'coord')
    incidencias(pg); espera(pg, 1200)
    filas = filas_mis_hojas(pg)
    empresas_col = [f[1] for f in filas]
    ok(filas and '—' not in empresas_col, 'M1 Columna Empresa con nombre en todas las filas', str(empresas_col))
    ok('EMPRESA HOJA VACIA UI' in empresas_col and any(e for e in empresas_col if e != 'EMPRESA HOJA VACIA UI'), 'M1 Aparece su empresa y la de su hoja vacía')
    ok('EMPRESA AJENA UI' not in empresas_col, 'M1 No aparece el periodo de la empresa ajena (sin personas asignadas)')
    bot = pg.evaluate("hv => { const b = document.querySelector(`[data-inc-hoja='${hv}']`); return b ? b.textContent.trim() : '' }", HV)
    ok(bot == 'Ver hoja', 'M1 La hoja vacía sin personas ofrece «Ver hoja» (no «Capturar»)', bot)
    ok(pg.query_selector(f'[data-inc-abrir="{PER1}"]') is not None and 'Abrir hoja' in pg.inner_text(f'[data-inc-abrir="{PER1}"]'), 'M1 El periodo con personal sigue ofreciendo «Abrir hoja»')
    pg.screenshot(path=f'{OUT}/mh_01_mis_hojas.png', full_page=True)
    # M2: la hoja vacía
    pg.click(f'[data-inc-hoja="{HV}"]'); espera(pg, 1500)
    av = texto(pg, '#inc-sin-personas')
    ok('EMPRESA HOJA VACIA UI' in av and 'no bloquea' in av, 'M2 Aviso «sin personas» con el nombre de la empresa', av[:140])
    ok(not pg.query_selector('#inc-enviar') and not pg.query_selector('#inc-guardar') and not pg.query_selector('#inc-complemento') and not pg.query_selector('#inc-obs-gral'),
       'M2 Sin «Enviar», «Guardar», complemento ni observación general')
    ok('EMPRESA HOJA VACIA UI' in texto(pg, '.inc-cab'), 'M2 El encabezado de la hoja muestra la empresa')
    pg.screenshot(path=f'{OUT}/mh_02_hoja_vacia.png', full_page=True)
    ok(sql(f"select estado||' v'||version_actual from public.inc_hojas where id='{HV}'") == 'borrador v0', 'M2 La hoja vacía no cambió')
    # M3: periodo con personal
    pg.click('#inc-volver'); espera(pg, 1200)
    pg.click(f'[data-inc-abrir="{PER1}"]'); espera(pg, 1800)
    cab = texto(pg, '.inc-cab')
    ok(sql(f"select count(*) from public.inc_hojas where periodo_id='{PER1}' and coordinador_id='{COORD}'") == '1' and '02/11/2026' in cab,
       'M3 «Abrir hoja» en el periodo con personal crea su hoja', cab[:120])
    ok(not pg.query_selector('#inc-sin-personas') and pg.query_selector('#inc-enviar'), 'M3 Hoja normal: sin aviso y con «Enviar y cerrar»')
    ok(len([e for e in pg.errores]) == 0, 'Coordinador: sin errores de JavaScript', str(pg.errores[:2]))
    ctx.close()
    # ============ Nómina: periodo con la hoja vacía ============
    ctx, pg = abrir(b, 'nomina')
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg)
    pg.click(f'#inc-r-periodos [data-rev-per="{PER3}"]'); espera(pg, 1500)
    ok(pg.query_selector('[data-no-bloquea]') is not None, 'M4 Tablero: la hoja vacía aparece marcada «sin personas · no bloquea»')
    ok(not pg.query_selector('#inc-r-faltan'), 'M4 No aparece en «Falta por enviar»')
    f0 = texto(pg, '#inc-r-faltantes')
    ok('Falta la firma de Nómina del periodo' in f0 and 'no ha enviado' not in f0 and 'no ha abierto' not in f0,
       'M4 Opción B: antes de firmar, solo falta la firma de Nómina del periodo; la hoja vacía no se cuenta', f0[:140])
    pg.click('#inc-r-ir-conc'); pg.wait_for_selector('#inc-c', timeout=15000); espera(pg, 800)
    pg.click('#inc-c-firma #inc-r-firmar-per'); espera(pg, 1500)
    ok(pg.query_selector('#inc-c-firma [data-firma-estado="vigente"]') is not None, 'M4 Nómina firma el periodo en «Concentrado»', texto(pg, '#inc-c-firma')[:100])
    pg.click('#inc-r-pestanas [data-r-pest="hojas"]'); pg.wait_for_selector('#inc-r-tablero', timeout=15000); espera(pg, 800)
    ok(texto(pg, '#inc-r-faltantes') == 'No hay pendientes que bloqueen el procesamiento. Las hojas sin personal asignado y sin capturas no requieren envío.',
       'M4 Mensaje: no hay pendientes que bloqueen; las hojas sin personal no requieren envío', texto(pg, '#inc-r-faltantes')[:120])
    chips = texto(pg, '#inc-r-resumen')
    ok('enviadas' not in chips and '1 hoja sin personal: no requiere envío' in chips, 'M4 Sin «0 de 1 hojas enviadas»; indica la hoja que no requiere envío', chips)
    pg.screenshot(path=f'{OUT}/mh_03_tablero_nomina.png', full_page=True)
    pg.click('#inc-r-proc'); espera(pg, 1500)
    ok(sql(f"select procesado_en is not null from public.inc_periodos where id='{PER3}'") == 't', 'M4 El periodo se procesa')
    ok(sql(f"select estado||' v'||version_actual from public.inc_hojas where id='{HV}'") == 'borrador v0', 'M4 La hoja vacía se conserva sin cambios')
    ok(not pg.errores, 'Nómina: sin errores de JavaScript', str(pg.errores[:2]))
    ctx.close()
    b.close()

ok(any('inc_empresas_visibles' in x for x in peticiones['coord']), 'Coordinador: los nombres llegan de inc_empresas_visibles')
total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
for n, _, d in malos: print('  FALLA:', n, d)
sys.exit(1 if malos else 0)
