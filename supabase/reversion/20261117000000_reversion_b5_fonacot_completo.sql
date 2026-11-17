-- BeeHuman · Reversión de 20261117000000_b5_fonacot_completo.
-- Restaura cred_creditos_persona (B5) y retira cred_falta_para_activar. No hay datos que perder.
begin;
do $$
begin
  if to_regclass('respaldo.b5_fonacot_completo_20261117') is null then
    raise exception 'BeeHuman: la corrección no está aplicada (falta respaldo.b5_fonacot_completo_20261117).';
  end if;
end $$;
do $$ declare o text; begin for o in select original from respaldo.b5_fonacot_completo_20261117 loop execute o; end loop; end $$;
drop function public.cred_falta_para_activar(public.cred_creditos);
drop table respaldo.b5_fonacot_completo_20261117;
commit;
