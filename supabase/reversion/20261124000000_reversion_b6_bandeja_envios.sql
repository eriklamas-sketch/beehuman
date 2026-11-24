-- BeeHuman · Reversión de B6 bandeja de envíos (20261124000000_b6_bandeja_envios.sql) · 24-nov-2026
-- Deja el esquema exactamente como antes de B6. ATENCIÓN: borra el seguimiento registrado (aperturas y atenciones);
-- respáldalo antes si ya se usó. No toca eventos, hojas, versiones, firmas ni periodos.
begin;
do $$
begin
  if to_regclass('public.inc_envio_seguimiento') is null then raise exception 'BeeHuman: B6 no está aplicada.'; end if;
end $$;
drop function public.inc_envio_atender(uuid, text);
drop function public.inc_envio_abrir(uuid);
drop function public.inc_envios_pendientes();
drop function public.inc_bandeja_envios(uuid, integer);
drop function public.inc__envios_base(uuid);
drop table public.inc_envio_seguimiento;
drop function public.inc_envio_seguimiento_proteger();
drop function public.inc_envio_seguimiento_validar();
drop index public.inc_eventos_envios;
commit;
