-- =====================================================================
-- BeeHuman · Reversión de 20261109000200_idse_validadores_guia
-- Restaura textualmente idse_validar e idse_generar_archivo y borra
-- es_nss_imss_valido. GUARDA: no se ejecuta si alguna cambió después.
-- No toca datos. Los archivos generados con guía 00000 se conservan.
-- Debe revertirse ANTES que 20261109000000_fechas_hora_mexico.
-- =====================================================================
begin;

do $$
declare r record;
begin
  if to_regclass('respaldo.idse_validadores_guia_20261109') is null then
    raise exception 'BeeHuman: la migración idse_validadores_guia no está aplicada; nada que revertir.';
  end if;
  for r in select * from respaldo.idse_validadores_guia_20261109 loop
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) is distinct from r.md5_aplicada then
      raise exception 'BeeHuman: % cambió después de la migración; revierte primero la migración posterior.', r.objeto;
    end if;
  end loop;
  for r in select * from respaldo.idse_validadores_guia_20261109 loop
    execute r.original;
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) <> md5(r.original) then
      raise exception 'BeeHuman: % no quedó idéntica a la original.', r.objeto;
    end if;
  end loop;
  execute format('alter table respaldo.idse_validadores_guia_20261109 rename to %I',
                 'idse_validadores_guia_20261109_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
end $$;
drop function public.es_nss_imss_valido(text);

commit;
