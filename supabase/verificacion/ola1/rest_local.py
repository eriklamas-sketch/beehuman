"""Traductor mínimo PostgREST → SQL para las pruebas de pantalla locales (sin PostgREST en este entorno).
Ejecuta cada petición /rest/v1 COMO EL USUARIO (rol authenticated + claims del JWT), con las mismas políticas RLS.
Igual que PostgREST, un PATCH actualiza solo las claves del cuerpo. Copia del traductor de ui_b5_fonacot_salud.py.
No es una prueba de integración con PostgREST real."""
import json, re
import psycopg2

DB = 'bhui'
U = {}
def conectar(): return psycopg2.connect(dbname=DB, host='/tmp', port=55432, user='postgres')

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

