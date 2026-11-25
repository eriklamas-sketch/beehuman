-- BeeHuman · Reversión del Excel canónico V1 y del reporte preliminar (20261125000000_excel_canonico_v1.sql) · 24-nov-2026
-- Quita solo las funciones que agregó la migración. Los eventos «exportacion» ya registrados se conservan
-- (inc_eventos es inmutable y el tipo ya existía desde Ola 1). No toca tablas, firmas, huellas ni periodos.
begin;
do $$
begin
  if to_regprocedure('public.inc_exportacion_canonica(uuid)') is null then raise exception 'BeeHuman: el Excel canónico V1 no está aplicado.'; end if;
end $$;
drop function public.inc_exportacion_preliminar(uuid);
drop function public.inc_exportacion_canonica(uuid);
drop function public.inc__exportacion_registrar(jsonb);
drop function public.inc__exportacion_datos(uuid, text);
drop function public.inc__exp_slug(text);
drop function public.inc__exp_linea(jsonb);
drop function public.inc__exp_ts(timestamptz);
drop function public.inc__exp_fecha(date);
drop function public.inc__exp_num(numeric);
drop function public.inc__exp_imp(numeric);
drop function public.inc__exp_t(text);
commit;
