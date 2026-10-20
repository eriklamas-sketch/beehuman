-- =====================================================================
-- BeeHuman · Semilla SINTÉTICA para la base aislada (no Supabase)
-- Archivo: supabase/verificacion/semilla_sintetica_local.sql
-- Reproduce la forma mínima de beehuman-pruebas que la prueba de
-- compatibilidad necesita: 3 tenants (mismos nombres e ids), las cuentas
-- A y B como administrador en tenants distintos, y datos en cada tenant.
-- Todo es ficticio. Se carga con triggers desactivados (session_replication_role)
-- porque como postgres no hay sesión de usuario para asignar tenant.
-- =====================================================================
begin;
set local session_replication_role = replica;
insert into public.tenants (id, nombre) values
  ('00000000-0000-4000-8000-0000007d6b01','TENANT SINTETICO 7D6B'),
  ('00000000-0000-4000-8000-0000007d6c01','TENANT SINTETICO 7D6B-B'),
  ('19ef5c93-692e-54d8-b2a5-4268f3b7780f','PILOTO SINTETICO 500');
insert into auth.users (id, email) values
  ('22222222-0000-4000-8000-000000000001','admin-prueba@beehuman.invalid'),
  ('00000000-0000-4000-8000-0000007d6c02','prueba2-7d6b@beehuman.invalid'),
  ('efe0b48f-2bf3-4bff-92d2-18ae58f20b44','prueba-7d6b@beehuman.invalid');
insert into public.usuarios_tenant (user_id, tenant_id, rol) values
  ('22222222-0000-4000-8000-000000000001','19ef5c93-692e-54d8-b2a5-4268f3b7780f','administrador'),
  ('00000000-0000-4000-8000-0000007d6c02','00000000-0000-4000-8000-0000007d6c01','administrador'),
  ('efe0b48f-2bf3-4bff-92d2-18ae58f20b44','00000000-0000-4000-8000-0000007d6b01','administrador');
-- Por tenant: empresas, áreas, periodicidad, clasificación, personas y esquemas
do $$
declare t record; e uuid; pe uuid; cl uuid; p uuid; i int;
begin
  for t in select * from (values
      ('19ef5c93-692e-54d8-b2a5-4268f3b7780f'::uuid, 5, 40),
      ('00000000-0000-4000-8000-0000007d6c01'::uuid, 1, 1),
      ('00000000-0000-4000-8000-0000007d6b01'::uuid, 1, 12)) v(tid, n_emp, n_per) loop
    for i in 1..t.n_emp loop
      insert into public.empresas (tenant_id, nombre) values (t.tid, 'EMPRESA SINTETICA '||i) returning id into e;
    end loop;
    insert into public.areas (tenant_id, nombre) values (t.tid, 'AREA SINTETICA');
    insert into public.periodicidades (tenant_id, nombre, dias_default) values (t.tid, 'Quincenal', 15) returning id into pe;
    insert into public.clasificaciones_personal (tenant_id, nombre) values (t.tid, 'Efectivo') returning id into cl;
    for i in 1..t.n_per loop
      insert into public.personal (tenant_id, nombre_completo, empresa_id, empleado_id)
        values (t.tid, 'PERSONA SINTETICA '||i, e, 'SIN-'||substr(md5(t.tid::text),1,6)||'-'||i) returning id into p;
      insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo)
        values (t.tid, p, cl, pe, 1000 + i, 'neto');
    end loop;
  end loop;
end $$;
commit;
