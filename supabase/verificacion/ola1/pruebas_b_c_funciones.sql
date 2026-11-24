-- B-c · Pruebas de funciones en beehuman-pruebas (opción B: concentrado y firma única de Nómina por periodo).
-- TODO dentro de una transacción que termina en un error forzado: nada se guarda.
-- Actúa con las cuentas reales de prueba (rol authenticated + claims, como PostgREST) y sus permisos/RLS reales.
-- Datos sintéticos creados dentro de la transacción (prefijo bc…); desaparecen con el rollback.
begin;
create temp table _v(k text primary key, v text);
create temp table _r(n serial, id text, ok boolean, det text);
grant all on _v, _r to authenticated; grant usage on sequence _r_n_seq to authenticated;
insert into _v select 'T', id::text from public.tenants where nombre = 'PILOTO SINTETICO 500';
insert into _v select 'T7', id::text from public.tenants where nombre = 'TENANT SINTETICO 7D6B';
insert into _v select 'u_'||split_part(email,'@',1), id::text from auth.users
 where email in ('admin-prueba@beehuman.invalid','nomina-prueba@beehuman.invalid','coord-prueba@beehuman.invalid','consulta-prueba@beehuman.invalid','prueba-7d6b@beehuman.invalid');
insert into _v select 'AABG', personal_id::text from public.usuarios_tenant where user_id = (select v::uuid from _v where k='u_coord-prueba');
insert into _v values ('d0', (date_trunc('week', public.hoy_mx() + 21))::date::text);
insert into _v values ('E','bc000000-0000-4000-8000-000000000001'),('RP','bc000000-0000-4000-8000-000000000002'),('SEM','bc000000-0000-4000-8000-000000000003'),
 ('CL1','bc000000-0000-4000-8000-000000000004'),('CL2','bc000000-0000-4000-8000-000000000005'),('HE','bc000000-0000-4000-8000-000000000006'),('CAP','bc000000-0000-4000-8000-000000000007'),
 ('X1','bc000000-0000-4000-8000-000000000011'),('X2','bc000000-0000-4000-8000-000000000012'),('X3','bc000000-0000-4000-8000-000000000013'),
 ('R1','bc000000-0000-4000-8000-000000000021'),('R2','bc000000-0000-4000-8000-000000000022'),('R3','bc000000-0000-4000-8000-000000000023');
insert into _r(id, ok, det) select 'S0 cuentas y tenants encontrados', count(*) = 8, string_agg(k, ',') from _v where k in ('T','T7','u_admin-prueba','u_nomina-prueba','u_coord-prueba','u_consulta-prueba','u_prueba-7d6b','AABG');

-- ===== Semilla sintética (como postgres con la sesión de admin-prueba, para que los disparadores sellen autoría y tenant) =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
insert into public.empresas (id, tenant_id, nombre) select (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), 'EMPRESA SINTETICA BC CONCENTRADO';
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo)
  select (select v::uuid from _v where k='RP'), (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), 'B1234567890', true;
insert into public.periodicidades (id, tenant_id, nombre, dias_default) select (select v::uuid from _v where k='SEM'), (select v::uuid from _v where k='T'), 'SEMANAL BC', 7;
insert into public.clasificaciones_personal (id, tenant_id, nombre) select (select v::uuid from _v where k='CL1'), (select v::uuid from _v where k='T'), 'IMSS BC'
  union all select (select v::uuid from _v where k='CL2'), (select v::uuid from _v where k='T'), 'EFECTIVO BC';
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, coordinador_id)
  select (select v::uuid from _v where k=x), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'SINTETICO BC '||x, (select v::uuid from _v where k='AABG')
    from unnest(array['X1','X2','X3']) x;
select set_config('beehuman.laboral', 'on', true);   -- solo para la semilla sintética de relaciones (mismo mecanismo que las funciones de historial)
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, registro_patronal_id, numero_interno)
  select (select v::uuid from _v where k='R'||i), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='X'||i), (select v::uuid from _v where k='E'), '2025-01-01', 'vigente', (select v::uuid from _v where k='RP'), 'BC'||i
    from generate_series(1,3) i;
select set_config('beehuman.laboral', 'off', true);
insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, activo)
  select ('bc000000-0000-4000-8000-00000000003'||n)::uuid, (select v::uuid from _v where k='T'), (select v::uuid from _v where k=px), (select v::uuid from _v where k=rx), (select v::uuid from _v where k='E'),
         (select v::uuid from _v where k=cl), (select v::uuid from _v where k='SEM'), su, mo, 7, '2025-01-01', true
    from (values (1,'X1','R1','CL1',3500,'bruto'),(2,'X2','R2','CL1',2800,'bruto'),(3,'X2','R2','CL2',700,'neto'),(4,'X3','R3','CL1',2800,'bruto')) s(n,px,rx,cl,su,mo);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user)
  select (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), '2025-01-01', (select v::uuid from _v where k='u_nomina-prueba'), (select v::uuid from _v where k='u_admin-prueba');
insert into _r(id, ok, det) select 'S1 Las 3 personas sintéticas quedan asignadas al coordinador de prueba (disparador de alta)', count(*) = 3, count(*)::text
  from public.inc_asignaciones where coordinador_id = (select v::uuid from _v where k='AABG') and personal_id in (select v::uuid from _v where k in ('X1','X2','X3')) and hasta is null;
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden)
  select (select v::uuid from _v where k='HE'), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'Horas extra BC', 'HE', 'horas', 'horas_extra', 'beehuman', null::numeric, 2, 1
  union all select (select v::uuid from _v where k='CAP'), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'Capacitación BC', 'CAP', 'horas', 'otro', 'sin_importe', null::numeric, null::numeric, 2;

-- ===== Nómina crea el periodo y el crédito; el coordinador abre su hoja (todo con authenticated) =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'P', public.inc_crear_periodo((select v::uuid from _v where k='E'), (select v::uuid from _v where k='SEM'), (select v::date from _v where k='d0'), (select v::date from _v where k='d0') + 6)::text;
insert into _v select 'CR', public.cred_guardar(null, jsonb_build_object('personal_id', (select v from _v where k='X3'), 'tipo', 'fonacot', 'referencia', 'FN-BC3',
   'relacion_laboral_id', (select v from _v where k='R3'), 'fecha_inicio', (select v from _v where k='d0'), 'periodicidad_id', (select v from _v where k='SEM'), 'importe_periodo', 150), null)::text;
do $$ begin
  if (select estado from public.cred_creditos where id = (select v::uuid from _v where k='CR')) <> 'activo' then
    perform public.cred_cambiar_estado((select v::uuid from _v where k='CR'), 'activo', (select v::date from _v where k='d0'), 'Alta B-c');
  end if;
end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_coord-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'H', public.inc_abrir_hoja((select v::uuid from _v where k='P'))::text;
insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo) select (select v::uuid from _v where k='H'), (select v::uuid from _v where k='X2'), (select v::date from _v where k='d0') + 1, 'F';
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
  select (select v::uuid from _v where k='H'), (select v::uuid from _v where k=x), (select v::date from _v where k='d0'), (select v::uuid from _v where k=c), q
    from (values ('X1','HE',2),('X2','HE',1),('X3','CAP',3)) s(x,c,q);
reset role;

-- ===== Nómina: concentrado preliminar con la hoja sin enviar =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.cred_descuentos_periodo((select v::uuid from _v where k='P'));
insert into _r(id, ok, det) select 'T01 Concentrado preliminar con la hoja sin enviar avisada', c->>'estado' = 'preliminar' and jsonb_array_length(c->'avisos'->'hojas_no_incluidas') = 1
   and jsonb_array_length(c->'hojas') = 0, (c->'avisos'->'hojas_no_incluidas')::text
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
do $$ begin
  perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), (public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total'));
  insert into _r(id, ok, det) values ('T02 Con hoja sin enviar no se puede firmar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T02 Con hoja sin enviar no se puede firmar', sqlerrm like '%no se puede firmar el periodo%no ha enviado su hoja%', sqlerrm); end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_coord-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'V', public.inc_enviar_hoja((select v::uuid from _v where k='H'))::text;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.cred_descuentos_periodo((select v::uuid from _v where k='P'));
insert into _r(id, ok, det) select 'T03 Pendientes que bloquean: importes por decidir y descuento FONACOT',
   (select count(*) from jsonb_array_elements(c->'faltantes') f where f->>'tipo' = 'importe') >= 2
   and (select count(*) from jsonb_array_elements(c->'faltantes') f where f->>'tipo' = 'descuento' and f->>'detalle' like 'SINTETICO BC X3%') = 1
   and jsonb_array_length(c->'avisos'->'hojas_no_incluidas') = 0 and jsonb_array_length(c->'hojas') = 1,
   (select string_agg(f->>'tipo', ',') from jsonb_array_elements(c->'faltantes') f)
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
do $$ begin
  perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), (public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total'));
  insert into _r(id, ok, det) values ('T04 Con importes por decidir no se puede firmar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T04 Con importes por decidir no se puede firmar', sqlerrm like '%importe por decidir%', left(sqlerrm, 160)); end $$;
select public.inc_aceptar_sugeridos((select v::uuid from _v where k='V'));
select public.cred_descuentos_periodo((select v::uuid from _v where k='P'));
select public.cred_aceptar_descuentos((select v::uuid from _v where k='P'));
insert into _r(id, ok, det) select 'T05 Sin bloqueantes: solo faltan la firma de Nómina del periodo y la de RH de la hoja',
   c->'firma'->>'estado' = 'sin_firma' and jsonb_array_length(c->'faltantes') = 2
   and exists (select 1 from jsonb_array_elements(c->'faltantes') f where f->>'detalle' = 'Falta la firma de Nómina del periodo')
   and exists (select 1 from jsonb_array_elements(c->'faltantes') f where f->>'detalle' like '%falta la firma de RH (versión 1)'),
   (c->'faltantes')::text
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
insert into _r(id, ok, det) select 'T06 La huella del concentrado y la del estado de firma coinciden (misma instantánea)',
   (public.inc_concentrado_periodo((select v::uuid from _v where k='P'))->'huella'->>'total') = (public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total'), null;
insert into _r(id, ok, det) select 'T07 Las líneas sin importe no entran a la huella; sí se ven en el concentrado',
   exists (select 1 from jsonb_array_elements(c->'personas') p, jsonb_array_elements(p->'importes') i where i->>'estado' = 'sin_importe'), null
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
do $$ begin
  perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), repeat('0', 64));
  insert into _r(id, ok, det) values ('T08 Huella desactualizada: la firma se rechaza', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T08 Huella desactualizada: la firma se rechaza', sqlerrm like '%cambió mientras lo revisabas%', sqlerrm); end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
do $$ begin
  perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), (public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total'));
  insert into _r(id, ok, det) values ('T09 Administrador que no es el responsable no puede firmar el periodo', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T09 Administrador que no es el responsable no puede firmar el periodo', sqlerrm like '%solo el responsable designado de Nómina%', sqlerrm); end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _r(id, ok, det) select 'T10 Ningún evento de firma de Nómina antes de firmar', count(*) = 0, count(*)::text from public.inc_eventos where periodo_id = (select v::uuid from _v where k='P') and tipo = 'firma_nomina';
insert into _v select 'HU1', public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total';
insert into _r(id, ok, det) select 'T11 El responsable firma el periodo con la huella revisada', public.inc_firmar_periodo((select v::uuid from _v where k='P'), (select v from _v where k='HU1')) = 'Firma de Nómina del periodo registrada.', null;
insert into _r(id, ok, det) select 'T12 Firma vigente; un evento sin hoja con la huella firmada',
   (public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->>'estado') = 'vigente'
   and (select count(*) from public.inc_eventos e where e.periodo_id = (select v::uuid from _v where k='P') and e.tipo = 'firma_nomina' and e.hoja_id is null and e.huella->>'total' = (select v from _v where k='HU1')) = 1, null;
do $$ begin
  perform public.inc_firmar_hoja((select v::uuid from _v where k='H'), 'nomina');
  insert into _r(id, ok, det) values ('T13 Nómina ya no firma por hoja', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T13 Nómina ya no firma por hoja', sqlerrm like '%Nómina firma el periodo completo%', sqlerrm); end $$;
do $$ begin
  perform public.inc_firmar_hoja((select v::uuid from _v where k='H'), 'rh');
  insert into _r(id, ok, det) values ('T14 Nómina no puede firmar como RH', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T14 Nómina no puede firmar como RH', sqlerrm like '%responsable designado de rh%', sqlerrm); end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_firmar_hoja((select v::uuid from _v where k='H'), 'rh');
insert into _r(id, ok, det) select 'T15 RH firma su hoja (responsable de RH); el periodo queda listo',
   (select count(*) from public.inc_eventos where hoja_id = (select v::uuid from _v where k='H') and tipo = 'firma_rh') = 1 and c->>'estado' = 'listo' and jsonb_array_length(c->'faltantes') = 0,
   c->>'estado'
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_decidir_importe((select id from public.inc_importes where version_id = (select v::uuid from _v where k='V') and personal_id = (select v::uuid from _v where k='X1') limit 1), 999, 'Ajuste B-c');
insert into _r(id, ok, det) select 'T16 Cambio después de firmar: firma invalidada solo por «importes»; vuelve a preliminar',
   c->'firma'->>'estado' = 'invalidada' and c->'firma'->'secciones_cambiadas' = '["importes"]'::jsonb and c->>'estado' = 'preliminar'
   and exists (select 1 from jsonb_array_elements(c->'faltantes') f where f->>'detalle' like '%ya no es vigente%(cambió: importes)'),
   (c->'firma'->'secciones_cambiadas')::text
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P')) c) s;
do $$ begin
  perform public.inc_marcar_procesado((select v::uuid from _v where k='P'));
  insert into _r(id, ok, det) values ('T17 Con la firma invalidada no se puede procesar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T17 Con la firma invalidada no se puede procesar', sqlerrm like '%no se puede procesar%ya no es vigente%', left(sqlerrm, 160)); end $$;
insert into _v select 'HU2', public.inc_firma_periodo_estado((select v::uuid from _v where k='P'))->'huella_actual'->>'total';
insert into _v select 'MSG18', public.inc_firmar_periodo((select v::uuid from _v where k='P'), (select v from _v where k='HU2'));
insert into _r(id, ok, det) select 'T18 Tras el cambio, el responsable vuelve a firmar con la huella nueva',
   (select v from _v where k='MSG18') = 'Firma de Nómina del periodo registrada.'
   and (select count(*) from public.inc_eventos where periodo_id = (select v::uuid from _v where k='P') and tipo = 'firma_nomina' and hoja_id is null) = 2,
   (select v from _v where k='MSG18') || ' / firmas=' || (select count(*) from public.inc_eventos where periodo_id = (select v::uuid from _v where k='P') and tipo = 'firma_nomina' and hoja_id is null);
-- Segundo periodo sintético: firma única y procesado (en uso real cada firma es su propia transacción; aquí, un periodo por flujo).
insert into _v select 'P2', public.inc_crear_periodo((select v::uuid from _v where k='E'), (select v::uuid from _v where k='SEM'), (select v::date from _v where k='d0') + 7, (select v::date from _v where k='d0') + 13)::text;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_coord-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'H2', public.inc_abrir_hoja((select v::uuid from _v where k='P2'))::text;
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
  select (select v::uuid from _v where k='H2'), (select v::uuid from _v where k='X1'), (select v::date from _v where k='d0') + 7, (select v::uuid from _v where k='HE'), 1;
insert into _v select 'V2', public.inc_enviar_hoja((select v::uuid from _v where k='H2'))::text;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_aceptar_sugeridos((select v::uuid from _v where k='V2'));
select public.cred_descuentos_periodo((select v::uuid from _v where k='P2'));
select public.cred_aceptar_descuentos((select v::uuid from _v where k='P2'));
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_firmar_hoja((select v::uuid from _v where k='H2'), 'rh');
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'HU3', public.inc_firma_periodo_estado((select v::uuid from _v where k='P2'))->'huella_actual'->>'total';
select public.inc_firmar_periodo((select v::uuid from _v where k='P2'), (select v from _v where k='HU3'));
insert into _v select 'MSG19', public.inc_marcar_procesado((select v::uuid from _v where k='P2'));
insert into _r(id, ok, det) select 'T19 Periodo firmado y sin pendientes: se procesa y el procesado guarda la huella firmada',
   (select v from _v where k='MSG19') = 'Periodo marcado como procesado.'
   and (select huella->>'total' from public.inc_eventos where periodo_id = (select v::uuid from _v where k='P2') and tipo = 'procesado') = (select v from _v where k='HU3')
   , null;
do $$ begin
  perform public.inc_firmar_periodo((select v::uuid from _v where k='P2'), (select v from _v where k='HU3'));
  insert into _r(id, ok, det) values ('T20 Un periodo procesado no se vuelve a firmar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T20 Un periodo procesado no se vuelve a firmar', sqlerrm like '%ya está procesado%', sqlerrm); end $$;
insert into _r(id, ok, det) select 'T21 Procesado sin cambios: estado procesado, firma vigente, sin aviso',
   c->>'estado' = 'procesado' and c->'firma'->>'estado' = 'vigente' and c->'avisos'->'cambio_posterior_procesado' = 'null'::jsonb, null
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P2')) c) s;
reset role;
-- Cambio después de procesar (esquema de pago de la persona sintética, dentro de la transacción)
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
insert into _v select 'PROC', procesado_en::text from public.inc_periodos where id = (select v::uuid from _v where k='P2');
update public.personal_registros_pago set sueldo = sueldo + 1 where id = 'bc000000-0000-4000-8000-000000000031';
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _r(id, ok, det) select 'T21b Cambio después de procesar: aviso con «esquemas»; el periodo NO se reabre',
   c->>'estado' = 'procesado' and c->'avisos'->'cambio_posterior_procesado'->'secciones' = '["esquemas"]'::jsonb
   and (select procesado_en::text from public.inc_periodos where id = (select v::uuid from _v where k='P2')) = (select v from _v where k='PROC'),
   (c->'avisos'->'cambio_posterior_procesado')::text
  from (select public.inc_concentrado_periodo((select v::uuid from _v where k='P2')) c) s;
reset role;

-- ===== Permisos por rol =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_coord-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
do $$ begin perform public.inc_concentrado_periodo((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T22 Coordinador no ve el concentrado', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T22 Coordinador no ve el concentrado', sqlerrm like '%sin permiso%', sqlerrm); end $$;
do $$ begin perform public.inc_firma_periodo_estado((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T23 Coordinador no ve el estado de la firma', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T23 Coordinador no ve el estado de la firma', sqlerrm like '%sin permiso%', sqlerrm); end $$;
do $$ begin perform public.inc__concentrado_base((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T24 Función interna no ejecutable por usuarios', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T24 Función interna no ejecutable por usuarios', sqlerrm like '%permission denied%', sqlerrm); end $$;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_consulta-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
do $$ begin perform public.inc_concentrado_periodo((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T25 Consulta no ve el concentrado', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T25 Consulta no ve el concentrado', sqlerrm like '%sin permiso%', sqlerrm); end $$;
do $$ begin perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), 'x'); insert into _r(id, ok, det) values ('T26 Consulta no puede firmar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T26 Consulta no puede firmar', sqlerrm like '%solo el responsable%', sqlerrm); end $$;
reset role;
insert into _r(id, ok, det) select 'T27 anon no ejecuta ninguna de las 9 funciones nuevas', bool_and(not has_function_privilege('anon', p.oid, 'execute')), string_agg(p.proname, ',') filter (where has_function_privilege('anon', p.oid, 'execute'))
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname in ('inc__concentrado_base','inc__huella_de','inc_concentrado_huella','inc_firma_periodo_estado','inc__faltantes_base','inc_faltantes_bloqueantes','inc__faltantes_con_firma','inc_concentrado_periodo','inc_firmar_periodo');
insert into _r(id, ok, det) select 'T28 authenticated solo ejecuta las 3 funciones de pantalla (no las 6 internas)',
   bool_and(has_function_privilege('authenticated', p.oid, 'execute') = (p.proname in ('inc_concentrado_periodo','inc_firma_periodo_estado','inc_firmar_periodo'))),
   string_agg(p.proname || '=' || has_function_privilege('authenticated', p.oid, 'execute'), ',')
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname in ('inc__concentrado_base','inc__huella_de','inc_concentrado_huella','inc_firma_periodo_estado','inc__faltantes_base','inc_faltantes_bloqueantes','inc__faltantes_con_firma','inc_concentrado_periodo','inc_firmar_periodo');

-- ===== Aislamiento entre tenants: administrador de TENANT SINTETICO 7D6B =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_prueba-7d6b'), 'role', 'authenticated')::text, true);
set local role authenticated;
do $$ begin perform public.inc_concentrado_periodo((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T29 Otro tenant no ve el concentrado', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T29 Otro tenant no ve el concentrado', sqlerrm like '%periodo no encontrado%', sqlerrm); end $$;
do $$ begin perform public.inc_firma_periodo_estado((select v::uuid from _v where k='P')); insert into _r(id, ok, det) values ('T30 Otro tenant no ve el estado de la firma', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T30 Otro tenant no ve el estado de la firma', sqlerrm like '%periodo no encontrado%', sqlerrm); end $$;
do $$ begin perform public.inc_firmar_periodo((select v::uuid from _v where k='P'), 'x'); insert into _r(id, ok, det) values ('T31 Otro tenant no puede firmar', false, 'no rechazó');
exception when others then insert into _r(id, ok, det) values ('T31 Otro tenant no puede firmar', sqlerrm like '%no encontrado%' or sqlerrm like '%solo el responsable%', sqlerrm); end $$;
insert into _r(id, ok, det) select 'T32 Otro tenant ve 0 periodos, 0 eventos y 0 personas del piloto',
   (select count(*) from public.inc_periodos where id = (select v::uuid from _v where k='P')) = 0
   and (select count(*) from public.inc_eventos where periodo_id = (select v::uuid from _v where k='P')) = 0
   and (select count(*) from public.personal where tenant_id = (select v::uuid from _v where k='T')) = 0, null;
reset role;

-- ===== Datos existentes (solo lectura) =====
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _r(id, ok, det) select 'T33 Periodo procesado antes de B-a (B1.1): procesado, sin firma de periodo y sin aviso',
   coalesce(bool_and(c->>'estado' = 'procesado' and c->'firma'->>'estado' = 'sin_firma' and c->'avisos'->'cambio_posterior_procesado' = 'null'::jsonb), true),
   coalesce(string_agg((c->>'estado') || '/' || (c->'firma'->>'estado'), ','), 'sin periodo B1.1 (no aplica)')
  from (select public.inc_concentrado_periodo(pe.id) c from public.inc_periodos pe join public.empresas e on e.id = pe.empresa_id
         where e.nombre = 'EMPRESA SINTETICA B1.1 HORAS EXTRA' and pe.procesado_en is not null) s;
reset role;
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _r(id, ok, det) select 'T34 Periodos abiertos existentes: el concentrado responde y exige designar responsable de Nómina',
   coalesce(bool_and(c->>'estado' = 'preliminar' and exists (select 1 from jsonb_array_elements(c->'faltantes') f where f->>'detalle' like 'Designa al responsable de Nómina%')), true),
   coalesce(count(*)::text || ' periodos', 'ninguno')
  from (select public.inc_concentrado_periodo(pe.id) c from public.inc_periodos pe join public.empresas e on e.id = pe.empresa_id
         join public.inc_parametros ip on ip.empresa_id = e.id
         where pe.procesado_en is null and ip.responsable_nomina_user is null and e.id <> (select v::uuid from _v where k='E')) s;
reset role;

do $z$ begin raise exception 'PRUEBAS_B_C %/% OK || %', (select count(*) filter (where ok) from _r), (select count(*) from _r),
  (select string_agg(case when ok then 'OK ' else 'FALLA ' end || id || coalesce(' [' || left(det, 200) || ']', ''), ' || ' order by n) from _r); end $z$;
rollback;
