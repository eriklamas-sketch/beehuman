-- =====================================================================
-- BeeHuman · Reversión de 20261111000000_idse_umf_numero_interno_opcionales
-- Restaura textualmente idse_validar e idse_linea_alta / _baja / _modificacion.
-- GUARDA: no se ejecuta si alguna cambió después. No toca datos: los
-- archivos ya generados con posiciones en blanco se conservan.
-- Debe revertirse ANTES que 20261109000200_idse_validadores_guia.
-- =====================================================================
begin;

do $$
declare r record;
begin
  if to_regclass('respaldo.idse_opcionales_20261111') is null then
    raise exception 'BeeHuman: la migración idse_umf_numero_interno_opcionales no está aplicada; nada que revertir.';
  end if;
  for r in select * from respaldo.idse_opcionales_20261111 loop
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) is distinct from r.md5_aplicada then
      raise exception 'BeeHuman: % cambió después de la migración; revierte primero la migración posterior.', r.objeto;
    end if;
  end loop;
  for r in select * from respaldo.idse_opcionales_20261111 loop
    execute r.original;
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) <> md5(r.original) then
      raise exception 'BeeHuman: % no quedó idéntica a la original.', r.objeto;
    end if;
  end loop;
  execute format('alter table respaldo.idse_opcionales_20261111 rename to %I',
                 'idse_opcionales_20261111_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
end $$;

commit;
