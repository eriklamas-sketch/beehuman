"""B1 · Pruebas de aceptación de la revisión de Nómina, en pantalla, contra la base LOCAL
(Postgres + PostgREST en :3010) con Ola 1 + fase 1 + B2 + B1 y datos FICTICIOS.
Criterios definidos ANTES de ejecutar (12-nov-2026):
  R1  Solo Administrador y Nómina ven «Revisión»; Coordinador y Consulta no.
  R2  Tablero: un renglón por coordinador con gente en la empresa; muestra quién falta por enviar.
  R3  La captura enviada se ve en solo lectura.
  R4  Varias líneas por persona y concepto, una por esquema de pago (con su clasificación).
  R5  Bruto y neto separados en totales y líneas; ningún total los suma.
  R6  Esquema sin relación: «Sin sueldo», con motivo y aviso visible.
  R7  Aceptar y modificar un importe; el sueldo manual recalcula sin pisar lo modificado.
  R8  Aceptar todos los sugeridos pendientes.
  R9  Firmas: solo el responsable designado ve el botón de su área.
  R10 Devolver exige motivo; el tablero y el procesado lo reflejan.
  R11 Reenvío → versión nueva. Procesar SOLO con todo completo (hojas enviadas, importes aceptados o
      modificados, firmas requeridas): dice exactamente qué falta y no hay forma de saltarlo (decisión de
      Erik, 12-nov). Hoja procesada en solo lectura.
  R12 El coordinador nunca pide importes ni el tablero; sin errores de JavaScript; celular sin desbordes.
Uso: python3 ui_b1.py <index.html> <carpeta_capturas>"""
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
sql(f"""
insert into auth.users (id, email) values ('{U['eder']}','eder@demo.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['eder']}','{T}','coordinador','0a100000-0000-4000-8000-000000000002');
insert into public.clasificaciones_personal (id, tenant_id, nombre, activo) values ('0f000000-0000-4000-8000-000000000002','{T}','EFECTIVO',true);
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, empresa_id)
 select '{T}', '{P['ADELA']}', rl.id, '0f000000-0000-4000-8000-000000000002', '0e000000-0000-4000-8000-000000000007', 700, 'neto', 7, '2025-01-01', '{E1}'
 from public.relaciones_laborales rl where rl.personal_id = '{P['ADELA']}';
update public.inc_parametros set responsable_nomina_user = '{U['nomina']}', responsable_rh_user = '{U['rh']}' where empresa_id = '{E1}';
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('0e300000-0000-4000-8000-000000000001','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('0e300000-0000-4000-8000-000000000002','{T}','{E1}','Turno nocturno','T','turnos','turno','tarifa',700,null,2)""", replica=True)
HE, TN = '0e300000-0000-4000-8000-000000000001', '0e300000-0000-4000-8000-000000000002'
PER = sql(f"select public.inc_crear_periodo('{E1}','0e000000-0000-4000-8000-000000000007','2026-11-02','2026-11-08')", 'nomina')
H = sql(f"select public.inc_abrir_hoja('{PER}')", 'coord')
sql(f"""insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values
 ('{H}','{P['ADELA']}','2026-11-02','{HE}',2), ('{H}','{P['BENITO']}','2026-11-02','{HE}',2),
 ('{H}','{P['FABIOLA']}','2026-11-03','{HE}',2), ('{H}','{P['CESAR']}','2026-11-04','{TN}',1)""", 'coord')
sql(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values ('{H}','{P['CESAR']}','2026-11-05','F')", 'coord')
sql(f"select public.inc_enviar_hoja('{H}', 'Semana normal, una falta')", 'coord')

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
    # ============ R1: quién ve la revisión ============
    for rol, espera_rev in [('admin', True), ('nomina', True), ('coord', False), ('consulta', False)]:
        ctx, pg = abrir(b, rol)
        visible = pg.is_visible('nav.tabs button[data-tab="incidencias"]')
        if visible: incidencias(pg)
        sv = subvistas(pg) if visible else []; ve = 'Revisión' in sv
        ok(ve == espera_rev, f"R1 {rol}: {'ve' if espera_rev else 'no ve'} «Revisión»", (', '.join(sv) or texto(pg, '#inc-raiz')[:60]) if visible else 'sin pestaña Incidencias')
        if rol == 'coord':
            coord_ctx, coord_pg = ctx, pg
        else:
            ctx.close()

    # ============ Nómina ============
    ctx, pg = abrir(b, 'nomina')
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg)
    ok(pg.query_selector('#inc-r-periodos [data-rev-per]') is not None, 'R2 Lista de periodos con «Revisar»')
    pg.click('#inc-r-periodos [data-rev-per]'); espera(pg)
    filas = pg.eval_on_selector_all('#inc-r-tablero tbody tr', 'els => els.map(e => e.innerText.replace(/\\s+/g," ").trim())')
    ok(len(filas) == 2 and any('JOSE MANUEL' in f and 'Enviada' in f and 'v1' in f for f in filas) and any('EDER' in f and 'Sin abrir' in f for f in filas),
       'R2 Tablero: un renglón por coordinador (uno enviado v1 y otro sin abrir)', ' | '.join(f[:60] for f in filas))
    ok('EDER LOPEZ RUIZ' in texto(pg, '#inc-r-faltan'), 'R2 Muestra quién falta por enviar', texto(pg, '#inc-r-faltan'))
    npers = pg.eval_on_selector_all('#inc-r-tablero tbody tr', 'els => els.map(e => e.dataset.coord.slice(-2) + "=" + e.children[1].innerText.trim())')
    ok(sorted(npers) == ['01=6', '02=2'], 'R2 Personas por coordinador según la relación laboral (6 y 2)', str(npers))
    pg.screenshot(path=f'{OUT}/b1_01_tablero.png', full_page=True)
    pg.click('#inc-r-tablero [data-rev-hoja]'); espera(pg, 1200)
    # R3 captura solo lectura
    ninputs = pg.eval_on_selector_all('#inc-r-captura input, #inc-r-captura select, #inc-r-captura textarea', 'els => els.length')
    cap = texto(pg, '#inc-r-captura')
    ok(ninputs == 0 and 'ADELA' in cap and 'F' in cap, 'R3 Captura enviada en solo lectura (sin campos editables)', f'campos={ninputs}')
    # R4 líneas por esquema
    la = linea(pg, 'ADELA')
    ok(len(la) == 2 and {l['cat'] for l in la} == {'bruto', 'neto'} and any('IMSS' in l['txt'] and '333.33' in l['txt'] for l in la) and any('EFECTIVO' in l['txt'] and '50.00' in l['txt'] for l in la),
       'R4 Una persona con dos esquemas: dos líneas (IMSS bruto $333.33 y EFECTIVO neto $50.00)', ' | '.join(l['txt'][:70] for l in la))
    # R5 totales separados
    tb = texto(pg, '#inc-r-totales [data-total="bruto"]'); tn = texto(pg, '#inc-r-totales [data-total="neto"]')
    # B1.1: el turno por tarifa de CESAR se liga a su único esquema (IMSS bruto) y entra al total bruto: 583.33 + 700
    ok('1,283.33' in tb and '50.00' in tn, 'R5 Totales por separado: Bruto $1,283.33 (incluye el turno por tarifa ligado a IMSS, B1.1) y Neto $50.00', f'{tb} / {tn}')
    todo = texto(pg, '#inc-r-totales') + ' ' + texto(pg, '#inc-r-importes')
    ok('633.33' not in todo, 'R5 Ningún total suma bruto con neto ($633.33 no aparece)')
    ok(all(l['cat'] in ('bruto', 'neto') for l in la) and 'Bruto' in la[0]['txt'] + la[1]['txt'] and 'Neto' in la[0]['txt'] + la[1]['txt'], 'R5 Cada línea dice si es Bruto o Neto')
    # R6 sin sueldo
    lf = linea(pg, 'FABIOLA')
    ok(len(lf) == 1 and lf[0]['origen'] == 'sin_sueldo' and 'Sin sueldo' in lf[0]['txt'] and 'Sin esquema' in lf[0]['txt'],
       'R6 Esquema sin relación: línea «Sin sueldo» con motivo', lf[0]['txt'][:120] if lf else '')
    ok('sin sueldo' in texto(pg, '#inc-r-sinsueldo').lower(), 'R6 Aviso visible en los totales', texto(pg, '#inc-r-sinsueldo'))
    clase = pg.eval_on_selector(f'#inc-r-importes tr[data-linea="{lf[0]["id"]}"]', 'e => e.className') if lf else ''
    ok('inc-sin-sueldo' in clase, 'R6 La línea sin sueldo se resalta')
    lt = linea(pg, 'CESAR')
    # B1.1: con un solo esquema vigente, la línea por tarifa se liga a él automáticamente
    ok(len(lt) == 1 and lt[0]['cat'] == 'bruto' and '700.00' in lt[0]['txt'] and 'Aceptado' in lt[0]['txt'] and 'único esquema vigente' in lt[0]['txt'], 'R4 Concepto por tarifa: una línea, aceptada y ligada a su único esquema (B1.1)', lt[0]['txt'][:90] if lt else '')
    pg.screenshot(path=f'{OUT}/b1_02_importes.png', full_page=True)
    # R7 modificar y aceptar
    lb = linea(pg, 'BENITO')[0]
    pg.fill(f'[data-final="{lb["id"]}"]', '300'); pg.fill(f'[data-motivo="{lb["id"]}"]', 'B1.1: motivo obligatorio'); pg.click(f'[data-guardar="{lb["id"]}"]'); espera(pg, 1200)
    lb2 = linea(pg, 'BENITO')[0]
    v2 = pg.input_value(f'[data-final="{lb2["id"]}"]')
    ok(lb2['origen'] == 'modificado' and 'Modificado' in lb2['txt'] and v2 == '300', 'R7 Modificar un importe (250 → 300)', f"{lb2['txt'][:60]} final={v2}")
    lab = linea(pg, 'ADELA', 'bruto')[0]
    pg.click(f'[data-aceptar="{lab["id"]}"]'); espera(pg, 1200)
    ok(linea(pg, 'ADELA', 'bruto')[0]['origen'] == 'aceptado', 'R7 Aceptar un importe sugerido')
    pg.fill(f'[data-manual="{P["FABIOLA"]}"]', '400'); pg.click(f'[data-manual-btn="{P["FABIOLA"]}"]'); espera(pg, 1500)
    lf2 = linea(pg, 'FABIOLA')
    ok(len(lf2) == 1 and lf2[0]['cat'] == 'manual' and '200.00' in lf2[0]['txt'] and lf2[0]['origen'] == 'pendiente',
       'R7 Sueldo manual: la línea pasa a «Sueldo manual» con importe (2 h × 400/8 × 2)', lf2[0]['txt'][:100] if lf2 else '')
    lb3 = linea(pg, 'BENITO')[0]
    v3 = pg.input_value(f'[data-final="{lb3["id"]}"]')
    ok(lb3['origen'] == 'modificado' and v3 == '300', 'R7 El recálculo no pisó el importe modificado por Nómina', f"{lb3['origen']} final={v3}")
    ok(linea(pg, 'ADELA', 'bruto')[0]['origen'] == 'aceptado', 'R7 El recálculo conserva lo aceptado')
    # R8 aceptar todos
    btn = pg.query_selector('#inc-r-aceptar-todos'); n_txt = btn.inner_text() if btn else ''
    if btn: btn.click(); espera(pg, 1200)
    pend = [l for per in ('ADELA', 'BENITO', 'CESAR', 'FABIOLA') for l in linea(pg, per) if l['origen'] == 'pendiente']
    ok(btn is not None and not pend and 'aceptados' in texto(pg, '#inc-r-msg'), 'R8 Aceptar todos los sugeridos pendientes', f'{n_txt} → {texto(pg, "#inc-r-msg")}')
    ok(linea(pg, 'BENITO')[0]['origen'] == 'modificado', 'R8 «Aceptar todos» no toca lo modificado')
    # R9 firmas
    ok(pg.query_selector('[data-firmar="nomina"]') is not None and pg.query_selector('[data-firmar="rh"]') is None,
       'R9 Nómina (responsable de Nómina) ve solo su botón de firma', texto(pg, '#inc-r-firmas'))
    pg.click('[data-firmar="nomina"]'); espera(pg, 1200)
    ok('✓ Nómina' in texto(pg, '#inc-r-firmas'), 'R9 Firma de Nómina registrada sobre la versión vigente', texto(pg, '#inc-r-firmas'))
    ctx.close()
    ctx, pg = abrir(b, 'rh'); abrir_hoja_revision(pg)
    ok(pg.query_selector('[data-firmar="rh"]') is not None and pg.query_selector('[data-firmar="nomina"]') is None, 'R9 El responsable de RH ve solo el botón de RH')
    pg.click('[data-firmar="rh"]'); espera(pg, 1200)
    ok('✓ RH' in texto(pg, '#inc-r-firmas') and '✓ Nómina' in texto(pg, '#inc-r-firmas'), 'R9 Ambas firmas visibles', texto(pg, '#inc-r-firmas'))
    ctx.close()
    # R10 devolver
    ctx, pg = abrir(b, 'admin'); abrir_hoja_revision(pg)
    ok(pg.query_selector('[data-firmar]') is None, 'R9 El Administrador no designado no puede firmar', texto(pg, '#inc-r-firmas'))
    pg.click('#inc-r-devolver'); espera(pg, 300); pg.click('#inc-r-devolver-ok'); espera(pg, 400)
    ok('motivo' in texto(pg, '#inc-r-msg').lower() and texto(pg, '#inc-r-estado') == 'Enviada', 'R10 Devolver sin motivo: no se permite', texto(pg, '#inc-r-msg'))
    pg.fill('#inc-r-motivo', 'Falta la hora extra de CESAR del jueves'); pg.click('#inc-r-devolver-ok'); espera(pg, 1200)
    ok(texto(pg, '#inc-r-estado') == 'Devuelta' and pg.query_selector('[data-final]') is None, 'R10 Hoja devuelta: estado «Devuelta» y sin decisiones de importe', texto(pg, '#inc-r-estado'))
    pg.click('#inc-r-volver'); espera(pg)
    fila = texto(pg, '#inc-r-tablero tbody tr[data-estado="devuelta"]')
    ok('Devuelta' in fila and 'CESAR' in fila, 'R10 El tablero muestra la devolución y su motivo', fila[:100])
    ok('devuelta' in texto(pg, '#inc-r-faltantes').lower() and pg.is_disabled('#inc-r-proc'), 'R10 Con una hoja devuelta no se puede procesar (lo dice y el botón está deshabilitado)', texto(pg, '#inc-r-faltantes')[:140])
    ctx.close()
    # R11 reenvío, versión 2 y procesado
    sql(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H}','{P['CESAR']}','2026-11-06','{HE}',1)", 'coord')
    sql(f"select public.inc_enviar_hoja('{H}')", 'coord')
    ctx, pg = abrir(b, 'nomina')
    incidencias(pg); pg.click('[data-inc-vista="revision"]'); espera(pg); pg.click('#inc-r-periodos [data-rev-per]'); espera(pg)
    fila = texto(pg, '#inc-r-tablero tbody tr[data-coord$="000000000001"]')
    ok('v2' in fila and '— Nómina' in fila and '— RH' in fila, 'R11 Reenvío: versión 2 y firmas pendientes de nuevo', fila[:100])
    pg.click('#inc-r-tablero [data-rev-hoja]'); espera(pg, 1200)
    lc = linea(pg, 'CESAR')
    ok(all(l['origen'] != 'modificado' for per in ('BENITO',) for l in linea(pg, per)), 'R11 La versión 2 se decide de nuevo (las decisiones eran de la versión 1)')
    ok(len(lc) == 2 and all(l['cat'] == 'bruto' for l in lc), 'R11 La versión 2 trae su propio cálculo (HE de CESAR por esquema + turno por tarifa ligado a IMSS, B1.1)', ' | '.join(l['txt'][:50] for l in lc))
    pg.click('#inc-r-volver'); espera(pg)
    falta = texto(pg, '#inc-r-faltantes')
    ok('EDER LOPEZ RUIZ: no ha abierto su hoja' in falta and 'importe por decidir' in falta and 'falta la firma de Nómina' in falta and 'falta la firma de RH' in falta
       and pg.is_disabled('#inc-r-proc'), 'R11 Antes de procesar dice exactamente qué falta (hoja sin abrir, importes, firmas) y no deja procesar', falta[:160])
    botones = pg.eval_on_selector_all('#inc-r-proc-panel button', 'els => els.map(e => e.textContent.trim() + (e.disabled ? " (deshabilitado)" : ""))')
    ok(botones == ['Marcar como procesado (deshabilitado)'], 'R11 No existe confirmación ni otro botón que permita saltarse la regla', str(botones))
    # Se completa todo: EDER envía, Nómina acepta y firma en pantalla, RH firma
    HE2 = sql(f"select public.inc_abrir_hoja('{PER}')", 'eder'); sql(f"select public.inc_enviar_hoja('{HE2}')", 'eder')
    pg.click('#inc-r-tablero tr[data-coord$="000000000001"] [data-rev-hoja]'); espera(pg, 1200)
    pg.click('#inc-r-aceptar-todos'); espera(pg, 1200)
    pg.click('[data-firmar="nomina"]'); espera(pg, 1200)
    sql(f"select public.inc_firmar_hoja('{HE2}','nomina')", 'nomina')
    for hh in (H, HE2): sql(f"select public.inc_firmar_hoja('{hh}','rh')", 'rh')
    pg.click('#inc-r-volver'); espera(pg)
    ok('Todo está completo' in texto(pg, '#inc-r-faltantes') and not pg.is_disabled('#inc-r-proc'), 'R11 Con todo completo, el botón se habilita', texto(pg, '#inc-r-faltantes')[:80])
    pg.click('#inc-r-proc'); espera(pg, 1500)
    ok('procesado' in texto(pg, '#inc-r-msg').lower() and pg.query_selector('#inc-r-proc') is None, 'R11 Periodo marcado como procesado', texto(pg, '#inc-r-msg'))
    pg.click('#inc-r-tablero tr[data-coord$="000000000001"] [data-rev-hoja]'); espera(pg, 1200)
    ok(texto(pg, '#inc-r-estado') == 'Procesada' and pg.query_selector('[data-final], [data-aceptar], #inc-r-devolver, #inc-r-aceptar-todos') is None,
       'R11 Hoja procesada: solo lectura')
    pg.screenshot(path=f'{OUT}/b1_03_procesada.png', full_page=True)
    nomina_err = pg.errores
    # R12 celular
    ctx2, pm = abrir(b, 'nomina', 390, 844); abrir_hoja_revision(pm)
    ancho = pm.evaluate('document.documentElement.scrollWidth')
    ok(ancho <= 392, 'R12 Celular (390 px): la página no se desborda; las tablas se desplazan dentro de su recuadro', str(ancho))
    pm.screenshot(path=f'{OUT}/b1_04_celular.png', full_page=True)
    ok(not nomina_err and not pm.errores, 'R12 Nómina: sin errores de JavaScript', str(nomina_err + pm.errores)[:150])
    ctx2.close(); ctx.close()
    # R12 coordinador
    coord_pg.click('[data-inc-vista="hojas"]') if coord_pg.query_selector('[data-inc-vista="hojas"]') else None
    espera(coord_pg, 600)
    malas = [x for x in peticiones['coord'] if any(k in x for k in ('inc_importes', 'inc_tablero', 'inc_aceptar', 'inc_sueldos', 'inc_decidir'))]
    ok(not malas, 'R12 El coordinador nunca pide importes, sueldos ni el tablero', str(malas))
    ok(not coord_pg.errores, 'R12 Coordinador: sin errores de JavaScript', str(coord_pg.errores)[:120])
    coord_ctx.close()
    b.close()

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} OK')
for n, _, d in malas: print('  FALLA:', n, d)
sys.exit(1 if malas else 0)
