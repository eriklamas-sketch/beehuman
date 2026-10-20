-- =====================================================================
-- BeeHuman V2.0 · REVERSIÓN de la migración 20261018000000
-- Archivo: supabase/reversion/20261018000000_reversion_v2_0.sql
-- DESTINO: PRODUCCIÓN, solo si hay que volver a V1 después de aplicar V2.0.
-- ESTADO: preparada y probada en beehuman-pruebas dentro de una
-- transacción revertida (ver cierre). NO aplicada en producción.
--
-- Deja el esquema EXACTAMENTE como estaba el 17-oct-2026 (huella
-- 03e98353d5e19d32ad52fd84b464f608): políticas «todo el tenant», permisos
-- originales, sin roles, sin número interno, sin ámbitos ni autoría.
-- No borra filas de personas, esquemas, empresas ni movimientos.
--
-- LO QUE SÍ SE PIERDE al revertir (capturado después de publicar V2.0):
--   * números internos de trabajador (personal.numero_interno_trabajador)
--   * roles y fichas vinculadas (usuarios_tenant.rol / personal_id)
--   * ámbitos de Consulta (usuario_alcances)
--   * autoría (creado_por / actualizado_por / actualizado_en) y
--     movimientos.usuario_id (el correo sigue en movimientos.usuario)
-- Antes de revertir, exporta esos datos con el bloque 0.
-- Después de revertir, vuelve a publicar el HTML anterior (main @ f7598d8):
-- el HTML V2.0 no funciona sin este esquema.
-- =====================================================================

-- 0. (Opcional, ANTES de revertir; solo lectura) Exportar lo que se perderá:
-- select empleado_id, numero_interno_trabajador from public.personal
--  where nullif(btrim(numero_interno_trabajador),'') is not null;
-- select ut.user_id, u.email, ut.rol, ut.personal_id from public.usuarios_tenant ut join auth.users u on u.id = ut.user_id;
-- select * from public.usuario_alcances;

begin;

-- @@CANDADO_PROD_INICIO
do $$
begin
  if not exists (select 1 from public.tenants where id = '00000000-0000-4000-8000-de0000000001' and nombre = 'BeeHuman — Demo') then
    raise exception 'DETENIDO: no se reconoce producción. No se revirtió nada.';
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='usuarios_tenant' and column_name='rol') then
    raise exception 'DETENIDO: V2.0 no está aplicada; no hay nada que revertir.';
  end if;
end $$;
-- @@CANDADO_PROD_FIN

create temp table _rv_conteos as
  select 'personal' t, count(*) n from public.personal
  union all select 'personal_registros_pago', count(*) from public.personal_registros_pago
  union all select 'movimientos', count(*) from public.movimientos
  union all select 'empresas', count(*) from public.empresas
  union all select 'usuarios_tenant', count(*) from public.usuarios_tenant;

-- 1. Políticas V2.0 → políticas V1
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

-- 2. Autoría
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

-- 3. M2 y M1
drop function public.resumen_agregado();
drop function public.equipo_coordinador();
drop function public.personal_organizacional();
drop function public.en_alcance_persona(uuid);
drop function public.coincidencias_numero_interno(text, uuid, uuid, uuid);
drop table public.usuario_alcances;
drop index public.personal_numero_interno_rp_uq;
alter table public.personal drop column numero_interno_trabajador;

-- 4. Roles
drop function public.tiene_rol(text[]);
drop function public.current_rol();
drop function public.current_personal_id();
alter table public.usuarios_tenant
  drop constraint usuarios_tenant_user_tenant_key,
  drop constraint usuarios_tenant_personal_fk,
  drop constraint usuarios_tenant_rol_check,
  drop column personal_id,
  drop column rol;

-- 5. Definiciones originales de V1 (texto literal de producción)
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
-- Se arma con E'\r\n' porque el original en producción tiene saltos de línea Windows (CRLF)
-- y la huella compara el texto exacto de la función.
do $rv$ begin
  execute E'CREATE OR REPLACE FUNCTION public.generar_empleado_id()\n RETURNS trigger\n LANGUAGE plpgsql\nAS $function$\r\nbegin\r\n  if new.empleado_id is null then\r\n    new.empleado_id := ''BEH-'' || lpad(nextval(''personal_empleado_id_seq'')::text, 6, ''0'');\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $rv$;

-- 6. Permisos originales de V1 (mismo orden que hoy en producción)
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

-- 7. Verificación
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

commit;
