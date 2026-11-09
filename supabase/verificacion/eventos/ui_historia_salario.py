"""Pantallas reorganizadas (8-nov-2026): Historia laboral como bitácora de solo lectura,
gestión en Relación laboral y modificación de salario (07) desde Compensación.
Base LOCAL bhui (montar_ui_eventos.sh + 20261108000200), datos sintéticos. Nunca toca Supabase.
Uso: python3 ui_historia_salario.py <index.html> <carpeta_capturas>"""
import sys, os, json, subprocess
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, 'ui_eventos.py'), encoding='utf-8').read()
exec(src[:src.index('with sync_playwright() as p:')])

PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui']
def q(s):
    r = subprocess.run(PSQL, input=s, capture_output=True, text=True)
    if 'ERROR' in r.stderr: sys.exit(r.stderr)
    return r.stdout.strip()
REL = lambda nombre, rp: q(f"select rl.id from relaciones_laborales rl join personal p on p.id = rl.personal_id join empresas_registros_patronales r on r.id = rl.registro_patronal_id "
                          f"where p.nombre_completo = '{nombre}' and r.registro_patronal = '{rp}'")
RA, RB1, RB2 = REL('ADELA PALACIOS GALVAN', 'Y1234567101'), REL('BENITO ZAVALA GALINDO', 'Y1234567101'), REL('BENITO ZAVALA GALINDO', 'Y1234567102')
RP1 = q("select id from empresas_registros_patronales where registro_patronal = 'Y1234567101'")
IDS = q("select string_agg(id::text, ',' order by id) from eventos_laborales")
md5_previos = lambda: q(f"select md5(string_agg(to_jsonb(e)::text, '' order by id)) from eventos_laborales e where id = any(string_to_array('{IDS}', ',')::uuid[])")
EV_ANTES = md5_previos()
txt = lambda pg, sel: (pg.text_content(sel) or '').strip() if pg.query_selector(sel) else ''

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'nomina')
    rpc = []
    pg.on('request', lambda r: rpc.append((r.url.split('/rpc/')[-1].split('?')[0], r.post_data)) if '/rpc/laboral_modificar_salario' in r.url else None)

    print('--- Historia laboral: bitácora de solo lectura')
    ficha(pg, 'BENITO ZAVALA GALINDO', 'historia')
    ok(not pg.query_selector('#hl-raiz [data-accion]') and not pg.query_selector('#hl-raiz #hl-btn-ingreso') and not pg.query_selector('#hl-raiz [data-sbc]')
       and not pg.query_selector('#hl-raiz [data-anular]') and not pg.query_selector('#hl-raiz form') and not pg.query_selector('#hl-raiz input')
       and pg.eval_on_selector_all('#hl-raiz button', 'bs => bs.map(b => b.id)') == ['hl-orden'],
       'B1 la bitácora es solo consulta: sin «Modificar salario», «Dar de baja», «Corregir datos», «Registrar ingreso», «Anular» ni formularios (solo filtro y orden)')
    donde = pg.eval_on_selector_all('#hl-raiz .hl-ev .hl-ev-donde', 'es => es.map(e => e.innerText.trim())')
    ok(len(donde) >= 2 and all(' · RP Y12345671' in d for d in donde) and len(set(donde)) == 2,
       'B2 con dos relaciones laborales, cada acontecimiento dice su empresa y RP', ' | '.join(donde))
    ok('más de una relación laboral' in txt(pg, '#hl-raiz'), 'B3 la bitácora avisa que la persona tiene más de una relación')
    reg = pg.eval_on_selector_all('#hl-raiz .hl-ev .hl-meta', 'es => es.map(e => e.innerText.trim()).filter(t => t.startsWith("Registrado por"))')
    ok(reg and all('Registrado por Migración inicial el' in r for r in reg), 'B4 cada acontecimiento dice quién lo registró y cuándo', reg[0] if reg else '')
    ok(pg.query_selector('#hl-raiz .hl-ev .hl-tabla thead') is not None and 'Dato' in txt(pg, '#hl-raiz .hl-tabla thead'), 'B5 los cambios se muestran como Dato | Anterior | Nuevo')
    fechas = lambda: pg.eval_on_selector_all('#hl-raiz .hl-ev .hl-ev-fecha', 'es => es.map(e => e.firstChild.textContent.trim())')
    f1 = fechas(); pg.click('#hl-orden'); pg.wait_for_timeout(300); f2 = fechas()
    ok(f1[-1] == 'Sin fecha' and f2[-1] == 'Sin fecha' and f1[0] != 'Sin fecha' and f2[0] != 'Sin fecha',
       'B6 los acontecimientos sin fecha efectiva quedan al final con cualquier orden', f'{f1} / {f2}')
    pg.click('#hl-orden'); pg.wait_for_timeout(300)
    foto(pg, 'b1-bitacora-dos-relaciones')

    print('--- Relación laboral: gestión y organización visual')
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(500)
    ok(pg.is_visible(f'#rl-raiz [data-accion="baja"][data-rel="{RB1}"]') and pg.is_visible(f'#rl-raiz [data-accion="corregir"][data-rel="{RB2}"]') and pg.is_visible('#rl-raiz #hl-btn-ingreso'),
       'R1 ingreso, baja y corrección están en Relación laboral')
    sec = txt(pg, '[data-detail-section="laboral"]')
    ok(sec.find('Datos de la relación y seguridad social') < sec.find('Datos internos de la empresa') and sec.find('Datos de la relación y seguridad social') >= 0
       and 'Jornada (descripción interna)' in sec and 'Fecha de ingreso (administrativa)' in sec and 'no se envían al IMSS' in sec,
       'R2 dos grupos: «Datos de la relación y seguridad social» y después «Datos internos de la empresa» (jornada y fecha internas rotuladas)')
    datos = txt(pg, f'#rl-raiz [data-relacion="{RB1}"] .hl-datos')
    orden = [datos.find(k) for k in ('Estado', 'Ingreso', 'Antigüedad', 'Tipo de trabajador', 'Tipo de salario', 'Jornada IMSS', 'SDI', 'UMF')]
    ok(all(x >= 0 for x in orden) and orden == sorted(orden) and 'SBC' not in datos,
       'R3 la relación muestra estado, ingreso, antigüedad, tipo de trabajador, tipo de salario, jornada IMSS, SDI y UMF (sin SBC aparte)', datos[:160])
    foto(pg, 'b2-relacion-laboral')

    print('--- Compensación: un solo dato, el SDI')
    dialogos = []
    pg.on('dialog', lambda d: dialogos.append(d.message))
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion')
    pg.wait_for_timeout(800)
    bloque = txt(pg, '#sbc-raiz')
    ok('Salario ante el IMSS (SDI)' in bloque and 'SDI vigente registrado: $420.00 diario' in bloque and 'Tope de cotización hoy: $2,932.75 diario (25 UMA × $117.31)' in bloque,
       'S1 muestra el SDI vigente y el tope de hoy (25 UMA × UMA vigente), con formato', bloque[:220])
    ok('No es el sueldo diario nominal (sueldo mensual ÷ 30)' in bloque and 'ni se calcula de los esquemas de pago' in bloque, 'S2 explica qué es el SDI y que no es el sueldo diario nominal')
    foto(pg, 'b3-compensacion-sdi')
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(500)
    f = f'#sbc-form-{RA} form'
    ok(pg.query_selector(f + ' [name=sbc]') is None and pg.query_selector(f + ' [name=sdi]') is not None
       and 'SDI — salario diario integrado' in txt(pg, f), 'S0 un solo campo de importe: «SDI — salario diario integrado» (ya no hay SBC y SDI por separado)')
    pg.fill(f + ' [name=sdi]', '3000'); pg.wait_for_timeout(700)
    av = txt(pg, f + ' .sbc-avisos')
    ok(txt(pg, f + ' .sbc-tecnico') == '$2,932.75' and 'rebasa el tope' in av and not pg.is_disabled(f + ' button[type=submit]'),
       'S3 SDI arriba del tope: no bloquea; el SBC técnico del 07 es el tope ($2,932.75) y se conserva el SDI', f"{txt(pg, f + ' .sbc-tecnico')} · {av[:100]}")
    foto(pg, 'b4-sdi-tope')
    pg.fill(f + ' [name=fecha]', '2026-01-15'); pg.dispatch_event(f + ' [name=fecha]', 'change'); pg.wait_for_timeout(900)
    ok(txt(pg, f + ' .sbc-tecnico') == '$2,828.50' and 'UMA vigente al 15/01/2026' in txt(pg, f + ' .sbc-tope-det'),
       'S5 el tope usa la UMA de la fecha efectiva (enero 2026: SBC técnico $2,828.50)', txt(pg, f + ' .sbc-tope-det'))
    pg.fill(f + ' [name=fecha]', '2026-11-01'); pg.dispatch_event(f + ' [name=fecha]', 'change')
    visible = lambda sel: pg.eval_on_selector(sel, "e => Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').get.call(e)")
    ok(visible(f + ' [name=fecha]') == '01/11/2026' and pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == '2026-11-01',
       'D1 el campo de fecha muestra DD/MM/AAAA (01/11/2026) aunque el navegador esté en inglés; internamente es 2026-11-01', visible(f + ' [name=fecha]'))
    pg.fill(f + ' [name=fecha]', ''); pg.click(f + ' [name=fecha]'); pg.keyboard.type('15012026', delay=30); pg.dispatch_event(f + ' [name=fecha]', 'change'); pg.wait_for_timeout(900)
    ok(visible(f + ' [name=fecha]') == '15/01/2026' and pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == '2026-01-15' and 'UMA vigente al 15/01/2026' in txt(pg, f + ' .sbc-tope-det'),
       'D2 se escribe con máscara (15012026 → 15/01/2026) y el tope usa esa fecha', visible(f + ' [name=fecha]'))
    pg.fill(f + ' [name=fecha]', ''); pg.click(f + ' [name=fecha]'); pg.keyboard.type('31022026', delay=30); pg.wait_for_timeout(200)
    ok(pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == '' and pg.eval_on_selector(f + ' [name=fecha]', 'e => !e.checkValidity()'),
       'D3 una fecha inexistente (31/02/2026) no se acepta', pg.eval_on_selector(f + ' [name=fecha]', 'e => e.validationMessage'))
    pg.eval_on_selector(f + ' .campo-fecha-mx-sel', "s => { s.value = '2026-11-01'; s.dispatchEvent(new Event('change')); }"); pg.wait_for_timeout(700)
    ok(visible(f + ' [name=fecha]') == '01/11/2026' and pg.is_visible(f + ' .campo-fecha-mx-btn'), 'D4 el calendario opcional también deja la fecha en DD/MM/AAAA')
    foto(pg, 'b4c-fecha-dd-mm-aaaa')
    pg.fill(f + ' [name=sdi]', '300'); pg.wait_for_timeout(700)
    ok('salario mínimo general ($315.04)' in txt(pg, f + ' .sbc-avisos') and pg.is_disabled(f + ' button[type=submit]'), 'S6 SDI debajo del salario mínimo: bloqueado, con el mínimo de la fecha')
    pg.fill(f + ' [name=sdi]', '320'); pg.wait_for_timeout(700)
    ok('salario mínimo integrado' in txt(pg, f + ' .sbc-avisos') and not pg.is_disabled(f + ' button[type=submit]'),
       'S8 entre el mínimo ($315.04) y el mínimo integrado (≈$330.57): solo aviso, no bloquea', txt(pg, f + ' .sbc-avisos')[:120])
    pg.fill(f + ' [name=sdi]', '420'); pg.wait_for_timeout(700)
    ok('no cambia' in txt(pg, f + ' .sbc-avisos') and pg.is_disabled(f + ' button[type=submit]'), 'S6b el mismo salario vigente: no hay 07 que registrar (no se envía)')
    pg.fill(f + ' [name=sdi]', '400'); pg.wait_for_timeout(700)
    av = txt(pg, f + ' .sbc-avisos')
    ok('menor que el vigente (SBC $420.00 → $400.00)' in av and 'obligatorio' in txt(pg, f + ' .sbc-motivo-lab'), 'S7 salario menor al vigente: advierte y el motivo pasa a obligatorio', av[:150])
    foto(pg, 'b5-sdi-menor')
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1000)
    ok(not rpc and 'justificación' in txt(pg, '#sbc-msg'), 'S9 sin justificación no se envía nada', txt(pg, '#sbc-msg')[:120])
    pg.fill(f + ' [name=motivo]', 'Cambio a salario variable acordado')
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sdi]'); pg.keyboard.type('1250000.5', delay=40); pg.wait_for_timeout(200)
    mientras = pg.input_value(f + ' [name=sdi]')
    pg.keyboard.type('678'); pg.wait_for_timeout(300)
    tope_dec = pg.input_value(f + ' [name=sdi]')
    ok(txt(pg, '#sbc-msg') == '', 'S9b el error anterior desaparece en cuanto se corrige el formulario', txt(pg, '#sbc-msg')[:80])
    foto(pg, 'b4b-separador-al-escribir')
    pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(200)
    ok(mientras == '1,250,000.5' and tope_dec == '1,250,000.56' and pg.input_value(f + ' [name=sdi]') == '1,250,000.56',
       'S10 el separador de miles aparece MIENTRAS se escribe y se limita a 2 decimales', f'{mientras} → {tope_dec}')
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sdi]'); pg.keyboard.type('3000', delay=30); pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(200)
    ok(pg.input_value(f + ' [name=sdi]') == '3,000.00', 'S10a al salir del SDI se completan los 2 decimales (3000 → 3,000.00)', pg.input_value(f + ' [name=sdi]'))
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sdi]'); pg.keyboard.type('1250', delay=40); pg.wait_for_timeout(200)
    escrito = pg.input_value(f + ' [name=sdi]')
    pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(300)
    ok(escrito == '1,250' and pg.input_value(f + ' [name=sdi]') == '1,250.00', 'S10b al salir del campo se completan los 2 decimales', escrito)
    falt = pg.eval_on_selector(f'#hl-faltan-07-{RA} > div', 'd => d.className')
    ok(falt == 'sbc-av' and 'todavía no estará listo para generar' in txt(pg, f'#hl-faltan-07-{RA}') and not pg.query_selector(f'#hl-faltan-07-{RA} .err'),
       'S10c los datos faltantes para el archivo son advertencia ámbar (se permite registrar)', falt)
    pg.fill(f + ' [name=sdi]', '415'); pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(500)
    rpc.clear(); dialogos.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2200)
    cuerpo = json.loads(rpc[-1][1]) if rpc else {}
    ok(cuerpo.get('p_sbc') == 415 and cuerpo.get('p_sdi') == 415 and isinstance(cuerpo.get('p_sbc'), (int, float)),
       'S11 se envían SDI y SBC técnico como números (415 / 415), no como texto con formato', f"{cuerpo.get('p_sbc')} / {cuerpo.get('p_sdi')}")
    m = txt(pg, '#sbc-msg')
    ok('Modificación de salario registrada' in m and 'pendiente en la bandeja IDSE del registro patronal Y1234567101' in m and 'con SBC $415.00' in m and pg.is_visible('#sbc-msg a:has-text("Ver en la bandeja IDSE")'),
       'S12 el aviso nombra el RP y el SBC del movimiento, dice que el 07 quedó pendiente y enlaza a su bandeja', m[:200])
    ok('Archivo todavía no listo: falta' in m, 'S12b distingue «movimiento registrado» de «archivo listo para generar»', m[m.find('Archivo'):][:120])
    ok(q(f"select motivo from eventos_laborales where relacion_laboral_id = '{RA}' and tipo = 'modificacion_salario'") == 'Cambio a salario variable acordado',
       'S13 la justificación queda en el evento')
    foto(pg, 'b6-aviso-07')

    print('--- Navegación después de guardar (aviso de cambios sin guardar)')
    pg.click('#sbc-msg a:has-text("Ver en la bandeja IDSE")'); pg.wait_for_timeout(2000)
    ok(not dialogos, 'G1 «Ver en la bandeja IDSE» después de guardar: sin aviso de cambios sin guardar', ' | '.join(dialogos)[:100])
    ok(pg.is_visible('#panel-idse') and pg.input_value('#idse-rp') == RP1 and 'ADELA PALACIOS GALVAN' in txt(pg, '#idse-pend-07'),
       'S14 el enlace abre la bandeja IDSE en ese RP, con el 07 pendiente')
    foto(pg, 'b7-bandeja-desde-aviso')

    print('--- Faltantes: completar desde la bandeja y volver')
    fila = txt(pg, '#idse-pend-07')
    ok('Falta: Tipo de trabajador' in fila and pg.is_visible('#idse-pend-07 [data-completar="rel"]'),
       'F1 la bandeja dice qué falta y ofrece «Completar datos de la relación laboral»', fila[fila.find('Falta'):][:120])
    pg.click('#idse-pend-07 [data-completar="rel"]'); pg.wait_for_timeout(2500)
    fc = f'#hl-form-{RA} form'
    marcados = pg.eval_on_selector_all(fc + ' .hl-falta', 'es => es.map(e => e.name)') if pg.query_selector(fc) else []
    ok(pg.is_visible('[data-detail-section="laboral"]') and set(marcados) >= {'tipo_trabajador', 'jornada'} and 'Falta para IDSE' in txt(pg, fc),
       'F2 abre la ficha en Relación laboral, en «Corregir datos» de esa relación, con los campos faltantes marcados', ','.join(marcados))
    foto(pg, 'b11-completar-faltantes')
    pg.select_option(fc + ' [name=tipo_trabajador]', '1'); pg.select_option(fc + ' [name=jornada]', '0')
    if 'tipo_salario' in marcados: pg.select_option(fc + ' [name=tipo_salario]', '0')
    pg.fill(fc + ' [name=motivo]', 'Datos para IDSE'); dialogos.clear()
    pg.click(fc + ' button[type=submit]'); pg.wait_for_timeout(2200)
    ok('Corrección registrada' in txt(pg, '#rl-msg') and pg.is_visible('#rl-msg a:has-text("Volver a la bandeja IDSE")'), 'F3 al guardar, el aviso ofrece volver a la bandeja IDSE', txt(pg, '#rl-msg')[:120])
    pg.click('#rl-msg a:has-text("Volver a la bandeja IDSE")'); pg.wait_for_timeout(2000)
    fila = txt(pg, '#idse-pend-07')
    ok(not dialogos and pg.is_visible('#panel-idse') and 'ADELA PALACIOS GALVAN' in fila and 'Tipo de trabajador' not in fila and 'Jornada' not in fila,
       'F4 regresa a la bandeja sin aviso de cambios y el movimiento ya no tiene esos faltantes', fila[:160])
    # Validadores: el aviso anticipado del 07 y la bandeja usan la misma regla de NSS
    nss_adela = q("select nss from public.personal where nombre_completo = 'ADELA PALACIOS GALVAN'")
    q("update public.personal set nss = '11111111111' where nombre_completo = 'ADELA PALACIOS GALVAN'")
    pg.reload(); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)  # la lista de personal se lee al cargar
    ir(pg, 'idse'); pg.wait_for_timeout(1200)
    ok(pg.is_visible('#idse-pend-07 [data-completar="persona"]'), 'F5 con un NSS inválido, la bandeja ofrece «Completar datos de la persona»')
    pg.click('#idse-pend-07 [data-completar="persona"]'); pg.wait_for_timeout(2000)
    ok(pg.is_visible('[data-detail-section="personal"]') and pg.eval_on_selector('#d-nss', 'e => e.classList.contains("hl-falta")')
       and pg.is_visible('#idse-retorno a:has-text("Volver a la bandeja IDSE")'), 'F6 abre Datos personales con el NSS marcado y el enlace para volver a la bandeja')
    foto(pg, 'b12-completar-persona')
    pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(400)
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(400)
    ok('NSS válido (el dígito verificador no corresponde)' in txt(pg, f'#hl-faltan-07-{RA}') and 'guía' not in txt(pg, f'#hl-faltan-07-{RA}'),
       'V5 el aviso del 07 detecta el NSS con dígito verificador incorrecto y ya no pide la guía', txt(pg, f'#hl-faltan-07-{RA}')[:160])
    dialogos.clear(); pg.click('.detail-head-actions > button'); pg.wait_for_timeout(500)
    ok(not dialogos, 'G2 cerrar la ficha con un formulario abierto pero sin escribir nada: sin advertencia', ' | '.join(dialogos)[:80])
    q(f"update public.personal set nss = '{nss_adela}' where nombre_completo = 'ADELA PALACIOS GALVAN'")
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion'); pg.wait_for_timeout(600)
    ok(txt(pg, '#sbc-msg') == '', 'P1 al volver a abrir la ficha el aviso verde ya no aparece')
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(300)
    pg.fill(f + ' [name=fecha]', '2026-11-02'); pg.fill(f + ' [name=sdi]', '3000'); pg.wait_for_timeout(600); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2200)
    ok('Modificación de salario registrada' in txt(pg, '#sbc-msg') and 'con SBC $2,932.75 (tope de 25 UMA; SDI $3,000.00)' in txt(pg, '#sbc-msg'), 'P2 (control) el aviso aparece tras registrar', txt(pg, '#sbc-msg')[:160])
    ok(q(f"select sbc||'/'||sdi from relaciones_laborales where id = '{RA}'") == '2932.75/3000.00'
       and q(f"select m.sbc from idse_movimientos m join eventos_laborales e on e.id = m.evento_id where e.relacion_laboral_id = '{RA}' and e.fecha_efectiva = '2026-11-02'") == '2932.75',
       'S15 SDI $3,000 sobre el tope: la relación guarda SDI 3,000 y el 07 lleva el SBC técnico $2,932.75', q(f"select sbc||'/'||sdi from relaciones_laborales where id = '{RA}'"))
    dialogos.clear(); pg.click('.detail-head-actions > button'); pg.wait_for_timeout(500)
    ok(not dialogos and not pg.is_visible('#modal-overlay'), 'G3 cerrar la ficha después de guardar: sin advertencia', ' | '.join(dialogos)[:80])
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion'); pg.wait_for_timeout(600)
    pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(300)
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(300); pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(300)
    ok(txt(pg, '#sbc-msg') == '', 'P3 al cambiar de sección y regresar el aviso ya no persiste')
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(300); pg.click(f + ' [name=sdi]'); pg.keyboard.type('500', delay=20)
    dialogos.clear(); pg.click('.detail-head-actions > button'); pg.wait_for_timeout(500)
    ok(dialogos and 'cambios sin guardar' in dialogos[0], 'G4 con un SDI escrito y sin guardar, cerrar la ficha SÍ advierte (protección conservada)', (dialogos or [''])[0][:60])
    ficha(pg, 'BENITO ZAVALA GALINDO', 'compensacion'); pg.wait_for_timeout(600)
    ok(txt(pg, '#sbc-msg') == '' and txt(pg, '#rl-msg') == '', 'P4 el aviso de una persona no aparece en la ficha de otra')

    print('--- Sueldo y SDI no se mezclan')
    ficha(pg, 'BENITO ZAVALA GALINDO', 'compensacion'); pg.wait_for_timeout(800)
    sbc_antes = q(f"select coalesce(sbc::text,'null') from relaciones_laborales where id = '{RB2}'")
    ok('SDI vigente registrado: No registrado' in txt(pg, '#sbc-raiz'), 'N1 sin SDI vigente se dice explícitamente (no se inventa)')
    pg.click(f'[data-sbc="{RB2}"]'); pg.wait_for_timeout(500)
    ok('Dato migrado sin SDI' in txt(pg, f'#sbc-form-{RB2} .sbc-resumen'), 'N2 el formulario explica el tratamiento del dato faltante')
    pg.click(f'#sbc-form-{RB2} [data-cancelar]')
    ESQ_LIG = q(f"select id from personal_registros_pago where relacion_laboral_id = '{RB2}' and activo")
    ESQ_SIN = q("select r.id from personal_registros_pago r join personal p on p.id = r.personal_id where p.nombre_completo = 'BENITO ZAVALA GALINDO' and r.activo and r.relacion_laboral_id is null")
    ok(ESQ_LIG and ESQ_SIN and 'Un esquema de pago no tiene relación laboral asignada' in txt(pg, '#sbc-raiz'),
       'V1 con dos relaciones (mismo empresa, dos RP) se avisa del esquema sin relación')
    pg.click(f'button[onclick="editarRegistroPago(\'{ESQ_SIN}\')"]'); pg.wait_for_timeout(500)
    v = float((pg.input_value('#rp-sueldo') or '0').replace(',', ''))
    pg.fill('#rp-sueldo', f'{v + 50:.2f}'); pg.click('#btn-rp-guardar'); pg.wait_for_timeout(2200)
    m = txt(pg, '#sbc-msg')
    ok('no tiene relación laboral asignada' in m and not pg.query_selector('#sbc-desde-sueldo'),
       'V2 esquema sin relación: no ofrece un 07 (no adivina la relación); pide asignarla', m[:160])
    pg.click(f'button[onclick="editarRegistroPago(\'{ESQ_LIG}\')"]'); pg.wait_for_timeout(500)
    v = float((pg.input_value('#rp-sueldo') or '0').replace(',', ''))
    pg.fill('#rp-sueldo', f'{v + 100:.2f}'); pg.click('#btn-rp-guardar'); pg.wait_for_timeout(2200)
    m = txt(pg, '#sbc-msg')
    ok('no se actualiza solo' in m and 'RP Y1234567102' in txt(pg, '#sbc-desde-sueldo') and q(f"select coalesce(sbc::text,'null') from relaciones_laborales where id = '{RB2}'") == sbc_antes,
       'N3 cambiar el sueldo NO cambia el SBC; ofrece el 07 de la relación de ESE esquema (RP …102)', txt(pg, '#sbc-desde-sueldo'))
    esq_txt = txt(pg, f'[data-sbc-rel="{RB2}"] .hl-meta')
    ok(f'{v + 100:,.2f}' in esq_txt, 'N3b la lista de esquemas de la relación ya muestra el sueldo recién guardado', esq_txt)
    pg.click('#sbc-desde-sueldo'); pg.wait_for_timeout(500)
    ok(pg.is_visible(f'#sbc-form-{RB2} form') and not pg.query_selector(f'#sbc-form-{RB1} form') and 'solo' in txt(pg, f'#sbc-form-{RB2}') and 'RP Y1234567102' in txt(pg, f'#sbc-form-{RB2} b'),
       'N4 el botón abre el 07 de la relación correcta y lo dice («solo para … RP Y1234567102»)')
    ok('Origen: cambio del esquema de pago' in txt(pg, f'#sbc-form-{RB2}') and 'RP Y1234567102' in txt(pg, f'#sbc-form-{RB2} .hl-aviso-sueldo'),
       'N4b el 07 abierto desde el esquema dice qué esquema lo origina y a qué relación y RP pertenece', txt(pg, f'#sbc-form-{RB2}')[:200])
    foto(pg, 'b8-aviso-cambio-sueldo')
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(400)
    opciones = pg.eval_on_selector_all(f'#hl-pend-{ESQ_SIN} option', 'os => os.map(o => o.textContent)')
    ok(len(opciones) == 3 and all('ingreso' in o and ('RP Y1234567101' in o or 'RP Y1234567102' in o) for o in opciones[1:]),
       'V3 al asignar, cada opción muestra empresa, RP e ingreso', ' | '.join(opciones[1:]))
    pg.select_option(f'#hl-pend-{ESQ_SIN}', RB1)
    dialogos = []
    pg.once('dialog', lambda d: dialogos.append(d.message))
    pg.click(f'[data-asignar="{ESQ_SIN}"]'); pg.wait_for_timeout(1800)
    ok(dialogos and 'RP Y1234567101' in dialogos[0] and q(f"select relacion_laboral_id from personal_registros_pago where id = '{ESQ_SIN}'") == RB1
       and 'RP Y1234567101' in txt(pg, '#rl-msg'), 'V4 la asignación pide confirmación nombrando la relación y queda en la correcta', (dialogos or [''])[0][:90])
    pg.click('[data-detail-tab="movimientos"]'); pg.wait_for_timeout(500)
    mv = txt(pg, '[data-detail-section="movimientos"]')
    ok('Bitácora administrativa de la ficha' in mv and 'Historia laboral' in mv and not pg.query_selector('[data-detail-section="movimientos"] .hl-ev'),
       'M3 Movimientos es la bitácora administrativa de la ficha: no lista acontecimientos laborales y remite a Historia laboral', mv[:120])
    foto(pg, 'b10-movimientos')
    ok(not pg.errores, 'N5 sin errores de JavaScript (Nómina)', '; '.join(pg.errores)[:200])
    ctx.close()

    print('--- Consulta y móvil')
    ctx, pg = abrir(b, 'consulta')
    ir(pg, 'lista'); pg.fill('#buscar-personal', 'ADELA'); pg.wait_for_timeout(500)
    ok(pg.eval_on_selector('#tabla-personal a:has-text("ADELA PALACIOS GALVAN")', 'a => getComputedStyle(a).pointerEvents') == 'none',
       'C1 Consulta sigue sin abrir fichas (V2.0): no ve bitácora, gestión ni SBC')
    ok(not pg.errores, 'C2 sin errores de JavaScript (Consulta)', '; '.join(pg.errores)[:200])
    ctx.close()
    ctx, pg = abrir(b, 'admin', 390, 844)
    ficha(pg, 'BENITO ZAVALA GALINDO', 'historia')
    ok(pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'M1 en teléfono la bitácora no desborda la pantalla')
    foto(pg, 'b9-bitacora-telefono')
    ok(not pg.errores, 'M2 sin errores de JavaScript (teléfono)', '; '.join(pg.errores)[:200])
    ctx.close()
    b.close()

ok(md5_previos() == EV_ANTES and len(IDS.split(',')) == int(q(f"select count(*) from eventos_laborales where id = any(string_to_array('{IDS}', ',')::uuid[])")),
   'X1 los eventos que ya existían quedan íntegros (mismo contenido, ninguno borrado)')
fallas = [n for n, c in res if not c]
print(f"\n{len(res) - len(fallas)}/{len(res)} pruebas de pantalla correctas")
sys.exit(1 if fallas else 0)
