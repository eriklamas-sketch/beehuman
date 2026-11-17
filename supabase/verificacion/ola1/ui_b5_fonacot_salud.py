"""B5 · Ficha sin «Salud» (17-nov-2026) · prueba de PANTALLA del guardado real de la ficha, con datos FICTICIOS.
  H1 Se fija un valor conocido en personal.restricciones_salud (ADELA PALACIOS GALVAN).
  H2 Como Administrador se abre su ficha en la aplicación (index.html real, supabase-js real).
  H3 Se modifica y se guarda OTRO campo (teléfono de emergencia) con «Guardar cambios».
  H4 Se consulta la base: el teléfono cambió (el guardado ocurrió) y restricciones_salud conserva EXACTAMENTE el valor.
  Además: la petición que envía la pantalla no incluye restricciones_salud; la ficha no muestra «Salud»; sin errores JS.
  Control (mutación): la misma prueba contra una copia de index.html cuya ficha volviera a enviar restricciones_salud ''
  debe FALLAR (demuestra que la prueba detecta la pérdida del dato).

Base: Postgres local (puerto 55432, base bhui = todas las migraciones de integracion/app + semilla_ui.sql).
Como PostgREST no está disponible en este entorno, las peticiones /rest/v1 del navegador las atiende un traductor
mínimo (más abajo) que ejecuta el SQL equivalente COMO EL USUARIO (rol authenticated + claims del JWT), es decir,
con las mismas políticas RLS y permisos. El PATCH de la ficha se aplica con las claves exactas que envía la pantalla,
igual que PostgREST: solo se actualizan las columnas presentes en el cuerpo.
Uso: SUPABASE_JS=<ruta a supabase.js umd> python3 ui_b5_fonacot_salud.py <index.html> <carpeta_capturas>"""
import sys, os, json, re, time, uuid
from urllib.parse import urlparse, parse_qsl
import psycopg2
from playwright.sync_api import sync_playwright

HTML, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
SUPABASE_JS = os.environ['SUPABASE_JS']
DB = os.environ.get('DB', 'bhui')
REF = 'sflvpgkmtaxzogpgetxn'
U = {'admin': '0b000000-0000-4000-8000-000000000001'}
ADELA = '0a100000-0000-4000-8000-000000000011'
VALOR = 'ALERGIA SINTETICA A LA PENICILINA · NO CARGAR MAS DE 10 KG'   # texto ficticio
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*',
        'access-control-expose-headers': 'content-range, content-profile'}

def conectar(): return psycopg2.connect(dbname=DB, host='/tmp', port=55432, user='postgres')
def sql(q, args=None):
    c = conectar()
    try:
        cur = c.cursor(); cur.execute(q, args); r = cur.fetchone() if cur.description else None; c.commit(); return r[0] if r else None
    finally: c.close()

# ---------------- traductor mínimo PostgREST → SQL (solo lo que usa esta pantalla) ----------------
qi = lambda s: '"' + s.replace('"', '""') + '"'
def partir(s, sep=','):
    out, prof, cur = [], 0, ''
    for ch in s:
        if ch == '(': prof += 1
        elif ch == ')': prof -= 1
        if ch == sep and prof == 0: out.append(cur); cur = ''
        else: cur += ch
    if cur: out.append(cur)
    return out
def fks(cur, a, b):
    """FK de la tabla a hacia b: lista de (constraint, columna_en_a, columna_en_b)."""
    cur.execute("""select c.conname, aa.attname, ab.attname from pg_constraint c
      join pg_attribute aa on aa.attrelid=c.conrelid and aa.attnum=c.conkey[1]
      join pg_attribute ab on ab.attrelid=c.confrelid and ab.attnum=c.confkey[1]
      where c.contype='f' and c.conrelid=('public.'||%s)::regclass and c.confrelid=('public.'||%s)::regclass""", (a, b))
    return cur.fetchall()
def columnas_select(cur, tabla, alias, sel, n=[0]):
    cols = []
    for it in partir(sel or '*'):
        it = it.strip()
        m = re.match(r'^(?:(\w+):)?(\w+)(?:!(\w+))?\((.*)\)$', it, re.S)
        if m:
            nombre, rel, pista, sub = m.group(1) or m.group(2), m.group(2), m.group(3), m.group(4)
            n[0] += 1; a2 = f't{n[0]}'
            dentro = columnas_select(cur, rel, a2, sub)
            ida = [f for f in fks(cur, tabla, rel) if not pista or pista in (f[0], f[1])]
            if ida:
                f = ida[0]
                cols.append(f"(select row_to_json(x) from (select {dentro} from public.{qi(rel)} {a2} where {a2}.{qi(f[2])} = {alias}.{qi(f[1])}) x) as {qi(nombre)}")
            else:
                vuelta = [f for f in fks(cur, rel, tabla) if not pista or pista in (f[0], f[1])]
                if not vuelta: raise RuntimeError(f'sin relación {tabla} → {rel}')
                f = vuelta[0]
                cols.append(f"(select coalesce(json_agg(x), '[]') from (select {dentro} from public.{qi(rel)} {a2} where {a2}.{qi(f[1])} = {alias}.{qi(f[2])}) x) as {qi(nombre)}")
            continue
        if it == '*': cols.append(f'{alias}.*'); continue
        m = re.match(r'^(?:(\w+):)?(\w+)(?:::(\w+))?$', it)
        if not m: raise RuntimeError('select no soportado: ' + it)
        cols.append(f"{alias}.{qi(m.group(2))}" + (f'::{m.group(3)}' if m.group(3) else '') + f" as {qi(m.group(1) or m.group(2))}")
    return ', '.join(cols)
OPS = {'eq': '=', 'neq': '<>', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<=', 'like': 'like', 'ilike': 'ilike'}
def condicion(alias, col, expr, args):
    neg = expr.startswith('not.'); expr = expr[4:] if neg else expr
    op, _, v = expr.partition('.')
    if op == 'is': c = f"{alias}.{qi(col)} is {({'null': 'null', 'true': 'true', 'false': 'false'})[v]}"
    elif op == 'in':
        vals = [x.strip().strip('"') for x in partir(v.strip('()'))]
        c = f"{alias}.{qi(col)} in ({', '.join(['%s'] * len(vals))})" if vals else 'false'; args += vals
    elif op in OPS:
        c = f"{alias}.{qi(col)} {OPS[op]} %s"; args.append(v.replace('*', '%') if op in ('like', 'ilike') else v)
    else: raise RuntimeError('operador no soportado: ' + op)
    return f'not ({c})' if neg else c
def donde(alias, params, args):
    conds = []
    for k, v in params:
        if k in ('select', 'order', 'limit', 'offset', 'columns', 'on_conflict'): continue
        if k == 'or':
            partes = []
            for p in partir(v.strip('()')):
                col, _, ex = p.partition('.'); partes.append(condicion(alias, col, ex, args))
            conds.append('(' + ' or '.join(partes) + ')'); continue
        if '.' in k: raise RuntimeError('filtro en recurso incrustado no soportado: ' + k)
        conds.append(condicion(alias, k, v, args))
    return (' where ' + ' and '.join(conds)) if conds else ''
def orden(alias, v):
    if not v: return ''
    out = []
    for p in v.split(','):
        t = p.split('.'); s = f"{alias}.{qi(t[0])}"
        if 'desc' in t[1:]: s += ' desc'
        if 'nullsfirst' in t[1:]: s += ' nulls first'
        if 'nullslast' in t[1:]: s += ' nulls last'
        out.append(s)
    return ' order by ' + ', '.join(out)
def ejecutar(quien, metodo, tabla, params, cuerpo, headers):
    c = conectar(); cur = c.cursor(); extra = {}
    try:
        cur.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps({'sub': U[quien], 'role': 'authenticated'}),))
        cur.execute('set local role authenticated')
        p = dict(params); args = []
        if tabla.startswith('rpc/'):
            fn = tabla[4:]
            cur.execute("""select p.proargnames, array(select format_type(t, null) from unnest(p.proargtypes) t), p.proretset,
                             (select typtype from pg_type where oid=p.prorettype) from pg_proc p
                           where p.proname=%s and p.pronamespace='public'::regnamespace""", (fn,))
            nombres, tipos, conj, tt = cur.fetchone()
            datos = cuerpo or {}; asig = []
            for nom, tip in zip(nombres or [], tipos):
                if nom in datos:
                    v = datos[nom]; asig.append(f'{qi(nom)} := %s::{tip}')
                    args.append(json.dumps(v) if tip in ('jsonb', 'json') else (None if v is None else ('{' + ','.join(map(str, v)) + '}' if isinstance(v, list) else str(v))))
            llamada = f"public.{qi(fn)}({', '.join(asig)})"
            if conj or tt in ('c', 'p'):
                cur.execute(f"select coalesce(json_agg(r), '[]') from (select * from {llamada} r) r", args); res = cur.fetchone()[0]
                if not conj and isinstance(res, list): res = res[0] if res else None
            else:
                cur.execute(f"select to_jsonb({llamada})", args); res = cur.fetchone()[0]
        elif metodo in ('GET', 'HEAD'):
            sel = columnas_select(cur, tabla, 't0', p.get('select'))
            w = donde('t0', params, args)
            lim = (f" limit {int(p['limit'])}" if 'limit' in p else '') + (f" offset {int(p['offset'])}" if 'offset' in p else '')
            rango = headers.get('range')
            if rango:
                a, b = rango.split('-'); lim = f" limit {int(b) - int(a) + 1} offset {int(a)}"
            cur.execute(f"select coalesce(json_agg(x), '[]') from (select {sel} from public.{qi(tabla)} t0{w}{orden('t0', p.get('order'))}{lim}) x", args)
            res = cur.fetchone()[0]
            if 'count=exact' in headers.get('prefer', ''):
                a2 = []; cur.execute(f"select count(*) from public.{qi(tabla)} t0{donde('t0', params, a2)}", a2)
                extra['content-range'] = f"0-{max(len(res) - 1, 0)}/{cur.fetchone()[0]}"
        elif metodo == 'PATCH':
            claves = list(cuerpo.keys())
            sets = ', '.join(f"{qi(k)} = (json_populate_record(null::public.{qi(tabla)}, %s::json)).{qi(k)}" for k in claves)
            args = [json.dumps(cuerpo)] * len(claves)
            w = donde('t0', params, args)
            cur.execute(f"with x as (update public.{qi(tabla)} t0 set {sets}{w} returning t0.*) "
                        f"select coalesce(json_agg(y), '[]') from (select {columnas_select(cur, tabla, 'x', p.get('select'))} from x) y", args)
            res = cur.fetchone()[0]
        elif metodo == 'POST':
            filas = cuerpo if isinstance(cuerpo, list) else [cuerpo]
            claves = sorted({k for f in filas for k in f})
            cl = ', '.join(qi(k) for k in claves)
            cur.execute(f"with x as (insert into public.{qi(tabla)} ({cl}) select {cl} from json_populate_recordset(null::public.{qi(tabla)}, %s::json) returning *) "
                        f"select coalesce(json_agg(y), '[]') from (select {columnas_select(cur, tabla, 'x', p.get('select'))} from x) y", [json.dumps(filas)])
            res = cur.fetchone()[0]
        elif metodo == 'DELETE':
            w = donde('t0', params, args)
            cur.execute(f"with x as (delete from public.{qi(tabla)} t0{w} returning t0.*) select coalesce(json_agg(x), '[]') from x", args)
            res = cur.fetchone()[0]
        else: raise RuntimeError('método no soportado: ' + metodo)
        c.commit()
        if 'vnd.pgrst.object' in headers.get('accept', ''):
            if not isinstance(res, list) or len(res) != 1:
                return 406, {'code': 'PGRST116', 'message': 'JSON object requested, multiple (or no) rows returned', 'details': None, 'hint': None}, extra
            res = res[0]
        if metodo in ('PATCH', 'POST', 'DELETE') and not tabla.startswith('rpc/') and 'return=representation' not in headers.get('prefer', ''):
            return 204, None, extra
        return 200, res, extra
    except psycopg2.Error as e:
        c.rollback()
        return (403 if e.pgcode == '42501' else 400), {'code': e.pgcode, 'message': (e.diag.message_primary or str(e)), 'details': e.diag.message_detail, 'hint': e.diag.message_hint}, extra
    finally: c.close()

peticiones, no_soportadas = [], []
def ruta_para(quien):
    def manejar(route):
        req = route.request; u = urlparse(req.url)
        if 'cdn.jsdelivr.net' in req.url and 'supabase-js' in req.url: return route.fulfill(path=SUPABASE_JS, content_type='application/javascript')
        if u.netloc == 'fonts.googleapis.com': return route.fulfill(body='', content_type='text/css')
        if u.netloc == f'{REF}.supabase.co':
            if req.method == 'OPTIONS': return route.fulfill(status=200, headers=CORS)
            if u.path.startswith('/auth/v1/user'):
                return route.fulfill(json={'id': U[quien], 'aud': 'authenticated', 'role': 'authenticated', 'email': quien + '@demo.invalid'}, headers=CORS)
            if u.path.startswith('/rest/v1/'):
                tabla = u.path[len('/rest/v1/'):]
                cuerpo = json.loads(req.post_data) if req.post_data else None
                peticiones.append((req.method, tabla, u.query, cuerpo))
                try: st, res, extra = ejecutar(quien, req.method, tabla, parse_qsl(u.query, keep_blank_values=True), cuerpo, {k.lower(): v for k, v in req.headers.items()})
                except Exception as e:
                    no_soportadas.append(f'{req.method} {tabla}?{u.query}: {e}'); st, res, extra = 400, {'code': 'LOCAL', 'message': str(e)}, {}
                h = dict(CORS); h.update(extra)
                if st == 204: return route.fulfill(status=204, headers=h, body='')
                return route.fulfill(status=st, headers=h, body=json.dumps(res), content_type='application/json')
            return route.fulfill(json={}, headers=CORS)
        if u.scheme in ('http', 'https'): return route.abort()
        return route.continue_()
    return manejar

res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

import base64
def token(sub):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b'=').decode()
    return b({'alg': 'HS256', 'typ': 'JWT'}) + '.' + b({'sub': sub, 'role': 'authenticated', 'aud': 'authenticated', 'exp': int(time.time()) + 86400}) + '.local'

def correr(html, etiqueta):
    """Recorrido completo; devuelve (valor_salud_final, telefono_final, cuerpo_patch, errores_js, ficha_muestra_salud)."""
    tel = '55' + str(int(time.time() * 1000))[-8:]
    sql("update public.personal set restricciones_salud = %s, contacto_emergencia_telefono = '5500000000' where id = %s", (VALOR, ADELA))
    peticiones.clear()
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1440, 'height': 950})
        sesion = {'access_token': token(U['admin']), 'token_type': 'bearer', 'expires_in': 86400, 'expires_at': int(time.time()) + 86400,
                  'refresh_token': 'x', 'user': {'id': U['admin'], 'aud': 'authenticated', 'role': 'authenticated'}}
        ctx.add_init_script(f"localStorage.setItem('sb-{REF}-auth-token', {json.dumps(json.dumps(sesion))});")
        ctx.route('**/*', ruta_para('admin'))
        pg = ctx.new_page(); errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.on('dialog', lambda d: d.accept())
        pg.goto('file://' + os.path.abspath(html))
        pg.wait_for_selector('#app-content', state='visible', timeout=20000); pg.wait_for_timeout(1500)
        pg.click('nav.tabs button[data-tab="lista"]'); pg.wait_for_timeout(700)
        pg.fill('#buscar-personal', 'ADELA PALACIOS GALVAN'); pg.wait_for_timeout(400)
        pg.click('#tabla-personal a:has-text("ADELA PALACIOS GALVAN")'); pg.wait_for_timeout(1500)
        muestra_salud = pg.evaluate("""() => !!document.querySelector('#d-restricciones') ||
            [...document.querySelectorAll('#modal-overlay h3')].some(h => h.textContent.trim() === 'Salud')""")
        pg.click('[data-detail-tab="prestaciones"]'); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}/{etiqueta}_1_ficha_prestaciones.png', full_page=True)
        pg.click('[data-detail-tab="contacto"]'); pg.wait_for_timeout(300)
        pg.fill('#d-emerg-telefono', tel)
        pg.click('#btn-guardar-detalle'); pg.wait_for_timeout(2000)
        pg.screenshot(path=f'{OUT}/{etiqueta}_2_guardado.png', full_page=True)
        toast = pg.inner_text('#toast-detalle') if pg.query_selector('#toast-detalle') else ''
        b.close()
    patch = [c for (m, t, q, c) in peticiones if m == 'PATCH' and t == 'personal' and ADELA in q]
    return (sql("select restricciones_salud from public.personal where id = %s", (ADELA,)),
            sql("select contacto_emergencia_telefono from public.personal where id = %s", (ADELA,)), tel,
            patch[-1] if patch else None, errores, muestra_salud, toast)

# ================= Prueba con el index.html a revisar =================
print('== H Guardado real de la ficha: restricciones_salud se conserva ==')
salud, tel_bd, tel, cuerpo, errores, muestra, toast = correr(HTML, 'ficha')
ok(cuerpo is not None, 'H2/H3 La pantalla envió el guardado de la ficha (PATCH personal de ADELA)', f'{len(cuerpo or {})} campos')
ok(tel_bd == tel, 'H4 El otro campo modificado (teléfono de emergencia) quedó guardado en la base', f'{tel_bd} · aviso: {toast[:60]}')
ok(cuerpo is not None and 'restricciones_salud' not in cuerpo, 'H3 La petición de la ficha no incluye restricciones_salud')
ok(salud == VALOR, 'H4 restricciones_salud conserva EXACTAMENTE el valor original después de guardar', repr(salud))
ok(not muestra, 'H2 La ficha no muestra la sección «Salud» ni el campo «Restricciones de salud»')
ok(not errores, 'Sin errores de JavaScript', str(errores[:2]))
ok(not no_soportadas, 'Todas las peticiones de la pantalla fueron atendidas por el traductor local', '; '.join(no_soportadas[:3]))

# ================= Control: mutación que volvería a enviar el campo vacío =================
print('== Control: copia de index.html cuya ficha enviara restricciones_salud vacío ==')
fuente = open(HTML, encoding='utf-8').read()
marca = "    // La ficha ya no muestra «Restricciones de salud»: no se envía, así el valor guardado se conserva.\n"
ok(fuente.count(marca) == 1, 'Control: se localizó el punto exacto del objeto que envía la ficha')
mutante = os.path.join(OUT, 'index_mutante_control.html')
open(mutante, 'w', encoding='utf-8').write(fuente.replace(marca, marca + "    restricciones_salud: '',\n"))
salud_m, tel_m, tel2, cuerpo_m, err_m, _, _ = correr(mutante, 'control')
ok(tel_m == tel2 and cuerpo_m is not None and 'restricciones_salud' in cuerpo_m, 'Control: la copia mutante sí guardó y sí envió restricciones_salud')
ok(salud_m != VALOR, 'Control: con la mutación la prueba DETECTA la pérdida del dato (H4 fallaría)', repr(salud_m))
os.remove(mutante)
sql("update public.personal set restricciones_salud = %s where id = %s", (VALOR, ADELA))

total = len(res); malos = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malos)} de {total} OK')
sys.exit(1 if malos else 0)
