"""Reglas de la modificación de salario (07) del 8-nov-2026, en una base Postgres
LOCAL y desechable (bhev, puerto 55432). Nunca toca Supabase.
Uso: ./montar.sh && python3 pruebas_modificacion_salario.py"""
import subprocess, json, sys, hashlib, os

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
PREVIAS = ['20261104000000_eventos_laborales_idse', '20261104000100_relacion_principal_con_rp', '20261105000000_idse_bajas',
           '20261105000100_idse_modificaciones', '20261107000000_laboral_historial_tipo_email']
MIG = os.path.join(S, 'pendiente', '20261108000200_modificacion_salario_reglas.sql')
REV = os.path.join(S, 'reversion', '20261108000200_reversion_modificacion_salario_reglas.sql')
HUELLA = os.path.join(S, 'verificacion', 'huella_esquema.sql')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhev']
ENV = dict(os.environ, PGOPTIONS='-c TimeZone=UTC')
res = []

def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True, env=ENV)
    return '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET')), p.stderr.strip()
def val(q, user=None):
    out, err = sql(q, user)
    if 'ERROR' in err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def falla_con(q, user, texto, nombre):
    out, err = sql(q, user)
    ok('ERROR' in err and texto.lower() in err.lower(), nombre, (err.split('\n')[0][:190] if err else 'NO FALLÓ: ' + out[:80]))
def archivo(f):
    p = subprocess.run(PSQL + ['-f', f], capture_output=True, text=True, env=ENV); return p.stdout + p.stderr
def huella():
    return hashlib.sha256(subprocess.run(PSQL + ['-f', HUELLA], capture_output=True, text=True, env=ENV).stdout.encode()).hexdigest()[:16]

T = 'ca000000-0000-4000-8000-000000000001'
U = {'admin': 'cb000000-0000-4000-8000-000000000001', 'nomina': 'cb000000-0000-4000-8000-000000000002'}
E, RP, RPF = 'cc000000-0000-4000-8000-000000000001', 'cd000000-0000-4000-8000-000000000001', 'cd000000-0000-4000-8000-000000000002'
P = {k: f'ce000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['A', 'B', 'C', 'D', 'F'], 1)}
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT SALARIO');
insert into auth.users (id, email) values ('{U['admin']}','admin@beehuman.invalid'),('{U['nomina']}','nomina@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U['admin']}','{T}','administrador'),('{U['nomina']}','{T}','nomina');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA SALARIO');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RP}','{E}','{T}','Y5555555101'),('{RPF}','{E}','{T}','Y5555555102');
""" + ''.join(f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, empresa_id) values ('{P[k]}','{T}','SAL-{k}','PERSONA SALARIO {k}','PERSONA','{k}','{E}');\n" for k in P)

o, e = sql(seed, replica=True)
if 'ERROR' in e: sys.exit(e)
for m in PREVIAS:
    s = archivo(os.path.join(S, 'pendiente', m + '.sql'))
    if 'ERROR' in s: sys.exit(m + ': ' + s[s.find('ERROR'):][:300])
sql(f"update public.empresas_registros_patronales set zona_salario_minimo = 'zlfn' where id = '{RPF}'", replica=True)
rel = {}
for k, (rp, sbc) in {'A': (RP, 1250), 'B': (RP, 'null'), 'C': (RP, 2000), 'D': (RP, 900), 'F': (RPF, 700)}.items():
    rel[k] = val(f"select public.laboral_registrar_ingreso('{P[k]}','{E}','{rp}','2025-12-01', null, {sbc})", 'admin')
    rel[k] = val(f"select id from public.relaciones_laborales where personal_id = '{P[k]}'")
sql(f"update public.relaciones_laborales set sbc = null, sdi = null where id = '{rel['B']}'", replica=True)  # dato migrado sin SBC

huella_datos = lambda: val("select md5(coalesce(string_agg(to_jsonb(e)::text, '' order by id),'')) from public.eventos_laborales e") + '|' + \
    val("select md5(coalesce(string_agg(to_jsonb(m)::text, '' order by id),'')) from public.idse_movimientos m")
D0, H0 = huella_datos(), huella()
n_ev0 = val("select count(*) from public.eventos_laborales")

print('--- Migración')
s = archivo(MIG)
ok('ERROR' not in s, 'aplica sin errores', s[s.find('ERROR'):][:200])
ok(huella_datos() == D0, 'no modifica eventos ni movimientos IDSE existentes')
ok('ya está aplicada' in archivo(MIG), 'una segunda aplicación se rechaza')
H1 = huella()

print('--- D3: disminución del SBC')
falla_con(f"select public.laboral_modificar_salario('{rel['A']}','2026-03-01', 1100)", 'nomina', 'es menor que el vigente ($1,250.00)', 'baja de SBC sin motivo: rechazada, con importes formateados')
falla_con(f"select public.laboral_modificar_salario('{rel['A']}','2026-03-01', 1100, null, null, 'abc')", 'nomina', 'justificación', 'motivo de menos de 5 caracteres: rechazado')
out, err = sql(f"select public.laboral_modificar_salario('{rel['A']}','2026-03-01', 1100, null, null, 'Convenio de reducción de jornada firmado')", 'nomina')
print('    detalle:', val(f"select motivo||'|'||(valores_anteriores->>'sbc')||'→'||(valores_nuevos->>'sbc') from public.eventos_laborales where relacion_laboral_id = '{rel['A']}' and tipo = 'modificacion_salario'"))
ok('ERROR' not in err and val(f"select motivo||'|'||(valores_anteriores->>'sbc')||'→'||(valores_nuevos->>'sbc') from public.eventos_laborales where relacion_laboral_id = '{rel['A']}' and tipo = 'modificacion_salario'")
   == 'Convenio de reducción de jornada firmado|1250.00→1100', 'con justificación se registra; el motivo queda en el evento', err[:150])
ok(val(f"select m.tipo_movimiento||'/'||m.estado||'/'||m.sbc from public.idse_movimientos m join public.eventos_laborales e on e.id = m.evento_id where e.relacion_laboral_id = '{rel['A']}' and e.tipo = 'modificacion_salario' and e.fecha_efectiva = '2026-03-01'") == '07/pendiente/1100.00',
   'el 07 queda pendiente en la bandeja (no se genera archivo)')
out, err = sql(f"select public.laboral_modificar_salario('{rel['A']}','2026-04-01', 1300)", 'nomina')
ok('ERROR' not in err, 'un aumento no exige motivo', err[:150])

print('--- Sin SBC vigente (dato migrado)')
out, err = sql(f"select public.laboral_modificar_salario('{rel['B']}','2026-03-01', 500)", 'nomina')
ant = val(f"select coalesce(valores_anteriores->>'sbc','(no registrado)')||'→'||(valores_nuevos->>'sbc') from public.eventos_laborales where relacion_laboral_id = '{rel['B']}' and tipo = 'modificacion_salario'")
ok('ERROR' not in err and ant == '(no registrado)→500', 'se registra sin inventar el anterior y sin pedir motivo', ant)

print('--- D2: tope de 25 UMA a la fecha efectiva')
falla_con(f"select public.laboral_modificar_salario('{rel['C']}','2026-01-15', 2900)", 'nomina', 'rebasa el tope de 25 UMA ($2,828.50) vigente al 15/01/2026', 'enero 2026: UMA 113.14 → tope $2,828.50; $2,900 rechazado')
out, err = sql(f"select public.laboral_modificar_salario('{rel['C']}','2026-02-01', 2900)", 'nomina')
ok('ERROR' not in err, 'febrero 2026: UMA 117.31 → tope $2,932.75; $2,900 aceptado', err[:150])
falla_con(f"select public.laboral_modificar_salario('{rel['C']}','2026-03-01', 2932.76)", 'nomina', 'rebasa el tope', 'un centavo arriba del tope: rechazado')
out, err = sql(f"select public.laboral_modificar_salario('{rel['C']}','2026-03-01', 2932.75, 3500)", 'nomina')
ok('ERROR' not in err and val(f"select sbc||'/'||sdi from public.relaciones_laborales where id = '{rel['C']}'") == '2932.75/3500.00',
   '«Usar el tope»: SBC = tope y el SDI real se conserva aparte (no se mezclan)', val(f"select sbc||'/'||sdi from public.relaciones_laborales where id = '{rel['C']}'"))
_, err = sql(f"select public.laboral_modificar_salario('{rel['C']}','2026-05-01', 9999)", 'nomina')
ok('sbc_tope' in err, 'el rechazo del tope lleva la pista «sbc_tope» para la pantalla', err.split('\n')[-1][:80])

print('--- D4: salario mínimo')
falla_con(f"select public.laboral_modificar_salario('{rel['D']}','2026-03-01', 300, null, null, 'Ajuste por jornada reducida')", 'nomina',
          'menor al salario mínimo general ($315.04)', 'debajo del mínimo general 2026 ($315.04): rechazado aun con motivo')
falla_con(f"select public.laboral_modificar_salario('{rel['F']}','2026-03-01', 420, null, null, 'Prueba del piso de la frontera')", 'nomina', 'zona libre de la frontera norte ($440.87)', 'RP de la frontera norte: el piso es el mínimo de la ZLFN')
_, err = sql(f"select public.laboral_modificar_salario('{rel['D']}','2026-03-01', 300, null, null, 'Ajuste por jornada reducida')", 'nomina')
ok('jornada o semana reducida' in err and 'sbc_minimo' in err, 'el mensaje explica que la jornada reducida también se ajusta al mínimo')

print('--- Reversión')
n_ev = val("select count(*) from public.eventos_laborales")
D1 = huella_datos()
s = archivo(REV)
ok('ERROR' not in s, 'la reversión se aplica sin errores', s[s.find('ERROR'):][:150])
ok(huella() == H0, 'el esquema vuelve a ser idéntico al de antes de la migración')
ok(huella_datos() == D1 and val("select count(*) from public.eventos_laborales") == n_ev, 'los movimientos registrados después se conservan íntegros')
s = archivo(MIG)
ok('ERROR' not in s and huella() == H1, 'se puede volver a aplicar y queda igual')

ok(all(b for _, b in res), f'TOTAL: {sum(1 for _, b in res if b)}/{len(res)} pruebas OK')
sys.exit(0 if all(b for _, b in res) else 1)
