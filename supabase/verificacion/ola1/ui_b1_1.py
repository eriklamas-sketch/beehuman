"""B1.1 · Pruebas de aceptación en pantalla del valor por hora configurable, contra la base LOCAL
(Postgres + PostgREST en :3010) con Ola 1 + fase 1 + B2 + B1 + B1.1 y datos FICTICIOS.
Criterios (claude/B1-1-valor-hora-criterios-aceptacion-12nov.md):
  C1 Columnas: concepto, cantidad, valor por hora, cálculo («9 h × $50.00 × 2 + 5 h × $50.00 × 3»), sugerido, final, esquema.
  C2 Línea del sueldo: valor por hora del esquema y su origen («sueldo de IMSS ÷ 8 h»).
  C3 Línea por asignar: destacada, con selector de los esquemas vigentes de esa persona; bloquea el procesado.
  C4 Modificar sin motivo: no se permite.
  C5 Dos ajustes con motivo: sugerido intacto, final nuevo y bitácora visible con ambos.
  C6 El coordinador ve las horas extra sin importe (el importe lo decide Nómina) y nunca pide bitácora ni esquemas.
  E1 El Administrador configura factor doble, umbral vacío, horas sencillas y esquema preferido.
  E2 Nómina ve la configuración en solo lectura.
  Sin errores de JavaScript; en celular la revisión no desborda la página.
Uso: python3 ui_b1_1.py <index.html> <carpeta_capturas>"""
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
EFE = '0f000000-0000-4000-8000-000000000002'
HET, HES = '0e300000-0000-4000-8000-000000000011', '0e300000-0000-4000-8000-000000000012'
sql(f"""
insert into public.clasificaciones_personal (id, tenant_id, nombre, activo) values ('{EFE}','{T}','EFECTIVO',true);
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, empresa_id)
 select '{T}', '{P['ADELA']}', rl.id, '{EFE}', '0e000000-0000-4000-8000-000000000007', 700, 'neto', 7, '2025-01-01', '{E1}'
 from public.relaciones_laborales rl where rl.personal_id = '{P['ADELA']}';
update public.inc_parametros set responsable_nomina_user = '{U['nomina']}', jornada_horas = 8, umbral_triples_semana = 9, factor_doble = 2, factor_triple = 3 where empresa_id = '{E1}';
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HET}','{T}','{E1}','Horas extra tarifa','HET','horas','horas_extra','tarifa',50,null,1),
 ('{HES}','{T}','{E1}','Horas extra sueldo','HES','horas','horas_extra','beehuman',null,null,2)""", replica=True)
PER = sql(f"select public.inc_crear_periodo('{E1}','0e000000-0000-4000-8000-000000000007','2026-11-02','2026-11-08')", 'nomina')
H = sql(f"select public.inc_abrir_hoja('{PER}')", 'coord')
sql(f"""insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values
 ('{H}','{P['BENITO']}','2026-11-02','{HET}',6), ('{H}','{P['BENITO']}','2026-11-03','{HET}',8),
 ('{H}','{P['ADELA']}','2026-11-02','{HET}',2), ('{H}','{P['CESAR']}','2026-11-04','{HES}',1)""", 'coord')

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

with sync_playwright() as p:
    b = p.chromium.launch()
    # ============ C6: coordinador antes de enviar ============
    ctx, pg = abrir(b, 'coord'); incidencias(pg)
    pg.click('[data-inc-hoja]'); espera(pg, 1500)
    tot = texto(pg, f'[data-tot="{P["BENITO"]}|{HET}"]')
    ok(tot.startswith('14') and '$' not in tot, 'C6 El coordinador ve 14 horas extra de BENITO sin importe (el importe con dobles y triples lo decide Nómina)', tot.replace('\n', ' '))
    ok(not pg.errores, 'Coordinador: sin errores de JavaScript', str(pg.errores[:2])); ctx.close()
    sql(f"select public.inc_enviar_hoja('{H}')", 'coord')

    # ============ Nómina: revisión ============
    ctx, pg = abrir(b, 'nomina'); abrir_hoja_revision(pg)
    cab = pg.eval_on_selector_all('#inc-r-importes thead th', 'els => els.map(e => e.textContent.trim())')
    ok(all(x in cab for x in ('Concepto', 'Cantidad', 'Valor por hora', 'Cálculo', 'Esquema de pago', 'Sugerido', 'Final')), 'C1 Columnas de la revisión', ' | '.join(cab))
    celda = lambda lid, attr: pg.eval_on_selector(f'#inc-r-importes tr[data-linea="{lid}"] [{attr}]', 'e => e.innerText.replace(/\\s+/g," ").trim()')
    lb = linea(pg, 'BENITO')[0]
    ok(celda(lb['id'], 'data-calculo') == '9 h × $50.00 × 2 + 5 h × $50.00 × 3' and '1,650.00' in lb['txt'],
       'C1 BENITO 14 h por tarifa (6 lunes + 8 martes): «9 h × $50.00 × 2 + 5 h × $50.00 × 3» = $1,650.00', celda(lb['id'], 'data-calculo'))
    ok(celda(lb['id'], 'data-valor-hora') == '$50.00 tarifa' and 'único esquema vigente' in lb['txt'] and lb['cat'] == 'bruto', 'C1 Valor por hora $50.00 (tarifa); ligado a su único esquema (IMSS bruto)', celda(lb['id'], 'data-valor-hora'))
    # B1.1a: el esquema se asigna solo, pero el importe llega por decidir
    ok(lb['origen'] == 'pendiente' and 'Por decidir' in lb['txt'] and pg.query_selector(f'[data-aceptar="{lb["id"]}"]') is not None, 'B1.1a La línea con esquema automático llega «Por decidir», con su botón Aceptar', lb['txt'][-60:])
    lc = linea(pg, 'CESAR')[0]
    ok(celda(lc['id'], 'data-valor-hora') == '$50.00 sueldo de IMSS ÷ 8 h' and celda(lc['id'], 'data-calculo') == '1 h × $50.00 × 2' and '100.00' in lc['txt'],
       'C2 Línea del sueldo: $12,000/30 ÷ 8 = $50.00 por hora (sueldo de IMSS) → 1 h × $50.00 × 2 = $100.00', celda(lc['id'], 'data-valor-hora') + ' / ' + celda(lc['id'], 'data-calculo'))
    la = linea(pg, 'ADELA')[0]
    clase = pg.eval_on_selector(f'#inc-r-importes tr[data-linea="{la["id"]}"]', 'e => e.className')
    opciones = pg.eval_on_selector_all(f'[data-esq="{la["id"]}"] option', 'els => els.map(e => e.textContent.trim())')
    ok(la['origen'] == 'por_asignar' and 'inc-por-asignar' in clase and 'Esquema por asignar' in la['txt'] and '200.00' in la['txt'], 'C3 ADELA (IMSS y EFECTIVO) sin preferido: $200.00 «Esquema por asignar», destacada', la['txt'][:110])
    ok(len(opciones) == 3 and any('IMSS · Bruto' in o for o in opciones) and any('EFECTIVO · Neto' in o for o in opciones), 'C3 El selector ofrece solo sus esquemas vigentes (IMSS bruto y EFECTIVO neto)', ' | '.join(opciones))
    ok(pg.query_selector(f'[data-final="{la["id"]}"]') is None and pg.is_visible('#inc-r-porasignar'), 'C3 Sin esquema no se decide el importe; aviso de líneas por asignar')
    pg.screenshot(path=f'{OUT}/b11_01_revision.png', full_page=True)
    pg.click('#inc-r-volver'); espera(pg, 1200)
    falta = texto(pg, '#inc-r-faltantes')
    ok('ADELA PALACIOS GALVAN · Horas extra tarifa: esquema de pago por asignar' in falta and pg.is_disabled('#inc-r-proc'), 'C3 El tablero lo lista entre lo que falta y no deja procesar', falta[:160])
    pg.click('#inc-r-tablero [data-rev-hoja]'); espera(pg, 1200)
    efe = pg.eval_on_selector(f'[data-esq="{la["id"]}"]', "s => [...s.options].find(o => o.textContent.includes('EFECTIVO')).value")
    pg.select_option(f'[data-esq="{la["id"]}"]', efe); pg.click(f'[data-asignar="{la["id"]}"]'); espera(pg, 1300)
    la2 = linea(pg, 'ADELA')[0]
    ok(la2['cat'] == 'neto' and la2['origen'] == 'pendiente' and 'asignado por Nómina' in la2['txt'], 'C3 Nómina asigna EFECTIVO: neto, por decidir, «asignado por Nómina»', la2['txt'][:110])
    ok(pg.query_selector('#inc-r-ajustes tr[data-ajuste="esquema"]') is not None and 'por asignar → EFECTIVO' in texto(pg, '#inc-r-ajustes'), 'C3 La asignación aparece en la bitácora', texto(pg, '#inc-r-ajustes')[:120])
    # C4 / C5
    lb = linea(pg, 'BENITO')[0]
    pg.fill(f'[data-final="{lb["id"]}"]', '1600'); pg.click(f'[data-guardar="{lb["id"]}"]'); espera(pg, 800)
    ok('motivo' in texto(pg, '#inc-r-msg').lower() and linea(pg, 'BENITO')[0]['origen'] == 'pendiente', 'C4 Modificar sin motivo no se permite (la línea sigue por decidir)', texto(pg, '#inc-r-msg'))
    pg.fill(f'[data-final="{lb["id"]}"]', '1600'); pg.fill(f'[data-motivo="{lb["id"]}"]', 'Se pagan 13 h'); pg.click(f'[data-guardar="{lb["id"]}"]'); espera(pg, 1300)
    lb = linea(pg, 'BENITO')[0]
    pg.fill(f'[data-final="{lb["id"]}"]', '1620'); pg.fill(f'[data-motivo="{lb["id"]}"]', 'Ajuste acordado'); pg.click(f'[data-guardar="{lb["id"]}"]'); espera(pg, 1300)
    lb = linea(pg, 'BENITO')[0]
    bit = pg.eval_on_selector_all('#inc-r-ajustes tr[data-ajuste="importe"]', 'els => els.map(e => e.innerText.replace(/\\s+/g," ").trim())')
    ok(lb['origen'] == 'modificado' and '$1,650.00' in lb['txt'] and pg.input_value(f'[data-final="{lb["id"]}"]') == '1620' and '2 ajustes' in lb['txt'],
       'C5 Sugerido $1,650.00 intacto, final 1,620 y «2 ajustes»', lb['txt'][:120])
    ok(len(bit) == 2 and any('$1,650.00 → $1,600.00' in x and 'Se pagan 13 h' in x for x in bit) and any('$1,600.00 → $1,620.00' in x and 'Ajuste acordado' in x for x in bit),
       'C5 Bitácora con los dos ajustes: anterior, nuevo, motivo y quién', ' | '.join(bit))
    pg.screenshot(path=f'{OUT}/b11_02_ajustes.png', full_page=True)
    ok(not pg.errores, 'Nómina (revisión): sin errores de JavaScript', str(pg.errores[:2]))
    # E2 configuración en solo lectura
    pg.click('[data-inc-vista="config"]'); espera(pg, 1300)
    dis = pg.eval_on_selector_all('#inc-c-cuerpo input, #inc-c-cuerpo select', 'els => els.every(e => e.disabled)')
    ok(pg.is_visible('#inc-c-solo-lectura') and dis and not pg.is_visible('#inc-c-guardar-prm') and not pg.is_visible('#inc-k-guardar'), 'E2 Nómina ve la configuración en solo lectura (sin guardar ni editar)')
    pg.screenshot(path=f'{OUT}/b11_03_config_nomina.png', full_page=True)
    ctx.close()
    # celular
    ctx, pg = abrir(b, 'nomina', 390, 844); abrir_hoja_revision(pg)
    ancho = pg.evaluate('document.documentElement.scrollWidth')
    ok(ancho <= 392, 'Celular: la revisión no desborda la página (la tabla se desplaza dentro de su caja)', f'scrollWidth={ancho}')
    pg.screenshot(path=f'{OUT}/b11_04_celular.png', full_page=True); ctx.close()

    # ============ E1: Administrador configura ============
    ctx, pg = abrir(b, 'admin'); incidencias(pg); pg.click('[data-inc-vista="config"]'); espera(pg, 1300)
    ok(pg.is_visible('#inc-c-fdo') and pg.input_value('#inc-c-fdo') in ('2', '2.000'), 'E1 Campo «Factor de horas dobles» (2)', pg.input_value('#inc-c-fdo'))
    pg.fill('#inc-c-umb', ''); pg.fill('#inc-c-fdo', '2.5'); pg.click('#inc-c-guardar-prm'); espera(pg, 1200)
    ok(sql(f"select coalesce(umbral_triples_semana::text,'vacío')||' '||factor_doble from public.inc_parametros where empresa_id='{E1}'") == 'vacío 2.500', 'E1 Umbral vacío (sin triples) y factor doble 2.5 guardados', texto(pg, '#inc-c-msg-prm'))
    pg.fill('#inc-k-nom', 'Horas sencillas'); pg.fill('#inc-k-abr', 'HS'); pg.select_option('#inc-k-tipo', 'horas'); pg.select_option('#inc-k-modo', 'tarifa')
    pg.dispatch_event('#inc-k-modo', 'change'); pg.fill('#inc-k-tar', '50')
    ok(pg.is_visible('#inc-k-cls') and 'Nómina lo asigna' in texto(pg, '#inc-k-ayuda'), 'E1 Con tarifa aparece «Esquema preferido» y la ayuda explica la asignación', texto(pg, '#inc-k-ayuda')[:90])
    pg.select_option('#inc-k-cls', EFE); pg.click('#inc-k-guardar'); espera(pg, 1200)
    ok(sql(f"select tipo||' '||modo||' '||tarifa||' '||(clasificacion_pago_id='{EFE}') from public.inc_conceptos where abreviatura='HS' and empresa_id='{E1}'") == 'horas tarifa 50.00 true', 'E1 Concepto de horas sencillas por tarifa con esquema preferido EFECTIVO')
    fila = pg.eval_on_selector_all('#inc-c-cuerpo table.inc-lista tbody tr', "els => els.map(e => e.innerText.replace(/\\s+/g,' ').trim()).filter(t => t.startsWith('HS '))")
    ok(fila and '$50.00 por hora' in fila[0] and 'EFECTIVO' in fila[0], 'E1 La lista muestra valor y esquema preferido', fila[0] if fila else '')
    pg.screenshot(path=f'{OUT}/b11_05_config_admin.png', full_page=True)
    ok(not pg.errores, 'Administrador: sin errores de JavaScript', str(pg.errores[:2])); ctx.close()
    b.close()

malas = [x for x in peticiones['coord'] if any(k in x for k in ('inc_importes', 'inc_esquemas_asignables', 'inc_asignar', 'inc_decidir'))]
ok(not malas, 'C6 El coordinador nunca pidió importes, bitácora ni esquemas', str(malas[:3]))
total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
for n, _, d in malos: print('  FALLA:', n, d)
sys.exit(1 if malos else 0)
