"""Opción B · Firma única de Nómina por periodo en pantalla (Incidencias → Revisión), con datos FICTICIOS.
Sustituye a la versión de B-1 del 20-nov. Base local bhui; peticiones atendidas por rest_local.py como el usuario
(mismas RLS y permisos), no PostgREST real (eso se valida en B-c).
  U1  Otro usuario de Nómina (no responsable): ve «Falta la firma de Nómina del periodo», sin botón.
  U2  Responsable con pendientes que bloquean (importe por decidir): botón deshabilitado y la explicación.
  U3  Responsable sin pendientes: firma; aparece «✓ Firma de Nómina vigente» y deja de faltar.
  U4  Un cambio posterior se ve: «ya no es vigente … Cambió: importes», botón «Volver a firmar», historial «invalidada».
  U5  Volver a firmar: vigente; historial con la anterior «reemplazada por una firma posterior».
  U6  Huella desactualizada: si el concentrado cambió mientras se veía la pantalla, la firma se rechaza y no se registra.
  U7  La hoja ya no ofrece «Firmar como Nómina»; RH sí firma su hoja; nota de que Nómina firma el periodo.
  U8  Tablero: la columna de firmas es solo de RH.
  U9  Firma antigua de Nómina por hoja: se muestra como «ya no autoriza el periodo».
  U10 Celular (390 px): el bloque de firma cabe, sin desplazamiento horizontal.
  U11 Sin errores de JavaScript.
  U12 (23-nov, firma exclusiva en «Concentrado») Desde «Hojas» no se puede firmar como Nómina, ni con pendientes ni sin
      ellos: no hay botón de firma; solo el estado y un acceso al concentrado, que abre la pestaña «Concentrado».
  RED Registro de red: las peticiones a la dirección de beehuman-pruebas se responden en local y nada sale a internet.
  Desde el 23-nov las firmas de Nómina de U1–U6 se hacen en la pestaña «Concentrado»; las comprobaciones no cambian.
Uso: SUPABASE_JS=<supabase.js umd> python3 ui_b1_2.py <index.html> <carpeta_capturas>"""
import sys, os, json, time, base64, subprocess, datetime
from urllib.parse import urlparse, parse_qsl
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rest_local as RL

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']; REF = 'sflvpgkmtaxzogpgetxn'
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', RL.DB]
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    if err: raise RuntimeError(err)
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET') and not l.startswith('{"sub"')]; return out[-1] if out else ''

T = '1b700000-0000-4000-8000-000000000001'
U = {k: f'1b710000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['admin', 'nomina', 'nomina2', 'coord'], 1)}
RL.U.update(U)
E1, SEM, CL = '1b720000-0000-4000-8000-000000000001', '1b730000-0000-4000-8000-000000000007', '1b740000-0000-4000-8000-000000000001'
P = {k: f'1b750000-0000-4000-8000-0000000000{n:02d}' for n, k in enumerate(['CO', 'X'], 1)}
RLB = {k: v[:-3] + '9' + v[-2:] for k, v in P.items()}
HE = '1b760000-0000-4000-8000-000000000001'
if sql(f"select count(*) from public.tenants where id = '{T}'") != '0': print('La semilla ya existe: reconstruye bhui (montar_bhui.sh).'); sys.exit(1)
L = datetime.date.fromisoformat(sql("select (date_trunc('week', public.hoy_mx() + 7))::date"))
sem = lambda n: ((L + datetime.timedelta(days=7 * n)).isoformat(), (L + datetime.timedelta(days=7 * n + 6)).isoformat())
sql(f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT UI FIRMA');
insert into auth.users (id, email) select v, k||'.uib12@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA UI FIRMA');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL}','{T}','IMSS');
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id) values
 ('{P['CO']}','{T}','{E1}','COORDINADORA UI','UB-CO',null),('{P['X']}','{T}','{E1}','PERSONA X UI','UB-X','{P['CO']}');
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values
 ('{RLB['CO']}','{T}','{P['CO']}','{E1}','2025-01-01','vigente'),('{RLB['X']}','{T}','{P['X']}','{E1}','2025-01-01','vigente');
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  values ('{T}','{P['X']}','{RLB['X']}','{E1}','{CL}','{SEM}',3500,'bruto',7,'2025-01-01',true);
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['nomina2']}','{T}','nomina',null),('{U['coord']}','{T}','coordinador','{P['CO']}');
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user) values ('{E1}','{T}','2025-01-01','{U['nomina']}','{U['admin']}');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota) values ('{T}','{P['X']}','{P['CO']}','2025-01-01','carga_inicial','UI');
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1);
""", replica=True)
P1 = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','{sem(0)[0]}','{sem(0)[1]}')", 'nomina')
H1 = sql(f"select public.inc_abrir_hoja('{P1}')", 'coord')
sql(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{H1}','{P['X']}','{sem(0)[0]}','{HE}',2)", 'coord')
V1 = sql(f"select public.inc_enviar_hoja('{H1}')", 'coord')
LINEA = sql(f"select id from public.inc_importes where version_id = '{V1}'")
eventos_firma = lambda: sql(f"select count(*) from public.inc_eventos where periodo_id = '{P1}' and tipo = 'firma_nomina' and hoja_id is null")

# PGRST=1: las peticiones /rest/v1 van al PostgREST LOCAL (127.0.0.1:3010, base bhui) con un JWT firmado con el secreto
# local de pruebas (el mismo que ui_b1.py). Sin PGRST: traductor rest_local.py (modo por omisión).
import hmac, hashlib
PGRST = os.environ.get('PGRST') == '1'
SECRETO_LOCAL = b"beehuman-local-solo-pruebas-secreto-de-32-caracteres-o-mas"
def _b64b(d): return base64.urlsafe_b64encode(d).rstrip(b'=')
def jwt_local(sub):
    h = _b64b(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p_ = _b64b(json.dumps({"sub": sub, "role": "authenticated", "aud": "authenticated", "exp": int(time.time()) + 86400}).encode())
    return (h + b'.' + p_ + b'.' + _b64b(hmac.new(SECRETO_LOCAL, h + b'.' + p_, hashlib.sha256).digest())).decode()
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}
def b64(d): return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
RED = []   # registro de red: cada petición del navegador y qué se hizo con ella (respondida en local, abortada o dejada pasar)
def ruta_para(quien):
    def ruta(route):
        req = route.request; u = urlparse(req.url)
        accion = ('local' if (u.netloc == f'{REF}.supabase.co' or ('cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url) or u.netloc == 'fonts.googleapis.com')
                  else 'abortada' if u.scheme in ('http', 'https') else 'archivo_local')
        RED.append((accion, u.scheme, u.netloc, req.method))
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path.startswith('/auth/v1/user'): return route.fulfill(json={'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}, headers=CORS)
            if u.path.startswith('/rest/v1/'):
                if PGRST:
                    destino = 'http://127.0.0.1:3010/' + u.path[len('/rest/v1/'):] + (('?' + u.query) if u.query else '')
                    r = route.fetch(url=destino); h = dict(r.headers); h.update(CORS)
                    return route.fulfill(status=r.status, headers=h, body=r.body())
                tabla = u.path[len('/rest/v1/'):]; cuerpo = json.loads(req.post_data) if req.post_data else None
                try: st, res_, extra = RL.ejecutar(quien, req.method, tabla, parse_qsl(u.query, keep_blank_values=True), cuerpo, {k.lower(): v for k, v in req.headers.items()})
                except Exception as e: st, res_, extra = 400, {'code': 'LOCAL', 'message': str(e)}, {}
                h = dict(CORS); h.update(extra)
                if st == 204: return route.fulfill(status=204, headers=h, body='')
                return route.fulfill(status=st, headers=h, body=json.dumps(res_), content_type='application/json')
            return route.fulfill(json={}, headers=CORS)
        if u.scheme in ('http', 'https'): return route.abort()
        return route.continue_()
    return ruta

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def texto(pg, sel):
    el = pg.query_selector(sel); return el.inner_text().strip() if el else ''

with sync_playwright() as p:
    b = p.chromium.launch()
    def abrir(quien, ancho=1440, alto=950):
        ctx = b.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1)
        ses = {'access_token': jwt_local(U[quien]) if PGRST else b64({'alg': 'HS256'}) + '.' + b64({'sub': U[quien], 'role': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local',
               'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400, 'refresh_token': 'x', 'user': {'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(ses))});")
        ctx.route('**/*', ruta_para(quien)); pg = ctx.new_page(); pg.errores = []
        pg.on('websocket', lambda ws: RED.append(('websocket', 'ws', ws.url, '')))
        pg.on('pageerror', lambda e: pg.errores.append(str(e))); pg.on('dialog', lambda d: d.accept())
        pg.goto('file://' + os.path.abspath(HTML)); pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
        return ctx, pg
    def periodo(pg, per):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
        pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(900)
        pg.click(f'#inc-r-periodos [data-rev-per="{per}"]'); pg.wait_for_timeout(1500)
    def periodo(pg, per):
        pg.click('nav.tabs button[data-tab="incidencias"]'); pg.wait_for_timeout(900)
        pg.click('[data-inc-vista="revision"]'); pg.wait_for_timeout(900)
        pg.click(f'#inc-r-periodos [data-rev-per="{per}"]'); pg.wait_for_timeout(1800)
    def concentrado(pg):   # la firma de Nómina se inicia solo aquí
        pg.click('#inc-r-pestanas [data-r-pest="concentrado"]'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(800)
    def hojas(pg):
        pg.click('#inc-r-pestanas [data-r-pest="hojas"]'); pg.wait_for_selector('#inc-r-tablero', timeout=15000); pg.wait_for_timeout(800)
    errores = []

    print('== U1 · Otro usuario de Nómina ==')
    ctx, pg = abrir('nomina2'); periodo(pg, P1); concentrado(pg)
    ok('Falta la firma de Nómina del periodo' in texto(pg, '#inc-r-firma-per') and pg.query_selector('#inc-r-firmar-per') is None
       and 'Solo el responsable designado' in texto(pg, '#inc-r-firma-per'), 'U1 Otro usuario de Nómina: ve que falta la firma y que solo firma el responsable; sin botón', texto(pg, '#inc-r-firma-per'))
    errores += pg.errores; ctx.close()

    print('== U2 · Responsable con pendientes ==')
    ctx, pg = abrir('nomina'); periodo(pg, P1)
    ok(pg.query_selector('#inc-r-firmar-per') is None and pg.query_selector('#inc-r-ir-conc') is not None and 'importe por decidir' in texto(pg, '#inc-r-faltantes'),
       'U12 Hojas, con pendientes: sin botón de firma de Nómina; solo el estado y el acceso al concentrado', texto(pg, '#inc-r-firma-per')[:120])
    ok(pg.is_disabled('#inc-r-proc') and 'Falta la firma de Nómina del periodo' in texto(pg, '#inc-r-faltantes'),
       '+CONS-U1 Sin firma: el faltante se explica y «Marcar como procesado» está deshabilitado')
    pg.screenshot(path=f'{OUT}/U2_hojas_sin_firma.png', full_page=True)
    concentrado(pg)
    ok(pg.is_disabled('#inc-r-firmar-per') and 'Primero resuelve los pendientes' in texto(pg, '#inc-r-firma-per') and 'importe por decidir' in texto(pg, '#inc-c-bloquean'),
       'U2 Con un importe por decidir: botón deshabilitado y la explicación (Concentrado)', texto(pg, '#inc-r-firma-per'))
    pg.screenshot(path=f'{OUT}/U2_con_pendientes.png', full_page=True)
    hojas(pg)

    print('== U8 · Tablero ==')
    cab = texto(pg, '#inc-r-tablero thead'); celda = texto(pg, '#inc-r-tablero tbody tr td:nth-child(4)')
    ok('Firma RH' in cab and 'Nómina' not in celda and 'RH' in celda, 'U8 Tablero: la columna de firmas es solo de RH', f'{cab} | {celda}')

    print('== U3 · Firmar ==')
    sql(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina')
    periodo(pg, P1)
    ok(pg.query_selector('#inc-r-firmar-per') is None and pg.query_selector('#inc-r-ir-conc') is not None,
       'U12 Hojas, sin pendientes que bloqueen y siendo el responsable: tampoco hay botón de firma de Nómina')
    pg.click('#inc-r-ir-conc'); pg.wait_for_selector('#inc-c', timeout=15000); pg.wait_for_timeout(800)
    ok(pg.query_selector('#inc-c') is not None and 'activo' in (pg.get_attribute('#inc-r-pestanas [data-r-pest="concentrado"]', 'class') or ''),
       'U12 El acceso «Revisar y firmar en Concentrado» abre la pestaña «Concentrado»')
    ok(not pg.is_disabled('#inc-r-firmar-per'), '+ Sin pendientes que bloqueen, el botón se habilita (la firma de RH no bloquea)')
    pg.click('#inc-r-firmar-per'); pg.wait_for_timeout(2000)
    fir_ok = pg.query_selector('[data-firma-estado="vigente"]') is not None and 'Firma de Nómina vigente' in texto(pg, '#inc-r-firma-per')
    msg_firma = texto(pg, '#inc-r-msg'); fir_txt = texto(pg, '#inc-r-firma-per')
    hojas(pg)
    ok(fir_ok and 'firma de Nómina del periodo' not in texto(pg, '#inc-r-faltantes') and eventos_firma() == '1',
       'U3 El responsable firma: «✓ Firma de Nómina vigente» y deja de faltar; un evento en la base', texto(pg, '#inc-r-firma-per')[:120])
    ok('registrada' in msg_firma.lower() and 'nomina.uib12@' in fir_txt,
       '+CONS-U2 Mensaje de firma registrada; la firma muestra quién y cuándo', msg_firma)
    ok(pg.query_selector('#inc-r-firma-per [data-firma-estado="vigente"]') is not None and pg.query_selector('#inc-r-firmar-per') is None,
       'U12 Hojas muestra la misma firma vigente, sin botón')
    concentrado(pg); pg.screenshot(path=f'{OUT}/U3_firmado.png', full_page=True)

    print('== U4 · Invalidación visible ==')
    sql(f"select public.inc_decidir_importe('{LINEA}', 999, 'Ajuste UI')", 'nomina')
    periodo(pg, P1)
    ok(pg.query_selector('[data-firma-estado="invalidada"]') is not None and pg.query_selector('#inc-r-firmar-per') is None,
       'U12 Hojas, firma invalidada: se ve el estado, sin botón «Volver a firmar»')
    concentrado(pg)
    t = texto(pg, '#inc-r-firma-per')
    ok(pg.query_selector('[data-firma-estado="invalidada"]') is not None and 'ya no es vigente' in t and 'Cambió: importes' in t
       and 'Volver a firmar el periodo' in texto(pg, '#inc-r-firmar-per') and pg.query_selector('[data-firma-hist="invalidada"]') is not None,
       'U4 Cambio posterior: «ya no es vigente … Cambió: importes», botón «Volver a firmar» e historial «invalidada»', t[:160])
    pg.screenshot(path=f'{OUT}/U4_invalidada.png', full_page=True)

    print('== U5 · Volver a firmar ==')
    pg.click('#inc-r-firmar-per'); pg.wait_for_timeout(2000)
    ok(pg.query_selector('[data-firma-estado="vigente"]') is not None and pg.query_selector('[data-firma-hist="reemplazada"]') is not None
       and pg.query_selector('[data-firma-hist="vigente"]') is not None and eventos_firma() == '2',
       'U5 Volver a firmar: vigente; el historial muestra la anterior «reemplazada por una firma posterior»', eventos_firma())

    print('== U6 · Huella desactualizada ==')
    sql(f"select public.inc_decidir_importe('{LINEA}', 1000, 'Ajuste UI 2')", 'nomina')
    periodo(pg, P1); concentrado(pg)                   # la pantalla muestra la huella con 1000
    sql(f"select public.inc_decidir_importe('{LINEA}', 1001, 'Cambio mientras se revisa')", 'nomina')   # cambia sin recargar
    pg.click('#inc-r-firmar-per'); pg.wait_for_timeout(2000)
    ok('cambió mientras lo revisabas' in texto(pg, '#inc-r-msg') and eventos_firma() == '2',
       'U6 Si el concentrado cambió mientras se revisaba, la firma se rechaza y no se registra', texto(pg, '#inc-r-msg')[:110])

    print('== U7 · U9 · Hoja ==')
    sql(f"insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre) values ('{T}','{H1}','{P1}','{V1}','firma_nomina','{U['nomina']}','firma antigua por hoja')", replica=True)
    hojas(pg)
    pg.click(f'[data-rev-hoja="{H1}"]'); pg.wait_for_timeout(1800)
    f_n = texto(pg, '#inc-r-firmas')
    ok(pg.query_selector('[data-firmar="nomina"]') is None and 'Nómina firma el periodo completo' in f_n, 'U7 La hoja ya no ofrece «Firmar como Nómina» al responsable de Nómina', f_n[:140])
    ok(pg.query_selector('[data-firma-hoja-antigua]') is not None and 'ya no autoriza el periodo' in f_n, 'U9 Una firma antigua de Nómina por hoja se ve como «ya no autoriza el periodo»')
    errores += pg.errores; ctx.close()
    ctx, pg = abrir('admin'); periodo(pg, P1)
    pg.click(f'[data-rev-hoja="{H1}"]'); pg.wait_for_timeout(1800)
    ok(pg.query_selector('[data-firmar="rh"]') is not None and pg.query_selector('[data-firmar="nomina"]') is None, '+ RH (responsable designado) sí ve «Firmar como RH»')
    errores += pg.errores; ctx.close()

    print('== Procesar desde la pantalla (conservación) ==')
    sql(f"select public.inc_firmar_hoja('{H1}','rh')", 'admin')
    sql(f"select public.inc_firmar_periodo('{P1}', public.inc_firma_periodo_estado('{P1}')->'huella_actual'->>'total')", 'nomina')
    ctx, pg = abrir('nomina'); periodo(pg, P1)
    habil = not pg.is_disabled('#inc-r-proc')
    pg.click('#inc-r-proc'); pg.wait_for_timeout(2000)
    ok(habil and 'procesado' in texto(pg, '#inc-r-msg').lower() and pg.query_selector('#inc-r-proc') is None and 'Procesado' in texto(pg, '.inc-cab'),
       '+CONS-U3 Con firma vigente y RH firmado, el botón se habilita y el periodo se procesa', texto(pg, '#inc-r-msg'))
    ok('Firma de Nómina vigente' in texto(pg, '#inc-r-firma-per') and pg.query_selector('#inc-r-firmar-per') is None,
       '+CONS-U4 Periodo procesado: se ve la firma vigente y su historial, sin botón de firmar')
    errores += pg.errores; ctx.close()

    print('== U10 · Celular ==')
    ctx, pg = abrir('nomina', 390, 844); periodo(pg, P1)
    caja = pg.evaluate("() => { const e = document.getElementById('inc-r-firma-per'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.right, document.documentElement.clientWidth, document.documentElement.scrollWidth]; }")
    ok(caja and caja[0] >= 0 and caja[1] <= caja[2] + 1 and caja[3] <= caja[2] + 1, 'U10 Celular: el bloque de firma cabe, sin desplazamiento horizontal', str(caja))
    pg.screenshot(path=f'{OUT}/U10_celular.png', full_page=True)
    errores += pg.errores; ctx.close()
    ok(not errores, 'U11 Sin errores de JavaScript', '; '.join(errores)[:200])
    b.close()

print('== Red: ninguna conexión fuera del equipo ==')
sb_local = [r for r in RED if r[2] == f'{REF}.supabase.co']
ok(sb_local and all(r[0] == 'local' for r in sb_local), f'RED Las {len(sb_local)} peticiones dirigidas a la dirección de beehuman-pruebas se respondieron en local (base bhui); ninguna salió', str(len(sb_local)))
ok(not [r for r in RED if r[0] not in ('local', 'abortada', 'archivo_local')], 'RED Ninguna petición ni websocket se dejó pasar a internet',
   str(sorted({(r[0], r[2]) for r in RED if r[0] not in ('local', 'archivo_local')}))[:200])
ok(all(r[1] == 'file' for r in RED if r[0] == 'archivo_local'), 'RED Lo que no se intercepta son solo archivos locales (file://)')
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
