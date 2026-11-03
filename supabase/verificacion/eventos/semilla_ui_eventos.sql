-- Datos FICTICIOS adicionales para probar Historia laboral e IDSE en pantalla.
begin;
set local session_replication_role = replica;
insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal) values
 ('0f900000-0000-4000-8000-000000000001','0c000000-0000-4000-8000-000000000001','0a000000-0000-4000-8000-000000000001','Y1234567101'),
 ('0f900000-0000-4000-8000-000000000002','0c000000-0000-4000-8000-000000000001','0a000000-0000-4000-8000-000000000001','Y1234567102');
-- ADELA: IMSS en RP1 con alta, NSS, CURP y número interno
update public.personal set registro_patronal_id='0f900000-0000-4000-8000-000000000001', fecha_alta_imss='2025-03-01', fecha_antiguedad='2021-06-01',
  nss='11111111111', curp='PAGA900101MDFLLD05', numero_interno_trabajador='101', sdi_imss=420 where id='0a100000-0000-4000-8000-000000000011';
-- BENITO: ficha en RP1 y un esquema activo en RP2 → dos relaciones; su esquema sin RP queda pendiente de asignar
update public.personal set registro_patronal_id='0f900000-0000-4000-8000-000000000001', fecha_alta_imss='2024-08-15', nss='22222222222',
  curp='ZAGB850505HDFVLN02', numero_interno_trabajador='102' where id='0a100000-0000-4000-8000-000000000012';
insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, empresa_id, registro_patronal_id)
select tenant_id, personal_id, clasificacion_id, periodicidad_id, 3000, 'bruto', dias_periodo, '2024-08-15', empresa_id, '0f900000-0000-4000-8000-000000000002'
  from public.personal_registros_pago where personal_id='0a100000-0000-4000-8000-000000000012' limit 1;
-- EDGAR (apellido con Ñ): solo efectivo; en la prueba se le registra el alta IMSS
update public.personal set nss='33333333333', curp='MOPE920303HDFRXD08' where id='0a100000-0000-4000-8000-000000000015';
-- FABIOLA: en Baja
update public.personal set estatus='Baja', fecha_baja='2025-09-30', comentario_baja='Renuncia' where id='0a100000-0000-4000-8000-000000000016';
select setval('public.personal_empleado_id_seq', 1000); -- los datos ficticios usan IDs fijos
commit;
