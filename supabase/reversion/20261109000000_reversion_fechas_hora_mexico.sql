-- =====================================================================
-- BeeHuman · Reversión de 20261109000000_fechas_hora_mexico
-- Restaura textualmente las funciones y los valores por omisión guardados
-- en respaldo.fechas_hora_mexico_20261109 y borra hoy_mx() y fecha_mx().
-- GUARDA: no se ejecuta si alguna función cambió después de la migración
-- o si algún valor por omisión ya no es public.hoy_mx().
-- No toca datos. La auditoría y el respaldo se renombran (traza) para
-- permitir reaplicar.
-- =====================================================================
begin;

do $$
declare r record; t text; c text;
begin
  if to_regclass('respaldo.fechas_hora_mexico_20261109') is null then
    raise exception 'BeeHuman: la migración fechas_hora_mexico no está aplicada; nada que revertir.';
  end if;
  for r in select * from respaldo.fechas_hora_mexico_20261109 where tipo = 'funcion' loop
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) is distinct from r.md5_aplicada then
      raise exception 'BeeHuman: % cambió después de la migración; revierte primero la migración posterior.', r.objeto;
    end if;
  end loop;
  for r in select * from respaldo.fechas_hora_mexico_20261109 where tipo = 'valor_omision' loop
    t := split_part(r.objeto, '.', 1); c := split_part(r.objeto, '.', 2);
    if coalesce((select column_default from information_schema.columns where table_schema = 'public' and table_name = t and column_name = c), '')
       !~ '^(public\.)?hoy_mx\(\)$' then
      raise exception 'BeeHuman: el valor por omisión de % cambió después de la migración.', r.objeto;
    end if;
  end loop;

  for r in select * from respaldo.fechas_hora_mexico_20261109 where tipo = 'funcion' loop
    execute r.original;
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) <> md5(r.original) then
      raise exception 'BeeHuman: % no quedó idéntica a la original.', r.objeto;
    end if;
  end loop;
  for r in select * from respaldo.fechas_hora_mexico_20261109 where tipo = 'valor_omision' loop
    execute format('alter table public.%I alter column %I set default %s', split_part(r.objeto, '.', 1), split_part(r.objeto, '.', 2), r.original);
  end loop;

  execute format('alter table respaldo.fechas_hora_mexico_20261109 rename to %I',
                 'fechas_hora_mexico_20261109_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
  execute format('alter table auditoria.fechas_utc_20261109 rename to %I',
                 'fechas_utc_20261109_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
end $$;

drop function public.hoy_mx();
drop function public.fecha_mx(timestamptz);

commit;
