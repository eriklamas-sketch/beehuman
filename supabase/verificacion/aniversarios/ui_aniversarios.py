import sys, os
HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
AQUI = '/tmp/claude-0/-home-claude/336c7d63-ad0b-5a5c-bdb2-4d158afd2866/scratchpad/ux'
src = open(os.path.join(AQUI, 'ux_pruebas.py'), encoding='utf-8').read()
src = src[:src.index('with sync_playwright() as p:')]
sys.argv = [sys.argv[0], HTML, OUT, 'x']; __file__ = os.path.join(AQUI, 'ux_pruebas.py'); exec(src)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'admin'); pg.wait_for_timeout(800)
    filas = pg.locator('.aniversarios-tabla tbody tr').all_inner_texts()
    print('filas:', [f.replace('\t', ' | ') for f in filas])
    print('sin fecha:', pg.locator('#resumen-revisar').inner_text().split('\n')[-1][:140])
    pg.locator('#resumen-revisar').screenshot(path=f'{OUT}/resumen-aniversarios.png')
    ir(pg, 'lista'); pg.select_option('#filtro-pendiente', 'aniversario'); pg.wait_for_timeout(300)
    print('filtro aniversario:', pg.locator('#tabla-personal tr').count(), pg.inner_text('#lista-conteo'))
    pg.select_option('#filtro-pendiente', 'sin_fecha_aniversario'); pg.wait_for_timeout(300)
    print('filtro sin fecha:', pg.locator('#tabla-personal tr').count())
    print('errores:', pg.errores[:2]); ctx.close()
    ctx, pg = abrir(b, 'admin', 390, 844); pg.wait_for_timeout(800)
    print('móvil ancho:', pg.evaluate('document.documentElement.scrollWidth')); ctx.close()
    b.close()
