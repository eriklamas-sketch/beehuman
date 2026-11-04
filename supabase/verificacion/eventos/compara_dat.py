"""Comparación byte a byte de archivos IDSE (alta 08 o baja 02).
Lee un archivo de referencia, reproduce sus movimientos con el código de BeeHuman
(migraciones de la etapa 1, base LOCAL desechable bhev) y compara el archivo generado.
Uso: ./montar.sh && python3 compara_dat.py <archivo_referencia.dat>
Los datos se leen del archivo recibido; el script no guarda ninguno."""
import sys, os, subprocess, json, base64, uuid
REF = open(sys.argv[1], 'rb').read()
renglones = [r.decode('ascii') for r in REF.split(b'\r\n') if r]
movs, final = renglones[:-1], renglones[-1]
c = lambda l, a, b: l[a-1:b]                      # posiciones 1-based, inclusivas
tipo = c(movs[0], 132, 133)
assert tipo in ('08', '02') and all(c(l, 132, 133) == tipo for l in movs), 'tipo de movimiento no soportado o mezclado'
rp, guia = c(movs[0], 1, 11), c(movs[0], 134, 138)
iso = lambda f: f'{f[4:]}-{f[2:4]}-{f[:2]}'

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase', 'pendiente')
MIGS = ['20261104000000_eventos_laborales_idse.sql', '20261104000100_relacion_principal_con_rp.sql', '20261105000000_idse_bajas.sql']
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhev']
def run(q):
    p = subprocess.run(PSQL, input=q, capture_output=True, text=True)
    if 'ERROR' in p.stderr: sys.exit(p.stderr)
    return [x for x in p.stdout.splitlines() if x and x != 'SET']
lit = lambda v: "'" + v.replace("'", "''") + "'"
T, U, E, R = ('ba000000-0000-4000-8000-00000000000' + x for x in '1234')
seed = f"""begin; set local session_replication_role = replica;
insert into public.tenants (id, nombre) values ('{T}','TENANT COMPARACION');
insert into auth.users (id, email) values ('{U}','admin@beehuman.invalid');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA COMPARACION');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{R}','{E}','{T}',{lit(rp)});
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U}','{T}','administrador');
"""
personas = []
for n, l in enumerate(movs, 1):
    pid = str(uuid.uuid4())
    d = dict(id=pid, nss=c(l, 12, 22), pat=c(l, 23, 49).strip(), mat=c(l, 50, 76).strip(), nom=c(l, 77, 103).strip(),
             fecha=iso(c(l, 119, 126)), clave=c(l, 139, 148).strip())
    if tipo == '08':
        d.update(sbc=int(c(l, 104, 109)) / 100, tt=c(l, 116, 116), ts=c(l, 117, 117), jo=c(l, 118, 118), umf=c(l, 127, 129), curp=c(l, 150, 167))
    else:
        d.update(causa=c(l, 149, 149), curp=None)
    personas.append(d)
    seed += (f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, nss, curp) values "
             f"('{pid}','{T}','CMP-{n}',{lit(d['nom'] + ' ' + d['pat'] + ' ' + d['mat'])},{lit(d['nom'])},{lit(d['pat'])},{lit(d['mat'])},{lit(d['nss'])},{lit(d['curp']) if d['curp'] else 'null'});\n")
run(seed + 'commit;')
for m in MIGS:
    p = subprocess.run(PSQL + ['-1', '-f', os.path.join(S, m)], capture_output=True, text=True)
    if 'ERROR' in p.stderr: sys.exit(m + ': ' + p.stderr)
run(f"begin; set local session_replication_role = replica; update public.empresas_registros_patronales set guia_idse = {lit(guia)} where id = '{R}'; commit;")
como = f"begin; select set_config('request.jwt.claims', '{json.dumps({'sub': U})}', true); set local role authenticated;\n"
for d in personas:
    if tipo == '08':
        run(como + f"select public.laboral_registrar_ingreso('{d['id']}','{E}','{R}','{d['fecha']}', null, {d['sbc']}, null, '{d['tt']}', '{d['ts']}', '{d['jo']}', '{d['umf']}', {lit(d['clave'])}); commit;")
    else:   # la persona necesita una relación vigente con RP para poder darla de baja
        rel = run(como + f"select public.laboral_registrar_ingreso('{d['id']}','{E}','{R}','2026-01-05', null, 400, null, '1', '0', '0', '001', {lit(d['clave'])}); commit;")[-1]
        run(como + f"select public.laboral_registrar_baja('{rel}','{d['fecha']}','{d['causa']}'); commit;")
arch = run(como + f"select public.idse_generar_archivo('{R}','{tipo}'); commit;")[-1]
b64, nombre = run(f"select replace(encode(convert_to(contenido,'UTF8'),'base64'), E'\\n', '') || '|' || nombre_archivo from public.idse_archivos where id='{arch}'")[-1].split('|')
GEN = base64.b64decode(b64)
print(f"Tipo {tipo}: {len(movs)} movimiento(s). Referencia {len(REF)} bytes; BeeHuman {len(GEN)} bytes; nombre generado: {nombre}")
if GEN == REF:
    print('IDÉNTICOS byte a byte (renglones de movimiento + renglón final + CRLF).')
else:
    for i, (a, b) in enumerate(zip(REF, GEN)):
        if a != b:
            r = REF[:i].count(b'\n') + 1; col = i - (REF.rfind(b'\n', 0, i) + 1) + 1
            print(f'Primera diferencia: renglón {r}, posición {col}: referencia {bytes([a])!r}, BeeHuman {bytes([b])!r}')
            break
    else: print('Diferente longitud')
    sys.exit(1)
