-- BeeHuman · Reversión de B1.1b (20261112000400_b1_1b_delete_con_where). No toca datos.
-- Atención: al revertir, enviar hojas desde la aplicación vuelve a fallar en Supabase.
begin;
do $$
begin
  if to_regclass('respaldo.b1_1b_delete_con_where_20261112') is null then
    raise exception 'BeeHuman: B1.1b no está aplicada (falta respaldo.b1_1b_delete_con_where_20261112).';
  end if;
end $$;
do $$ declare o text; begin for o in select original from respaldo.b1_1b_delete_con_where_20261112 loop execute o; end loop; end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
drop table respaldo.b1_1b_delete_con_where_20261112;
commit;
