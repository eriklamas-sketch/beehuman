"""Comparación byte a byte: genera con el código de BeeHuman (migración de la etapa 1, base LOCAL
desechable) el archivo de alta con los mismos datos del archivo aceptado por el IMSS y compara.
Uso: ./montar.sh && python3 compara_dat.py <archivo_aceptado.dat>
Los datos del trabajador se leen del propio archivo; no se guardan en el repositorio."""
import sys, os, subprocess, json, base64
REF = open(sys.argv[1], 'rb').read()
l = REF.split(b'\r\n')[0].decode('ascii'); tr = REF.split(b'\r\n')[1].decode('ascii')
c = lambda a, b: l[a-1:b]          # posiciones 1-based, inclusivas
d = dict(rp=c(1,11), nss=c(12,22), pat=c(23,49).strip(), mat=c(50,76).strip(), nom=c(77,103).strip(),
         sbc=int(c(104,109))/100, tt=c(116,116), ts=c(117,117), jo=c(118,118), fecha=c(119,126), umf=c(127,129),
         mov=c(132,133), guia=c(134,138), num=c(139,148).strip(), curp=c(150,167))
fecha = f"{d['fecha'][4:]}-{d['fecha'][2:4]}-{d['fecha'][:2]}"
AQUI = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase', 'pendiente')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhev']
def run(q):
    p = subprocess.run(PSQL, input=q, capture_output=True, text=True)
    if 'ERROR' in p.stderr: sys.exit(p.stderr)
    return [x for x in p.stdout.splitlines() if x and x != 'SET']
T, U, E, R, P = ('ba000000-0000-4000-8000-00000000000' + x for x in '12345')
run(f"""begin; set local session_replication_role = replica;
insert into public.tenants (id, nombre) values ('{T}','TENANT COMPARACION');
insert into auth.users (id, email) values ('{U}','admin@beehuman.invalid');
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA COMPARACION');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values ('{R}','{E}','{T}','{d['rp']}');
insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, nss, curp)
 values ('{P}','{T}','CMP-1','{d['nom']} {d['pat']} {d['mat']}','{d['nom']}','{d['pat']}','{d['mat']}','{d['nss']}','{d['curp']}');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values ('{U}','{T}','administrador'); commit;""")
for m in ['20261104000000_eventos_laborales_idse.sql', '20261104000100_relacion_principal_con_rp.sql']:
    p = subprocess.run(PSQL + ['-1', '-f', os.path.join(S, m)], capture_output=True, text=True)
    if 'ERROR' in p.stderr: sys.exit(p.stderr)
como = f"begin; select set_config('request.jwt.claims', '{json.dumps({'sub': U})}', true); set local role authenticated;\n"
run(f"begin; set local session_replication_role = replica; update public.empresas_registros_patronales set guia_idse = '{d['guia']}' where id = '{R}'; commit;")
run(como + f"select public.laboral_registrar_ingreso('{P}','{E}','{R}','{fecha}', null, {d['sbc']}, null, '{d['tt']}', '{d['ts']}', '{d['jo']}', '{d['umf']}', '{d['num']}'); commit;")
arch = run(como + f"select public.idse_generar_archivo('{R}','08'); commit;")[-1]
fila = run(f"select replace(encode(convert_to(contenido,'UTF8'),'base64'), E'\\n', '') || '|' || nombre_archivo from public.idse_archivos where id='{arch}'")[-1]
b64, nombre = fila.split('|')
GEN = base64.b64decode(b64)
print('Archivo aceptado:', len(REF), 'bytes;', 'generado por BeeHuman:', len(GEN), 'bytes;', 'nombre generado:', nombre)
if GEN == REF:
    print('IDÉNTICOS byte a byte (renglón de alta + renglón final + CRLF).')
else:
    for i, (a, b) in enumerate(zip(REF, GEN)):
        if a != b:
            r = REF[:i].count(b'\n') + 1; col = i - (REF.rfind(b'\n', 0, i) + 1) + 1
            print(f'Primera diferencia: renglón {r}, posición {col}: aceptado {bytes([a])!r}, BeeHuman {bytes([b])!r}')
            print('  aceptado:', REF.split(b"\r\n")[r-1][max(0,col-15):col+15]); print('  BeeHuman:', GEN.split(b"\r\n")[r-1][max(0,col-15):col+15])
            break
    else: print('Diferente longitud')
    sys.exit(1)
