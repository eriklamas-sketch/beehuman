-- BeeHuman · Reversión de B5 (20261113000000_b5_creditos_descuentos).
-- Se niega si ya existen datos capturados con B5: créditos capturados (no
-- convertidos), descuentos, ajustes o movimientos de saldo, o historia más
-- allá de la conversión. Los créditos convertidos de no_fonacot se retiran
-- sin pérdida: personal.no_fonacot nunca se modificó.
-- Restaura inc_faltantes_procesar e inc_marcar_procesado (B1.1 / B1).
begin;
do $$
begin
  if to_regclass('respaldo.b5_creditos_20261113') is null then
    raise exception 'BeeHuman: B5 no está aplicada (falta respaldo.b5_creditos_20261113).';
  end if;
  if exists (select 1 from public.cred_creditos where origen <> 'conversion_no_fonacot')
     or exists (select 1 from public.cred_descuentos) or exists (select 1 from public.cred_descuentos_ajustes)
     or exists (select 1 from public.cred_movimientos) or exists (select 1 from public.cred_historia where evento <> 'conversion') then
    raise exception 'BeeHuman: hay créditos, descuentos o movimientos capturados con B5; la reversión los perdería.';
  end if;
end $$;

do $$ declare o text; begin for o in select original from respaldo.b5_creditos_20261113 loop execute o; end loop; end $$;

drop function public.cred_guardar(uuid, jsonb, text);
drop function public.cred_cambiar_estado(uuid, text, date, text);
drop function public.cred_creditos_persona(uuid);
drop function public.cred_descuentos_periodo(uuid);
drop function public.cred_decidir_descuento(uuid, numeric, text);
drop function public.cred_aceptar_descuentos(uuid);
drop function public.cred_sincronizar_periodo(uuid);
drop function public.cred_propuestas(uuid);
drop function public.cred_disponible(uuid, uuid);
drop function public.cred_validar(public.cred_creditos);
drop function public.cred_aplica(public.cred_creditos, public.inc_periodos);
drop function public.cred_saldo_actual(uuid);
drop function public.cred_etiqueta(public.cred_creditos);
drop function public.cred_es_calculable(public.cred_creditos);

-- Las tablas tienen disparadores contra borrado y truncado: se eliminan
-- completas (DROP TABLE no dispara esos disparadores).
drop table public.cred_movimientos;
drop table public.cred_descuentos_ajustes;
drop table public.cred_descuentos;
drop table public.cred_historia;
drop table public.cred_creditos;
drop function public.cred_descuentos_proteger();

drop table respaldo.b5_creditos_20261113;
commit;
