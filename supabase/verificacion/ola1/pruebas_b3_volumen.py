"""B3 · C15 · Rendimiento del concentrado con 500 personas (base LOCAL desechable, datos ficticios).
Escenario: 1 empresa, 500 personas con relación vigente, 5 coordinadores con 100 personas cada uno y su hoja
ENVIADA (celdas, horas extra y bono), la mitad con dos esquemas de pago (IMSS bruto y EFECTIVO neto),
100 préstamos con descuento en el periodo y 50 movimientos laborales.
Criterio: inc_concentrado_periodo responde en menos de 3 s (mediana de 5 llamadas, ya en caché) y devuelve 505
personas (500 + 5 coordinadores, que también tienen relación en la empresa).
Nota: en local; en beehuman-pruebas se repite con el tenant PILOTO SINTETICO 500 al aplicar la etapa 5.
Uso: DB=bh python3 pruebas_b3_volumen.py"""
import subprocess, json, sys, os, time, datetime, statistics

DB = os.environ.get('DB', 'bh')
PSQL = ['psql', '-X', '-q', '-At', '-v', 'ON_ERROR_STOP=1', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', DB]
def val(q, user=None, replica=False):
    pre = 'begin;\n' + ("set local session_replication_role = replica;\n" if replica else '')
    if user: pre += f"select set_config('request.jwt.claims', '{json.dumps({'sub': U[user]})}', true);\nset local role authenticated;\n"
    p = subprocess.run(PSQL, input=pre + q + ';\ncommit;', capture_output=True, text=True)
    err = '\n'.join(l for l in p.stderr.splitlines() if not l.startswith('NOTICE:')).strip()
    if err: raise RuntimeError(err)
    out = [l for l in p.stdout.splitlines() if l not in ('', 'SET')]; return out[-1] if out else ''
res = []
def ok(c, n, d=''):
    res.append((n, bool(c), d)); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

T = '3c000000-0000-4000-8000-000000000001'
U = {'nomina': '3c100000-0000-4000-8000-000000000001', **{f'c{i}': f'3c100000-0000-4000-8000-0000000001{i:02d}' for i in range(5)}}
E, SEM, IM, EF, HE, BO = ('3c200000-0000-4000-8000-000000000001', '3c300000-0000-4000-8000-000000000001', '3c400000-0000-4000-8000-000000000001',
                          '3c400000-0000-4000-8000-000000000002', '3c500000-0000-4000-8000-000000000001', '3c500000-0000-4000-8000-000000000002')
L = datetime.date.fromisoformat(val("select (date_trunc('week', public.hoy_mx() + 7))::date"))
ini, fin = L.isoformat(), (L + datetime.timedelta(days=6)).isoformat()
t0 = time.time()
val(f"""
insert into public.tenants (id, nombre) values ('{T}','TENANT B3 VOLUMEN');
insert into auth.users (id, email) select v::uuid, k||'.b3v@beehuman.invalid' from (values {','.join(f"('{v}','{k}')" for k, v in U.items())}) x(v,k);
insert into public.empresas (id, tenant_id, nombre) values ('{E}','{T}','EMPRESA VOLUMEN B3');
insert into public.periodicidades (id, tenant_id, nombre, dias_default) values ('{SEM}','{T}','SEMANAL',7);
insert into public.clasificaciones_personal (id, tenant_id, nombre) values ('{IM}','{T}','IMSS'),('{EF}','{T}','EFECTIVO');
-- 5 coordinadores (c0..c4) y 500 personas
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id)
  select ('3c600000-0000-4000-8000-' || lpad(i::text, 12, '0'))::uuid, '{T}', '{E}', 'COORDINADOR V' || i, 'CV' || i, null from generate_series(0, 4) i;
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, empleado_id, coordinador_id)
  select ('3c700000-0000-4000-8000-' || lpad(i::text, 12, '0'))::uuid, '{T}', '{E}', 'PERSONA V' || lpad(i::text, 3, '0'), 'PV' || i,
         ('3c600000-0000-4000-8000-' || lpad((i % 5)::text, 12, '0'))::uuid from generate_series(1, 500) i;
insert into public.relaciones_laborales (tenant_id, personal_id, empresa_id, fecha_ingreso, estado, numero_interno)
  select '{T}', id, '{E}', '2025-01-01', 'vigente', right(empleado_id, 10) from public.personal where tenant_id = '{T}';
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  select '{T}', rl.personal_id, rl.id, '{E}', '{IM}', '{SEM}', 2800, 'bruto', 7, '2025-01-01', true from public.relaciones_laborales rl where rl.tenant_id = '{T}';
insert into public.personal_registros_pago (tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  select '{T}', rl.personal_id, rl.id, '{E}', '{EF}', '{SEM}', 700, 'neto', 7, '2025-01-01', true
    from public.relaciones_laborales rl join public.personal p on p.id = rl.personal_id where rl.tenant_id = '{T}' and p.empleado_id ~ '^PV' and right(p.empleado_id, 1) in ('0','2','4','6','8');
insert into public.usuarios_tenant (user_id, tenant_id, rol, personal_id) values ('{U['nomina']}','{T}','nomina',null),
  {','.join(f"('{U[f'c{i}']}','{T}','coordinador','3c600000-0000-4000-8000-{i:012d}')" for i in range(5))};
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial) values ('{E}','{T}','2025-01-01');
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
  select tenant_id, id, coordinador_id, '2025-01-01', 'carga_inicial', 'B3V' from public.personal where tenant_id = '{T}' and coordinador_id is not null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden) values
  ('{HE}','{T}','{E}','Horas extra','HE','horas','horas_extra','beehuman',null,2,1),('{BO}','{T}','{E}','Bono','BON','importe','otro','tarifa',1,null,2);
-- 50 movimientos laborales en el periodo
insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, origen)
  select '{T}', rl.personal_id, rl.id, 'modificacion_salario', '{ini}'::date + 2, 'pantalla' from public.relaciones_laborales rl
    join public.personal p on p.id = rl.personal_id where rl.tenant_id = '{T}' and p.empleado_id ~ '^PV' and right(p.empleado_id, 1) = '7';
""", replica=True)
PER = val(f"select public.inc_crear_periodo('{E}','{SEM}','{ini}','{fin}')", 'nomina')
for i in range(5):
    u = f'c{i}'; co = f'3c600000-0000-4000-8000-{i:012d}'
    H = val(f"select public.inc_abrir_hoja('{PER}')", u)
    # Los datos se arman aquí y se insertan como el coordinador (con sus validaciones y RLS).
    gente = [(r.split('|')[0], int(r.split('|')[1])) for r in val(f"select string_agg(id || '|' || substr(empleado_id, 3), ',') from public.personal where coordinador_id = '{co}'").split(',')]
    dia = lambda n: (L + datetime.timedelta(days=n)).isoformat()
    celdas = ','.join(f"('{H}','{pid}','{dia(n % 7)}','{'FIDVP'[n % 5]}')" for pid, n in gente)
    cants = ','.join(f"('{H}','{pid}','{dia(k)}','{HE}',{1 + (n + k) % 3})" for pid, n in gente for k in range(3))
    bonos = ','.join(f"('{H}','{pid}','{dia(4)}','{BO}',150)" for pid, n in gente if n % 4 == 0)
    val(f"insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) values {celdas}; "
        f"insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad) values {cants}, {bonos}", u)
    val(f"select public.inc_enviar_hoja('{H}')", u)
for k in range(100):
    pid = f'3c700000-0000-4000-8000-{k * 5 + 1:012d}'
    rl = val(f"select id from public.relaciones_laborales where personal_id = '{pid}'")
    val(f"""select public.cred_guardar(null, '{json.dumps({'personal_id': pid, 'tipo': 'prestamo', 'referencia': f'PV-{k}', 'relacion_laboral_id': rl, 'fecha_inicio': ini,
            'periodicidad_id': SEM, 'importe_periodo': 200, 'monto_total': 1000})}'::jsonb, null)""", 'nomina')
val(f"select public.cred_descuentos_periodo('{PER}')", 'nomina')
print(f'Semilla lista en {time.time() - t0:.1f} s')
n_imp = val(f"select count(*) from public.inc_importes i join public.inc_versiones v on v.id = i.version_id join public.inc_hojas h on h.id = v.hoja_id where h.periodo_id = '{PER}'")
n_desc = val(f"select count(*) from public.cred_descuentos where periodo_id = '{PER}'")
print(f'Volumen: 505 personas, 5 hojas enviadas, {n_imp} líneas de importe, {n_desc} descuentos')

tiempos = []
for _ in range(6):
    out = val(f"""select set_config('request.jwt.claims', '{json.dumps({'sub': U['nomina']})}', true);
                  set local role authenticated;
                  select clock_timestamp() as t \\gset
                  select length(public.inc_concentrado_periodo('{PER}')::text) || '|' || extract(epoch from clock_timestamp() - :'t'::timestamptz)""")
    tiempos.append(float(out.split('|')[1])); tam = int(out.split('|')[0])
med = statistics.median(tiempos[1:])
ok(med < 3, f'C15 500 personas: mediana {med:.2f} s (< 3 s); primera llamada {tiempos[0]:.2f} s; respuesta de {tam / 1024:.0f} KB',
   ', '.join(f'{t:.2f}' for t in tiempos))
c = json.loads(val(f"select public.inc_concentrado_periodo('{PER}')", 'nomina'))
ok(c['totales']['personas'] == 505 and len(c['hojas']) == 5 and c['totales']['con_incidencias'] == 500, 'C15 Devuelve 505 personas, 5 hojas y 500 con incidencias',
   f"{c['totales']['personas']} / {len(c['hojas'])} / {c['totales']['con_incidencias']}")
ok(sum(c['totales']['dias'].values()) == 500 and c['totales']['movimientos'] == {'modificacion_salario': 50} and c['totales']['descuentos_por_decidir'] == 100,
   'C15 Cuadran 500 celdas, 50 movimientos y 100 descuentos por decidir')

# Opción B: faltantes (calcula la huella) y firma del periodo con 500 personas, < 3 s cada uno
val(f"update public.inc_parametros set responsable_nomina_user = '{U['nomina']}' where empresa_id = '{E}'", replica=True)
for v in val(f"select string_agg(v.id::text, ',') from public.inc_versiones v join public.inc_hojas h on h.id = v.hoja_id and v.numero = h.version_actual where h.periodo_id = '{PER}'").split(','):
    val(f"select public.inc_aceptar_sugeridos('{v}')", 'nomina')
    for x in (val(f"select coalesce(string_agg(a.linea_id::text||'/'||a.registro_pago_id, ','), '') from (select distinct on (linea_id) linea_id, registro_pago_id from public.inc_esquemas_asignables('{v}') order by linea_id, clasificacion) a", 'nomina') or '').split(','):
        if x: val(f"select public.inc_asignar_esquema('{x.split('/')[0]}','{x.split('/')[1]}')", 'nomina')
    val(f"select public.inc_aceptar_sugeridos('{v}')", 'nomina')
val(f"select public.cred_aceptar_descuentos('{PER}')", 'nomina')
def medir(q):
    out = val(f"""select set_config('request.jwt.claims', '{json.dumps({'sub': U['nomina']})}', true);
                  select clock_timestamp() as t \\gset
                  select ({q}) is not null as r \\gset
                  select extract(epoch from clock_timestamp() - :'t'::timestamptz)""")
    return float(out)
t_f = statistics.median([medir(f"select count(*) from public.inc_faltantes_procesar('{PER}')") for _ in range(3)])
h = val(f"select public.inc_firma_periodo_estado('{PER}')->'huella_actual'->>'total'", 'nomina')
t_fi = medir(f"select public.inc_firmar_periodo('{PER}', '{h}')")
est = val(f"select public.inc_firma_periodo_estado('{PER}')->>'estado'", 'nomina')
ok(t_f < 3 and t_fi < 3 and est == 'vigente', f'C15b Opción B con 500 personas: faltantes {t_f:.2f} s y firma {t_fi:.2f} s (< 3 s); firma vigente', est)

total = len(res); malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {total - len(malas)} de {total} verificaciones OK')
for nn, _, dd in malas: print('  FALLA:', nn, dd)
sys.exit(1 if malas else 0)
