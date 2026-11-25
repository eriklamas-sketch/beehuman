"""Ojo para mostrar u ocultar «Nueva contraseña» y su confirmación (25-nov-2026). Página local, sin base de datos.
Uso: SJ=<ruta a supabase.js UMD> python3 ui_recuperacion_ojo.py
Cada lista: [tipo campo 1 tras clic, tipo campo 2 sin tocar, etiqueta del botón, tipo campo 2 tras clic, valor visible, campo 1 tras 2.º clic, campo 2 tras cambiar de pantalla]"""
from playwright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    b=p.chromium.launch(); res=[]
    for w,h in ((1280,800),(390,844)):
        pg=b.new_page(viewport={'width':w,'height':h}); err=[]; pg.on('pageerror',lambda e: err.append(str(e)))
        pg.route('**/*', lambda r: r.fulfill(path=os.environ['SJ'], content_type='application/javascript') if 'supabase-js' in r.request.url else (r.abort() if r.request.url.startswith('http') else r.continue_()))
        pg.goto('file://' + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'app', 'index.html')) + '#access_token=x&type=recovery&refresh_token=y'); pg.wait_for_timeout(1500)
        pg.evaluate("vistaLogin('nueva')"); pg.fill('#nueva-pass','Prueba123'); pg.fill('#nueva-pass2','Prueba124')
        b1,b2=pg.locator('#form-nueva-pass .ver-pass').all()
        b1.click(); t=[pg.get_attribute('#nueva-pass','type'),pg.get_attribute('#nueva-pass2','type'),b1.get_attribute('aria-label')]
        b2.click(); t+= [pg.get_attribute('#nueva-pass2','type'), pg.input_value('#nueva-pass2')]
        b1.click(); t+= [pg.get_attribute('#nueva-pass','type')]
        bx=b1.bounding_box(); ix=pg.locator('#nueva-pass').bounding_box()
        dentro = ix['x'] < bx['x'] and bx['x']+bx['width'] <= ix['x']+ix['width']+1 and ix['y'] <= bx['y'] and bx['y']+bx['height'] <= ix['y']+ix['height']+1
        pg.evaluate("vistaLogin('login'); vistaLogin('nueva')"); t+=[pg.get_attribute('#nueva-pass2','type')]
        pg.locator('#form-nueva-pass').screenshot(path=f'/tmp/ojo_{w}.png')
        print(w, t, 'ojo dentro del campo:', dentro, 'errores:', err[:1])
    b.close()
