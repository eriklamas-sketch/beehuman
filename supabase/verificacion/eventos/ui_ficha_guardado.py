"""Pruebas de las correcciones del diagnóstico IDSE (5-nov-2026). Base LOCAL, datos sintéticos.
Ficha general con y sin historial, mensajes entre fichas, registros de pago independientes,
barra de guardado por sección y fecha/faltantes de la modificación de salario.
Uso: ./montar_ui_eventos.sh && python3 ui_ficha_guardado.py <index.html> <carpeta_capturas>"""
import sys, os, json, subprocess, datetime
AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, 'ui_eventos.py'), encoding='utf-8').read()
exec(src[:src.index('with sync_playwright() as p:')])
try:
    from zoneinfo import ZoneInfo
    HOY_MX = datetime.datetime.now(ZoneInfo('America/Mexico_City')).date().isoformat()
except Exception:
    HOY_MX = (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).date().isoformat()

PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui']
def q(sql):
    r = subprocess.run(PSQL, input=sql, capture_output=True, text=True)
    if 'ERROR' in r.stderr: sys.exit(r.stderr)
    return r.stdout.strip()
TEN = q("select tenant_id from personal limit 1")
EMP_SIN_RP = q("select id from empresas where nombre='SERVICIOS CUMBRE DEMO'")
EMP_CON_RP = q("select id from empresas where nombre='CONSTRUCTORA ALTIPLANO DEMO'")
RP1 = q("select id from empresas_registros_patronales where empresa_id='%s' order by registro_patronal limit 1" % EMP_CON_RP)
# Dos personas sintéticas SIN historial laboral, para comprobar que siguen como antes.
q(f"""begin; set local session_replication_role = replica;
insert into personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, empresa_id, estatus, comentario_baja)
values ('0a1fff00-0000-4000-8000-000000000001','{TEN}','BEH-SH-01','SOFIA SINHIST UNO','SOFIA','SINHIST','UNO','{EMP_SIN_RP}','Activo', null),
       ('0a1fff00-0000-4000-8000-000000000002','{TEN}','BEH-SH-02','TOMAS SINHIST DOS','TOMAS','SINHIST','DOS','{EMP_CON_RP}','Activo', '');
update personal set registro_patronal_id = '{RP1}' where id = '0a1fff00-0000-4000-8000-000000000002'; commit;""")
fila = lambda nombre, cols: q(f"select {cols} from personal where nombre_completo='{nombre}'")

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg = abrir(b, 'admin')
    envios = []
    pg.on('request', lambda r: envios.append((r.method, r.url.split('/rest/v1/')[-1].split('?')[0], r.post_data)) if r.method in ('PATCH', 'POST', 'DELETE') and '/rest/v1/' in r.url and '/rpc/' not in r.url else None)
    patch_personal = lambda: [json.loads(d) for m, t, d in envios if m == 'PATCH' and t == 'personal']
    toast = lambda: (pg.text_content('#toast-detalle') or '').strip()
    def poner(sel, valor): pg.eval_on_selector(sel, '(e, v) => { e.value = v; e.dispatchEvent(new Event("input", {bubbles: true})); }', valor)
    def guardar(): envios.clear(); pg.click('#btn-guardar-detalle'); pg.wait_for_timeout(1700)
    CONTROLADOS = {'empresa_id', 'registro_patronal_id', 'numero_interno_trabajador', 'fecha_baja', 'comentario_baja'}

    print('--- Ficha con historial y registro patronal (ADELA)')
    antes = fila('ADELA PALACIOS GALVAN', "registro_patronal_id||'|'||coalesce(numero_interno_trabajador,'')||'|'||empresa_id")
    ficha(pg, 'ADELA PALACIOS GALVAN', 'personal')
    guardar()
    ok('No hay cambios por guardar' in toast() and not patch_personal(), 'sin modificaciones: «No hay cambios por guardar» y no se envía nada', toast())
    poner('#d-emerg-telefono', '5511112222'); guardar()
    env = patch_personal()
    ok(env and not (CONTROLADOS & set(env[-1])) and 'No se pudo' not in toast(), 'con una modificación: se guarda y no envía ningún dato de Historia laboral', f"{toast()} | claves={sorted(set(env[-1]) & CONTROLADOS) if env else 'sin envío'}")
    ok(fila('ADELA PALACIOS GALVAN', 'contacto_emergencia_telefono') == '5511112222', 'el teléfono quedó guardado en la base')
    ok(fila('ADELA PALACIOS GALVAN', "registro_patronal_id||'|'||coalesce(numero_interno_trabajador,'')||'|'||empresa_id") == antes, 'registro patronal, número interno y empresa no cambiaron')
    pg.select_option('#d-estatus', 'Suspendido'); guardar()
    ok(fila('ADELA PALACIOS GALVAN', 'estatus') == 'Suspendido' and 'No se pudo' not in toast(), 'Activo → Suspendido sigue permitido con historial', toast())
    pg.select_option('#d-estatus', 'Activo'); guardar()

    print('--- Ficha con historial sin registro patronal (CESAR, solo efectivo)')
    ficha(pg, 'CESAR DELGADILLO HINOJOSA', 'personal')
    guardar()
    ok('No hay cambios por guardar' in toast() and not patch_personal(), 'sin modificaciones: no se envía nada', toast())
    poner('#d-emerg-telefono', '5533334444'); guardar()
    env = patch_personal()
    ok(env and not (CONTROLADOS & set(env[-1])) and fila('CESAR DELGADILLO HINOJOSA', 'contacto_emergencia_telefono') == '5533334444', 'con una modificación: se guarda sin enviar datos de Historia laboral', toast())
    ok(fila('CESAR DELGADILLO HINOJOSA', "coalesce(comentario_baja,'<null>')") == '<null>', 'el comentario de baja sigue en NULL (antes se intentaba guardar como texto vacío)')

    print('--- Persona sin historial (sigue como antes)')
    ficha(pg, 'TOMAS SINHIST DOS', 'personal')
    ok(not pg.is_disabled('#d-empresa') and not pg.is_disabled('#d-numero-interno'), 'sin historial, empresa y número interno se editan en la ficha')
    poner('#d-numero-interno', '777'); poner('#d-comentariobaja', '   '); guardar()
    env = patch_personal()
    ok(env and env[-1].get('numero_interno_trabajador') == '777' and env[-1].get('registro_patronal_id') == RP1, 'sin historial, el guardado sigue enviando empresa, registro patronal y número interno', str({k: env[-1].get(k) for k in ('numero_interno_trabajador', 'registro_patronal_id')}) if env else 'sin envío')
    ok(fila('TOMAS SINHIST DOS', "numero_interno_trabajador||'|'||registro_patronal_id||'|'||coalesce(comentario_baja,'<null>')") == f'777|{RP1}|<null>', 'quedó guardado; el comentario de baja vacío se normaliza a NULL')
    ficha(pg, 'SOFIA SINHIST UNO', 'personal')
    opciones_rp = pg.eval_on_selector('#d-registro-patronal', 'e => [...e.options].map(o => o.text)')
    poner('#d-emerg-telefono', '5599990000'); guardar()
    env = patch_personal()
    ok(opciones_rp == ['Sin asignar'] and env and env[-1].get('registro_patronal_id') is None and fila('SOFIA SINHIST UNO', "contacto_emergencia_telefono||'|'||coalesce(registro_patronal_id::text,'<null>')") == '5599990000|<null>',
       'empresa sin registros patronales: guarda como antes, con el registro patronal en NULL', str(opciones_rp))

    print('--- Mensajes: una ficha nueva no hereda los de la anterior')
    ficha(pg, 'ADELA PALACIOS GALVAN', 'personal')
    poner('#d-curp', 'CURP-INVALIDA'); guardar()
    t1 = toast()
    ficha(pg, 'CESAR DELGADILLO HINOJOSA', 'personal')
    ok(t1 and not pg.is_visible('#toast-detalle') and toast() == '', 'un error en una ficha no aparece al abrir la siguiente', f'antes: {t1[:60]!r}')
    guardar(); t2 = toast()
    ficha(pg, 'DIANA FUENTES ORTIZ', 'personal')
    ficha(pg, 'EDER LOPEZ RUIZ', 'personal')
    ok(t2 and not pg.is_visible('#toast-detalle'), 'tampoco un aviso de éxito, al abrir varias fichas seguidas', f'antes: {t2[:40]!r}')

    print('--- Registro de pago independiente y barra de guardado por sección')
    ficha(pg, 'ADELA PALACIOS GALVAN', 'personal')
    ok(pg.is_visible('#btn-guardar-detalle'), '«Guardar cambios» se ve en Datos personales')
    pg.click('[data-detail-tab="compensacion"]'); pg.wait_for_timeout(600)
    ok(not pg.is_visible('#btn-guardar-detalle'), '«Guardar cambios» de la ficha no se ve en Compensación')
    envios.clear()
    pg.click('button[onclick^="editarRegistroPago("]'); pg.wait_for_timeout(500)
    v = float(pg.input_value('#rp-sueldo') or 0); pg.fill('#rp-sueldo', f'{v + 25:.2f}')
    pg.click('#btn-rp-guardar'); pg.wait_for_timeout(1800)
    escrit = [(m, t) for m, t, d in envios]
    ok(('PATCH', 'personal_registros_pago') in escrit and not [e for e in escrit if e[1] == 'personal'], 'guardar el registro de pago solo escribe el registro de pago, nunca la ficha', str(escrit))
    ok('guardados' in (pg.text_content('#toast-registros-pago') or ''), 'el registro de pago confirma su propio guardado', (pg.text_content('#toast-registros-pago') or '').strip())
    ficha(pg, 'CESAR DELGADILLO HINOJOSA', 'compensacion')
    ok(not pg.is_visible('#toast-registros-pago'), 'el aviso del registro de pago no pasa a la siguiente ficha')
    pg.click('[data-detail-tab="historia"]'); pg.wait_for_timeout(700)
    ok(not pg.is_visible('#btn-guardar-detalle'), '«Guardar cambios» de la ficha no se ve en Historia laboral')
    foto(pg, 'f1-historia-sin-barra')

    print('--- Modificación de salario: fecha de hoy (México) y datos que faltan para el IDSE')
    ficha(pg, 'ADELA PALACIOS GALVAN', 'compensacion')
    rel = q("select rl.id from relaciones_laborales rl join personal p on p.id=rl.personal_id where p.nombre_completo='ADELA PALACIOS GALVAN' and rl.estado='vigente'")
    pg.click(f'[data-sbc="{rel}"]'); pg.wait_for_timeout(400)
    f = f'#sbc-form-{rel} form'
    ok(pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value') == HOY_MX, 'la fecha efectiva aparece con la fecha de hoy en México', f"{pg.eval_on_selector(f + ' [name=fecha]', 'e => e.value')} / esperado {HOY_MX}")
    faltan = (pg.text_content(f'#hl-faltan-07-{rel}') or '')
    ok('tipo de trabajador' in faltan and 'tipo de salario' in faltan and 'jornada' in faltan and 'Se puede registrar el movimiento' in faltan
       and pg.eval_on_selector(f'#hl-faltan-07-{rel} > div', 'd => d.className') == 'sbc-av',
       'antes de registrar se ve qué falta para el IDSE (tipos), como advertencia ámbar', faltan[:160])
    foto(pg, 'f2-modificacion-faltantes')
    pg.select_option(f + ' [name=ts]', '0'); pg.wait_for_timeout(200)
    ok('tipo de salario' not in (pg.text_content(f'#hl-faltan-07-{rel}') or ''), 'al elegir el tipo de salario en el formulario, deja de marcarse como faltante')
    pg.fill(f + ' [name=fecha]', '2026-10-30'); pg.fill(f + ' [name=sdi]', '612.40'); pg.wait_for_timeout(500)
    enviar(pg, f); pg.wait_for_timeout(1800)
    ok('Modificación de salario registrada' in msg(pg, '#sbc-msg') and q(f"select fecha_efectiva from eventos_laborales where relacion_laboral_id='{rel}' and tipo='modificacion_salario' and estado='vigente' order by registrado_en desc limit 1") == '2026-10-30',
       'la fecha se puede editar y la modificación queda con la fecha efectiva elegida', msg(pg))

    ok(not pg.errores, 'ningún error de JavaScript', '; '.join(pg.errores[:2]))
    b.close()
print(f"\n{sum(1 for _, c in res if c)}/{len(res)} pruebas correctas")
