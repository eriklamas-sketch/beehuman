"""D6 · Recuperación de contraseña en la pantalla de inicio de sesión (Auth simulado; nunca toca Supabase).
  C1  «¿Olvidaste tu contraseña?» abre la solicitud y conserva el correo escrito.
  C2  Solicitud: llama a /recover con el correo y redirect_to = la URL de la app; mensaje que no revela si el correo existe.
  C3  Correo inexistente: el mismo mensaje. Límite (429) y falla de red: mensajes propios, sin revelar nada.
  C4  Retorno desde el enlace con la última actividad vieja (> 30 min): pantalla «Nueva contraseña», la regla de
      inactividad no cierra la sesión de recuperación, la aplicación no se abre y la URL queda sin tokens.
  C5  Validaciones: mínimo 8 caracteres y confirmación igual; «same_password» con mensaje claro.
  C6  Guardar: PUT /user con la contraseña, cierre de sesión global, sin sesión guardada y vuelta al login con aviso.
  C7  Enlace vencido (#error_code=otp_expired): vuelve a la solicitud con aviso.
  C8  Abandonar la pantalla «Nueva contraseña» sin guardar: la siguiente visita NO abre la aplicación.
  C9  Sin errores de JavaScript; nada sale a internet.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_recuperacion.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']; REF = 'sflvpgkmtaxzogpgetxn'
UID = 'e9000000-0000-4000-8000-000000000001'; CORREO = 'nomina.demo@beehuman.invalid'
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'}
b64 = lambda x: base64.urlsafe_b64encode(json.dumps(x).encode()).rstrip(b'=').decode()
TOKEN = b64({'alg': 'HS256', 'typ': 'JWT'}) + '.' + b64({'sub': UID, 'role': 'authenticated', 'aud': 'authenticated', 'exp': int(time.time()) + 3600,
                                                          'email': CORREO, 'amr': [{'method': 'recovery', 'timestamp': int(time.time())}]}) + '.firma'
USUARIO = {'id': UID, 'aud': 'authenticated', 'role': 'authenticated', 'email': CORREO}

res = []
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

def abrir(b, hash_='', actividad_previa_ms=None, modo_recover='ok', modo_update='ok', sesion_previa=False, pendiente=False):
    ctx = b.new_context(viewport={'width': 1280, 'height': 900})
    js = "if(!sessionStorage.getItem('_iny')){sessionStorage.setItem('_iny','1');"
    if actividad_previa_ms is not None: js += f"localStorage.setItem('bh_ultima_actividad', String(Date.now() - {actividad_previa_ms}));"
    if sesion_previa:
        ses = {'access_token': TOKEN, 'token_type': 'bearer', 'expires_in': 3600, 'expires_at': int(time.time()) + 3600, 'refresh_token': 'r', 'user': USUARIO}
        js += f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});"
    if pendiente: js += "localStorage.setItem('bh_recuperacion_pendiente','1');"
    js += "}"
    ctx.add_init_script(js)
    reg = {'recover': [], 'put_user': [], 'logout': [], 'rest': [], 'externo': []}
    def ruta(route):
        req = route.request; u = urlparse(req.url)
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path == '/auth/v1/recover':
                reg['recover'].append({'body': json.loads(req.post_data or '{}'), 'q': parse_qs(u.query)})
                if modo_recover == '429': return route.fulfill(status=429, headers=CORS, json={'code': 'over_email_send_rate_limit', 'msg': 'For security purposes, you can only request this after 60 seconds.'})
                if modo_recover == 'red': return route.abort()
                return route.fulfill(status=200, headers=CORS, json={})
            if u.path == '/auth/v1/user' and req.method == 'GET': return route.fulfill(status=200, headers=CORS, json=USUARIO)
            if u.path == '/auth/v1/user' and req.method == 'PUT':
                reg['put_user'].append(json.loads(req.post_data or '{}'))
                if modo_update == 'same': return route.fulfill(status=422, headers={**CORS, 'x-supabase-api-version': '2024-01-01', 'access-control-expose-headers': 'x-supabase-api-version'},
                                                               json={'code': 'same_password', 'message': 'New password should be different from the old password.'})
                return route.fulfill(status=200, headers=CORS, json=USUARIO)
            if u.path == '/auth/v1/logout':
                reg['logout'].append(parse_qs(u.query)); return route.fulfill(status=204, headers=CORS, body='')
            if u.path.startswith('/rest/v1/'):
                reg['rest'].append(u.path); return route.fulfill(status=200, headers=CORS, json=[])
            return route.fulfill(status=200, headers=CORS, json={})
        if u.scheme in ('http', 'https'): reg['externo'].append(req.url); return route.abort()
        return route.continue_()
    ctx.route('**/*', ruta)
    pg = ctx.new_page(); pg.errores = []
    pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda dl: dl.accept())
    pg.goto('file://' + os.path.abspath(HTML) + hash_)
    pg.wait_for_selector('#login-screen', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    return ctx, pg, reg

vis = lambda pg, sel: pg.is_visible(sel)
txt = lambda pg, sel: (pg.text_content(sel) or '').strip()
sesion = lambda pg: pg.evaluate(f"() => !!localStorage.getItem('sb-{REF}-auth-token')")
HASH_REC = f'#access_token={TOKEN}&expires_in=3600&expires_at={int(time.time()) + 3600}&refresh_token=r1&token_type=bearer&type=recovery'
errores = []; externos = []

with sync_playwright() as p:
    b = p.chromium.launch()

    print('== C1–C3 · Solicitud ==')
    ctx, pg, reg = abrir(b)
    ok(vis(pg, '#login-olvide') and txt(pg, '#login-olvide') == '¿Olvidaste tu contraseña?', 'C1 El inicio de sesión muestra «¿Olvidaste tu contraseña?»')
    pg.fill('#login-email', CORREO); pg.click('#login-olvide'); pg.wait_for_timeout(300)
    ok(vis(pg, '#form-recuperar') and not vis(pg, '#form-login') and txt(pg, '#login-titulo') == 'Recuperar contraseña' and pg.input_value('#rec-email') == CORREO,
       'C1 Abre «Recuperar contraseña» y conserva el correo escrito')
    pg.screenshot(path=f'{OUT}/R1_solicitud.png')
    pg.fill('#rec-email', 'no-es-correo'); pg.click('#btn-recuperar'); pg.wait_for_timeout(300)
    ok('correo válido' in txt(pg, '#toast-recuperar') and not reg['recover'], 'C2 Correo con formato inválido: aviso y no se llama al servidor')
    pg.fill('#rec-email', CORREO); pg.click('#btn-recuperar'); pg.wait_for_timeout(1200)
    r = reg['recover'][-1] if reg['recover'] else {}
    destino = (r.get('q', {}).get('redirect_to') or [''])[0]
    ok(r and r['body'].get('email') == CORREO and destino.startswith('file://') and destino.endswith('/app/index.html'),
       'C2 Llama a /recover con el correo y redirect_to = la URL de la aplicación', destino)
    m_ok = txt(pg, '#toast-recuperar')
    ok(m_ok.startswith('Si el correo está registrado') and 'registrado' in m_ok, 'C2 Mensaje que no revela si el correo existe', m_ok[:70])
    pg.screenshot(path=f'{OUT}/R2_enviado.png')
    pg.fill('#rec-email', 'nadie@ejemplo.invalid'); pg.click('#btn-recuperar'); pg.wait_for_timeout(1200)
    ok(txt(pg, '#toast-recuperar') == m_ok, 'C3 Correo inexistente: exactamente el mismo mensaje')
    pg.click('#rec-volver'); pg.wait_for_timeout(300)
    ok(vis(pg, '#form-login') and txt(pg, '#login-titulo') == 'Iniciar sesión', 'C1 «Volver a iniciar sesión» regresa al login')
    errores += pg.errores; externos += reg['externo']; ctx.close()
    for modo, esperado, n in (('429', 'Espera unos minutos', 'C3 Límite de envíos (429): pide esperar, sin revelar nada'),
                              ('red', 'Revisa tu conexión', 'C3 Falla de red: mensaje de reintento')):
        ctx, pg, reg = abrir(b, modo_recover=modo)
        pg.click('#login-olvide'); pg.fill('#rec-email', CORREO); pg.click('#btn-recuperar'); pg.wait_for_timeout(1500)
        ok(esperado in txt(pg, '#toast-recuperar') and 'registrad' not in txt(pg, '#toast-recuperar').replace('Si el correo está registrado', ''), n, txt(pg, '#toast-recuperar'))
        errores += pg.errores; externos += reg['externo']; ctx.close()

    print('== C4–C6 · Retorno desde el enlace con la sesión inactiva hace 2 horas ==')
    ctx, pg, reg = abrir(b, hash_=HASH_REC, actividad_previa_ms=2 * 3600 * 1000, modo_update='same')
    ok(vis(pg, '#form-nueva-pass') and txt(pg, '#login-titulo') == 'Nueva contraseña' and not vis(pg, '#app-content'),
       'C4 El enlace abre «Nueva contraseña» aunque la última actividad sea de hace 2 h; la aplicación no se abre')
    ok(sesion(pg) and not reg['logout'], 'C4 La regla de inactividad no cierra la sesión de recuperación')
    ok('access_token' not in pg.url and '#' not in pg.url, 'C4 La URL queda sin tokens', pg.url[-40:])
    ok(not reg['rest'], 'C4 No se consulta ningún dato de la aplicación', str(reg['rest'][:3]))
    pg.screenshot(path=f'{OUT}/R3_nueva_contrasena.png')
    pg.fill('#nueva-pass', 'corta'); pg.fill('#nueva-pass2', 'corta'); pg.click('#btn-nueva-pass'); pg.wait_for_timeout(300)
    ok('al menos 8' in txt(pg, '#toast-nueva-pass') and not reg['put_user'], 'C5 Menos de 8 caracteres: aviso, sin llamar al servidor')
    pg.fill('#nueva-pass', 'Nueva-Clave-2026'); pg.fill('#nueva-pass2', 'Nueva-Clave-2027'); pg.click('#btn-nueva-pass'); pg.wait_for_timeout(300)
    ok('no coinciden' in txt(pg, '#toast-nueva-pass') and not reg['put_user'], 'C5 Confirmación distinta: aviso, sin llamar al servidor')
    pg.fill('#nueva-pass2', 'Nueva-Clave-2026'); pg.click('#btn-nueva-pass'); pg.wait_for_timeout(1200)
    ok('distinta de la anterior' in txt(pg, '#toast-nueva-pass') and vis(pg, '#form-nueva-pass'), 'C5 Igual a la anterior (same_password): mensaje claro y sigue en la pantalla')
    errores += pg.errores; externos += reg['externo']; ctx.close()

    ctx, pg, reg = abrir(b, hash_=HASH_REC, actividad_previa_ms=2 * 3600 * 1000)
    pg.fill('#nueva-pass', 'Nueva-Clave-2026'); pg.fill('#nueva-pass2', 'Nueva-Clave-2026'); pg.click('#btn-nueva-pass'); pg.wait_for_timeout(1800)
    ok(reg['put_user'] and reg['put_user'][-1].get('password') == 'Nueva-Clave-2026', 'C6 Guarda con PUT /user y la contraseña nueva')
    ok(reg['logout'] and reg['logout'][-1].get('scope') == ['global'] and not sesion(pg), 'C6 Cierra la sesión en todos los dispositivos y no queda sesión guardada', str(reg['logout']))
    ok(vis(pg, '#form-login') and not vis(pg, '#app-content') and 'se actualizó' in txt(pg, '#toast-login'), 'C6 Vuelve al login con «Tu contraseña se actualizó…»', txt(pg, '#toast-login'))
    ok(pg.evaluate("() => localStorage.getItem('bh_recuperacion_pendiente')") is None, 'C6 No queda marca de recuperación pendiente')
    pg.screenshot(path=f'{OUT}/R4_actualizada.png')
    errores += pg.errores; externos += reg['externo']; ctx.close()

    print('== C7 · Enlace vencido ==')
    ctx, pg, reg = abrir(b, hash_='#error=access_denied&error_code=otp_expired&error_description=Email+link+is+invalid+or+has+expired')
    ok(vis(pg, '#form-recuperar') and 'venció o ya se usó' in txt(pg, '#toast-recuperar') and '#' not in pg.url and not vis(pg, '#app-content'),
       'C7 Enlace vencido: vuelve a la solicitud con aviso y la URL limpia', txt(pg, '#toast-recuperar'))
    pg.screenshot(path=f'{OUT}/R5_vencido.png')
    errores += pg.errores; externos += reg['externo']; ctx.close()

    print('== C8 · Recuperación abandonada ==')
    ctx, pg, reg = abrir(b, sesion_previa=True, pendiente=True, actividad_previa_ms=1000)
    ok(vis(pg, '#form-login') and not vis(pg, '#app-content') and not sesion(pg) and pg.evaluate("() => localStorage.getItem('bh_recuperacion_pendiente')") is None,
       'C8 Con una recuperación abandonada, la siguiente visita pide iniciar sesión y descarta la sesión del enlace')
    errores += pg.errores; externos += reg['externo']; ctx.close()
    b.close()

ok(not errores, 'C9 Sin errores de JavaScript', '; '.join(errores)[:200])
ok(not externos, 'C9 Nada sale a internet', str(externos[:3]))
malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {len(res) - len(malas)} de {len(res)} verificaciones OK')
for n, _ in malas: print('  FALLA:', n)
sys.exit(1 if malas else 0)
