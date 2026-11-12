-- =====================================================================
-- BeeHuman · Reversión de B2 (20261112000000_b2_incidencias_relacion_esquemas)
-- Restaura las funciones originales guardadas en respaldo.b2_incidencias_20261112,
-- quita las columnas nuevas y vuelve los permisos de DELETE al estado anterior.
-- Se detiene si ya hay importes por esquema que no caben en el modelo anterior
-- (varias líneas por persona y concepto, o líneas «descartado»): los importes
-- no se borran, así que en ese caso hay que decidir antes qué hacer con ellos.
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.b2_incidencias_20261112') is null then
    raise exception 'BeeHuman: B2 no está aplicada (falta respaldo.b2_incidencias_20261112).';
  end if;
  if exists (select 1 from public.inc_importes group by version_id, personal_id, concepto_id having count(*) > 1)
     or exists (select 1 from public.inc_importes where origen = 'descartado') then
    raise exception 'BeeHuman: hay importes calculados por esquema; la reversión no puede volver a una línea por persona y concepto sin borrarlos.';
  end if;
end $$;

drop function public.inc_personas_hoja(uuid);
do $$
declare o text;
begin
  for o in select original from respaldo.b2_incidencias_20261112 loop
    execute o;
  end loop;
end $$;

drop function public.inc_esquemas_dia(uuid,uuid,date,text);
drop function public.inc_relacion_en(uuid,uuid,date);

drop index public.inc_importes_linea_uq;
alter table public.inc_importes add constraint inc_importes_version_id_personal_id_concepto_id_key unique (version_id, personal_id, concepto_id);
alter table public.inc_importes drop constraint inc_importes_origen_check;
alter table public.inc_importes add constraint inc_importes_origen_check
  check (origen in ('pendiente','aceptado','modificado','sin_sueldo','sin_importe'));
alter table public.inc_importes drop column modalidad, drop column registro_pago_id, drop column relacion_laboral_id;
alter table public.inc_celdas drop column relacion_laboral_id;
alter table public.inc_cantidades drop column relacion_laboral_id;

revoke delete on public.inc_celdas, public.inc_cantidades, public.inc_observaciones, public.inc_tarifas_area from authenticated;
-- Permisos de las funciones restauradas, como en la Ola 1
revoke all on function public.inc_sueldo_diario(uuid,uuid,text) from public, anon, authenticated;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
revoke all on function public.inc_validar_captura() from public, anon, authenticated;
revoke all on function public.inc_personas_hoja(uuid) from public, anon;
grant execute on function public.inc_personas_hoja(uuid) to authenticated;

drop table respaldo.b2_incidencias_20261112;
commit;
