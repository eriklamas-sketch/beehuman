-- =====================================================================
-- BeeHuman V2.0 · Huellas de beehuman-pruebas (SOLO LECTURA)
-- Ejecutar ANTES y DESPUÉS de prueba_compatibilidad_beehuman-pruebas.sql.
-- Ambos resultados deben ser idénticos fila por fila.
-- Línea base registrada 18-oct-2026 12:10: evidencia_antes_20261018.txt
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
  from pg_class c where c.relnamespace='public'::regnamespace and c.relkind='v') t),
dat as (
  select tabla, count(*) filas, md5(string_agg(j::text, '|' order by k)) h from (
    select 'personal' tabla, t.id::text k, to_jsonb(t) j from public.personal t
    union all select 'personal_registros_pago', t.id::text, to_jsonb(t) from public.personal_registros_pago t
    union all select 'movimientos', t.id::text, to_jsonb(t) from public.movimientos t
    union all select 'empresas', t.id::text, to_jsonb(t) from public.empresas t
    union all select 'empresas_registros_patronales', t.id::text, to_jsonb(t) from public.empresas_registros_patronales t
    union all select 'usuarios_tenant', t.user_id::text, to_jsonb(t) from public.usuarios_tenant t
    union all select 'usuario_alcances', t.id::text, to_jsonb(t) from public.usuario_alcances t
    union all select 'tenants', t.id::text, to_jsonb(t) from public.tenants t
    union all select 'proyectos', t.id::text, to_jsonb(t) from public.proyectos t
    union all select 'periodicidades', t.id::text, to_jsonb(t) from public.periodicidades t
    union all select 'clasificaciones_personal', t.id::text, to_jsonb(t) from public.clasificaciones_personal t
    union all select 'areas', t.id::text, to_jsonb(t) from public.areas t
    union all select 'departamentos', t.id::text, to_jsonb(t) from public.departamentos t
    union all select 'puestos', t.id::text, to_jsonb(t) from public.puestos t
    union all select 'localidades', t.id::text, to_jsonb(t) from public.localidades t
    union all select 'centros_costo', t.id::text, to_jsonb(t) from public.centros_costo t
    union all select 'combos', t.id::text, to_jsonb(t) from public.combos t
    union all select 'combo_conceptos', t.id::text, to_jsonb(t) from public.combo_conceptos t
    union all select 'conceptos_percepcion', t.id::text, to_jsonb(t) from public.conceptos_percepcion t
    union all select 'personal_percepciones', t.id::text, to_jsonb(t) from public.personal_percepciones t) x group by tabla)
select 'ESQUEMA' clase, 'total' item, md5(fn.s||pol.s||trg.s||col.s||con.s||idx.s||tbl.s||vw.s) valor, null::bigint filas from fn,pol,trg,col,con,idx,tbl,vw
union all select 'DATOS', tabla, h, filas from dat
union all select 'SECUENCIA','personal_empleado_id_seq', last_value::text, null from public.personal_empleado_id_seq
union all select 'SESIONES','idle in transaction', count(*)::text, null from pg_stat_activity where datname=current_database() and state like 'idle in transaction%'
union all select 'RESIDUOS','areas ZZ_PRUEBA_AISLAMIENTO_A/B', count(*)::text, null from public.areas where nombre in ('ZZ_PRUEBA_AISLAMIENTO_A','ZZ_PRUEBA_AISLAMIENTO_B')
order by 1,2;
