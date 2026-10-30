select 'CAT', p.nombre, p.dias_default, (select count(*) from personal_registros_pago r where r.periodicidad_id=p.id) rp,
 (select count(*) from personal x where x.periodicidad_id=p.id) per, (select count(*) from inc_periodos i where i.periodicidad_id=p.id) inc
from periodicidades p order by upper(p.nombre), p.nombre;
select 'IMPORTES', count(*), sum(sueldo), sum(coalesce(dias_periodo,0)), string_agg(fecha_inicio::text||coalesce(fecha_fin::text,''),'' order by id) = string_agg(fecha_inicio::text||coalesce(fecha_fin::text,''),'' order by id) from personal_registros_pago;
select 'AUTORIA', count(*) filter (where actualizado_en is not null) from personal;
