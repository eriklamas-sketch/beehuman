"""Ingreso / reingreso en un solo formulario (fase A, 11-nov-2026), probado desde la interfaz
como usuario de RH (rol Nómina): alta sin duplicar identidades, BeeHuman decide el tipo,
formas de pago dentro del flujo, estatus, Compensación, bajas, fechas e IDSE.
Base LOCAL bhui (montar_ui_eventos.sh + migraciones pendientes + semilla_reingreso.sql),
datos sintéticos. Nunca toca Supabase.
Uso: python3 ui_reingreso.py <index.html> <carpeta_capturas>"""
import sys, os, json, subprocess
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, 'ui_eventos.py'), encoding='utf-8').read()
exec(src[:src.index('with sync_playwright() as p:')])

PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui']
def q(s):
    r = subprocess.run(PSQL, input=s, capture_output=True, text=True)
    if 'ERROR' in r.stderr: sys.exit(r.stderr)
    return r.stdout.strip()
q(open(os.path.join(AQUI, 'semilla_reingreso.sql'), encoding='utf-8').read())

ALTI, CUMBRE = '0c000000-0000-4000-8000-000000000001', '0c000000-0000-4000-8000-000000000002'
RP1, RP2 = '0f900000-0000-4000-8000-000000000001', '0f900000-0000-4000-8000-000000000002'
PID = {'RAMIRO': '0a200000-0000-4000-8000-000000000001', 'SOFIA': '0a200000-0000-4000-8000-000000000002',
       'TOMAS': '0a200000-0000-4000-8000-000000000003', 'ULISES': '0a200000-0000-4000-8000-000000000004',
       'DIANA': '0a100000-0000-4000-8000-000000000014', 'BENITO': '0a100000-0000-4000-8000-000000000012', 'MARTA': '0a200000-0000-4000-8000-000000000005'}
_ficha = ficha
def ficha(pg, nombre, seccion='historia'):
    # incluye personas con estatus Baja (el filtro de la lista arranca en Activo)
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(300)
    if pg.query_selector('#hl-aviso-imss'): pg.click('#hl-aviso-imss [data-av="cerrar"]'); pg.wait_for_timeout(300)
    ir(pg, 'lista'); pg.select_option('#filtro-estatus', ''); pg.wait_for_timeout(300)
    _ficha(pg, nombre, seccion)
txt = lambda pg, sel: (pg.text_content(sel) or '').strip() if pg.query_selector(sel) else ''
# «Huella» de todo lo que ya existía de una persona: relaciones, eventos, movimientos IDSE y esquemas.
def huella(pid):
    return q(f"""select md5(concat_ws('|',
      (select string_agg(to_jsonb(r)::text, '' order by id) from relaciones_laborales r where personal_id = '{pid}'),
      (select string_agg(to_jsonb(e)::text, '' order by id) from eventos_laborales e where personal_id = '{pid}'),
      (select string_agg(to_jsonb(m)::text, '' order by id) from idse_movimientos m where relacion_laboral_id in (select id from relaciones_laborales where personal_id = '{pid}')),
      (select string_agg(to_jsonb(x)::text, '' order by id) from personal_registros_pago x where personal_id = '{pid}')))""")
def huella_ids(tabla, ids):
    return q(f"select md5(string_agg(to_jsonb(x)::text, '' order by id)) from {tabla} x where id::text = any(string_to_array('{','.join(ids)}', ','))")
lista = lambda s: [x for x in q(s).split('\n') if x]
habilitado = lambda pg, f: not pg.is_disabled(f + ' button[type=submit]')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'nomina')
    rpc = []
    pg.on('request', lambda r: rpc.append(r.url.split('/rpc/')[-1].split('?')[0]) if '/rpc/laboral_' in r.url else None)
    pg.on('dialog', lambda d: d.accept())

    # ------------------------------------------------------------------
    print('--- 6. Alta de personal con identificadores existentes: nunca se crea otra persona ni se elige un expediente al azar')
    ID3 = "'" + "','".join([PID['RAMIRO'], PID['SOFIA'], PID['TOMAS']]) + "'"
    huella_personas = lambda: q(f"select md5(string_agg(to_jsonb(p)::text, '' order by id)) from personal p where id in ({ID3})")
    H_PERS = huella_personas()
    n_antes = q("select count(*) from personal")
    ir(pg, 'alta')
    def alta_con(curp='', rfc='', nss='', nombre=('PRUEBA', 'IDENTIDAD', 'SINTETICA')):
        pg.fill('#f-nombres', nombre[0]); pg.fill('#f-apellido1', nombre[1]); pg.fill('#f-apellido2', nombre[2])
        pg.fill('#f-curp', curp); pg.fill('#f-rfc', rfc); pg.fill('#f-nss', nss)
        pg.click('#btn-alta'); pg.wait_for_timeout(1800)
        return txt(pg, '#toast-alta')
    # Conflicto: CURP de RAMIRO y RFC de SOFIA
    t = alta_con('RESR880808HDFYTM01', 'TELS910412CD2')
    items = pg.eval_on_selector_all('#toast-alta [data-exp-conflicto]', 'ls => ls.map(l => [l.dataset.expConflicto, l.innerText])')
    ok('apuntan a expedientes distintos' in t and [i[0] for i in items] == [PID['RAMIRO'], PID['SOFIA']]
       and 'BEH-001001 · RAMIRO REYES SOTO' in items[0][1] and 'coincide CURP' in items[0][1] and 'BEH-001002 · SOFIA TREJO LUNA' in items[1][1] and 'coincide RFC' in items[1][1]
       and not pg.query_selector('#btn-alta-abrir-existente') and not pg.is_visible('#modal-overlay') and q("select count(*) from personal") == n_antes,
       'C1 CURP de una persona y RFC de otra: bloquea, lista ambos expedientes con su coincidencia y no ofrece abrir ninguno', t[:220])
    foto(pg, 'r00a-alta-conflicto-curp-rfc')
    # Conflicto con tres personas: CURP de RAMIRO, RFC de SOFIA y NSS de TOMAS
    t = alta_con('RESR880808HDFYTM01', 'TELS910412CD2', '66666666660')
    items = pg.eval_on_selector_all('#toast-alta [data-exp-conflicto]', 'ls => ls.map(l => [l.dataset.expConflicto, l.innerText])')
    ok([i[0] for i in items] == [PID['RAMIRO'], PID['SOFIA'], PID['TOMAS']] and 'coincide NSS' in items[2][1]
       and not pg.query_selector('#btn-alta-abrir-existente') and q("select count(*) from personal") == n_antes,
       'C2 tres personas con coincidencias distintas: bloquea y lista las tres; no se elige ninguna', ' | '.join(i[1] for i in items))
    foto(pg, 'r00b-alta-conflicto-tres-personas')
    # Una sola coincidencia, por NSS (TOMAS)
    t = alta_con('', '', '66666666660')
    ok('No se creó otra persona' in t and 'BEH-001003 · TOMAS UGALDE VARGAS' in t and 'misma NSS' in t and pg.query_selector('#btn-alta-abrir-existente')
       and q("select count(*) from personal") == n_antes,
       'C3 una sola coincidencia por NSS: identifica ese expediente y permite abrirlo', t[:160])
    # Una persona, CURP de ella pero RFC distinto al de su expediente: se abre la misma persona y se avisa la diferencia
    t = alta_con('RESR880808HDFYTM01', 'RESR880808ZZ9')
    ok('BEH-001001' in t and 'misma CURP' in t and 'el RFC capturado (RESR880808ZZ9) es distinto al del expediente (RESR880808AB1)' in t and pg.query_selector('#btn-alta-abrir-existente'),
       'C4 si un identificador capturado difiere del expediente encontrado (sin apuntar a otra persona), se avisa la diferencia', t[:220])
    # Error al consultar la identidad (simulado): el alta se bloquea y no se crea ninguna ficha.
    posts = []
    pg.on('request', lambda r: posts.append(r.url) if r.method == 'POST' and '/rest/v1/personal' in r.url else None)
    def falla_consulta(route):
        if route.request.method == 'GET' and 'or=' in route.request.url:
            route.fulfill(status=503, content_type='application/json', body=json.dumps({'message': 'Servicio no disponible (simulado)'}))
        else:
            route.fallback()
    pg.route('**/rest/v1/personal?*', falla_consulta)
    n0 = q("select count(*) from personal")
    t = alta_con('ZAZZ990101HDFXXX09', 'ZAZZ990101AB1', '99999999990', ('ERROR', 'DE', 'CONSULTA'))
    pg.unroute('**/rest/v1/personal?*', falla_consulta)
    ok('no se pudo verificar' in t and not posts and q("select count(*) from personal") == n0 and not pg.query_selector('#btn-alta-abrir-existente')
       and q("select count(*) from personal where curp = 'ZAZZ990101HDFXXX09'") == '0',
       'C7 si falla la consulta de identidad, el alta se bloquea: no se envía ninguna ficha ni se crea nada', t[:150])
    foto(pg, 'r00c-alta-error-consulta')
    # Dos expedientes ya existentes con la MISMA CURP (duplicado previo): no se elige ninguno.
    q("""select set_config('request.jwt.claims', '{"sub":"0b000000-0000-4000-8000-000000000001","role":"authenticated"}', false);
      insert into personal (id, tenant_id, nombres, primer_apellido, nombre_completo, curp, estatus) values
      ('0a300000-0000-4000-8000-000000000001', '0a000000-0000-4000-8000-000000000001', 'XIMENA', 'DUPLICADA', 'XIMENA DUPLICADA', 'DUPL800101HDFPLC01', 'Baja'),
      ('0a300000-0000-4000-8000-000000000002', '0a000000-0000-4000-8000-000000000001', 'XIMENA', 'DUPLICADA DOS', 'XIMENA DUPLICADA DOS', 'DUPL800101HDFPLC01', 'Baja')""")
    H_DUP = q("select md5(string_agg(to_jsonb(p)::text, '' order by id)) from personal p where curp = 'DUPL800101HDFPLC01'")
    n0 = q("select count(*) from personal")
    t = alta_con('DUPL800101HDFPLC01', '', '', ('XIMENA', 'DUPLICADA', ''))
    items = pg.eval_on_selector_all('#toast-alta [data-exp-conflicto]', 'ls => ls.map(l => [l.dataset.expConflicto, l.innerText])')
    ok('apuntan a expedientes distintos' in t and sorted(i[0] for i in items) == ['0a300000-0000-4000-8000-000000000001', '0a300000-0000-4000-8000-000000000002']
       and all('coincide CURP' in i[1] for i in items) and not pg.query_selector('#btn-alta-abrir-existente') and not pg.is_visible('#modal-overlay')
       and q("select count(*) from personal") == n0 and q("select md5(string_agg(to_jsonb(p)::text, '' order by id)) from personal p where curp = 'DUPL800101HDFPLC01'") == H_DUP,
       'C8 dos expedientes con la misma CURP: bloquea, lista los dos y no selecciona ninguno; no crea ni modifica fichas', ' | '.join(i[1] for i in items))
    foto(pg, 'r00d-alta-dos-expedientes-misma-curp')
    # CURP, RFC y NSS de la misma persona (RAMIRO)
    n_antes = q("select count(*) from personal")  # C8 agregó dos fichas sintéticas duplicadas
    t = alta_con('RESR880808HDFYTM01', 'RESR880808AB1', '44444444440', ('RAMIRO', 'REYES', 'SOTO'))
    ok('No se creó otra persona' in t and 'BEH-001001 · RAMIRO REYES SOTO' in t and 'misma CURP, RFC, NSS' in t and 'distinto' not in t
       and pg.query_selector('#btn-alta-abrir-existente') and not pg.query_selector('#toast-alta [data-exp-conflicto]') and q("select count(*) from personal") == n_antes,
       'A1 CURP, RFC y NSS de la misma persona: un solo expediente (BEH-001001), se ofrece abrirlo', t[:170])
    ok(huella_personas() == H_PERS, 'C5 ninguno de los expedientes encontrados se modificó')
    foto(pg, 'r01-alta-curp-existente')
    pg.click('#btn-alta-abrir-existente'); pg.wait_for_timeout(2200)
    f = '#hl-form-ingreso form'
    ok(pg.is_visible('#modal-overlay') and pg.is_visible(f) and 'Registrar reingreso' in txt(pg, f) and 'Expediente existente' in txt(pg, '#rl-msg'),
       'A2 «Abrir expediente para registrar el reingreso» abre la ficha existente directamente en el reingreso', txt(pg, '#rl-msg')[:120])

    ok('Reingreso a CONSTRUCTORA ALTIPLANO DEMO' in txt(pg, f + ' .ing-tipo') and pg.eval_on_selector(f + ' button[type=submit]', 'b => b.textContent') == 'Registrar reingreso',
       'A3 en el expediente encontrado, BeeHuman ya identifica el reingreso a la empresa anterior', txt(pg, f + ' .ing-tipo')[:120])

    # Formas de pago: una fila por esquema (sección 4)
    IMSS, EFEC, TRANS, HONO = ('0f000000-0000-4000-8000-00000000000%d' % i for i in (1, 2, 3, 4))
    SEM, MEN = '0e000000-0000-4000-8000-000000000007', '0e000000-0000-4000-8000-000000000030'
    def fila(i, cl, per, mod, sueldo):
        base = f'{f} .esq-filas > .esq-fila:nth-child({i})'
        if not pg.query_selector(base): pg.click(f + ' [data-esq-agregar]'); pg.wait_for_timeout(150)
        pg.select_option(base + ' [data-esq=cl]', cl); pg.select_option(base + ' [data-esq=per]', per)
        pg.select_option(base + ' [data-esq=mod]', mod); pg.fill(base + ' [data-esq=sueldo]', sueldo); pg.dispatch_event(base + ' [data-esq=sueldo]', 'input')
    def fecha(v): pg.fill(f + ' [name=fecha]', v); pg.dispatch_event(f + ' [name=fecha]', 'change')
    errores = lambda: pg.eval_on_selector_all(f + ' .ing-err li', 'ls => ls.map(l => l.innerText)')
    en_vista = lambda sel: pg.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight; }", sel)
    def registrar(espera=3000):
        rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(espera)
    sin_null = lambda: pg.evaluate("""() => [...document.querySelectorAll('#hl-form-ingreso input, #hl-form-ingreso select')]
        .every(e => (e.value || '') !== 'null' && (e.placeholder || '') !== 'null')""")

    # ------------------------------------------------------------------
    print('--- R1. RAMIRO: Compensación bloqueada sin relación vigente; atajo desde Estatus; reingreso misma empresa con IMSS + efectivo')
    H_RAMIRO = huella(PID['RAMIRO'])
    REL_VIEJA = q(f"select id from relaciones_laborales where personal_id = '{PID['RAMIRO']}'")
    ESQ_VIEJO = q(f"select id from personal_registros_pago where personal_id = '{PID['RAMIRO']}'")
    H_REL_VIEJA = huella_ids('relaciones_laborales', [REL_VIEJA])
    EVS_VIEJOS = lista(f"select id from eventos_laborales where relacion_laboral_id = '{REL_VIEJA}'")
    MOVS_VIEJOS = lista(f"select id from idse_movimientos where relacion_laboral_id = '{REL_VIEJA}'")
    H_EVS, H_MOVS = huella_ids('eventos_laborales', EVS_VIEJOS), huella_ids('idse_movimientos', MOVS_VIEJOS)
    ficha(pg, 'RAMIRO REYES SOTO', 'compensacion')
    pg.evaluate('abrirFormRegistroPago()'); pg.wait_for_timeout(400)
    ok(not pg.is_visible('#rp-form') and 'no tiene una relación laboral vigente' in txt(pg, '#toast-registros-pago'),
       'S1 sin relación vigente, Compensación no agrega esquemas y dice que se registra el ingreso o reingreso', txt(pg, '#toast-registros-pago')[:120])
    opc = pg.eval_on_selector_all('#d-estatus option', 'os => os.map(o => [o.value, o.disabled])')
    ok(not pg.is_disabled('#d-estatus') and ['__ingreso', False] in opc and ['Activo', True] in opc,
       'S2 en Baja, el menú Estatus ofrece «Registrar ingreso / reingreso…» (Activo no se elige a mano)', str(opc))
    pg.select_option('#d-estatus', '__ingreso'); pg.wait_for_timeout(700)
    ok(pg.is_visible(f) and pg.input_value('#d-estatus') == 'Baja' and pg.is_visible('[data-detail-section="laboral"]') if pg.query_selector('[data-detail-section="laboral"]') else pg.is_visible(f),
       'S3 el atajo abre el registro en Relación laboral; el estatus no cambia hasta registrar', pg.input_value('#d-estatus'))
    ok(pg.is_visible('#hl-btn-ingreso') and 'Registrar ingreso / reingreso' in txt(pg, '#hl-btn-ingreso') and not pg.query_selector('#hl-btn-reingreso'),
       'U1 un solo botón: «Registrar ingreso / reingreso»')
    emps = pg.eval_on_selector_all(f + ' [name=empresa] option', 'os => os.map(o => o.text)')
    ok(emps == ['Elige…', 'CONSTRUCTORA ALTIPLANO DEMO', 'SERVICIOS CUMBRE DEMO'], 'U2 ofrece todas las empresas activas del tenant, no solo donde trabajó', str(emps))
    ok('Reingreso a CONSTRUCTORA ALTIPLANO DEMO' in txt(pg, f + ' .ing-tipo') and '01/02/2022' in txt(pg, f + ' .ing-tipo') and '31/05/2025' in txt(pg, f + ' .ing-tipo'),
       'U3 BeeHuman determina que es reingreso (trabajó ahí del 01/02/2022 al 31/05/2025)', txt(pg, f + ' .ing-tipo')[:150])
    ok(pg.eval_on_selector_all(f + ' [name=rp] option', 'os => os.map(o => o.text)') == ['Sin registro patronal (sin IDSE)', 'Y1234567101', 'Y1234567102']
       and pg.eval_on_selector(f + ' [name=rp]', 's => s.options[s.selectedIndex].text') == 'Y1234567101',
       'U4 registro patronal según la empresa (con «Sin registro patronal»); propone el de la relación anterior')
    ok('RESR880808HDFYTM01' in txt(pg, f) and 'F-778812' in txt(pg, f) and 'LUCIA SOTO' in txt(pg, f) and not pg.query_selector(f + ' [name=confirma_expediente]'),
       'U5 recupera el expediente (CURP, FONACOT, contacto) sin volver a capturarlo y sin casilla obligatoria')
    ok(pg.input_value(f + ' [name=sdi]') == '' and pg.input_value(f + ' [name=umf]') == '' and len(pg.query_selector_all(f + ' .esq-fila')) == 1
       and pg.input_value(f + ' .esq-fila [data-esq=sueldo]') == '' and sin_null(),
       'U6 condiciones y forma de pago empiezan vacías (no se copian las anteriores) y ningún campo dice «null»')
    pg.select_option(f + ' [name=empresa]', CUMBRE); pg.wait_for_timeout(300)
    ok(pg.eval_on_selector_all(f + ' [name=rp] option', 'os => os.map(o => o.text)') == ['Sin registro patronal (sin IDSE)'] and 'Ingreso nuevo a SERVICIOS CUMBRE' in txt(pg, f + ' .ing-tipo')
       and not pg.is_visible(f + ' [name=sdi]'),
       'U7 al cambiar de empresa cambia la lista de RP y el tipo (ingreso nuevo); sin RP no se piden datos IMSS')
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(300)
    ok(pg.is_visible(f + ' [name=sdi]') and pg.eval_on_selector(f + ' button[type=submit]', 'b => b.textContent') == 'Registrar reingreso' and habilitado(pg, f),
       'U8 de vuelta en ALTIPLANO con RP: pide los datos IMSS; el botón dice «Registrar reingreso» y está habilitado')
    foto(pg, 'r02-formulario-unico-reingreso')
    # Falta información: todo junto al botón, con su sección
    fecha('2025-05-20')
    fila(1, IMSS, '', '', '')
    registrar(900)
    errs = errores()
    ok('laboral_registrar_ingreso' not in rpc and any('posterior a la baja anterior' in e and '31/05/2025' in e for e in errs) and any('SDI' in e and 'sección 3' in e for e in errs)
       and any('periodicidad de la forma de pago 1' in e for e in errs) and any('importe de la forma de pago 1' in e for e in errs) and en_vista(f + ' .ing-err'),
       'E1 si falta algo, junto al botón aparece la lista exacta (fecha posterior a la baja, SDI, periodicidad, importe) con su sección, a la vista; no se envía nada', ' | '.join(errs)[:400])
    ok(pg.query_selector(f + ' [name=sdi].hl-falta') is not None and pg.query_selector(f + ' .esq-fila [data-esq=per].hl-falta') is not None,
       'E2 los campos que faltan quedan marcados')
    foto(pg, 'r03-faltantes-junto-al-boton')
    # Datos personales: se actualizan en su sección y TODO lo capturado se conserva
    fecha('2026-11-02')
    pg.fill(f + ' [name=sdi]', '520'); pg.dispatch_event(f + ' [name=sdi]', 'input')
    fila(1, IMSS, MEN, 'neto', '18000'); fila(2, EFEC, SEM, 'neto', '1500')
    pg.click(f + ' [data-ir-seccion="contacto"]'); pg.wait_for_timeout(400)
    pg.fill('#d-emerg-telefono', '5559998888')
    pg.click('#btn-guardar-detalle'); pg.wait_for_timeout(2500)
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(600)
    filas_v = pg.eval_on_selector_all(f + ' .esq-fila', 'fs => fs.map(x => [...x.querySelectorAll("[data-esq]")].map(e => e.value).join("|"))')
    ok(pg.is_visible(f) and pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == '2026-11-02' and pg.input_value(f + ' [name=sdi]').replace(',', '') in ('520', '520.00')
       and filas_v == [f'{IMSS}|{MEN}|neto|18,000', f'{EFEC}|{SEM}|neto|1,500'] and '5559998888' in txt(pg, f)
       and q(f"select contacto_emergencia_telefono from personal where id = '{PID['RAMIRO']}'") == '5559998888' and habilitado(pg, f),
       'B1 actualizar un dato personal no pierde nada: fecha, SDI y las dos formas de pago siguen; el botón sigue habilitado', str(filas_v) + ' ' + txt(pg, '#rl-msg')[:80])
    pg.click(f + ' [data-copiar-anterior]'); pg.wait_for_timeout(300)
    copiados = pg.evaluate("f => ['tt','ts','jo','umf','num'].map(n => document.querySelector(f + ' [name=' + n + ']').value)", f)
    ok(copiados == ['1', '0', '0', '015', 'R01'] and pg.query_selector(f + ' [name=umf].hl-falta') is not None and pg.input_value(f + ' [name=sdi]').replace(',', '') in ('520', '520.00'),
       'U9 «Usar las condiciones anteriores» es opcional: copia tipos, jornada, UMF y número interno (marcados); el SDI capturado no cambia', str(copiados))
    pg.fill(f + ' [name=umf]', '016'); pg.fill(f + ' [name=motivo]', 'Reingreso tras renuncia')
    foto(pg, 'r04-reingreso-imss-y-efectivo')
    registrar()
    m = txt(pg, '#rl-msg')
    ok('Reingreso registrado' in m and '02/11/2026' in m and 'pendiente' in m and 'Y1234567101' in m and 'Formas de pago registradas: IMSS · $18,000.00 neto · Mensual; EFECTIVO · $1,500.00 neto · Semanal' in m,
       'R1a reingreso registrado: dónde, fecha, 08 pendiente y las dos formas de pago', m[:300])
    foto(pg, 'r05-reingreso-registrado')
    REL_NUEVA = q(f"select id from relaciones_laborales where personal_id = '{PID['RAMIRO']}' and id <> '{REL_VIEJA}'")
    ok(q(f"select count(*) from personal where curp = 'RESR880808HDFYTM01'") == '1' and q(f"select empleado_id || '|' || estatus from personal where id = '{PID['RAMIRO']}'") == 'BEH-001001|Activo'
       and pg.input_value('#d-estatus') == 'Activo' and not pg.query_selector('#d-estatus option[value="__ingreso"]'),
       'R1b mismo expediente BEH-001001; la persona queda Activa y el atajo desaparece del menú')
    ok(q(f"select estado || '|' || fecha_ingreso || '|' || sdi || '|' || sbc || '|' || umf || '|' || numero_interno || '|' || registro_patronal_id from relaciones_laborales where id = '{REL_NUEVA}'")
       == f'vigente|2026-11-02|520.00|520.00|016|R01|{RP1}', 'R1c la relación nueva tiene sus propias condiciones (SDI 520, UMF 016)')
    ok(q(f"select tipo || '|' || estado from eventos_laborales where relacion_laboral_id = '{REL_NUEVA}' and tipo in ('ingreso','reingreso')") == 'reingreso|vigente',
       'R1d la Historia laboral lo registra como «reingreso»')
    esq = q(f"select string_agg(c.nombre || ':' || x.sueldo || ':' || x.modalidad_sueldo || ':' || coalesce(x.registro_patronal_id::text, 'sinRP') || ':' || x.fecha_inicio || ':' || x.activo, ',' order by c.nombre) from personal_registros_pago x join clasificaciones_personal c on c.id = x.clasificacion_id where x.relacion_laboral_id = '{REL_NUEVA}'")
    ok(esq == f'EFECTIVO:1500.00:neto:sinRP:2026-11-02:true,IMSS:18000.00:neto:{RP1}:2026-11-02:true',
       'R1e las dos formas de pago quedan ligadas a la relación nueva: IMSS con su RP, efectivo sin RP, desde la fecha de ingreso', esq)
    ok(huella_ids('relaciones_laborales', [REL_VIEJA]) == H_REL_VIEJA and huella_ids('eventos_laborales', EVS_VIEJOS) == H_EVS and huella_ids('idse_movimientos', MOVS_VIEJOS) == H_MOVS
       and q(f"select count(*) from eventos_laborales where relacion_laboral_id = '{REL_VIEJA}'") == str(len(EVS_VIEJOS)),
       'R1f la relación anterior, sus eventos y sus movimientos 08/02 quedan idénticos')
    ok(q(f"select activo || '|' || fecha_fin || '|' || relacion_laboral_id from personal_registros_pago where id = '{ESQ_VIEJO}'") == f'false|2025-05-31|{REL_VIEJA}',
       'R1g el esquema anterior sigue cerrado y en su relación (no se reactivó)')
    ok(q(f"select tipo_movimiento || '|' || estado || '|' || fecha_movimiento || '|' || sbc from idse_movimientos where relacion_laboral_id = '{REL_NUEVA}'") == '08|pendiente|2026-11-02|520.00',
       'R1h el reingreso con RP genera su alta (08) pendiente con fecha y SBC nuevos (uno solo)')
    pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(700)
    tarjetas = pg.eval_on_selector_all('#d-registros-pago .rp-tarjeta', 'ts => ts.map(t => t.innerText.replace(/\\s+/g, " "))')
    ok(sum(1 for t in tarjetas if 'Activo' in t and 'ingreso 02/11/2026' in t) == 2, 'R1i Compensación muestra las dos formas de pago vigentes ligadas al nuevo periodo', ' || '.join(tarjetas)[:300])
    pg.evaluate('abrirFormRegistroPago()'); pg.wait_for_timeout(400)
    ok(pg.is_visible('#rp-form'), 'S4 con la relación vigente, Compensación permite agregar otro esquema (no depende del estatus anterior)')
    pg.evaluate("document.querySelector('#btn-rp-cancelar') && document.querySelector('#btn-rp-cancelar').click()"); pg.wait_for_timeout(300)
    foto(pg, 'r06-compensacion-dos-formas')
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    if pg.query_selector('#hl-aviso-imss'): pg.click('#hl-aviso-imss [data-av="cerrar"]'); pg.wait_for_timeout(300)
    ir(pg, 'idse'); pg.wait_for_timeout(600)
    pg.select_option('#idse-rp', RP1); pg.wait_for_timeout(1200)
    ok('RAMIRO REYES SOTO' in txt(pg, '#idse-pend-08') and '02/11/2026' in txt(pg, '#idse-pend-08'), 'R1j el 08 aparece en la bandeja IDSE del RP Y1234567101', txt(pg, '#idse-pend-08')[:120])

    # ------------------------------------------------------------------
    print('--- R2. SOFIA: trabajó con IMSS en ALTIPLANO; entra a SERVICIOS CUMBRE (otra empresa, sin RP) en efectivo')
    REL_S = q(f"select id from relaciones_laborales where personal_id = '{PID['SOFIA']}'"); H_RS = huella_ids('relaciones_laborales', [REL_S])
    ESQ_S = q(f"select id from personal_registros_pago where personal_id = '{PID['SOFIA']}'")
    ficha(pg, 'SOFIA TREJO LUNA', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', CUMBRE); pg.wait_for_timeout(300)
    ok('Ingreso nuevo a SERVICIOS CUMBRE DEMO' in txt(pg, f + ' .ing-tipo') and 'Antecedentes de esta persona en el grupo' in txt(pg, f + ' .ri-ref-caja') and '10/01/2021' in txt(pg, f + ' .ri-ref-caja'),
       'R2a otra empresa del grupo: es ingreso nuevo en esa empresa, con sus antecedentes como referencia, en el mismo formulario')
    fecha('2026-11-03'); fila(1, IMSS, SEM, 'bruto', '2500')
    registrar(900)
    ok('laboral_registrar_ingreso' not in rpc and any('es de nómina IMSS: elige un registro patronal' in e for e in errores())
       and 'necesita un registro patronal' in txt(pg, f + ' .esq-fila .esq-nota'),
       'R2b una forma de pago IMSS sin registro patronal no procede: lo dice junto al botón y en la propia fila', ' | '.join(errores()))
    fila(1, EFEC, SEM, 'neto', '2500')
    ok(not any('SDI' in e for e in errores()), 'R2c sin RP no se pide SDI ni datos de afiliación')
    registrar()
    REL_S2 = q(f"select id from relaciones_laborales where personal_id = '{PID['SOFIA']}' and id <> '{REL_S}'")
    ok('Ingreso registrado' in txt(pg, '#rl-msg') and 'no genera movimiento IDSE' in txt(pg, '#rl-msg') and 'EFECTIVO · $2,500.00 neto · Semanal' in txt(pg, '#rl-msg')
       and q(f"select empresa_id || '|' || estado || '|' || coalesce(registro_patronal_id::text, 'sinRP') || '|' || coalesce(sdi::text, '-') from relaciones_laborales where id = '{REL_S2}'") == f'{CUMBRE}|vigente|sinRP|-',
       'R2d mismo expediente, relación separada en SERVICIOS CUMBRE sin RP ni SDI', txt(pg, '#rl-msg')[:150])
    ok(q(f"select count(*) from idse_movimientos where relacion_laboral_id = '{REL_S2}'") == '0' and q(f"select tipo from eventos_laborales where relacion_laboral_id = '{REL_S2}' and tipo in ('ingreso','reingreso')") == 'ingreso',
       'R2e sin registro patronal no genera movimiento IDSE; en la historia es «ingreso» (nuevo en esa empresa)')
    ok(q(f"select x.relacion_laboral_id || '|' || coalesce(x.registro_patronal_id::text,'sinRP') || '|' || x.activo from personal_registros_pago x where x.personal_id = '{PID['SOFIA']}' and x.id <> '{ESQ_S}'") == f'{REL_S2}|sinRP|true'
       and q(f"select activo::text from personal_registros_pago where id = '{ESQ_S}'") == 'false' and huella_ids('relaciones_laborales', [REL_S]) == H_RS
       and q(f"select estatus from personal where id = '{PID['SOFIA']}'") == 'Activo',
       'R2f IMSS → efectivo: el esquema IMSS anterior sigue cerrado, el de efectivo es nuevo; la relación anterior no cambia; queda Activa')
    foto(pg, 'r07-otra-empresa-efectivo')

    # ------------------------------------------------------------------
    print('--- R3. MARTA: IMSS en ALTIPLANO RP1; regresa a ALTIPLANO sin RP, pagada por transferencia')
    REL_M = q(f"select id from relaciones_laborales where personal_id = '{PID['MARTA']}'"); ESQ_M = q(f"select id from personal_registros_pago where personal_id = '{PID['MARTA']}'")
    ficha(pg, 'MARTA MARIN ROMO', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(200)
    pg.select_option(f + ' [name=rp]', ''); pg.wait_for_timeout(300)
    fecha('2026-11-04'); fila(1, HONO, MEN, 'bruto', '12000')
    registrar(900)
    ok('laboral_registrar_ingreso' not in rpc and any('HONORARIOS' in e and 'Código postal fiscal' in e and 'Datos personales' in e for e in errores()),
       'R3a honorarios exige RFC y CP fiscal del expediente: dice cuál falta y en qué sección', ' | '.join(errores()))
    fila(1, TRANS, MEN, 'neto', '12000')
    registrar()
    REL_M2 = q(f"select id from relaciones_laborales where personal_id = '{PID['MARTA']}' and id <> '{REL_M}'")
    ok('Reingreso registrado' in txt(pg, '#rl-msg') and q(f"select count(*) from idse_movimientos where relacion_laboral_id = '{REL_M2}'") == '0',
       'R3b reingreso a la misma empresa sin RP: la pantalla lo registra como reingreso a ALTIPLANO y no genera IDSE')
    # LIMITACIÓN CONOCIDA (fase B, requiere migración): la base marca «reingreso» solo con la misma empresa Y el mismo RP;
    # con otro RP (aquí: sin RP) el evento de la Historia laboral queda como «ingreso».
    ok(q(f"select tipo from eventos_laborales where relacion_laboral_id = '{REL_M2}' and tipo in ('ingreso','reingreso')") == 'ingreso',
       'R3b2 (limitación conocida, fase B) con otro RP la Historia laboral lo guarda como «ingreso», no «reingreso»')
    ok(q(f"select c.nombre || ':' || coalesce(x.registro_patronal_id::text,'sinRP') || ':' || x.activo from personal_registros_pago x join clasificaciones_personal c on c.id = x.clasificacion_id where x.relacion_laboral_id = '{REL_M2}'") == 'TRANSFERENCIA:sinRP:true'
       and q(f"select activo::text from personal_registros_pago where id = '{ESQ_M}'") == 'false',
       'R3c IMSS → transferencia: la transferencia queda en la relación nueva; el IMSS anterior sigue cerrado')

    # ------------------------------------------------------------------
    print('--- R4. Persona nueva (VALERIA, recién dada de alta sin relación): ingreso nuevo con IMSS + transferencia')
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    ir(pg, 'alta')
    pg.fill('#f-nombres', 'VALERIA'); pg.fill('#f-apellido1', 'NUEVA'); pg.fill('#f-apellido2', 'PRUEBA')
    pg.fill('#f-curp', 'NUPV950505MDFVRL09'); pg.fill('#f-rfc', 'NUPV950505AB3'); pg.fill('#f-nss', '88888888880')
    pg.click('#btn-alta'); pg.wait_for_timeout(2500)
    PV = q("select id from personal where curp = 'NUPV950505MDFVRL09'")
    ok(PV and q(f"select count(*) from relaciones_laborales where personal_id = '{PV}'") == '0', 'R4a alta sin coincidencias: persona nueva sin relaciones')
    ficha(pg, 'VALERIA NUEVA PRUEBA', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(200); pg.select_option(f + ' [name=rp]', RP2); pg.wait_for_timeout(200)
    ok('Ingreso nuevo a CONSTRUCTORA ALTIPLANO DEMO' in txt(pg, f + ' .ing-tipo'), 'R4b sin historia: ingreso nuevo')
    fecha('2026-11-05'); pg.fill(f + ' [name=sdi]', '400'); pg.dispatch_event(f + ' [name=sdi]', 'input')
    fila(1, IMSS, SEM, 'bruto', '2800'); fila(2, TRANS, SEM, 'neto', '700')
    registrar()
    RV = q(f"select id from relaciones_laborales where personal_id = '{PV}'")
    ok('Ingreso registrado' in txt(pg, '#rl-msg') and q(f"select tipo_movimiento || '|' || estado || '|' || fecha_movimiento from idse_movimientos where relacion_laboral_id = '{RV}'") == '08|pendiente|2026-11-05'
       and q(f"select string_agg(c.nombre || ':' || coalesce(x.registro_patronal_id::text,'sinRP'), ',' order by c.nombre) from personal_registros_pago x join clasificaciones_personal c on c.id = x.clasificacion_id where x.relacion_laboral_id = '{RV}'") == f'IMSS:{RP2},TRANSFERENCIA:sinRP',
       'R4c ingreso nuevo con RP2: 08 pendiente y las dos formas de pago (IMSS con RP, transferencia sin RP)')

    # ------------------------------------------------------------------
    print('--- R5. Bloqueos y relación adicional: TOMAS (vigente en ALTIPLANO RP1)')
    H_TOMAS = huella(PID['TOMAS'])
    ficha(pg, 'TOMAS UGALDE VARGAS', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(200); pg.select_option(f + ' [name=rp]', RP1); pg.wait_for_timeout(300)
    blq = txt(pg, f + ' .ing-aviso')
    ok('No se puede registrar' in blq and 'vigente' in blq and '15/01/2024' in blq and habilitado(pg, f), 'R5a misma empresa y RP con relación vigente: el aviso lo explica (el botón no queda «muerto»)', blq[:160])
    fecha('2026-11-04'); pg.fill(f + ' [name=sdi]', '420'); pg.dispatch_event(f + ' [name=sdi]', 'input')
    registrar(900)
    ok('laboral_registrar_ingreso' not in rpc and any('Ya existe una relación vigente' in e for e in errores()), 'R5b al intentarlo, junto al botón dice por qué no procede y no se envía nada', ' | '.join(errores()))
    err = pg.evaluate("""async () => { const r = await sb.rpc('laboral_registrar_ingreso', { p_personal_id: '%s', p_empresa_id: '%s', p_registro_patronal_id: '%s', p_fecha_ingreso: '2026-11-04' }); return r.error ? r.error.message : 'sin error'; }"""
                      % (PID['TOMAS'], ALTI, RP1))
    ok('ya tiene una relación vigente con esa empresa y registro patronal' in err and huella(PID['TOMAS']) == H_TOMAS, 'R5c la base también lo impide; nada de TOMAS cambió', err[:100])
    pg.select_option(f + ' [name=rp]', ''); pg.wait_for_timeout(300)
    ok('Relación adicional en CONSTRUCTORA ALTIPLANO DEMO' in txt(pg, f + ' .ing-tipo') and pg.query_selector(f + ' [name=confirma_adicional]') is not None,
       'R5d con otro RP en la misma empresa es una relación adicional y pide confirmarla')
    registrar(900)
    ok('laboral_registrar_ingreso' not in rpc and any('relación laboral adicional' in e for e in errores()), 'R5e sin la confirmación no se registra y se dice qué falta', ' | '.join(errores()))
    pg.click(f + ' [data-cancelar]')
    print('--- R6. DIANA: relación migrada vigente sin fecha (no se confunde con un reingreso)')
    ficha(pg, 'DIANA FUENTES ORTIZ', 'laboral')
    REL_DA = q(f"select id from relaciones_laborales where personal_id = '{PID['DIANA']}' and estado = 'vigente'")
    REL_DB = q(f"select id from relaciones_laborales where personal_id = '{PID['DIANA']}' and estado = 'baja'")
    H_DB = huella_ids('relaciones_laborales', [REL_DB])
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(200); pg.select_option(f + ' [name=rp]', ''); pg.wait_for_timeout(300)
    blq = txt(pg, f + ' .ing-aviso')
    ok('solo le falta su fecha de ingreso' in blq and pg.query_selector(f + ' .ing-aviso [data-ir-corregir]'), 'R6a la relación migrada sin fecha: lo explica y ofrece «Corregir datos de esa relación»', blq[:160])
    foto(pg, 'r08-migrada-sin-fecha')
    pg.click(f + ' .ing-aviso [data-ir-corregir]'); pg.wait_for_timeout(500)
    fc = f'#hl-form-{REL_DA} form'
    ok(pg.is_visible(fc) and 'Relación que se corrige: CONSTRUCTORA ALTIPLANO DEMO · sin registro patronal' in txt(pg, fc), 'R6b lleva a «Corregir datos» de esa relación')
    print('--- P2. Fechas de ingreso por relación')
    pg.fill(fc + ' [name=fecha_ingreso]', '2018-04-02'); pg.dispatch_event(fc + ' [name=fecha_ingreso]', 'change'); pg.wait_for_timeout(300)
    av = txt(pg, fc + ' .fd-caja')
    ok('02/04/2018' in av and 'CONSTRUCTORA ALTIPLANO DEMO · RP Y1234567102 (baja 30/06/2019)' in av and not habilitado(pg, fc),
       'P2a si la fecha ya existe en otra relación, el aviso dice dónde está registrada y pide confirmar (botón inactivo)', av[:200])
    foto(pg, 'r14-fecha-ya-registrada')
    pg.fill(fc + ' [name=fecha_ingreso]', '2020-01-06'); pg.dispatch_event(fc + ' [name=fecha_ingreso]', 'change'); pg.wait_for_timeout(300)
    ok(txt(pg, fc + ' .fd-caja') == '' and habilitado(pg, fc), 'P2b con una fecha que no existe en otra relación, el aviso desaparece y se puede guardar')
    pg.fill(fc + ' [name=motivo]', 'Fecha del expediente'); pg.click(fc + ' button[type=submit]'); pg.wait_for_timeout(2200)
    ok('Fecha de ingreso de la relación CONSTRUCTORA ALTIPLANO DEMO · sin registro patronal: 06/01/2020' in txt(pg, '#rl-msg')
       and q(f"select fecha_ingreso from relaciones_laborales where id = '{REL_DA}'") == '2020-01-06' and huella_ids('relaciones_laborales', [REL_DB]) == H_DB,
       'P2c la corrección actualiza esa misma relación (y lo dice); la otra relación no cambia', txt(pg, '#rl-msg')[:140])
    cards = pg.eval_on_selector_all('#rl-raiz .hl-card', 'cs => cs.map(c => c.innerText.replace(/\\s+/g, " "))')
    ok(any('Vigente' in c and '06/01/2020' in c for c in cards) and any('RP Y1234567102' in c and '02/04/2018' in c for c in cards),
       'P2d cada relación muestra su propia fecha de ingreso', ' || '.join(c[:80] for c in cards))
    foto(pg, 'r15-cada-relacion-su-fecha')
    print('--- 5c. CESAR: ingreso sin RP con su relación migrada sin fecha')
    ficha(pg, 'CESAR DELGADILLO HINOJOSA', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.select_option(f + ' [name=rp]', ''); pg.wait_for_timeout(300)
    ok('solo le falta su fecha de ingreso' in txt(pg, f + ' .ing-aviso') and pg.query_selector(f + ' .ing-aviso [data-ir-corregir]'),
       '5c sin RP con una relación migrada sin fecha: se bloquea y lleva a «Corregir datos»')
    print('--- P2e. BENITO: misma fecha en sus dos relaciones, solo con confirmación')
    ficha(pg, 'BENITO ZAVALA GALINDO', 'laboral')
    RB1 = q(f"select rl.id from relaciones_laborales rl where personal_id = '{PID['BENITO']}' and registro_patronal_id = '{RP1}'")
    RB2 = q(f"select rl.id from relaciones_laborales rl where personal_id = '{PID['BENITO']}' and registro_patronal_id = '{RP2}'")
    H_RB1 = huella_ids('relaciones_laborales', [RB1])
    pg.click(f'[data-accion="corregir"][data-rel="{RB2}"]'); pg.wait_for_timeout(400)
    fc = f'#hl-form-{RB2} form'
    pg.fill(fc + ' [name=fecha_ingreso]', '2024-08-15'); pg.dispatch_event(fc + ' [name=fecha_ingreso]', 'change'); pg.wait_for_timeout(300)
    pg.fill(fc + ' [name=motivo]', 'Inicio en RP2 el mismo día')
    ok('RP Y1234567101 (vigente)' in txt(pg, fc + ' .fd-caja') and not habilitado(pg, fc), 'P2e la fecha ya está en la relación RP Y1234567101: se identifica y exige confirmar')
    rpc.clear(); pg.eval_on_selector(fc, 'fm => { fm.querySelector("button[type=submit]").disabled = false; fm.requestSubmit(); }'); pg.wait_for_timeout(800)
    ok('laboral_corregir_datos' not in rpc and 'ya está registrada en otra relación' in txt(pg, '#rl-msg'), 'P2f sin confirmar no se guarda (aunque se fuerce el botón)', str(rpc) + ' ' + txt(pg, '#rl-msg')[:100])
    pg.check(fc + ' [name=confirma_fecha]'); pg.wait_for_timeout(200)
    pg.click(fc + ' button[type=submit]'); pg.wait_for_timeout(2200)
    ok(q(f"select fecha_ingreso from relaciones_laborales where id = '{RB2}'") == '2024-08-15' and huella_ids('relaciones_laborales', [RB1]) == H_RB1
       and 'RP Y1234567102' in txt(pg, '#rl-msg'),
       'P2g confirmado, se guarda solo en la relación RP Y1234567102; la de RP Y1234567101 queda igual', txt(pg, '#rl-msg')[:120])
    print('--- P1c. BENITO: esquema activo sin relación → la baja en la empresa no procede hasta asignarlo')
    pg.select_option('#d-estatus', 'Baja'); pg.wait_for_timeout(700)
    fb = '#hl-form-bajacab form'
    ok(pg.is_visible(fb) and 'sin relación laboral asignada' in txt(pg, fb + ' .bd-pend') and not habilitado(pg, fb),
       'P1c un esquema activo sin relación: la baja avisa que no lo desactivaría y queda inactiva hasta asignarlo', txt(pg, fb + ' .bd-pend')[:150])
    foto(pg, 'r16-baja-esquema-sin-relacion')
    pg.click(fb + ' [data-cancelar]')

    # ------------------------------------------------------------------
    print('--- P1, P3, P4, 10. ULISES: dos relaciones vigentes (RP1 y sin RP) y un solo esquema')
    ficha(pg, 'ULISES VIDAL ROJAS', 'laboral')
    U1 = q(f"select id from relaciones_laborales where personal_id = '{PID['ULISES']}' and registro_patronal_id is not null")
    U2 = q(f"select id from relaciones_laborales where personal_id = '{PID['ULISES']}' and registro_patronal_id is null")
    ESQ_U = q(f"select id from personal_registros_pago where personal_id = '{PID['ULISES']}'")
    ok('IMSS · $15,000.00 bruto · Mensual (activo)' in txt(pg, f'[data-relacion="{U1}"] .rl-esqs') and 'ninguno asociado' in txt(pg, f'[data-relacion="{U2}"] .rl-esqs'),
       'P1d con dos relaciones y un esquema, cada tarjeta dice si tiene esquema (RP1: IMSS $15,000; sin RP: ninguno)')
    foto(pg, 'r17-dos-relaciones-un-esquema')
    pg.select_option('#d-estatus', 'Baja'); pg.wait_for_timeout(700)
    lis = pg.eval_on_selector_all(fb + ' .bd-lista li', 'ls => ls.map(l => l.innerText.replace(/\\s+/g, " "))')
    li1 = next((l for l in lis if 'Y1234567101' in l), ''); li2 = next((l for l in lis if 'sin registro patronal' in l), '')
    ok('Genera la baja (02)' in li1 and 'Se desactiva: IMSS · $15,000.00 bruto · Mensual' in li1 and 'no genera movimiento IDSE' in li2 and 'no se desactiva ninguno' in li2,
       'P1e la baja explica qué relaciones termina, qué esquemas desactiva y dónde genera 02', ' || '.join(lis))
    ok('Confirmo que se terminan las 2 relaciones listadas y se desactiva el esquema de pago indicado.' in txt(pg, fb + ' .bd-confirma') and not habilitado(pg, fb),
       'P3c la confirmación es obligatoria y el botón se ve inactivo', txt(pg, fb + ' .bd-confirma'))
    pg.fill(fb + ' [name=fecha]', '2026-11-05'); pg.select_option(fb + ' [name=causa]', '2'); pg.wait_for_timeout(200)
    estilo = lambda: pg.eval_on_selector(fb + ' button[type=submit]', 'b => [b.disabled, getComputedStyle(b).opacity, getComputedStyle(b).cursor].join("|")')
    e1 = estilo(); foto(pg, 'r18-baja-boton-inactivo')
    pg.check(fb + ' [name=confirma]'); pg.wait_for_timeout(250)
    e2 = estilo(); foto(pg, 'r19-baja-boton-habilitado')
    ok(e1.startswith('true|0.42|not-allowed') and e2.startswith('false|1|'), 'P3d al marcar la casilla el botón cambia visualmente de inactivo a habilitado', f'{e1} → {e2}')
    pg.uncheck(fb + ' [name=confirma]'); pg.eval_on_selector(fb + ' button[type=submit]', 'b => b.disabled = false'); rpc.clear()
    pg.click(fb + ' button[type=submit]'); pg.wait_for_timeout(800)
    ok('laboral_registrar_baja' not in rpc and 'Confirma que se terminan las 2 relaciones' in txt(pg, '#rl-msg'),
       'P3e la validación sigue en la lógica: forzando el botón sin la casilla no se registra nada', txt(pg, '#rl-msg')[:100])
    pg.check(fb + ' [name=confirma]'); pg.wait_for_timeout(200); rpc.clear()
    pg.click(fb + ' button[type=submit]'); pg.wait_for_timeout(3000)
    ok(q(f"select string_agg(estado, ',') from relaciones_laborales where personal_id = '{PID['ULISES']}'") == 'baja,baja'
       and q(f"select activo::text from personal_registros_pago where id = '{ESQ_U}'") == 'false',
       'P1f la baja terminó las 2 relaciones y desactivó el esquema indicado')
    ok(q(f"select string_agg(tipo_movimiento || ':' || estado, ',') from idse_movimientos where relacion_laboral_id = '{U1}' and tipo_movimiento = '02'") == '02:pendiente'
       and q(f"select count(*) from idse_movimientos where relacion_laboral_id = '{U2}'") == '0',
       'P4b con RP genera su baja (02) pendiente; sin RP no genera movimiento IDSE')
    if pg.query_selector('#hl-aviso-imss'): foto(pg, 'r20-aviso-imss-tras-baja'); pg.click('#hl-aviso-imss [data-av="seguir"]'); pg.wait_for_timeout(300)
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(400)
    btn = pg.query_selector(f'[data-anular][data-rel="{U1}"]')
    ok(btn is not None and 'Baja del 05/11/2026' in (btn.text_content() or ''), '10a la baja recién registrada se puede anular (último movimiento, 02 sin presentar)')
    btn.click(); pg.wait_for_timeout(400)
    fa = f'#hl-form-{U1} form'
    pg.fill(fa + ' [name=motivo]', 'Baja capturada por error'); pg.click(fa + ' button[type=submit]'); pg.wait_for_timeout(2500)
    ok(q(f"select estado from relaciones_laborales where id = '{U1}'") == 'vigente'
       and q(f"select estado from idse_movimientos where relacion_laboral_id = '{U1}' and tipo_movimiento = '02'") == 'cancelado'
       and q(f"select estado from eventos_laborales where relacion_laboral_id = '{U1}' and tipo = 'baja'") == 'anulado'
       and q(f"select estatus from personal where id = '{PID['ULISES']}'") == 'Activo',
       '10b anular la baja: la relación vuelve a vigente, su 02 se cancela, el evento queda anulado y la persona vuelve a Activo')
    ok(q(f"select activo::text from personal_registros_pago where id = '{ESQ_U}'") == 'true',
       '10c al anular la baja, el esquema que esa baja desactivó vuelve a estar activo', q(f"select activo || '|' || coalesce(fecha_fin::text,'-') from personal_registros_pago where id = '{ESQ_U}'"))
    foto(pg, 'r21-baja-anulada')

    ok(not pg.errores, 'sin errores de JavaScript (Nómina)', '; '.join(pg.errores)[:300])
    ctx.close()
    # Móvil: el formulario de reingreso no desborda
    ctx, pg = abrir(b, 'nomina', 390, 844)
    ficha(pg, 'RAMIRO REYES SOTO', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(500)
    pg.select_option('#hl-form-ingreso form [name=empresa]', CUMBRE); pg.wait_for_timeout(300)
    pg.click('#hl-form-ingreso form [data-esq-agregar]'); pg.wait_for_timeout(200)
    ok(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'M1 en móvil el formulario (con dos formas de pago) no desborda la pantalla')
    foto(pg, 'r22-reingreso-movil')
    ok(not pg.errores, 'sin errores de JavaScript (móvil)', '; '.join(pg.errores)[:200])
    ctx.close(); b.close()

n_ok = sum(1 for _, c in res if c)
print(f'\n{n_ok}/{len(res)} pruebas OK')
sys.exit(0 if n_ok == len(res) else 1)
