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

    print('--- Relación laboral: gestión')
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(500)
    ok(pg.is_visible(f'#rl-raiz [data-accion="baja"][data-rel="{RB1}"]') and pg.is_visible(f'#rl-raiz [data-accion="corregir"][data-rel="{RB2}"]') and pg.is_visible('#rl-raiz #hl-btn-ingreso'),
       'R1 ingreso, baja y corrección están en Relación laboral')
    ok('Datos internos de la ficha' in txt(pg, '[data-detail-section="laboral"]') and 'Jornada (descripción interna)' in txt(pg, '[data-detail-section="laboral"]'),
       'R2 los campos antiguos quedan como «Datos internos» y su jornada no se confunde con la jornada IMSS')
    foto(pg, 'b2-relacion-laboral')

    print('--- Compensación: salario ante el IMSS (SBC)')
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion')
    pg.wait_for_timeout(800)
    bloque = txt(pg, '#sbc-raiz')
    ok('SBC vigente registrado: $420.00 diario' in bloque and 'Tope de cotización hoy: $2,932.75 diario (25 UMA × $117.31)' in bloque,
       'S1 muestra el SBC vigente y el tope de hoy (25 UMA × UMA vigente), con formato', bloque[:220])
    ok('No es el sueldo de los esquemas de pago' in bloque, 'S2 distingue sueldo y SBC')
    foto(pg, 'b3-compensacion-sbc')
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(500)
    f = f'#sbc-form-{RA} form'
    pg.fill(f + ' [name=sbc]', '3000'); pg.wait_for_timeout(700)
    av = txt(pg, f + ' .sbc-avisos')
    ok('no puede rebasar el tope de $2,932.75' in av and pg.is_visible(f + ' [data-usar-tope]') and pg.is_disabled(f + ' button[type=submit]'),
       'S3 arriba del tope: lo bloquea, explica y ofrece «Usar el tope»', av[:160])
    foto(pg, 'b4-tope')
    pg.click(f + ' [data-usar-tope]'); pg.wait_for_timeout(700)
    ok(pg.input_value(f + ' [name=sbc]') == '2,932.75' and pg.input_value(f + ' [name=sdi]') == '3,000.00' and not pg.is_disabled(f + ' button[type=submit]'),
       'S4 «Usar el tope»: SBC = tope y el valor capturado pasa al SDI (no se mezclan)', pg.input_value(f + ' [name=sbc]') + ' / ' + pg.input_value(f + ' [name=sdi]'))
    pg.fill(f + ' [name=fecha]', '2026-01-15'); pg.dispatch_event(f + ' [name=fecha]', 'change'); pg.wait_for_timeout(900)
    ok(txt(pg, f + ' .sbc-tope') == '$2,828.50' and 'UMA vigente al 15/01/2026' in txt(pg, f + ' .sbc-tope-det') and pg.is_disabled(f + ' button[type=submit]'),
       'S5 el tope usa la UMA de la fecha efectiva (enero 2026: $2,828.50)', txt(pg, f + ' .sbc-tope-det'))
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
    pg.fill(f + ' [name=sdi]', ''); pg.fill(f + ' [name=sbc]', '300'); pg.wait_for_timeout(700)
    ok('salario mínimo general ($315.04)' in txt(pg, f + ' .sbc-avisos') and pg.is_disabled(f + ' button[type=submit]'), 'S6 debajo del salario mínimo: bloqueado, con el mínimo de la fecha')
    pg.fill(f + ' [name=sbc]', '320'); pg.wait_for_timeout(700)
    ok('salario mínimo integrado' in txt(pg, f + ' .sbc-avisos') and not pg.is_disabled(f + ' button[type=submit]'),
       'S8 entre el mínimo ($315.04) y el mínimo integrado (≈$330.57): solo aviso, no bloquea', txt(pg, f + ' .sbc-avisos')[:120])
    pg.fill(f + ' [name=sbc]', '400'); pg.wait_for_timeout(700)
    av = txt(pg, f + ' .sbc-avisos')
    ok('menor que el vigente ($420.00 → $400.00)' in av and 'obligatorio' in txt(pg, f + ' .sbc-motivo-lab'), 'S7 SBC menor al vigente: advierte y el motivo pasa a obligatorio', av[:150])
    foto(pg, 'b5-sbc-menor')
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(1000)
    ok(not rpc and 'justificación' in txt(pg, '#sbc-msg'), 'S9 sin justificación no se envía nada', txt(pg, '#sbc-msg')[:120])
    pg.fill(f + ' [name=motivo]', 'Cambio a salario variable acordado')
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sdi]'); pg.keyboard.type('1250000.5', delay=40); pg.wait_for_timeout(200)
    mientras = pg.input_value(f + ' [name=sdi]')
    pg.keyboard.type('678'); pg.wait_for_timeout(100)
    tope_dec = pg.input_value(f + ' [name=sdi]')
    pg.click(f + ' [name=sbc]'); pg.fill(f + ' [name=sbc]', ''); pg.keyboard.type('2345.6', delay=40); pg.wait_for_timeout(300)
    ok(txt(pg, '#sbc-msg') == '', 'S9b el error anterior desaparece en cuanto se corrige el formulario', txt(pg, '#sbc-msg')[:80])
    foto(pg, 'b4b-separador-al-escribir')
    pg.click(f + ' [name=sdi]'); pg.keyboard.press('End')
    pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(200)
    ok(mientras == '1,250,000.5' and tope_dec == '1,250,000.56' and pg.input_value(f + ' [name=sdi]') == '1,250,000.56',
       'S10 el separador de miles aparece MIENTRAS se escribe y se limita a 2 decimales', f'{mientras} → {tope_dec}')
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sdi]'); pg.keyboard.type('3000', delay=30); pg.dispatch_event(f + ' [name=sdi]', 'blur'); pg.wait_for_timeout(200)
    ok(pg.input_value(f + ' [name=sdi]') == '3,000.00', 'S10a al salir del SDI se completan los 2 decimales (3000 → 3,000.00)', pg.input_value(f + ' [name=sdi]'))
    pg.fill(f + ' [name=sdi]', ''); pg.click(f + ' [name=sbc]'); pg.fill(f + ' [name=sbc]', ''); pg.keyboard.type('1250', delay=40); pg.wait_for_timeout(200)
    escrito = pg.input_value(f + ' [name=sbc]')
    pg.dispatch_event(f + ' [name=sbc]', 'blur'); pg.wait_for_timeout(300)
    ok(escrito == '1,250' and pg.input_value(f + ' [name=sbc]') == '1,250.00', 'S10b al salir del campo se completan los 2 decimales', escrito)
    # punto 2: faltantes = advertencia ámbar, no error
    falt = pg.eval_on_selector(f'#hl-faltan-07-{RA} > div', 'd => d.className')
    ok(falt == 'sbc-av' and 'todavía no estará listo para generar' in txt(pg, f'#hl-faltan-07-{RA}') and not pg.query_selector(f'#hl-faltan-07-{RA} .err'),
       'S10c los datos faltantes para el archivo son advertencia ámbar (se permite registrar)', falt)
    pg.fill(f + ' [name=sbc]', '415'); pg.dispatch_event(f + ' [name=sbc]', 'blur'); pg.wait_for_timeout(500)
    rpc.clear(); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2200)
    cuerpo = json.loads(rpc[-1][1]) if rpc else {}
    ok(cuerpo.get('p_sbc') == 415 and isinstance(cuerpo.get('p_sbc'), (int, float)), 'S11 se envía como número (415), no como texto con formato', str(cuerpo.get('p_sbc')))
    m = txt(pg, '#sbc-msg')
    ok('Modificación de salario registrada' in m and 'pendiente en la bandeja IDSE del registro patronal Y1234567101' in m and pg.is_visible('#sbc-msg a:has-text("Ver en la bandeja IDSE")'),
       'S12 el aviso nombra el RP, dice que el 07 quedó pendiente y enlaza a su bandeja', m[:200])
    ok('Archivo todavía no listo: falta' in m, 'S12b distingue «movimiento registrado» de «archivo listo para generar»', m[m.find('Archivo'):][:120])
    ok(q(f"select motivo from eventos_laborales where relacion_laboral_id = '{RA}' and tipo = 'modificacion_salario'") == 'Cambio a salario variable acordado',
       'S13 la justificación queda en el evento')
    foto(pg, 'b6-aviso-07')
    pg.click('#sbc-msg a:has-text("Ver en la bandeja IDSE")'); pg.wait_for_timeout(2000)
    ok(pg.is_visible('#panel-idse') and pg.input_value('#idse-rp') == RP1 and 'ADELA PALACIOS GALVAN' in txt(pg, '#idse-pend-07'),
       'S14 el enlace abre la bandeja IDSE en ese RP, con el 07 pendiente')
    foto(pg, 'b7-bandeja-desde-aviso')
    # Validadores: el aviso anticipado del 07 usa la misma regla de NSS que la bandeja
    nss_adela = q("select nss from public.personal where nombre_completo = 'ADELA PALACIOS GALVAN'")
    q("update public.personal set nss = '11111111111' where nombre_completo = 'ADELA PALACIOS GALVAN'")
    pg.reload(); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)  # la lista de personal se lee al cargar
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion'); pg.wait_for_timeout(600)
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(400)
    ok('NSS válido (el dígito verificador no corresponde)' in txt(pg, f'#hl-faltan-07-{RA}') and 'guía' not in txt(pg, f'#hl-faltan-07-{RA}'),
       'V5 el aviso del 07 detecta el NSS con dígito verificador incorrecto y ya no pide la guía', txt(pg, f'#hl-faltan-07-{RA}')[:160])
    q(f"update public.personal set nss = '{nss_adela}' where nombre_completo = 'ADELA PALACIOS GALVAN'")
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion'); pg.wait_for_timeout(600)
    ok(txt(pg, '#sbc-msg') == '', 'P1 al volver a abrir la ficha el aviso verde ya no aparece')
    pg.click(f'[data-sbc="{RA}"]'); pg.wait_for_timeout(300)
    pg.fill(f + ' [name=fecha]', '2026-11-02'); pg.fill(f + ' [name=sbc]', '430'); pg.click(f + ' button[type=submit]'); pg.wait_for_timeout(2200)
    ok('Modificación de salario registrada' in txt(pg, '#sbc-msg'), 'P2 (control) el aviso aparece tras registrar')
    pg.click('[data-detail-tab="laboral"]'); pg.wait_for_timeout(300); pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(300)
    ok(txt(pg, '#sbc-msg') == '', 'P3 al cambiar de sección y regresar el aviso ya no persiste')
    ficha(pg, 'BENITO ZAVALA GALINDO', 'compensacion'); pg.wait_for_timeout(600)
    ok(txt(pg, '#sbc-msg') == '' and txt(pg, '#rl-msg') == '', 'P4 el aviso de una persona no aparece en la ficha de otra')

    print('--- Sueldo y SBC no se mezclan')
    ficha(pg, 'BENITO ZAVALA GALINDO', 'compensacion'); pg.wait_for_timeout(800)
    sbc_antes = q(f"select coalesce(sbc::text,'null') from relaciones_laborales where id = '{RB2}'")
    ok('SBC vigente registrado: No registrado' in txt(pg, '#sbc-raiz'), 'N1 sin SBC vigente se dice explícitamente (no se inventa)')
    pg.click(f'[data-sbc="{RB2}"]'); pg.wait_for_timeout(500)
    ok('Dato migrado sin SBC' in txt(pg, f'#sbc-form-{RB2} .sbc-resumen'), 'N2 el formulario explica el tratamiento del dato faltante')
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
