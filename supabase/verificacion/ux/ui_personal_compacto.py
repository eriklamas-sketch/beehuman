"""Personal compacto (25-nov-2026): las funciones de la tabla de Personal siguen dando EXACTAMENTE el mismo resultado
que antes del rediseño, y lo nuevo cumple lo aprobado. Base LOCAL (Postgres + PostgREST), datos ficticios.
Uso: python3 ui_personal_compacto.py <index.html> <carpeta_salida> <antes|despues>
  · En los dos modos se registran en <carpeta>/funciones_<modo>.json los resultados de: conteo, paginación, orden,
    búsqueda, cada estatus, empresa, proyecto, coordinador, pendientes, exportaciones (huella de cada CSV y del NOI)
    y la edición del proyecto en la fila (lo que se envía a la base). Comparar los dos archivos = paridad.
  · En «despues» además se verifican los elementos nuevos (P1–P10)."""
import sys, os, json, time, hashlib, datetime
HTML, OUT, MODO = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
fuente = open(os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py'), encoding='utf-8').read()
fuente = fuente[:fuente.index('def abrir(')]
sys.argv = [sys.argv[0], HTML, OUT]
__file__ = os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py')
exec(fuente)
from playwright.sync_api import sync_playwright

R = {}; envios = []; res = []
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

def abrir(b, quien, ancho=1440, alto=950):
    ctx = b.new_context(viewport={'width': ancho, 'height': alto}, accept_downloads=True)
    sesion = {'access_token': jwt(U[quien]), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
              'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
    ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});")
    base = ruta_para(quien)
    def ruta(route):
        r = route.request
        if '/rest/v1/' in r.url and r.method in ('POST', 'PATCH', 'DELETE') and '/rpc/' not in r.url:
            envios.append(f"{r.method} {r.url.split('/rest/v1/')[1]} {r.post_data or ''}")
        return base(route)
    ctx.route('**/*', ruta)
    pg = ctx.new_page(); pg.errores = []
    pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + os.path.abspath(HTML))
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    pg.click('nav.tabs button[data-tab="lista"]'); pg.wait_for_timeout(1500)
    return ctx, pg

filas = lambda pg: pg.locator('#tabla-personal tr').count()
ids = lambda pg: pg.locator('#tabla-personal tr td.col-id').all_inner_texts()
def estatus(pg, v):
    if MODO == 'despues': pg.click(f'#per-estatus button[data-est="{v}"]')
    else: pg.select_option('#filtro-estatus', v)
    pg.wait_for_timeout(300)
def mas(pg):
    if MODO == 'despues' and pg.locator('#per-mas-filtros').is_hidden(): pg.click('#per-mas'); pg.wait_for_timeout(200)
def descargar(pg, sel):
    if MODO == 'despues' and not pg.locator('#per-exportar').evaluate('e => e.open'): pg.click('#per-exportar summary'); pg.wait_for_timeout(200)
    with pg.expect_download() as d: pg.click(sel)
    contenido = open(d.value.path(), 'rb').read()
    return [hashlib.sha256(contenido).hexdigest()[:16], contenido.count(b'\n'), d.value.suggested_filename.split('_')[0]]

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'admin')
    R['conteo'] = pg.inner_text('#lista-conteo'); R['filas_p1'] = filas(pg); R['ids_p1'] = ids(pg)[:5]
    pg.click('#pagina-siguiente'); pg.wait_for_timeout(300)
    R['p2'] = [pg.inner_text('#pagina-texto'), filas(pg), ids(pg)[:3]]
    pg.click('#pagina-anterior'); pg.wait_for_timeout(300)
    pg.select_option('#lista-tamano', '100'); pg.wait_for_timeout(300); R['tam100'] = [filas(pg), pg.inner_text('#pagina-texto')]
    pg.select_option('#lista-tamano', '50'); pg.wait_for_timeout(300)
    R['csv_personas'] = descargar(pg, '#exportar-personal'); R['csv_esquemas'] = descargar(pg, '#exportar-esquemas')
    if MODO == 'despues': pg.click('#per-exportar summary'); pg.wait_for_timeout(200)
    pg.click('#exportar-noi'); pg.wait_for_timeout(800)
    R['noi'] = [pg.is_visible('#modal-noi-overlay'), pg.inner_text('#noi-resumen')[:120]]
    pg.click('#noi-cerrar'); pg.wait_for_timeout(300)
    for v in ('Baja', '__vigentes__', 'Suspendido', ''):
        estatus(pg, v); R['estatus_' + (v or 'todos')] = [filas(pg), pg.inner_text('#lista-conteo')]
    estatus(pg, 'Activo')
    pg.click('#encabezado-personal th:has-text("ID")'); pg.wait_for_timeout(300); R['orden_id'] = ids(pg)[:4]
    pg.click('#encabezado-personal th:has-text("ID")'); pg.wait_for_timeout(300); R['orden_id_desc'] = ids(pg)[:4]
    pg.click('#encabezado-personal th:has-text("Nombre")'); pg.wait_for_timeout(300)
    pg.fill('#buscar-personal', 'ADELA'); pg.wait_for_timeout(500); R['busqueda'] = [filas(pg), ids(pg)]
    R['csv_busqueda'] = descargar(pg, '#exportar-personal')
    pg.fill('#buscar-personal', ''); pg.wait_for_timeout(400)
    emp = pg.eval_on_selector('#filtro-empresa', 'e => [...e.options].map(o => o.value).filter(Boolean)')
    if emp: pg.select_option('#filtro-empresa', emp[0]); pg.wait_for_timeout(300); R['empresa'] = filas(pg); pg.select_option('#filtro-empresa', ''); pg.wait_for_timeout(300)
    mas(pg)
    for sel in ('#filtro-proyecto', '#filtro-coordinador', '#filtro-clasificacion'):
        op = pg.eval_on_selector(sel, 'e => [...e.querySelectorAll("option")].map(o => o.value).filter(Boolean)')
        if op: pg.select_option(sel, op[0]); pg.wait_for_timeout(300); R[sel] = [filas(pg), pg.inner_text('#lista-conteo')]; pg.select_option(sel, ''); pg.wait_for_timeout(300)
    for v in ('sin_esquema', 'contrato'):
        pg.select_option('#filtro-pendiente', v); pg.wait_for_timeout(300); R['pendiente_' + v] = filas(pg)
    pg.select_option('#filtro-pendiente', ''); pg.wait_for_timeout(300)
    pg.click('#limpiar-filtros') if pg.locator('#limpiar-filtros').is_enabled() else None; pg.wait_for_timeout(300)
    R['tras_limpiar'] = pg.inner_text('#lista-conteo')
    # Edición del proyecto en la fila: lo que se envía a la base
    pg.fill('#buscar-personal', 'CESAR'); pg.wait_for_timeout(500)
    sel = pg.locator('#tabla-personal tr select').first
    opciones = sel.evaluate('e => [...e.options].filter(o => o.value).map(o => o.value)')
    actual = sel.input_value(); nuevo = next(o for o in opciones if o != actual)
    envios.clear(); sel.select_option(nuevo); pg.wait_for_timeout(1500)
    R['edicion_proyecto'] = [e.split(' ', 1)[0] + ' ' + e.split(' ', 1)[1].split('?')[0] + ' ' + e.rsplit(' ', 1)[-1] for e in envios]
    R['edicion_bd'] = sql(f"select proyecto_id from personal where empleado_id = '{ids(pg)[0]}'") == nuevo
    sel.select_option(actual); pg.wait_for_timeout(1200)
    pg.fill('#buscar-personal', ''); pg.wait_for_timeout(400)
    R['errores_admin'] = pg.errores[:3]

    if MODO == 'despues':
        print('== Lo nuevo ==')
        hoy = datetime.date.today()
        ok(pg.is_visible('#per-btn-alta') and pg.is_visible('nav.tabs button[data-tab="alta"]'), 'P1 «Alta de personal»: botón amarillo arriba y entrada en el menú lateral')
        color = pg.eval_on_selector('#per-btn-alta', 'e => getComputedStyle(e).backgroundColor')
        ok(color == 'rgb(255, 200, 44)', 'P1 El botón de alta es amarillo', color)
        pg.click('#per-btn-alta'); pg.wait_for_timeout(500)
        ok(pg.is_visible('#panel-alta'), 'P1 El botón abre «Alta de personal»')
        pg.click('nav.tabs button[data-tab="lista"]'); pg.wait_for_timeout(800)
        vence_bd = int(sql("select count(*) from personal where fecha_baja is null and coalesce(estatus,'') <> 'Baja' and estatus = 'Activo' and fecha_vencimiento_contrato between (now() at time zone 'America/Mexico_City')::date and (now() at time zone 'America/Mexico_City')::date + 30"))
        ok(pg.inner_text('#kpi-vence') == str(vence_bd), 'P2 Vencimientos (30 días) = fechas válidas entre hoy y hoy + 30 de los activos (la base dice ' + str(vence_bd) + ')', pg.inner_text('#kpi-vence'))
        sin_fecha = int(sql("select count(*) from personal where estatus = 'Activo' and fecha_vencimiento_contrato is null"))
        ok(pg.inner_text('#kpi-vence') != str(sin_fecha) or sin_fecha == vence_bd, 'P2 Los registros sin fecha no cuentan como próximos a vencer')
        vencidos = int(sql("select count(*) from personal where estatus = 'Activo' and fecha_vencimiento_contrato < (now() at time zone 'America/Mexico_City')::date"))
        ok(vencidos > 0, '+P2 La semilla tiene contratos ya vencidos (no deben contar)', str(vencidos))
        ok(pg.inner_text('#kpi-vence-sub') == 'Tipo de contrato no registrado' and 'no distingue contratos temporales' in (pg.get_attribute('#kpi-vence-sub', 'title') or ''),
           'P3 Aviso «Tipo de contrato no registrado» (con la explicación al pasar el ratón); no muestra «sin fecha»')
        sin_esq = pg.inner_text('#kpi-sinesquema')
        ok(sin_esq.isdigit() and pg.inner_text('#kpi-personas').replace(',', '').isdigit(), 'P2 Indicadores Personas y Sin esquema de pago con cifra', sin_esq)
        tam_p = pg.eval_on_selector('#kpi-percepciones', 'e => parseFloat(getComputedStyle(e).fontSize)')
        tam_n = pg.eval_on_selector('#kpi-personas', 'e => parseFloat(getComputedStyle(e).fontSize)')
        ok(tam_p < tam_n and pg.inner_text('#kpi-percepciones').startswith('$'), 'P4 Percepciones registradas como dato secundario (letra menor)', f'{tam_p} < {tam_n}')
        alto_fila = pg.eval_on_selector('#tabla-personal tr', 'e => e.getBoundingClientRect().height')
        ok(alto_fila <= 42, 'P5 Filas compactas de una línea', f'{alto_fila:.0f} px')
        sel = pg.locator('#tabla-personal tr select.per-proy').first
        borde = sel.evaluate('e => getComputedStyle(e).borderTopColor')
        ok(sel.is_visible() and borde in ('rgba(0, 0, 0, 0)', 'transparent'), 'P6 Proyecto editable en la fila, discreto (sin borde hasta pasar el ratón)', borde)
        ok(pg.is_visible('#lista-paginador') and '–' in pg.inner_text('#pagina-rango') and pg.locator('#pagina-numeros button').count() >= 2, 'P7 Paginación visible con rango y páginas numeradas', pg.inner_text('#pagina-rango'))
        pg.click('#pagina-numeros button[data-pag="3"]'); pg.wait_for_timeout(300)
        ok(pg.inner_text('#pagina-texto') == 'Página 3 de 3', 'P7 Ir directo a la página 3', pg.inner_text('#pagina-texto'))
        pg.click('#pagina-numeros button[data-pag="1"]'); pg.wait_for_timeout(300)
        pg.click('#per-mas'); pg.wait_for_timeout(200); ok(pg.is_hidden('#per-mas-filtros'), 'P8 «Más filtros» se abre y se cierra'); pg.click('#per-mas'); pg.wait_for_timeout(200)
        op = pg.eval_on_selector('#filtro-proyecto', 'e => [...e.options].map(o => o.value).filter(Boolean)')[0]
        pg.select_option('#filtro-proyecto', op); pg.wait_for_timeout(300)
        ok('· 1' in pg.inner_text('#per-mas'), 'P8 «Más filtros · 1» cuenta los filtros aplicados que guarda', pg.inner_text('#per-mas'))
        pg.select_option('#filtro-proyecto', ''); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}/personal_1440.png')
        ctx.close()
        ctx, pg = abrir(b, 'admin', 1280, 720)
        visibles = pg.evaluate("[...document.querySelectorAll('#tabla-personal tr')].filter(r => r.getBoundingClientRect().bottom <= innerHeight).length")
        ancho = pg.evaluate("[document.querySelector('#panel-lista .table-wrap').scrollWidth, document.querySelector('#panel-lista .table-wrap').clientWidth]")
        ok(visibles >= 6 and ancho[0] <= ancho[1] + 1, 'P9 Laptop 1280×720: varias filas a la vista y la tabla cabe sin desplazar a los lados', f'{visibles} filas; {ancho}')
        pg.screenshot(path=f'{OUT}/personal_1280x720.png'); ctx.close()
        ctx, pg = abrir(b, 'admin', 390, 844)
        disp = pg.eval_on_selector('#tabla-personal tr', 'e => getComputedStyle(e).display')
        ok(disp == 'grid' and pg.evaluate('document.documentElement.scrollWidth') <= 390 and pg.locator('#tabla-personal tr select.per-proy').first.is_visible(),
           'P10 Celular: tarjetas, sin desborde, con el proyecto editable', disp)
        pg.evaluate("document.querySelector('#tabla-personal').scrollIntoView()"); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}/personal_movil.png'); ctx.close()
        ctx, pg = abrir(b, 'consulta')
        ok(pg.is_hidden('#per-btn-alta') and pg.is_hidden('#kpi-sinesquema') and pg.is_hidden('#kpi-percepciones') and pg.is_visible('#kpi-personas'),
           'P1/P4 Consulta: sin botón de alta ni indicadores de pago; ve Personas')
        R['consulta_columnas'] = pg.locator('#encabezado-personal th').all_inner_texts()
        ok(not pg.errores, 'Sin errores de JavaScript', str(pg.errores[:2])); ctx.close()
    else:
        ctx.close()
    b.close()

json.dump(R, open(f'{OUT}/funciones_{MODO}.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
if MODO == 'despues':
    antes_f = f'{OUT}/funciones_antes.json'
    if os.path.exists(antes_f):
        A = json.load(open(antes_f)); difs = [k for k in A if k != 'errores_admin' and A.get(k) != R.get(k)]
        ok(not difs, 'PARIDAD Búsqueda, filtros, orden, paginación, exportaciones y edición dan lo mismo que antes', ', '.join(difs))
        for k in difs: print('   ', k, 'antes:', A.get(k), '| después:', R.get(k))
    ok(not R['errores_admin'], 'Sin errores de JavaScript (administrador)', str(R['errores_admin']))
    malas = [r for r in res if not r[1]]
    print(f'\nRESULTADO: {len(res) - len(malas)} de {len(res)} verificaciones OK')
    sys.exit(1 if malas else 0)
print('Registrado:', len(R), 'resultados')
