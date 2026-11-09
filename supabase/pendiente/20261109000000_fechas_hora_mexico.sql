-- =====================================================================
-- BeeHuman · Fechas en hora de México (Incidencia 5) · 9-nov-2026
-- En Supabase el servidor usa UTC: entre las 18:00 y las 23:59 de México,
-- current_date ya es «mañana». Esta migración:
--   1. crea public.fecha_mx(timestamptz) y public.hoy_mx();
--   2. sustituye current_date por public.hoy_mx() en las funciones que lo
--      usan (las que existan en este entorno) y en 3 valores por omisión;
--   3. registra, SIN modificarlos, los acontecimientos de la bitácora y las
--      fechas de asignación que quedaron un día adelantadas
--      (auditoria.fechas_utc_20261109).
-- Las definiciones originales se guardan textualmente en
-- respaldo.fechas_hora_mexico_20261109 (cada entorno guarda la suya; en
-- pruebas las funciones están compactadas y no hay md5 portable).
-- No cambia ninguna otra lógica. No toca datos de negocio.
-- Reversión: supabase/reversion/20261109000000_reversion_fechas_hora_mexico.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.fechas_hora_mexico_20261109') is not null then
    raise exception 'BeeHuman: la migración fechas_hora_mexico ya está aplicada.';
  end if;
  if to_regprocedure('public.hoy_mx()') is not null then
    raise exception 'BeeHuman: public.hoy_mx() ya existe; revisa qué migración la creó antes de continuar.';
  end if;
end $$;

create schema if not exists respaldo;
create schema if not exists auditoria;
revoke all on schema respaldo, auditoria from public;

create table respaldo.fechas_hora_mexico_20261109 (
  tipo        text not null check (tipo in ('funcion', 'valor_omision')),
  objeto      text primary key,          -- firma de la función o tabla.columna
  original    text not null,             -- definición o expresión original
  md5_aplicada text                       -- definición después de la migración (guarda de la reversión)
);

-- 1. Fecha de México ---------------------------------------------------
create function public.fecha_mx(p_momento timestamptz) returns date
language sql stable set search_path to '' as $$
  select (p_momento at time zone 'America/Mexico_City')::date
$$;
comment on function public.fecha_mx(timestamptz) is 'BeeHuman: día calendario de México de un instante (el servidor usa UTC).';

create function public.hoy_mx() returns date
language sql stable set search_path to '' as $$
  select public.fecha_mx(now())
$$;
comment on function public.hoy_mx() is 'BeeHuman: fecha de hoy en México. Usar en lugar de current_date.';

-- 2. Funciones: current_date → public.hoy_mx() ---------------------------
-- Usos esperados por función (si la función existe en este entorno).
do $$
declare
  esperado constant jsonb := '{"idse_validar": 1, "inc_asignacion_desde_expediente": 1, "laboral_corregir_datos": 3,
                               "laboral_evento_por_ficha": 2, "laboral_evento_por_registro_pago": 2}';
  f record; def text; nueva text; n int;
begin
  for f in select p.oid, p.proname, p.oid::regprocedure::text as firma
             from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind = 'f'
              and pg_get_functiondef(p.oid) ~* 'current_date' loop
    if not esperado ? f.proname then
      raise exception 'BeeHuman: % usa current_date y no está en el inventario de esta migración; revísala antes de aplicar.', f.firma;
    end if;
    def := pg_get_functiondef(f.oid);
    n := (select count(*) from regexp_matches(def, '\mcurrent_date\M', 'gi'));
    if n <> (esperado ->> f.proname)::int then
      raise exception 'BeeHuman: % tiene % usos de current_date; se esperaban %. Revisa si cambió.', f.firma, n, esperado ->> f.proname;
    end if;
    insert into respaldo.fechas_hora_mexico_20261109 (tipo, objeto, original) values ('funcion', f.firma, def);
    nueva := regexp_replace(def, '\mcurrent_date\M', 'public.hoy_mx()', 'gi');
    execute nueva;
    update respaldo.fechas_hora_mexico_20261109 set md5_aplicada = md5(pg_get_functiondef(f.oid)) where objeto = f.firma;
  end loop;
end $$;

-- 3. Valores por omisión ------------------------------------------------
do $$
declare c record;
begin
  for c in select table_name, column_name, column_default from information_schema.columns
            where table_schema = 'public' and column_default ~* '^\s*current_date\s*$' loop
    if (c.table_name || '.' || c.column_name) not in ('personal.fecha_asignacion', 'personal_registros_pago.fecha_inicio', 'inc_parametros.inicio_historial') then
      raise exception 'BeeHuman: %.% usa current_date por omisión y no está en el inventario.', c.table_name, c.column_name;
    end if;
    insert into respaldo.fechas_hora_mexico_20261109 (tipo, objeto, original)
      values ('valor_omision', c.table_name || '.' || c.column_name, c.column_default);
    execute format('alter table public.%I alter column %I set default public.hoy_mx()', c.table_name, c.column_name);
  end loop;
end $$;

-- 4. Guarda: ya no queda current_date en funciones ni valores por omisión --
do $$
begin
  if exists (select 1 from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind = 'f'
              and pg_get_functiondef(p.oid) ~* '\mcurrent_date\M') then
    raise exception 'BeeHuman: todavía hay funciones con current_date.';
  end if;
  if exists (select 1 from information_schema.columns where table_schema = 'public' and column_default ~* 'current_date') then
    raise exception 'BeeHuman: todavía hay valores por omisión con current_date.';
  end if;
end $$;

-- 5. Auditoría de lo ya registrado (no se modifica nada) -----------------
-- Regla: la fecha salió de current_date (no la escribió el usuario), es la
-- fecha UTC del momento de captura y es un día después de la de México.
create table auditoria.fechas_utc_20261109 (
  tabla           text not null,
  registro_id     uuid not null,
  campo           text not null,
  fecha_guardada  date not null,
  fecha_correcta  date not null,
  capturado_en    timestamptz not null,
  detalle         text,
  registrado_en   timestamptz not null default now(),
  primary key (tabla, registro_id, campo)
);
comment on table auditoria.fechas_utc_20261109 is
  'BeeHuman: fechas guardadas en UTC (un día adelantadas) antes de la migración 20261109000000. Los acontecimientos de la bitácora se conservan sin cambios; aquí consta su fecha correcta.';

do $$
begin
  if to_regclass('public.eventos_laborales') is not null then
    insert into auditoria.fechas_utc_20261109 (tabla, registro_id, campo, fecha_guardada, fecha_correcta, capturado_en, detalle)
    select 'eventos_laborales', e.id, 'fecha_efectiva', e.fecha_efectiva, public.fecha_mx(e.registrado_en), e.registrado_en,
           e.tipo || ' · ' || e.origen || ' · se conserva sin cambios (bitácora inmutable)'
      from public.eventos_laborales e
     where e.origen in ('automatico', 'pantalla')
       and e.tipo in ('cambio_esquema_pago', 'correccion_datos', 'cambio_puesto', 'cambio_jefe', 'cambio_organizacion')
       and e.fecha_efectiva = (e.registrado_en at time zone 'UTC')::date
       and e.fecha_efectiva = public.fecha_mx(e.registrado_en) + 1;
  end if;
  insert into auditoria.fechas_utc_20261109 (tabla, registro_id, campo, fecha_guardada, fecha_correcta, capturado_en, detalle)
  select 'personal', p.id, 'fecha_asignacion', p.fecha_asignacion, public.fecha_mx(p.created_at), p.created_at,
         'valor por omisión en UTC; se corrige aparte con supabase/datos/20261109000100_corregir_fecha_asignacion_utc.sql'
    from public.personal p
   where p.fecha_asignacion = (p.created_at at time zone 'UTC')::date
     and p.fecha_asignacion = public.fecha_mx(p.created_at) + 1;
  insert into auditoria.fechas_utc_20261109 (tabla, registro_id, campo, fecha_guardada, fecha_correcta, capturado_en, detalle)
  select 'personal_registros_pago', r.id, 'fecha_inicio', r.fecha_inicio, public.fecha_mx(r.created_at), r.created_at,
         'valor por omisión en UTC; revisar caso por caso (la fecha de inicio también se captura en pantalla)'
    from public.personal_registros_pago r
   where r.fecha_inicio = (r.created_at at time zone 'UTC')::date
     and r.fecha_inicio = public.fecha_mx(r.created_at) + 1;
end $$;

commit;
