-- Reversión de 20261104000000_eventos_laborales_idse.sql
-- Quita todo lo que agregó la etapa 1. Las fichas de personal conservan los
-- valores que les copió el historial (empresa, RP, alta/baja, SDI, número
-- interno, antigüedad): no se restauran valores anteriores porque esos
-- cambios fueron capturas reales hechas por los usuarios.
--
-- DOS ESCENARIOS DISTINTOS:
--   a) Sin operaciones (solo hay datos migrados): reversión ordinaria y segura.
--   b) Con operaciones reales (ingresos, bajas, modificaciones, cambios
--      registrados o archivos IDSE): NO es una recuperación ordinaria; destruye
--      historial real y archivos presentados al IMSS. Se bloquea salvo que se
--      confirme expresamente, después de exportar las tablas:
--        set beehuman.reversion_con_datos = 'confirmo';
-- Qué NO se quita, a propósito: el respaldo de la ficha
-- (respaldo.personal_ficha_20261104) y la extensión btree_gist (la usa la
-- Ola 1). Por eso el esquema público queda como antes, pero la base no queda
-- literalmente idéntica: conserva esos dos elementos.
begin;
-- Se considera captura de usuarios todo lo que la migración no creó:
-- eventos no migrados, archivos IDSE, primas de riesgo y la configuración
-- IDSE de los registros patronales (guía y zona de salario mínimo).
do $$
declare n_ev bigint := 0; n_arch bigint := 0; n_prima bigint := 0; n_rp bigint := 0;
begin
  if to_regclass('public.eventos_laborales') is not null then
    select count(*) into n_ev from public.eventos_laborales where origen <> 'migracion';
    select count(*) into n_arch from public.idse_archivos;
    select count(*) into n_prima from public.prima_riesgo_rp;
    select count(*) into n_rp from public.empresas_registros_patronales
     where guia_idse is not null or zona_salario_minimo <> 'general';
  end if;
  if (n_ev + n_arch + n_prima + n_rp) > 0 and coalesce(current_setting('beehuman.reversion_con_datos', true), '') <> 'confirmo' then
    raise exception 'BeeHuman: hay datos capturados por usuarios (% eventos, % archivos IDSE, % primas de riesgo, % registros patronales con guía o zona). Esta reversión los destruiría. Exporta las tablas y confirma con: set beehuman.reversion_con_datos = ''confirmo'';', n_ev, n_arch, n_prima, n_rp;
  end if;
end $$;
drop trigger if exists trg_laboral_proteger_ficha on public.personal;
drop trigger if exists trg_laboral_evento_por_ficha on public.personal;
drop trigger if exists trg_laboral_enlazar_registro_pago on public.personal_registros_pago;
drop trigger if exists trg_laboral_evento_por_registro_pago on public.personal_registros_pago;

alter table public.personal_registros_pago drop constraint if exists personal_registros_pago_relacion_fk;
drop index if exists public.prp_relacion_idx;
alter table public.personal_registros_pago drop column if exists relacion_laboral_id;

drop table if exists public.idse_archivo_renglones, public.idse_movimientos, public.idse_archivos,
  public.eventos_laborales, public.relaciones_laborales, public.prima_riesgo_rp,
  public.causas_baja, public.parametros_generales cascade;

alter table public.empresas_registros_patronales drop column if exists guia_idse;
alter table public.empresas_registros_patronales drop column if exists zona_salario_minimo;

do $$
declare f record;
begin
  for f in select p.oid::regprocedure sig from pg_proc p
           where p.pronamespace = 'public'::regnamespace
             and (p.proname like 'laboral\_%' or p.proname like 'idse\_%' or p.proname in ('parametro_vigente','prima_riesgo_registrar')) loop
    execute format('drop function %s', f.sig);
  end loop;
end $$;
-- btree_gist se conserva: también lo usa la Ola 1.
commit;
