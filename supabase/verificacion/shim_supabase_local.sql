-- =====================================================================
-- BeeHuman · SHIM SUPABASE PARA UNA BASE POSTGRESQL AISLADA
-- Archivo: supabase/verificacion/shim_supabase_local.sql
-- USO: solo en una base PostgreSQL 17 vacía y desechable (local o Docker),
-- NUNCA en Supabase: allí estos objetos ya existen.
-- Crea lo mínimo que el esquema de BeeHuman espera de Supabase y no toca
-- el esquema public (no altera la huella).
-- =====================================================================
do $$
begin
  if exists (select 1 from pg_namespace where nspname in ('storage','graphql','realtime','supabase_functions')) then
    raise exception 'DETENIDO: esto parece un proyecto Supabase. El shim es solo para una base aislada.';
  end if;
end $$;

-- Roles de la API de Supabase (sin login)
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant anon, authenticated, service_role to postgres;

-- Esquema public: mismos permisos de uso que en Supabase
grant usage on schema public to postgres, anon, authenticated, service_role;

-- Privilegios por defecto de Supabase (tomados de pg_default_acl de
-- producción): todo objeto nuevo en public creado por postgres se concede
-- a anon, authenticated y service_role. Sin esto, una base aislada no se
-- comporta como Supabase al crear tablas o funciones nuevas.
alter default privileges for role postgres in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema public grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema public grant execute on functions to anon, authenticated, service_role;

-- Esquema extensions (Supabase instala ahí pgcrypto y uuid-ossp; el esquema
-- de BeeHuman no los usa: gen_random_uuid() es nativo de PostgreSQL)
create schema if not exists extensions;
grant usage on schema extensions to anon, authenticated, service_role;

-- Esquema auth mínimo: auth.users(id, email) y auth.uid()
create schema if not exists auth;
grant usage on schema auth to anon, authenticated, service_role;
create table if not exists auth.users (
  id uuid primary key,
  email text
);
-- Misma definición que usa Supabase: lee el claim «sub» de la sesión.
create or replace function auth.uid() returns uuid
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;
grant execute on function auth.uid() to anon, authenticated, service_role;
