"""Migración 20261109000200_idse_validadores_guia (NSS con dígito verificador,
nombres sin dígitos, guía 00000) en una base Postgres LOCAL y desechable (bhev,
puerto 55432). Nunca toca Supabase.
Uso: ./montar.sh && python3 pruebas_idse_validadores.py"""
import subprocess, json, sys, hashlib, os

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
PREVIAS = ['20261104000000_eventos_laborales_idse', '20261104000100_relacion_principal_con_rp', '20261105000000_idse_bajas',
           '20261105000100_idse_modificaciones', '20261107000000_laboral_historial_tipo_email', '20261108000200_modificacion_salario_reglas']
FECHAS = os.path.join(S, 'pendiente', '20261109000000_fechas_hora_mexico.sql')
REV_FECHAS = os.path.join(S, 'reversion', '20261109000000_reversion_fechas_hora_mexico.sql')
MIG = os.path.join(S, 'pendiente', '20261109000200_idse_validadores_guia.sql')
REV = os.path.join(S, 'reversion', '20261109000200_reversion_idse_validadores_guia.sql')
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
def archivo(f):
    p = subprocess.run(PSQL + ['-f', f], capture_output=True, text=True, env=ENV); return p.stdout + p.stderr
def huella():
    return hashlib.sha256(subprocess.run(PSQL + ['-f', HUELLA], capture_output=True, text=True, env=ENV).stdout.encode()).hexdigest()[:16]

T = 'ca200000-0000-4000-8000-000000000001'
U = {'admin': 'cb200000-0000-4000-8000-000000000001', 'nomina': 'cb200000-0000-4000-8000-000000000002'}
E, RP, RP2 = 'cc200000-0000-4000-8000-000000000001', 'cd200000-0000-4000-8000-000000000001', 'cd200000-0000-4000-8000-000000000002'
# BIEN: NSS válido · NSSX: NSS con dígito verificador incorrecto · DIG: nombre con dígitos · BIEN2: válido en otro RP
P = {'BIEN': ('ce200000-0000-4000-8000-000000000001', '11111111115', 'PAOLA', 'GARCIA', 'PAGA900101MDFLLD05'),
     'NSSX': ('ce200000-0000-4000-8000-000000000002', '11111111111', 'PEDRO', 'MORALES', 'MOPE920303HDFRXD08'),
     'DIG':  ('ce200000-0000-4000-8000-000000000003', '22222222220', 'PERSONA 0007', 'PILOTO', 'LOPE900202HDFPRN05'),
     'BIEN2': ('ce200000-0000-4000-8000-000000000004', '33333333335', 'ROSA', 'NAVA', 'NARO880808MDFVSS02')}
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT VALIDADORES');
insert into auth.users (id, email) values ('{U['admin']}','admin.val@beehuman.invalid'),('{U['nomina']}','nomina.val@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U['admin']}','{T}','administrador'),('{U['nomina']}','{T}','nomina');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA VALIDADORES');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RP}','{E}','{T}','Y5555555301'),('{RP2}','{E}','{T}','Y5555555302');
""" + ''.join(f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, nss, curp, empresa_id) "
              f"values ('{pid}','{T}','VAL-{k}','{nom} {ap} LOPEZ','{nom}','{ap}','LOPEZ','{nss}','{curp}','{E}');\n" for k, (pid, nss, nom, ap, curp) in P.items())
o, e = sql(seed, replica=True)
if 'ERROR' in e: sys.exit(e)
for m in PREVIAS:
    s = archivo(os.path.join(S, 'pendiente', m + '.sql'))
    if 'ERROR' in s: sys.exit(m + ': ' + s[s.find('ERROR'):][:300])
for k, (pid, *_) in P.items():
    rp = RP2 if k == 'BIEN2' else RP
    val(f"select public.laboral_registrar_ingreso('{pid}','{E}','{rp}','2026-11-02', null, 500, null, '1', '0', '0', '012', '{k[:4]}', null)", 'admin')

print('--- Dependencia')
s = archivo(MIG)
ok('falta la migración 20261109000000_fechas_hora_mexico' in s, 'sin la migración de fechas no se aplica', s[s.find('ERROR'):][:120])
s = archivo(FECHAS); assert 'ERROR' not in s, s
H_FECHAS = huella()
gen = lambda rp, tipo, ids=None, u='nomina': sql(f"select public.idse_generar_archivo('{rp}','{tipo}'{', array[' + ','.join(repr(i) for i in ids) + ']::uuid[]' if ids else ''})", u)
mov = lambda k: val(f"select m.id from public.idse_movimientos m join public.relaciones_laborales r on r.id = m.relacion_laboral_id where r.personal_id = '{P[k][0]}' and m.tipo_movimiento = '08'")
out, err = gen(RP, '08', [mov('BIEN')])
ok('no tiene número de guía' in err, 'antes de la migración: sin guía no se genera (comportamiento anterior)', err.split('\n')[0][:110])

print('--- Migración')
s = archivo(MIG)
ok('ERROR' not in s, 'aplica sin errores (después de la de fechas)', s[s.find('ERROR'):][:200])
ok('ya está aplicada' in archivo(MIG), 'una segunda aplicación se rechaza')
H1 = huella()

print('--- NSS: 11 dígitos y dígito verificador')
for nss, esp, n in [('11111111115', 't', 'válido'), ('11111111111', 'f', 'dígito verificador incorrecto'), ('00000000007', 'f', 'el NSS sintético de PERSONA PILOTO 0007'),
                    ('00000000000', 't', 'todo ceros es aritméticamente válido (lo rechaza el IMSS, no la fórmula)'), ('1111111111', 'f', '10 dígitos'),
                    ('1111111111A', 'f', 'con letra'), ('22222222220', 't', 'válido'), ('33333333335', 't', 'válido')]:
    ok(val(f"select coalesce(public.es_nss_imss_valido('{nss}')::text, 'null')")[0] == esp, f'{nss}: {n}')
ok(val("select public.es_nss_imss_valido(null)") == 'f', 'NSS vacío: no válido')
ok(val("select public.es_nss_valido('11111111111')") == 't', 'es_nss_valido (expediente) no cambia: solo revisa 11 dígitos')

print('--- Bandeja: errores claros')
filas = dict(l.split('|', 1) for l in sql(f"select nombre || '|' || array_to_string(errores, ' / ') from public.idse_validar('{RP}','08')", 'nomina')[0].splitlines() if '|' in l)
print('    ', filas)
ok(filas.get('PAOLA GARCIA LOPEZ') == '', 'persona con NSS válido: sin errores')
ok('NSS inválido: el dígito verificador no corresponde' in filas.get('PEDRO MORALES LOPEZ', ''), 'NSS con dígito verificador incorrecto: error claro')
ok('Nombre con dígitos' in filas.get('PERSONA 0007 PILOTO LOPEZ', ''), 'nombre con dígitos: error claro')
ok(not any('guía' in v for v in filas.values()), 'la guía ya no aparece como error')

print('--- La generación se impide con esos errores')
out, err = gen(RP, '08', [mov('NSSX')])
ok('NSS inválido' in err and val(f"select count(*) from public.idse_archivos where registro_patronal_id = '{RP}'") == '0', 'con NSS inválido no se genera el archivo', err.split('\n')[0][:120])
out, err = gen(RP, '08', [mov('DIG')])
ok('Nombre con dígitos' in err, 'con nombre con dígitos no se genera el archivo', err.split('\n')[0][:120])
out, err = gen(RP, '08', [mov('BIEN'), mov('NSSX')])
ok('ERROR' in err and val(f"select count(*) from public.idse_archivos where registro_patronal_id = '{RP}'") == '0', 'una selección que incluye un movimiento con error no genera nada (ni los buenos)')

print('--- Guía 00000 por omisión')
out, err = gen(RP, '08', [mov('BIEN')])
lin = val(f"select string_agg(substr(texto, 134, 5), ',') from public.idse_archivo_renglones r join public.idse_archivos a on a.id = r.archivo_id where a.registro_patronal_id = '{RP}'")
fin = val(f"select substr(split_part(contenido, E'\\r\\n', 2), 134, 5) || '|' || guia from public.idse_archivos where registro_patronal_id = '{RP}'")
ok('ERROR' not in err and lin == '00000' and fin == '00000|00000', 'sin guía configurada: el archivo lleva 00000 en el movimiento y en el renglón final', f'{lin} · {fin} · {err[:80]}')
val(f"update public.empresas_registros_patronales set guia_idse = '40001' where id = '{RP2}'", 'admin')
out, err = gen(RP2, '08', [mov('BIEN2')])
fin = val(f"select substr(split_part(contenido, E'\\r\\n', 1), 134, 5) || '|' || substr(split_part(contenido, E'\\r\\n', 2), 134, 5) || '|' || guia from public.idse_archivos where registro_patronal_id = '{RP2}'")
ok(fin == '40001|40001|40001', 'con guía capturada por el Administrador se usa esa guía', fin)
out, err = sql(f"update public.empresas_registros_patronales set guia_idse = '40002' where id = '{RP2}'", 'nomina')
ok(val(f"select guia_idse from public.empresas_registros_patronales where id = '{RP2}'") == '40001', 'Nómina no puede cambiar la guía', (err or out)[:100])

print('--- Reversión')
s = archivo(REV_FECHAS)
ok('cambió después de la migración' in s, 'la de fechas no se puede revertir antes que esta (orden protegido)', s[s.find('ERROR'):][:120])
n_arch = val("select count(*) from public.idse_archivos")
s = archivo(REV)
ok('ERROR' not in s and huella() == H_FECHAS, 'la reversión deja el esquema idéntico al de antes', s[s.find('ERROR'):][:150])
ok(val("select count(*) from public.idse_archivos") == n_arch, 'los archivos ya generados se conservan')
s = archivo(MIG)
ok('ERROR' not in s and huella() == H1, 'se puede volver a aplicar y queda igual', s[s.find('ERROR'):][:150])

ok(all(b for _, b in res), f'TOTAL: {sum(1 for _, b in res if b)}/{len(res)} pruebas OK')
sys.exit(0 if all(b for _, b in res) else 1)
