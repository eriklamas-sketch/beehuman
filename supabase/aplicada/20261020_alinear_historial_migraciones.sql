-- =====================================================================
-- BeeHuman · Alinear el historial de migraciones de PRODUCCIÓN con el repositorio
-- Archivo: supabase/aplicada/20261020_alinear_historial_migraciones.sql
-- DESTINO: producción (vovyvvpwtjdlswerfjqb), SQL Editor. Autorizado por Erik el 20-oct-2026.
--
-- Qué hace (equivale a `supabase migration repair`, sin instalar la CLI):
--   1. Guarda las 11 filas actuales del historial en
--      supabase_migrations.schema_migrations_respaldo_20261020 (nada se pierde).
--   2. Quita del historial las 10 versiones antiguas (fase 7a … 7d6), que en el
--      repositorio sustituye 20261001173928_base_v1_esquema_reconstruido.sql.
--   3. Registra 20261018000000 (V2.0) como aplicada.
-- Resultado: historial = 20261001173928, 20261018000000 = carpeta supabase/migrations.
--
-- Solo cambia METADATOS del historial. No ejecuta cambios de esquema ni toca
-- datos: las huellas ebcd0aad… (esquema) y de datos no cambian.
-- Si algo no cuadra, se revierte todo y no queda nada aplicado.
-- Para deshacer: borrar las 2 filas actuales e insertar de nuevo las 11 del respaldo.
-- =====================================================================
begin;

do $$
begin
  if to_regclass('supabase_migrations.schema_migrations_respaldo_20261020') is not null then
    raise exception 'DETENIDO: el respaldo ya existe; este archivo ya se ejecutó. No se aplicó nada.';
  end if;
  if (select string_agg(version, ',' order by version) from supabase_migrations.schema_migrations) <>
     '20260928222644,20260928231550,20260928232701,20260928234451,20260928235220,20260928235919,20260929144837,20260929144906,20260929180714,20260929195237,20261001173928' then
    raise exception 'DETENIDO: el historial no es el esperado. No se aplicó nada.';
  end if;
end $$;

create table supabase_migrations.schema_migrations_respaldo_20261020 as
  select * from supabase_migrations.schema_migrations;

delete from supabase_migrations.schema_migrations where version < '20261001173928';

insert into supabase_migrations.schema_migrations (version, name, statements)
values ('20261018000000', 'beehuman_v2_0_roles_m1_m2', array[
'-- Aplicada el 20-oct-2026 en el SQL Editor de Supabase (no por la CLI). Texto aplicado: supabase/aplicada/V2.0_migracion_pegable.sql, SHA-256 cb6d4e707646d30ccdf678947df3de8c22d4c74faf80fca9fdc27a2d401aeedd (equivalente a supabase/migrations/20261018000000_beehuman_v2_0_roles_m1_m2.sql, SHA-256 49a6369db8f2c0f47fa2d00459f419d928bf81c6c51cf91951eee756e5a4357a). Esquema resultante: huella ebcd0aad4284c492ae7b44b379d6e208. Las 11 filas previas del historial están en supabase_migrations.schema_migrations_respaldo_20261020.']);

do $$
begin
  if (select count(*) from supabase_migrations.schema_migrations_respaldo_20261020) <> 11 then
    raise exception 'Verificación: el respaldo no tiene 11 filas.';
  end if;
  if (select string_agg(version, ',' order by version) from supabase_migrations.schema_migrations) <> '20261001173928,20261018000000' then
    raise exception 'Verificación: el historial resultante no es el esperado.';
  end if;
end $$;

commit;

-- Resultado esperado: 2 renglones (20261001173928 y 20261018000000).
select version, name from supabase_migrations.schema_migrations order by version;
