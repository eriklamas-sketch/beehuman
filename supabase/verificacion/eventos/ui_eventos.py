"""Pruebas de pantalla de la etapa 1 (Historia laboral e IDSE) contra la base LOCAL
(Postgres + PostgREST en 3010) con datos ficticios. Nunca toca Supabase.
Uso: python3 ui_eventos.py <index.html> <carpeta_capturas>"""
import sys, os, json, time
HTML, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
fuente = open(os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py'), encoding='utf-8').read()
fuente = fuente[:fuente.index('def abrir(')]
sys.argv = [sys.argv[0], HTML, OUT]
__file__ = os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py')
exec(fuente)
from playwright.sync_api import sync_playwright

res = []
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

def abrir(b, quien, ancho=1440, alto=950):
    ctx = b.new_context(viewport={'width': ancho, 'height': alto}, accept_downloads=True, **({} if ancho > 800 else {'device_scale_factor': 2}))
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

def ir(pg, tab): pg.click(f'nav.tabs button[data-tab="{tab}"]'); pg.wait_for_timeout(900)
def ficha(pg, nombre, seccion='historia'):
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(300)
    ir(pg, 'lista'); pg.fill('#buscar-personal', nombre); pg.wait_for_timeout(400)
    pg.click(f'#tabla-personal a:has-text("{nombre}")'); pg.wait_for_timeout(1200)
    pg.click(f'[data-detail-tab="{seccion}"]'); pg.wait_for_timeout(900)
def msg(pg, sel='#hl-msg'): return (pg.text_content(sel) or '').strip()
def foto(pg, nombre): pg.screenshot(path=os.path.join(OUT, nombre + '.png'), full_page=False)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'admin')

    print('--- Historia laboral: relación migrada')
    ficha(pg, 'ADELA PALACIOS GALVAN')
    card = pg.text_content('#hl-raiz') or ''
    ok('RP Y1234567101' in card and 'Vigente' in card and '01/03/2025' in card and '01/06/2021' in card,
       'ADELA: relación migrada con RP, ingreso y antigüedad reconocida por separado')
    ok(pg.is_disabled('#d-empresa') and pg.is_disabled('#d-registro-patronal') and pg.is_disabled('#d-numero-interno'),
       'con historial, empresa, RP y número interno quedan bloqueados en la ficha')
    ok(pg.eval_on_selector('#d-estatus', "s => [...s.options].find(o => o.text === 'Baja').disabled"), 'la opción «Baja» del estatus queda deshabilitada')
    foto(pg, '01-historia-migrada')
    pg.click('[data-accion="corregir"]'); pg.wait_for_timeout(300)
    f = '#hl-raiz form'
    pg.fill(f + ' [name=sbc]', '450'); pg.fill(f + ' [name=umf]', '012')
    pg.select_option(f + ' [name=tipo_trabajador]', '1'); pg.select_option(f + ' [name=tipo_salario]', '0'); pg.select_option(f + ' [name=jornada]', '0')
    pg.fill(f + ' [name=motivo]', 'Datos del expediente IMSS')
    pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1800)
    ok('Corrección registrada' in msg(pg), 'corregir datos de una relación migrada', msg(pg))
    ok('Corrección de datos' in (pg.text_content('#hl-raiz') or '') and 'UMF: — → 012' in (pg.text_content('#hl-raiz') or ''),
       'la corrección aparece en la línea de tiempo con antes → después')

    print('--- Esquema ambiguo')
    ficha(pg, 'BENITO ZAVALA GALINDO')
    ok(pg.is_visible('.hl-pend'), 'BENITO: el esquema sin relación aparece para que Nómina lo asigne')
    foto(pg, '02-esquema-pendiente')
    sel = pg.query_selector('.hl-pend select')
    opc = sel.eval_on_selector_all('option', 'os => os.map(o => [o.value, o.text])')
    destino = next(v for v, t in opc if 'Y1234567102' in t)
    sel.select_option(destino); pg.click('[data-asignar]'); pg.wait_for_timeout(1500)
    ok('Esquema asignado' in msg(pg) and not pg.is_visible('.hl-pend'), 'Nómina asigna el esquema a la relación correcta', msg(pg))

    print('--- Ingreso IMSS de alguien que solo tenía efectivo')
    ficha(pg, 'EDGAR MORALES PEÑA')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(300)
    f = '#hl-form-ingreso form'
    ok(pg.eval_on_selector(f + ' [name=rp]', 's => s.options[s.selectedIndex].text') == 'Y1234567101', 'el RP de la empresa se propone solo')
    pg.fill(f + ' [name=fecha]', '2026-10-20'); pg.fill(f + ' [name=sbc]', '400'); pg.fill(f + ' [name=umf]', '045'); pg.fill(f + ' [name=num]', '77')
    pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2000)
    t = pg.text_content('#hl-raiz') or ''
    ok('Ingreso registrado' in msg(pg) and 'RP Y1234567101' in t and 'IDSE pendiente' in t, 'ingreso registrado con su movimiento IDSE pendiente', msg(pg))
    ok(pg.eval_on_selector('#d-registro-patronal', 's => s.options[s.selectedIndex] ? s.options[s.selectedIndex].text : ""').startswith('Y1234567101'),
       'la ficha pasa a mostrar la relación con RP (v3.1)')
    foto(pg, '03-ingreso-registrado')
    rel = pg.get_attribute('.hl-card:has-text("Y1234567101")', 'data-relacion')
    pg.click(f'[data-accion="salario"][data-rel="{rel}"]'); pg.wait_for_timeout(300)
    f = f'#hl-form-{rel} form'
    pg.fill(f + ' [name=fecha]', '2026-10-25'); pg.fill(f + ' [name=sbc]', '410'); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1800)
    ok('Modificación de salario registrada' in msg(pg), 'modificación de salario', msg(pg))
    pg.click('[data-anular]'); pg.wait_for_timeout(300)
    pg.fill('[id^="hl-anular-"] [name=motivo]', 'Monto equivocado'); pg.click('[id^="hl-anular-"] button[type=submit]'); pg.wait_for_timeout(1800)
    ok('Movimiento anulado' in msg(pg) and 'Anulado' in (pg.text_content('#hl-raiz') or ''), 'anular la modificación deja el evento marcado como anulado', msg(pg))
    pg.click(f'[data-accion="baja"][data-rel="{rel}"]'); pg.wait_for_timeout(300)
    f = f'#hl-form-{rel} form'
    pg.fill(f + ' [name=fecha]', '2026-10-21'); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1500)
    ok('causa' in msg(pg).lower(), 'baja sin causa: la base la rechaza y la pantalla lo explica', msg(pg))
    pg.click(f'#hl-form-{rel} [data-cancelar]')

    print('--- Bandeja IDSE')
    pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    ir(pg, 'idse'); pg.wait_for_timeout(1200)
    ok('Falta: El registro patronal no tiene número de guía IDSE' in (pg.text_content('#idse-pend-08') or ''), 'sin guía, la bandeja dice qué falta')
    pg.fill('#idse-guia', '40001'); pg.click('#idse-guardar-rp'); pg.wait_for_timeout(1500)
    t = pg.text_content('#idse-pend-08') or ''
    ok('EDGAR MORALES PEÑA' in t and 'Contiene Ñ' in t, 'con guía: el alta queda lista, con el aviso de la Ñ')
    foto(pg, '04-bandeja-idse')
    pg.check('.idse-sel[data-tipo="08"]')
    with pg.expect_download() as d:
        pg.click('[data-generar="08"]')
    ruta = d.value.path(); nombre = d.value.suggested_filename
    cont = open(ruta, 'rb').read().decode('ascii')
    lineas = cont.split('\r\n')
    ok(nombre.endswith('.dat') and len(lineas) == 3 and lineas[2] == '' and all(len(l) == 168 for l in lineas[:2]),
       'se descarga el .dat: 1 movimiento + renglón final, 168 posiciones, CRLF', nombre)
    ok(lineas[0][22:49].rstrip() == 'MORALES' and lineas[0][49:76].rstrip() == 'PE#A' and lineas[0][103:109] == '040000' and lineas[0][138:148] == '        77',
       'contenido: apellidos (Ñ → #), SBC y clave del trabajador en su posición')
    pg.wait_for_timeout(800)
    pg.click('[data-pres]'); pg.wait_for_timeout(300)
    pg.fill('#idse-arch form [name=lote]', 'LOTE-001'); pg.fill('#idse-arch form [name=fecha]', '2026-10-21')
    pg.click('#idse-arch form button[type=submit]'); pg.wait_for_timeout(1500)
    ok('Presentado' in (pg.text_content('#idse-arch') or ''), 'archivo marcado como presentado con su lote')
    pg.click('[data-res]'); pg.wait_for_timeout(800)
    pg.fill('#idse-arch form [name=folio]', 'ACUSE-123'); pg.click('#idse-arch form button[type=submit]'); pg.wait_for_timeout(1500)
    ok('Con resultado' in (pg.text_content('#idse-arch') or '') and 'ACUSE-123' in (pg.text_content('#idse-arch') or ''), 'resultado registrado con folio del acuse')
    foto(pg, '05-archivo-con-resultado')
    ficha(pg, 'EDGAR MORALES PEÑA')
    t = pg.text_content('#hl-raiz') or ''
    ok('IDSE confirmado' in t and not pg.is_visible('[data-anular]'), 'en la ficha, el ingreso queda confirmado y ya no se puede anular')

    print('--- Modificación de salario y su archivo IDSE (07)')
    pg.click(f'[data-accion="salario"][data-rel="{rel}"]'); pg.wait_for_timeout(300)
    f = f'#hl-form-{rel} form'
    pg.fill(f + ' [name=fecha]', '2026-10-28'); pg.fill(f + ' [name=sbc]', '420'); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1800)
    ok('Modificación de salario registrada' in msg(pg), 'modificación de salario registrada para el archivo', msg(pg))
    pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    ir(pg, 'idse'); pg.wait_for_timeout(1500)
    t = pg.text_content('#idse-pend-07') or ''
    ok('EDGAR MORALES PEÑA' in t and '28/10/2026' in t and '420.00' in t, 'la bandeja muestra la modificación con fecha y SBC nuevo', t[:160])
    foto(pg, '05a-bandeja-modificaciones')
    pg.check('.idse-sel[data-tipo="07"]')
    with pg.expect_download() as d:
        pg.click('[data-generar="07"]')
    nombre = d.value.suggested_filename; lineas = open(d.value.path(), 'rb').read().decode('ascii').split('\r\n')
    m0 = lineas[0]
    ok(nombre.startswith('IDSE_MODIFICACIONES_') and len(lineas) == 3 and all(len(l) == 168 for l in lineas[:2]), 'se descarga el .dat de modificaciones: 1 + final, 168 posiciones, CRLF', nombre)
    ok(m0[103:109] == '042000' and m0[115:118] == '100' and m0[118:126] == '28102026' and m0[126:131] == ' ' * 5 and m0[131:138] == '0740001' and m0[149:167] == 'MOPE920303HDFRXD08',
       'contenido de la modificación: SBC nuevo, tipos, fecha, sin UMF, tipo 07 + guía y CURP', repr(m0[103:168]))
    pg.wait_for_timeout(800)
    ok('No hay modificaciones pendientes' in (pg.text_content('#idse-pend-07') or ''), 'la modificación sale de pendientes al generar su archivo')
    ficha(pg, 'EDGAR MORALES PEÑA')

    print('--- Baja y su archivo IDSE (02)')
    pg.click(f'[data-accion="baja"][data-rel="{rel}"]'); pg.wait_for_timeout(300)
    f = f'#hl-form-{rel} form'
    pg.fill(f + ' [name=fecha]', '2026-11-03'); pg.select_option(f + ' [name=causa]', '2'); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2000)
    ok('Baja registrada' in msg(pg), 'baja registrada con su causa', msg(pg))
    pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    ir(pg, 'idse'); pg.wait_for_timeout(1500)
    t = pg.text_content('#idse-pend-02') or ''
    ok('EDGAR MORALES PEÑA' in t and '2 · Separación voluntaria' in t and '03/11/2026' in t, 'la bandeja muestra la baja con fecha y causa', t[:160])
    ok('No hay altas pendientes' in (pg.text_content('#idse-pend-08') or ''), 'la baja no aparece entre las altas')
    foto(pg, '05b-bandeja-bajas')
    pg.check('.idse-sel[data-tipo="02"]')
    with pg.expect_download() as d:
        pg.click('[data-generar="02"]')
    nombre = d.value.suggested_filename; cont = open(d.value.path(), 'rb').read().decode('ascii'); lineas = cont.split('\r\n')
    b0 = lineas[0]
    ok(nombre.startswith('IDSE_BAJAS_') and nombre.endswith('.dat') and len(lineas) == 3 and lineas[2] == '' and all(len(l) == 168 for l in lineas[:2]),
       'se descarga el .dat de bajas: 1 baja + renglón final, 168 posiciones, CRLF', nombre)
    ok(b0[103:118] == '0' * 15 and b0[118:126] == '03112026' and b0[131:138] == '0240001' and b0[138:148] == '        77' and b0[148] == '2' and b0[149:167] == ' ' * 18,
       'contenido de la baja: ceros, fecha, tipo 02 + guía, clave, causa en 149 y sin CURP', repr(b0[103:168]))
    pg.wait_for_timeout(800)
    ok('IDSE_BAJAS_' in (pg.text_content('#idse-arch') or '') and 'No hay bajas pendientes' in (pg.text_content('#idse-pend-02') or ''), 'el archivo de bajas aparece en «Archivos generados» y la baja sale de pendientes')
    foto(pg, '05c-archivo-bajas')

    print('--- Alta de personal conectada al historial')
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    ir(pg, 'alta')
    ok(pg.is_visible('#f-fecha-ingreso-laboral'), 'el alta tiene el campo de fecha de ingreso')
    pg.fill('#f-nombres', 'PRUEBA'); pg.fill('#f-apellido1', 'ALTA'); pg.fill('#f-apellido2', 'HISTORIA')
    pg.select_option('#f-empresa', '0c000000-0000-4000-8000-000000000001'); pg.wait_for_timeout(300)
    pg.fill('#f-fecha-ingreso-laboral', '2026-11-02')
    pg.click('#panel-alta button[type=submit]'); pg.wait_for_timeout(2500)
    ok('Ingreso registrado en su Historia laboral' in (pg.text_content('#alta-guardada-texto') or ''), 'el alta registra el ingreso en la Historia laboral',
       (pg.text_content('#alta-guardada-texto') or '')[:160])

    print('--- Móvil y errores')
    ok(not pg.errores, 'sin errores de JavaScript (Administrador)', '; '.join(pg.errores)[:200])
    ctx.close()
    ctx, pg = abrir(b, 'nomina', 390, 844)
    ficha(pg, 'ADELA PALACIOS GALVAN')
    foto(pg, '06-historia-movil')
    ok(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'en móvil la Historia laboral no desborda la pantalla')
    ok(pg.is_visible('[data-accion="corregir"]') and not pg.is_visible('#idse-guardar-rp'), 'Nómina opera la historia; la guía del RP solo la edita Administrador')
    ok(not pg.errores, 'sin errores de JavaScript (Nómina, móvil)', '; '.join(pg.errores)[:200])
    ctx.close()
    for quien in ('consulta', 'coord'):
        ctx, pg = abrir(b, quien)
        ok(not pg.is_visible('nav.tabs button[data-tab="idse"]'), f'{quien}: no ve la pestaña IDSE')
        ok(not pg.errores, f'sin errores de JavaScript ({quien})', '; '.join(pg.errores)[:200])
        ctx.close()
    b.close()

fallas = [n for n, c in res if not c]
print(f"\n{len(res) - len(fallas)}/{len(res)} pruebas de pantalla correctas")
sys.exit(1 if fallas else 0)
