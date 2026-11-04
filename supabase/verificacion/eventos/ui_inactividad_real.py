"""Prueba cronometrada con los tiempos REALES (30 min, aviso a los 28). Base LOCAL.
Sesión A: nadie responde. Sesión B: «Seguir trabajando» al aparecer el aviso.
Uso: python3 ui_inactividad_real.py <index.html> <carpeta_capturas>"""
import sys, os, json, time
HTML, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, 'ui_sesion.py'), encoding='utf-8').read()
exec(src[:src.index('with sync_playwright() as p:')])

def t(): return time.strftime('%H:%M:%S')
def mmss(s): return f'{int(s // 60)}:{int(s % 60):02d}'
with sync_playwright() as p:
    b = p.chromium.launch()
    ca, A = abrir(b, 'nomina'); esperar_app(A)
    cb, B = abrir(b, 'admin'); esperar_app(B)
    t0 = time.time(); print(t(), 'inicio: dos sesiones abiertas, sin actividad', flush=True)
    visto = {}
    while time.time() - t0 < 32 * 60:
        s = time.time() - t0
        for nombre, pg in (('A', A), ('B', B)):
            try:
                aviso = pg.is_visible('#aviso-inactividad'); login = pg.is_visible('#login-screen')
            except Exception:
                aviso, login = False, False
            if aviso and (nombre, 'aviso') not in visto:
                visto[(nombre, 'aviso')] = s; print(t(), f'{nombre}: aviso a los {mmss(s)} ({pg.text_content("#aviso-inactividad-tiempo")} restantes)', flush=True)
                pg.screenshot(path=os.path.join(OUT, f'real-{nombre}-aviso.png'))
                if nombre == 'B':
                    pg.click('#aviso-inactividad-seguir'); visto[('B', 'seguir')] = s
                    print(t(), f'B: «Seguir trabajando» a los {mmss(s)}', flush=True)
            if login and (nombre, 'login') not in visto:
                visto[(nombre, 'login')] = s; print(t(), f'{nombre}: sesión cerrada a los {mmss(s)}', flush=True)
                pg.screenshot(path=os.path.join(OUT, f'real-{nombre}-cerrada.png'))
        time.sleep(5)
    sA = visto.get(('A', 'aviso')); cA = visto.get(('A', 'login'))
    ok(sA is not None and 27.9 * 60 <= sA <= 28.3 * 60, 'A: el aviso aparece a los 28 min', mmss(sA) if sA else 'no apareció')
    ok(cA is not None and 29.9 * 60 <= cA <= 30.4 * 60 and not sesion_guardada(A), 'A: sin respuesta, la sesión se cierra a los 30 min', mmss(cA) if cA else 'no cerró')
    ok('inactividad' in (A.text_content('#toast-login') or ''), 'A: el inicio de sesión explica el motivo')
    ok(('B', 'seguir') in visto and ('B', 'login') not in visto and B.is_visible('#app-content') and sesion_guardada(B),
       'B: con «Seguir trabajando» la sesión sigue abierta después de los 30 min')
    ok(not A.errores and not B.errores, 'ningún error de JavaScript', '; '.join((A.errores + B.errores)[:2]))
    b.close()
print(f"\n{sum(1 for _, c in res if c)}/{len(res)} pruebas correctas")
