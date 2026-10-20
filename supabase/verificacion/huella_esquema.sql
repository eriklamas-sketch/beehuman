-- =====================================================================
-- BeeHuman V2.0 · Huella del esquema público (SOLO LECTURA)
-- Devuelve una huella (md5) por categoría y una total. Dos bases con la
-- misma huella tienen idénticos: funciones (cuerpo, SECURITY DEFINER y
-- permisos), políticas RLS, triggers, columnas, restricciones, índices,
-- RLS activado por tabla, permisos de tablas y definición de vistas.
-- No mira datos. Se usa antes y después de migrar y en la reversión.
-- =====================================================================
with
fn as (select string_agg(x, E'\n' order by x) s from (
  select p.proname||'('||pg_get_function_identity_arguments(p.oid)||')|'||md5(pg_get_functiondef(p.oid))||'|'||p.prosecdef||'|'||coalesce(array_to_string(p.proacl,','),'') x
  from pg_proc p where p.pronamespace='public'::regnamespace and p.prokind='f') t),
pol as (select string_agg(x, E'\n' order by x) s from (
  select tablename||'.'||policyname||'|'||cmd||'|'||permissive||'|'||array_to_string(roles,',')||'|'||coalesce(qual,'')||'|'||coalesce(with_check,'') x
  from pg_policies where schemaname='public') t),
trg as (select string_agg(x, E'\n' order by x) s from (
  select c.relname||'.'||t.tgname||'|'||pg_get_triggerdef(t.oid)||'|'||t.tgenabled::text x
  from pg_trigger t join pg_class c on c.oid=t.tgrelid
  where c.relnamespace='public'::regnamespace and not t.tgisinternal) t),
col as (select string_agg(x, E'\n' order by x) s from (
  select table_name||'.'||column_name||'|'||data_type||'|'||coalesce(column_default,'')||'|'||is_nullable x
  from information_schema.columns where table_schema='public') t),
con as (select string_agg(x, E'\n' order by x) s from (
  select conrelid::regclass::text||'.'||conname||'|'||pg_get_constraintdef(oid) x
  from pg_constraint where connamespace='public'::regnamespace) t),
idx as (select string_agg(x, E'\n' order by x) s from (
  select indexname||'|'||indexdef x from pg_indexes where schemaname='public') t),
tbl as (select string_agg(x, E'\n' order by x) s from (
  select c.relname||'|'||c.relkind::text||'|'||c.relrowsecurity||'|'||coalesce(array_to_string(c.relacl,','),'')||'|'||coalesce(array_to_string(c.reloptions,','),'') x
  from pg_class c where c.relnamespace='public'::regnamespace and c.relkind in ('r','v','S')) t),
vw as (select string_agg(x, E'\n' order by x) s from (
  select c.relname||'|'||pg_get_viewdef(c.oid) x
  from pg_class c where c.relnamespace='public'::regnamespace and c.relkind='v') t)
select md5(fn.s) funciones, md5(pol.s) politicas, md5(trg.s) triggers, md5(col.s) columnas,
       md5(con.s) restricciones, md5(idx.s) indices, md5(tbl.s) tablas_permisos, md5(vw.s) vistas,
       md5(fn.s||pol.s||trg.s||col.s||con.s||idx.s||tbl.s||vw.s) total
from fn, pol, trg, col, con, idx, tbl, vw;
