-- BeeHuman · Corrección «Mis hojas» del coordinador (D1, D2, D3) · 16-nov-2026
-- Diagnóstico: claude/Mis-hojas-coordinador-diagnostico-14nov.md
-- Diseño aprobado por Erik (16-nov 18:15): claude/Mis-hojas-coordinador-diseno-correccion-16nov.md
--
-- Regla única (la misma de inc_tablero_periodo e inc_personas_hoja): un
-- coordinador «tiene personal» en un periodo si existe al menos un día del
-- periodo con una asignación suya vigente y la persona con relación laboral
-- en la empresa del periodo (inc_relacion_en). Se evalúa con las fechas del
-- periodo, no con la asignación de hoy.
--
-- D1  inc_periodos_select: el coordinador solo ve periodos donde tiene
--     personal o donde ya tiene una hoja suya (conserva sus hojas). Los demás
--     roles, sin cambio (todo el tenant).
-- D2  inc_abrir_hoja rechaza abrir una hoja nueva sin personal.
--     inc_enviar_hoja rechaza enviar una hoja normal nunca enviada, sin
--     personal y sin capturas ni observaciones.
--     inc_faltantes_procesar no cuenta esa misma hoja vacía (condición
--     específica: inc_hoja_vacia_sin_personal + borrador + versión 0).
-- D3  inc_empresas_visibles(): id y nombre solo de las empresas con periodos
--     visibles para quien llama. Los permisos de la tabla empresas no cambian.
-- No crea, borra ni modifica datos. Originales en respaldo.mis_hojas_20261116.
begin;
do $$
begin
  if to_regclass('respaldo.mis_hojas_20261116') is not null then
    raise exception 'BeeHuman: la corrección «Mis hojas» ya está aplicada.';
  end if;
  if to_regclass('respaldo.b5_creditos_20261113') is null then
    raise exception 'BeeHuman: esta corrección requiere B5 (20261113000000).';
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'inc_periodos'
                  and policyname = 'inc_periodos_select' and qual = '(tenant_id = current_tenant_id())') then
    raise exception 'BeeHuman: la política inc_periodos_select no es la esperada; revisar antes de aplicar.';
  end if;
end $$;

create table respaldo.mis_hojas_20261116 (objeto text primary key, original text not null);
insert into respaldo.mis_hojas_20261116
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array[
    'public.inc_abrir_hoja(uuid,uuid)', 'public.inc_enviar_hoja(uuid,text)', 'public.inc_faltantes_procesar(uuid)']) x;
insert into respaldo.mis_hojas_20261116 values
  ('policy inc_periodos_select', 'create policy inc_periodos_select on public.inc_periodos for select to authenticated using (tenant_id = public.current_tenant_id())');
revoke all on table respaldo.mis_hojas_20261116 from public;

-- ---------------------------------------------------------------------
-- 1. Reglas
-- ---------------------------------------------------------------------
create function public.inc_coordinador_tiene_personal(p_coord uuid, p_periodo uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select exists (
    select 1
      from public.inc_periodos pe
      join public.inc_asignaciones a on a.coordinador_id = p_coord and a.tenant_id = pe.tenant_id
           and a.desde <= pe.fin and (a.hasta is null or a.hasta >= pe.inicio)
     cross join lateral generate_series(greatest(a.desde, pe.inicio), least(coalesce(a.hasta, pe.fin), pe.fin), interval '1 day') d
     where pe.id = p_periodo
       and public.inc_relacion_en(a.personal_id, pe.empresa_id, d::date) is not null)
$$;

-- Hoja normal cuyo coordinador no tiene personal en el periodo y que no tiene
-- ninguna captura (celdas, cantidades), observación por persona ni
-- observación general.
create function public.inc_hoja_vacia_sin_personal(p_hoja uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select exists (
    select 1 from public.inc_hojas h
     where h.id = p_hoja and h.tipo = 'normal'
       and not public.inc_coordinador_tiene_personal(h.coordinador_id, h.periodo_id)
       and not exists (select 1 from public.inc_celdas c where c.hoja_id = h.id)
       and not exists (select 1 from public.inc_cantidades q where q.hoja_id = h.id)
       and not exists (select 1 from public.inc_observaciones o where o.hoja_id = h.id)
       and coalesce(btrim(h.observacion_general), '') = '')
$$;

-- D1: visibilidad de un periodo para quien llama (la política agrega el tenant).
create function public.inc_periodo_visible(p_periodo uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select case
    when public.tiene_rol('administrador','nomina','consulta') then true
    when public.tiene_rol('coordinador') and public.current_personal_id() is not null then
      exists (select 1 from public.inc_hojas h where h.periodo_id = p_periodo and h.coordinador_id = public.current_personal_id())
      or public.inc_coordinador_tiene_personal(public.current_personal_id(), p_periodo)
    else false end
$$;

drop policy inc_periodos_select on public.inc_periodos;
create policy inc_periodos_select on public.inc_periodos for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.inc_periodo_visible(id));

-- D3: nombres de empresa limitados a los periodos visibles.
create function public.inc_empresas_visibles() returns table (id uuid, nombre text)
language sql stable security definer set search_path to '' as $$
  select e.id, e.nombre from public.empresas e
   where e.tenant_id = public.current_tenant_id()
     and exists (select 1 from public.inc_periodos pe
                  where pe.empresa_id = e.id and pe.tenant_id = e.tenant_id and public.inc_periodo_visible(pe.id))
   order by e.nombre
$$;

-- ---------------------------------------------------------------------
-- 2. Abrir y enviar (cambian; originales en respaldo)
-- ---------------------------------------------------------------------
create or replace function public.inc_abrir_hoja(p_periodo uuid, p_complemento_de uuid default null::uuid)
returns uuid language plpgsql security definer set search_path to '' as $$
declare v_id uuid; v_coord uuid := public.current_personal_id(); pe record; raiz record;
begin
  if not public.tiene_rol('coordinador') or v_coord is null then raise exception 'BeeHuman: solo un coordinador abre su hoja.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  if p_complemento_de is null then
    if pe.procesado_en is not null then raise exception 'BeeHuman: el periodo ya fue procesado; usa un complemento.'; end if;
    select id into v_id from public.inc_hojas where periodo_id = p_periodo and coordinador_id = v_coord and tipo = 'normal';
    if v_id is not null then return v_id; end if;
    -- D2: sin personal asignado en el periodo no hay hoja que abrir.
    if not public.inc_coordinador_tiene_personal(v_coord, p_periodo) then
      raise exception 'BeeHuman: no tienes personas asignadas en % durante este periodo; no hay hoja que abrir.',
        coalesce((select e.nombre from public.empresas e where e.id = pe.empresa_id), 'esta empresa');
    end if;
    v_id := gen_random_uuid();
    insert into public.inc_hojas (id, tenant_id, periodo_id, coordinador_id, tipo, hoja_raiz_id, creado_por)
    values (v_id, pe.tenant_id, p_periodo, v_coord, 'normal', v_id, auth.uid());
  else
    select * into raiz from public.inc_hojas where id = p_complemento_de and tipo = 'normal' and coordinador_id = v_coord and periodo_id = p_periodo;
    if raiz.id is null then raise exception 'BeeHuman: la hoja original no es tuya.'; end if;
    if raiz.estado not in ('enviada','procesada') then raise exception 'BeeHuman: la hoja original sigue abierta; corrígela directamente.'; end if;
    insert into public.inc_hojas (tenant_id, periodo_id, coordinador_id, tipo, hoja_raiz_id, posterior_procesamiento, creado_por)
    values (pe.tenant_id, p_periodo, v_coord, 'complemento', raiz.id, pe.procesado_en is not null, auth.uid())
    returning id into v_id;
  end if;
  return v_id;
end $$;
create or replace function public.inc_enviar_hoja(p_hoja uuid, p_observacion_general text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare h record; v_ver uuid; v_num int;
begin
  if not public.inc_es_mi_hoja(p_hoja) then raise exception 'BeeHuman: solo el coordinador de la hoja la envía.'; end if;
  select * into h from public.inc_hojas where id = p_hoja for update;
  if h.estado not in ('borrador','devuelta') then raise exception 'BeeHuman: la hoja ya fue enviada.'; end if;
  -- D2: una hoja normal nunca enviada, sin personal y sin capturas ni
  -- observaciones no se envía (no hay nada que reportar).
  if h.tipo = 'normal' and h.version_actual = 0 and coalesce(btrim(p_observacion_general), '') = ''
     and public.inc_hoja_vacia_sin_personal(p_hoja) then
    raise exception 'BeeHuman: no tienes personas asignadas en esta empresa durante el periodo; esta hoja no se envía y no bloquea el procesamiento.';
  end if;
  v_num := h.version_actual + 1;
  insert into public.inc_versiones (tenant_id, hoja_id, numero, creada_por, datos)
  values (h.tenant_id, p_hoja, v_num, auth.uid(), jsonb_build_object(
    'observacion_general', coalesce(p_observacion_general, h.observacion_general),
    'celdas', coalesce((select jsonb_agg(to_jsonb(c) - 'tenant_id' order by c.personal_id, c.fecha) from public.inc_celdas c where c.hoja_id = p_hoja), '[]'),
    'cantidades', coalesce((select jsonb_agg(to_jsonb(q) - 'tenant_id' order by q.personal_id, q.fecha) from public.inc_cantidades q where q.hoja_id = p_hoja), '[]'),
    'observaciones', coalesce((select jsonb_agg(jsonb_build_object('personal_id', o.personal_id, 'texto', o.texto)) from public.inc_observaciones o where o.hoja_id = p_hoja), '[]'),
    'conceptos', coalesce((select jsonb_agg(to_jsonb(k) - 'tenant_id') from public.inc_conceptos k join public.inc_periodos pe on pe.empresa_id = k.empresa_id where pe.id = h.periodo_id), '[]'),
    'tarifas_area', coalesce((select jsonb_agg(to_jsonb(t) - 'tenant_id') from public.inc_tarifas_area t join public.inc_conceptos k on k.id = t.concepto_id join public.inc_periodos pe on pe.empresa_id = k.empresa_id where pe.id = h.periodo_id), '[]'),
    'parametros', (select to_jsonb(x) - 'tenant_id' from public.inc_parametros x join public.inc_periodos pe on pe.empresa_id = x.empresa_id where pe.id = h.periodo_id)))
  returning id into v_ver;
  update public.inc_hojas set estado = 'enviada', version_actual = v_num,
         observacion_general = coalesce(p_observacion_general, observacion_general) where id = p_hoja;
  insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre)
  values (h.tenant_id, p_hoja, h.periodo_id, v_ver, case when h.tipo = 'complemento' then 'complemento' else 'envio' end,
          auth.uid(), public.inc_nombre_usuario());
  perform public.inc_calcular_version(v_ver);
  return v_ver;
end $function$;

create or replace function public.inc_faltantes_procesar(p_periodo uuid)
returns table (tipo text, detalle text)
language plpgsql stable security definer set search_path to '' as $$
#variable_conflict use_column
declare pe record; prm record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  select * into prm from public.inc_parametros x where x.empresa_id = pe.empresa_id;
  return query
  select f.tipo, f.detalle from (
    select 1 as orden, 'hoja'::text as tipo, t.coordinador || ': ' || case t.estado
             when 'sin_abrir' then 'no ha abierto su hoja' when 'borrador' then 'no ha enviado su hoja'
             else 'su hoja está devuelta y no la ha reenviado' end as detalle
      from public.inc_tablero_periodo(p_periodo) t where t.estado in ('sin_abrir','borrador','devuelta')
       -- Corrección D2 (16-nov): no bloquea una hoja normal en borrador, nunca
       -- enviada, cuyo coordinador no tiene personal en el periodo y que no tiene
       -- ninguna captura ni observación.
       and not (t.estado = 'borrador' and coalesce(t.version_actual, 0) = 0 and t.hoja_id is not null
                and public.inc_hoja_vacia_sin_personal(t.hoja_id))
    union all
    select 1, 'hoja', co.nombre_completo || ': tiene un complemento ' || case h.estado when 'borrador' then 'sin enviar' else 'devuelto sin reenviar' end
      from public.inc_hojas h join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.tipo = 'complemento' and h.estado in ('borrador','devuelta')
    union all
    select 2, 'importe', p.nombre_completo || ' · ' || k.nombre || ': ' ||
             case i.origen when 'sin_sueldo' then 'sin sueldo (captura el sueldo diario manual o escribe el importe)'
                           when 'por_asignar' then 'esquema de pago por asignar'
                           else 'importe por decidir' end
             || ' — hoja de ' || co.nombre_completo
      from public.inc_importes i
      join public.inc_versiones v on v.id = i.version_id
      join public.inc_hojas h on h.id = v.hoja_id and v.numero = h.version_actual
      join public.personal p on p.id = i.personal_id
      join public.inc_conceptos k on k.id = i.concepto_id
      join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.estado = 'enviada' and i.origen in ('pendiente','sin_sueldo','por_asignar')
    union all
    -- B5: descuentos de créditos por decidir, que exceden el saldo o sin generar
    select 2, 'descuento', p.nombre_completo || ' · ' || public.cred_etiqueta(c) || ': ' ||
             case when d.origen = 'pendiente' then 'descuento por decidir'
                  else 'el descuento ($' || to_char(d.final, 'FM999,999,990.00') || ') excede el saldo disponible del crédito ($'
                       || to_char(greatest(public.cred_disponible(c.id, pe.id), 0), 'FM999,999,990.00') || ')' end
      from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id join public.personal p on p.id = d.personal_id
     where d.periodo_id = pe.id and (d.origen = 'pendiente'
            or (d.origen in ('aceptado','modificado') and c.monto_total is not null and d.final > public.cred_disponible(c.id, pe.id)))
    union all
    select 2, 'descuento', p.nombre_completo || ' · ' || public.cred_etiqueta(c) || ': descuento del periodo sin revisar (abre «Descuentos del periodo»)'
      from public.cred_propuestas(pe.id) x join public.cred_creditos c on c.id = x.credito_id join public.personal p on p.id = x.personal_id
     where pe.procesado_en is null
       and not exists (select 1 from public.cred_descuentos d where d.periodo_id = pe.id and d.credito_id = x.credito_id and d.origen <> 'descartado')
    union all
    select 3, 'firma', 'Designa al responsable de Nómina (Incidencias → Configuración): su firma es obligatoria para procesar'
     where prm.responsable_nomina_user is null
       and exists (select 1 from public.inc_hojas h where h.periodo_id = pe.id and h.estado = 'enviada')
    union all
    select 3, 'firma', co.nombre_completo || ': falta la firma de ' || a.nombre || ' (versión ' || h.version_actual || ')'
      from public.inc_hojas h
      join public.inc_versiones v on v.hoja_id = h.id and v.numero = h.version_actual
      join public.personal co on co.id = h.coordinador_id
      cross join (values ('nomina', 'Nómina', prm.responsable_nomina_user), ('rh', 'RH', prm.responsable_rh_user)) a(area, nombre, resp)
     where h.periodo_id = pe.id and h.estado = 'enviada' and a.resp is not null
       and not exists (select 1 from public.inc_eventos e where e.version_id = v.id and e.tipo = 'firma_' || a.area)
  ) f
  order by f.orden, f.detalle;
end $$;

-- ---------------------------------------------------------------------
-- 3. Permisos de funciones
-- ---------------------------------------------------------------------
revoke all on function public.inc_coordinador_tiene_personal(uuid, uuid), public.inc_hoja_vacia_sin_personal(uuid)
  from public, anon, authenticated;
-- inc_periodo_visible la evalúa la política con el rol del usuario: necesita EXECUTE.
revoke all on function public.inc_periodo_visible(uuid), public.inc_empresas_visibles() from public, anon;
grant execute on function public.inc_periodo_visible(uuid), public.inc_empresas_visibles() to authenticated;
commit;
