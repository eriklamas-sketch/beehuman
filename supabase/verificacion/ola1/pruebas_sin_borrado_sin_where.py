"""Regresión B1.1b: ninguna función de public ejecuta DELETE o UPDATE sin WHERE.

En Supabase, el rol authenticator carga la extensión safeupdate, que rechaza
esas sentencias («DELETE requires a WHERE clause»), también dentro de funciones
llamadas desde la aplicación. La base local de pruebas no carga safeupdate, así
que este análisis estático de las definiciones es la protección: falla si
aparece cualquier sentencia de ese tipo.
Uso: DB=bh python3 pruebas_sin_borrado_sin_where.py"""
import subprocess, os, sys

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-F', '\t', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
CONSULTA = r"""
with defs as (
  select p.oid::regprocedure::text fn, regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g') d
    from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind in ('f','p')
), sent as (
  select fn, btrim(regexp_replace(s, '\s+', ' ', 'g')) s from defs, regexp_split_to_table(d, ';') s
)
select fn, left(s, 140) from sent
 where s ~* '^(.*\m(begin|loop|then|else|\$\$)\M\s*)?(delete|update)\M'
   and s !~* '\mwhere\M' and s !~* 'on conflict'
 order by 1;
"""
res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

p = subprocess.run(PSQL, input=CONSULTA, capture_output=True, text=True)
if p.returncode: print(p.stderr); sys.exit(1)
hallazgos = [l for l in p.stdout.splitlines() if l.strip()]
nfun = subprocess.run(PSQL, input="select count(*) from pg_proc where pronamespace='public'::regnamespace and prokind in ('f','p');", capture_output=True, text=True).stdout.strip()
ok(int(nfun) > 50, 'Se revisaron las funciones de public', f'{nfun} funciones')
ok(not hallazgos, 'Ninguna función tiene DELETE o UPDATE sin WHERE (safeupdate de Supabase)', '; '.join(hallazgos[:5]))
# control del propio detector: debe encontrar un DELETE sin WHERE en una función de muestra
q = """begin; create function public._bh_muestra_sin_where() returns void language plpgsql as $f$ begin delete from _x; end $f$;
""" + CONSULTA.replace('order by 1;', "and fn like '_bh_muestra%' order by 1;") + "rollback;"
p2 = subprocess.run(PSQL, input=q, capture_output=True, text=True)
ok('_bh_muestra_sin_where' in p2.stdout, 'Control: el detector sí encuentra un DELETE sin WHERE en una función de muestra', p2.stdout.strip()[:80])
total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
sys.exit(1 if malas else 0)
