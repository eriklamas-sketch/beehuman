-- BeeHuman · Reversión de B1.1a (20261112000300_b1_1a_tarifa_por_decidir). No toca datos:
-- los importes ya calculados conservan su estado; solo los cálculos futuros
-- vuelven a aceptar automáticamente las líneas por tarifa con esquema automático.
begin;
do $$
begin
  if to_regclass('respaldo.b1_1a_tarifa_por_decidir_20261112') is null then
    raise exception 'BeeHuman: B1.1a no está aplicada (falta respaldo.b1_1a_tarifa_por_decidir_20261112).';
  end if;
end $$;
do $$ declare o text; begin for o in select original from respaldo.b1_1a_tarifa_por_decidir_20261112 loop execute o; end loop; end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
drop table respaldo.b1_1a_tarifa_por_decidir_20261112;
commit;
