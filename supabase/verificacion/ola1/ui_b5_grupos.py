"""B5 · «Prestaciones y créditos» agrupado y contraíble (17-nov-2026) · prueba de PANTALLA con datos FICTICIOS.
Cambio de presentación: no cambia reglas, estados, permisos ni la base.
  G1 Apertura: con ≤3 créditos vigentes todo abierto; con más, solo los grupos con algo por completar o activar;
     «Terminados» siempre plegado; sin categorías vacías.
  G2 Resumen: etiquetas con conteos correctos; «por completar o activar» = solo créditos incompletos (NO cuenta
     descuentos «por decidir» de Revisión); las etiquetas filtran.
  G3 Búsqueda desde 10 registros; «Mostrar más» cuando un grupo tiene más de 6 tarjetas.
  G4 Resumen económico: saldo = suma de saldos de la base; propuesto se suma solo con un mismo periodo y una misma
     periodicidad; si no, «Sin sumar».
  G5 Posición: abrir o cerrar grupos, Historia y Editar → Cancelar no mueven la vista; el formulario de edición se
     abre dentro de la tarjeta.
  G7 Saldo total de préstamos (junto al título): suma el saldo de la base de préstamos y anticipos no terminados,
     incluidos suspendidos; excluye terminados, FONACOT, INFONAVIT, pensiones y otros; $0.00 sin préstamos;
     no cambia con filtros ni búsqueda; no muestra el total de otra persona.
  G6 Celular (390 px): notas secundarias ocultas; importes, estados, vigencia y acciones visibles; acciones en una
     fila; nada se sale de la pantalla. Sin errores de JavaScript.
Base local bhui; peticiones atendidas por rest_local.py como el usuario (mismas RLS), no PostgREST real.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_b5_grupos.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL
import semilla_creditos as SC
from semilla_creditos import sql, U, NOMBRE

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']
REF = 'sflvpgkmtaxzogpgetxn'
S = SC.montar(montar_diana=True); D = S['D']
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}
peticiones = []
def b64(d): return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
def ruta(route):
    req = route.request; u = urlparse(req.url)
    if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
    if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
    if u.netloc == f'{REF}.supabase.co':
        if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
        if u.path.startswith('/auth/v1/user'): return route.fulfill(json={'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}, headers=CORS)
        if u.path.startswith('/rest/v1/'):
            tabla = u.path[len('/rest/v1/'):]; cuerpo = json.loads(req.post_data) if req.post_data else None
            peticiones.append((req.method, tabla, u.query))
            try: st, res, extra = RL.ejecutar('admin', req.method, tabla, parse_qsl(u.query, keep_blank_values=True), cuerpo, {k.lower(): v for k, v in req.headers.items()})
            except Exception as e: st, res, extra = 400, {'code': 'LOCAL', 'message': str(e)}, {}; peticiones.append(('ERROR', tabla, str(e)))
            h = dict(CORS); h.update(extra)
            if st == 204: return route.fulfill(status=204, headers=h, body='')
            return route.fulfill(status=st, headers=h, body=json.dumps(res), content_type='application/json')
        return route.fulfill(json={}, headers=CORS)
    if u.scheme in ('http', 'https'): return route.abort()
    return route.continue_()

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

def abrir_ficha(pg, quien):
    pg.click('nav.tabs button[data-tab="lista"]'); pg.wait_for_timeout(600)
    pg.fill('#buscar-personal', NOMBRE[quien]); pg.wait_for_timeout(400)
    pg.click(f'#tabla-personal a:has-text("{NOMBRE[quien]}")'); pg.wait_for_timeout(1300)
    pg.click('[data-detail-tab="prestaciones"]'); pg.wait_for_timeout(1200)
def cerrar(pg): pg.evaluate("() => { if (typeof cerrarDetalleYa === 'function') cerrarDetalleYa(); }"); pg.wait_for_timeout(400)
def grupos(pg):
    return pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#cred-lista details.cred-grupo')].map(d => [d.dataset.grupo,
      { open: d.open, head: d.querySelector('summary').innerText.replace(/\\s+/g, ' '), n: d.querySelectorAll('[data-cred]').length,
        vis: [...d.querySelectorAll('[data-cred]')].filter(e => d.open && e.getClientRects().length).map(e => e.dataset.cred) }]))""")
def chips(pg): return pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('.cred-resumen [data-filtro]')].map(b => [b.dataset.filtro, b.innerText.replace(/\\s+/g, ' ').trim()]))")
JS_SC_SET = """(v) => { const box = document.getElementById('cred-ficha');
  for (let e = box.parentElement; e; e = e.parentElement) { const o = getComputedStyle(e).overflowY; if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight) { e.scrollTop = v; return; } }
  (document.scrollingElement || document.documentElement).scrollTop = v; }"""
def top_de(pg, sel): return pg.evaluate(f"() => document.querySelector('{sel}').getBoundingClientRect().top")
def mueve(pg, sel, accion):
    antes = top_de(pg, sel); accion(); pg.wait_for_timeout(500); return abs(top_de(pg, sel) - antes)

with sync_playwright() as p:
    b = p.chromium.launch()
    def contexto(ancho, alto, escala=1):
        ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=escala)
        ses = {'access_token': b64({'alg': 'HS256'}) + '.' + b64({'sub': U['admin'], 'role': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local',
               'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x', 'user': {'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});")
        ctx.route('**/*', ruta); pg = ctx.new_page(); pg.errores = []
        pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda d: d.accept())
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
        return ctx, pg
    ctx, pg = contexto(1440, 950)
    errores = []

    print('== G1 Apertura ==')
    abrir_ficha(pg, 'BENITO'); g = grupos(pg)
    ok(set(g) == {'prestamos', 'fonacot', 'infonavit'} and all(v['open'] for v in g.values()), 'G1 3 créditos vigentes: todos los grupos abiertos y sin categorías vacías', str({k: v['open'] for k, v in g.items()}))
    errores += pg.errores; cerrar(pg)
    abrir_ficha(pg, 'DIANA'); g = grupos(pg)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/G1_dieciseis_inicio.png')
    ok(set(g) == {'prestamos', 'fonacot', 'infonavit', 'otros', 'terminados'}, 'G1 14 vigentes + 2 terminados: cinco grupos, en orden', ','.join(g))
    ok(list(g) == ['prestamos', 'fonacot', 'infonavit', 'otros', 'terminados'], 'G1 Orden: Préstamos y anticipos, FONACOT, INFONAVIT y pensiones, Otros, Terminados')
    ok(g['fonacot']['open'] and not g['prestamos']['open'] and not g['infonavit']['open'] and not g['otros']['open'], 'G1 Con más de 3: solo se abre el grupo con algo por completar o activar (FONACOT)', str({k: v['open'] for k, v in g.items()}))
    ok(not g['terminados']['open'] and g['terminados']['n'] == 2, 'G1 Terminados plegado (2)')
    ok('1 por activar' in g['fonacot']['head'] and '1 incompleto' in g['fonacot']['head'], 'G1 Encabezado FONACOT: «1 por activar» y «1 incompleto»', g['fonacot']['head'])
    ok('1 suspendido' in g['prestamos']['head'] and '7 registros' in g['prestamos']['head'], 'G1 Encabezado Préstamos y anticipos: 7 registros, «1 suspendido»', g['prestamos']['head'])
    ok('2 informativos NOI' in g['infonavit']['head'], 'G1 Encabezado INFONAVIT y pensiones: «2 informativos NOI»', g['infonavit']['head'])

    print('== G2 Resumen y filtros ==')
    c = chips(pg)
    ok(c.get('') == '16 registros' and c.get('activo') == '9 activos' and c.get('pendiente') == '2 por completar o activar' and c.get('suspendido') == '1 suspendido'
       and c.get('informativo') == '2 informativos NOI' and c.get('terminado') == '2 terminados', 'G2 Conteos del resumen', str(c))
    lineas_por_decidir = int(sql(f"select count(*) from public.cred_descuentos where personal_id = '{SC.P['DIANA']}' and origen = 'pendiente'"))
    ok(lineas_por_decidir >= 6 and c.get('pendiente') == '2 por completar o activar', f'G2 «Por completar o activar» = solo créditos incompletos; NO incluye los {lineas_por_decidir} descuentos por decidir de Revisión')
    pg.click('[data-filtro="pendiente"]'); pg.wait_for_timeout(400); g = grupos(pg)
    vis = [i for v in g.values() for i in v['vis']]
    ok(set(vis) == {D['FON-31'], D['FON-32']} and set(g) == {'fonacot'}, 'G2 Filtro «por completar o activar»: solo los 2 incompletos, en su grupo abierto', str(len(vis)))
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/G2_filtro.png')
    pg.click('[data-filtro="terminado"]'); pg.wait_for_timeout(400); g = grupos(pg)
    ok(set(g) == {'terminados'} and g['terminados']['open'] and len(g['terminados']['vis']) == 2, 'G2 Filtro «terminados»: se abre ese grupo')
    pg.click('[data-filtro=""]'); pg.wait_for_timeout(400)
    ok(set(grupos(pg)) == {'prestamos', 'fonacot', 'infonavit', 'otros', 'terminados'}, 'G2 «16 registros» quita el filtro')

    print('== G3 Búsqueda y «Mostrar más» ==')
    ok(pg.is_visible('#cred-buscar'), 'G3 Con 16 registros aparece el buscador')
    pg.fill('#cred-buscar', 'caja'); pg.wait_for_timeout(500); g = grupos(pg)
    ok(set(g) == {'otros'} and g['otros']['vis'] == [D['OTR-60']] and pg.evaluate("document.activeElement.id") == 'cred-buscar', 'G3 Buscar «caja»: solo la caja de ahorro; el cursor sigue en el buscador')
    pg.fill('#cred-buscar', ''); pg.wait_for_timeout(500)
    pg.click('details[data-grupo="prestamos"] > summary'); pg.wait_for_timeout(300); g = grupos(pg)
    ok(len(g['prestamos']['vis']) == 6 and pg.is_visible('details[data-grupo="prestamos"] [data-ver-todo]') and 'Mostrar 1 más' in pg.inner_text('details[data-grupo="prestamos"] [data-ver-todo]'),
       'G3 Préstamos (7): muestra 6 y «Mostrar 1 más»', str(len(g['prestamos']['vis'])))
    pg.click('details[data-grupo="prestamos"] [data-ver-todo]'); pg.wait_for_timeout(400)
    ok(len(grupos(pg)['prestamos']['vis']) == 7, 'G3 «Mostrar más» muestra los 7')

    print('== G4 Resumen económico ==')
    g = grupos(pg)
    saldo = float(sql(f"select sum(public.cred_saldo_actual(id)) from public.cred_creditos where personal_id = '{SC.P['DIANA']}' and tipo in ('prestamo','anticipo') and estado <> 'terminado'"))
    ok(f"${saldo:,.2f}" in g['prestamos']['head'], f'G4 Saldo pendiente del grupo = suma de saldos de la base (${saldo:,.2f})', g['prestamos']['head'])
    ok('2 periodos' in g['prestamos']['head'] and 'Sin sumar' in g['prestamos']['head'], 'G4 Préstamos con propuestas en 2 periodos: no suma el propuesto')
    ok('propuesto · 09/11/2026 – 15/11/2026 $280.00' in g['fonacot']['head'].lower(), 'G4 FONACOT: una sola propuesta del periodo → la muestra con su periodo', g['fonacot']['head'])
    ok('Periodicidades distintas' in g['otros']['head'] and '$1,100.00' not in g['otros']['head'], 'G4 Otros: mismo periodo pero periodicidad semanal y mensual → no suma', g['otros']['head'])
    ok('Informativo NOI · Sin descuento en BeeHuman' in g['infonavit']['head'] and '$' not in g['infonavit']['head'], 'G4 INFONAVIT y pensiones (solo informativos): «Informativo NOI · Sin descuento en BeeHuman», ningún importe', g['infonavit']['head'])

    print('== G5 Posición ==')
    pg.evaluate(JS_SC_SET, 0)
    pg.locator('details[data-grupo="otros"] > summary').scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    d = mueve(pg, 'details[data-grupo="otros"] > summary', lambda: pg.click('details[data-grupo="otros"] > summary'))
    ok(d < 2, 'G5 Abrir un grupo no mueve la vista', f'{d:.0f} px')
    d = mueve(pg, 'details[data-grupo="otros"] > summary', lambda: pg.click('details[data-grupo="otros"] > summary'))
    ok(d < 2, 'G5 Cerrarlo tampoco', f'{d:.0f} px')
    pg.click('details[data-grupo="otros"] > summary'); pg.wait_for_timeout(300)
    sel = f'#cred-lista [data-cred="{D["OTR-61"]}"]'
    # Primero se lleva la tarjeta a la vista (Playwright desplaza solo antes de pulsar); luego se mide.
    pg.locator(f'{sel} .cred-acciones').scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    d = mueve(pg, sel, lambda: pg.click(f'[data-cred-hist="{D["OTR-61"]}"]'))
    ok(d < 2, 'G5 Historia: la tarjeta no se mueve al repintar', f'{d:.0f} px')
    pg.click(f'[data-cred-hist="{D["OTR-61"]}"]'); pg.wait_for_timeout(300)
    d = mueve(pg, sel, lambda: pg.click(f'[data-cred-editar="{D["OTR-61"]}"]'))
    ok(pg.evaluate(f"() => !!document.querySelector('{sel} #cred-form')") and d < 40, 'G5 Editar: el formulario se abre dentro de la tarjeta, sin saltar al inicio', f'{d:.0f} px')
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/G5_editar_en_tarjeta.png')
    d = mueve(pg, sel, lambda: pg.click('#cred-cancelar'))
    ok(d < 40 and not pg.is_visible('#cred-form'), 'G5 Cancelar: se regresa a la misma tarjeta', f'{d:.0f} px')
    pg.click(f'[data-cred-editar="{D["OTR-61"]}"]'); pg.wait_for_timeout(300)
    pg.fill('#cred-notas', 'Nota de prueba'); pg.fill('#cred-motivo', 'Ajuste de prueba')
    d = mueve(pg, sel, lambda: (pg.click('#cred-guardar'), pg.wait_for_timeout(900)))
    ok(d < 40 and 'Cambio guardado' in pg.inner_text('#cred-msg') and pg.evaluate("document.querySelector('details[data-grupo=otros]').open"),
       'G5 Guardar: el grupo sigue abierto y la tarjeta en su lugar', f'{d:.0f} px')

    print('== G7 Saldo total de préstamos ==')
    NOMBRE['EDGAR'] = 'EDGAR MORALES PEÑA'; SC.P['EDGAR'] = '0a100000-0000-4000-8000-000000000015'
    def esperado(q):
        return float(sql(f"""select coalesce(sum(public.cred_saldo_actual(id)), 0) from public.cred_creditos
                          where personal_id = '{SC.P[q]}' and tipo in ('prestamo','anticipo') and estado <> 'terminado'"""))
    def indicador(pg):
        return pg.evaluate("""() => { const el = document.getElementById('cred-saldo-total'); if (!el) return null;
          const h = el.closest('h3'); const chips = document.querySelector('.cred-resumen');
          return { total: el.dataset.total, txt: el.innerText.replace(/\\s+/g, ' '), en_titulo: !!h && h.textContent.includes('Prestaciones y créditos'),
                   derecha: el.getBoundingClientRect().left > h.firstChild.parentElement.getBoundingClientRect().left + 150,
                   antes_chips: !chips || el.getBoundingClientRect().bottom <= chips.getBoundingClientRect().top + 1 }; }""")
    i = indicador(pg)   # DIANA sigue abierta
    e = esperado('DIANA')
    pg.locator('section[data-detail-section="prestaciones"]').screenshot(path=f'{OUT}/G7_saldo_total.png')
    ok(i and float(i['total']) == e and f'${e:,.2f}' in i['txt'], f'G7 DIANA: total = saldo de la base de préstamos y anticipos no terminados (${e:,.2f})', i and i['txt'])
    ok(i and '6 préstamos activos · 1 suspendido' in i['txt'], 'G7 DIANA: referencia «6 préstamos activos · 1 suspendido» (terminados excluidos)', i and i['txt'])
    term = float(sql(f"select coalesce(sum(public.cred_saldo_actual(id)), 0) from public.cred_creditos where personal_id = '{SC.P['DIANA']}' and tipo in ('prestamo','anticipo') and estado = 'terminado'"))
    ok(term > 0 and float(i['total']) == e, f'G7 El préstamo terminado con saldo (${term:,.2f}) no se suma')
    ok(i and i['en_titulo'] and i['antes_chips'], 'G7 Va en el renglón del título y antes de las etiquetas de registros')
    pg.click('[data-filtro="pendiente"]'); pg.wait_for_timeout(300)
    ok(float(indicador(pg)['total']) == e, 'G7 Con un filtro activo, el total no cambia')
    pg.click('[data-filtro=""]'); pg.wait_for_timeout(300); cerrar(pg)
    for q, esp_txt, n in [('ADELA', 'Sin préstamos vigentes', 'solo FONACOT'), ('BENITO', '1 préstamo activo', 'préstamo activo; INFONAVIT y FONACOT excluidos'),
                          ('CESAR', '1 suspendido', 'préstamo suspendido incluido; anticipo terminado excluido'), ('EDGAR', 'Sin préstamos vigentes', 'sin créditos')]:
        abrir_ficha(pg, q); i = indicador(pg); e = esperado(q)
        ok(i and float(i['total']) == e and f'${e:,.2f}' in i['txt'] and esp_txt in i['txt'], f'G7 {q} ({n}): ${e:,.2f} · «{esp_txt}»', i and i['txt'])
        cerrar(pg)
    errores += pg.errores; ctx.close()

    print('== G6 Celular ==')
    ctx, pg = contexto(390, 844, 2)
    abrir_ficha(pg, 'DIANA'); pg.click('details[data-grupo="prestamos"] > summary'); pg.wait_for_timeout(400)
    pg.locator('#cred-ficha').screenshot(path=f'{OUT}/G6_celular.png')
    info = pg.evaluate("""() => { const c = document.querySelector('details[data-grupo="prestamos"] [data-cred]');
      const vis = s => [...c.querySelectorAll(s)].some(e => e.getClientRects().length && getComputedStyle(e).display !== 'none');
      const tops = [...c.querySelectorAll('.cred-acciones button')].map(b => Math.round(b.getBoundingClientRect().top));
      return { sec: [...document.querySelectorAll('#cred-lista .cred-m-n.sec')].every(e => getComputedStyle(e).display === 'none'),
               importes: vis('[data-configurado] b') && vis('[data-propuesto] b') && vis('[data-saldo] b'), estado: vis('.cred-est'),
               vigencia: c.innerText.includes('Vigencia'), filas_acciones: new Set(tops).size, n_acciones: tops.length,
               desborde: [...document.querySelectorAll('#cred-ficha *')].filter(e => e.getClientRects().length && e.getBoundingClientRect().right > innerWidth + 1).length }; }""")
    ok(info['sec'], 'G6 Notas secundarias ocultas en celular')
    ok(info['importes'] and info['estado'] and info['vigencia'], 'G6 Importes, estado y vigencia visibles')
    ok(info['n_acciones'] == 4 and info['filas_acciones'] == 1, 'G6 Acciones visibles y en una sola fila', str(info))
    ok(info['desborde'] == 0, 'G6 Nada se sale de la pantalla (390 px)', str(info['desborde']))
    errores += pg.errores; ctx.close(); b.close()

ok(not errores, 'Sin errores de JavaScript', str(errores[:2]))
ok(not [x for x in peticiones if x[0] == 'ERROR'], 'Todas las peticiones atendidas por el traductor local', str([x for x in peticiones if x[0] == 'ERROR'][:2]))
total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
sys.exit(1 if malos else 0)
