"""Migración 20261111000000_idse_umf_numero_interno_opcionales (número interno
y UMF opcionales para IDSE) en una base Postgres LOCAL y desechable (bhev,
puerto 55432). Nunca toca Supabase.
Uso: ./montar.sh && python3 pruebas_idse_opcionales.py"""
import subprocess, json, sys, hashlib, os

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
PREVIAS = ['20261104000000_eventos_laborales_idse', '20261104000100_relacion_principal_con_rp', '20261105000000_idse_bajas',
           '20261105000100_idse_modificaciones', '20261107000000_laboral_historial_tipo_email', '20261108000200_modificacion_salario_reglas',
           '20261109000000_fechas_hora_mexico', '20261109000200_idse_validadores_guia']
MIG = os.path.join(S, 'pendiente', '20261111000000_idse_umf_numero_interno_opcionales.sql')
REV = os.path.join(S, 'reversion', '20261111000000_reversion_idse_umf_numero_interno_opcionales.sql')
REV_GUIA = os.path.join(S, 'reversion', '20261109000200_reversion_idse_validadores_guia.sql')
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

T = 'ca300000-0000-4000-8000-000000000001'
U = {'admin': 'cb300000-0000-4000-8000-000000000001', 'nomina': 'cb300000-0000-4000-8000-000000000002'}
E, RP = 'cc300000-0000-4000-8000-000000000001', 'cd300000-0000-4000-8000-000000000001'
# clave: (id, NSS válido, nombre, apellido, CURP, UMF, número interno)
#  SIN/CON: altas · BSIN/BCON: bajas · MSIN/MCON: modificaciones · FALTA: sin tipos ni SDI
P = {'SIN':   ('ce300000-0000-4000-8000-000000000001', '11111111115', 'ALBA', 'DIAZ', 'DIAA900101MDFZLL05', None, None),
     'CON':   ('ce300000-0000-4000-8000-000000000002', '22222222220', 'CARLOS', 'RUIZ', 'RUCA910202HDFZRR06', '012', 'CON1'),
     'BSIN':  ('ce300000-0000-4000-8000-000000000003', '33333333335', 'BEATRIZ', 'SOTO', 'SOBE920303MDFTTT07', None, None),
     'BCON':  ('ce300000-0000-4000-8000-000000000004', '44444444440', 'BRUNO', 'LARA', 'LABR930404HDFRRR08', '021', 'B77'),
     'MSIN':  ('ce300000-0000-4000-8000-000000000005', '55555555550', 'MONICA', 'PAZ', 'PAMO940505MDFZNN09', None, None),
     'MCON':  ('ce300000-0000-4000-8000-000000000006', '66666666665', 'MARIO', 'LUNA', 'LUMA950606HDFNRR01', '030', 'M9'),
     'FALTA': ('ce300000-0000-4000-8000-000000000007', '77777777770', 'FELIPE', 'ROJO', 'ROFE960707HDFJLL02', None, None)}
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT OPCIONALES');
insert into auth.users (id, email) values ('{U['admin']}','admin.opc@beehuman.invalid'),('{U['nomina']}','nomina.opc@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U['admin']}','{T}','administrador'),('{U['nomina']}','{T}','nomina');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA OPCIONALES');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{RP}','{E}','{T}','Y6666666401');
""" + ''.join(f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, nss, curp, empresa_id) "
              f"values ('{v[0]}','{T}','OPC-{k}','{v[2]} {v[3]} LOPEZ','{v[2]}','{v[3]}','LOPEZ','{v[1]}','{v[4]}','{E}');\n" for k, v in P.items())
o, e = sql(seed, replica=True)
if 'ERROR' in e: sys.exit(e)
for m in PREVIAS:
    s = archivo(os.path.join(S, 'pendiente', m + '.sql'))
    if 'ERROR' in s: sys.exit(m + ': ' + s[s.find('ERROR'):][:300])
lit = lambda x: 'null' if x is None else f"'{x}'"
rel = {}
for k, (pid, nss, nom, ap, curp, umf, num) in P.items():
    fecha = '2026-11-02' if k in ('SIN', 'CON', 'FALTA') else '2026-10-01'
    tipos = "null, null, null" if k == 'FALTA' else "'1', '0', '0'"
    sdi = 'null' if k == 'FALTA' else '500'
    val(f"select public.laboral_registrar_ingreso('{pid}','{E}','{RP}','{fecha}', null, {sdi}, null, {tipos}, {lit(umf)}, {lit(num)}, null)", 'admin')
    rel[k] = val(f"select id from public.relaciones_laborales where personal_id = '{pid}'")
for k in ('BSIN', 'BCON'):
    val(f"select public.laboral_registrar_baja('{rel[k]}','2026-11-05','2','Renuncia voluntaria')", 'nomina')
for k in ('MSIN', 'MCON'):
    val(f"select public.laboral_modificar_salario('{rel[k]}','2026-11-05', 650)", 'nomina')
mov = lambda k, t: val(f"select m.id from public.idse_movimientos m where m.relacion_laboral_id = '{rel[k]}' and m.tipo_movimiento = '{t}'")
FN = {'08': 'idse_linea_alta', '02': 'idse_linea_baja', '07': 'idse_linea_modificacion'}
linea = lambda k, t: val(f"select coalesce(public.{FN[t]}('{mov(k, t)}', '00000'), '<null>')")
errores = lambda t: dict(l.split('|', 1) for l in sql(f"select nombre || '|' || array_to_string(errores, ' / ') from public.idse_validar('{RP}','{t}')", 'nomina')[0].splitlines() if '|' in l)
nombre = lambda k: f'{P[k][2]} {P[k][3]} LOPEZ'
gen = lambda t, ks: sql(f"select public.idse_generar_archivo('{RP}','{t}', array[{','.join(repr(mov(k, t)) for k in ks)}]::uuid[])", 'nomina')

print('--- Antes de la migración (comportamiento anterior)')
e08, e02 = errores('08'), errores('02')
ok('Número interno (clave del trabajador)' in e08.get(nombre('SIN'), '') and 'UMF' in e08.get(nombre('SIN'), ''),
   'el alta sin número interno ni UMF aparece con esos dos faltantes', e08.get(nombre('SIN'), ''))
ok('Número interno' in e02.get(nombre('BSIN'), ''), 'la baja sin número interno aparece como faltante')
ok(linea('SIN', '08') == '<null>', 'y su línea no se puede armar (los valores vacíos anulan el renglón)')
ANTES = {(k, t): linea(k, t) for k, t in [('CON', '08'), ('BCON', '02'), ('MCON', '07')]}
H0 = huella()
datos_rel = lambda: val(f"select md5(string_agg(coalesce(umf,'∅')||'|'||coalesce(numero_interno,'∅'), ',' order by id)) from public.relaciones_laborales where tenant_id = '{T}'")
D0 = datos_rel()

print('--- Migración')
s = archivo(MIG)
ok('ERROR' not in s, 'aplica sin errores', s[s.find('ERROR'):][:200])
ok('ya está aplicada' in archivo(MIG), 'una segunda aplicación se rechaza')
ok(datos_rel() == D0, 'no modifica datos: UMF y número interno siguen como estaban (vacíos o capturados)')
H1 = huella()

print('--- Bandeja: ya no son faltantes')
e08, e02, e07 = errores('08'), errores('02'), errores('07')
print('    08:', e08); print('    02:', e02); print('    07:', e07)
ok(e08.get(nombre('SIN')) == '', 'alta sin número interno ni UMF: sin errores')
ok(e08.get(nombre('CON')) == '', 'alta con número interno y UMF: sin errores')
ok(e02.get(nombre('BSIN')) == '' and e02.get(nombre('BCON')) == '', 'baja sin número interno: sin errores (y con número interno igual)')
ok(e07.get(nombre('MSIN')) == '' and e07.get(nombre('MCON')) == '', 'modificación sin número interno: sin errores (y con número interno igual)')
ok(not any('Número interno' in v or v.endswith('UMF') or 'UMF /' in v for d in (e08, e02, e07) for v in d.values()), 'ningún movimiento muestra número interno ni UMF como faltante')
f = e08.get(nombre('FALTA'), '')
ok(all(x in f for x in ('SBC', 'Tipo de trabajador', 'Tipo de salario', 'Jornada')), 'los requisitos reales siguen: sin SDI ni tipos el alta tiene errores', f)

print('--- Con datos capturados: renglón idéntico al validado')
for (k, t), antes in ANTES.items():
    ok(linea(k, t) == antes and len(antes) == 168, f'{t} con número interno{" y UMF" if t == "08" else ""}: renglón igual byte a byte al de antes de la migración',
       repr(antes[126:148]))
l = linea('CON', '08')
ok(l[126:129] == '012' and l[138:148] == '      CON1', 'alta: UMF en 127-129 y clave alineada a la derecha en 139-148', repr(l[126:148]))

print('--- Sin datos: posiciones en blanco, misma estructura')
for k, t in [('SIN', '08'), ('BSIN', '02'), ('MSIN', '07')]:
    l = linea(k, t)
    ok(len(l) == 168 and l[138:148] == ' ' * 10 and l[126:131] == ' ' * 5 and l[-1] == '9', f'{t}: 168 posiciones; 127-131 y clave 139-148 en blanco; termina en 9', repr(l[118:150]))
l, c = linea('SIN', '08'), linea('CON', '08')
ok(l[:11] == c[:11] and l[103:126] == c[103:126] and l[129:138] == c[129:138] == '  0800000' and l[148] == c[148] == ' '
   and l[149:167] == P['SIN'][4] and l[167] == '9',
   'alta sin datos: tipo 08, guía, separador y CURP en sus posiciones de siempre', repr(l[126:168]))
ok(linea('BSIN', '02')[148] == '2', 'baja sin número interno: la causa sigue en la posición 149')

print('--- Generación del archivo')
out, err = gen('08', ['SIN', 'CON'])
ok('ERROR' not in err, 'se genera el archivo de altas con un alta sin número interno ni UMF y otra con ellos', err[:150])
cont = val(f"select replace(replace(contenido, E'\\r', '<CR>'), E'\\n', '<LF>') from public.idse_archivos where registro_patronal_id = '{RP}' and tipo_movimiento = '08'")
lineas = cont.split('<CR><LF>')
ok(len(lineas) == 4 and lineas[3] == '' and all(len(x) == 168 for x in lineas[:3]), 'dos movimientos + renglón final, 168 posiciones cada uno, CRLF', str([len(x) for x in lineas]))
ok(lineas[2][56:62] == '000002' and lineas[2].startswith('*************'), 'renglón final con 000002 movimientos')
ok(set(lineas[:2]) == {linea('SIN', '08'), linea('CON', '08')}, 'el archivo lleva exactamente las líneas revisadas')
for t, ks in (('02', ['BSIN', 'BCON']), ('07', ['MSIN', 'MCON'])):
    out, err = gen(t, ks)
    n = val(f"select num_registros from public.idse_archivos where registro_patronal_id = '{RP}' and tipo_movimiento = '{t}'") if 'ERROR' not in err else '0'
    ok('ERROR' not in err and n == '2', f'se genera el archivo {t} con y sin número interno', err[:150])
ok(datos_rel() == D0, 'no se inventaron valores: UMF y número interno vacíos siguen vacíos después de generar')
ok(val(f"select count(*) from public.idse_movimientos where relacion_laboral_id in ('{rel['SIN']}','{rel['CON']}') and tipo_movimiento = '08' and estado = 'en_archivo'") == '2',
   'los dos movimientos quedan en archivo')

print('--- Reversión')
s = archivo(REV_GUIA)
ok('cambió después de la migración' in s, 'la migración de validadores no se puede revertir antes que esta (orden protegido)', s[s.find('ERROR'):][:120])
n_arch = val("select count(*) from public.idse_archivos")
s = archivo(REV)
ok('ERROR' not in s and huella() == H0, 'la reversión deja el esquema idéntico al de antes', s[s.find('ERROR'):][:150])
ok(val("select count(*) from public.idse_archivos") == n_arch, 'los archivos ya generados se conservan')
s = archivo(MIG)
ok('ERROR' not in s and huella() == H1, 'se puede volver a aplicar y queda igual', s[s.find('ERROR'):][:150])

ok(all(b for _, b in res), f'TOTAL: {sum(1 for _, b in res if b)}/{len(res)} pruebas OK')
sys.exit(0 if all(b for _, b in res) else 1)
