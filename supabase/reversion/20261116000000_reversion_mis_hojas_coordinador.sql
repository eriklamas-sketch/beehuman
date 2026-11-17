-- BeeHuman · Reversión de la corrección «Mis hojas» (20261116000000_mis_hojas_coordinador).
-- Restaura inc_abrir_hoja, inc_enviar_hoja, inc_faltantes_procesar (versión B5)
-- y la política original de inc_periodos (todo el tenant). No hay datos que
-- perder: la corrección no crea ni modifica registros.
begin;
do $$
begin
  if to_regclass('respaldo.mis_hojas_20261116') is null then
    raise exception 'BeeHuman: la corrección «Mis hojas» no está aplicada (falta respaldo.mis_hojas_20261116).';
  end if;
end $$;
drop policy inc_periodos_select on public.inc_periodos;
do $$ declare o text; begin for o in select original from respaldo.mis_hojas_20261116 order by objeto loop execute o; end loop; end $$;
drop function public.inc_empresas_visibles();
drop function public.inc_periodo_visible(uuid);
drop function public.inc_hoja_vacia_sin_personal(uuid);
drop function public.inc_coordinador_tiene_personal(uuid, uuid);
drop table respaldo.mis_hojas_20261116;
commit;
