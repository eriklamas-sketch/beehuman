import sys, os, json
HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, 'ux_pruebas.py'), encoding='utf-8').read()
src = src[:src.index('with sync_playwright() as p:')]
sys.argv = [sys.argv[0], HTML, OUT, 'x']; exec(src)
with sync_playwright() as p:
    b = p.chromium.launch()
    for quien, ancho, alto in [('admin', 1440, 950), ('admin', 390, 844), ('consulta', 1440, 950), ('nomina', 1440, 950)]:
        ctx, pg = abrir(b, quien, ancho, alto); pg.wait_for_timeout(800)
        filas = pg.locator('.comparativo-fila').all_inner_texts()
        det = pg.inner_text('.comparativo-detalle')
        pg.locator('#comparativo-empresas-card').screenshot(path=f'{OUT}/{quien}-{ancho}-1.png')
        if len(filas) > 1:
            pg.locator('.comparativo-fila').nth(1).click(); pg.wait_for_timeout(200)
            det2 = pg.inner_text('.comparativo-detalle')
            pg.locator('#comparativo-empresas-card').screenshot(path=f'{OUT}/{quien}-{ancho}-2.png')
        else: det2 = ''
        print(quien, ancho, '| filas:', [f.replace('\n', ' ') for f in filas], '| detalle:', det.replace('\n', ' / '), '| al elegir 2ª:', det2.replace('\n', ' / '),
              '| ancho:', pg.evaluate('document.documentElement.scrollWidth'), '| errores:', pg.errores[:2])
        ctx.close()
    b.close()
