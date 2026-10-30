-- Fechas ficticias relativas a hoy para ver las alertas en pantalla
begin; set local session_replication_role = replica;
update personal set fecha_antiguedad = (current_date - interval '6 years' + interval '10 days')::date where empleado_id='BEH-000011';
update personal set fecha_alta_imss  = (current_date - interval '3 years' - interval '5 days')::date where empleado_id='BEH-000012';
update personal set fecha_inicio_contrato = (current_date - interval '2 years')::date where empleado_id='BEH-000013';
update personal set fecha_antiguedad = (current_date - interval '4 years' + interval '90 days')::date where empleado_id='BEH-000014';
update personal set fecha_antiguedad = (current_date - interval '8 years' + interval '3 days')::date where empleado_id='BEH-000015'; -- en Baja: sin alerta
update personal set fecha_inicio_contrato = '2020-01-15' where empleado_id like 'BEH-0001%';
commit;
