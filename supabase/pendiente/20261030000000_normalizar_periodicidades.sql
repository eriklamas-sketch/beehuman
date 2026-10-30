-- =====================================================================
-- BeeHuman · Normalización de periodicidades (30-oct-2026)
--
-- Problema: el catálogo `periodicidades` admite nombres repetidos que solo
-- cambian en mayúsculas/minúsculas (p. ej. «Quincenal» y «QUINCENAL»), y
-- ambos aparecen en los selectores.
--
-- Qué hace, por tenant y por nombre normalizado (MAYÚSCULAS, sin espacios
-- al inicio o al final):
--   1. Elige una periodicidad canónica: la más usada en esquemas de pago;
--      empate → la escrita en mayúsculas; empate → la más antigua por id.
--      La canónica conserva su nombre y sus días (no se recalcula nada).
--   2. Respalda en el esquema `respaldo` las duplicadas y cada referencia
--      que se mueve (personal, personal_registros_pago, inc_periodos).
--   3. Mueve esas referencias a la canónica. Solo cambia `periodicidad_id`;
--      sueldos, días propios, fechas e importes no se tocan. Los disparadores
--      de usuario de esas tablas se apagan solo durante este movimiento para
--      no sellar autoría ni revalidar expedientes por un cambio de catálogo.
--   4. Borra las duplicadas, que ya no tienen referencias.
--   5. Impide nuevos duplicados: índice único (tenant, nombre normalizado).
--
-- Quincenal y catorcenal siguen siendo distintas: solo se unen nombres
-- idénticos al normalizar, nunca por días parecidos.
-- Reversión: 20261030000000_reversion_normalizar_periodicidades.sql
-- =====================================================================
begin;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then execute 'revoke all on schema respaldo from anon'; end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then execute 'revoke all on schema respaldo from authenticated'; end if;
end $$;

create table if not exists respaldo.periodicidades_20261030 (
  id uuid primary key, tenant_id uuid not null, nombre text not null, dias_default numeric,
  canonica_id uuid not null, respaldado_en timestamptz not null default now());
create table if not exists respaldo.periodicidades_refs_20261030 (
  tabla text not null, fila_id uuid not null, periodicidad_anterior uuid not null, periodicidad_nueva uuid not null,
  primary key (tabla, fila_id));

do $$
declare
  hay_inc boolean := to_regclass('public.inc_periodos') is not null;
  usos_antes bigint; usos_despues bigint; n_dup int;
begin
  -- Mapa duplicada → canónica
  create temp table _mapa on commit drop as
  with p as (
    select pe.id, pe.tenant_id, pe.nombre, pe.dias_default, upper(btrim(pe.nombre)) as clave,
           (select count(*) from public.personal_registros_pago r where r.periodicidad_id = pe.id) as usos_rp
    from public.periodicidades pe
  ), orden as (
    select p.*, row_number() over (partition by tenant_id, clave
             order by usos_rp desc, (nombre = upper(nombre)) desc, id) as n
    from p
  )
  select d.id as dup_id, d.tenant_id, d.nombre, d.dias_default, c.id as canonica_id
  from orden d join orden c on c.tenant_id = d.tenant_id and c.clave = d.clave and c.n = 1
  where d.n > 1;

  select count(*) into n_dup from _mapa;
  raise notice 'Periodicidades duplicadas a unificar: %', n_dup;
  if n_dup = 0 then
    raise notice 'Sin duplicados: solo se agrega la protección.';
  else
    -- Total de referencias antes (para comprobar que no se pierde ninguna)
    select (select count(*) from public.personal where periodicidad_id is not null)
         + (select count(*) from public.personal_registros_pago)
      into usos_antes;
    if hay_inc then execute 'select $1 + count(*) from public.inc_periodos' into usos_antes using usos_antes; end if;

    insert into respaldo.periodicidades_20261030 (id, tenant_id, nombre, dias_default, canonica_id)
    select dup_id, tenant_id, nombre, dias_default, canonica_id from _mapa
    on conflict (id) do nothing;

    insert into respaldo.periodicidades_refs_20261030
    select 'personal', x.id, x.periodicidad_id, m.canonica_id from public.personal x join _mapa m on m.dup_id = x.periodicidad_id
    on conflict do nothing;
    insert into respaldo.periodicidades_refs_20261030
    select 'personal_registros_pago', r.id, r.periodicidad_id, m.canonica_id from public.personal_registros_pago r join _mapa m on m.dup_id = r.periodicidad_id
    on conflict do nothing;
    if hay_inc then
      execute 'insert into respaldo.periodicidades_refs_20261030
               select ''inc_periodos'', i.id, i.periodicidad_id, m.canonica_id from public.inc_periodos i join _mapa m on m.dup_id = i.periodicidad_id
               on conflict do nothing';
    end if;

    alter table public.personal disable trigger user;
    alter table public.personal_registros_pago disable trigger user;
    update public.personal x set periodicidad_id = m.canonica_id from _mapa m where x.periodicidad_id = m.dup_id;
    update public.personal_registros_pago r set periodicidad_id = m.canonica_id from _mapa m where r.periodicidad_id = m.dup_id;
    alter table public.personal enable trigger user;
    alter table public.personal_registros_pago enable trigger user;
    if hay_inc then
      execute 'alter table public.inc_periodos disable trigger user';
      execute 'update public.inc_periodos i set periodicidad_id = m.canonica_id from _mapa m where i.periodicidad_id = m.dup_id';
      execute 'alter table public.inc_periodos enable trigger user';
    end if;

    delete from public.periodicidades pe using _mapa m where pe.id = m.dup_id;

    select (select count(*) from public.personal where periodicidad_id is not null)
         + (select count(*) from public.personal_registros_pago)
      into usos_despues;
    if hay_inc then execute 'select $1 + count(*) from public.inc_periodos' into usos_despues using usos_despues; end if;
    if usos_antes <> usos_despues then
      raise exception 'Referencias antes % y después % no coinciden; se cancela todo.', usos_antes, usos_despues;
    end if;
  end if;

  if exists (select 1 from public.periodicidades group by tenant_id, upper(btrim(nombre)) having count(*) > 1) then
    raise exception 'Quedan periodicidades duplicadas; se cancela todo.';
  end if;
end $$;

create unique index if not exists periodicidades_tenant_nombre_unico
  on public.periodicidades (tenant_id, upper(btrim(nombre)));

commit;
