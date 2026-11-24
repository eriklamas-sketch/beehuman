-- BeeHuman · Reversión de 20261124000100_ola1_fechas_hora_mexico.sql · 24-nov-2026
-- Restaura textualmente lo que la corrección cambió (si cambió algo) y borra su tabla de respaldo.
-- Se niega si una función corregida fue modificada después (su md5 ya no es el que dejó la corrección).
-- No toca datos.
begin;
do $$
declare r record;
begin
  if to_regclass('respaldo.ola1_fechas_hora_mexico_20261124') is null then
    raise exception 'BeeHuman: la corrección de fechas de Ola 1 no está aplicada.';
  end if;
  for r in select * from respaldo.ola1_fechas_hora_mexico_20261124 where tipo = 'funcion' loop
    if md5(pg_get_functiondef(r.objeto::regprocedure)) is distinct from r.md5_aplicada then
      raise exception 'BeeHuman: % cambió después de la corrección; revisa antes de revertir.', r.objeto;
    end if;
    execute r.original;
  end loop;
  for r in select * from respaldo.ola1_fechas_hora_mexico_20261124 where tipo = 'valor_omision' loop
    execute format('alter table public.%I alter column %I set default %s', split_part(r.objeto, '.', 1), split_part(r.objeto, '.', 2), r.original);
  end loop;
end $$;
drop table respaldo.ola1_fechas_hora_mexico_20261124;
commit;
