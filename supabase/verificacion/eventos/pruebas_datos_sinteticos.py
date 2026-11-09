"""Script de datos 20261109000300_adaptar_datos_sinteticos_idse (y su reversión)
sobre una base Postgres LOCAL y desechable (bhev), con una réplica sintética del
tenant «PILOTO SINTETICO 500». Nunca toca Supabase.
Uso: ./montar.sh && python3 pruebas_datos_sinteticos.py"""
import subprocess, json, sys, os

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
CADENA = ['20261104000000_eventos_laborales_idse', '20261104000100_relacion_principal_con_rp', '20261105000000_idse_bajas',
          '20261105000100_idse_modificaciones', '20261107000000_laboral_historial_tipo_email', '20261108000200_modificacion_salario_reglas',
          '20261109000000_fechas_hora_mexico', '20261109000200_idse_validadores_guia']
DAT = os.path.join(S, 'datos', '20261109000300_adaptar_datos_sinteticos_idse.sql')
DREV = os.path.join(S, 'datos', '20261109000300_reversion_adaptar_datos_sinteticos_idse.sql')
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
def archivo(f, cambios=()):
    t = open(f, encoding='utf-8').read()
    for a, b in cambios: t = t.replace(a, b)
    p = subprocess.run(PSQL, input=t, capture_output=True, text=True, env=ENV); return p.stdout + p.stderr

T, T2 = 'ca300000-0000-4000-8000-000000000001', 'ca300000-0000-4000-8000-000000000002'
U = {'admin': 'cb300000-0000-4000-8000-000000000001'}
E, RP = 'cc300000-0000-4000-8000-000000000001', 'cd300000-0000-4000-8000-000000000001'
CURPS = ['PAGA900101MDFLLD05', 'MOPE920303HDFRXD08', 'LOPE900202HDFPRN05', 'NARO880808MDFVSS02']
def dv(n):
    s = 0
    for i, ch in enumerate(n[:10]):
        d = int(ch) * (2 if i % 2 else 1); s += d // 10 + d % 10
    return str((10 - s % 10) % 10)
# 12 personas como el piloto: «PERSONA 00NN»; NSS 00000000NNN (inválidos salvo los que caen bien), algunos vacíos
personas = []
for n in range(1, 13):
    nss = '' if n % 4 == 0 else f'{n:011d}'
    if n == 5: nss = '0000000000' + dv('0000000000')     # uno válido de origen: se queda igual
    personas.append((f'ce300000-0000-4000-8000-{n:012d}', f'P500-{n:06d}', f'PERSONA {n:04d}', nss, CURPS[n % 4]))
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','PILOTO SINTETICO 500'),('{T2}','TENANT SINTETICO 7D6B');
insert into auth.users (id, email) values ('{U['admin']}','admin.sint@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U['admin']}','{T}','administrador');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA PILOTO');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RP}','{E}','{T}','Z9900000901');
""" + ''.join(f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, nss, curp, empresa_id) "
              f"values ('{pid}','{T}','{eid}','{nom} PILOTO SINTETICO','{nom}','PILOTO','SINTETICO',{repr(nss) if nss else 'null'},'{curp}','{E}');\n"
              for pid, eid, nom, nss, curp in personas) + \
    f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, nss) values ('ce300000-0000-4000-8000-999999999999','{T2}','OTRO-1','PRUEBA 7D6B 01','PRUEBA 01','7D6B','00000000001');"
o, e = sql(seed, replica=True)
if 'ERROR' in e: sys.exit(e)
for m in CADENA:
    s = archivo(os.path.join(S, 'pendiente', m + '.sql'))
    if 'ERROR' in s: sys.exit(m + ': ' + s[s.find('ERROR'):][:300])
# Dos personas con relación, alta pendiente en la bandeja y un archivo ya generado de otra (histórico)
for k in (0, 1):
    pid = personas[k][0]
    val(f"select public.laboral_registrar_ingreso('{pid}','{E}','{RP}','2026-11-02', null, 500, null, '1', '0', '0', '012', 'N{k}', null)", 'admin')
errores = lambda: val(f"select string_agg(nombre || ':' || array_to_string(errores, '/'), ' | ' order by nombre) from public.idse_validar('{RP}','08')", 'admin')
E0 = errores()
print('    bandeja antes:', E0[:200])
ok('NSS inválido' in E0 and 'Nombre con dígitos' in E0, 'antes: el piloto queda bloqueado en la bandeja (NSS y nombre)')
inv = sum(1 for _, _, _, nss, _ in personas if nss and dv(nss) != nss[10])
print(f'    plan esperado: {inv} NSS, 12 nombres')
huellas = lambda: val("select md5(string_agg(t, '|')) from (select md5(coalesce(string_agg(to_jsonb(x)::text,'' order by x.id),'')) t from public.relaciones_laborales x "
                      "union all select md5(coalesce(string_agg(to_jsonb(x)::text,'' order by x.id),'')) from public.eventos_laborales x "
                      "union all select md5(coalesce(string_agg(to_jsonb(x)::text,'' order by x.id),'')) from public.idse_movimientos x "
                      "union all select md5(coalesce(string_agg(to_jsonb(x)::text,'' order by x.id),'')) from public.idse_archivos x "
                      "union all select md5(coalesce(string_agg(x.id||x.empleado_id||x.tenant_id,'' order by x.id),'')) from public.personal x) z")
datos = lambda: val(f"select md5(string_agg(coalesce(nss,'-')||nombres||nombre_completo, '|' order by id)) from public.personal where tenant_id = '{T}'")
otro = lambda: val(f"select nss||'|'||nombres from public.personal where tenant_id = '{T2}'")
H0, D0, O0 = huellas(), datos(), otro()

print('--- Guardas')
s = archivo(DAT)
ok('se esperaban 300 y 500' in s and datos() == D0, 'con conteos distintos a los del precheck no cambia nada', s[s.find('ERROR'):][:120])
CAMBIOS = [('c_nss      constant int := 300', f'c_nss      constant int := {inv}'), ('c_nombres  constant int := 500', 'c_nombres  constant int := 12')]

print('--- Adaptación')
s = archivo(DAT, CAMBIOS)
ok('ERROR' not in s, 'se aplica sin errores', s[s.find('ERROR'):][:200])
filas = [l.split('|') for l in sql(f"select empleado_id||'|'||coalesce(nss,'')||'|'||nombres||'|'||nombre_completo from public.personal where tenant_id = '{T}' order by empleado_id")[0].splitlines()]
print('    ', filas[0], filas[4], filas[3])
ok(all(not f[1] or (len(f[1]) == 11 and dv(f[1]) == f[1][10]) for f in filas), 'todos los NSS no vacíos tienen dígito verificador correcto')
ok(len({f[1] for f in filas if f[1]}) == sum(1 for f in filas if f[1]), 'los NSS son únicos')
ok(sum(1 for f in filas if not f[1]) == 3, 'los NSS vacíos siguen vacíos (3)')
ok(next(f for f in filas if f[0] == 'P500-000005')[1] == '0000000000' + dv('0000000000'), 'el NSS que ya era válido no cambia')
ok(next(f for f in filas if f[0] == 'P500-000007')[1] == '9900000007' + dv('9900000007'), 'NSS nuevo = 9900 + número del empleado + dígito verificador', next(f for f in filas if f[0] == 'P500-000007')[1])
ok(all(not any(c.isdigit() for c in f[2] + f[3]) for f in filas) and next(f for f in filas if f[0] == 'P500-000007')[2] == 'PERSONA AAAH',
   'nombres sin dígitos: «PERSONA 0007» → «PERSONA AAAH» (también en nombre completo)')
ok(len({f[3] for f in filas}) == len(filas), 'sin nombres duplicados')
ok(huellas() == H0, 'no cambian relaciones, eventos, movimientos ni archivos IDSE, ni ids/empleado_id/tenant de personas')
ok(otro() == O0, 'el otro tenant sintético no se toca')
n_mov = val("select count(*) from public.movimientos where usuario = 'sistema · adaptación datos sintéticos IDSE 20261109'")
ok(n_mov == str(inv + 12 + 12), 'una fila en Movimientos por campo cambiado, con valor anterior y nuevo', n_mov)
ok(val("select count(*) from respaldo.datos_sinteticos_idse_20261109") == '12', 'respaldo con los valores anteriores de las 12 personas')
E1 = errores()
ok('NSS inválido' not in E1 and 'Nombre con dígitos' not in E1, 'después: la bandeja ya no los bloquea', E1[:160])
ok('ya se aplicó' in archivo(DAT, CAMBIOS), 'una segunda ejecución se rechaza')

print('--- Reversión')
s = archivo(DREV)
ok('ERROR' not in s and datos() == D0 and huellas() == H0, 'la reversión devuelve exactamente los valores anteriores', s[s.find('ERROR'):][:150])
ok(val("select count(*) from public.movimientos where usuario like 'sistema · %adaptación datos sintéticos IDSE 20261109'") == str(2 * (inv + 24)), 'la reversión deja constancia en Movimientos y no borra la traza')
s = archivo(DAT, CAMBIOS)
ok('ERROR' not in s and datos() != D0, 'se puede volver a aplicar', s[s.find('ERROR'):][:150])
sql(f"update public.personal set nombres = 'EDITADO A MANO' where id = '{personas[2][0]}'", replica=True)
s = archivo(DREV)
ok('cambió después de la adaptación' in s, 'guarda: si alguien editó un dato después, la reversión no se ejecuta')

ok(all(b for _, b in res), f'TOTAL: {sum(1 for _, b in res if b)}/{len(res)} pruebas OK')
sys.exit(0 if all(b for _, b in res) else 1)
