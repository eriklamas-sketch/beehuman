-- =====================================================================
-- BeeHuman V2.0 · PRUEBA DE COMPATIBILIDAD (v5, 19-oct-2026)
-- DESTINO: EXCLUSIVAMENTE beehuman-pruebas (sflvpgkmtaxzogpgetxn).
-- Una sola transacción. Termina SIEMPRE en error, así que nunca se confirma:
--   · «PRUEBA_COMPLETA_OK | …»  → todas las comprobaciones pasaron.
--   · «PRUEBA_FALLIDA: …»       → una comprobación falló (dice cuál).
--   · cualquier otro error      → falló la reversión o la migración (dice cuál).
-- Corrección frente a v1: v1 medía el aislamiento con las cuentas en rol
-- «consulta» (la migración recrea usuarios_tenant.rol con ese valor por
-- defecto) y llamaba a current_rol(), que el rol authenticated no puede
-- ejecutar. v2 restaura los roles explícitamente, exige rol efectivo
-- «administrador» y aborta si no lo consigue.
-- Corrección v3: el INSERT con tenant ajeno acepta solo dos resultados
-- legítimos (reasignado al propio o rechazado por RLS 42501); «mover a otro
-- tenant» acepta solo el error del trigger o 42501; cualquier otro error
-- aborta la prueba (nunca cuenta como éxito); al final, como postgres, se
-- verifica que nada quedó en el tenant ajeno ni cambiaron los conteos.
-- Corrección v4: antes de simular sesiones se exige que authenticated tenga
-- exactamente los privilegios que la prueba necesita (y que NO tenga DELETE).
-- Así un 42501 en INSERT/UPDATE solo puede deberse a RLS, y en DELETE solo a
-- la falta de privilegio esperada. Si falta o sobra un privilegio, se detiene
-- indicando cuál.
-- v5 (19-oct): sin cambios en la lógica de la prueba. Solo se regenera con
-- la migración V2.0 corregida (texto exacto, con CRLF, de sellar_autoria,
-- sellar_movimiento y generar_empleado_id); con el texto anterior la
-- verificación de huella de la migración habría detenido la v4.
-- =====================================================================
begin;
-- 0. Precondiciones (antes de tocar nada) -------------------------------
do $$
begin
  if not exists (select 1 from public.tenants where nombre like 'TENANT SINTETICO 7D6B%')
     or exists (select 1 from public.tenants where nombre = 'BeeHuman — Demo') then
    raise exception 'PRUEBA_FALLIDA: no se reconoce beehuman-pruebas. No se ejecutó nada.';
  end if;
end $$;
create temp table _ut_snapshot as
  select user_id, tenant_id, rol, personal_id from public.usuarios_tenant;
do $$
declare ta uuid; tb uuid; ra text; rb text;
begin
  select tenant_id, rol into ta, ra from _ut_snapshot where user_id = '22222222-0000-4000-8000-000000000001';
  select tenant_id, rol into tb, rb from _ut_snapshot where user_id = '00000000-0000-4000-8000-0000007d6c02';
  if ta is null or tb is null then
    raise exception 'PRUEBA_FALLIDA: falta alguna de las cuentas de prueba A/B en usuarios_tenant.';
  end if;
  if ta = tb then
    raise exception 'PRUEBA_FALLIDA: las cuentas A y B pertenecen al mismo tenant (%).', ta;
  end if;
  if ra <> 'administrador' or rb <> 'administrador' then
    raise exception 'PRUEBA_FALLIDA: A o B no son administrador antes de empezar (A=%, B=%).', ra, rb;
  end if;
end $$;
-- 1. Reversión a V1 y migración V2.0 (texto idéntico a los archivos de supabase/) --
create temp table _rv_conteos as
  select 'personal' t, count(*) n from public.personal
  union all select 'personal_registros_pago', count(*) from public.personal_registros_pago
  union all select 'movimientos', count(*) from public.movimientos
  union all select 'empresas', count(*) from public.empresas
  union all select 'usuarios_tenant', count(*) from public.usuarios_tenant;
drop policy areas_insert on public.areas;
drop policy areas_select on public.areas;
drop policy areas_update on public.areas;
drop policy centros_costo_insert on public.centros_costo;
drop policy centros_costo_select on public.centros_costo;
drop policy centros_costo_update on public.centros_costo;
drop policy clasificaciones_personal_insert on public.clasificaciones_personal;
drop policy clasificaciones_personal_select on public.clasificaciones_personal;
drop policy clasificaciones_personal_update on public.clasificaciones_personal;
drop policy combo_conceptos_insert on public.combo_conceptos;
drop policy combo_conceptos_select on public.combo_conceptos;
drop policy combo_conceptos_update on public.combo_conceptos;
drop policy combos_insert on public.combos;
drop policy combos_select on public.combos;
drop policy combos_update on public.combos;
drop policy conceptos_percepcion_insert on public.conceptos_percepcion;
drop policy conceptos_percepcion_select on public.conceptos_percepcion;
drop policy conceptos_percepcion_update on public.conceptos_percepcion;
drop policy departamentos_insert on public.departamentos;
drop policy departamentos_select on public.departamentos;
drop policy departamentos_update on public.departamentos;
drop policy empresas_insert on public.empresas;
drop policy empresas_select on public.empresas;
drop policy empresas_update on public.empresas;
drop policy empresas_registros_patronales_insert on public.empresas_registros_patronales;
drop policy empresas_registros_patronales_select on public.empresas_registros_patronales;
drop policy empresas_registros_patronales_update on public.empresas_registros_patronales;
drop policy localidades_insert on public.localidades;
drop policy localidades_select on public.localidades;
drop policy localidades_update on public.localidades;
drop policy periodicidades_insert on public.periodicidades;
drop policy periodicidades_select on public.periodicidades;
drop policy periodicidades_update on public.periodicidades;
drop policy personal_insert on public.personal;
drop policy personal_select on public.personal;
drop policy personal_update on public.personal;
drop policy personal_percepciones_insert on public.personal_percepciones;
drop policy personal_percepciones_select on public.personal_percepciones;
drop policy personal_percepciones_update on public.personal_percepciones;
drop policy proyectos_insert on public.proyectos;
drop policy proyectos_select on public.proyectos;
drop policy proyectos_update on public.proyectos;
drop policy puestos_insert on public.puestos;
drop policy puestos_select on public.puestos;
drop policy puestos_update on public.puestos;
drop policy movimientos_insert on public.movimientos;
drop policy movimientos_select on public.movimientos;
drop policy registros_pago_insert on public.personal_registros_pago;
drop policy registros_pago_select on public.personal_registros_pago;
drop policy registros_pago_update on public.personal_registros_pago;
create policy tenant_acceso_areas on public.areas for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_centros_costo on public.centros_costo for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_clasificaciones_personal on public.clasificaciones_personal for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_combo_conceptos on public.combo_conceptos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_combos on public.combos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_conceptos on public.conceptos_percepcion for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_departamentos on public.departamentos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_empresas on public.empresas for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_empresas_registros_patronales on public.empresas_registros_patronales for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_localidades on public.localidades for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_movimientos on public.movimientos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_periodicidades on public.periodicidades for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_personal on public.personal for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_personal_percepciones on public.personal_percepciones for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_proyectos on public.proyectos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_acceso_puestos on public.puestos for all to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
create policy tenant_insert_personal_registros_pago on public.personal_registros_pago for insert to public
  with check ((tenant_id = current_tenant_id()));
create policy tenant_select_personal_registros_pago on public.personal_registros_pago for select to public
  using ((tenant_id = current_tenant_id()));
create policy tenant_update_personal_registros_pago on public.personal_registros_pago for update to public
  using ((tenant_id = current_tenant_id()))
  with check ((tenant_id = current_tenant_id()));
drop trigger trg_sellar_autoria on public.empresas;
drop trigger trg_sellar_autoria on public.empresas_registros_patronales;
drop trigger trg_sellar_autoria on public.personal;
drop trigger trg_sellar_autoria on public.personal_registros_pago;
drop trigger trg_sellar_movimiento on public.movimientos;
drop function public.sellar_autoria();
drop function public.sellar_movimiento();
alter table public.empresas drop column creado_por, drop column actualizado_por, drop column actualizado_en;
alter table public.empresas_registros_patronales drop column creado_por, drop column actualizado_por, drop column actualizado_en;
alter table public.personal drop column creado_por, drop column actualizado_por, drop column actualizado_en;
alter table public.personal_registros_pago drop column creado_por, drop column actualizado_por, drop column actualizado_en;
alter table public.movimientos drop column usuario_id;
drop function public.resumen_agregado();
drop function public.equipo_coordinador();
drop function public.personal_organizacional();
drop function public.en_alcance_persona(uuid);
drop function public.coincidencias_numero_interno(text, uuid, uuid, uuid);
drop table public.usuario_alcances;
drop index public.personal_numero_interno_rp_uq;
alter table public.personal drop column numero_interno_trabajador;
drop function public.tiene_rol(text[]);
drop function public.current_rol();
drop function public.current_personal_id();
alter table public.usuarios_tenant
  drop constraint usuarios_tenant_user_tenant_key,
  drop constraint usuarios_tenant_personal_fk,
  drop constraint usuarios_tenant_rol_check,
  drop column personal_id,
  drop column rol;
CREATE OR REPLACE FUNCTION public.bloquear_cambio_tenant()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
  if new.tenant_id is distinct from old.tenant_id then
    raise exception 'No está permitido reasignar tenant_id de un registro existente';
  end if;
  return new;
end;
$function$;
do $rv$ begin
  execute E'CREATE OR REPLACE FUNCTION public.generar_empleado_id()\n RETURNS trigger\n LANGUAGE plpgsql\nAS $function$\r\nbegin\r\n  if new.empleado_id is null then\r\n    new.empleado_id := ''BEH-'' || lpad(nextval(''personal_empleado_id_seq'')::text, 6, ''0'');\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $rv$;
revoke all on public.areas, public.centros_costo, public.clasificaciones_personal, public.combo_conceptos,
  public.combos, public.conceptos_percepcion, public.departamentos, public.empresas,
  public.empresas_registros_patronales, public.localidades, public.movimientos,
  public.periodicidades, public.personal, public.personal_percepciones, public.proyectos,
  public.puestos, public.tenants, public.usuarios_tenant from authenticated, service_role;
grant all on public.areas, public.centros_costo, public.clasificaciones_personal, public.combo_conceptos,
  public.combos, public.conceptos_percepcion, public.departamentos, public.empresas,
  public.empresas_registros_patronales, public.localidades, public.movimientos,
  public.periodicidades, public.personal, public.personal_percepciones, public.proyectos,
  public.puestos, public.tenants, public.usuarios_tenant to anon, authenticated, service_role;
revoke all on all functions in schema public from postgres, service_role, authenticated;
grant execute on all functions in schema public to public, postgres, anon, authenticated, service_role;
do $$
declare h text; r record;
begin
  for r in
    select c.t, c.n antes, d.n despues from _rv_conteos c join (
      select 'personal' t, count(*) n from public.personal
      union all select 'personal_registros_pago', count(*) from public.personal_registros_pago
      union all select 'movimientos', count(*) from public.movimientos
      union all select 'empresas', count(*) from public.empresas
      union all select 'usuarios_tenant', count(*) from public.usuarios_tenant) d using (t)
  loop
    if r.antes <> r.despues then
      raise exception 'Verificación: cambió el conteo de % (% → %)', r.t, r.antes, r.despues;
    end if;
  end loop;
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
    raise exception 'Verificación: el esquema revertido no es idéntico al de V1 (huella %).', h;
  end if;
  raise notice 'Reversión completa: esquema idéntico a V1 del 17-oct-2026.';
end $$;
drop table _rv_conteos;
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
alter table public.empresas add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.empresas_registros_patronales add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.personal add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.personal_registros_pago add column creado_por uuid, add column actualizado_por uuid, add column actualizado_en timestamptz;
alter table public.movimientos add column usuario_id uuid;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.sellar_autoria()\n RETURNS trigger\n LANGUAGE plpgsql\n SET search_path TO ''''\nAS $function$\r\nbegin\r\n  if tg_op = ''INSERT'' then\r\n    new.creado_por := auth.uid();\r\n    new.actualizado_por := null;\r\n    new.actualizado_en := null;\r\n  else\r\n    new.creado_por := old.creado_por;\r\n    new.actualizado_por := auth.uid();\r\n    new.actualizado_en := now();\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.sellar_movimiento()\n RETURNS trigger\n LANGUAGE plpgsql\n SECURITY DEFINER\n SET search_path TO ''''\nAS $function$\r\nbegin\r\n  new.usuario_id := auth.uid();\r\n  new.usuario := coalesce((select u.email from auth.users u where u.id = auth.uid()), ''sistema'');\r\n  new.fecha := now();\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;
create trigger trg_sellar_autoria before insert or update on public.empresas for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.empresas_registros_patronales for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.personal for each row execute function public.sellar_autoria();
create trigger trg_sellar_autoria before insert or update on public.personal_registros_pago for each row execute function public.sellar_autoria();
create trigger trg_sellar_movimiento before insert on public.movimientos for each row execute function public.sellar_movimiento();
CREATE OR REPLACE FUNCTION public.bloquear_cambio_tenant()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  if new.tenant_id is distinct from old.tenant_id then
    raise exception 'No está permitido reasignar tenant_id de un registro existente';
  end if;
  return new;
end;
$function$;
do $v2fn$ begin
  execute E'CREATE OR REPLACE FUNCTION public.generar_empleado_id()\n RETURNS trigger\n LANGUAGE plpgsql\n SET search_path TO ''public''\nAS $function$\r\nbegin\r\n  if new.empleado_id is null then\r\n    new.empleado_id := ''BEH-'' || lpad(nextval(''personal_empleado_id_seq'')::text, 6, ''0'');\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $v2fn$;
alter table public.personal add column numero_interno_trabajador text;
create unique index personal_numero_interno_rp_uq
  on public.personal (tenant_id, registro_patronal_id, upper(btrim(numero_interno_trabajador)))
  where registro_patronal_id is not null
    and btrim(numero_interno_trabajador) <> '';
comment on index public.personal_numero_interno_rp_uq is
  'V2.0 M1: número interno único por tenant + registro patronal (ignora mayúsculas y espacios externos).';
CREATE OR REPLACE FUNCTION public.coincidencias_numero_interno(p_numero text, p_empresa_id uuid, p_registro_patronal_id uuid, p_excluir_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, estatus text, empresa text, registro_patronal text, relacion text)
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
  select p.id, p.empleado_id, p.nombre_completo, p.estatus,
         e.nombre, rp.registro_patronal,
         case
           when p_registro_patronal_id is not null and p.registro_patronal_id = p_registro_patronal_id then 'mismo_rp'
           when p.registro_patronal_id is not null then 'otro_rp'
           when p.empresa_id is not distinct from p_empresa_id then 'sin_rp_misma_empresa'
           else 'sin_rp_otra_empresa'
         end
  from public.personal p
  left join public.empresas e on e.id = p.empresa_id and e.tenant_id = p.tenant_id
  left join public.empresas_registros_patronales rp on rp.id = p.registro_patronal_id and rp.tenant_id = p.tenant_id
  where public.tiene_rol('administrador','nomina')
    and p.tenant_id = public.current_tenant_id()
    and nullif(btrim(p_numero), '') is not null
    and upper(btrim(p.numero_interno_trabajador)) = upper(btrim(p_numero))
    and (p_excluir_id is null or p.id <> p_excluir_id)
  order by (p_registro_patronal_id is not null and p.registro_patronal_id = p_registro_patronal_id) desc,
           p.empleado_id
  limit 50;
$function$;
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
CREATE OR REPLACE FUNCTION public.en_alcance_persona(p_personal_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select case public.current_rol()
    when 'administrador' then true
    when 'nomina'        then true
    when 'consulta' then exists (
      select 1
      from public.personal p
      join public.usuario_alcances a
        on a.tenant_id = p.tenant_id
       and a.user_id   = auth.uid()
       and (a.empresa_id  is null or a.empresa_id  = p.empresa_id)
       and (a.proyecto_id is null or a.proyecto_id = p.proyecto_id)
      where p.id = p_personal_id
        and p.tenant_id = public.current_tenant_id())
    when 'coordinador' then exists (
      select 1
      from public.personal p
      where p.id = p_personal_id
        and p.tenant_id = public.current_tenant_id()
        and public.current_personal_id() is not null
        and p.coordinador_id = public.current_personal_id())
    else false
  end;
$function$;
CREATE OR REPLACE FUNCTION public.personal_organizacional()
 RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, empresa_id uuid, empresa_nombre text, registro_patronal_id uuid, registro_patronal text, proyecto_id uuid, proyecto_nombre text, puesto_id uuid, puesto_nombre text, area_id uuid, area_nombre text, departamento_id uuid, departamento_nombre text, localidad_id uuid, localidad_nombre text, centro_costo_id uuid, centro_costo_nombre text, coordinador_id uuid, coordinador_nombre text, coordinador_externo text, coordinador text, coordinador_asignado boolean, estatus text, fecha_antiguedad date, fecha_alta_imss date, fecha_baja date, tipo_contrato text, fecha_asignacion date, created_at timestamp with time zone)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select p.id, p.empleado_id, p.nombre_completo,
         p.empresa_id, e.nombre, p.registro_patronal_id, rp.registro_patronal,
         p.proyecto_id, pr.nombre, p.puesto_id, pu.nombre, p.area_id, ar.nombre,
         p.departamento_id, de.nombre, p.localidad_id, lo.nombre,
         p.centro_costo_id, cc.nombre,
         case when public.current_rol() = 'consulta'
                    and p.coordinador_id is not null
                    and not public.en_alcance_persona(p.coordinador_id)
              then null else p.coordinador_id end,
         case when public.current_rol() = 'consulta'
                    and p.coordinador_id is not null
                    and not public.en_alcance_persona(p.coordinador_id)
              then null else co.nombre_completo end,
         case when public.current_rol() = 'consulta'
                    and p.coordinador_id is not null
                    and not public.en_alcance_persona(p.coordinador_id)
              then null else p.coordinador_externo end,
         case when public.current_rol() = 'consulta'
                    and p.coordinador_id is not null
                    and not public.en_alcance_persona(p.coordinador_id)
              then 'Coordinador asignado'
              when p.coordinador_id is not null then coalesce(co.nombre_completo, '—')
              when p.coordinador_externo is not null then p.coordinador_externo || ' (externo)'
              else p.coordinador end,
         (p.coordinador_id is not null),
         p.estatus, p.fecha_antiguedad::date, p.fecha_alta_imss::date,
         p.fecha_baja::date, p.tipo_contrato, p.fecha_asignacion::date, p.created_at
  from public.personal p
  left join public.empresas e on e.id = p.empresa_id and e.tenant_id = p.tenant_id
  left join public.empresas_registros_patronales rp on rp.id = p.registro_patronal_id and rp.tenant_id = p.tenant_id
  left join public.proyectos pr on pr.id = p.proyecto_id and pr.tenant_id = p.tenant_id
  left join public.puestos pu on pu.id = p.puesto_id and pu.tenant_id = p.tenant_id
  left join public.areas ar on ar.id = p.area_id and ar.tenant_id = p.tenant_id
  left join public.departamentos de on de.id = p.departamento_id and de.tenant_id = p.tenant_id
  left join public.localidades lo on lo.id = p.localidad_id and lo.tenant_id = p.tenant_id
  left join public.centros_costo cc on cc.id = p.centro_costo_id and cc.tenant_id = p.tenant_id
  left join public.personal co on co.id = p.coordinador_id and co.tenant_id = p.tenant_id
  where p.tenant_id = public.current_tenant_id()
    and public.tiene_rol('administrador','nomina','consulta')
    and public.en_alcance_persona(p.id)
  order by p.created_at desc, p.id;
$function$;
CREATE OR REPLACE FUNCTION public.equipo_coordinador()
 RETURNS TABLE(id uuid, empleado_id text, nombre_completo text, puesto text, area text, departamento text, proyecto text, localidad text, estatus text, fecha_asignacion date, telefono_celular text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select p.id, p.empleado_id, p.nombre_completo,
         pu.nombre, ar.nombre, de.nombre, pr.nombre, lo.nombre,
         p.estatus, p.fecha_asignacion::date, p.telefono_celular
  from public.personal p
  left join public.puestos pu on pu.id = p.puesto_id and pu.tenant_id = p.tenant_id
  left join public.areas ar on ar.id = p.area_id and ar.tenant_id = p.tenant_id
  left join public.departamentos de on de.id = p.departamento_id and de.tenant_id = p.tenant_id
  left join public.proyectos pr on pr.id = p.proyecto_id and pr.tenant_id = p.tenant_id
  left join public.localidades lo on lo.id = p.localidad_id and lo.tenant_id = p.tenant_id
  where p.tenant_id = public.current_tenant_id()
    and public.tiene_rol('coordinador')
    and public.current_personal_id() is not null
    and p.coordinador_id = public.current_personal_id()
  order by p.nombre_completo, p.id;
$function$;
CREATE OR REPLACE FUNCTION public.resumen_agregado()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
with
cfg as (select 3 as k),
permitido as (
  select public.current_tenant_id() as tenant
  where public.tiene_rol('administrador','nomina','consulta')
),
ve_importes as (select public.tiene_rol('administrador','nomina') as si),
pers as (
  select p.* from public.personal p, permitido
  where p.tenant_id = permitido.tenant and public.en_alcance_persona(p.id)
),
vig as (select * from pers where coalesce(estatus,'') <> 'Baja'),
esq as (
  select rp.personal_id, rp.sueldo, rp.modalidad_sueldo as modalidad,
         rp.periodicidad_id, pe.nombre as periodicidad,
         coalesce(rp.dias_periodo, pe.dias_default)::numeric as dias,
         rp.clasificacion_id, coalesce(c.nombre, 'Sin clasificación') as clasificacion,
         v.proyecto_id,
         case when v.coordinador_id is not null then coalesce(co.nombre_completo, '—')
              when v.coordinador_externo is not null then v.coordinador_externo || ' (externo)'
              when coalesce(v.coordinador,'') <> '' then v.coordinador
              else 'Sin coordinador' end as coordinador
  from public.personal_registros_pago rp
  join vig v on v.id = rp.personal_id and v.tenant_id = rp.tenant_id
  join public.periodicidades pe on pe.id = rp.periodicidad_id and pe.tenant_id = rp.tenant_id
  left join public.clasificaciones_personal c on c.id = rp.clasificacion_id and c.tenant_id = rp.tenant_id
  left join public.personal co on co.id = v.coordinador_id and co.tenant_id = v.tenant_id
  where rp.activo and (select si from ve_importes)
),
vig_dim as (
  select v.id, v.proyecto_id,
         case when public.current_rol() = 'consulta'
                    and v.coordinador_id is not null
                    and not public.en_alcance_persona(v.coordinador_id)
              then 'Coordinador asignado'
              when v.coordinador_id is not null then coalesce(co.nombre_completo, '—')
              when v.coordinador_externo is not null then v.coordinador_externo || ' (externo)'
              when coalesce(v.coordinador,'') <> '' then v.coordinador
              else 'Sin coordinador' end as coordinador
  from vig v
  left join public.personal co on co.id = v.coordinador_id and co.tenant_id = v.tenant_id
),
celdas as (
  select 'total'::text as dim, ''::text as clave, ''::text as nombre,
         modalidad, periodicidad_id, periodicidad, dias,
         count(*) as esquemas, count(distinct personal_id) as personas,
         sum(round(sueldo * 100))::bigint as centavos
  from esq group by modalidad, periodicidad_id, periodicidad, dias
  union all
  select 'clasificacion', coalesce(clasificacion_id::text,''), clasificacion,
         modalidad, periodicidad_id, periodicidad, dias,
         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint
  from esq group by clasificacion_id, clasificacion, modalidad, periodicidad_id, periodicidad, dias
  union all
  select 'proyecto', coalesce(e.proyecto_id::text,''), coalesce(pr.nombre, 'Sin proyecto'),
         modalidad, periodicidad_id, periodicidad, dias,
         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint
  from esq e left join public.proyectos pr on pr.id = e.proyecto_id and pr.tenant_id = (select tenant from permitido)
  group by e.proyecto_id, pr.nombre, modalidad, periodicidad_id, periodicidad, dias
  union all
  select 'coordinador', coordinador, coordinador,
         modalidad, periodicidad_id, periodicidad, dias,
         count(*), count(distinct personal_id), sum(round(sueldo * 100))::bigint
  from esq group by coordinador, modalidad, periodicidad_id, periodicidad, dias
),
rankeadas as (
  select c.*, row_number() over w as rn,
         sum(personas) over w as acumuladas,
         count(*) filter (where personas < (select k from cfg)) over (partition by dim, modalidad, periodicidad_id, dias) as primarias
  from celdas c
  window w as (partition by dim, modalidad, periodicidad_id, dias order by personas, clave
               rows between unbounded preceding and current row)
),
corte as (
  select dim, modalidad, periodicidad_id, dias,
         coalesce(min(rn) filter (where rn >= primarias and rn >= 2 and acumuladas >= (select k from cfg)), max(rn)) as n_ocultas,
         max(primarias) as primarias
  from rankeadas where dim <> 'total'
  group by dim, modalidad, periodicidad_id, dias
),
marcadas as (
  select r.*,
         case when r.dim = 'total' then r.personas < (select k from cfg)
              when co.primarias = 0 then false else r.rn <= co.n_ocultas end as oculto
  from rankeadas r left join corte co using (dim, modalidad, periodicidad_id, dias)
),
grupo_json as (
  select dim, clave, nombre,
         jsonb_agg(jsonb_build_object('modalidad', modalidad, 'periodicidad', periodicidad, 'dias', dias,
           'esquemas', esquemas, 'personas', personas,
           'importe', case when oculto then null else centavos / 100.0 end, 'oculto', oculto)
           order by modalidad, periodicidad, dias) as grupos,
         sum(esquemas) as esquemas
  from marcadas group by dim, clave, nombre
),
personas_dim as (
  select 'proyecto'::text as dim, coalesce(vd.proyecto_id::text,'') as clave,
         coalesce(pr.nombre, 'Sin proyecto') as nombre, count(*) as personas
  from vig_dim vd left join public.proyectos pr on pr.id = vd.proyecto_id and pr.tenant_id = (select tenant from permitido)
  group by vd.proyecto_id, pr.nombre
  union all
  select 'coordinador', coordinador, coordinador, count(*) from vig_dim group by coordinador
  union all
  select 'clasificacion', coalesce(clasificacion_id::text,''), clasificacion, count(distinct personal_id)
  from esq group by clasificacion_id, clasificacion
),
desglose as (
  select pd.dim, jsonb_agg(jsonb_build_object('nombre', pd.nombre, 'personas', pd.personas,
         'esquemas', coalesce(g.esquemas, 0), 'grupos', coalesce(g.grupos, '[]'::jsonb))
         order by pd.nombre) as filas
  from personas_dim pd left join grupo_json g on g.dim = pd.dim and g.clave = pd.clave
  group by pd.dim
)
select case when not exists (select 1 from permitido) then null else jsonb_build_object(
  'k', (select k from cfg), 'importes', (select si from ve_importes),
  'personal', jsonb_build_object('vigentes', (select count(*) from vig),
     'baja', (select count(*) from pers) - (select count(*) from vig),
     'empresas', (select count(distinct empresa_id) from vig where empresa_id is not null),
     'proyectos', (select count(distinct proyecto_id) from vig where proyecto_id is not null)),
  'compensacion', case when (select si from ve_importes) then jsonb_build_object(
     'esquemas', (select count(*) from esq), 'bruto', (select count(*) from esq where modalidad = 'bruto'),
     'neto', (select count(*) from esq where modalidad = 'neto'),
     'personas_con_esquema', (select count(distinct personal_id) from esq),
     'sin_esquema', (select count(*) from vig) - (select count(distinct personal_id) from esq)) end,
  'grupos', case when (select si from ve_importes) then coalesce((select grupos from grupo_json where dim = 'total'), '[]'::jsonb) end,
  'desglose', coalesce((select jsonb_object_agg(dim, filas) from desglose), '{}'::jsonb)
) end;
$function$;
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
revoke all on all tables in schema public from anon;
revoke delete, truncate, references, trigger on
  public.areas, public.centros_costo, public.clasificaciones_personal, public.combo_conceptos,
  public.combos, public.conceptos_percepcion, public.departamentos, public.empresas,
  public.empresas_registros_patronales, public.localidades, public.movimientos,
  public.periodicidades, public.personal, public.personal_percepciones, public.proyectos,
  public.puestos, public.tenants, public.usuarios_tenant
  from authenticated;
revoke all on table public.usuario_alcances from public, anon, authenticated;
revoke execute on all functions in schema public from public, anon, authenticated;
grant execute on function
  public.current_tenant_id(), public.tiene_rol(text[]),
  public.es_cp_valido(text), public.es_curp_valida(text), public.es_nss_valido(text),
  public.es_rfc_persona_valido(text), public.fecha_aammdd_valida(text, text),
  public.coincidencias_numero_interno(text, uuid, uuid, uuid), public.en_alcance_persona(uuid),
  public.personal_organizacional(), public.equipo_coordinador(), public.resumen_agregado()
  to authenticated;
do $$
declare h text; r record;
begin
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

-- 2. Restaurar roles (equivale al bloque D de la migración de producción) --
-- La migración recrea usuarios_tenant.rol con valor por defecto «consulta».
-- Se reponen rol y ficha vinculada tal como estaban al inicio y se exige
-- que A y B queden como administrador en tenants distintos.
update public.usuarios_tenant ut
   set rol = s.rol, personal_id = s.personal_id
  from _ut_snapshot s
 where s.user_id = ut.user_id;
do $$
declare ta uuid; tb uuid;
begin
  if (select count(*) from public.usuarios_tenant ut join _ut_snapshot s using (user_id)
       where ut.rol is not distinct from s.rol and ut.personal_id is not distinct from s.personal_id
         and ut.tenant_id = s.tenant_id) <> (select count(*) from _ut_snapshot)
     or (select count(*) from public.usuarios_tenant) <> (select count(*) from _ut_snapshot) then
    raise exception 'PRUEBA_FALLIDA: no se pudieron restaurar los roles iniciales de usuarios_tenant.';
  end if;
  select tenant_id into ta from public.usuarios_tenant where user_id = '22222222-0000-4000-8000-000000000001' and rol = 'administrador';
  select tenant_id into tb from public.usuarios_tenant where user_id = '00000000-0000-4000-8000-0000007d6c02' and rol = 'administrador';
  if ta is null or tb is null then
    raise exception 'PRUEBA_FALLIDA: A o B no quedaron como administrador tras la migración.';
  end if;
  if ta = tb then
    raise exception 'PRUEBA_FALLIDA: A y B quedaron en el mismo tenant.';
  end if;
  -- Valores esperados (vistos como postgres, sin RLS) y existencia de datos ajenos
  perform set_config('bh.a_tenant', ta::text, true);
  perform set_config('bh.b_tenant', tb::text, true);
  perform set_config('bh.a_esp_personal', (select count(*) from public.personal where tenant_id = ta)::text, true);
  perform set_config('bh.b_esp_personal', (select count(*) from public.personal where tenant_id = tb)::text, true);
  perform set_config('bh.a_esp_empresas', (select count(*) from public.empresas where tenant_id = ta)::text, true);
  perform set_config('bh.b_esp_empresas', (select count(*) from public.empresas where tenant_id = tb)::text, true);
  perform set_config('bh.a_datos', format('personas=%s,empresas=%s,esquemas=%s,areas=%s',
    (select count(*) from public.personal where tenant_id = ta), (select count(*) from public.empresas where tenant_id = ta),
    (select count(*) from public.personal_registros_pago where tenant_id = ta), (select count(*) from public.areas where tenant_id = ta)), true);
  perform set_config('bh.b_datos', format('personas=%s,empresas=%s,esquemas=%s,areas=%s',
    (select count(*) from public.personal where tenant_id = tb), (select count(*) from public.empresas where tenant_id = tb),
    (select count(*) from public.personal_registros_pago where tenant_id = tb), (select count(*) from public.areas where tenant_id = tb)), true);
  if (select count(*) from public.personal where tenant_id = ta) = 0
     or (select count(*) from public.personal where tenant_id = tb) = 0
     or (select count(*) from public.empresas where tenant_id = ta) = 0
     or (select count(*) from public.empresas where tenant_id = tb) = 0 then
    raise exception 'PRUEBA_FALLIDA: algún tenant de prueba no tiene personas o empresas; el aislamiento no sería concluyente.';
  end if;
end $$;

-- 2b. Privilegios de authenticated para las operaciones probadas ------
-- (como postgres, después de migrar y antes de simular sesiones)
do $$
declare t text; f text; faltan text := '';
  lectura text[] := array['personal','empresas','empresas_registros_patronales','personal_registros_pago',
    'v_personal_registros_pago','movimientos','proyectos','periodicidades','clasificaciones_personal',
    'areas','departamentos','puestos','localidades','centros_costo','usuarios_tenant','tenants'];
  escritura text[] := array['personal','empresas','personal_registros_pago','areas'];
begin
  if not has_schema_privilege('authenticated', 'public', 'USAGE') then
    faltan := faltan || ' USAGE en esquema public;';
  end if;
  foreach t in array lectura loop
    if not has_table_privilege('authenticated', 'public.' || t, 'SELECT') then
      faltan := faltan || ' SELECT en ' || t || ';';
    end if;
  end loop;
  foreach t in array escritura loop
    if not has_table_privilege('authenticated', 'public.' || t, 'UPDATE') then
      faltan := faltan || ' UPDATE en ' || t || ';';
    end if;
  end loop;
  if not has_table_privilege('authenticated', 'public.areas', 'INSERT') then
    faltan := faltan || ' INSERT en areas;';
  end if;
  foreach f in array array['public.current_tenant_id()','public.tiene_rol(text[])',
                           'public.personal_organizacional()','auth.uid()'] loop
    if not has_function_privilege('authenticated', f, 'EXECUTE') then
      faltan := faltan || ' EXECUTE en ' || f || ';';
    end if;
  end loop;
  if faltan <> '' then
    raise exception 'PRUEBA_FALLIDA: a authenticated le faltan privilegios necesarios para la prueba:%', faltan;
  end if;
  -- El DELETE se prueba esperando falta de privilegio; si existiera, el
  -- resultado no sería interpretable como está escrito.
  if has_table_privilege('authenticated', 'public.empresas', 'DELETE') then
    raise exception 'PRUEBA_FALLIDA: authenticated tiene DELETE en empresas; V2.0 debía retirarlo.';
  end if;
  perform set_config('bh.priv', 'select_16_ok;update_4_ok;insert_areas_ok;execute_4_ok;sin_delete_empresas', true);
end $$;

-- 3a. Aislamiento como A admin-prueba ---------------------------------
select set_config('request.jwt.claims', '{"sub":"22222222-0000-4000-8000-000000000001","role":"authenticated"}', true);
select set_config('request.jwt.claim.sub', '22222222-0000-4000-8000-000000000001', true);
set local role authenticated;
do $$
declare
  v_t uuid := current_setting('bh.a_tenant')::uuid;
  v_otro uuid := current_setting('bh.b_tenant')::uuid;
  v_rol text; n bigint; t text; v_emp uuid; v_nuevo uuid; v_tins uuid; res text := '';
  tablas text[] := array['personal','empresas','empresas_registros_patronales','personal_registros_pago',
    'v_personal_registros_pago','movimientos','proyectos','periodicidades','clasificaciones_personal',
    'areas','departamentos','puestos','localidades','centros_costo','usuarios_tenant'];
begin
  -- Rol y tenant efectivos, tal como los resuelve el servidor para esta sesión
  if current_user <> 'authenticated' then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: la sesión no corre como authenticated (%)', current_user;
  end if;
  select rol into v_rol from public.usuarios_tenant where user_id = auth.uid();
  if v_rol is distinct from 'administrador' or not public.tiene_rol('administrador') then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: rol efectivo no es administrador (rol=%). No se acepta la prueba.', coalesce(v_rol,'null');
  end if;
  if public.current_tenant_id() is distinct from v_t then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: tenant efectivo % distinto del esperado %', public.current_tenant_id(), v_t;
  end if;

  -- LECTURA propia: ve exactamente lo de su tenant
  select count(*) into n from public.personal;
  if n <> current_setting('bh.a_esp_personal')::bigint then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: ve % personas propias, se esperaban %', n, current_setting('bh.a_esp_personal');
  end if;
  res := res || 'personas_propias=' || n;
  select count(*) into n from public.empresas;
  if n <> current_setting('bh.a_esp_empresas')::bigint then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: ve % empresas propias, se esperaban %', n, current_setting('bh.a_esp_empresas');
  end if;
  res := res || ';empresas_propias=' || n;
  select count(*) into n from public.personal_organizacional();
  if n <> current_setting('bh.a_esp_personal')::bigint then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: personal_organizacional() devuelve %, se esperaban %', n, current_setting('bh.a_esp_personal');
  end if;

  -- LECTURA ajena: 0 filas en 15 tablas/vistas y en tenants
  foreach t in array tablas loop
    execute format('select count(*) from public.%I where tenant_id <> $1', t) into n using v_t;
    if n <> 0 then
      raise exception 'PRUEBA_FALLIDA [A admin-prueba]: ve % fila(s) ajenas en %', n, t;
    end if;
  end loop;
  select count(*) into n from public.tenants where id <> v_t;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: ve % tenant(s) ajenos', n; end if;
  res := res || ';lectura_ajena=0_en_16';

  -- MODIFICACIÓN ajena: UPDATE dirigido al otro tenant afecta 0 filas
  update public.personal set nombre_completo = nombre_completo where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: modificó % persona(s) ajenas', n; end if;
  update public.empresas set nombre = nombre where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: modificó % empresa(s) ajenas', n; end if;
  update public.personal_registros_pago set notas = notas where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: modificó % esquema(s) ajenos', n; end if;
  update public.areas set nombre = nombre where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: modificó % catálogo(s) ajenos', n; end if;
  res := res || ';update_ajeno=0';

  -- INSERT dirigido al otro tenant. Resultados aceptados:
  --   a) el servidor lo deja en el tenant propio (trigger de asignación), o
  --   b) se rechaza por RLS (42501, WITH CHECK).
  -- Cualquier otro error no se captura y aborta la prueba.
  begin
    insert into public.areas (nombre, tenant_id) values ('ZZ_PRUEBA_AISLAMIENTO_A', v_otro)
      returning id, tenant_id into v_nuevo, v_tins;
    if v_tins is distinct from v_t then
      raise exception 'PRUEBA_FALLIDA [A admin-prueba]: un INSERT con tenant ajeno quedó en el tenant %', v_tins;
    end if;
    res := res || ';insert_ajeno=reasignado_al_propio';
  exception
    when insufficient_privilege then res := res || ';insert_ajeno=rechazado_RLS(42501_con_privilegio_INSERT)';
  end;

  -- Mover un registro propio al otro tenant. Resultados aceptados:
  --   a) error del trigger bloquear_cambio_tenant (P0001, mensaje conocido), o
  --   b) rechazo por RLS (42501).
  -- Cualquier otro error, o que no haya error, aborta la prueba.
  select id into v_emp from public.empresas limit 1;
  if v_emp is null then
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: no hay empresa propia visible para probar el cambio de tenant';
  end if;
  begin
    update public.empresas set tenant_id = v_otro where id = v_emp;
    get diagnostics n = row_count;
    raise exception 'PRUEBA_FALLIDA [A admin-prueba]: permitió mover % empresa(s) propia(s) a otro tenant', n;
  exception
    when insufficient_privilege then
      res := res || ';mover_a_otro_tenant=rechazado_RLS(42501_con_privilegio_UPDATE)';
    when raise_exception then
      if sqlerrm like 'No está permitido reasignar tenant_id%' then
        res := res || ';mover_a_otro_tenant=rechazado_trigger';
      else
        raise;
      end if;
  end;

  -- DELETE dirigido al otro tenant: sin privilegio o 0 filas
  begin
    delete from public.empresas where tenant_id = v_otro;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'PRUEBA_FALLIDA [A admin-prueba]: borró % empresa(s) ajenas', n; end if;
    res := res || ';delete_ajeno=0_filas';
  exception
    when insufficient_privilege then res := res || ';delete_ajeno=sin_privilegio_DELETE';
  end;

  perform set_config('bh.a_res', 'rol=' || v_rol || ';' || res, true);
end $$;
reset role;

-- 3b. Aislamiento como B prueba2-7d6b ---------------------------------
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-8000-0000007d6c02","role":"authenticated"}', true);
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-0000007d6c02', true);
set local role authenticated;
do $$
declare
  v_t uuid := current_setting('bh.b_tenant')::uuid;
  v_otro uuid := current_setting('bh.a_tenant')::uuid;
  v_rol text; n bigint; t text; v_emp uuid; v_nuevo uuid; v_tins uuid; res text := '';
  tablas text[] := array['personal','empresas','empresas_registros_patronales','personal_registros_pago',
    'v_personal_registros_pago','movimientos','proyectos','periodicidades','clasificaciones_personal',
    'areas','departamentos','puestos','localidades','centros_costo','usuarios_tenant'];
begin
  -- Rol y tenant efectivos, tal como los resuelve el servidor para esta sesión
  if current_user <> 'authenticated' then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: la sesión no corre como authenticated (%)', current_user;
  end if;
  select rol into v_rol from public.usuarios_tenant where user_id = auth.uid();
  if v_rol is distinct from 'administrador' or not public.tiene_rol('administrador') then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: rol efectivo no es administrador (rol=%). No se acepta la prueba.', coalesce(v_rol,'null');
  end if;
  if public.current_tenant_id() is distinct from v_t then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: tenant efectivo % distinto del esperado %', public.current_tenant_id(), v_t;
  end if;

  -- LECTURA propia: ve exactamente lo de su tenant
  select count(*) into n from public.personal;
  if n <> current_setting('bh.b_esp_personal')::bigint then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: ve % personas propias, se esperaban %', n, current_setting('bh.b_esp_personal');
  end if;
  res := res || 'personas_propias=' || n;
  select count(*) into n from public.empresas;
  if n <> current_setting('bh.b_esp_empresas')::bigint then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: ve % empresas propias, se esperaban %', n, current_setting('bh.b_esp_empresas');
  end if;
  res := res || ';empresas_propias=' || n;
  select count(*) into n from public.personal_organizacional();
  if n <> current_setting('bh.b_esp_personal')::bigint then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: personal_organizacional() devuelve %, se esperaban %', n, current_setting('bh.b_esp_personal');
  end if;

  -- LECTURA ajena: 0 filas en 15 tablas/vistas y en tenants
  foreach t in array tablas loop
    execute format('select count(*) from public.%I where tenant_id <> $1', t) into n using v_t;
    if n <> 0 then
      raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: ve % fila(s) ajenas en %', n, t;
    end if;
  end loop;
  select count(*) into n from public.tenants where id <> v_t;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: ve % tenant(s) ajenos', n; end if;
  res := res || ';lectura_ajena=0_en_16';

  -- MODIFICACIÓN ajena: UPDATE dirigido al otro tenant afecta 0 filas
  update public.personal set nombre_completo = nombre_completo where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: modificó % persona(s) ajenas', n; end if;
  update public.empresas set nombre = nombre where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: modificó % empresa(s) ajenas', n; end if;
  update public.personal_registros_pago set notas = notas where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: modificó % esquema(s) ajenos', n; end if;
  update public.areas set nombre = nombre where tenant_id = v_otro;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: modificó % catálogo(s) ajenos', n; end if;
  res := res || ';update_ajeno=0';

  -- INSERT dirigido al otro tenant. Resultados aceptados:
  --   a) el servidor lo deja en el tenant propio (trigger de asignación), o
  --   b) se rechaza por RLS (42501, WITH CHECK).
  -- Cualquier otro error no se captura y aborta la prueba.
  begin
    insert into public.areas (nombre, tenant_id) values ('ZZ_PRUEBA_AISLAMIENTO_B', v_otro)
      returning id, tenant_id into v_nuevo, v_tins;
    if v_tins is distinct from v_t then
      raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: un INSERT con tenant ajeno quedó en el tenant %', v_tins;
    end if;
    res := res || ';insert_ajeno=reasignado_al_propio';
  exception
    when insufficient_privilege then res := res || ';insert_ajeno=rechazado_RLS(42501_con_privilegio_INSERT)';
  end;

  -- Mover un registro propio al otro tenant. Resultados aceptados:
  --   a) error del trigger bloquear_cambio_tenant (P0001, mensaje conocido), o
  --   b) rechazo por RLS (42501).
  -- Cualquier otro error, o que no haya error, aborta la prueba.
  select id into v_emp from public.empresas limit 1;
  if v_emp is null then
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: no hay empresa propia visible para probar el cambio de tenant';
  end if;
  begin
    update public.empresas set tenant_id = v_otro where id = v_emp;
    get diagnostics n = row_count;
    raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: permitió mover % empresa(s) propia(s) a otro tenant', n;
  exception
    when insufficient_privilege then
      res := res || ';mover_a_otro_tenant=rechazado_RLS(42501_con_privilegio_UPDATE)';
    when raise_exception then
      if sqlerrm like 'No está permitido reasignar tenant_id%' then
        res := res || ';mover_a_otro_tenant=rechazado_trigger';
      else
        raise;
      end if;
  end;

  -- DELETE dirigido al otro tenant: sin privilegio o 0 filas
  begin
    delete from public.empresas where tenant_id = v_otro;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'PRUEBA_FALLIDA [B prueba2-7d6b]: borró % empresa(s) ajenas', n; end if;
    res := res || ';delete_ajeno=0_filas';
  exception
    when insufficient_privilege then res := res || ';delete_ajeno=sin_privilegio_DELETE';
  end;

  perform set_config('bh.b_res', 'rol=' || v_rol || ';' || res, true);
end $$;
reset role;

-- 3c. Verificación posterior como postgres (sin RLS) -----------------
do $$
declare ta uuid := current_setting('bh.a_tenant')::uuid; tb uuid := current_setting('bh.b_tenant')::uuid;
begin
  if current_user = 'authenticated' then
    raise exception 'PRUEBA_FALLIDA: la verificación posterior no corre como postgres';
  end if;
  if exists (select 1 from public.areas where nombre = 'ZZ_PRUEBA_AISLAMIENTO_A' and tenant_id <> ta)
     or exists (select 1 from public.areas where nombre = 'ZZ_PRUEBA_AISLAMIENTO_B' and tenant_id <> tb) then
    raise exception 'PRUEBA_FALLIDA: un INSERT de prueba quedó en un tenant ajeno';
  end if;
  if (select count(*) from public.empresas where tenant_id = ta) <> current_setting('bh.a_esp_empresas')::bigint
     or (select count(*) from public.empresas where tenant_id = tb) <> current_setting('bh.b_esp_empresas')::bigint
     or (select count(*) from public.personal where tenant_id = ta) <> current_setting('bh.a_esp_personal')::bigint
     or (select count(*) from public.personal where tenant_id = tb) <> current_setting('bh.b_esp_personal')::bigint then
    raise exception 'PRUEBA_FALLIDA: cambiaron los conteos de personas o empresas por tenant durante la prueba';
  end if;
  perform set_config('bh.post', 'sin_filas_en_tenant_ajeno;conteos_por_tenant_intactos', true);
end $$;

-- 4. Resultado y reversión forzada ------------------------------------
do $$ begin
  raise exception 'PRUEBA_COMPLETA_OK | reversion=huella_prod_03e9 OK | migracion=huella_pruebas_ebcd OK | roles_restaurados OK | privilegios: % | datos A: % | datos B: % | A: % | B: % | posterior: %',
    current_setting('bh.priv'), current_setting('bh.a_datos'), current_setting('bh.b_datos'), current_setting('bh.a_res'), current_setting('bh.b_res'), current_setting('bh.post');
end $$;
commit;
