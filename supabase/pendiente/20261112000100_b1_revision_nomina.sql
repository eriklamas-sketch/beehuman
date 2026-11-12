-- =====================================================================
-- BeeHuman · Fase 2 · B1: revisión de Nómina (12-nov-2026). Solo beehuman-pruebas.
-- La pantalla de revisión usa las funciones de la Ola 1 (devolver, firmar,
-- decidir importe, sueldo manual, procesado). Esta migración agrega lo mínimo
-- que la pantalla necesita del servidor:
--   1. inc_tablero_periodo: una fila por coordinador con gente en la empresa
--      del periodo (según B2: relación vigente), aunque todavía no abra su
--      hoja: personas, estado, versión, envío, firmas de la versión vigente,
--      complementos y devoluciones. Solo Administrador y Nómina.
--   2. inc_aceptar_sugeridos: acepta de una vez los importes «pendiente» con
--      sugerencia de la versión vigente. No toca modificados, sin sueldo,
--      sin importe ni descartados.
--   3. inc_decidir_importe: misma función con tres candados nuevos: solo la
--      versión vigente de una hoja enviada (no devuelta ni procesada), y no
--      se deciden líneas «descartado» ni «sin_importe».
--   4. inc_calcular_version (de B2): al recalcular (p. ej. por un sueldo
--      manual) también respeta lo ACEPTADO por Nómina mientras el sugerido no
--      cambie; antes solo respetaba lo modificado y lo aceptado volvía a
--      «pendiente». Es el único cambio a esa función.
--   5. Procesar el periodo exige la prenómina completa (decisión de Erik,
--      12-nov): inc_faltantes_procesar lista exactamente qué falta, e
--      inc_marcar_procesado se niega mientras falte algo. No hay forma de
--      saltarse la regla. Falta algo si:
--        - un coordinador con gente en la empresa no abrió, no envió o tiene
--          devuelta su hoja, o hay un complemento sin enviar o devuelto;
--        - un importe de la versión vigente está «por decidir» o «sin sueldo»
--          (debe quedar aceptado o modificado);
--        - falta la firma de Nómina en una hoja enviada (Nómina debe tener
--          responsable designado), o la de RH cuando la empresa designó
--          responsable de RH.
-- No cambia tablas ni datos. Originales de inc_decidir_importe,
-- inc_calcular_version e inc_marcar_procesado en respaldo.b1_revision_20261112.
-- Reversión: supabase/reversion/20261112000100_reversion_b1_revision_nomina.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.b1_revision_20261112') is not null then
    raise exception 'BeeHuman: la migración B1 ya está aplicada.';
  end if;
  if to_regprocedure('public.inc_relacion_en(uuid,uuid,date)') is null then
    raise exception 'BeeHuman: B1 requiere B2 (20261112000000).';
  end if;
end $$;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
create table respaldo.b1_revision_20261112 (objeto text primary key, original text not null);
insert into respaldo.b1_revision_20261112 values
  ('public.inc_decidir_importe(uuid,numeric)', pg_get_functiondef('public.inc_decidir_importe(uuid,numeric)'::regprocedure)),
  ('public.inc_calcular_version(uuid)', pg_get_functiondef('public.inc_calcular_version(uuid)'::regprocedure)),
  ('public.inc_marcar_procesado(uuid)', pg_get_functiondef('public.inc_marcar_procesado(uuid)'::regprocedure));
revoke all on table respaldo.b1_revision_20261112 from public;

-- 1. Tablero del periodo ----------------------------------------------------
create function public.inc_tablero_periodo(p_periodo uuid)
returns table (coordinador_id uuid, coordinador text, personas integer, hoja_id uuid, estado text, version_actual integer,
               enviada_en timestamptz, firma_nomina boolean, firma_rh boolean, complementos integer,
               devoluciones integer, ultimo_motivo text)
language plpgsql stable security definer set search_path to '' as $$
#variable_conflict use_column
declare pe record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  return query
  with asign as (
    select a.coordinador_id as cid, count(distinct a.personal_id) filter (where exists (
             select 1 from generate_series(greatest(a.desde, pe.inicio), least(coalesce(a.hasta, pe.fin), pe.fin), interval '1 day') d
              where public.inc_relacion_en(a.personal_id, pe.empresa_id, d::date) is not null)) as n
      from public.inc_asignaciones a
     where a.tenant_id = pe.tenant_id and a.desde <= pe.fin and (a.hasta is null or a.hasta >= pe.inicio)
     group by a.coordinador_id
  ), c as (
    select x.cid, max(x.n)::integer as n from (
      select asign.cid, asign.n from asign
      union all
      select h0.coordinador_id, 0 from public.inc_hojas h0 where h0.periodo_id = pe.id
    ) x group by x.cid
  )
  select c.cid, p.nombre_completo, c.n, h.id, coalesce(h.estado, 'sin_abrir'), coalesce(h.version_actual, 0),
         (select max(e.creado_en) from public.inc_eventos e where e.hoja_id = h.id and e.tipo = 'envio'),
         exists (select 1 from public.inc_eventos e join public.inc_versiones v on v.id = e.version_id
                  where e.hoja_id = h.id and v.numero = h.version_actual and e.tipo = 'firma_nomina'),
         exists (select 1 from public.inc_eventos e join public.inc_versiones v on v.id = e.version_id
                  where e.hoja_id = h.id and v.numero = h.version_actual and e.tipo = 'firma_rh'),
         (select count(*) from public.inc_hojas x where x.hoja_raiz_id = h.id and x.tipo = 'complemento')::integer,
         (select count(*) from public.inc_eventos e where e.hoja_id = h.id and e.tipo = 'devolucion')::integer,
         (select e.motivo from public.inc_eventos e where e.hoja_id = h.id and e.tipo = 'devolucion' order by e.creado_en desc limit 1)
    from c
    join public.personal p on p.id = c.cid
    left join public.inc_hojas h on h.periodo_id = pe.id and h.coordinador_id = c.cid and h.tipo = 'normal'
   where c.n > 0 or h.id is not null
   order by p.nombre_completo;
end $$;

-- 2. Aceptar sugeridos de una versión ----------------------------------------
create function public.inc_aceptar_sugeridos(p_version uuid)
returns integer language plpgsql security definer set search_path to '' as $$
declare n integer;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  if not exists (select 1 from public.inc_versiones v join public.inc_hojas h on h.id = v.hoja_id
                  where v.id = p_version and v.tenant_id = public.current_tenant_id()
                    and v.numero = h.version_actual and h.estado = 'enviada') then
    raise exception 'BeeHuman: solo se deciden importes de la versión vigente de una hoja enviada.';
  end if;
  update public.inc_importes i
     set final = i.sugerido, origen = 'aceptado', decidido_por = auth.uid(), decidido_en = now()
   where i.version_id = p_version and i.origen = 'pendiente' and i.sugerido is not null;
  get diagnostics n = row_count;
  return n;
end $$;

-- 3. Decidir un importe, con candados ----------------------------------------
create or replace function public.inc_decidir_importe(p_importe uuid, p_final numeric)
returns void language plpgsql security definer set search_path to '' as $$
declare i record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into i from public.inc_importes where id = p_importe and tenant_id = public.current_tenant_id() for update;
  if i.id is null then raise exception 'BeeHuman: importe no encontrado.'; end if;
  if not exists (select 1 from public.inc_versiones v join public.inc_hojas h on h.id = v.hoja_id
                  where v.id = i.version_id and v.numero = h.version_actual and h.estado = 'enviada') then
    raise exception 'BeeHuman: solo se deciden importes de la versión vigente de una hoja enviada.';
  end if;
  if i.origen in ('descartado','sin_importe') then
    raise exception 'BeeHuman: esta línea no lleva importe que decidir.';
  end if;
  if p_final is null and i.sugerido is null then raise exception 'BeeHuman: no hay sugerencia que aceptar.'; end if;
  if p_final is not null and p_final < 0 then raise exception 'BeeHuman: el importe no puede ser negativo.'; end if;
  update public.inc_importes
     set final = coalesce(round(p_final, 2), sugerido),
         origen = case when p_final is null or round(p_final,2) = sugerido then 'aceptado' else 'modificado' end,
         decidido_por = auth.uid(), decidido_en = now()
   where id = p_importe;
end $$;

-- 4. Recálculo que respeta lo aceptado ---------------------------------------
create or replace function public.inc_calcular_version(p_version uuid)
returns void language plpgsql security definer set search_path to '' as $$
declare
  ve record; h record; pe record; prm record; r record; l record;
  k jsonb; ta numeric; v_tarifa numeric; v_base text; v_jornada numeric; v_umbral numeric; v_ftriple numeric; v_pct numeric;
  v_manual numeric;
begin
  select * into ve from public.inc_versiones where id = p_version;
  select * into h  from public.inc_hojas where id = ve.hoja_id;
  select * into pe from public.inc_periodos where id = h.periodo_id;
  select * into prm from public.inc_parametros where empresa_id = pe.empresa_id;
  if prm.empresa_id is null then
    insert into public.inc_parametros (empresa_id, tenant_id) values (pe.empresa_id, pe.tenant_id) returning * into prm;
  end if;
  -- configuración congelada en la versión (no la vigente)
  v_base    := ve.datos->'parametros'->>'base_calculo';
  v_jornada := (ve.datos->'parametros'->>'jornada_horas')::numeric;
  v_umbral  := (ve.datos->'parametros'->>'umbral_triples_semana')::numeric;
  v_ftriple := (ve.datos->'parametros'->>'factor_triple')::numeric;
  v_pct     := (ve.datos->'parametros'->>'prima_dominical_pct')::numeric;

  create temp table if not exists _inc_lineas (
    pid uuid, cid uuid, rid uuid, rp uuid, modalidad text, cant numeric, sug numeric, usa boolean, origen text, det jsonb
  ) on commit drop;
  delete from _inc_lineas;

  -- Días capturados con su relación (la guardada al capturar; si la versión es
  -- anterior a B2, la vigente ese día).
  create temp table if not exists _inc_dias (pid uuid, cid uuid, f date, cant numeric, rid uuid) on commit drop;
  delete from _inc_dias;
  insert into _inc_dias
  select (q->>'personal_id')::uuid, (q->>'concepto_id')::uuid, (q->>'fecha')::date, (q->>'cantidad')::numeric,
         coalesce((q->>'relacion_laboral_id')::uuid,
                  public.inc_relacion_en((q->>'personal_id')::uuid, pe.empresa_id, (q->>'fecha')::date))
    from jsonb_array_elements(ve.datos->'cantidades') q;

  for r in select pid, cid from _inc_dias group by 1, 2 loop
    select c into k from jsonb_array_elements(ve.datos->'conceptos') c where (c->>'id')::uuid = r.cid;
    select (t->>'tarifa')::numeric into ta from jsonb_array_elements(ve.datos->'tarifas_area') t
      where (t->>'concepto_id')::uuid = r.cid
        and (t->>'area_id')::uuid = (select area_id from public.personal where id = r.pid);

    if k->>'modo' = 'sin_importe' then
      insert into _inc_lineas select r.pid, r.cid, d.rid, null, null, sum(d.cant), null, false, 'sin_importe', '{}'::jsonb
        from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid;
    elsif k->>'tipo' = 'descuento' then
      insert into _inc_lineas select r.pid, r.cid, d.rid, null, null, sum(d.cant), round(sum(d.cant), 2), false, 'pendiente',
             jsonb_build_object('regla','descuento_operativo')
        from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid;
    elsif k->>'modo' = 'tarifa' or (k->>'tipo' = 'domingo' and (ta is not null or k->>'tarifa' is not null)) then
      v_tarifa := coalesce(ta, (k->>'tarifa')::numeric);
      insert into _inc_lineas select r.pid, r.cid, d.rid, null, null, sum(d.cant), round(sum(d.cant) * v_tarifa, 2), false, 'aceptado',
             jsonb_build_object('regla', case when ta is not null then 'tarifa_area' else 'tarifa_empresa' end, 'tarifa', v_tarifa)
        from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid;
    else
      -- modo beehuman: depende del sueldo de cada esquema que paga ese día.
      -- Horas extra: las primeras «umbral» horas de la semana son dobles y el
      -- resto triples, en orden de fecha; cada día conserva sus dobles/triples.
      v_manual := (select m.sueldo_diario from public.inc_sueldos_manuales m where m.periodo_id = pe.id and m.personal_id = r.pid);
      for l in
        with dias as (
          select d.f, d.rid, sum(d.cant) cant from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.f, d.rid
        ), acum as (
          select x.*, coalesce(sum(x.cant) over (partition by date_trunc('week', x.f) order by x.f
                                                 rows between unbounded preceding and 1 preceding), 0) previas
            from dias x
        ), partes as (
          select a.f, a.rid, a.cant,
                 case when k->>'tipo' = 'horas_extra' then greatest(least(a.cant, v_umbral - a.previas), 0) else a.cant end dobles,
                 case when k->>'tipo' = 'horas_extra' then a.cant - greatest(least(a.cant, v_umbral - a.previas), 0) else 0 end triples
            from acum a
        ), con_esquema as (
          select p.*, e.registro_pago_id rp, e.relacion_laboral_id rid_esq, e.modalidad, e.clasificacion, e.sueldo_diario sd
            from partes p
            left join lateral public.inc_esquemas_dia(r.pid, pe.empresa_id, p.f, v_base) e on true
        )
        select coalesce(rid_esq, rid) rid, rp,
               case when rp is not null then modalidad when v_manual is not null then 'manual' end modalidad,
               max(clasificacion) clasificacion,
               sum(cant) cant, sum(dobles) dobles, sum(triples) triples,
               min(coalesce(sd, v_manual)) sd_min, max(coalesce(sd, v_manual)) sd_max,
               sum(case
                     when coalesce(sd, v_manual) is null then null
                     when k->>'tipo' = 'horas_extra' then coalesce(sd, v_manual) / v_jornada
                          * (dobles * coalesce((k->>'factor')::numeric, 2) + triples * v_ftriple)
                     when k->>'tipo' = 'domingo' then cant * coalesce(sd, v_manual) * v_pct / 100
                     else cant * coalesce(sd, v_manual) * coalesce((k->>'factor')::numeric, 1)
                   end) importe,
               bool_and(coalesce(sd, v_manual) is not null) con_sueldo,
               jsonb_agg(f::text order by f) fechas
          from con_esquema
         group by coalesce(rid_esq, rid), rp,
                  case when rp is not null then modalidad when v_manual is not null then 'manual' end
      loop
        insert into _inc_lineas values (r.pid, r.cid, l.rid, l.rp, l.modalidad, l.cant,
          case when l.con_sueldo then round(l.importe, 2) end, true,
          case when l.con_sueldo then 'pendiente' else 'sin_sueldo' end,
          jsonb_strip_nulls(jsonb_build_object(
            'regla', case k->>'tipo' when 'horas_extra' then 'horas_extra' when 'domingo' then 'prima_dominical' else 'porcentaje_sueldo' end,
            'horas_dobles', case when k->>'tipo' = 'horas_extra' then l.dobles end,
            'horas_triples', case when k->>'tipo' = 'horas_extra' then l.triples end,
            'pct', case when k->>'tipo' = 'domingo' then v_pct end,
            'factor', case when k->>'tipo' not in ('horas_extra','domingo') then (k->>'factor')::numeric end,
            'clasificacion', l.clasificacion,
            'sueldo_diario', case when l.sd_min = l.sd_max then round(l.sd_min, 4) end,
            'fechas', l.fechas,
            'motivo', case when not l.con_sueldo then 'Sin esquema de pago enlazado a la relación de esta empresa en esas fechas' end)));
      end loop;
    end if;
  end loop;

  -- Escribir las líneas (un recálculo no pisa lo modificado por Nómina)
  insert into public.inc_importes (tenant_id, version_id, personal_id, concepto_id, relacion_laboral_id, registro_pago_id,
                                   modalidad, cantidad, sugerido, final, origen, usa_sueldo, base_calculo, detalle)
  select ve.tenant_id, p_version, x.pid, x.cid, x.rid, x.rp, x.modalidad, x.cant, x.sug,
         case when x.origen = 'aceptado' then x.sug end, x.origen, x.usa,
         case when x.usa then v_base end, x.det
    from _inc_lineas x
  on conflict (version_id, personal_id, concepto_id,
               coalesce(relacion_laboral_id, '00000000-0000-0000-0000-000000000000'::uuid),
               coalesce(registro_pago_id,    '00000000-0000-0000-0000-000000000000'::uuid)) do update
    set cantidad = excluded.cantidad, sugerido = excluded.sugerido, modalidad = excluded.modalidad,
        -- Lo decidido por Nómina se respeta: lo modificado siempre; lo aceptado,
        -- mientras el sugerido no cambie (si cambia, vuelve a «pendiente»).
        final = case when public.inc_importes.origen = 'modificado' then public.inc_importes.final
                     when public.inc_importes.origen = 'aceptado' and public.inc_importes.sugerido is not distinct from excluded.sugerido
                          and public.inc_importes.final is not null then public.inc_importes.final
                     else excluded.final end,
        origen = case when public.inc_importes.origen = 'modificado' then 'modificado'
                      when public.inc_importes.origen = 'aceptado' and public.inc_importes.sugerido is not distinct from excluded.sugerido
                           and public.inc_importes.final is not null then 'aceptado'
                      else excluded.origen end,
        usa_sueldo = excluded.usa_sueldo, base_calculo = excluded.base_calculo, detalle = excluded.detalle;

  -- Líneas que ya no aplican (p. ej. cambió el esquema): no se borran.
  update public.inc_importes i set origen = 'descartado', final = null,
         detalle = i.detalle || jsonb_build_object('descartado_en', now())
   where i.version_id = p_version and i.origen not in ('modificado','descartado')
     and not exists (select 1 from _inc_lineas x
                      where x.pid = i.personal_id and x.cid = i.concepto_id
                        and x.rid is not distinct from i.relacion_laboral_id and x.rp is not distinct from i.registro_pago_id);
end $$;

revoke all on function public.inc_tablero_periodo(uuid) from public, anon;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
revoke all on function public.inc_aceptar_sugeridos(uuid) from public, anon;
revoke all on function public.inc_decidir_importe(uuid,numeric) from public, anon;
grant execute on function public.inc_tablero_periodo(uuid), public.inc_aceptar_sugeridos(uuid),
  public.inc_decidir_importe(uuid,numeric) to authenticated;

-- 5. Procesar solo con la prenómina completa --------------------------------
create function public.inc_faltantes_procesar(p_periodo uuid)
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
    -- hojas normales: cada coordinador con gente en la empresa debe haber enviado
    select 1 as orden, 'hoja'::text as tipo, t.coordinador || ': ' || case t.estado
             when 'sin_abrir' then 'no ha abierto su hoja' when 'borrador' then 'no ha enviado su hoja'
             else 'su hoja está devuelta y no la ha reenviado' end as detalle
      from public.inc_tablero_periodo(p_periodo) t where t.estado in ('sin_abrir','borrador','devuelta')
    union all
    select 1, 'hoja', co.nombre_completo || ': tiene un complemento ' || case h.estado when 'borrador' then 'sin enviar' else 'devuelto sin reenviar' end
      from public.inc_hojas h join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.tipo = 'complemento' and h.estado in ('borrador','devuelta')
    union all
    -- importes de la versión vigente: aceptados o modificados
    select 2, 'importe', p.nombre_completo || ' · ' || k.nombre || ': ' ||
             case i.origen when 'sin_sueldo' then 'sin sueldo (captura el sueldo diario manual o escribe el importe)' else 'importe por decidir' end
             || ' — hoja de ' || co.nombre_completo
      from public.inc_importes i
      join public.inc_versiones v on v.id = i.version_id
      join public.inc_hojas h on h.id = v.hoja_id and v.numero = h.version_actual
      join public.personal p on p.id = i.personal_id
      join public.inc_conceptos k on k.id = i.concepto_id
      join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.estado = 'enviada' and i.origen in ('pendiente','sin_sueldo')
    union all
    -- firmas: Nómina siempre; RH si la empresa designó responsable
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

create or replace function public.inc_marcar_procesado(p_periodo uuid)
returns text language plpgsql security definer set search_path to '' as $$
declare pe record; v_falta text; v_n integer;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id() for update;
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  if pe.procesado_en is not null then
    return 'Ya estaba procesado el ' || to_char(pe.procesado_en, 'YYYY-MM-DD HH24:MI') || '; no se registró de nuevo.';
  end if;
  select count(*), string_agg(f.detalle, '; ') into v_n, v_falta from public.inc_faltantes_procesar(p_periodo) f;
  if v_n > 0 then
    raise exception 'BeeHuman: no se puede procesar; faltan % pendiente(s): %', v_n, left(v_falta, 1500);
  end if;
  update public.inc_periodos set procesado_en = now(), procesado_por = auth.uid() where id = p_periodo;
  update public.inc_hojas set estado = 'procesada' where periodo_id = p_periodo and estado = 'enviada';
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre)
  values (pe.tenant_id, p_periodo, 'procesado', auth.uid(), public.inc_nombre_usuario());
  return 'Periodo marcado como procesado.';
end $$;

revoke all on function public.inc_faltantes_procesar(uuid) from public, anon;
revoke all on function public.inc_marcar_procesado(uuid) from public, anon;
grant execute on function public.inc_faltantes_procesar(uuid), public.inc_marcar_procesado(uuid) to authenticated;

commit;
