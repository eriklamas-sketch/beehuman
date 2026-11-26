-- Catálogos ficticios para la prueba de importación masiva v2 (tenant de prueba).
-- :ten = tenant. Se ejecuta como postgres; los disparadores de tenant se respetan con tenant_id explícito.
begin;
set local session_replication_role = replica;
insert into public.empresas (id, tenant_id, nombre, activo) values
  ('0e100000-0000-4000-8000-000000000001', :'ten', 'IMPORTA NORTE DEMO', true),
  ('0e100000-0000-4000-8000-000000000002', :'ten', 'IMPORTA SUR DEMO', true),
  ('0e100000-0000-4000-8000-000000000003', :'ten', 'IMPORTA CENTRO DEMO', true);
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo) values
  ('0e200000-0000-4000-8000-000000000001', '0e100000-0000-4000-8000-000000000001', :'ten', 'A0000000001', true),
  ('0e200000-0000-4000-8000-000000000002', '0e100000-0000-4000-8000-000000000002', :'ten', 'B0000000002', true);
insert into public.clasificaciones_personal (id, tenant_id, nombre, activo, requiere_rfc, requiere_curp, requiere_nss, requiere_cp_fiscal) values
  ('0e300000-0000-4000-8000-000000000001', :'ten', 'Base / IMSS', true, true, true, true, true),
  ('0e300000-0000-4000-8000-000000000002', :'ten', 'Efectivo', true, false, false, false, false);
insert into public.periodicidades (id, tenant_id, nombre, dias_default)
  select '0e400000-0000-4000-8000-000000000001', :'ten', 'Quincenal', 15
  where not exists (select 1 from public.periodicidades where tenant_id = :'ten' and lower(nombre) = 'quincenal');
insert into public.proyectos (id, tenant_id, nombre) values ('0e500000-0000-4000-8000-000000000001', :'ten', 'PROYECTO IMPORTACION');
select setval('public.personal_empleado_id_seq', greatest((select coalesce(max(substring(empleado_id from '[0-9]+$')::bigint), 1) from public.personal where empleado_id ~ '^BEH-[0-9]+$'), (select last_value from public.personal_empleado_id_seq)));
commit;
