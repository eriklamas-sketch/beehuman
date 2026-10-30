-- Reversión: devuelve a cada periodicidad mensual el valor de días que tenía.
alter table public.periodicidades disable trigger user;
update public.periodicidades p set dias_default = b.dias_anterior
from respaldo.periodicidad_mensual_20261030 b where b.id = p.id;
alter table public.periodicidades enable trigger user;
drop table respaldo.periodicidad_mensual_20261030;
