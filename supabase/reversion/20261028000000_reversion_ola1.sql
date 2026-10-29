-- =====================================================================
-- BeeHuman · Reversión de la Ola 1 (solo beehuman-pruebas)
-- Quita todo lo creado por 20261028000000_ola1_hoja_coordinador.sql.
-- No toca tablas ni datos existentes. btree_gist se deja instalada.
-- =====================================================================
begin;
drop trigger if exists trg_inc_asignacion_alta on public.personal;
drop trigger if exists trg_inc_asignacion_cambio on public.personal;
drop table if exists public.inc_eventos, public.inc_importes, public.inc_sueldos_manuales, public.inc_versiones,
  public.inc_observaciones, public.inc_cantidades, public.inc_celdas, public.inc_hojas, public.inc_periodos,
  public.inc_asignaciones, public.inc_tarifas_area, public.inc_conceptos, public.inc_parametros cascade;
do $$
declare f record;
begin
  for f in select p.oid::regprocedure sig from pg_proc p
           where p.pronamespace='public'::regnamespace and p.proname like 'inc\_%' loop
    execute format('drop function %s cascade', f.sig);
  end loop;
end $$;
commit;
