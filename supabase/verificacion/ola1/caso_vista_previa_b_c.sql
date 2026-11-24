-- B-c · Caso de prueba PERMANENTE para validar la vista previa en beehuman-pruebas (decisión de Erik, 23-nov 19:0x).
-- Empresa «EMPRESA SINTETICA BC VISTA PREVIA» (tenant PILOTO SINTETICO 500), datos 100 % ficticios.
-- Todo se crea con las funciones de la aplicación actuando como cada rol, salvo la semilla de catálogo (como postgres
-- con la sesión de admin-prueba) y las relaciones laborales (con la bandera de las funciones de historial).
-- Periodos (semanas futuras, sin traslape con los existentes):
--   PV1 preliminar  · hoja enviada, importes y FONACOT por decidir (para recorrer el flujo completo en pantalla)
--   PV2 firmado     · decidido, RH firmó, Nómina firmó: «Listo para procesar»
--   PV3 invalidado  · firmado y luego un importe modificado: firma invalidada («importes»)
--   PV4 procesado   · firmado y procesado; después cambia el sueldo de X4 (ingresa esa semana; PV4 es el último): aviso «esquemas» y «movimientos»
--                   (el cambio de sueldo registra su movimiento) y la firma se muestra como la que autorizó lo procesado
-- Una sola transacción: si algo falla, no queda nada.
begin;
create temp table _v(k text primary key, v text);
grant all on _v to authenticated;
do $$ begin if exists (select 1 from public.empresas where nombre = 'EMPRESA SINTETICA BC VISTA PREVIA') then raise exception 'El caso ya existe'; end if; end $$;
insert into _v select 'T', id::text from public.tenants where nombre = 'PILOTO SINTETICO 500';
insert into _v select 'u_'||split_part(email,'@',1), id::text from auth.users where email in ('admin-prueba@beehuman.invalid','nomina-prueba@beehuman.invalid','coord-prueba@beehuman.invalid');
insert into _v select 'AABG', personal_id::text from public.usuarios_tenant where user_id = (select v::uuid from _v where k='u_coord-prueba');
insert into _v values ('w', (date_trunc('week', public.hoy_mx() + 35))::date::text);
insert into _v values ('E','be000000-0000-4000-8000-000000000001'),('RP','be000000-0000-4000-8000-000000000002'),('SEM','be000000-0000-4000-8000-000000000003'),
 ('CL1','be000000-0000-4000-8000-000000000004'),('CL2','be000000-0000-4000-8000-000000000005'),('HE','be000000-0000-4000-8000-000000000006'),('CAP','be000000-0000-4000-8000-000000000007'),
 ('X1','be000000-0000-4000-8000-000000000011'),('X2','be000000-0000-4000-8000-000000000012'),('X3','be000000-0000-4000-8000-000000000013'),('X4','be000000-0000-4000-8000-000000000014'),
 ('R1','be000000-0000-4000-8000-000000000021'),('R2','be000000-0000-4000-8000-000000000022'),('R3','be000000-0000-4000-8000-000000000023'),('R4','be000000-0000-4000-8000-000000000024');
do $$ begin if (select count(*) from _v where k in ('T','u_admin-prueba','u_nomina-prueba','u_coord-prueba','AABG')) <> 5 then raise exception 'Faltan cuentas de prueba'; end if; end $$;

select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
insert into public.empresas (id, tenant_id, nombre) select (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), 'EMPRESA SINTETICA BC VISTA PREVIA';
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo)
  select (select v::uuid from _v where k='RP'), (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), 'B5550000001', true;
insert into public.periodicidades (id, tenant_id, nombre, dias_default) select (select v::uuid from _v where k='SEM'), (select v::uuid from _v where k='T'), 'SEMANAL BC VISTA PREVIA', 7;
insert into public.clasificaciones_personal (id, tenant_id, nombre) select (select v::uuid from _v where k='CL1'), (select v::uuid from _v where k='T'), 'IMSS BC VP'
  union all select (select v::uuid from _v where k='CL2'), (select v::uuid from _v where k='T'), 'EFECTIVO BC VP';
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, coordinador_id)
  select (select v::uuid from _v where k=x), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'SINTETICO VP ' || x, (select v::uuid from _v where k='AABG')
    from unnest(array['X1','X2','X3','X4']) x;
select set_config('beehuman.laboral', 'on', true);
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, registro_patronal_id, numero_interno)
  select (select v::uuid from _v where k='R'||i), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='X'||i), (select v::uuid from _v where k='E'), '2025-01-01', 'vigente', (select v::uuid from _v where k='RP'), 'VP'||i
    from generate_series(1,3) i;
-- X4 ingresa la semana de PV4 (el último periodo): no aparece en PV1–PV3, así que su cambio posterior solo toca PV4.
insert into public.relaciones_laborales (id, tenant_id, personal_id, empresa_id, fecha_ingreso, estado, registro_patronal_id, numero_interno)
  select (select v::uuid from _v where k='R4'), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='X4'), (select v::uuid from _v where k='E'),
         (select v::date from _v where k='w') + 21, 'vigente', (select v::uuid from _v where k='RP'), 'VP4';
select set_config('beehuman.laboral', 'off', true);
insert into public.personal_registros_pago (id, tenant_id, personal_id, relacion_laboral_id, empresa_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, fecha_fin, activo)
  select ('be000000-0000-4000-8000-00000000003'||n)::uuid, (select v::uuid from _v where k='T'), (select v::uuid from _v where k=px), (select v::uuid from _v where k=rx), (select v::uuid from _v where k='E'),
         (select v::uuid from _v where k=cl), (select v::uuid from _v where k='SEM'), su, mo, 7, fi, ff, true
    from (values (1,'X1','R1','CL1',3500,'bruto','2025-01-01'::date,null::date),(2,'X2','R2','CL1',2800,'bruto','2025-01-01',null),(3,'X2','R2','CL2',700,'neto','2025-01-01',null),
                 (4,'X3','R3','CL1',2800,'bruto','2025-01-01',null),
                 (5,'X4','R4','CL1',3000,'bruto',(select v::date from _v where k='w') + 21,null)) s(n,px,rx,cl,su,mo,fi,ff);
insert into public.inc_parametros (empresa_id, tenant_id, inicio_historial, responsable_nomina_user, responsable_rh_user)
  select (select v::uuid from _v where k='E'), (select v::uuid from _v where k='T'), '2025-01-01', (select v::uuid from _v where k='u_nomina-prueba'), (select v::uuid from _v where k='u_admin-prueba');
insert into public.inc_conceptos (id, tenant_id, empresa_id, nombre, abreviatura, unidad, tipo, modo, tarifa, factor, orden)
  select (select v::uuid from _v where k='HE'), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'Horas extra VP', 'HE', 'horas', 'horas_extra', 'beehuman', null::numeric, 2, 1
  union all select (select v::uuid from _v where k='CAP'), (select v::uuid from _v where k='T'), (select v::uuid from _v where k='E'), 'Capacitación VP', 'CAP', 'horas', 'otro', 'sin_importe', null::numeric, null::numeric, 2;

-- Nómina: 4 periodos y crédito FONACOT de X3
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'PV'||i, public.inc_crear_periodo((select v::uuid from _v where k='E'), (select v::uuid from _v where k='SEM'), (select v::date from _v where k='w') + 7*(i-1), (select v::date from _v where k='w') + 7*(i-1) + 6)::text
  from generate_series(1,4) i;
insert into _v select 'CR', public.cred_guardar(null, jsonb_build_object('personal_id', (select v from _v where k='X3'), 'tipo', 'fonacot', 'referencia', 'FN-VP3',
   'relacion_laboral_id', (select v from _v where k='R3'), 'fecha_inicio', (select v from _v where k='w'), 'periodicidad_id', (select v from _v where k='SEM'), 'importe_periodo', 150), null)::text;
do $$ begin if (select estado from public.cred_creditos where id = (select v::uuid from _v where k='CR')) <> 'activo' then
  perform public.cred_cambiar_estado((select v::uuid from _v where k='CR'), 'activo', (select v::date from _v where k='w'), 'Alta caso vista previa'); end if; end $$;
reset role;

-- Coordinador: una hoja por periodo, con captura, y la envía
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_coord-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
insert into _v select 'H'||i, public.inc_abrir_hoja((select v::uuid from _v where k='PV'||i))::text from generate_series(1,4) i;
insert into public.inc_celdas (hoja_id, personal_id, fecha, codigo)
  select (select v::uuid from _v where k='H'||i), (select v::uuid from _v where k='X2'), (select v::date from _v where k='w') + 7*(i-1) + 1, 'F' from generate_series(1,4) i;
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
  select (select v::uuid from _v where k='H'||i), (select v::uuid from _v where k=x), (select v::date from _v where k='w') + 7*(i-1), (select v::uuid from _v where k=c), q
    from generate_series(1,4) i, (values ('X1','HE',2),('X2','HE',1),('X3','CAP',3)) s(x,c,q);
insert into public.inc_cantidades (hoja_id, personal_id, fecha, concepto_id, cantidad)
  select (select v::uuid from _v where k='H4'), (select v::uuid from _v where k='X4'), (select v::date from _v where k='w') + 22, (select v::uuid from _v where k='HE'), 1;
insert into _v select 'V'||i, public.inc_enviar_hoja((select v::uuid from _v where k='H'||i), 'Caso de prueba vista previa B-c')::text from generate_series(1,4) i;
reset role;

-- Nómina decide PV2–PV4 (PV1 queda por decidir)
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.cred_descuentos_periodo((select v::uuid from _v where k='PV'||i)) from generate_series(1,4) i;
select public.inc_aceptar_sugeridos((select v::uuid from _v where k='V'||i)) from generate_series(2,4) i;
select public.cred_aceptar_descuentos((select v::uuid from _v where k='PV'||i)) from generate_series(2,4) i;
reset role;
-- RH firma las hojas de PV2–PV4
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_firmar_hoja((select v::uuid from _v where k='H'||i), 'rh') from generate_series(2,4) i;
reset role;
-- Nómina firma PV2–PV4 con la huella revisada; PV3: cambia un importe; PV4: procesa
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
select public.inc_firmar_periodo((select v::uuid from _v where k='PV'||i), public.inc_firma_periodo_estado((select v::uuid from _v where k='PV'||i))->'huella_actual'->>'total') from generate_series(2,4) i;
select public.inc_decidir_importe((select id from public.inc_importes where version_id = (select v::uuid from _v where k='V3') and personal_id = (select v::uuid from _v where k='X1') limit 1), 999, 'Ajuste después de firmar (caso vista previa)');
select public.inc_marcar_procesado((select v::uuid from _v where k='PV4'));
reset role;
-- PV4: cambio después de procesar (sueldo de X4, que ingresa en PV4, el último periodo)
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_admin-prueba'), 'role', 'authenticated')::text, true);
update public.personal_registros_pago set sueldo = 3100 where id = 'be000000-0000-4000-8000-000000000035';

-- Verificación del caso (como Nómina): si un estado no es el esperado, se revierte todo
select set_config('request.jwt.claims', json_build_object('sub', (select v from _v where k='u_nomina-prueba'), 'role', 'authenticated')::text, true);
set local role authenticated;
do $$ declare c jsonb; s text := ''; i int; esperado text[] := array['preliminar/sin_firma','listo/vigente','preliminar/invalidada','procesado/invalidada'];
begin
  for i in 1..4 loop
    c := public.inc_concentrado_periodo((select v::uuid from _v where k='PV'||i));
    s := s || 'PV' || i || '=' || (c->>'estado') || '/' || (c->'firma'->>'estado') || coalesce(' post=' || (c->'avisos'->'cambio_posterior_procesado'->'secciones')::text, '') || '; ';
    if (c->>'estado') || '/' || (c->'firma'->>'estado') <> esperado[i] then raise exception 'Caso vista previa: estado inesperado en PV%: %', i, s; end if;
  end loop;
  if (public.inc_concentrado_periodo((select v::uuid from _v where k='PV3'))->'firma'->'secciones_cambiadas') <> '["importes"]'::jsonb
     or (public.inc_concentrado_periodo((select v::uuid from _v where k='PV4'))->'avisos'->'cambio_posterior_procesado'->'secciones') <> '["esquemas", "movimientos"]'::jsonb then
    raise exception 'Caso vista previa: secciones inesperadas: %', s;
  end if;
  raise notice 'CASO_VISTA_PREVIA_OK %', s;
end $$;
reset role;
select 'CASO_VISTA_PREVIA_OK' as resultado, string_agg(k || '=' || v, ' ' order by k) as ids from _v where k like 'PV%';
commit;
