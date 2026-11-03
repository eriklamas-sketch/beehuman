"""Pruebas de pantalla: encabezado (bloque de usuario a la derecha, «Cerrar sesión»)
y cierre por inactividad. Base LOCAL; nunca toca Supabase.
Uso: python3 ui_sesion.py <index.html> <carpeta_capturas>"""
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

def abrir(b, quien, ancho=1440, alto=900, inact_ms=None, aviso_ms=None, actividad_previa=None):
    ctx = b.new_context(viewport={'width': ancho, 'height': alto}, **({} if ancho > 800 else {'device_scale_factor': 2}))
    sesion = {'access_token': jwt(U[quien]), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
              'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
    js = "if(!sessionStorage.getItem('_iny')){sessionStorage.setItem('_iny','1');"
    js += f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});"
    if actividad_previa is not None: js += f"localStorage.setItem('bh_ultima_actividad', String(Date.now() - {actividad_previa}));"
    js += "}"
    if inact_ms: js += f"window.BH_PRUEBA_INACTIVIDAD_MS={inact_ms};window.BH_PRUEBA_AVISO_MS={aviso_ms};"
    ctx.add_init_script(js)
    ctx.route('**/*', ruta_para(quien))
    pg = ctx.new_page(); pg.errores = []
    pg.on('pageerror', lambda e: pg.errores.append(str(e)))
    pg.goto('file://' + os.path.abspath(HTML))
    return ctx, pg

def esperar_app(pg):
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1200)

def caja(pg, sel): return pg.eval_on_selector(sel, 'e => { const r = e.getBoundingClientRect(); return {l: r.left, r: r.right, w: r.width, vis: r.width > 0 && getComputedStyle(e).display !== "none"}; }')
def sesion_guardada(pg): return pg.evaluate(f"() => !!localStorage.getItem('sb-{REF}-auth-token')")

with sync_playwright() as p:
    b = p.chromium.launch()
    errores = []

    print('--- Encabezado por rol (escritorio)')
    bordes = {}
    for quien in ['admin', 'nomina', 'consulta', 'coord']:
        ctx, pg = abrir(b, quien); esperar_app(pg)
        u, t, bt = caja(pg, '.topbar-user'), caja(pg, '.app-topbar'), caja(pg, '.user-menu.btn-salir')
        bordes[quien] = u['r']
        ok(u['l'] > t['l'] + t['w'] / 2 and abs(t['r'] - u['r']) < 4, f'{quien}: bloque de usuario alineado a la derecha', f"usuario {u['l']:.0f}-{u['r']:.0f}, barra {t['l']:.0f}-{t['r']:.0f}")
        ok(bt['vis'] and (pg.inner_text('.user-menu.btn-salir') or '').strip().endswith('Cerrar sesión'), f'{quien}: botón «Cerrar sesión» visible')
        if quien == 'coord': pg.screenshot(path=os.path.join(OUT, '01-coordinador-encabezado.png'), clip={'x': 0, 'y': 0, 'width': 1440, 'height': 160})
        if quien == 'admin': pg.screenshot(path=os.path.join(OUT, '02-admin-encabezado.png'), clip={'x': 0, 'y': 0, 'width': 1440, 'height': 160})
        errores += pg.errores; ctx.close()
    ok(max(bordes.values()) - min(bordes.values()) < 2, 'el bloque termina en el mismo lugar en los cuatro roles', str(bordes))

    print('--- Móvil (390 px)')
    for quien in ['coord', 'admin']:
        ctx, pg = abrir(b, quien, 390, 844); esperar_app(pg)
        bt = caja(pg, '.user-menu.btn-salir')
        ancho = pg.evaluate('() => document.documentElement.scrollWidth')
        ok(bt['vis'] and 'Salir' in pg.inner_text('.user-menu.btn-salir') and bt['r'] <= 390, f'{quien} móvil: botón «Salir» visible dentro de la pantalla')
        ok(ancho <= 390, f'{quien} móvil: sin desborde horizontal', str(ancho))
        if quien == 'coord': pg.screenshot(path=os.path.join(OUT, '03-coordinador-movil.png'), clip={'x': 0, 'y': 0, 'width': 390, 'height': 200})
        errores += pg.errores; ctx.close()

    print('--- Cerrar sesión con el botón')
    ctx, pg = abrir(b, 'coord'); esperar_app(pg)
    pg.click('.user-menu.btn-salir')
    try: pg.wait_for_selector('#login-screen', state='visible', timeout=10000); pg.wait_for_timeout(500)
    except Exception: pass
    ok(pg.is_visible('#login-screen') and not pg.is_visible('#app-content') and not sesion_guardada(pg), 'el botón cierra la sesión y lleva al inicio de sesión',
       f"app={pg.is_visible('#app-content')} login={pg.is_visible('#login-screen')} token={sesion_guardada(pg)} url={pg.url[-30:]}")
    errores += pg.errores; ctx.close()

    print('--- Inactividad (tiempos acortados: 10 s, aviso a los 6 s)')
    ctx, pg = abrir(b, 'nomina', inact_ms=10000, aviso_ms=6000); esperar_app(pg)
    pg.mouse.move(10, 10)
    for i in range(14):               # usuario activo: se mueve cada segundo durante 14 s (más que el límite)
        pg.mouse.move(200 + i * 10, 300); pg.wait_for_timeout(1000)
    ok(pg.is_visible('#app-content') and not pg.is_visible('#aviso-inactividad'), 'usuario activo: ni aviso ni cierre aunque pase el límite')
    pg.wait_for_selector('#aviso-inactividad', timeout=8000)
    estilo = pg.eval_on_selector('#aviso-inactividad', 'e => { const c = getComputedStyle(e); return c.position + " " + c.backgroundColor + " " + c.zIndex; }')
    ok('fixed' in estilo and 'rgba' in estilo, 'el aviso cubre la pantalla con fondo oscurecido', estilo)
    ok(pg.is_visible('#aviso-inactividad'), 'sin actividad aparece el aviso antes del cierre', pg.text_content('#aviso-inactividad-tiempo') if pg.is_visible('#aviso-inactividad') else '')
    pg.click('#aviso-inactividad-seguir'); pg.wait_for_timeout(500)
    ok(not pg.is_visible('#aviso-inactividad') and pg.is_visible('#app-content'), '«Seguir trabajando» quita el aviso y mantiene la sesión')
    pg.wait_for_selector('#aviso-inactividad', timeout=10000); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(OUT, '04-aviso-inactividad.png'))
    pg.keyboard.press('Shift'); pg.wait_for_timeout(500)
    ok(not pg.is_visible('#aviso-inactividad') and pg.is_visible('#app-content'), 'una tecla también cuenta como «sigo aquí»')
    pg.wait_for_selector('#aviso-inactividad', timeout=10000)
    pg.wait_for_selector('#login-screen', state='visible', timeout=15000); pg.wait_for_timeout(800)
    ok(not sesion_guardada(pg) and 'inactividad' in (pg.text_content('#toast-login') or ''), 'sin respuesta, la sesión se cierra y el inicio explica por qué', (pg.text_content('#toast-login') or '').strip())
    pg.screenshot(path=os.path.join(OUT, '05-login-tras-inactividad.png'))
    errores += pg.errores; ctx.close()

    print('--- «Cerrar sesión» dentro del aviso')
    ctx, pg = abrir(b, 'coord', inact_ms=10000, aviso_ms=6000); esperar_app(pg)
    pg.wait_for_selector('#aviso-inactividad', timeout=10000)
    pg.click('#aviso-inactividad-salir'); pg.wait_for_selector('#login-screen', state='visible', timeout=10000); pg.wait_for_timeout(500)
    ok(not sesion_guardada(pg), 'el botón del aviso cierra la sesión de inmediato')
    errores += pg.errores; ctx.close()

    print('--- Dos pestañas: la actividad en una mantiene la otra')
    ctx, pg = abrir(b, 'admin', inact_ms=10000, aviso_ms=6000); esperar_app(pg)
    pg2 = ctx.new_page(); pg2.errores = []; pg2.on('pageerror', lambda e: pg2.errores.append(str(e)))
    pg2.goto('file://' + os.path.abspath(HTML)); esperar_app(pg2)
    for i in range(13): pg2.mouse.move(100 + i * 5, 200); pg2.wait_for_timeout(1000)
    ok(pg.is_visible('#app-content') and not pg.is_visible('#login-screen'), 'la pestaña sin uso sigue abierta mientras se trabaja en la otra')
    errores += pg.errores + pg2.errores; ctx.close()

    print('--- Regreso tras 31 min sin actividad (navegador cerrado)')
    ctx, pg = abrir(b, 'admin', actividad_previa=31 * 60 * 1000)
    pg.wait_for_selector('#login-screen', state='visible', timeout=15000); pg.wait_for_timeout(800)
    ok(not pg.is_visible('#app-content') and not sesion_guardada(pg), 'entra al inicio de sesión, no a los datos')
    errores += pg.errores; ctx.close()
    ctx, pg = abrir(b, 'admin', actividad_previa=10 * 60 * 1000); esperar_app(pg)
    ok(pg.is_visible('#app-content'), 'con 10 min de inactividad la sesión sigue')
    errores += pg.errores; ctx.close()

    ok(not errores, 'ningún error de JavaScript', '; '.join(errores[:3]))
    b.close()

print(f"\n{sum(1 for _, c in res if c)}/{len(res)} pruebas correctas")
