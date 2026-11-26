"""Revisión única de la página publicada en el preview (bytes idénticos al commit) con la base local:
selector de tipo de carga, plantilla, simulación, errores y reporte. No guarda nada."""
import sys, os, json, time, csv
HTML, CSV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; os.makedirs(OUT, exist_ok=True)
H = '/home/claude/beehuman/supabase/verificacion/ola1/ui_ola1.py'
f = open(H, encoding='utf-8').read(); f = f[:f.index('def abrir(')]
sys.argv = [sys.argv[0], HTML, OUT]; __file__ = H; exec(f)
V21 = '/home/claude/herramientas_prueba_bh/env/v21'
from playwright.sync_api import sync_playwright
escrituras = []
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
    s = {'access_token': jwt(U['admin']), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x', 'user': {'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}}
    ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(s))});")
    base = ruta_para('admin')
    def ruta(route):
        r = route.request
        if '/rest/v1/' in r.url and r.method in ('POST', 'PATCH', 'DELETE'):
            cuerpo = r.post_data or ''
            if '/rpc/imp_alta_personas' in r.url: escrituras.append('rpc confirmar=' + str(json.loads(cuerpo).get('p_confirmar')))
            elif '/rpc/' not in r.url: escrituras.append(r.method + ' ' + r.url.split('/rest/v1/')[1])
        return base(route)
    ctx.route('**/*', ruta)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    pg.click('nav.tabs button[data-tab="alta"]'); pg.wait_for_timeout(500)
    ok(pg.is_visible('#imp-tipo-carga') and pg.locator('input[name="imp-tipo-carga"][value="carga_inicial"]').is_checked(), 'Selector de tipo de carga visible, «Carga inicial» marcada')
    pg.locator('#imp-card').screenshot(path=f'{OUT}/r1_tarjeta.png')
    with pg.expect_download() as d: pg.click('#imp-plantilla')
    enc = open(d.value.path(), encoding='utf-8-sig').read().strip().split(',')
    ok(len(enc) == 37, 'Plantilla de 37 columnas', ', '.join(enc[21:]))
    pg.check('input[name="imp-tipo-carga"][value="carga_inicial"]')
    pg.set_input_files('#imp-archivo', os.path.join(CSV, 'imp_v2_errores.csv'))
    pg.wait_for_selector('#imp-confirmar', timeout=120000); pg.wait_for_timeout(300)
    st = [x for x in pg.locator('#imp-contenido .summary-grid .stat .num').all_inner_texts()]
    ok(st[:3] == ['31', '11', '20'] or st[:3] == ['31', '10', '21'], 'Simulación del archivo de errores (vista previa)', ' · '.join(st))
    ok('Carga inicial' in pg.inner_text('#imp-tipo-elegido'), 'La vista previa muestra el tipo de carga')
    pg.screenshot(path=f'{OUT}/r2_vista_previa_errores.png', full_page=True)
    with pg.expect_download() as d: pg.click('#imp-reporte')
    filas = list(csv.reader(open(d.value.path(), encoding='utf-8-sig')))
    ok(filas[0] == ['Fila', 'Nombre completo', 'Resultado', 'ID de empleado', 'Detalle', 'Tipo de carga'] and len(filas) == 32, 'Reporte descargable con 31 filas, resultado, detalle y tipo de carga', f'{len(filas) - 1} filas')
    open(f'{OUT}/r3_reporte.csv', 'w', encoding='utf-8').write(open(d.value.path(), encoding='utf-8-sig').read())
    pg.click('#imp-cancelar'); pg.wait_for_timeout(300)
    ok(escrituras and all(e == 'rpc confirmar=False' for e in escrituras), 'Solo hubo llamadas de simulación; nada se guardó', ', '.join(sorted(set(escrituras))))
    ok(not errs, 'Sin errores de JavaScript', '; '.join(errs)[:200])
    b.close()
print(f"\n{sum(1 for r in res if r[1])} OK · {sum(1 for r in res if not r[1])} FALLA")
