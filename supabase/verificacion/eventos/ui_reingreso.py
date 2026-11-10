"""Reingreso de personal reutilizando expediente (10-nov-2026), probado desde la interfaz
como usuario de RH (rol Nómina), más las comprobaciones de baja, fechas e IDSE.
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
       'DIANA': '0a100000-0000-4000-8000-000000000014', 'BENITO': '0a100000-0000-4000-8000-000000000012'}
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

    # ------------------------------------------------------------------
    print('--- 1, 2, 7, 8, 9. RAMIRO: baja en ALTIPLANO RP1 → reingreso a la misma empresa con otras condiciones')
    H_RAMIRO = huella(PID['RAMIRO'])
    REL_VIEJA = q(f"select id from relaciones_laborales where personal_id = '{PID['RAMIRO']}'")
    ESQ_VIEJO = q(f"select id from personal_registros_pago where personal_id = '{PID['RAMIRO']}'")
    H_REL_VIEJA = huella_ids('relaciones_laborales', [REL_VIEJA])
    EVS_VIEJOS = lista(f"select id from eventos_laborales where relacion_laboral_id = '{REL_VIEJA}'")
    MOVS_VIEJOS = lista(f"select id from idse_movimientos where relacion_laboral_id = '{REL_VIEJA}'")
    H_EVS, H_MOVS = huella_ids('eventos_laborales', EVS_VIEJOS), huella_ids('idse_movimientos', MOVS_VIEJOS)
    ficha(pg, 'RAMIRO REYES SOTO', 'laboral')
    ok(pg.is_visible('#hl-btn-reingreso') and pg.is_visible('#hl-btn-ingreso') and 'Registrar nuevo ingreso' in txt(pg, '#hl-btn-ingreso'),
       '1a «Relación laboral» distingue «Registrar reingreso» y «Registrar nuevo ingreso»')
    ok('IMSS · $2,800.00 bruto · Semanal (cerrado el 31/05/2025)' in txt(pg, f'[data-relacion="{REL_VIEJA}"]'),
       'P1a la tarjeta de la relación dice qué esquema de pago le pertenece (cerrado con la baja)', txt(pg, f'[data-relacion="{REL_VIEJA}"] .rl-esqs'))
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(400)
    blq = txt(pg, f + ' .ing-aviso')
    ok('Es un reingreso' in blq and '31/05/2025' in blq and not habilitado(pg, f),
       '1b «Nuevo ingreso» en una empresa donde ya trabajó: lo detiene, explica que es reingreso y el botón queda inactivo', blq[:140])
    foto(pg, 'r02-nuevo-ingreso-es-reingreso')
    pg.click(f + ' [data-ir-reingreso]'); pg.wait_for_timeout(500)
    sec = txt(pg, f)
    ok('Registrar reingreso' in sec and 'RESR880808HDFYTM01' in sec and '44444444440' in sec and 'F-778812' in sec and 'LUCIA SOTO' in sec,
       '3.1-3.2 recupera el expediente: CURP, NSS, FONACOT y contacto anteriores visibles')
    ref = txt(pg, f + ' .ri-ref-caja')
    ok(all(k in ref for k in ('01/02/2022', '31/05/2025', 'Separación voluntaria', '$400.00', 'Permanente', 'Fijo', 'Semana completa', '015', 'R01', '$2,800.00 bruto', 'no se copian ni se reactivan')),
       '3.5 muestra la relación anterior como referencia: ingreso, baja y causa, SDI, tipos, jornada, UMF, número interno y su esquema cerrado', ref[:200])
    ok(pg.eval_on_selector(f + ' [name=rp]', 's => s.options[s.selectedIndex].text') == 'Y1234567101',
       '3.4 propone el registro patronal de la relación anterior (se puede cambiar)')
    vacios = pg.evaluate("f => ['fecha','sdi','tt','ts','jo','umf','num'].map(n => document.querySelector(f + ' [name=' + n + ']').value)", f)
    ok(all(v == '' for v in vacios), '3.6 las condiciones del nuevo periodo empiezan vacías: no se dan por válidas las anteriores', str(vacios))
    ok(not habilitado(pg, f), 'P3a el botón «Registrar reingreso» se ve inactivo mientras no se confirme el expediente')
    foto(pg, 'r03-reingreso-formulario')
    # Fecha no posterior a la baja anterior
    pg.fill(f + ' [name=fecha]', '2025-05-20'); pg.dispatch_event(f + ' [name=fecha]', 'change')
    pg.check(f + ' [name=confirma_expediente]'); pg.wait_for_timeout(200)
    ok(habilitado(pg, f), 'P3b al marcar la confirmación el botón cambia a habilitado')
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(800)
    ok('posterior a la baja anterior' in txt(pg, '#rl-msg') and 'laboral_registrar_ingreso' not in rpc,
       '1c la fecha de reingreso debe ser posterior a la baja anterior (31/05/2025); no se envía nada', txt(pg, '#rl-msg')[:120])
    # Datos personales: se actualizan en su sección y el reingreso capturado se conserva
    pg.fill(f + ' [name=fecha]', '2026-11-02'); pg.dispatch_event(f + ' [name=fecha]', 'change')
    pg.fill(f + ' [name=sdi]', '520'); pg.dispatch_event(f + ' [name=sdi]', 'input')
    pg.click(f + ' [data-ir-seccion="contacto"]'); pg.wait_for_timeout(400)
    pg.fill('#d-emerg-telefono', '5559998888')
    pg.click('#btn-guardar-detalle'); pg.wait_for_timeout(2500)
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(600)
    ok(pg.is_visible(f) and pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == '2026-11-02' and pg.input_value(f + ' [name=sdi]').replace(',', '') in ('520', '520.00')
       and '5559998888' in txt(pg, f) and not pg.is_checked(f + ' [name=confirma_expediente]') and q(f"select contacto_emergencia_telefono from personal where id = '{PID['RAMIRO']}'") == '5559998888',
       '3.3 actualizar un dato personal (teléfono de emergencia) no pierde lo capturado; el expediente se muestra actualizado y la confirmación se pide otra vez',
       str([pg.is_visible(f), pg.input_value(f + ' [name=fecha]') if pg.query_selector(f) else None, pg.input_value(f + ' [name=sdi]') if pg.query_selector(f) else None, '5559998888' in txt(pg, f), txt(pg, '#rl-msg')[:80]]))
    foto(pg, 'r04-reingreso-tras-actualizar-contacto')
    # Usar los datos anteriores como punto de partida (explícito) y ajustarlos
    pg.click(f + ' [data-copiar-anterior]'); pg.wait_for_timeout(300)
    copiados = pg.evaluate("f => ['tt','ts','jo','umf','num'].map(n => document.querySelector(f + ' [name=' + n + ']').value)", f)
    ok(copiados == ['1', '0', '0', '015', 'R01'] and pg.query_selector(f + ' [name=umf].hl-falta') is not None,
       '3.6b «Usar … anteriores como punto de partida» copia solo tipos, jornada, UMF y número interno, marcados para revisar', str(copiados))
    pg.fill(f + ' [name=umf]', '016')
    pg.fill(f + ' [name=motivo]', 'Reingreso tras renuncia')
    pg.check(f + ' [name=confirma_expediente]'); pg.wait_for_timeout(200)
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2500)
    m = txt(pg, '#rl-msg')
    ok('Reingreso registrado' in m and '02/11/2026' in m and 'pendiente' in m and 'Y1234567101' in m and 'sus esquemas de pago siguen cerrados' in m and 'Paso 2' in m,
       '1d reingreso registrado: dice dónde, con qué fecha, el 08 pendiente y que la relación anterior no cambió', m[:200])
    foto(pg, 'r05-reingreso-registrado')
    REL_NUEVA = q(f"select id from relaciones_laborales where personal_id = '{PID['RAMIRO']}' and id <> '{REL_VIEJA}'")
    ok(q(f"select count(*) from personal where curp = 'RESR880808HDFYTM01'") == '1' and q(f"select empleado_id || '|' || estatus from personal where id = '{PID['RAMIRO']}'") == 'BEH-001001|Activo',
       '6 el expediente no se duplica: misma persona BEH-001001 (una sola CURP), estatus vuelve a Activo')
    ok(q(f"select estado || '|' || fecha_ingreso || '|' || sdi || '|' || sbc || '|' || umf || '|' || numero_interno || '|' || registro_patronal_id from relaciones_laborales where id = '{REL_NUEVA}'")
       == f'vigente|2026-11-02|520.00|520.00|016|R01|{RP1}',
       '2a nuevo periodo = relación nueva con sus propias condiciones (SDI 520, UMF 016)')
    ok(q(f"select tipo || '|' || estado from eventos_laborales where relacion_laboral_id = '{REL_NUEVA}' and tipo in ('ingreso','reingreso')") == 'reingreso|vigente',
       '1e la Historia laboral lo registra como «reingreso»')
    ok(huella_ids('relaciones_laborales', [REL_VIEJA]) == H_REL_VIEJA and
       q(f"select estado || '|' || fecha_ingreso || '|' || fecha_baja || '|' || causa_baja || '|' || sdi from relaciones_laborales where id = '{REL_VIEJA}'") == 'baja|2022-02-01|2025-05-31|2|400.00',
       '7a la relación anterior queda idéntica, byte a byte (ingreso 01/02/2022, baja 31/05/2025, causa 2, SDI 400)')
    ok(huella_ids('eventos_laborales', EVS_VIEJOS) == H_EVS and huella_ids('idse_movimientos', MOVS_VIEJOS) == H_MOVS
       and q(f"select count(*) from eventos_laborales where relacion_laboral_id = '{REL_VIEJA}'") == str(len(EVS_VIEJOS))
       and q(f"select string_agg(tipo_movimiento || ':' || estado, ',' order by tipo_movimiento desc) from idse_movimientos where relacion_laboral_id = '{REL_VIEJA}'") == '08:confirmado,02:confirmado',
       '7b sus eventos y sus movimientos 08 y 02 quedan idénticos; no se agregó nada a esa relación')
    ok(q(f"select activo || '|' || fecha_fin || '|' || relacion_laboral_id from personal_registros_pago where id = '{ESQ_VIEJO}'") == f'false|2025-05-31|{REL_VIEJA}'
       and q(f"select count(*) from personal_registros_pago where relacion_laboral_id = '{REL_NUEVA}'") == '0',
       '8a el esquema anterior sigue cerrado y no se ligó al nuevo periodo')
    ok(q(f"select tipo_movimiento || '|' || estado || '|' || fecha_movimiento || '|' || sbc from idse_movimientos where relacion_laboral_id = '{REL_NUEVA}'") == '08|pendiente|2026-11-02|520.00',
       '9a el reingreso con RP genera su alta (08) pendiente con la fecha y el SBC nuevos')
    # Paso 2: el nuevo esquema de pago, ya ligado a la relación nueva
    pg.click('#rl-msg [data-definir-esquema]'); pg.wait_for_timeout(1500)
    ok(pg.is_visible('#rp-form') and pg.input_value('#rp-empresa') == ALTI and pg.input_value('#rp-registro-patronal') == RP1 and pg.eval_on_selector('#rp-fecha-inicio', 'e => e.value') == '2026-11-02'
       and pg.input_value('#rp-sueldo') == '' and 'no se copian del periodo anterior' in txt(pg, '#toast-registros-pago'),
       '3.7 «Definir el esquema de pago» abre Compensación con empresa, RP y fecha del nuevo periodo; sueldo y periodicidad se capturan',
       str([pg.is_visible('#rp-form'), pg.input_value('#rp-empresa'), pg.input_value('#rp-registro-patronal'), pg.eval_on_selector('#rp-fecha-inicio', 'e => e.value'), pg.input_value('#rp-sueldo'), txt(pg, '#toast-registros-pago')[:90]]))
    pg.select_option('#rp-clasificacion', '0f000000-0000-4000-8000-000000000001'); pg.select_option('#rp-periodicidad', '0e000000-0000-4000-8000-000000000030')
    pg.select_option('#rp-modalidad', 'neto'); pg.fill('#rp-sueldo', '18000')
    foto(pg, 'r06-paso2-esquema')
    pg.click('#btn-rp-guardar'); pg.wait_for_timeout(2500)
    ok(q(f"select relacion_laboral_id || '|' || activo || '|' || sueldo || '|' || modalidad_sueldo from personal_registros_pago where personal_id = '{PID['RAMIRO']}' and id <> '{ESQ_VIEJO}'")
       == f'{REL_NUEVA}|true|18000.00|neto' and q(f"select activo::text from personal_registros_pago where id = '{ESQ_VIEJO}'") == 'false',
       '2b el nuevo esquema (Mensual, $18,000 neto) queda ligado a la relación nueva; el anterior sigue cerrado (8b)')
    tarjetas = pg.eval_on_selector_all('#d-registros-pago .rp-tarjeta', 'ts => ts.map(t => [...t.querySelectorAll("dt,dd,.pill")].map(x => x.textContent.trim()).join(" "))')
    ok(any('Activo' in t and 'Relación laboral CONSTRUCTORA ALTIPLANO DEMO · RP Y1234567101 · ingreso 02/11/2026' in t for t in tarjetas)
       and any('Relación laboral CONSTRUCTORA ALTIPLANO DEMO · RP Y1234567101 · ingreso 01/02/2022 · baja 31/05/2025' in t for t in tarjetas)
       and 'Esquema de pago registrado' in txt(pg, '#sbc-msg'),
       'P1b Compensación dice a qué relación pertenece cada esquema (el nuevo y el cerrado del periodo anterior)', txt(pg, '#sbc-msg')[:120] + ' || ' + ' || '.join(tarjetas)[:400])
    pg.evaluate("document.querySelector('.rp-historicos') && (document.querySelector('.rp-historicos').open = true)")
    foto(pg, 'r07-compensacion-esquemas-por-relacion')
    pg.click('[data-detail-tab="historia"]'); pg.wait_for_timeout(700)
    hist = txt(pg, '#hl-raiz')
    ok('Reingreso' in hist and 'Baja' in hist and 'Ingreso' in hist, '7c Historia laboral muestra el periodo anterior (ingreso y baja) y el reingreso')
    foto(pg, 'r08-historia-reingreso')
    # Bandeja IDSE
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    if pg.query_selector('#hl-aviso-imss'): pg.click('#hl-aviso-imss [data-av="cerrar"]'); pg.wait_for_timeout(300)
    ir(pg, 'idse'); pg.wait_for_timeout(600)
    pg.select_option('#idse-rp', RP1); pg.wait_for_timeout(1200)
    p08 = txt(pg, '#idse-pend-08')
    ok('RAMIRO REYES SOTO' in p08 and '02/11/2026' in p08, '9b el 08 del reingreso aparece en la bandeja IDSE del RP Y1234567101', p08[:160])
    foto(pg, 'r09-bandeja-08-reingreso')

    # ------------------------------------------------------------------
    print('--- 3 y P4. SOFIA: trabajó en ALTIPLANO; regresa al grupo en SERVICIOS CUMBRE (sin RP)')
    H_SOFIA = huella(PID['SOFIA']); REL_S = q(f"select id from relaciones_laborales where personal_id = '{PID['SOFIA']}'")
    ficha(pg, 'SOFIA TREJO LUNA', 'laboral')
    pg.click('#hl-btn-reingreso'); pg.wait_for_timeout(400)
    opc = pg.eval_on_selector_all(f + ' [name=empresa] option', 'os => os.map(o => o.text)')
    ok(opc == ['Elige…', 'CONSTRUCTORA ALTIPLANO DEMO'] and 'otra empresa del grupo, usa «Registrar nuevo ingreso»' in txt(pg, f),
       '3a el reingreso solo ofrece empresas donde ya trabajó; para otra empresa del grupo indica «Registrar nuevo ingreso»', str(opc))
    pg.click(f + ' [data-cancelar]'); pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', CUMBRE); pg.wait_for_timeout(400)
    ok('Antecedentes de esta persona en el grupo' in txt(pg, f) and '10/01/2021' in txt(pg, f + ' .ri-ref-caja') and txt(pg, f + ' .ing-aviso') == ''
       and pg.eval_on_selector_all(f + ' [name=rp] option', 'os => os.map(o => o.text)') == ['Sin registro patronal (sin IDSE)'],
       '3b nuevo ingreso en otra empresa: muestra sus antecedentes en el grupo como referencia y no lo bloquea')
    pg.fill(f + ' [name=fecha]', '2026-11-03'); pg.dispatch_event(f + ' [name=fecha]', 'change')
    foto(pg, 'r10-otra-empresa-del-grupo')
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2500)
    REL_S2 = q(f"select id from relaciones_laborales where personal_id = '{PID['SOFIA']}' and id <> '{REL_S}'")
    ok('Ingreso registrado' in txt(pg, '#rl-msg') and 'no genera movimiento IDSE' in txt(pg, '#rl-msg')
       and q(f"select count(*) from personal where curp = 'TELS910412MDFRNF02'") == '1'
       and q(f"select empresa_id || '|' || estado || '|' || coalesce(registro_patronal_id::text, 'sinRP') from relaciones_laborales where id = '{REL_S2}'") == f'{CUMBRE}|vigente|sinRP',
       '3c mismo expediente; relación separada en SERVICIOS CUMBRE', txt(pg, '#rl-msg')[:120])
    ok(q(f"select count(*) from idse_movimientos where relacion_laboral_id = '{REL_S2}'") == '0',
       'P4a una relación SIN registro patronal no genera ningún movimiento IDSE')
    ok(q(f"select estado || '|' || empresa_id || '|' || fecha_baja from relaciones_laborales where id = '{REL_S}'") == f'baja|{ALTI}|2024-12-31'
       and q(f"select string_agg(tipo_movimiento || ':' || estado, ',' order by tipo_movimiento desc) from idse_movimientos where relacion_laboral_id = '{REL_S}'") == '08:confirmado,02:confirmado',
       '3d la relación anterior en ALTIPLANO no cambia')
    foto(pg, 'r11-dos-empresas-relaciones-separadas')

    # ------------------------------------------------------------------
    print('--- 4. TOMAS: ya tiene una relación vigente en ALTIPLANO RP1')
    H_TOMAS = huella(PID['TOMAS'])
    ficha(pg, 'TOMAS UGALDE VARGAS', 'laboral')
    pg.click('#hl-btn-reingreso'); pg.wait_for_timeout(500)
    blq = txt(pg, f + ' .ing-aviso')
    pg.check(f + ' [name=confirma_expediente]'); pg.wait_for_timeout(200)
    ok('No se puede registrar el reingreso' in blq and 'vigente' in blq and 'Y1234567101' in blq and '15/01/2024' in blq and not habilitado(pg, f),
       '4a reingreso con una relación vigente en la misma empresa y RP: lo impide y explica el motivo; el botón sigue inactivo aun confirmando', blq[:170])
    foto(pg, 'r12-reingreso-duplicado-bloqueado')
    pg.fill(f + ' [name=fecha]', '2026-11-04')
    rpc.clear(); pg.eval_on_selector(f, 'fm => { fm.querySelector("button[type=submit]").disabled = false; fm.requestSubmit(); }'); pg.wait_for_timeout(900)
    ok('laboral_registrar_ingreso' not in rpc and 'No se puede registrar' in txt(pg, '#rl-msg'),
       '4b aunque se fuerce el botón, la lógica de envío vuelve a revisar y no envía nada', str(rpc) + ' ' + txt(pg, '#rl-msg')[:100])
    err = pg.evaluate("""async () => { const r = await sb.rpc('laboral_registrar_ingreso', { p_personal_id: '%s', p_empresa_id: '%s', p_registro_patronal_id: '%s', p_fecha_ingreso: '2026-11-04' }); return r.error ? r.error.message : 'sin error'; }"""
                      % (PID['TOMAS'], ALTI, RP1))
    ok('ya tiene una relación vigente con esa empresa y registro patronal' in err and huella(PID['TOMAS']) == H_TOMAS,
       '4c la base también lo impide (llamada directa) y nada de TOMAS cambió', err[:120])
    pg.click(f + ' [data-cancelar]'); pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.wait_for_timeout(300)
    ok('No se puede registrar el ingreso' in txt(pg, f + ' .ing-aviso') and not habilitado(pg, f), '4d «Nuevo ingreso» en el mismo RP también queda bloqueado')

    # ------------------------------------------------------------------
    print('--- 5. DIANA: relación migrada vigente sin fecha de ingreso (y una relación anterior dada de baja)')
    ficha(pg, 'DIANA FUENTES ORTIZ', 'laboral')
    REL_DA = q(f"select id from relaciones_laborales where personal_id = '{PID['DIANA']}' and estado = 'vigente'")
    REL_DB = q(f"select id from relaciones_laborales where personal_id = '{PID['DIANA']}' and estado = 'baja'")
    H_DB = huella_ids('relaciones_laborales', [REL_DB])
    pg.click('#hl-btn-reingreso'); pg.wait_for_timeout(500)
    blq = txt(pg, f + ' .ing-aviso')
    ok('No es un reingreso' in blq and 'solo le falta su fecha de ingreso' in blq and pg.query_selector(f + ' .ing-aviso [data-ir-corregir]') and not habilitado(pg, f),
       '5a la relación migrada sin fecha no se confunde con un reingreso: se bloquea y ofrece «Corregir datos de esa relación»', blq[:170])
    foto(pg, 'r13-migrada-sin-fecha-no-es-reingreso')
    pg.click(f + ' .ing-aviso [data-ir-corregir]'); pg.wait_for_timeout(500)
    fc = f'#hl-form-{REL_DA} form'
    ok(pg.is_visible(fc) and 'Relación que se corrige: CONSTRUCTORA ALTIPLANO DEMO · sin registro patronal' in txt(pg, fc),
       '5b lleva a «Corregir datos» de la relación migrada, indicando cuál se corrige')
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
    print('--- 5c. CESAR: «Nuevo ingreso» sin RP con su relación migrada sin fecha')
    ficha(pg, 'CESAR DELGADILLO HINOJOSA', 'laboral')
    pg.click('#hl-btn-ingreso'); pg.wait_for_timeout(400)
    pg.select_option(f + ' [name=empresa]', ALTI); pg.select_option(f + ' [name=rp]', ''); pg.wait_for_timeout(300)
    ok('solo le falta su fecha de ingreso' in txt(pg, f + ' .ing-aviso') and pg.query_selector(f + ' .ing-aviso [data-ir-corregir]') and not habilitado(pg, f),
       '5c «Nuevo ingreso» sin RP con una relación migrada sin fecha: se bloquea y lleva a «Corregir datos»')
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

    print('--- 6b. Alta sin coincidencias: se crea normalmente')
    if pg.is_visible('#modal-overlay'): pg.click('.detail-head-actions > button'); pg.wait_for_timeout(400)
    if pg.query_selector('#hl-aviso-imss'): pg.click('#hl-aviso-imss [data-av="cerrar"]'); pg.wait_for_timeout(300)
    n_antes = q("select count(*) from personal")
    ir(pg, 'alta')
    pg.fill('#f-nombres', 'VALERIA'); pg.fill('#f-apellido1', 'NUEVA'); pg.fill('#f-apellido2', 'PRUEBA')
    pg.fill('#f-curp', 'NUPV950505MDFVRL09'); pg.fill('#f-rfc', 'NUPV950505AB3'); pg.fill('#f-nss', '88888888880')
    pg.click('#btn-alta'); pg.wait_for_timeout(2500)
    ok(q("select count(*) from personal") == str(int(n_antes) + 1) and q("select count(*) from personal where curp = 'NUPV950505MDFVRL09'") == '1'
       and not pg.is_visible('#toast-alta') and 'Persona registrada: VALERIA NUEVA PRUEBA' in txt(pg, '#alta-guardada-texto'),
       'C6 sin coincidencias: el alta se guarda normalmente (una sola ficha nueva)', txt(pg, '#alta-guardada-texto')[:120])
    ok(not pg.errores, 'sin errores de JavaScript (Nómina)', '; '.join(pg.errores)[:300])
    ctx.close()
    # Móvil: el formulario de reingreso no desborda
    ctx, pg = abrir(b, 'nomina', 390, 844)
    ficha(pg, 'SOFIA TREJO LUNA', 'laboral')
    pg.click('#hl-btn-reingreso'); pg.wait_for_timeout(500)
    ok(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'M1 en móvil el reingreso no desborda la pantalla')
    foto(pg, 'r22-reingreso-movil')
    ok(not pg.errores, 'sin errores de JavaScript (móvil)', '; '.join(pg.errores)[:200])
    ctx.close(); b.close()

n_ok = sum(1 for _, c in res if c)
print(f'\n{n_ok}/{len(res)} pruebas OK')
sys.exit(0 if n_ok == len(res) else 1)
