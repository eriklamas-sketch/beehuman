"""Pruebas de la etapa 1 (relaciones laborales, historial por eventos e IDSE)
en una base Postgres LOCAL y desechable (bhev, puerto 55432). Nunca toca Supabase.
Cada paso corre en su propia transacción con la identidad de un usuario
(rol authenticated + claim sub), igual que una petición real de la app.
Uso: ./montar.sh && python3 pruebas_eventos.py"""
import subprocess, json, sys, hashlib, os

AQUI = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(AQUI, '..', 'repo', 'beehuman-int', 'supabase')
MIG = os.path.join(S, 'pendiente', '20261104000000_eventos_laborales_idse.sql')
REV = os.path.join(S, 'reversion', '20261104000000_reversion_eventos_laborales_idse.sql')
MIG31 = os.path.join(S, 'pendiente', '20261104000100_relacion_principal_con_rp.sql')
REV31 = os.path.join(S, 'reversion', '20261104000100_reversion_relacion_principal_con_rp.sql')
DEF_PRINCIPAL = "select md5(pg_get_functiondef('public.laboral_relacion_principal(uuid)'::regprocedure))"
HUELLA = os.path.join(S, 'verificacion', 'huella_esquema.sql')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhev']
res = []

def sql(q, user=None, replica=False):
    pre = 'begin;\n'
    if replica: pre += "set local session_replication_role = replica;\n"
    if user:
        pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    out = '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET'))
    return out, p.stderr.strip()

def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err and 'ERROR' in err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''

def ok(cond, nombre, detalle=''):
    res.append((nombre, bool(cond)))
    print(('OK    ' if cond else 'FALLA ') + nombre + (f'  [{detalle}]' if detalle else ''))

def falla_con(q, user, texto, nombre):
    out, err = sql(q, user)
    ok('ERROR' in err and texto.lower() in err.lower(), nombre, (err.split('\n')[0][:150] if err else 'NO FALLÓ: ' + out[:80]))

def archivo(f, previo=''):
    p = subprocess.run(PSQL, input=previo + open(f).read(), capture_output=True, text=True)
    return p.stdout + p.stderr

def huella():
    p = subprocess.run(PSQL + ['-f', HUELLA], capture_output=True, text=True)
    return hashlib.sha256(p.stdout.encode()).hexdigest()[:16]

# ---------------- Datos ficticios ----------------
T, T2 = 'aa000000-0000-4000-8000-000000000001', 'aa000000-0000-4000-8000-000000000002'
U = {k: f'ab000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['admin', 'nomina', 'consulta', 'coord', 'admin2'], 1)}
E1, E2, E9 = ('ac000000-0000-4000-8000-00000000000' + c for c in '129')
RP1, RP2, RP3, RP9 = ('ad000000-0000-4000-8000-00000000000' + c for c in '1239')
CL, PER = 'ae000000-0000-4000-8000-000000000001', 'ae000000-0000-4000-8000-000000000002'
P = {k: f'af000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'PC', 'PX', 'P8', 'P9', 'P10', 'P11', 'P12', 'P13'], 1)}

seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT EVENTOS'),('{T2}','TENANT OTRO');
insert into auth.users (id, email) select v::uuid, k||'@beehuman.invalid' from (values {','.join(f"('{v}','{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA UNO'),('{E2}','{T}','EMPRESA DOS'),('{E9}','{T2}','EMPRESA AJENA');
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values
 ('{RP1}','{E1}','{T}','Y1234567101'),('{RP2}','{E1}','{T}','Y1234567102'),('{RP3}','{E2}','{T}','Y7654321103'),('{RP9}','{E9}','{T2}','Y9999999109');
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL}','{T}','Base / IMSS');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{PER}','{T}','QUINCENAL',15);
"""
def persona(k, emp=None, rp=None, extra=''):
    return (f"insert into public.personal (id, tenant_id, empleado_id, nombre_completo, nombres, primer_apellido, segundo_apellido, empresa_id, registro_patronal_id{',' if extra else ''}{extra.split('|')[0]}) "
            f"values ('{P[k]}','{T if k != 'PX' else T2}','BEH-{k}','PERSONA {k}','PERSONA','{k}','PRUEBA',{repr(emp) if emp else 'null'},{repr(rp) if rp else 'null'}{',' if extra else ''}{extra.split('|')[1] if extra else ''});\n")
seed += persona('P1', E1, RP1, "fecha_alta_imss, sdi_imss, numero_interno_trabajador, nss, curp, fecha_antiguedad|'2024-03-01', 500, '101', '12345678901', 'GARC800101HDFRRL09', '2020-01-15'")
seed += persona('P2', E1, RP1, "fecha_alta_imss, nss|'2025-02-01', '12345678902'")
seed += persona('P3', E1, RP2, "fecha_alta_imss, estatus, fecha_baja, comentario_baja|'2024-01-10', 'Baja', '2025-06-30', 'Renuncia'")
seed += persona('P4')
seed += persona('P5', E1, None, "fecha_inicio_contrato|'2025-01-10'")
seed += persona('P6', E1, RP1)
seed += persona('P7')
seed += persona('PC', E1, RP1, "fecha_alta_imss|'2023-05-05'")
seed += persona('PX', E9, RP9, "fecha_alta_imss|'2024-05-05'")
seed += persona('P8', E1, RP1, "fecha_alta_imss, nss|'2024-04-01', '42345678901'")
seed += persona('P9', E1, RP2, "fecha_alta_imss, estatus, fecha_baja, comentario_baja|'2025-01-15', 'Baja', '2025-08-31', 'Fin de obra'")
seed += persona('P10', extra="nss, curp|'52345678901', 'RAMJ880808HDFMRN03'")
seed += persona('P11', extra="nss, curp|'62345678901', 'SOTL910909MDFTRS02'")
seed += persona('P12', E1, RP1, "fecha_alta_imss|'2024-02-01'")
seed += persona('P13', E1, None, "fecha_inicio_contrato, nss|'2025-02-01', '72345678901'")
seed += f"""
update public.personal set coordinador_id = '{P['PC']}' where id = '{P['P1']}';
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values
 ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),('{U['consulta']}','{T}','consulta',null),
 ('{U['coord']}','{T}','coordinador','{P['PC']}'),('{U['admin2']}','{T2}','administrador',null);
insert into public.usuario_alcances (tenant_id, user_id, empresa_id) values ('{T}','{U['consulta']}','{E1}');
insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, empresa_id, registro_patronal_id, activo, fecha_inicio) values
 ('{T}','{P['P1']}','{CL}','{PER}',7500,'bruto','{E1}','{RP1}',true,'2024-03-01'),
 ('{T}','{P['P1']}','{CL}','{PER}',1500,'neto','{E1}',null,true,'2024-03-01'),
 ('{T}','{P['P2']}','{CL}','{PER}',6000,'bruto','{E2}','{RP3}',true,'2025-02-01'),
 ('{T}','{P['P3']}','{CL}','{PER}',5000,'bruto','{E1}','{RP2}',false,'2024-01-10'),
 ('{T}','{P['P5']}','{CL}','{PER}',4000,'neto',null,null,true,'2025-01-10'),
 ('{T}','{P['P8']}','{CL}','{PER}',5000,'bruto','{E1}','{RP2}',true,'2024-06-01'),
 ('{T}','{P['P9']}','{CL}','{PER}',5200,'bruto','{E1}','{RP2}',false,'2025-01-15'),
 ('{T}','{P['P9']}','{CL}','{PER}',4800,'bruto','{E2}','{RP3}',false,'2022-03-01'),
 ('{T}','{P['P12']}','{CL}','{PER}',5100,'bruto','{E1}','{RP2}',true,'2024-02-01'),
 ('{T}','{P['P12']}','{CL}','{PER}',700,'neto','{E1}',null,true,'2024-02-01');
"""
o, e = sql(seed, replica=True)
if 'ERROR' in e: print(e); sys.exit(1)

H0 = huella()
antes_personal = val("select md5(string_agg(to_jsonb(p)::text, '' order by id)) from public.personal p")
antes_rp = val("select md5(string_agg((to_jsonb(r))::text, '' order by id)) from public.personal_registros_pago r")

print('--- Migración')
salida = archivo(MIG)
print('\n'.join(l for l in salida.splitlines() if 'NOTICE' in l or 'ERROR' in l))
def_v3 = val(DEF_PRINCIPAL)
salida31 = archivo(MIG31)
ok('ERROR' not in salida31, 'v3.1 (relación principal con RP) se aplica sin errores', salida31[:150])
ok('ERROR' not in salida, 'la migración se aplica sin errores')
ok(val("select md5(string_agg(to_jsonb(p)::text, '' order by id)) from public.personal p") == antes_personal,
   'la migración no modifica ninguna fila de personal')
ok(val("select md5(string_agg((to_jsonb(r) - 'relacion_laboral_id')::text, '' order by id)) from public.personal_registros_pago r")
   == val("select md5(string_agg((to_jsonb(r))::text, '' order by id)) from (select id, tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, empresa_id, registro_patronal_id, fecha_inicio, fecha_fin, activo, notas, created_at, creado_por, actualizado_por, actualizado_en from public.personal_registros_pago) r")
   and val("select count(*) from public.personal_registros_pago where actualizado_en is not null") == '0',
   'registros de pago: solo cambia el enlace (sin sellar autoría)')

rel = lambda k: val(f"select string_agg(coalesce(e.nombre,'')||'/'||coalesce(rp.registro_patronal,'-')||'/'||rl.estado||'/'||rl.fecha_ingreso_origen, ',' order by e.nombre, rp.registro_patronal) from public.relaciones_laborales rl join public.empresas e on e.id=rl.empresa_id left join public.empresas_registros_patronales rp on rp.id=rl.registro_patronal_id where rl.personal_id='{P[k]}'")
ok(rel('P1') == 'EMPRESA UNO/Y1234567101/vigente/fecha_alta_imss', 'P1: una relación con dos esquemas (con y sin RP)', rel('P1'))
ok(val(f"select count(distinct relacion_laboral_id)||'/'||count(*) from public.personal_registros_pago where personal_id='{P['P1']}'") == '1/2', 'P1: los dos esquemas en la misma relación')
ok(rel('P2') == 'EMPRESA DOS/Y7654321103/vigente/sin_dato,EMPRESA UNO/Y1234567101/vigente/fecha_alta_imss', 'P2: dos relaciones en paralelo (multirregistro)', rel('P2'))
ok(rel('P3') == 'EMPRESA UNO/Y1234567102/baja/fecha_alta_imss', 'P3: relación en baja con su evento', rel('P3'))
ok(val(f"select count(*) from public.eventos_laborales where personal_id='{P['P3']}' and tipo='baja'") == '1', 'P3: evento de baja migrado')
ok(rel('P4') == '', 'P4: sin empresa → sin relación')
ok(rel('P5') == 'EMPRESA UNO/-/vigente/fecha_inicio_contrato', 'P5: relación sin RP (solo efectivo) con historial', rel('P5'))
ok(val(f"select count(*) from public.personal_registros_pago where personal_id='{P['P5']}' and relacion_laboral_id is not null") == '1', 'P5: esquema sin empresa enlazado a su única relación')
ok(rel('P6') == 'EMPRESA UNO/Y1234567101/vigente/sin_dato', 'P6: sin fecha queda marcada para revisar', rel('P6'))
ok(val(f"select fecha_ingreso||'|'||fecha_reconocimiento_antiguedad||'|'||sbc||'|'||numero_interno from public.relaciones_laborales where personal_id='{P['P1']}'") == '2024-03-01|2020-01-15|500.00|101',
   'P1: ingreso IMSS y antigüedad reconocida se migran por separado')
ok(val("select count(*) from public.idse_movimientos") == '0', 'lo migrado no genera movimientos IDSE')

print('--- Ficha: datos controlados y eventos automáticos')
falla_con(f"update public.personal set empresa_id='{E2}' where id='{P['P1']}'", 'admin', 'Historia laboral', 'no se cambia la empresa directo en la ficha')
falla_con(f"update public.personal set estatus='Baja' where id='{P['P1']}'", 'admin', 'Historia laboral', 'no se da de baja directo en la ficha')
falla_con(f"update public.personal set fecha_antiguedad='2019-01-01' where id='{P['P1']}'", 'admin', 'Historia laboral', 'la antigüedad reconocida no se cambia directo en la ficha')
out, err = sql(f"update public.personal set empresa_id='{E1}', nombre_completo=nombre_completo where id='{P['P1']}'", 'admin')
ok('ERROR' not in err, 'guardar la ficha reenviando los mismos valores sigue funcionando', err[:120])
out, err = sql(f"update public.personal set estatus='Suspendido' where id='{P['P1']}'", 'admin')
ok('ERROR' not in err, 'Activo ↔ Suspendido sigue editable', err[:120])
sql(f"update public.personal set estatus='Activo' where id='{P['P1']}'", 'admin')
out, err = sql(f"update public.personal set empresa_id='{E1}' where id='{P['P4']}'", 'admin')
ok('ERROR' not in err, 'persona sin historial: se edita como antes', err[:120])
sql(f"update public.personal set empresa_id=null where id='{P['P4']}'", 'admin')
sql(f"insert into public.puestos (id, tenant_id, nombre) values ('ae000000-0000-4000-8000-000000000009','{T}','SUPERVISOR')", replica=True)
sql(f"update public.personal set puesto_id='ae000000-0000-4000-8000-000000000009' where id='{P['P1']}'", 'admin')
ok(val(f"select valores_nuevos->>'puesto' from public.eventos_laborales where personal_id='{P['P1']}' and tipo='cambio_puesto'") == 'SUPERVISOR',
   'cambiar el puesto en la ficha registra el evento en el servidor')
sql(f"update public.personal set nombre_completo='PERSONA P1' where id='{P['P1']}'", 'admin')
ok(val(f"select count(*) from public.eventos_laborales where personal_id='{P['P1']}' and origen='automatico'") == '1', 'editar un dato no laboral no crea eventos')

print('--- Escritura directa y permisos')
falla_con(f"insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, origen) select tenant_id, personal_id, id, 'baja', current_date, 'pantalla' from public.relaciones_laborales limit 1", 'admin', 'permission denied', 'el navegador no puede insertar eventos (ni siendo administrador)')
falla_con("update public.relaciones_laborales set sbc = 1", 'admin', 'permission denied', 'el navegador no puede editar relaciones')
falla_con("delete from public.eventos_laborales", None, 'no se puede borrar', 'ni el dueño de la base puede borrar eventos')
falla_con("update public.eventos_laborales set motivo='x'", None, 'solo se modifica con las funciones', 'ni el dueño puede editar fuera de las funciones')
falla_con("select set_config('beehuman.laboral','on',true); update public.eventos_laborales set motivo='x'", None, 'no se edita', 'con el interruptor encendido, un evento tampoco se edita')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-01')", 'consulta', 'tu rol no permite', 'Consulta no registra movimientos')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-01')", 'coord', 'tu rol no permite', 'Coordinador no registra movimientos')
falla_con(f"select public.laboral_sincronizar_persona('{P['P1']}')", 'admin', 'permission denied', 'las funciones internas no se pueden llamar desde la app')
falla_con(f"select * from public.idse_validar('{RP1}')", 'consulta', 'tu rol no permite', 'Consulta no ve la bandeja IDSE')
ok(val("select count(*) from public.relaciones_laborales", 'consulta') == '0', 'Consulta no lee las tablas directo (ve el historial por la función)')
ok(val("select count(*) from public.idse_archivos", 'coord') == '0', 'Coordinador no lee archivos IDSE')

print('--- Ingreso, reglas y sincronización de la ficha')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP3}','2026-10-01')", 'admin', 'no pertenece a la empresa', 'RP de otra empresa: rechazado')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-01', null, 10000)", 'admin', 'tope de 25 UMA', 'SBC arriba de 25 UMA: rechazado')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-01', null, 200)", 'admin', 'salario mínimo', 'SBC abajo del salario mínimo: rechazado')
sql(f"update public.personal set nss='12345678901', curp='GARC800101HDFRRL09' where id='{P['P7']}'", replica=True)
falla_con(f"select public.laboral_registrar_ingreso('{P['P7']}','{E1}','{RP1}','2026-10-01', null, 400)", 'admin', 'posible persona duplicada', 'mismo NSS vigente en el RP con otra ficha: rechazado')
sql(f"update public.personal set nss='22345678907', curp='MUNA850505MDFXXR01', primer_apellido='MUÑOZ', segundo_apellido='PEÑA', nombres='ANA SOFÍA' where id='{P['P7']}'", replica=True)
sql(f"update public.personal set nss='32345678904', curp='LOPE900202HDFPRN05', primer_apellido='LÓPEZ', segundo_apellido='', nombres='JUAN' where id='{P['P4']}'", replica=True)
rel4 = val(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-01', '2018-06-01', 400, 420, '1', '0', '0', '012', '204')", 'nomina')
ok(len(rel4) == 36, 'Nómina registra un ingreso')
ok(val(f"select fecha_ingreso||'|'||fecha_reconocimiento_antiguedad from public.relaciones_laborales where id='{rel4}'") == '2026-10-01|2018-06-01',
   'el ingreso conserva su fecha aunque se reconozca antigüedad anterior')
ok(val(f"select empresa_id||'|'||registro_patronal_id||'|'||fecha_alta_imss||'|'||sdi_imss||'|'||numero_interno_trabajador||'|'||fecha_antiguedad from public.personal where id='{P['P4']}'")
   == f"{E1}|{RP1}|2026-10-01|420.00|204|2018-06-01", 'la ficha se sincroniza desde la relación')
ok(val(f"select tipo_movimiento||'|'||estado||'|'||sbc from public.idse_movimientos where relacion_laboral_id='{rel4}'") == '08|pendiente|400.00', 'el ingreso con RP crea el movimiento IDSE 08 pendiente')
falla_con(f"select public.laboral_registrar_ingreso('{P['P4']}','{E1}','{RP1}','2026-10-02')", 'admin', 'ya tiene una relación vigente', 'segundo ingreso vigente en la misma empresa y RP: rechazado')
rel5b = val(f"select public.laboral_registrar_ingreso('{P['P4']}','{E2}',null,'2026-10-05')", 'admin')
ok(val(f"select count(*) from public.idse_movimientos where relacion_laboral_id='{rel5b}'") == '0', 'relación sin RP: historial sin IDSE')
ok(val(f"select registro_patronal_id from public.personal where id='{P['P4']}'") == RP1, 'la relación con RP sigue siendo la principal de la ficha')

print('--- Esquemas de pago')
sql(f"insert into public.personal_registros_pago (personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, empresa_id, registro_patronal_id, fecha_inicio) values ('{P['P4']}','{CL}','{PER}',6200,'bruto','{E1}','{RP1}','2026-10-01')", 'admin')
ok(val(f"select (relacion_laboral_id = '{rel4}')::text from public.personal_registros_pago where personal_id='{P['P4']}' and sueldo=6200") == 'true', 'un esquema nuevo se enlaza solo a su relación')
ok(val(f"select valores_nuevos->>'sueldo' from public.eventos_laborales where relacion_laboral_id='{rel4}' and tipo='cambio_esquema_pago'") == '6200.00', 'el esquema nuevo queda en el historial')
falla_con(f"update public.personal_registros_pago set relacion_laboral_id='{rel5b}' where personal_id='{P['P4']}' and sueldo=6200", 'admin', 'deben ser los de su relación', 'un esquema no se mueve a una relación de otra empresa')

print('--- Modificación de salario, baja, anulación')
ev7 = val(f"select public.laboral_modificar_salario('{rel4}','2026-10-15', 450)", 'nomina')
falla_con(f"select public.laboral_modificar_salario('{rel4}','2026-10-15', 460)", 'nomina', 'posterior a la última', 'dos modificaciones con la misma fecha: rechazado')
falla_con(f"select public.laboral_registrar_baja('{rel4}','2026-10-10','2')", 'nomina', 'no puede ser anterior', 'baja anterior a la última modificación: rechazado')
falla_con(f"select public.laboral_registrar_baja('{rel4}','2026-10-31',null)", 'nomina', 'causa de baja', 'baja sin causa: rechazado')
evb = val(f"select public.laboral_registrar_baja('{rel4}','2026-10-31','2','Renuncia voluntaria')", 'nomina')
ok(val(f"select estado||'|'||fecha_baja||'|'||causa_baja from public.relaciones_laborales where id='{rel4}'") == 'baja|2026-10-31|2', 'la baja cierra la relación')
ok(val(f"select count(*) filter (where activo) from public.personal_registros_pago where relacion_laboral_id='{rel4}'") == '0', 'la baja desactiva los esquemas de esa relación')
ok(val(f"select estatus from public.personal where id='{P['P4']}'") == 'Activo', 'con otra relación vigente, la persona sigue Activa')
ok(val(f"select string_agg(tipo_movimiento||':'||estado, ',' order by creado_en) from public.idse_movimientos where relacion_laboral_id='{rel4}'") == '08:pendiente,07:pendiente,02:pendiente', 'alta, modificación y baja quedan en la bandeja IDSE')
falla_con(f"select public.laboral_anular_evento('{ev7}','error')", 'nomina', 'solo se puede anular el último', 'no se anula un movimiento con otros posteriores')
sql(f"select public.laboral_anular_evento('{evb}','Se capturó por error')", 'nomina')
ok(val(f"select estado||'|'||coalesce(fecha_baja::text,'-') from public.relaciones_laborales where id='{rel4}'") == 'vigente|-', 'anular la baja reabre la relación')
ok(val(f"select count(*) filter (where activo) from public.personal_registros_pago where relacion_laboral_id='{rel4}'") == '1', 'anular la baja reactiva sus esquemas')
ok(val(f"select estado from public.idse_movimientos where evento_id='{evb}'") == 'cancelado', 'el movimiento 02 de la baja anulada se cancela')
sql(f"select public.laboral_anular_evento('{ev7}','Monto equivocado')", 'nomina')
ok(val(f"select sbc from public.relaciones_laborales where id='{rel4}'") == '400.00', 'anular la modificación regresa el SBC anterior')
ok(val(f"select count(*)||'|'||count(*) filter (where estado='anulado') from public.eventos_laborales where relacion_laboral_id='{rel4}'") == '4|2', 'los eventos anulados se conservan en el historial')

print('--- Baja total, reingreso y correcciones')
rel3 = val(f"select id from public.relaciones_laborales where personal_id='{P['P3']}'")
r3b = val(f"select public.laboral_registrar_ingreso('{P['P3']}','{E1}','{RP2}','2026-11-01', '2024-01-10', 350)", 'admin')
ok(val(f"select tipo from public.eventos_laborales where relacion_laboral_id='{r3b}' and tipo in ('ingreso','reingreso')") == 'reingreso', 'regresar al mismo RP es un reingreso (relación nueva)')
ok(val(f"select estatus||'|'||coalesce(fecha_baja::text,'-') from public.personal where id='{P['P3']}'") == 'Activo|-', 'el reingreso reactiva la ficha')
ok(val(f"select fecha_ingreso||'|'||fecha_reconocimiento_antiguedad from public.relaciones_laborales where id='{r3b}'") == '2026-11-01|2024-01-10', 'el reingreso conserva la antigüedad reconocida sin tocar la fecha de ingreso')
sql(f"select public.laboral_registrar_baja('{r3b}','2026-11-30','1')", 'admin')
ok(val(f"select estatus||'|'||fecha_baja||'|'||comentario_baja from public.personal where id='{P['P3']}'") == 'Baja|2026-11-30|Término de contrato', 'sin relaciones vigentes la ficha queda en Baja')
rel6 = val(f"select id from public.relaciones_laborales where personal_id='{P['P6']}'")
sql(f"select public.laboral_corregir_datos('{rel6}', '{{\"fecha_ingreso\":\"2025-05-01\"}}', 'Dato de expediente físico')", 'admin')
ok(val(f"select fecha_ingreso||'|'||fecha_ingreso_origen from public.relaciones_laborales where id='{rel6}'") == '2025-05-01|captura', 'se corrige la fecha de un dato migrado')
falla_con(f"select public.laboral_corregir_datos('{rel4}', '{{\"sbc\":500}}', 'x')", 'admin', 'solo se corrige en datos migrados', 'el SBC de un ingreso real no se corrige: va por modificación')
falla_con(f"select public.laboral_corregir_datos('{rel4}', '{{\"empresa_id\":\"{E2}\"}}', 'x')", 'admin', 'no se corrige por esta vía', 'la empresa no se corrige por esta vía')
falla_con(f"select public.laboral_corregir_datos('{rel4}', '{{\"umf\":\"9\"}}', 'x')", 'admin', 'check', 'UMF con formato inválido: rechazado')


print('--- V2: hallazgos de la revisión técnica')
# 1.4 Bajas migradas: la fecha de la ficha solo va a la relación de la ficha
ok(val(f"select string_agg(rp.registro_patronal||':'||rl.estado||':'||coalesce(rl.fecha_baja::text,'-')||':'||array_to_string(rl.pendientes_migracion,'+'), ',' order by rp.registro_patronal) from public.relaciones_laborales rl join public.empresas_registros_patronales rp on rp.id=rl.registro_patronal_id where rl.personal_id='{P['P9']}'")
   == 'Y1234567102:baja:2025-08-31:,Y7654321103:baja:-:sin_fecha_ingreso+historica_por_reconstruir',
   'H4: la fecha de baja de la ficha solo va a su relación; el empleo anterior queda por reconstruir sin fecha inventada')
ok(val(f"select motivo from public.eventos_laborales e join public.relaciones_laborales rl on rl.id=e.relacion_laboral_id where rl.personal_id='{P['P9']}' and e.tipo='baja' and rl.fecha_baja is null") == 'Relación histórica: fecha de baja por reconstruir',
   'H4: la baja histórica no hereda el comentario de la ficha')
ok(val("select count(*) from respaldo.personal_ficha_20261104") == val("select count(*) from public.personal"), 'respaldo completo de la ficha antes de migrar')
# 1.1 Enlace de esquemas con varias relaciones candidatas
ok(val(f"select count(*) from public.relaciones_laborales where personal_id='{P['P8']}' and estado='vigente'") == '2', 'H1: P8 tiene dos relaciones vigentes en la misma empresa (RP1 y RP2)')
sql(f"insert into public.personal_registros_pago (personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, empresa_id, fecha_inicio) values ('{P['P8']}','{CL}','{PER}',900,'neto','{E1}','2026-10-01')", 'admin')
ok(val(f"select coalesce(relacion_laboral_id::text,'sin enlace') from public.personal_registros_pago where personal_id='{P['P8']}' and sueldo=900") == 'sin enlace',
   'H1: con dos relaciones candidatas el esquema NO se enlaza solo')
rel8b = val(f"select rl.id from public.relaciones_laborales rl where rl.personal_id='{P['P8']}' and rl.registro_patronal_id='{RP2}'")
out, err = sql(f"update public.personal_registros_pago set relacion_laboral_id='{rel8b}' where personal_id='{P['P8']}' and sueldo=900", 'nomina')
ok('ERROR' not in err and val(f"select (relacion_laboral_id='{rel8b}')::text from public.personal_registros_pago where personal_id='{P['P8']}' and sueldo=900") == 'true',
   'H1: Nómina elige la relación correcta del esquema', err[:120])
sql(f"insert into public.personal_registros_pago (personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, empresa_id, registro_patronal_id, fecha_inicio) values ('{P['P8']}','{CL}','{PER}',950,'bruto','{E1}','{RP1}','2026-10-01')", 'admin')
ok(val(f"select (relacion_laboral_id = (select id from public.relaciones_laborales where personal_id='{P['P8']}' and registro_patronal_id='{RP1}'))::text from public.personal_registros_pago where personal_id='{P['P8']}' and sueldo=950") == 'true',
   'H1: con RP explícito el enlace es exacto')
# 1.2 Sincronización explícita de la ficha
r10a = val(f"select public.laboral_registrar_ingreso('{P['P10']}','{E1}','{RP2}','2026-09-01','2015-01-01',400,410,'1','0','0','010','300')", 'admin')
r10b = val(f"select public.laboral_registrar_ingreso('{P['P10']}','{E2}',null,'2026-09-05')", 'admin')
ok(val(f"select empresa_id||'|'||registro_patronal_id from public.personal where id='{P['P10']}'") == f'{E1}|{RP2}', 'H2: abrir otra relación no hace «saltar» la ficha de empresa')
# 1.3 Orden de modificaciones
sql(f"select public.laboral_modificar_salario('{r10a}','2026-09-20',420)", 'admin')
falla_con(f"select public.laboral_modificar_salario('{r10a}','2026-09-10',430)", 'admin', 'posterior a la última modificación', 'H3: una modificación anterior a la última vigente: rechazada')
falla_con(f"select public.laboral_modificar_salario('{r10a}','2026-09-20',430)", 'admin', 'posterior a la última modificación', 'H3: misma fecha que la última: rechazada')
sql(f"select public.laboral_registrar_baja('{r10a}','2026-09-30','2')", 'admin')
ok(val(f"select concat_ws('|', empresa_id, coalesce(registro_patronal_id::text,'-'), coalesce(fecha_alta_imss::text,'-'), coalesce(sdi_imss::text,'-'), coalesce(numero_interno_trabajador,'-'), coalesce(fecha_antiguedad::text,'-'), estatus) from public.personal where id='{P['P10']}'")
   == f'{E2}|-|-|-|-|-|Activo', 'H2: la ficha refleja solo la relación principal (sin SDI, alta, número ni antigüedad de la anterior)')
sql(f"select public.laboral_registrar_baja('{r10b}','2026-10-15','1')", 'admin')
ok(val(f"select concat_ws('|', empresa_id, coalesce(registro_patronal_id::text,'-'), estatus, fecha_baja) from public.personal where id='{P['P10']}'") == f'{E2}|-|Baja|2026-10-15',
   'H2: sin relaciones vigentes la ficha muestra la última baja')
# 2.1 Salario mínimo por zona del RP
sql(f"update public.empresas_registros_patronales set zona_salario_minimo='zlfn' where id='{RP3}'", 'admin')
falla_con(f"select public.laboral_registrar_ingreso('{P['P11']}','{E2}','{RP3}','2026-10-01',null,400)", 'admin', 'zona libre de la frontera norte', 'H5: en un RP de la frontera norte el piso es el salario mínimo de la ZLFN')
r11 = val(f"select public.laboral_registrar_ingreso('{P['P11']}','{E2}','{RP3}','2026-10-01',null,450,null,'1','0','0','001','5')", 'admin')
ok(len(r11) == 36, 'H5: con SBC sobre el mínimo de la ZLFN se acepta')
m11 = val(f"select id from public.idse_movimientos where relacion_laboral_id='{r11}'")

print('--- V3: hallazgos de la segunda revisión')
ok(val(f"select count(*) from public.relaciones_laborales where personal_id='{P['P12']}' and estado='vigente'") == '2'
   and val(f"select coalesce(relacion_laboral_id::text,'sin enlace') from public.personal_registros_pago where personal_id='{P['P12']}' and sueldo=700") == 'sin enlace',
   'V3-1: migración: esquema sin RP con dos relaciones en la empresa queda sin enlazar')
sql(f"select public.laboral_registrar_ingreso('{P['P12']}','{E1}',null,'2026-10-01')", 'admin')
ok(val(f"select coalesce(relacion_laboral_id::text,'sin enlace') from public.personal_registros_pago where personal_id='{P['P12']}' and sueldo=700") == 'sin enlace',
   'V3-1: un ingreso nuevo sin RP no se queda con un esquema ambiguo')
rel9 = val(f"select id from public.relaciones_laborales where personal_id='{P['P9']}' and registro_patronal_id='{RP2}'")
falla_con(f"select public.laboral_corregir_datos('{rel9}', '{{\"fecha_ingreso\":\"2025-09-30\"}}', 'x')", 'admin', 'posterior a la baja', 'V3-3: ingreso corregido después de la baja: rechazado')
falla_con(f"select public.laboral_corregir_datos('{rel9}', '{{\"fecha_ingreso\":null}}', 'x')", 'admin', 'no puede quedar vacía', 'V3-3: ingreso corregido vacío: rechazado')
falla_con(f"select public.laboral_corregir_datos('{rel6}', '{{\"sbc\":10000}}', 'x')", 'admin', 'tope de 25 UMA', 'V3-3: SBC corregido arriba del tope: rechazado')
falla_con(f"select public.laboral_corregir_datos('{rel6}', '{{\"sbc\":100}}', 'x')", 'admin', 'salario mínimo', 'V3-3: SBC corregido abajo del mínimo de su fecha: rechazado')
out, err = sql(f"select public.laboral_corregir_datos('{rel6}', '{{\"sbc\":500}}', 'Dato del expediente')", 'admin')
ok('ERROR' not in err and val(f"select sbc from public.relaciones_laborales where id='{rel6}'") == '500.00', 'V3-3: SBC corregido dentro de límites: aceptado', err[:120])

print('--- V3.1: relación principal')
sql(f"select public.laboral_registrar_ingreso('{P['P5']}','{E1}','{RP2}','2026-10-12',null,400,null,'1','0','0','020','55')", 'admin')
ok(val(f"select concat_ws('|', registro_patronal_id, fecha_alta_imss, sdi_imss) from public.personal where id='{P['P5']}'") == f'{RP2}|2026-10-12|400.00',
   'V3.1: quien solo tenía relación de efectivo y recibe alta IMSS: la ficha muestra la relación con RP')
r13a = val(f"select id from public.relaciones_laborales where personal_id='{P['P13']}'")
r13b = val(f"select public.laboral_registrar_ingreso('{P['P13']}','{E2}','{RP3}','2026-10-12',null,450,null,'1','0','0','030','66')", 'admin')
ok(val(f"select concat_ws('|', empresa_id, coalesce(registro_patronal_id::text,'-'), coalesce(fecha_alta_imss::text,'-')) from public.personal where id='{P['P13']}'") == f'{E1}|-|-',
   'V3.1: efectivo vigente en A + relación con RP en B: la ficha NO cambia de empresa')
sql(f"select public.laboral_registrar_baja('{r13a}','2026-10-31','2')", 'admin')
ok(val(f"select concat_ws('|', empresa_id, registro_patronal_id, fecha_alta_imss, estatus) from public.personal where id='{P['P13']}'") == f'{E2}|{RP3}|2026-10-12|Activo',
   'V3.1: si la empresa de la ficha ya no tiene relación vigente, la ficha pasa a la relación con RP de la otra')

print('--- IDSE: validación, archivo, presentación y resultado')
r7 = val(f"select public.laboral_registrar_ingreso('{P['P7']}','{E1}','{RP1}','2026-10-20', null, 380.5, null, '1', '0', '0', '045', '77')", 'admin')
filas = val(f"select count(*)||'|'||bool_or('El registro patronal no tiene número de guía IDSE' = any(errores)) from public.idse_validar('{RP1}')", 'admin')
ok(filas == '2|true', 'sin guía IDSE la validación lo señala', filas)
falla_con(f"select public.idse_generar_archivo('{RP1}')", 'admin', 'faltan datos', 'con errores no se genera nada')
sql(f"update public.empresas_registros_patronales set guia_idse='40001' where id='{RP1}'", 'admin')
ok('Contiene Ñ' in val(f"select array_to_string(avisos,';') from public.idse_validar('{RP1}') where personal_id='{P['P7']}'", 'admin'), 'la Ñ se avisa antes de generar')
# 2.2 Selección exacta
m4 = val(f"select id from public.idse_movimientos where relacion_laboral_id='{rel4}' and tipo_movimiento='08'")
falla_con(f"select public.idse_generar_archivo('{RP1}','08',array['{m4}','{m11}']::uuid[])", 'admin', 'no están disponibles', 'H6: un movimiento de otro RP en la selección: no se genera nada')
falla_con(f"select public.idse_generar_archivo('{RP1}','08',array['{m4}','{m4}']::uuid[])", 'admin', 'repetidos', 'H6: selección con repetidos: rechazada')
falla_con(f"select public.idse_generar_archivo('{RP1}','08',array[]::uuid[])", 'admin', 'no seleccionaste', 'H6: selección vacía: rechazada')
ok(val(f"select count(*) from public.idse_archivos") == '0', 'H6: ninguna selección inválida dejó archivo')
arch1 = val(f"select public.idse_generar_archivo('{RP1}','08',array['{m4}']::uuid[])", 'nomina')
ok(val(f"select num_registros||'|'||(nombre_archivo like '%.dat')::text from public.idse_archivos where id='{arch1}'") == '1|true', 'H6: selección válida: el archivo trae exactamente lo elegido (.dat)')
sql(f"select public.idse_cancelar_archivo('{arch1}','Prueba de selección')", 'admin')
arch = val(f"select public.idse_generar_archivo('{RP1}')", 'nomina')
cont = val(f"select replace(replace(contenido, E'\\r', '<CR>'), E'\\n', '<LF>') from public.idse_archivos where id='{arch}'", 'nomina')
lineas = cont.split('<CR><LF>')[:-1]
ok(len(lineas) == 3 and all(len(l) == 168 for l in lineas), '3 líneas (2 movimientos + final) de 168 posiciones con CRLF', str([len(l) for l in lineas]))
l1 = next(l for l in lineas if 'L#PEZ' in l or 'LOPEZ' in l)
l2 = next(l for l in lineas if 'MU#OZ' in l)
ok(l1[0:11] == 'Y1234567101' and l1[11:22] == '32345678904' and l1[22:49].rstrip() == 'LOPEZ' and l1[76:103].rstrip() == 'JUAN', 'RP, NSS, apellido sin acento y nombre en su posición')
ok(l1[103:109] == '040000' and l1[115:118] == '100' and l1[118:126] == '01102026' and l1[126:129] == '012', 'SBC, tipo de trabajador/salario/jornada, fecha DDMMAAAA y UMF', l1[103:129])
ok(l1[131:138] == '0840001' and l1[138:148] == '       204' and l1[149:167] == 'LOPE900202HDFPRN05' and l1[167] == '9', 'tipo 08 + guía, clave a la derecha, CURP y 9 final')
ok(l2[22:49].rstrip() == 'MU#OZ' and l2[49:76].rstrip() == 'PE#A' and l2[76:103].rstrip() == 'ANA SOFIA' and l2[103:109] == '038050', 'Ñ → #, acentos fuera y SBC con centavos', l2[22:109])
t = lineas[2]
ok(t[0:13] == '*' * 13 and t[56:62] == '000002' and t[133:138] == '40001' and t[167] == '9', 'renglón final: asteriscos, total, guía y 9')
ok(val(f"select (hash_sha256 = encode(sha256(convert_to(contenido,'UTF8')),'hex'))::text from public.idse_archivos where id='{arch}'", 'admin') == 'true', 'la huella SHA-256 corresponde al contenido')
falla_con(f"select public.idse_generar_archivo('{RP1}')", 'admin', 'no hay movimientos pendientes', 'un movimiento no entra en dos archivos')
falla_con(f"select public.laboral_anular_evento((select evento_id from public.idse_movimientos where relacion_laboral_id='{r7}'),'x')", 'admin', 'en_archivo', 'no se anula un ingreso cuyo movimiento ya está en un archivo')
sql(f"select public.idse_cancelar_archivo('{arch}','Faltaba una persona')", 'admin')
ok(val(f"select count(*) from public.idse_movimientos where registro_patronal_id='{RP1}' and estado='pendiente'", 'admin') == '2', 'cancelar un archivo regresa sus movimientos a pendientes')
arch2 = val(f"select public.idse_generar_archivo('{RP1}')", 'admin')
falla_con(f"select public.idse_registrar_resultado('{arch2}')", 'admin', 'primero marca el archivo', 'no hay resultado sin presentación')
sql(f"select public.idse_marcar_presentado('{arch2}','LOTE-123','2026-10-21')", 'admin')
m7 = val(f"select id from public.idse_movimientos where relacion_laboral_id='{r7}'")
sql(f"select public.idse_registrar_resultado('{arch2}', '[{{\"movimiento_id\":\"{m7}\",\"motivo\":\"NSS no vigente\"}}]', 'ACUSE-9', '2026-10-22')", 'admin')
ok(val(f"select string_agg(estado, ',' order by estado) from public.idse_movimientos where archivo_id='{arch2}'") == 'confirmado,rechazado', 'resultado: uno confirmado y uno rechazado')
falla_con(f"select public.laboral_anular_evento((select evento_id from public.idse_movimientos where relacion_laboral_id='{rel4}' and tipo_movimiento='08'),'x')", 'admin', 'confirmado', 'un ingreso confirmado por el IMSS no se anula')
arch3 = val(f"select public.idse_generar_archivo('{RP1}')", 'admin')
ok(val(f"select num_registros from public.idse_archivos where id='{arch3}'") == '1', 'el rechazado se reenvía en un archivo nuevo')
ok(val(f"select count(*) from public.idse_archivo_renglones where movimiento_id='{m7}'") == '3', 'la traza guarda cada archivo en el que viajó el movimiento')
falla_con(f"select set_config('beehuman.laboral','on',true); update public.idse_archivos set contenido='x' where id='{arch2}'", None, 'no cambia', 'el contenido de un archivo generado no cambia')

print('--- Historial por rol y aislamiento')
h = val(f"select count(*)||'|'||bool_or(valores_nuevos ? 'sbc') from public.laboral_historial('{P['P1']}')", 'admin')
ok(h.endswith('|true'), 'Administrador ve el historial con importes', h)
h = val(f"select count(*)||'|'||coalesce(bool_or(valores_nuevos ? 'sbc'),false) from public.laboral_historial('{P['P1']}')", 'consulta')
ok(h.split('|')[0] != '0' and h.endswith('|false'), 'Consulta ve el historial sin importes', h)
ok(val(f"select count(*) from public.laboral_historial('{P['P1']}')", 'coord') != '0', 'Coordinador ve el historial de su equipo')
ok(val(f"select count(*) from public.laboral_historial('{P['P2']}')", 'coord') == '0', 'Coordinador no ve a quien no es de su equipo')
ok(val(f"select count(*) from public.laboral_historial('{P['P1']}')", 'admin2') == '0', 'otro tenant no ve el historial')
falla_con(f"select public.laboral_registrar_baja('{rel4}','2026-12-01','2')", 'admin2', 'no encontrada', 'otro tenant no da de baja')
falla_con(f"select * from public.idse_validar('{RP1}')", 'admin2', 'no encontrado', 'otro tenant no ve la bandeja de un RP ajeno')
falla_con(f"select public.laboral_registrar_ingreso('{P['PX']}','{E1}','{RP1}','2026-10-01')", 'admin', 'persona no encontrada', 'no se registra un ingreso de una persona de otro tenant')

print('--- Prima de riesgo y parámetros')
sql(f"select public.prima_riesgo_registrar('{RP1}', 2.59840, 'II', '2026-03-01')", 'admin')
falla_con(f"select public.prima_riesgo_registrar('{RP1}', 2.1, 'II', '2026-02-01')", 'admin', 'debe iniciar después', 'una prima no sobrescribe una vigencia anterior')
falla_con(f"select public.prima_riesgo_registrar('{RP1}', 2.1, 'II', '2027-03-01')", 'nomina', 'tu rol no permite', 'solo el Administrador registra la prima')
ok(val("select public.parametro_vigente('UMA_DIARIA','2026-01-15')||'|'||public.parametro_vigente('UMA_DIARIA','2026-02-01')", 'consulta') == '113.1400|117.3100', 'la UMA cambia el 1 de febrero')
falla_con("insert into public.parametros_generales (clave, valor, vigente_desde, fuente) values ('UMA_DIARIA', 1, '2026-06-01', 'x')", None, 'conflicting key', 'no se traslapan vigencias de un parámetro')

print('--- Reversión')
ok(val(DEF_PRINCIPAL) != def_v3, 'la v3.1 sí cambió la función de relación principal')
salida = archivo(REV31)
ok('ERROR' not in salida and val(DEF_PRINCIPAL) == def_v3, 'la reversión de la v3.1 restaura exactamente la función de la v3', salida[:120])
salida = archivo(REV)
ok('reversión los destruiría' in salida and val("select to_regclass('public.eventos_laborales') is not null") == 't',
   'H7: con operaciones reales la reversión se bloquea sin confirmación expresa', salida[salida.find('ERROR'):][:120])
salida = archivo(REV, "set beehuman.reversion_con_datos = 'confirmo';\n")
ok('ERROR' not in salida, 'con confirmación expresa la reversión se aplica', salida[:200])
ok(huella() == H0, 'la reversión deja el esquema idéntico al de antes')
salida = archivo(MIG)
ok('ERROR' not in salida, 'la migración se puede volver a aplicar', salida[salida.find('ERROR'):][:150])
salida = archivo(REV)
ok('ERROR' not in salida and huella() == H0, 'sin operaciones (solo migrados) la reversión es ordinaria y deja el esquema idéntico', salida[salida.find('ERROR'):][:150])
archivo(MIG)
sql(f"select public.prima_riesgo_registrar('{RP1}', 2.5, 'II', '2026-03-01')", 'admin')
salida = archivo(REV)
ok('1 primas de riesgo' in salida and val("select to_regclass('public.prima_riesgo_rp') is not null") == 't', 'V3-2: una prima de riesgo capturada bloquea la reversión', salida[salida.find('ERROR'):][:160])
salida = archivo(REV, "set beehuman.reversion_con_datos = 'confirmo';\n")
archivo(MIG)
sql(f"update public.empresas_registros_patronales set guia_idse='40001' where id='{RP2}'", 'admin')
salida = archivo(REV)
ok('1 registros patronales con guía' in salida, 'V3-2: la guía IDSE capturada en un RP también bloquea la reversión', salida[salida.find('ERROR'):][:160])
salida = archivo(REV, "set beehuman.reversion_con_datos = 'confirmo';\n")
ok('ERROR' not in salida and huella() == H0, 'tras confirmar, el esquema público queda como antes (se conservan el respaldo y btree_gist)')
ok(val("select count(*) from respaldo.personal_ficha_20261104") != '0', 'el respaldo de la ficha se conserva tras revertir')

fallas = [n for n, c in res if not c]
print(f"\n{len(res) - len(fallas)}/{len(res)} pruebas correctas")
sys.exit(1 if fallas else 0)
