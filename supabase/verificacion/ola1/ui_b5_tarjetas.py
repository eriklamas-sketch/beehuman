"""B5 · «Prestaciones y créditos» en tarjetas (17-nov-2026) · prueba de PANTALLA con datos FICTICIOS.
Cambio de presentación: no cambia reglas, estados, permisos ni la base. Casos:
  T1 Un crédito (ADELA): FONACOT completo pendiente de activar → «Completo · falta activar», Activar, aviso;
     propuesto «Sin propuesta aún» y procesado «—»; sin saldo (no maneja monto total).
  T3 Tres créditos (BENITO): INFONAVIT informativo (sin descuentos ni Activar); FONACOT activo con propuesto y
     procesado tomados de cred_descuentos; préstamo con saldo pendiente.
  T5 Cinco créditos (CESAR): FONACOT con dos periodos abiertos (+1), préstamo suspendido (Reactivar), FONACOT
     incompleto con faltantes (sin Activar) y un terminado agrupado y plegado en «Terminados (1)».
  A  Acciones: Activar abre fecha y motivo y llama a cred_cambiar_estado como antes; Editar abre el formulario;
     Historia se despliega; la ficha solo LEE cred_descuentos (sin escrituras al pintar).
  Sin errores de JavaScript, sin desborde horizontal en celular (390 px), capturas en <carpeta>.
Base: Postgres local bhui (Ola 1 + semilla_ui + resto de migraciones). Las peticiones /rest/v1 las atiende
rest_local.py como el usuario (mismas RLS); no es PostgREST real.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_b5_tarjetas.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']
REF = 'sflvpgkmtaxzogpgetxn'
U = {'admin': '0b000000-0000-4000-8000-000000000001', 'nomina': '0b000000-0000-4000-8000-000000000002'}
RL.U.update(U)
T = '0a000000-0000-4000-8000-000000000001'; E1 = '0c000000-0000-4000-8000-000000000001'; SEM = '0e000000-0000-4000-8000-000000000007'
P = {'ADELA': '0a100000-0000-4000-8000-000000000011', 'BENITO': '0a100000-0000-4000-8000-000000000012', 'CESAR': '0a100000-0000-4000-8000-000000000013'}
NOMBRE = {'ADELA': 'ADELA PALACIOS GALVAN', 'BENITO': 'BENITO ZAVALA GALINDO', 'CESAR': 'CESAR DELGADILLO HINOJOSA'}
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}

def sql(q, quien=None, replica=False):
    c = RL.conectar(); cur = c.cursor()
    try:
        if replica: cur.execute('set local session_replication_role = replica')
        if quien:
            cur.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps({'sub': U[quien], 'role': 'authenticated'}),))
            cur.execute('set local role authenticated')
        cur.execute(q); r = cur.fetchone() if cur.description else None; c.commit(); return r[0] if r else None
    finally: c.close()
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"
rel = {k: sql(f"select id from public.relaciones_laborales where personal_id = '{v}' and estado = 'vigente'") for k, v in P.items()}
def credito(quien_p, d):
    d = dict(d, personal_id=P[quien_p], relacion_laboral_id=rel[quien_p], fecha_inicio=d.get('fecha_inicio', '2026-11-01'))
    return sql(f"select public.cred_guardar(null, {lit(d)})", 'nomina')

# ---------------- datos ficticios ----------------
sql(f"update public.inc_parametros set responsable_nomina_user = '{U['nomina']}' where empresa_id = '{E1}'", replica=True)
PER_PROC = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-02','2026-11-08')", 'nomina')
PER_AB1 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-09','2026-11-15')", 'nomina')
PER_AB2 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-16','2026-11-22')", 'nomina')
FON = lambda ref, imp: {'tipo': 'fonacot', 'referencia': ref, 'periodicidad_id': SEM, 'importe_periodo': imp}
# 1 crédito: ADELA, FONACOT completo convertido, pendiente de activar
A1 = credito('ADELA', FON('FON-UNO-01', 250))
sql(f"update public.cred_creditos set estado = 'incompleto', origen = 'conversion_no_fonacot' where id = '{A1}'", replica=True)
# 3 créditos: BENITO
B_INF = credito('BENITO', {'tipo': 'infonavit', 'referencia': 'INF-9921', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 1200, 'infonavit_fecha_aviso': '2026-10-15'})
B_FON = credito('BENITO', FON('FON-B-02', 250))
B_PRE = credito('BENITO', {'tipo': 'prestamo', 'referencia': 'PRE-04', 'periodicidad_id': SEM, 'importe_periodo': 500, 'monto_total': 10000})
# 5 créditos: CESAR
C_INF = credito('CESAR', {'tipo': 'infonavit', 'referencia': 'INF-5550', 'infonavit_tipo': 'porcentaje', 'infonavit_valor': 20})
C_FON = credito('CESAR', FON('FON-C-01', 300))
C_SUS = credito('CESAR', {'tipo': 'prestamo', 'referencia': 'PRE-SUS', 'periodicidad_id': SEM, 'importe_periodo': 400, 'monto_total': 4000})
C_INC = credito('CESAR', FON('FON-C-INC', 180))
C_TER = credito('CESAR', {'tipo': 'anticipo', 'referencia': 'ANT-OLD', 'periodicidad_id': SEM, 'importe_periodo': 1000, 'monto_total': 1000})
sql(f"select public.cred_cambiar_estado('{C_SUS}', 'suspendido', '2026-11-12', 'Acuerdo con el trabajador')", 'nomina')
sql(f"select public.cred_cambiar_estado('{C_TER}', 'terminado', '2026-11-05', 'Liquidado en efectivo')", 'nomina')
sql(f"update public.cred_creditos set estado = 'incompleto', origen = 'conversion_no_fonacot', importe_periodo = null where id = '{C_INC}'", replica=True)
def linea(cred, per, quien_p, sug, fin, origen):
    return sql(f"""insert into public.cred_descuentos (tenant_id, periodo_id, credito_id, personal_id, relacion_laboral_id, sugerido, final, origen)
                   values ('{T}', '{per}', '{cred}', '{P[quien_p]}', '{rel[quien_p]}', {sug}, {fin if fin is not None else 'null'}, '{origen}') returning id""")
linea(B_FON, PER_PROC, 'BENITO', 250, 250, 'aceptado'); linea(B_FON, PER_AB1, 'BENITO', 250, None, 'pendiente')
LP = linea(B_PRE, PER_PROC, 'BENITO', 500, 500, 'aceptado'); linea(B_PRE, PER_AB1, 'BENITO', 500, 450, 'modificado')
sql(f"""insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo)
        values ('{T}', '{B_PRE}', '{PER_PROC}', '{LP}', 500, 10000, 9500) returning id""")
linea(C_FON, PER_AB1, 'CESAR', 300, None, 'pendiente'); linea(C_FON, PER_AB2, 'CESAR', 300, 300, 'aceptado')
linea(C_FON, PER_PROC, 'CESAR', 300, None, 'descartado')   # descartada: no debe contarse como procesada
# El periodo se marca procesado después de registrar sus líneas (como ocurre al procesar).
sql(f"update public.inc_periodos set procesado_en = '2026-11-10 12:00-06', procesado_por = '{U['nomina']}' where id = '{PER_PROC}'", replica=True)

# ---------------- navegador ----------------
peticiones = []
def b64(d): return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
def ruta(route):
    req = route.request; u = urlparse(req.url)
    if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
    if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
    if u.netloc == f'{REF}.supabase.co':
        if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
        if u.path.startswith('/auth/v1/user'): return route.fulfill(json={'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}, headers=CORS)
        if u.path.startswith('/rest/v1/'):
            tabla = u.path[len('/rest/v1/'):]; cuerpo = json.loads(req.post_data) if req.post_data else None
            peticiones.append((req.method, tabla, u.query))
            try: st, res, extra = RL.ejecutar('admin', req.method, tabla, parse_qsl(u.query, keep_blank_values=True), cuerpo, {k.lower(): v for k, v in req.headers.items()})
            except Exception as e: st, res, extra = 400, {'code': 'LOCAL', 'message': str(e)}, {}; peticiones.append(('ERROR', tabla, str(e)))
            h = dict(CORS); h.update(extra)
            if st == 204: return route.fulfill(status=204, headers=h, body='')
            return route.fulfill(status=st, headers=h, body=json.dumps(res), content_type='application/json')
        return route.fulfill(json={}, headers=CORS)
    if u.scheme in ('http', 'https'): return route.abort()
    return route.continue_()

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

def tarjetas(pg):
    return pg.evaluate("""() => [...document.querySelectorAll('#cred-lista [data-cred]')].map(e => ({
      id: e.dataset.cred, tipo: e.dataset.tipo, estado: e.dataset.estado, visible: !e.closest('details:not([open])') && e.getClientRects().length > 0,
      chip: (e.querySelector('.cred-est') || {}).textContent || '',
      acciones: [...e.querySelectorAll('.cred-acciones button')].map(b => b.textContent.trim()),
      propuesto: (e.querySelector('[data-propuesto]') || {}).innerText || null,
      procesado: (e.querySelector('[data-procesado]') || {}).innerText || null,
      saldo: (e.querySelector('[data-saldo]') || {}).innerText || null,
      configurado: (e.querySelector('[data-configurado]') || {}).innerText || null,
      listo: !!e.querySelector('[data-cred-listo]'), falta: (e.querySelector('[data-cred-falta]') || {}).innerText || null,
      txt: e.innerText.replace(/\\s+/g, ' ')}))""")
def por(ts, cid): return next((t for t in ts if t['id'] == cid), None)
def plano(s): return (s or '').replace('\n', ' ')

def abrir_ficha(pg, quien_p):
    pg.click('nav.tabs button[data-tab="lista"]'); pg.wait_for_timeout(600)
    pg.fill('#buscar-personal', NOMBRE[quien_p]); pg.wait_for_timeout(400)
    pg.click(f'#tabla-personal a:has-text("{NOMBRE[quien_p]}")'); pg.wait_for_timeout(1300)
    pg.click('[data-detail-tab="prestaciones"]'); pg.wait_for_timeout(1200)

def cerrar(pg):
    pg.evaluate("() => { if (typeof cerrarDetalleYa === 'function') cerrarDetalleYa(); }"); pg.wait_for_timeout(400)

with sync_playwright() as p:
    b = p.chromium.launch()
    def contexto(ancho, alto, escala=1):
        ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=escala)
        ses = {'access_token': b64({'alg': 'HS256'}) + '.' + b64({'sub': U['admin'], 'role': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local',
               'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x',
               'user': {'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});")
        ctx.route('**/*', ruta)
        pg = ctx.new_page(); pg.errores = []
        pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda d: d.accept())
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
        return ctx, pg
    ctx, pg = contexto(1440, 950)

    # ---- T1: un crédito ----
    print('== T1 Un crédito (ADELA) ==')
    peticiones.clear(); abrir_ficha(pg, 'ADELA')
    ts = tarjetas(pg); a = por(ts, A1)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/T1_un_credito.png')
    ok(len(ts) == 1 and a and a['estado'] == 'incompleto', 'T1 Una tarjeta, estado real «incompleto» en data-estado', str(len(ts)))
    ok(a and 'Completo · falta activar' in a['chip'], 'T1 Etiqueta «Completo · falta activar»', a and a['chip'])
    ok(a and a['acciones'] == ['Activar', 'Editar', 'Terminar', 'Historia'], 'T1 Acciones: Activar (primero), Editar, Terminar, Historia', a and str(a['acciones']))
    ok(a and a['listo'] and 'fecha efectiva y motivo' in a['txt'], 'T1 Aviso de datos completos, avisa que pedirá fecha y motivo')
    ok(a and '$250.00' in plano(a['configurado']) and 'Semanal' in plano(a['configurado']), 'T1 Importe configurado $250.00 Semanal', plano(a and a['configurado']))
    ok(a and 'Sin propuesta aún' in plano(a['propuesto']), 'T1 Propuesto: «Sin propuesta aún» (no inventa importe)', plano(a and a['propuesto']))
    ok(a and plano(a['procesado']).lower().startswith('procesado —'), 'T1 Procesado: «—»', plano(a and a['procesado']))
    ok(a and a['saldo'] is None, 'T1 Sin saldo: FONACOT sin monto total no muestra saldo')

    # ---- A: acciones (sobre el crédito de ADELA) ----
    print('== A Acciones ==')
    pg.click(f'[data-cred-hist="{A1}"]'); pg.wait_for_timeout(400)
    ok('Historia' in pg.inner_text(f'#cred-lista [data-cred="{A1}"]') and 'Ocultar historia' in pg.inner_text(f'#cred-lista [data-cred="{A1}"] .cred-acciones'), 'A Historia se despliega dentro de la tarjeta')
    pg.click(f'[data-cred-hist="{A1}"]'); pg.wait_for_timeout(300)
    pg.click(f'[data-cred-editar="{A1}"]'); pg.wait_for_timeout(400)
    ok(pg.is_visible('#cred-form') and pg.is_visible('#cred-motivo'), 'A Editar abre el mismo formulario (con motivo del cambio)')
    pg.click('#cred-cancelar'); pg.wait_for_timeout(300)
    ESCRIBEN = ('rpc/cred_guardar', 'rpc/cred_cambiar_estado', 'rpc/cred_decidir_descuento', 'rpc/cred_aceptar_descuentos')
    escrituras_pintar = [x for x in peticiones if x[0] in ('PATCH', 'DELETE') or (x[0] == 'POST' and not x[1].startswith('rpc/')) or x[1] in ESCRIBEN]
    lecturas_desc = [x for x in peticiones if x[0] == 'GET' and x[1] == 'cred_descuentos']
    ok(not escrituras_pintar and lecturas_desc, 'A Al pintar la ficha solo se LEE cred_descuentos; ninguna escritura', str(escrituras_pintar[:2]))
    pg.click(f'[data-cred-estado="{A1}"][data-a="activo"]'); pg.wait_for_timeout(400)
    ok(pg.is_visible(f'[data-mini="{A1}"] [data-est-fecha]') and pg.is_visible(f'[data-mini="{A1}"] [data-est-motivo]'), 'A Activar pide fecha efectiva y motivo')
    peticiones.clear()
    pg.fill(f'[data-mini="{A1}"] [data-est-motivo]', 'Cédula recibida'); pg.click(f'[data-est-ok="{A1}"]'); pg.wait_for_timeout(1400)
    ok(any(x[1] == 'rpc/cred_cambiar_estado' for x in peticiones), 'A Confirmar llama a cred_cambiar_estado, como antes')
    a = por(tarjetas(pg), A1)
    ok(a and a['estado'] == 'activo' and 'Activo · propone descuento' in a['chip'] and 'Activar' not in a['acciones'], 'A Activado: estado activo, sin repetir «Activar»', a and str(a['acciones']))
    ok(sql(f"select estado from public.cred_creditos where id = '{A1}'") == 'activo', 'A La base registra el cambio (misma regla de activación)')
    cerrar(pg)

    # ---- T3: tres créditos ----
    print('== T3 Tres créditos (BENITO) ==')
    abrir_ficha(pg, 'BENITO'); ts = tarjetas(pg)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/T3_tres_creditos.png')
    inf, fon, pre = por(ts, B_INF), por(ts, B_FON), por(ts, B_PRE)
    ok(len(ts) == 3 and inf and fon and pre, 'T3 Tres tarjetas', str(len(ts)))
    ok(inf and 'Informativo NOI · Sin descuento en BeeHuman' in inf['chip'] and 'Activar' not in inf['acciones'], 'T3 INFONAVIT: «Informativo NOI · Sin descuento en BeeHuman», sin Activar', inf and inf['chip'])
    ok(inf and inf['propuesto'] is None and inf['procesado'] is None and inf['saldo'] is None and 'No genera' in inf['txt'] and 'Cuota fija mensual' in inf['txt'],
       'T3 INFONAVIT: muestra sus datos para NOI y «No genera»; ningún importe de descuento')
    ok(fon and 'Activo · propone descuento' in fon['chip'] and fon['acciones'] == ['Editar', 'Suspender', 'Terminar', 'Historia'], 'T3 FONACOT activo: sin Activar; Editar, Suspender, Terminar, Historia', fon and str(fon['acciones']))
    ok(fon and '$250.00' in plano(fon['propuesto']) and 'Por decidir' in plano(fon['propuesto']) and '09/11/2026' in plano(fon['propuesto']), 'T3 FONACOT: propuesto $250.00 «Por decidir» del periodo abierto', plano(fon and fon['propuesto']))
    ok(fon and '$250.00' in plano(fon['procesado']) and '02/11/2026' in plano(fon['procesado']), 'T3 FONACOT: procesado $250.00 del periodo cerrado', plano(fon and fon['procesado']))
    ok(fon and fon['saldo'] is None, 'T3 FONACOT sin monto total: sin saldo')
    ok(pre and '$450.00' in plano(pre['propuesto']) and 'Modificado' in plano(pre['propuesto']), 'T3 Préstamo: propuesto = importe final decidido ($450.00, Modificado)', plano(pre and pre['propuesto']))
    ok(pre and '$500.00' in plano(pre['procesado']), 'T3 Préstamo: procesado $500.00', plano(pre and pre['procesado']))
    ok(pre and '$9,500.00' in plano(pre['saldo']) and '$10,000.00' in plano(pre['saldo']), 'T3 Préstamo: saldo pendiente $9,500.00 de $10,000.00 (de la base)', plano(pre and pre['saldo']))
    cerrar(pg)

    # ---- T5: cinco créditos ----
    print('== T5 Cinco créditos (CESAR) ==')
    abrir_ficha(pg, 'CESAR'); ts = tarjetas(pg)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/T5_cinco_creditos.png')
    vis = [t for t in ts if t['visible']]
    ok(len(ts) == 5 and len(vis) == 4, 'T5 Cinco créditos: 4 visibles y el terminado plegado', f'{len(ts)} / {len(vis)}')
    ok(pg.is_visible('#cred-terminados') and 'Terminados (1)' in pg.inner_text('#cred-terminados summary') and not pg.evaluate("document.querySelector('#cred-terminados').open"),
       'T5 «Terminados (1)» al final, plegado')
    ok(pg.evaluate("() => { const l = document.querySelector('#cred-lista'); const s = getComputedStyle(l); return s.overflowY !== 'auto' && s.overflowY !== 'scroll' && !l.querySelector('.cred-cards[style*=overflow]'); }"), 'T5 Sin scroll interno en la lista')
    f2, sus, inc, inf5 = por(ts, C_FON), por(ts, C_SUS), por(ts, C_INC), por(ts, C_INF)
    ok(f2 and '$300.00' in plano(f2['propuesto']) and '16/11/2026' in plano(f2['propuesto']) and '+1 periodo abierto' in plano(f2['propuesto']), 'T5 Dos periodos abiertos: muestra el más reciente y «+1 periodo abierto»', plano(f2 and f2['propuesto']))
    ok(f2 and plano(f2['procesado']).lower().startswith('procesado —'), 'T5 Línea descartada en periodo procesado: no cuenta como procesado («—»)', plano(f2 and f2['procesado']))
    ok(sus and 'Suspendido' in sus['chip'] and sus['acciones'] == ['Editar', 'Reactivar', 'Terminar', 'Historia'], 'T5 Suspendido: Editar, Reactivar, Terminar, Historia', sus and str(sus['acciones']))
    ok(sus and '$4,000.00' in plano(sus['saldo']), 'T5 Suspendido con monto total: muestra saldo', plano(sus and sus['saldo']))
    ok(inc and 'Incompleto · faltan datos' in inc['chip'] and 'Activar' not in inc['acciones'] and inc['falta'], 'T5 FONACOT incompleto con faltantes: dice qué falta y no ofrece Activar', plano(inc and inc['falta']))
    ok(inf5 and 'Informativo NOI' in inf5['chip'] and 'Porcentaje del SBC' in inf5['txt'] and inf5['propuesto'] is None, 'T5 INFONAVIT por porcentaje: informativo, sin descuentos')
    pg.click('#cred-terminados summary'); pg.wait_for_timeout(300)
    ter = por(tarjetas(pg), C_TER)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/T5_terminados_abiertos.png')
    ok(ter and ter['visible'] and ter['acciones'] == ['Historia'] and 'Terminado' in ter['chip'], 'T5 Al desplegar: el terminado solo ofrece Historia', ter and str(ter['acciones']))
    pg.click(f'[data-cred-hist="{C_TER}"]'); pg.wait_for_timeout(400)
    ok(pg.evaluate("document.querySelector('#cred-terminados').open") and 'Liquidado en efectivo' in pg.inner_text(f'#cred-lista [data-cred="{C_TER}"]'),
       'T5 La historia del terminado se ve y el grupo sigue abierto al repintar')
    errores_escritorio = list(pg.errores)
    ctx.close()

    # ---- celular ----
    ctx, pg = contexto(390, 844, 2)
    abrir_ficha(pg, 'CESAR')
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/T5_celular.png')
    desb = pg.evaluate("() => [...document.querySelectorAll('#cred-lista .cred-card')].filter(e => e.getClientRects().length && e.getBoundingClientRect().right > window.innerWidth + 1).length")
    ok(desb == 0, 'Celular (390 px): ninguna tarjeta se sale de la pantalla', str(desb))
    ok(not errores_escritorio and not pg.errores, 'Sin errores de JavaScript', str((errores_escritorio + pg.errores)[:2]))
    ok(not [x for x in peticiones if x[0] == 'ERROR'], 'Todas las peticiones atendidas por el traductor local', str([x for x in peticiones if x[0] == 'ERROR'][:2]))
    ctx.close(); b.close()

total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
sys.exit(1 if malos else 0)
