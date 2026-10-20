-- =====================================================================
-- BeeHuman V2.0 · Migración única de cierre (roles + M1 + M2)
-- Archivo: supabase/migrations/20261018000000_beehuman_v2_0_roles_m1_m2.sql
-- VARIANTE PEGABLE: las 6 funciones multilínea se crean con E'' para que
-- pegar en el editor de Windows no altere sus saltos de línea. Resultado
-- idéntico (lo exige la misma verificación final ebcd0aad…).
-- DESTINO: PRODUCCIÓN (vovyvvpwtjdlswerfjqb). ESTADO: preparada, NO aplicada.
--
-- Reconstruye en producción exactamente el esquema aprobado en
-- beehuman-pruebas (sflvpgkmtaxzogpgetxn) al 17-oct-2026:
--   A. Roles: Administrador, Nómina, Consulta, Coordinador
--      (usuarios_tenant.rol / personal_id, current_rol, tiene_rol,
--      políticas por operación y por rol, autoría de cambios, movimientos
--      con usuario sellado por el servidor, permisos endurecidos).
--   B. M1: número interno + índice único por tenant y registro patronal
--      + función de coincidencias.
--   C. M2: ámbito de Consulta (usuario_alcances) y «Mi equipo» del
--      Coordinador; Consulta sin directorio, catálogos ni compensación.
--   D. Asignación explícita de roles a las 2 cuentas existentes.
--
-- Garantías (si alguna falla, se revierte TODO y no queda nada aplicado):
--   * Solo corre en producción y solo sobre el esquema de hoy
--     (huella 03e98353d5e19d32ad52fd84b464f608).
--   * Solo corre si existen exactamente las 2 cuentas conocidas.
--   * No modifica ni borra filas de datos: solo agrega columnas,
--     tabla nueva, funciones, políticas y permisos. Los conteos de todas
--     las tablas se comparan antes y después.
--   * Al terminar, el esquema debe tener la huella de pruebas
--     (ebcd0aad4284c492ae7b44b379d6e208); si no, no se confirma.
--
-- Cuentas y roles (D):
--   erik.lamas@gmail.com   28b037db-6fde-4175-8408-a644c6aeee50
--     tenant «BeeHuman — Entorno inicial»  → administrador
--   demo@beehuman.invalid  c42d6b9a-b543-4b52-a621-b19d26d5041b
--     tenant «BeeHuman — Demo» (datos ficticios) → administrador
--     (mantiene el acceso que tiene hoy; ver decisión D1 en el cierre)
--   Cuentas de prueba: no existen en producción; las de beehuman-pruebas
--   no se migran. Cualquier cuenta futura nace como «consulta» sin
--   ámbito: no ve ninguna persona hasta que se le asigne rol o ámbito.
-- =====================================================================
begin;

-- @@CANDADO_PROD_INICIO -----------------------------------------------
do $$
declare h text;
begin
  if not exists (select 1 from public.tenants where id = '00000000-0000-4000-8000-de0000000001' and nombre = 'BeeHuman — Demo')
     or not exists (select 1 from public.tenants where id = '99f1a014-0cd4-44c3-8d2f-cfa15dc5a1ed' and nombre = 'BeeHuman — Entorno inicial') then
    raise exception 'DETENIDO: no se reconoce producción. No se aplicó nada.';
  end if;
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='usuarios_tenant' and column_name='rol') then
    raise exception 'DETENIDO: V2.0 ya parece aplicada (usuarios_tenant.rol existe). No se aplicó nada.';
  end if;
  if (select count(*) from public.usuarios_tenant) <> 2
     or not exists (select 1 from public.usuarios_tenant ut join auth.users u on u.id = ut.user_id
                    where ut.user_id = '28b037db-6fde-4175-8408-a644c6aeee50' and u.email = 'erik.lamas@gmail.com'
                      and ut.tenant_id = '99f1a014-0cd4-44c3-8d2f-cfa15dc5a1ed')
     or not exists (select 1 from public.usuarios_tenant ut join auth.users u on u.id = ut.user_id
                    where ut.user_id = 'c42d6b9a-b543-4b52-a621-b19d26d5041b' and u.email = 'demo@beehuman.invalid'
                      and ut.tenant_id = '00000000-0000-4000-8000-de0000000001') then
    raise exception 'DETENIDO: las cuentas de producción no son las 2 esperadas. Clasifícalas antes de migrar. No se aplicó nada.';
  end if;
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
  select md5(fn.s||pol.s||trg.s||col.s||con.s||idx.s||tbl.s||vw.s) into h
  from fn, pol, trg, col, con, idx, tbl, vw;
  if h <> '03e98353d5e19d32ad52fd84b464f608' then
    raise exception 'DETENIDO: el esquema de producción cambió desde el diagnóstico (huella %). No se aplicó nada.', h;
  end if;
end $$;
-- @@CANDADO_PROD_FIN ---------------------------------------------------

-- Conteos previos (se comparan al final) ------------------------------
create temp table _v2_conteos as
  select 'personal' t, count(*) n from public.personal
  union all select 'personal_registros_pago', count(*) from public.personal_registros_pago
  union all select 'movimientos', count(*) from public.movimientos
  union all select 'empresas', count(*) from public.empresas
  union all select 'empresas_registros_patronales', count(*) from public.empresas_registros_patronales
  union all select 'usuarios_tenant', count(*) from public.usuarios_tenant
  union all select 'tenants', count(*) from public.tenants
  union all select 'proyectos', count(*) from public.proyectos
  union all select 'periodicidades', count(*) from public.periodicidades
  union all select 'clasificaciones_personal', count(*) from public.clasificaciones_personal
  union all select 'areas', count(*) from public.areas
  union all select 'departamentos', count(*) from public.departamentos
  union all select 'puestos', count(*) from public.puestos
  union all select 'localidades', count(*) from public.localidades
  union all select 'centros_costo', count(*) from public.centros_costo;

-- =====================================================================
-- A. ROLES
-- =====================================================================
alter table public.usuarios_tenant
  add column rol text not null default 'consulta',
  add column personal_id uuid;
alter table public.usuarios_tenant
  add constraint usuarios_tenant_rol_check
    check (rol = any (array['administrador'::text, 'nomina'::text, 'consulta'::text, 'coordinador'::text])),
  add constraint usuarios_tenant_personal_fk
    foreign key (personal_id, tenant_id) references public.personal(id, tenant_id),
  add constraint usuarios_tenant_user_tenant_key unique (user_id, tenant_id);

CREATE OR REPLACE FUNCTION public.current_rol()
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$ select rol from public.usuarios_tenant where user_id = auth.uid(); $function$;
CREATE OR REPLACE FUNCTION public.current_personal_id()
 RETURNS uuid
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$ select personal_id from public.usuarios_tenant where user_id = auth.uid(); $function$;
CREATE OR REPLACE FUNCTION public.tiene_rol(VARIADIC p_roles text[])
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$ select coalesce(public.current_rol() = any(p_roles), false); $function$;

-- Autoría de cambios: la sella el servidor, el navegador no la envía.
alter table public.empresas add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.empresas_registros_patronales add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.personal add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.personal_registros_pago add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.movimientos add column usuario_id uuid;

-- sellar_autoria(): texto idéntico al de beehuman-pruebas, que contiene saltos de línea
-- Windows (CRLF). Se crea con E'' para conservarlos byte a byte; el
-- comportamiento es el mismo que con saltos Unix, pero la huella exige el texto exacto.
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.sellar_autoria()\n RETURNS trigger\n LANGUAGE plpgsql\n SET search_path TO ''''\nAS $function$\r\nbegin\r\n  if tg_op = ''INSERT'' then\r\n    new.creado_por := auth.uid();\r\n    new.actualizado_por := null;\r\n    new.actualizado_en := null;\r\n  else\r\n    new.creado_por := old.creado_por;\r\n    new.actualizado_por := auth.uid();\r\n    new.actualizado_en := now();\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;
-- sellar_movimiento(): texto idéntico al de beehuman-pruebas, que contiene saltos de línea
-- Windows (CRLF). Se crea con E'' para conservarlos byte a byte; el
-- comportamiento es el mismo que con saltos Unix, pero la huella exige el texto exacto.
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.sellar_movimiento()\n RETURNS trigger\n LANGUAGE plpgsql\n SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\r\nbegin\r\n  new.usuario_id := auth.uid();\r\n  new.usuario := coalesce((select u.email from auth.users u where u.id = auth.uid()), ''sistema'');\r\n  new.fecha := now();\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;

create trigger trg_sellar_autoria before insert or update on public.empresas for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.empresas_registros_patronales for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.personal for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.personal_registros_pago for each row execute function public.sellar_autoria();
create trigger trg_sellar_movimiento before insert on public.movimientos for each row execute function public.sellar_movimiento();

-- search_path fijo en dos funciones existentes (mismo comportamiento).
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.bloquear_cambio_tenant()\n RETURNS trigger\n LANGUAGE plpgsql\n SET search_path TO ''''\nAS $function$\nbegin\n  if new.tenant_id is distinct from old.tenant_id then\n    raise exception ''No está permitido reasignar tenant_id de un registro existente'';\n  end if;\n  return new;\nend;\n$function$';
end $v2fn$;
-- generar_empleado_id(): texto idéntico al de beehuman-pruebas, que contiene saltos de línea
-- Windows (CRLF). Se crea con E'' para conservarlos byte a byte; el
-- comportamiento es el mismo que con saltos Unix, pero la huella exige el texto exacto.
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.generar_empleado_id()\n RETURNS trigger\n LANGUAGE plpgsql\n SET search_path TO ''public''\nAS $function$\r\nbegin\r\n  if new.empleado_id is null then\r\n    new.empleado_id := ''BEH-'' || lpad(nextval(''personal_empleado_id_seq'')::text, 6, ''0'');\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;

-- =====================================================================
-- B. M1 · Número interno
-- =====================================================================
alter table public.personal add column numero_interno_trabajador text;

create unique index personal_numero_interno_rp_uq
  on public.personal (tenant_id, registro_patronal_id, upper(btrim(numero_interno_trabajador)))
  where registro_patronal_id is not null
    and btrim(numero_interno_trabajador) <> '';
comment on index public.personal_numero_interno_rp_uq is
  'V2.0 M1: número interno único por tenant + registro patronal (ignora mayúsculas y espacios externos).';

do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.coincidencias_numero_interno(p_numero text, p_empresa_id uuid, p_registro_patronal_id uuid, p_excluir_id uuid DEFAULT NULL::uuid)\n RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, estatus text, empresa text, registro_patronal text, relacion text)\n LANGUAGE sql\n STABLE\n SET search_path TO ''''\nAS $function$\n  select p.id, p.empleado_id, p.nombre_completo, p.estatus,\n         e.nombre, rp.registro_patronal,\n         case\n           when p_registro_patronal_id is not null and p.registro_patronal_id = p_registro_patronal_id then ''mismo_rp''\n           when p.registro_patronal_id is not null then ''otro_rp''\n           when p.empresa_id is not distinct from p_empresa_id then ''sin_rp_misma_empresa''\n           else ''sin_rp_otra_empresa''\n         end\n  from public.personal p\n  left join public.empresas e on e.id = p.empresa_id and e.tenant_id = p.tenant_id\n  left join public.empresas_registros_patronales rp on rp.id = p.registro_patronal_id and rp.tenant_id = p.tenant_id\n  where public.tiene_rol(''administrador'',''nomina'')\n    and p.tenant_id = public.current_tenant_id()\n    and nullif(btrim(p_numero), '''') is not null\n    and upper(btrim(p.numero_interno_trabajador)) = upper(btrim(p_numero))\n    and (p_excluir_id is null or p.id <> p_excluir_id)\n  order by (p_registro_patronal_id is not null and p.registro_patronal_id = p_registro_patronal_id) desc,\n           p.empleado_id\n  limit 50;\n$function$';
end $v2fn$;

-- =====================================================================
-- C. M2 · Ámbitos
-- =====================================================================
create table public.usuario_alcances (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null,
  user_id     uuid not null,
  empresa_id  uuid,
  proyecto_id uuid,
  nota        text,
  created_at  timestamptz not null default now(),
  constraint usuario_alcances_al_menos_una_dimension
    check (empresa_id is not null or proyecto_id is not null),
  constraint usuario_alcances_usuario_fkey
    foreign key (user_id, tenant_id) references public.usuarios_tenant(user_id, tenant_id) on delete cascade,
  constraint usuario_alcances_empresa_fkey
    foreign key (empresa_id, tenant_id) references public.empresas(id, tenant_id),
  constraint usuario_alcances_proyecto_fkey
    foreign key (proyecto_id, tenant_id) references public.proyectos(id, tenant_id),
  constraint usuario_alcances_unica unique nulls not distinct (user_id, empresa_id, proyecto_id)
);
comment on table public.usuario_alcances is
  'V2.0 M2: ámbito del rol Consulta. Cada fila es una concesión (empresa, proyecto o ambos = intersección); las filas se suman. Sin filas = sin acceso. Se administra solo desde Supabase.';
alter table public.usuario_alcances enable row level security;
-- Sin políticas: la app no puede leerla ni escribirla.

do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.en_alcance_persona(p_personal_id uuid)\n RETURNS boolean\n LANGUAGE sql\n STABLE SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\n  select case public.current_rol()\n    when ''administrador'' then true\n    when ''nomina''        then true\n    when ''consulta'' then exists (\n      select 1\n      from public.personal p\n      join public.usuario_alcances a\n        on a.tenant_id = p.tenant_id\n       and a.user_id   = auth.uid()\n       and (a.empresa_id  is null or a.empresa_id  = p.empresa_id)\n       and (a.proyecto_id is null or a.proyecto_id = p.proyecto_id)\n      where p.id = p_personal_id\n        and p.tenant_id = public.current_tenant_id())\n    when ''coordinador'' then exists (\n      select 1\n      from public.personal p\n      where p.id = p_personal_id\n        and p.tenant_id = public.current_tenant_id()\n        and public.current_personal_id() is not null\n        and p.coordinador_id = public.current_personal_id())\n    else false\n  end;\n$function$';
end $v2fn$;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.personal_organizacional()\n RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, empresa_id uuid, empresa_nombre text, registro_patronal_id uuid, registro_patronal text, proyecto_id uuid, proyecto_nombre text, puesto_id uuid, puesto_nombre text, area_id uuid, area_nombre text, departamento_id uuid, departamento_nombre text, localidad_id uuid, localidad_nombre text, centro_costo_id uuid, centro_costo_nombre text, coordinador_id uuid, coordinador_nombre text, coordinador_externo text, coordinador text, coordinador_asignado boolean, estatus text, fecha_antiguedad date, fecha_alta_imss date, fecha_baja date, tipo_contrato text, fecha_asignacion date, created_at timestamp with time zone)\n LANGUAGE sql\n STABLE SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\n  select p.id, p.empleado_id, p.nombre_completo,\n         p.empresa_id, e.nombre, p.registro_patronal_id, rp.registro_patronal,\n         p.proyecto_id, pr.nombre, p.puesto_id, pu.nombre, p.area_id, ar.nombre,\n         p.departamento_id, de.nombre, p.localidad_id, lo.nombre,\n         p.centro_costo_id, cc.nombre,\n         case when public.current_rol() = ''consulta''\n                    and p.coordinador_id is not null\n                    and not public.en_alcance_persona(p.coordinador_id)\n              then null else p.coordinador_id end,\n         case when public.current_rol() = ''consulta''\n                    and p.coordinador_id is not null\n                    and not public.en_alcance_persona(p.coordinador_id)\n              then null else co.nombre_completo end,\n         case when public.current_rol() = ''consulta''\n                    and p.coordinador_id is not null\n                    and not public.en_alcance_persona(p.coordinador_id)\n              then null else p.coordinador_externo end,\n         case when public.current_rol() = ''consulta''\n                    and p.coordinador_id is not null\n                    and not public.en_alcance_persona(p.coordinador_id)\n              then ''Coordinador asignado''\n              when p.coordinador_id is not null then coalesce(co.nombre_completo, ''—'')\n              when p.coordinador_externo is not null then p.coordinador_externo || '' (externo)''\n              else p.coordinador end,\n         (p.coordinador_id is not null),\n         p.estatus, p.fecha_antiguedad::date, p.fecha_alta_imss::date,\n         p.fecha_baja::date, p.tipo_contrato, p.fecha_asignacion::date, p.created_at\n  from public.personal p\n  left join public.empresas e on e.id = p.empresa_id and e.tenant_id = p.tenant_id\n  left join public.empresas_registros_patronales rp on rp.id = p.registro_patronal_id and rp.tenant_id = p.tenant_id\n  left join public.proyectos pr on pr.id = p.proyecto_id and pr.tenant_id = p.tenant_id\n  left join public.puestos pu on pu.id = p.puesto_id and pu.tenant_id = p.tenant_id\n  left join public.areas ar on ar.id = p.area_id and ar.tenant_id = p.tenant_id\n  left join public.departamentos de on de.id = p.departamento_id and de.tenant_id = p.tenant_id\n  left join public.localidades lo on lo.id = p.localidad_id and lo.tenant_id = p.tenant_id\n  left join public.centros_costo cc on cc.id = p.centro_costo_id and cc.tenant_id = p.tenant_id\n  left join public.personal co on co.id = p.coordinador_id and co.tenant_id = p.tenant_id\n  where p.tenant_id = public.current_tenant_id()\n    and public.tiene_rol(''administrador'',''nomina'',''consulta'')\n    and public.en_alcance_persona(p.id)\n  order by p.created_at desc, p.id;\n$function$';
end $v2fn$;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.equipo_coordinador()\n RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, puesto text, area text, departamento text, proyecto text, localidad text, estatus text, fecha_asignacion date, telefono_celular text)\n LANGUAGE sql\n STABLE SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\n  select p.id, p.empleado_id, p.nombre_completo,\n         pu.nombre, ar.nombre, de.nombre, pr.nombre, lo.nombre,\n         p.estatus, p.fecha_asignacion::date, p.telefono_celular\n  from public.personal p\n  left join public.puestos pu on pu.id = p.puesto_id and pu.tenant_id = p.tenant_id\n  left join public.areas ar on ar.id = p.area_id and ar.tenant_id = p.tenant_id\n  left join public.departamentos de on de.id = p.departamento_id and de.tenant_id = p.tenant_id\n  left join public.proyectos pr on pr.id = p.proyecto_id and pr.tenant_id = p.tenant_id\n  left join public.localidades lo on lo.id = p.localidad_id and lo.tenant_id = p.tenant_id\n  where p.tenant_id = public.current_tenant_id()\n    and public.tiene_rol(''coordinador'')\n    and public.current_personal_id() is not null\n    and p.coordinador_id = public.current_personal_id()\n  order by p.nombre_completo, p.id;\n$function$';
end $v2fn$;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.resumen_agregado()\n RETURNS jsonb\n LANGUAGE sql\n STABLE SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\nwith\ncfg as (select 3 as k),\npermitido as (\n  select public.current_tenant_id() as tenant\n  where public.tiene_rol(''administrador'',''nomina'',''consulta'')\n),\nve_importes as (select public.tiene_rol(''administrador'',''nomina'') as si),\npers as (\n  select p.* from public.personal p, permitido\n  where p.tenant_id = permitido.tenant and public.en_alcance_persona(p.id)\n),\nvig as (select * from pers where coalesce(estatus,'''') <> ''Baja''),\nesq as (\n  select rp.personal_id, rp.sueldo, rp.modalidad_sueldo as modalidad,\n         rp.periodicidad_id, pe.nombre as periodicidad,\n         coalesce(rp.dias_periodo, pe.dias_default)::numeric as dias,\n         rp.clasificacion_id, coalesce(c.nombre, ''Sin clasificación'') as clasificacion,\n         v.proyecto_id,\n         case when v.coordinador_id is not null then coalesce(co.nombre_completo, ''—'')\n              when v.coordinador_externo is not null then v.coordinador_externo || '' (externo)''\n              when coalesce(v.coordinador,'''') <> '''' then v.coordinador\n              else ''Sin coordinador'' end as coordinador\n  from public.personal_registros_pago rp\n  join vig v on v.id = rp.personal_id and v.tenant_id = rp.tenant_id\n  join public.periodicidades pe on pe.id = rp.periodicidad_id and pe.tenant_id = rp.tenant_id\n  left join public.clasificaciones_personal c on c.id = rp.clasificacion_id and c.tenant_id = rp.tenant_id\n  left join public.personal co on co.id = v.coordinador_id and co.tenant_id = v.tenant_id\n  where rp.activo and (select si from ve_importes)\n),\nvig_dim as (\n  select v.id, v.proyecto_id,\n         case when public.current_rol() = ''consulta''\n                    and v.coordinador_id is not null\n                    and not public.en_alcance_persona(v.coordinador_id)\n              then ''Coordinador asignado''\n              when v.coordinador_id is not null then coalesce(co.nombre_completo, ''—'')\n              when v.coordinador_externo is not null then v.coordinador_externo || '' (externo)''\n              when coalesce(v.coordinador,'''') <> '''' then v.coordinador\n              else ''Sin coordinador'' end as coordinador\n  from vig v\n  left join public.personal co on co.id = v.coordinador_id and co.tenant_id = v.tenant_id\n),\nceldas as (\n  select ''total''::text as dim, ''''::text as clave, ''''::text as nombre,\n         modalidad, periodicidad_id, periodicidad, dias,\n         count(*) as esquemas, count(distinct personal_id) as personas,\n         sum(round(sueldo * 100))::bigint as centavos\n  from esq group by modalidad, periodicidad_id, periodicidad, dias\n  union all\n  select ''clasificacion'', coalesce(clasificacion_id::text,''''), clasificacion,\n         modalidad, periodicidad_id, periodicidad, dias,\n         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint\n  from esq group by clasificacion_id, clasificacion, modalidad, periodicidad_id, periodicidad, dias\n  union all\n  select ''proyecto'', coalesce(e.proyecto_id::text,''''), coalesce(pr.nombre, ''Sin proyecto''),\n         modalidad, periodicidad_id, periodicidad, dias,\n         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint\n  from esq e left join public.proyectos pr on pr.id = e.proyecto_id and pr.tenant_id = (select tenant from permitido)\n  group by e.proyecto_id, pr.nombre, modalidad, periodicidad_id, periodicidad, dias\n  union all\n  select ''coordinador'', coordinador, coordinador,\n         modalidad, periodicidad_id, periodicidad, dias,\n         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint\n  from esq group by coordinador, modalidad, periodicidad_id, periodicidad, dias\n),\nrankeadas as (\n  select c.*, row_number() over w as rn,\n         sum(personas) over w as acumuladas,\n         count(*) filter (where personas < (select k from cfg)) over (partition by dim, modalidad, periodicidad_id, dias) as primarias\n  from celdas c\n  window w as (partition by dim, modalidad, periodicidad_id, dias order by personas, clave\n               rows between unbounded preceding and current row)\n),\ncorte as (\n  select dim, modalidad, periodicidad_id, dias,\n         coalesce(min(rn) filter (where rn >= primarias and rn >= 2 and acumuladas >= (select k from cfg)), max(rn)) as n_ocultas,\n         max(primarias) as primarias\n  from rankeadas where dim <> ''total''\n  group by dim, modalidad, periodicidad_id, dias\n),\nmarcadas as (\n  select r.*,\n         case when r.dim = ''total'' then r.personas < (select k from cfg)\n              when co.primarias = 0 then false else r.rn <= co.n_ocultas end as oculto\n  from rankeadas r left join corte co using (dim, modalidad, periodicidad_id, dias)\n),\ngrupo_json as (\n  select dim, clave, nombre,\n         jsonb_agg(jsonb_build_object(''modalidad'', modalidad, ''periodicidad'', periodicidad, ''dias'', dias,\n           ''esquemas'', esquemas, ''personas'', personas,\n           ''importe'', case when oculto then null else centavos / 100.0 end, ''oculto'', oculto)\n           order by modalidad, periodicidad, dias) as grupos,\n         sum(esquemas) as esquemas\n  from marcadas group by dim, clave, nombre\n),\npersonas_dim as (\n  select ''proyecto''::text as dim, coalesce(vd.proyecto_id::text,'''') as clave,\n         coalesce(pr.nombre, ''Sin proyecto'') as nombre, count(*) as personas\n  from vig_dim vd left join public.proyectos pr on pr.id = vd.proyecto_id and pr.tenant_id = (select tenant from permitido)\n  group by vd.proyecto_id, pr.nombre\n  union all\n  select ''coordinador'', coordinador, coordinador, count(*) from vig_dim group by coordinador\n  union all\n  select ''clasificacion'', coalesce(clasificacion_id::text,''''), clasificacion, count(distinct personal_id)\n  from esq group by clasificacion_id, clasificacion\n),\ndesglose as (\n  select pd.dim, jsonb_agg(jsonb_build_object(''nombre'', pd.nombre, ''personas'', pd.personas,\n         ''esquemas'', coalesce(g.esquemas, 0), ''grupos'', coalesce(g.grupos, ''[]''::jsonb))\n         order by pd.nombre) as filas\n  from personas_dim pd left join grupo_json g on g.dim = pd.dim and g.clave = pd.clave\n  group by pd.dim\n)\nselect case when not exists (select 1 from permitido) then null else jsonb_build_object(\n  ''k'', (select k from cfg), ''importes'', (select si from ve_importes),\n  ''personal'', jsonb_build_object(''vigentes'', (select count(*) from vig),\n     ''baja'', (select count(*) from pers) - (select count(*) from vig),\n     ''empresas'', (select count(distinct empresa_id) from vig where empresa_id is not null),\n     ''proyectos'', (select count(distinct proyecto_id) from vig where proyecto_id is not null)),\n  ''compensacion'', case when (select si from ve_importes) then jsonb_build_object(\n     ''esquemas'', (select count(*) from esq), ''bruto'', (select count(*) from esq where modalidad = ''bruto''),\n     ''neto'', (select count(*) from esq where modalidad = ''neto''),\n     ''personas_con_esquema'', (select count(distinct personal_id) from esq),\n     ''sin_esquema'', (select count(*) from vig) - (select count(distinct personal_id) from esq)) end,\n  ''grupos'', case when (select si from ve_importes) then coalesce((select grupos from grupo_json where dim = ''total''), ''[]''::jsonb) end,\n  ''desglose'', coalesce((select jsonb_object_agg(dim, filas) from desglose), ''{}''::jsonb)\n) end;\n$function$';
end $v2fn$;

-- =====================================================================
-- A (cont.) · Políticas por operación y rol. No hay políticas DELETE:
-- desde la app no se borra nada (se desactiva o se da de baja).
-- =====================================================================
-- Se retiran las políticas «todo el tenant» de V1.
drop policy tenant_acceso_areas on public.areas;
drop policy tenant_acceso_centros_costo on public.centros_costo;
drop policy tenant_acceso_clasificaciones_personal on public.clasificaciones_personal;
drop policy tenant_acceso_combo_conceptos on public.combo_conceptos;
drop policy tenant_acceso_combos on public.combos;
drop policy tenant_acceso_conceptos on public.conceptos_percepcion;
drop policy tenant_acceso_departamentos on public.departamentos;
drop policy tenant_acceso_empresas on public.empresas;
drop policy tenant_acceso_empresas_registros_patronales on public.empresas_registros_patronales;
drop policy tenant_acceso_localidades on public.localidades;
drop policy tenant_acceso_movimientos on public.movimientos;
drop policy tenant_acceso_periodicidades on public.periodicidades;
drop policy tenant_acceso_personal on public.personal;
drop policy tenant_acceso_personal_percepciones on public.personal_percepciones;
drop policy tenant_insert_personal_registros_pago on public.personal_registros_pago;
drop policy tenant_select_personal_registros_pago on public.personal_registros_pago;
drop policy tenant_update_personal_registros_pago on public.personal_registros_pago;
drop policy tenant_acceso_proyectos on public.proyectos;
drop policy tenant_acceso_puestos on public.puestos;

-- Políticas V2.0 (texto exacto de pruebas).
create policy areas_insert on public.areas for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy areas_select on public.areas for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy areas_update on public.areas for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy centros_costo_insert on public.centros_costo for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy centros_costo_select on public.centros_costo for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy centros_costo_update on public.centros_costo for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy clasificaciones_personal_insert on public.clasificaciones_personal for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy clasificaciones_personal_select on public.clasificaciones_personal for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy clasificaciones_personal_update on public.clasificaciones_personal for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combo_conceptos_insert on public.combo_conceptos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combo_conceptos_select on public.combo_conceptos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combo_conceptos_update on public.combo_conceptos for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combos_insert on public.combos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combos_select on public.combos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy combos_update on public.combos for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy conceptos_percepcion_insert on public.conceptos_percepcion for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy conceptos_percepcion_select on public.conceptos_percepcion for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy conceptos_percepcion_update on public.conceptos_percepcion for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy departamentos_insert on public.departamentos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy departamentos_select on public.departamentos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy departamentos_update on public.departamentos for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy empresas_insert on public.empresas for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy empresas_select on public.empresas for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy empresas_update on public.empresas for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy empresas_registros_patronales_insert on public.empresas_registros_patronales for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy empresas_registros_patronales_select on public.empresas_registros_patronales for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy empresas_registros_patronales_update on public.empresas_registros_patronales for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy localidades_insert on public.localidades for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy localidades_select on public.localidades for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy localidades_update on public.localidades for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy movimientos_insert on public.movimientos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy movimientos_select on public.movimientos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy periodicidades_insert on public.periodicidades for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy periodicidades_select on public.periodicidades for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy periodicidades_update on public.periodicidades for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy personal_insert on public.personal for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy personal_select on public.personal for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text]) AND en_alcance_persona(id)));
create policy personal_update on public.personal for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text]) AND en_alcance_persona(id)))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy personal_percepciones_insert on public.personal_percepciones for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy personal_percepciones_select on public.personal_percepciones for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy personal_percepciones_update on public.personal_percepciones for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy registros_pago_insert on public.personal_registros_pago for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy registros_pago_select on public.personal_registros_pago for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text]) AND en_alcance_persona(personal_id)));
create policy registros_pago_update on public.personal_registros_pago for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text]) AND en_alcance_persona(personal_id)))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy proyectos_insert on public.proyectos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy proyectos_select on public.proyectos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy proyectos_update on public.proyectos for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy puestos_insert on public.puestos for insert to authenticated
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));
create policy puestos_select on public.puestos for select to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text, 'nomina'::text])));
create policy puestos_update on public.puestos for update to authenticated
  using (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])))
  with check (((tenant_id = current_tenant_id()) AND tiene_rol(VARIADIC ARRAY['administrador'::text])));

-- =====================================================================
-- A (cont.) · Permisos
-- =====================================================================
-- anon (sin sesión) no toca ninguna tabla; authenticated no borra ni trunca.
revoke all on all tables in schema public from anon;
revoke delete, truncate, references, trigger on
  public.areas, public.centros_costo, public.clasificaciones_personal, public.combo_conceptos,
  public.combos, public.conceptos_percepcion, public.departamentos, public.empresas,
  public.empresas_registros_patronales, public.localidades, public.movimientos,
  public.periodicidades, public.personal, public.personal_percepciones, public.proyectos,
  public.puestos, public.tenants, public.usuarios_tenant
  from authenticated;
revoke all on table public.usuario_alcances from public, anon, authenticated;

-- Funciones: nadie las ejecuta salvo lo indispensable para la app.
revoke execute on all functions in schema public from public, anon, authenticated;
grant execute on function
  public.current_tenant_id(), public.tiene_rol(text[]),
  public.es_cp_valido(text), public.es_curp_valida(text), public.es_nss_valido(text),
  public.es_rfc_persona_valido(text), public.fecha_aammdd_valida(text, text),
  public.coincidencias_numero_interno(text, uuid, uuid, uuid), public.en_alcance_persona(uuid),
  public.personal_organizacional(), public.equipo_coordinador(), public.resumen_agregado()
  to authenticated;

-- =====================================================================
-- D. Asignación de roles (solo producción)
-- =====================================================================
-- @@ASIGNACIONES_PROD_INICIO
update public.usuarios_tenant set rol = 'administrador'
 where user_id = '28b037db-6fde-4175-8408-a644c6aeee50'
   and tenant_id = '99f1a014-0cd4-44c3-8d2f-cfa15dc5a1ed';
update public.usuarios_tenant set rol = 'administrador'
 where user_id = 'c42d6b9a-b543-4b52-a621-b19d26d5041b'
   and tenant_id = '00000000-0000-4000-8000-de0000000001';
do $$
begin
  if (select count(*) from public.usuarios_tenant) <> 2
     or (select count(*) from public.usuarios_tenant where rol = 'administrador') <> 2
     or exists (select 1 from public.usuarios_tenant where personal_id is not null) then
    raise exception 'Verificación: asignación de roles distinta a la esperada.';
  end if;
end $$;
-- @@ASIGNACIONES_PROD_FIN

-- =====================================================================
-- Verificación final (si algo falla, no se confirma nada)
-- =====================================================================
do $$
declare h text; r record;
begin
  -- Datos intactos
  for r in
    select c.t, c.n antes, d.n despues from _v2_conteos c join (
      select 'personal' t, count(*) n from public.personal
      union all select 'personal_registros_pago', count(*) from public.personal_registros_pago
      union all select 'movimientos', count(*) from public.movimientos
      union all select 'empresas', count(*) from public.empresas
      union all select 'empresas_registros_patronales', count(*) from public.empresas_registros_patronales
      union all select 'usuarios_tenant', count(*) from public.usuarios_tenant
      union all select 'tenants', count(*) from public.tenants
      union all select 'proyectos', count(*) from public.proyectos
      union all select 'periodicidades', count(*) from public.periodicidades
      union all select 'clasificaciones_personal', count(*) from public.clasificaciones_personal
      union all select 'areas', count(*) from public.areas
      union all select 'departamentos', count(*) from public.departamentos
      union all select 'puestos', count(*) from public.puestos
      union all select 'localidades', count(*) from public.localidades
      union all select 'centros_costo', count(*) from public.centros_costo) d using (t)
  loop
    if r.antes <> r.despues then
      raise exception 'Verificación: cambió el conteo de % (% → %)', r.t, r.antes, r.despues;
    end if;
  end loop;
  -- Seguridad mínima
  if has_table_privilege('anon', 'public.personal', 'select') then
    raise exception 'Verificación: anon puede leer personal';
  end if;
  if has_table_privilege('authenticated', 'public.personal', 'delete') then
    raise exception 'Verificación: authenticated puede borrar personal';
  end if;
  if has_table_privilege('authenticated', 'public.usuario_alcances', 'select') then
    raise exception 'Verificación: la app puede leer usuario_alcances';
  end if;
  if exists (select 1 from pg_policies where schemaname='public' and tablename='usuario_alcances') then
    raise exception 'Verificación: usuario_alcances no debe tener políticas';
  end if;
  if (select prosecdef from pg_proc where proname = 'coincidencias_numero_interno') then
    raise exception 'Verificación: coincidencias_numero_interno quedó como SECURITY DEFINER';
  end if;
  -- Esquema idéntico al aprobado en pruebas
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
  select md5(fn.s||pol.s||trg.s||col.s||con.s||idx.s||tbl.s||vw.s) into h
  from fn, pol, trg, col, con, idx, tbl, vw;
  if h <> 'ebcd0aad4284c492ae7b44b379d6e208' then
    raise exception 'Verificación: el esquema resultante no es idéntico al de pruebas (huella %).', h;
  end if;
  raise notice 'V2.0 aplicada y verificada: esquema idéntico a pruebas, datos intactos.';
end $$;

drop table _v2_conteos;

commit;
