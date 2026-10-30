-- Datos FICTICIOS adicionales para probar la tabla de Personal y la ficha (UX).
begin;
set local session_replication_role = replica;
insert into public.clasificaciones_personal (id, tenant_id, nombre, activo) values
 ('0f000000-0000-4000-8000-000000000002','0a000000-0000-4000-8000-000000000001','Efectivo',true),
 ('0f000000-0000-4000-8000-000000000003','0a000000-0000-4000-8000-000000000001','Transferencia',true),
 ('0f000000-0000-4000-8000-000000000004','0a000000-0000-4000-8000-000000000001','Asimilados',true);
insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, dias_periodo, fecha_inicio, fecha_fin, activo, empresa_id) values
 ('0a000000-0000-4000-8000-000000000001','0a100000-0000-4000-8000-000000000011','0f000000-0000-4000-8000-000000000002','0e000000-0000-4000-8000-000000000030',3000,'neto',null,'2025-01-01',null,true,null),
 ('0a000000-0000-4000-8000-000000000001','0a100000-0000-4000-8000-000000000012','0f000000-0000-4000-8000-000000000003','0e000000-0000-4000-8000-000000000007',2000,'neto',null,'2025-03-01',null,true,'0c000000-0000-4000-8000-000000000001'),
 ('0a000000-0000-4000-8000-000000000001','0a100000-0000-4000-8000-000000000013','0f000000-0000-4000-8000-000000000001','0e000000-0000-4000-8000-000000000030',10000,'bruto',null,'2024-01-01','2024-12-31',false,'0c000000-0000-4000-8000-000000000001'),
 ('0a000000-0000-4000-8000-000000000001','0a100000-0000-4000-8000-000000000013','0f000000-0000-4000-8000-000000000004','0e000000-0000-4000-8000-000000000030',1500,'bruto',null,'2024-01-01','2024-06-30',false,null);
update public.personal set estatus='Baja', fecha_baja='2026-10-15' where id='0a100000-0000-4000-8000-000000000015';
update public.personal set estatus='Suspendido' where id='0a100000-0000-4000-8000-000000000014';
insert into public.personal (id, tenant_id, empresa_id, nombre_completo, nombres, primer_apellido, segundo_apellido, empleado_id, estatus, area_id, created_at)
select ('0a2' || lpad(g::text, 5, '0') || '-0000-4000-8000-000000000001')::uuid, '0a000000-0000-4000-8000-000000000001',
       (case when g % 3 = 0 then '0c000000-0000-4000-8000-000000000002' else '0c000000-0000-4000-8000-000000000001' end)::uuid,
       'PERSONA DEMO ' || lpad(g::text, 3, '0'), 'PERSONA', 'DEMO', lpad(g::text, 3, '0'), 'BEH-' || lpad((100 + g)::text, 6, '0'), 'Activo',
       '0d000000-0000-4000-8000-000000000001'::uuid, '2026-09-03'
from generate_series(1, 55) g;
commit;
