"""Importación masiva v2 (26-nov-2026): pruebas I1–I10 contra la base LOCAL (Postgres + PostgREST, esquema de
beehuman-pruebas + migración 20261126000000), con la pantalla real. Datos 100 % ficticios.
Uso: python3 ui_importacion_v2.py <index.html> <carpeta_csv> <carpeta_salida>"""
import sys, os, json, time, re
HTML, CSV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
H = '/home/claude/beehuman/supabase/verificacion/ola1/ui_ola1.py'
fuente = open(H, encoding='utf-8').read(); fuente = fuente[:fuente.index('def abrir(')]
sys.argv = [sys.argv[0], HTML, OUT]; __file__ = H
exec(fuente)
V21 = '/home/claude/herramientas_prueba_bh/env/v21'
from playwright.sync_api import sync_playwright

TEN = '0a000000-0000-4000-8000-000000000001'
cargas = []          # cuerpos enviados a imp_alta_personas
control = {'abortar_confirmacion_n': None, 'n_conf': 0}
def huella():
    return sql("""select md5(string_agg(t||':'||coalesce(h,''), '|' order by t)) from (
      select 'personal' t, md5(string_agg(x::text, '' order by x.id)) h from personal x union all
      select 'relaciones', md5(string_agg(x::text, '' order by x.id)) from relaciones_laborales x union all
      select 'registros_pago', md5(string_agg(x::text, '' order by x.id)) from personal_registros_pago x union all
      select 'eventos', md5(string_agg(x::text, '' order by x.id)) from eventos_laborales x union all
      select 'idse', md5(string_agg(x::text, '' order by x.id)) from idse_movimientos x union all
      select 'asignaciones', md5(string_agg(x::text, '' order by x.id)) from inc_asignaciones x union all
      select 'secuencia_beh', (select last_value::text from personal_empleado_id_seq)) s""")
def n(q): return int(sql(q) or 0)
def conteos():
    return {'personas': n('select count(*) from personal'), 'relaciones': n("select count(*) from relaciones_laborales where estado='vigente'"),
            'esquemas': n('select count(*) from personal_registros_pago where activo'), 'idse08': n("select count(*) from idse_movimientos where tipo_movimiento='08'"),
            'ev_import': n("select count(*) from eventos_laborales where origen='importacion' and tipo='ingreso'"),
            'asignaciones': n('select count(*) from inc_asignaciones')}
def delta(a, b): return {k: b[k] - a[k] for k in a}
def esperado_csv(nombre):
    import csv
    filas = list(csv.DictReader(open(os.path.join(CSV, nombre), encoding='utf-8-sig')))
    esq = sum(1 for f in filas for k in ('Forma de pago 1', 'Forma de pago 2') if f.get(k))
    return len(filas), esq, sum(1 for f in filas if f.get('Coordinador')), sum(1 for f in filas if f.get('Registro patronal'))

def abrir(b):
    ctx = b.new_context(viewport={'width': 1440, 'height': 950}, accept_downloads=True)
    sesion = {'access_token': jwt(U['admin']), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
              'refresh_token': 'x', 'user': {'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}}
    ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});")
    base = ruta_para('admin')
    def ruta(route):
        r = route.request
        if '/rpc/imp_alta_personas' in r.url and r.method == 'POST':
            cuerpo = json.loads(r.post_data or '{}'); cargas.append(cuerpo)
            open(f'{OUT}/envios.jsonl', 'a').write(json.dumps({'etapa': control.get('etapa'), 'cuerpo': cuerpo}, ensure_ascii=False) + '\n')
            if cuerpo.get('p_confirmar'):
                control['n_conf'] += 1
                if control['abortar_confirmacion_n'] and control['n_conf'] >= control['abortar_confirmacion_n']:
                    return route.abort('internetdisconnected')
        return base(route)
    ctx.route('**/*', ruta)
    pg = ctx.new_page(); pg.errores = []
    pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto('file://' + os.path.abspath(HTML))
    pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
    pg.click('nav.tabs button[data-tab="alta"]'); pg.wait_for_timeout(500)
    return ctx, pg

def cargar(pg, nombre, tipo='carga_inicial'):
    if pg.locator('#imp-otra').count(): pg.click('#imp-otra'); pg.wait_for_timeout(300)
    if pg.locator('#imp-cancelar').count(): pg.click('#imp-cancelar'); pg.wait_for_timeout(300)
    pg.check(f'input[name="imp-tipo-carga"][value="{tipo}"]')
    pg.set_input_files('#imp-archivo', os.path.join(CSV, nombre))
    pg.wait_for_function("document.querySelector('#imp-confirmar') || (document.querySelector('#imp-toast') && document.querySelector('#imp-toast').style.display === 'block')", timeout=180000)
    pg.wait_for_timeout(300)
def stats(pg, sel='#imp-contenido .summary-grid'):
    return [int(x.replace(',', '')) for x in pg.locator(f'{sel} .stat .num').all_inner_texts()]
def importar(pg):
    t = time.time(); pg.click('#imp-confirmar')
    pg.wait_for_selector('#imp-otra', timeout=300000); pg.wait_for_timeout(500)
    return time.time() - t
def detalle(pg):
    if not pg.locator('#imp-detalle').count(): return {}
    filas = pg.eval_on_selector_all('#imp-detalle tbody tr', "trs => trs.map(tr => [...tr.cells].map(td => td.innerText))")
    return {int(r[0]): r for r in filas}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b)
    ok(pg.locator('#imp-tipo-carga input[value="carga_inicial"]').is_checked(), 'Tipo de carga predeterminado: Carga inicial')
    control['etapa'] = 'I1'
    # ---------------- I1 simulación sin persistencia ----------------
    h0 = huella(); c0 = conteos()
    t0 = time.time(); cargar(pg, 'imp_v2_validos_450.csv'); t_sim = time.time() - t0
    h1 = huella()
    s = stats(pg)
    ok(s[:4] == [450, 450, 0, 0], 'I1 Vista previa: 450 filas, 450 se crearán, 0 con error', str(s))
    ok(h0 == h1, 'I1 Huella de datos (6 tablas + secuencia BEH) antes = después de la simulación', f'{h0[:8]} / {h1[:8]}')
    ok(all(not c['p_confirmar'] for c in cargas) and sum(len(c['p_filas']) for c in cargas) == 450, 'I1 La simulación envió 450 filas, todas con p_confirmar = false', str(len(cargas)))
    ok(pg.locator('#imp-tipo-elegido').get_attribute('data-tipo') == 'carga_inicial' and 'Carga inicial' in pg.inner_text('#imp-tipo-elegido'), 'I1 La vista previa muestra el tipo de carga elegido')
    filas_csv, esq_csv, coord_csv, rp_csv = esperado_csv('imp_v2_validos_450.csv')
    ok(s[4:] == [450, esq_csv, 0, coord_csv], 'I1 Resumen: relaciones, formas de pago, 0 altas IMSS, asignaciones', str(s[4:]))
    pg.screenshot(path=f'{OUT}/i1_vista_previa.png', full_page=False)
    control['etapa'] = 'I2'
    # ---------------- I2 carga inicial de 450 + I10 tiempo ----------------
    cargas.clear()
    t_imp = importar(pg); c1 = conteos(); d = delta(c0, c1)
    ok(d == {'personas': 450, 'relaciones': 450, 'esquemas': esq_csv, 'idse08': 0, 'ev_import': 450, 'asignaciones': coord_csv},
       'I2 Carga inicial: 450 personas, 450 relaciones vigentes, formas de pago del archivo, 0 altas 08, 450 eventos de importación, asignaciones', json.dumps(d))
    open(f'{OUT}/i2_detalle.txt','w',encoding='utf-8').write('\n'.join('\t'.join(x) for x in detalle(pg).values()))
    r = stats(pg)
    ok(r[0] == 450 and r[1] == 0 and r[2] == 0, 'I2 Resultado en pantalla: 450 creadas', str(r))
    ok(n("select count(*) from personal p where p.created_at > now() - interval '1 hour' and not exists (select 1 from relaciones_laborales r where r.personal_id = p.id) and p.empresa_id in (select id from empresas where nombre like 'IMPORTA%')") == 0,
       'I2 Ninguna persona importada sin relación laboral')
    ok(n("select count(*) from personal_registros_pago r join empresas_registros_patronales x on x.id = r.registro_patronal_id where r.relacion_laboral_id is null") == 0 and
       n("select count(*) from personal_registros_pago rp join relaciones_laborales rl on rl.id = rp.relacion_laboral_id where rp.empresa_id is distinct from rl.empresa_id") == 0,
       'I2 Cada forma de pago ligada a su relación y a la misma empresa')
    ok(n("select count(*) from personal p join personal c on c.id = p.coordinador_id where c.curp is not null and p.empresa_id in (select id from empresas where nombre like 'IMPORTA%')") == coord_csv,
       'I2 Coordinadores del mismo archivo resueltos por CURP', str(coord_csv))
    ok(n("select count(*) from personal where empleado_id like 'SIM-%'") == 0, 'I2 Ningún ID de simulación quedó guardado')
    ok(t_imp < 120 and t_sim < 120, 'I10 Tiempo: simulación y carga de 450 en menos de 2 minutos cada una', f'simulación {t_sim:.1f} s · carga {t_imp:.1f} s')
    ok(all(len(c['p_filas']) <= 50 for c in cargas), 'I2 Bloques de 50 filas como máximo', str([len(c['p_filas']) for c in cargas]))
    control['etapa'] = 'I3'
    # ---------------- I3 archivo de errores ----------------
    cA = conteos(); cargas.clear()
    cargar(pg, 'imp_v2_errores.csv')
    s = stats(pg); det = detalle(pg)
    esperados = open(os.path.join(CSV, 'imp_v2_errores_esperados.txt'), encoding='utf-8').read()
    ok(s[:3] == [31, 10, 21], 'I3 Vista previa: 31 filas, 10 se crearán, 21 con error', str(s))
    claves = {2: 'no pertenece a la empresa', 3: 'no existe', 4: 'salario mínimo', 5: 'Falta el SDI', 6: 'NSS', 7: 'CURP', 8: 'aparece en las filas', 9: 'aparece en las filas',
              10: 'ya está registrado', 11: 'no existe', 12: 'solo puede llevar uno', 13: 'periodicidad 1', 14: 'forma de pago 1', 15: 'modalidad 1', 16: 'importe 1',
              17: 'incompleta', 18: 'Fecha de ingreso', 19: 'Fecha de ingreso', 20: 'Tipo de trabajador', 21: 'UMF', 22: 'empresa'}
    malos = [l for l, k in claves.items() if l not in det or k.lower() not in det[l][3].lower()]
    ok(not malos, 'I3 Cada caso de error rechazado con su mensaje (20 casos, 21 filas)', 'sin mensaje esperado: ' + ','.join(map(str, malos)) if malos else '')
    open(f'{OUT}/i3_mensajes.txt', 'w', encoding='utf-8').write('\n'.join(f"fila {l}: {det[l][3]}" for l in sorted(det)))
    ok(any('salario mínimo' in det.get(4, ['', '', '', ''])[3] and 'Rechazada por BeeHuman' in det[4][3] for _ in [0]), 'I3 El SBC bajo el mínimo lo detecta la simulación en la base (no la pantalla)')
    importar(pg); cB = conteos(); d = delta(cA, cB)
    ok(d['personas'] == 10 and d['relaciones'] == 10 and d['idse08'] == 0, 'I3 Solo se guardan las 10 filas de control', json.dumps(d))
    ok(n("select count(*) from personal p where p.empresa_id in (select id from empresas where nombre like 'IMPORTA%') and not exists (select 1 from relaciones_laborales r where r.personal_id = p.id)") == 0,
       'I3 Ninguna persona a medias (persona sin relación)')
    control['etapa'] = 'I4'
    # ---------------- I4 reimportar el mismo archivo ----------------
    cA = conteos()
    cargar(pg, 'imp_v2_validos_450.csv')
    s = stats(pg); det = detalle(pg)
    ok(s[:3] == [450, 0, 450] and all('ya está registrado' in r[3] for r in det.values()), 'I4 Reimportar 450: 0 nuevas, 450 «ya está registrado»', str(s[:3]))
    ok(pg.locator('#imp-confirmar').is_disabled() and conteos() == cA, 'I4 No hay nada que importar y la base no cambió')
    control['etapa'] = 'I5'
    # ---------------- I5 corte de conexión a mitad + reintento ----------------
    cA = conteos(); cargas.clear()
    cargar(pg, 'imp_v2_corte_120.csv')
    control['n_conf'] = 0; control['abortar_confirmacion_n'] = 2
    importar(pg); control['abortar_confirmacion_n'] = None
    cB = conteos(); r = stats(pg, '#imp-contenido > div.summary-grid:not(#imp-resumen-resultado)')
    ok(cB['personas'] - cA['personas'] == 50 and r[0] == 50 and r[-1] == 70, 'I5 Corte en el 2.º bloque: 50 creadas y 70 pendientes, reportadas con exactitud', f'{cB["personas"] - cA["personas"]} creadas · pantalla {r}')
    cargar(pg, 'imp_v2_corte_120.csv')
    s = stats(pg)
    ok(s[:3] == [120, 70, 50], 'I5 Reintento: las 50 ya creadas se detectan como existentes; 70 por crear', str(s[:3]))
    importar(pg); cC = conteos()
    ok(cC['personas'] - cA['personas'] == 120 and n("select count(*) from (select curp from personal where curp is not null group by curp having count(*) > 1) x") == 0,
       'I5 Tras el reintento: 120 en total y ninguna CURP duplicada')
    control['etapa'] = 'I6'
    # ---------------- I6 altas nuevas ----------------
    cA = conteos()
    cargar(pg, 'imp_v2_altas_10.csv', 'altas_nuevas')
    ok(pg.locator('#imp-tipo-elegido').get_attribute('data-tipo') == 'altas_nuevas', 'I6 La vista previa muestra «Altas nuevas»')
    s = stats(pg)
    ok(s[6] == 10, 'I6 Vista previa: 10 altas IMSS (08) pendientes', str(s))
    importar(pg); d = delta(cA, conteos())
    ok(d['personas'] == 10 and d['idse08'] == 10 and n("select count(*) from idse_movimientos where tipo_movimiento='08' and estado='pendiente' and creado_en > now() - interval '5 minutes'") >= 10,
       'I6 Altas nuevas: 10 personas y 10 movimientos 08 pendientes', json.dumps(d))
    control['etapa'] = 'I7'
    # ---------------- I7 regresión: archivo de 21 columnas y proyecto opcional ----------------
    cA = conteos()
    cargar(pg, 'imp_f3_21col_5.csv')
    s = stats(pg)
    ok(s[:3] == [5, 5, 0] and s[4] == 0 and s[5] == 0, 'I7 Archivo anterior (21 columnas) válido: 5 personas, sin relación ni formas de pago', str(s))
    importar(pg); d = delta(cA, conteos())
    ok(d['personas'] == 5 and d['relaciones'] == 0 and d['esquemas'] == 0, 'I7 Se crean como antes (solo la persona)', json.dumps(d))
    ok(n("select count(*) from personal where proyecto_id is null and empresa_id = '0e100000-0000-4000-8000-000000000003'") >= 1, 'I7 Proyecto vacío se guarda vacío (sin crear ni asignar proyecto)')
    ok(n("select count(*) from proyectos") == 3, 'I7 No se creó ningún proyecto')
    ok(not pg.errores, 'Sin errores de JavaScript en la página', '; '.join(pg.errores)[:300])
    # Plantilla: 37 columnas, empieza con las 21 anteriores
    with pg.expect_download() as dl:
        if pg.locator('#imp-otra').count(): pg.click('#imp-otra'); pg.wait_for_timeout(200)
        pg.click('#imp-plantilla')
    enc = open(dl.value.path(), encoding='utf-8-sig').read().strip().split(',')
    ok(len(enc) == 37 and enc[:21][-1] == 'Fecha de vencimiento de contrato' and enc[21] == 'Fecha de ingreso', 'Plantilla con 37 columnas (21 anteriores + 16 nuevas)', str(len(enc)))
    json.dump(cargas[:1], open(f'{OUT}/ejemplo_envio.json', 'w'), ensure_ascii=False)
    b.close()

print(f"\n{sum(1 for r in res if r[1])} OK · {sum(1 for r in res if not r[1])} FALLA")
