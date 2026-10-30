"""Pruebas de la tabla de Personal y la ficha contra la base LOCAL (Postgres + PostgREST),
con datos ficticios. Sirve para comparar ANTES y DESPUÉS de la mejora UX.
Uso: python3 ux_pruebas.py <index.html> <carpeta_salida> <antes|despues>"""
import sys, os, json, time, hashlib
HTML, OUT, MODO = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
# Reutiliza la conexión simulada (rutas a PostgREST local, sesión firmada) de las pruebas de la Ola 1.
fuente = open(os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py'), encoding='utf-8').read()
fuente = fuente[:fuente.index('def abrir(')]
sys.argv = [sys.argv[0], HTML, OUT]
__file__ = os.path.join(AQUI, '..', 'ola1', 'ui_ola1.py')
exec(fuente)
from playwright.sync_api import sync_playwright

resultados = {}
envios = []
def abrir(b, quien, ancho=1440, alto=950):
    ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 800 else 2, accept_downloads=True)
    sesion = {'access_token': jwt(U[quien]), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
              'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
    ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});")
    base = ruta_para(quien)
    def ruta(route):
        r = route.request
        if '/rest/v1/' in r.url and r.method in ('POST', 'PATCH', 'DELETE') and '/rpc/' not in r.url:
            cuerpo = r.post_data or ''
            try:
                d = json.loads(cuerpo)
                # se omiten valores que cambian en cada corrida
                def limpiar(x):
                    if isinstance(x, dict): return {k: limpiar(v) for k, v in x.items() if k not in ('id', 'actualizado_en', 'fecha')}
                    if isinstance(x, list): return [limpiar(v) for v in x]
                    return x
                cuerpo = json.dumps(limpiar(d), sort_keys=True, ensure_ascii=False)
            except Exception: pass
            envios.append(f"{r.method} {r.url.split('/rest/v1/')[1].split('?')[0]} {cuerpo}")
        return base(route)
    ctx.route('**/*', ruta)
    pg = ctx.new_page(); pg.errores = []; pg.dialogos = []; pg.respuesta_dialogo = True
    pg.on('pageerror', lambda e: pg.errores.append(str(e)))
    def dialogo(d):
        pg.dialogos.append(d.message)
        d.accept() if pg.respuesta_dialogo else d.dismiss()
    pg.on('dialog', dialogo)
    pg.goto('file://' + os.path.abspath(HTML))
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    return ctx, pg

def ir(pg, tab):
    pg.click(f'nav.tabs button[data-tab="{tab}"]'); pg.wait_for_timeout(700)

def descargar(pg, sel):
    with pg.expect_download() as d:
        pg.click(sel)
    ruta = d.value.path()
    return hashlib.sha256(open(ruta, 'rb').read()).hexdigest()[:16], open(ruta, encoding='utf-8-sig').read().count('\n')

def abrir_ficha(pg, nombre):
    pg.fill('#buscar-personal', nombre); pg.wait_for_timeout(400)
    pg.click(f'#tabla-personal a:has-text("{nombre}")'); pg.wait_for_timeout(1200)

def seccion(pg, s):
    pg.click(f'[data-detail-tab="{s}"]'); pg.wait_for_timeout(300)

def cerrar(pg):
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button')

SECCIONES = ['personal', 'organizacion', 'laboral', 'compensacion', 'prestaciones', 'contacto', 'movimientos']

with sync_playwright() as p:
    b = p.chromium.launch()
    # ================= Administrador: tabla =================
    ctx, pg = abrir(b, 'admin'); ir(pg, 'lista')
    resultados['conteo'] = pg.inner_text('#lista-conteo')
    resultados['filas_pagina1'] = pg.locator('#tabla-personal tr').count()
    pg.screenshot(path=f'{OUT}/01-personal-escritorio.png', full_page=False)
    pg.click('#pagina-siguiente'); pg.wait_for_timeout(300)
    resultados['pagina2'] = [pg.inner_text('#pagina-texto'), pg.locator('#tabla-personal tr').count()]
    pg.click('#pagina-anterior'); pg.wait_for_timeout(300)
    resultados['csv_personal_todo'] = descargar(pg, '#exportar-personal')
    resultados['csv_esquemas_todo'] = descargar(pg, '#exportar-esquemas')
    pg.select_option('#filtro-estatus', 'Baja'); pg.wait_for_timeout(300)
    resultados['filtro_baja'] = pg.locator('#tabla-personal tr').count()
    pg.select_option('#filtro-estatus', ''); pg.wait_for_timeout(300)
    pg.fill('#buscar-personal', 'ADELA'); pg.wait_for_timeout(400)
    resultados['busqueda_adela'] = pg.locator('#tabla-personal tr').count()
    resultados['csv_personal_adela'] = descargar(pg, '#exportar-personal')
    pg.fill('#buscar-personal', ''); pg.wait_for_timeout(300)
    pg.click('#encabezado-personal th:has-text("ID")'); pg.wait_for_timeout(300)
    resultados['orden_id_primero'] = pg.inner_text('#tabla-personal tr:first-child td:first-child')
    pg.click('#encabezado-personal th:has-text("Nombre")'); pg.wait_for_timeout(300)
    pg.fill('#buscar-personal', 'CESAR'); pg.wait_for_timeout(300)
    pg.locator('#panel-lista .table-wrap').screenshot(path=f'{OUT}/02-personal-fila-cesar.png')
    pg.fill('#buscar-personal', ''); pg.wait_for_timeout(300)
    pg.locator('#panel-lista .table-wrap').screenshot(path=f'{OUT}/03-personal-tabla.png')
    resultados['admin_errores'] = pg.errores[:3]

    # ================= Ficha: secciones, edición y guardado =================
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN')
    for i, s in enumerate(SECCIONES):
        seccion(pg, s); pg.screenshot(path=f'{OUT}/1{i}-ficha-{s}.png', full_page=True)
    seccion(pg, 'prestaciones'); pg.fill('#d-fonacot', 'FON-12345')
    seccion(pg, 'contacto'); pg.fill('#d-emerg-telefono', '5512345678')
    seccion(pg, 'personal')
    resultados['valor_tras_navegar'] = [pg.input_value('#d-fonacot'), pg.input_value('#d-emerg-telefono')]
    pg.click('#btn-guardar-detalle'); pg.wait_for_timeout(1800)
    resultados['guardado_bd'] = sql("select no_fonacot||'|'||contacto_emergencia_telefono from personal where id='0a100000-0000-4000-8000-000000000011'")
    resultados['movimientos_bd'] = sql("select string_agg(campo, ',' order by campo) from movimientos where personal_id='0a100000-0000-4000-8000-000000000011'")
    resultados['toast_guardado'] = pg.inner_text('#toast-detalle')

    # ================= Confirmación al cerrar =================
    pg.dialogos.clear(); cerrar(pg); pg.wait_for_timeout(400)
    resultados['cerrar_sin_cambios'] = [pg.is_visible('#modal-overlay'), len(pg.dialogos)]
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN')
    seccion(pg, 'contacto'); pg.fill('#d-emerg-nombre', 'CAMBIO SIN GUARDAR')
    pg.dialogos.clear(); pg.respuesta_dialogo = False
    cerrar(pg); pg.wait_for_timeout(400)
    resultados['cerrar_con_cambios_cancelar'] = [pg.is_visible('#modal-overlay'), len(pg.dialogos), pg.input_value('#d-emerg-nombre')]
    pg.respuesta_dialogo = True
    cerrar(pg); pg.wait_for_timeout(400)
    resultados['cerrar_con_cambios_aceptar'] = [pg.is_visible('#modal-overlay'), len(pg.dialogos)]
    resultados['descartado_en_bd'] = sql("select coalesce(contacto_emergencia_nombre,'(vacío)') from personal where id='0a100000-0000-4000-8000-000000000011'")
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN'); seccion(pg, 'contacto')
    resultados['reabrir_valor'] = pg.input_value('#d-emerg-nombre')
    seccion(pg, 'personal'); pg.select_option('#d-estatus', 'Suspendido'); pg.select_option('#d-estatus', 'Activo')
    pg.dialogos.clear(); cerrar(pg); pg.wait_for_timeout(400)
    resultados['cambiar_y_regresar_valor'] = [pg.is_visible('#modal-overlay'), len(pg.dialogos)]
    if pg.is_visible('#modal-overlay'): cerrar(pg); pg.wait_for_timeout(300)

    # ================= Registros de pago =================
    abrir_ficha(pg, 'CESAR DELGADILLO HINOJOSA'); seccion(pg, 'compensacion'); pg.wait_for_timeout(800)
    pg.locator('#rp-componente').screenshot(path=f'{OUT}/20-pagos-cesar.png')
    if pg.locator('#d-registros-pago details.rp-historicos > summary').count():
        pg.click('#d-registros-pago details.rp-historicos > summary'); pg.wait_for_timeout(200)
        pg.locator('#rp-componente').screenshot(path=f'{OUT}/20b-pagos-cesar-historicos.png')
    cerrar(pg); pg.wait_for_timeout(300)
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN'); seccion(pg, 'compensacion'); pg.wait_for_timeout(800)
    pg.locator('#rp-componente').screenshot(path=f'{OUT}/21-pagos-adela.png')
    efectivo = sql("select id from personal_registros_pago where personal_id='0a100000-0000-4000-8000-000000000011' and clasificacion_id='0f000000-0000-4000-8000-000000000002'")
    pg.click(f'#d-registros-pago button[onclick="cerrarRegistroPago(\'{efectivo}\')"]'); pg.wait_for_timeout(1200)
    resultados['cerrar_registro_bd'] = sql(f"select activo from personal_registros_pago where id='{efectivo}'")
    pg.locator('#rp-componente').screenshot(path=f'{OUT}/22-pagos-adela-cerrado.png')
    if pg.locator('#d-registros-pago details.rp-historicos:not([open]) > summary').count(): pg.click('#d-registros-pago details.rp-historicos > summary'); pg.wait_for_timeout(200)
    pg.click(f'#d-registros-pago button[onclick="reactivarRegistroPago(\'{efectivo}\')"]'); pg.wait_for_timeout(1200)
    resultados['reactivar_registro_bd'] = sql(f"select activo from personal_registros_pago where id='{efectivo}'")
    pg.click(f'#d-registros-pago button[onclick="editarRegistroPago(\'{efectivo}\')"]'); pg.wait_for_timeout(500)
    resultados['editar_abre_form'] = [pg.is_visible('#rp-form'), pg.input_value('#rp-sueldo')]
    pg.fill('#rp-notas', 'nota de prueba'); pg.click('#btn-rp-guardar'); pg.wait_for_timeout(1200)
    resultados['editar_guarda_bd'] = sql(f"select sueldo||'|'||coalesce(notas,'') from personal_registros_pago where id='{efectivo}'")
    resultados['ficha_errores'] = pg.errores[:3]
    cerrar(pg); pg.wait_for_timeout(300)
    ctx.close()

    # ================= Móvil =================
    ctx, pg = abrir(b, 'admin', 390, 844); ir(pg, 'lista')
    pg.screenshot(path=f'{OUT}/30-movil-personal.png', full_page=False)
    resultados['movil_ancho_lista'] = pg.evaluate('document.documentElement.scrollWidth')
    abrir_ficha(pg, 'ADELA PALACIOS GALVAN')
    pg.screenshot(path=f'{OUT}/31-movil-ficha.png', full_page=False)
    seccion(pg, 'movimientos'); pg.screenshot(path=f'{OUT}/32-movil-ficha-movimientos.png', full_page=False)
    seccion(pg, 'compensacion'); pg.wait_for_timeout(600); pg.screenshot(path=f'{OUT}/33-movil-ficha-compensacion.png', full_page=True)
    resultados['movil_ancho_ficha'] = pg.evaluate('document.documentElement.scrollWidth')
    resultados['movil_errores'] = pg.errores[:3]
    ctx.close()

    # ================= Nómina y Consulta =================
    ctx, pg = abrir(b, 'nomina'); ir(pg, 'lista')
    resultados['nomina_csv_esquemas'] = descargar(pg, '#exportar-esquemas')
    pg.locator('#panel-lista .table-wrap').screenshot(path=f'{OUT}/40-nomina-tabla.png'); ctx.close()
    ctx, pg = abrir(b, 'consulta'); ir(pg, 'lista')
    resultados['consulta_columnas'] = pg.locator('#encabezado-personal th').count()
    pg.locator('#panel-lista .table-wrap').screenshot(path=f'{OUT}/41-consulta-tabla.png')
    resultados['consulta_errores'] = pg.errores[:3]; ctx.close()
    b.close()

resultados['envios'] = envios
json.dump(resultados, open(f'{OUT}/resultados.json', 'w'), ensure_ascii=False, indent=1)
for k, v in resultados.items():
    if k != 'envios': print(k, '=>', v)
print('envíos de escritura:', len(envios))
