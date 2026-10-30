-- Reversión de 20261030000000_normalizar_periodicidades.sql
-- Restaura las periodicidades unificadas y devuelve cada referencia a la
-- periodicidad que tenía, desde el esquema `respaldo`. Quita la protección.
begin;
drop index if exists public.periodicidades_tenant_nombre_unico;

alter table public.periodicidades disable trigger user; -- el tenant viene del respaldo
insert into public.periodicidades (id, tenant_id, nombre, dias_default)
select id, tenant_id, nombre, dias_default from respaldo.periodicidades_20261030
on conflict (id) do nothing;
alter table public.periodicidades enable trigger user;

alter table public.personal disable trigger user;
alter table public.personal_registros_pago disable trigger user;
update public.personal x set periodicidad_id = r.periodicidad_anterior
  from respaldo.periodicidades_refs_20261030 r where r.tabla = 'personal' and r.fila_id = x.id;
update public.personal_registros_pago p set periodicidad_id = r.periodicidad_anterior
  from respaldo.periodicidades_refs_20261030 r where r.tabla = 'personal_registros_pago' and r.fila_id = p.id;
alter table public.personal enable trigger user;
alter table public.personal_registros_pago enable trigger user;

do $$ begin
  if to_regclass('public.inc_periodos') is not null then
    execute 'alter table public.inc_periodos disable trigger user';
    execute 'update public.inc_periodos i set periodicidad_id = r.periodicidad_anterior
             from respaldo.periodicidades_refs_20261030 r where r.tabla = ''inc_periodos'' and r.fila_id = i.id';
    execute 'alter table public.inc_periodos enable trigger user';
  end if;
end $$;

drop table respaldo.periodicidades_refs_20261030;
drop table respaldo.periodicidades_20261030;
commit;
