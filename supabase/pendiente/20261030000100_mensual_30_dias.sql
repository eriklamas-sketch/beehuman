-- BeeHuman · Periodicidad mensual = 30 días (decisión de Erik, 30-oct-2026)
-- Solo cambia `dias_default` de las periodicidades llamadas MENSUAL (sin
-- importar mayúsculas). No toca sueldos ni los días propios de cada esquema;
-- los esquemas sin días propios usarán 30 en lugar del valor anterior.
-- Respaldo del valor anterior en `respaldo`; reversión en
-- 20261030000100_reversion_mensual_30_dias.sql
create schema if not exists respaldo;
create table if not exists respaldo.periodicidad_mensual_20261030 (
  id uuid primary key, tenant_id uuid not null, nombre text not null, dias_anterior numeric,
  esquemas_sin_dias_propios int not null, respaldado_en timestamptz not null default now());
insert into respaldo.periodicidad_mensual_20261030 (id, tenant_id, nombre, dias_anterior, esquemas_sin_dias_propios)
select p.id, p.tenant_id, p.nombre, p.dias_default,
       (select count(*) from public.personal_registros_pago r where r.periodicidad_id = p.id and r.dias_periodo is null)
from public.periodicidades p
where upper(btrim(p.nombre)) = 'MENSUAL' and p.dias_default is distinct from 30
on conflict (id) do nothing;
alter table public.periodicidades disable trigger user;
update public.periodicidades p set dias_default = 30
from respaldo.periodicidad_mensual_20261030 b where b.id = p.id;
alter table public.periodicidades enable trigger user;
