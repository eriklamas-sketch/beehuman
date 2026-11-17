-- BeeHuman · Reversión de B1.1 (20261112000200_b1_1_valor_hora).
-- Se niega si ya hay datos que solo existen con B1.1 (se perderían): bitácora
-- de ajustes, líneas por asignar o con esquema asignado por Nómina, conceptos
-- de horas sencillas o con esquema preferido, umbral vacío o factor doble
-- distinto de 2. En ese caso hay que decidir antes qué hacer con esos datos.
begin;
do $$
begin
  if to_regclass('respaldo.b1_1_valor_hora_20261112') is null then
    raise exception 'BeeHuman: B1.1 no está aplicada (falta respaldo.b1_1_valor_hora_20261112).';
  end if;
  if exists (select 1 from public.inc_importes_ajustes)
     or exists (select 1 from public.inc_importes where origen = 'por_asignar' or esquema_asignado_por is not null)
     or exists (select 1 from public.inc_conceptos where tipo = 'horas' or clasificacion_pago_id is not null)
     or exists (select 1 from public.inc_parametros where umbral_triples_semana is null or factor_doble <> 2) then
    raise exception 'BeeHuman: hay datos de B1.1 (bitácora, líneas por asignar, horas sencillas, esquema preferido, umbral vacío o factor doble distinto de 2); la reversión los perdería.';
  end if;
end $$;

drop trigger trg_inc_importes_proteger on public.inc_importes;
drop function public.inc_importes_proteger();
drop function public.inc_asignar_esquema(uuid,uuid,text);
drop function public.inc_esquemas_asignables(uuid);
drop function public.inc_esquemas_vigentes(uuid,uuid,date[],text);
drop function public.inc_decidir_importe(uuid,numeric,text);
drop table public.inc_importes_ajustes;

-- originales (B1 / Ola 1)
do $$ declare o text; begin for o in select original from respaldo.b1_1_valor_hora_20261112 loop execute o; end loop; end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
revoke all on function public.inc_decidir_importe(uuid,numeric) from public, anon, authenticated, service_role;
grant execute on function public.inc_decidir_importe(uuid,numeric) to service_role;
grant execute on function public.inc_decidir_importe(uuid,numeric) to authenticated;

alter table public.inc_importes drop column esquema_asignado_por;
alter table public.inc_importes drop column esquema_asignado_en;
alter table public.inc_importes drop constraint inc_importes_origen_check;
alter table public.inc_importes add constraint inc_importes_origen_check
  check (origen in ('pendiente','aceptado','modificado','sin_sueldo','sin_importe','descartado'));

alter table public.inc_conceptos drop column clasificacion_pago_id;
alter table public.inc_conceptos drop constraint inc_conceptos_tipo_check;
alter table public.inc_conceptos add constraint inc_conceptos_tipo_check
  check (tipo in ('horas_extra','domingo','turno','descuento','otro'));

alter table public.inc_parametros alter column umbral_triples_semana set not null;
alter table public.inc_parametros drop column factor_doble;
comment on column public.inc_parametros.umbral_triples_semana is null;

drop table respaldo.b1_1_valor_hora_20261112;
commit;
