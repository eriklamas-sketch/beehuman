"""Pruebas de base de B1 (revisión de Nómina) en la base LOCAL desechable (puerto 55432, base bh)
con Ola 1 + fase 1 + B2 + B1. Criterios definidos antes de ejecutar:
  S1 El tablero lista a cada coordinador con gente en la empresa (aunque no abra su hoja); solo Administrador y Nómina.
  S2 «Aceptar sugeridos» acepta solo pendientes con sugerencia de la versión vigente de una hoja enviada.
  S3 Decidir un importe: solo versión vigente de hoja enviada; no descartados ni sin importe; no negativos.
  S4 Recalcular respeta lo modificado siempre y lo aceptado mientras el sugerido no cambie.
  S5 Procesar exige hojas enviadas, importes aceptados o modificados y firmas requeridas; dice qué falta; sin forma de saltarlo.
Uso: python3 pruebas_b1.py"""
import subprocess, json, sys, datetime, os

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
res = []
def sql(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    return '\n'.join(l for l in p.stdout.splitlines() if l not in ('', 'SET')), p.stderr.strip()
def val(q, user=None, replica=False):
    out, err = sql(q, user, replica)
    if err: raise RuntimeError(err)
    return out.splitlines()[-1] if out else ''
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))
def falla_con(q, user, texto, n):
    out, err = sql(q, user); ok(err and texto.lower() in err.lower(), n, (err.split('\n')[0][:140] if err else 'NO FALLÓ'))

T = '2a000000-0000-4000-8000-000000000001'
U = {k: f'2b000000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['admin', 'nomina', 'coordA', 'coordB', 'consulta'], 1)}
E1 = '2c000000-0000-4000-8000-000000000001'; SEM = '2e000000-0000-4000-8000-000000000007'; CL = '2f000000-0000-4000-8000-000000000001'
P = {k: f'2a100000-0000-4000-8000-0000000000{i:02d}' for i, k in enumerate(['CA', 'CB', 'X', 'Y', 'Z'], 1)}
HE, DESC, OBS = '2d000000-0000-4000-8000-000000000001', '2d000000-0000-4000-8000-000000000002', '2d000000-0000-4000-8000-000000000003'
hoy = datetime.date.fromisoformat(val('select public.hoy_mx()'))
lunes = hoy + datetime.timedelta(days=(7 - hoy.weekday()) % 7 or 7); d = lambda n: (lunes + datetime.timedelta(days=n)).isoformat()
seed = f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B1');
insert into auth.users (id, email) select v, k||'.b1@beehuman.invalid' from (values {','.join(f"('{v}'::uuid,'{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E1}','{T}','EMPRESA B1');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{CL}','{T}','IMSS');
"""
for k in P:
    co = 'null' if k in ('CA', 'CB') else (f"'{P['CB']}'" if k == 'Z' else f"'{P['CA']}'")
    seed += f"insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id) values ('{P[k]}','{T}','{E1}','PERSONA {k}','B1-{k}',{co});\n"
    seed += f"insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado) values ('{P[k][:-2]}9{P[k][-1]}','{T}','{P[k]}','{E1}','2025-01-01','vigente');\n"
for k, su in [('X', 5600), ('Y', 2800)]:
    seed += (f"insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo) values "
             f"('{T}','{P[k]}','{P[k][:-2]}9{P[k][-1]}','{E1}','{CL}','{SEM}',{su},'bruto',7,'2025-01-01',true);\n")
seed += f"""
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['admin']}','{T}','administrador',null),('{U['nomina']}','{T}','nomina',null),
 ('{U['coordA']}','{T}','coordinador','{P['CA']}'),('{U['coordB']}','{T}','coordinador','{P['CB']}'),('{U['consulta']}','{T}','consulta',null);
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, public.hoy_mx(), 'carga_inicial', 'B1' from public.personal where tenant_id='{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
 ('{HE}','{T}','{E1}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),
 ('{DESC}','{T}','{E1}','Descuento','DESC','importe','descuento','tarifa',1,null,2),
 ('{OBS}','{T}','{E1}','Capacitación','CAP','horas','otro','sin_importe',null,null,3);
"""
o, e = sql(seed, replica=True)
if e: print(e); sys.exit(1)
PER = val(f"select public.inc_crear_periodo('{E1}','{SEM}','{lunes}','{d(6)}')", 'nomina')

print('== S1 Tablero ==')
tb = lambda u: val(f"select string_agg(coordinador||':'||personas||':'||estado||':'||version_actual, ' | ' order by coordinador) from public.inc_tablero_periodo('{PER}')", u)
ok(tb('nomina') == 'PERSONA CA:2:sin_abrir:0 | PERSONA CB:1:sin_abrir:0', 'S1 Lista a cada coordinador con su gente aunque no haya abierto su hoja', tb('nomina'))
H = val(f"select public.inc_abrir_hoja('{PER}')", 'coordA')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad, motivo) values ('{H}','{P['X']}','{d(0)}','{HE}',2,null),('{H}','{P['Y']}','{d(0)}','{HE}',2,null),('{H}','{P['X']}','{d(1)}','{DESC}',50,'Herramienta'),('{H}','{P['X']}','{d(2)}','{OBS}',3,null)", 'coordA')
V1 = val(f"select public.inc_enviar_hoja('{H}')", 'coordA')
ok(tb('admin').startswith('PERSONA CA:2:enviada:1'), 'S1 Refleja el envío (versión 1)', tb('admin'))
for r in ('coordA', 'consulta'):
    falla_con(f"select * from public.inc_tablero_periodo('{PER}')", r, 'sin permiso', f'S1 {r}: no puede ver el tablero')

print('== S2/S3 Decisiones ==')
lid = lambda per, c: val(f"select id from public.inc_importes where version_id='{V1}' and personal_id='{P[per]}' and concepto_id='{c}'", 'nomina')
X_HE, Y_HE, X_DESC, X_OBS = lid('X', HE), lid('Y', HE), lid('X', DESC), lid('X', OBS)
falla_con(f"select public.inc_decidir_importe('{X_OBS}', null)", 'nomina', 'no lleva importe', 'S3 Una línea «sin importe» no se decide')
falla_con(f"select public.inc_decidir_importe('{X_HE}', -5)", 'nomina', 'negativo', 'S3 No se aceptan importes negativos')
falla_con(f"select public.inc_decidir_importe('{X_HE}', 10)", 'coordA', 'sin permiso', 'S3 El coordinador no decide importes')
val(f"select public.inc_decidir_importe('{Y_HE}', 999)", 'nomina')
n = val(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina')
est = val(f"select string_agg(substr(p.nombre_completo,9)||'-'||k.abreviatura||'='||i.origen, ',' order by p.nombre_completo, k.abreviatura) from public.inc_importes i join public.personal p on p.id=i.personal_id join public.inc_conceptos k on k.id=i.concepto_id where i.version_id='{V1}'", 'nomina')
ok(n == '2' and est == 'X-CAP=sin_importe,X-DESC=aceptado,X-HE=aceptado,Y-HE=modificado', 'S2 «Aceptar sugeridos» acepta solo los pendientes con sugerencia (no toca modificado ni sin importe)', f'{n}: {est}')
falla_con(f"select public.inc_aceptar_sugeridos('{V1}')", 'coordA', 'sin permiso', 'S2 El coordinador no puede aceptar sugeridos')

print('== S4 Recálculo ==')
val(f"select public.inc_capturar_sueldo_manual('{PER}','{P['Z']}',100)", 'nomina')  # dispara recálculo de las versiones vigentes
est2 = val(f"select string_agg(substr(p.nombre_completo,9)||'-'||k.abreviatura||'='||i.origen||':'||coalesce(i.final::text,'-'), ',' order by p.nombre_completo, k.abreviatura) from public.inc_importes i join public.personal p on p.id=i.personal_id join public.inc_conceptos k on k.id=i.concepto_id where i.version_id='{V1}'", 'nomina')
ok(est2 == 'X-CAP=sin_importe:-,X-DESC=aceptado:50.00,X-HE=aceptado:400.00,Y-HE=modificado:999.00', 'S4 Recalcular respeta lo aceptado (sugerido igual) y lo modificado', est2)
val(f"update public.personal_registros_pago set sueldo = 7000 where personal_id='{P['X']}'", 'admin')
val(f"select public.inc_capturar_sueldo_manual('{PER}','{P['Z']}',100)", 'nomina')
est3 = val(f"select origen||':'||coalesce(final::text,'-')||':'||sugerido from public.inc_importes where id='{X_HE}'", 'nomina')
ok(est3 == 'pendiente:-:500.00', 'S4 Si el sugerido cambia (cambió el sueldo), lo aceptado vuelve a «por decidir»', est3)
ok(val(f"select origen||':'||final from public.inc_importes where id='{Y_HE}'", 'nomina') == 'modificado:999.00', 'S4 Lo modificado se respeta aunque cambie el sugerido')

print('== S3 Versión vigente y estado de la hoja ==')
val(f"select public.inc_devolver_hoja('{H}','Revisar horas','nomina')", 'nomina')
falla_con(f"select public.inc_decidir_importe('{X_HE}', null)", 'nomina', 'versión vigente', 'S3 Hoja devuelta: no se deciden importes')
falla_con(f"select public.inc_aceptar_sugeridos('{V1}')", 'nomina', 'versión vigente', 'S3 Hoja devuelta: tampoco «aceptar sugeridos»')
V2 = val(f"select public.inc_enviar_hoja('{H}')", 'coordA')
falla_con(f"select public.inc_decidir_importe('{X_HE}', null)", 'nomina', 'versión vigente', 'S3 Un importe de la versión anterior ya no se decide')
ok(val(f"select public.inc_aceptar_sugeridos('{V2}')", 'nomina') == '3', 'S2 La versión vigente sí se decide')

print('== S5 Procesar solo con la prenómina completa ==')
falt = lambda: val(f"select coalesce(string_agg(tipo||': '||detalle, ' | '), '') from public.inc_faltantes_procesar('{PER}')", 'nomina')
f1 = falt()
ok('PERSONA CB: no ha abierto su hoja' in f1 and 'Designa al responsable de Nómina' in f1, 'S5 Dice exactamente qué falta (hoja sin abrir, responsable de Nómina)', f1)
falla_con(f"select public.inc_marcar_procesado('{PER}')", 'nomina', 'no se puede procesar', 'S5 No permite procesar mientras falte algo')
HB = val(f"select public.inc_abrir_hoja('{PER}')", 'coordB')
val(f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values ('{HB}','{P['Z']}','{d(3)}','{HE}',1)", 'coordB')
val(f"select public.inc_enviar_hoja('{HB}')", 'coordB')
val(f"update public.inc_parametros set responsable_nomina_user='{U['nomina']}', responsable_rh_user='{U['admin']}' where empresa_id='{E1}'", 'admin')
f2 = falt()
ok('PERSONA Z · Horas extra: importe por decidir' in f2 and 'PERSONA CA: falta la firma de Nómina' in f2 and 'PERSONA CB: falta la firma de RH' in f2,
   'S5 Lista importes por decidir y cada firma faltante (Nómina y RH designados)', f2[:200])
val(f"select public.inc_aceptar_sugeridos((select id from public.inc_versiones where hoja_id='{HB}'))", 'nomina')
for hh in (H, HB):
    val(f"select public.inc_firmar_hoja('{hh}','nomina')", 'nomina')
falla_con(f"select public.inc_marcar_procesado('{PER}')", 'nomina', 'falta la firma de RH', 'S5 Con firmas de RH pendientes: sigue sin procesar')
for hh in (H, HB):
    val(f"select public.inc_firmar_hoja('{hh}','rh')", 'admin')
ok(val(f"select count(*) from public.inc_faltantes_procesar('{PER}')", 'nomina') == '0', 'S5 Completo: ya no falta nada')
ok(val(f"select public.inc_marcar_procesado('{PER}')", 'nomina') == 'Periodo marcado como procesado.', 'S5 Ahora sí se procesa')
for r in ('coordA', 'consulta'):
    falla_con(f"select * from public.inc_faltantes_procesar('{PER}')", r, 'sin permiso', f'S5 {r}: no consulta los faltantes')
X2 = val(f"select id from public.inc_importes where version_id='{V2}' and personal_id='{P['X']}' and concepto_id='{HE}'", 'nomina')
falla_con(f"select public.inc_decidir_importe('{X2}', 1)", 'nomina', 'versión vigente', 'S3 Periodo procesado: los importes quedan cerrados')

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
