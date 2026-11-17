-- BeeHuman · Reversión de B1 (20261112000100_b1_revision_nomina). No toca datos.
begin;
do $$
begin
  if to_regclass('respaldo.b1_revision_20261112') is null then
    raise exception 'BeeHuman: B1 no está aplicada (falta respaldo.b1_revision_20261112).';
  end if;
end $$;
drop function public.inc_tablero_periodo(uuid);
drop function public.inc_aceptar_sugeridos(uuid);
drop function public.inc_faltantes_procesar(uuid);
do $$ declare o text; begin for o in select original from respaldo.b1_revision_20261112 loop execute o; end loop; end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
drop table respaldo.b1_revision_20261112;
commit;
