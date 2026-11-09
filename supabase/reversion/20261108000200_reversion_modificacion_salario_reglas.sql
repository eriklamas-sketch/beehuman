-- =====================================================================
-- BeeHuman · Reversión de 20261108000200_modificacion_salario_reglas
-- Restaura textualmente las definiciones guardadas al aplicar
-- (respaldo.modificacion_salario_20261108) y borra laboral_importe_texto.
-- GUARDA: no se ejecuta si alguna de las dos funciones cambió después de la
-- migración (otra migración posterior debe revertirse primero).
-- No toca datos: los eventos y movimientos registrados se conservan.
-- El respaldo se renombra (traza) para permitir reaplicar.
-- =====================================================================
begin;

do $$
declare r record;
begin
  if to_regclass('respaldo.modificacion_salario_20261108') is null then
    raise exception 'BeeHuman: la migración modificacion_salario_reglas no está aplicada; nada que revertir.';
  end if;
  for r in select * from respaldo.modificacion_salario_20261108 loop
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) is distinct from r.md5_aplicada then
      raise exception 'BeeHuman: % cambió después de la migración; revierte primero la migración posterior.', r.objeto;
    end if;
  end loop;
  for r in select * from respaldo.modificacion_salario_20261108 loop
    execute r.original;
    if md5(pg_get_functiondef(to_regprocedure(r.objeto))) <> md5(r.original) then
      raise exception 'BeeHuman: % no quedó idéntica a la original.', r.objeto;
    end if;
  end loop;
  execute format('alter table respaldo.modificacion_salario_20261108 rename to %I',
                 'modificacion_salario_20261108_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
end $$;
drop function public.laboral_importe_texto(numeric);

commit;
