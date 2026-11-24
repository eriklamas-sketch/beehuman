-- BeeHuman · Ola 1: fechas en hora de México en el orden de PRODUCCIÓN (D2) · 24-nov-2026
-- Autorización de Erik (24-nov 11:49): preparar, documentar y probar en local. NO aplicar en bases remotas todavía.
--
-- Por qué existe:
--  * La migración 20261109000000_fechas_hora_mexico sustituyó current_date por public.hoy_mx() en las funciones
--    y valores por omisión que EXISTÍAN al aplicarla.
--  * En beehuman-pruebas, Ola 1 (20261028000000) se aplicó ANTES que esa migración, así que sus objetos se corrigieron.
--  * En producción el orden es el inverso: la fase 1 (con fechas_hora_mexico) ya está aplicada y Ola 1 entrará
--    DESPUÉS. Dos objetos de Ola 1 quedarían con current_date, que en Supabase es la fecha UTC
--    (entre las 18:00 y las 23:59 de México ya es «mañana»):
--      - public.inc_asignacion_desde_expediente(): fecha «desde» al cambiar el coordinador en la ficha;
--      - public.inc_parametros.inicio_historial: valor por omisión.
--  * Detectado en el ensayo local del orden de producción (claude/Candidato-liberacion-Ba-Bc-B6-24nov.md, §4).
--
-- Qué hace: aplica a esos dos objetos exactamente la misma sustitución que 20261109000000 (current_date → public.hoy_mx()),
-- con inventario cerrado; cualquier otro current_date en public detiene la migración. Guarda el original textual en
-- respaldo.ola1_fechas_hora_mexico_20261124 para la reversión. CREATE OR REPLACE conserva dueño y permisos.
-- Idempotente en efecto: donde ya no hay current_date (beehuman-pruebas) no cambia nada y no guarda nada.
-- Orden: después de 20261028000000_ola1_hoja_coordinador (lo exige) y de 20261109000000 (usa public.hoy_mx()).
-- EN PRODUCCIÓN: ejecutar INMEDIATAMENTE DESPUÉS de Ola 1 y ANTES de registrar cualquier asignación de coordinador
-- (paso 1b de la etapa 2; aunque el nombre del archivo la ordene al final, ahí es donde va). Decisión D2 de Erik, 24-nov.
-- No toca datos. Si se aplica justo después de Ola 1 no hay asignaciones afectadas; si no, la consulta de auditoría
-- de la reversión/documentación permite localizarlas.
-- Reversión: reversion/20261124000100_reversion_ola1_fechas_hora_mexico.sql
begin;
do $$
begin
  if to_regclass('respaldo.ola1_fechas_hora_mexico_20261124') is not null then
    raise exception 'BeeHuman: la corrección de fechas de Ola 1 ya está aplicada.';
  end if;
  if to_regprocedure('public.hoy_mx()') is null then
    raise exception 'BeeHuman: requiere 20261109000000_fechas_hora_mexico (public.hoy_mx).';
  end if;
  if to_regclass('public.inc_parametros') is null or to_regprocedure('public.inc_asignacion_desde_expediente()') is null then
    raise exception 'BeeHuman: requiere Ola 1 (20261028000000).';
  end if;
end $$;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
create table respaldo.ola1_fechas_hora_mexico_20261124 (
  tipo         text not null check (tipo in ('funcion', 'valor_omision')),
  objeto       text primary key,
  original     text not null,
  md5_aplicada text
);

-- Funciones: inventario cerrado (nombre → usos esperados de current_date).
do $$
declare
  esperado constant jsonb := '{"inc_asignacion_desde_expediente": 1}';
  f record; def text; n int;
begin
  for f in select p.oid, p.proname, p.oid::regprocedure::text as firma
             from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind = 'f'
              and pg_get_functiondef(p.oid) ~* '\mcurrent_date\M' loop
    if not esperado ? f.proname then
      raise exception 'BeeHuman: % usa current_date y no está en el inventario de esta corrección; revísala antes de aplicar.', f.firma;
    end if;
    def := pg_get_functiondef(f.oid);
    n := (select count(*) from regexp_matches(def, '\mcurrent_date\M', 'gi'));
    if n <> (esperado ->> f.proname)::int then
      raise exception 'BeeHuman: % tiene % usos de current_date; se esperaban %.', f.firma, n, esperado ->> f.proname;
    end if;
    insert into respaldo.ola1_fechas_hora_mexico_20261124 (tipo, objeto, original) values ('funcion', f.firma, def);
    execute regexp_replace(def, '\mcurrent_date\M', 'public.hoy_mx()', 'gi');
    update respaldo.ola1_fechas_hora_mexico_20261124 set md5_aplicada = md5(pg_get_functiondef(f.oid)) where objeto = f.firma;
  end loop;
end $$;

-- Valores por omisión: inventario cerrado.
do $$
declare c record;
begin
  for c in select table_name, column_name, column_default from information_schema.columns
            where table_schema = 'public' and column_default ~* '\mcurrent_date\M' loop
    if (c.table_name || '.' || c.column_name) <> 'inc_parametros.inicio_historial' or c.column_default !~* '^\s*current_date\s*$' then
      raise exception 'BeeHuman: %.% usa current_date por omisión (%) y no está en el inventario.', c.table_name, c.column_name, c.column_default;
    end if;
    insert into respaldo.ola1_fechas_hora_mexico_20261124 (tipo, objeto, original)
      values ('valor_omision', c.table_name || '.' || c.column_name, c.column_default);
    execute format('alter table public.%I alter column %I set default public.hoy_mx()', c.table_name, c.column_name);
  end loop;
end $$;

-- Guarda final: no queda current_date en funciones ni en valores por omisión de public.
do $$
declare n int;
begin
  if exists (select 1 from pg_proc p where p.pronamespace = 'public'::regnamespace and p.prokind = 'f'
              and pg_get_functiondef(p.oid) ~* '\mcurrent_date\M')
     or exists (select 1 from information_schema.columns where table_schema = 'public' and column_default ~* '\mcurrent_date\M') then
    raise exception 'BeeHuman: todavía queda current_date en public.';
  end if;
  select count(*) into n from respaldo.ola1_fechas_hora_mexico_20261124;
  raise notice 'B-D2: % objeto(s) de Ola 1 pasaron a la fecha de México (0 = ya estaban corregidos).', n;
end $$;
commit;
