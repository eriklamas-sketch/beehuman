-- =====================================================================
-- BeeHuman · Fase 2 · B2: incidencias conectadas con la relación laboral
-- y con los esquemas de pago (12-nov-2026). Solo beehuman-pruebas.
--
-- Antes (Ola 1): la hoja tomaba a la persona por la empresa y la baja de la
-- ficha, y el importe usaba un «sueldo diario» que sumaba todos los esquemas
-- activos de la persona (de cualquier empresa, bruto con neto).
--
-- Ahora:
--   1. Una persona entra a la hoja (y se le puede capturar) el día D solo si
--      tiene una relación laboral vigente ese día con la empresa del periodo.
--      Cada renglón capturado guarda esa relación (relacion_laboral_id).
--      Vigente el día D: no anulada, ingreso <= D (ingreso desconocido de un
--      dato migrado = sin límite inferior) y, si tiene baja, D <= baja.
--      Si la persona tiene dos relaciones vigentes con la misma empresa ese día
--      (p. ej. una con registro patronal y otra sin él), se guarda la que
--      tiene registro patronal; después, la de ingreso más reciente.
--   2. Los importes que dependen del sueldo se calculan POR ESQUEMA DE PAGO:
--      una línea por esquema, con su relación, modalidad (bruto/neto) y
--      clasificación. Solo cuentan los esquemas enlazados a una relación de
--      esa persona con la empresa del periodo y vigentes el día de la
--      incidencia. Bruto y neto nunca se suman. La base de la empresa filtra
--      (mixto = todos, bruto = solo brutos, neto = solo netos).
--      Días sin esquema: sueldo manual de Nómina si existe; si no, una línea
--      «sin_sueldo» (no se inventa sueldo).
--   3. Los importes por tarifa, descuento o sin importe quedan en una línea
--      por relación (sin esquema).
--   4. authenticated recibe DELETE en inc_celdas, inc_cantidades,
--      inc_observaciones e inc_tarifas_area (las políticas ya limitan quién y
--      cuándo; faltaba el permiso y vaciar una captura fallaba).
--   5. Una línea de importe que deja de aplicar al recalcular no se borra
--      (los importes no se borran): queda con origen «descartado».
-- No cambia el flujo (envío, devolución, firmas, procesado, complementos) ni
-- las pantallas existentes; inc_personas_hoja agrega una columna al final.
-- Originales en respaldo.b2_incidencias_20261112.
-- Reversión: supabase/reversion/20261112000000_reversion_b2_incidencias_relacion_esquemas.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.b2_incidencias_20261112') is not null then
    raise exception 'BeeHuman: la migración B2 ya está aplicada.';
  end if;
  if to_regclass('public.inc_hojas') is null or to_regclass('public.relaciones_laborales') is null then
    raise exception 'BeeHuman: B2 requiere la Ola 1 y la fase 1 (relaciones laborales).';
  end if;
  if to_regprocedure('public.inc_sueldo_diario(uuid,uuid,text)') is null then
    raise exception 'BeeHuman: inc_sueldo_diario no existe; la Ola 1 no es la versión esperada.';
  end if;
end $$;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
create table respaldo.b2_incidencias_20261112 (objeto text primary key, original text not null);
insert into respaldo.b2_incidencias_20261112 (objeto, original)
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array[
    'public.inc_validar_captura()', 'public.inc_personas_hoja(uuid)',
    'public.inc_calcular_version(uuid)', 'public.inc_sueldo_diario(uuid,uuid,text)']) x;
revoke all on table respaldo.b2_incidencias_20261112 from public;

-- ---------------------------------------------------------------------
-- 1. Columnas nuevas
-- ---------------------------------------------------------------------
alter table public.inc_celdas     add column relacion_laboral_id uuid references public.relaciones_laborales(id);
alter table public.inc_cantidades add column relacion_laboral_id uuid references public.relaciones_laborales(id);

alter table public.inc_importes add column relacion_laboral_id uuid references public.relaciones_laborales(id);
alter table public.inc_importes add column registro_pago_id    uuid references public.personal_registros_pago(id);
alter table public.inc_importes add column modalidad           text check (modalidad is null or modalidad in ('bruto','neto','manual'));
alter table public.inc_importes drop constraint inc_importes_origen_check;
alter table public.inc_importes add constraint inc_importes_origen_check
  check (origen in ('pendiente','aceptado','modificado','sin_sueldo','sin_importe','descartado'));
alter table public.inc_importes drop constraint inc_importes_version_id_personal_id_concepto_id_key;
create unique index inc_importes_linea_uq on public.inc_importes (version_id, personal_id, concepto_id,
  coalesce(relacion_laboral_id, '00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(registro_pago_id,    '00000000-0000-0000-0000-000000000000'::uuid));
comment on column public.inc_importes.registro_pago_id is 'Esquema de pago del que sale el importe (null: tarifa, descuento, sin importe, sueldo manual o sin sueldo).';
comment on column public.inc_importes.modalidad is 'bruto / neto del esquema, o manual (sueldo capturado por Nómina). Bruto y neto nunca se suman.';

-- ---------------------------------------------------------------------
-- 2. Relación vigente y esquemas de un día
-- ---------------------------------------------------------------------
create function public.inc_relacion_en(p_personal uuid, p_empresa uuid, p_fecha date) returns uuid
language sql stable security definer set search_path to '' as $$
  select rl.id from public.relaciones_laborales rl
   where rl.personal_id = p_personal and rl.empresa_id = p_empresa and rl.estado <> 'anulada'
     and coalesce(rl.fecha_ingreso, '-infinity'::date) <= p_fecha
     and ((rl.estado = 'vigente' and rl.fecha_baja is null) or p_fecha <= rl.fecha_baja)
   order by (rl.registro_patronal_id is not null) desc, rl.fecha_ingreso desc nulls last, rl.creado_en desc
   limit 1
$$;
comment on function public.inc_relacion_en(uuid,uuid,date) is
  'BeeHuman: relación laboral vigente de la persona con la empresa ese día (con registro patronal primero). Null si no tiene.';

-- Esquemas que pagan a la persona ese día en esa empresa (uno por renglón).
create function public.inc_esquemas_dia(p_personal uuid, p_empresa uuid, p_fecha date, p_base text)
returns table (registro_pago_id uuid, relacion_laboral_id uuid, modalidad text, clasificacion text, sueldo_diario numeric)
language sql stable security definer set search_path to '' as $$
  select r.id, r.relacion_laboral_id, r.modalidad_sueldo, c.nombre,
         r.sueldo / coalesce(nullif(r.dias_periodo, 0), nullif(pz.dias_default, 0))
    from public.personal_registros_pago r
    join public.relaciones_laborales rl on rl.id = r.relacion_laboral_id
    join public.periodicidades pz on pz.id = r.periodicidad_id
    left join public.clasificaciones_personal c on c.id = r.clasificacion_id
   where r.personal_id = p_personal and rl.empresa_id = p_empresa and rl.estado <> 'anulada'
     and coalesce(rl.fecha_ingreso, '-infinity'::date) <= p_fecha
     and ((rl.estado = 'vigente' and rl.fecha_baja is null) or p_fecha <= rl.fecha_baja)
     and r.fecha_inicio <= p_fecha
     and p_fecha <= coalesce(r.fecha_fin, case when r.activo then 'infinity'::date end)
     and (p_base = 'mixto' or r.modalidad_sueldo = p_base)
     and coalesce(nullif(r.dias_periodo, 0), nullif(pz.dias_default, 0)) is not null
   order by r.modalidad_sueldo, c.nombre, r.id
$$;

-- ---------------------------------------------------------------------
-- 3. Validación de la captura: relación vigente en vez de la ficha
-- ---------------------------------------------------------------------
create or replace function public.inc_validar_captura() returns trigger
language plpgsql security definer set search_path to '' as $$
declare h record; pe record; c record; v_rel uuid;
begin
  if tg_op = 'DELETE' then
    if not public.inc_hoja_editable(old.hoja_id) then
      raise exception 'BeeHuman: la hoja ya fue enviada; corrige con devolución o complemento.';
    end if;
    return old;
  end if;
  select * into h from public.inc_hojas where id = new.hoja_id;
  if h.estado not in ('borrador','devuelta') then
    raise exception 'BeeHuman: la hoja ya fue enviada; corrige con devolución o complemento.';
  end if;
  select * into pe from public.inc_periodos where id = h.periodo_id;
  new.tenant_id := h.tenant_id; new.hoja_raiz_id := h.hoja_raiz_id;
  new.periodo_id := h.periodo_id; new.es_normal := (h.tipo = 'normal');
  if new.fecha < pe.inicio or new.fecha > pe.fin then
    raise exception 'BeeHuman: la fecha % está fuera del periodo.', new.fecha;
  end if;
  v_rel := public.inc_relacion_en(new.personal_id, pe.empresa_id, new.fecha);
  if v_rel is null then
    raise exception 'BeeHuman: la persona no tiene relación laboral vigente con la empresa del periodo el %.', new.fecha;
  end if;
  new.relacion_laboral_id := v_rel;
  if public.inc_coordinador_en(new.personal_id, new.fecha) is distinct from h.coordinador_id then
    raise exception 'BeeHuman: la persona no estaba asignada a este coordinador el %.', new.fecha;
  end if;
  if tg_table_name = 'inc_cantidades' then
    select * into c from public.inc_conceptos where id = new.concepto_id;
    if c.empresa_id is distinct from pe.empresa_id or not c.activo then
      raise exception 'BeeHuman: el concepto no está activo para esta empresa.';
    end if;
    if c.tipo = 'descuento' and length(trim(coalesce(new.motivo,''))) = 0 then
      raise exception 'BeeHuman: el descuento operativo requiere motivo.';
    end if;
    if new.tipo_linea = 'ajuste' and h.tipo <> 'complemento' then
      raise exception 'BeeHuman: los ajustes solo van en un complemento.';
    end if;
    if coalesce(new.conformidad_declarada, false) and (tg_op = 'INSERT' or not coalesce(old.conformidad_declarada, false)) then
      new.conformidad_por := auth.uid(); new.conformidad_en := now();
    end if;
  end if;
  return new;
end $$;

-- ---------------------------------------------------------------------
-- 4. Personas de la hoja: por relación vigente cada día
-- ---------------------------------------------------------------------
drop function public.inc_personas_hoja(uuid);
create function public.inc_personas_hoja(p_hoja uuid)
returns table (personal_id uuid, nombre_completo text, empleado_id text, area_id uuid, proyecto_id uuid,
               centro_costo_id uuid, fecha date, relacion_laboral_id uuid)
language sql stable security definer set search_path to '' as $$
  select p.id, p.nombre_completo, p.empleado_id, p.area_id, p.proyecto_id, p.centro_costo_id, d::date, x.rid
  from public.inc_hojas h
  join public.inc_periodos pe on pe.id = h.periodo_id
  cross join generate_series(pe.inicio, pe.fin, interval '1 day') d
  join public.inc_asignaciones a on a.coordinador_id = h.coordinador_id
       and d::date >= a.desde and (a.hasta is null or d::date <= a.hasta)
  join public.personal p on p.id = a.personal_id
  cross join lateral (select public.inc_relacion_en(p.id, pe.empresa_id, d::date) as rid) x
  where h.id = p_hoja and x.rid is not null
    and (public.inc_es_mi_hoja(p_hoja) or public.tiene_rol('administrador','nomina'))
  order by p.nombre_completo, d
$$;

-- ---------------------------------------------------------------------
-- 5. Cálculo por esquema de pago
-- ---------------------------------------------------------------------
drop function public.inc_sueldo_diario(uuid,uuid,text);

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
        final = case when public.inc_importes.origen = 'modificado' then public.inc_importes.final else excluded.final end,
        origen = case when public.inc_importes.origen = 'modificado' then 'modificado' else excluded.origen end,
        usa_sueldo = excluded.usa_sueldo, base_calculo = excluded.base_calculo, detalle = excluded.detalle;

  -- Líneas que ya no aplican (p. ej. cambió el esquema): no se borran.
  update public.inc_importes i set origen = 'descartado', final = null,
         detalle = i.detalle || jsonb_build_object('descartado_en', now())
   where i.version_id = p_version and i.origen not in ('modificado','descartado')
     and not exists (select 1 from _inc_lineas x
                      where x.pid = i.personal_id and x.cid = i.concepto_id
                        and x.rid is not distinct from i.relacion_laboral_id and x.rp is not distinct from i.registro_pago_id);
end $$;

-- ---------------------------------------------------------------------
-- 6. Relación en la captura que ya existe (sin disparadores: no es una edición)
-- ---------------------------------------------------------------------
alter table public.inc_celdas disable trigger user;
alter table public.inc_cantidades disable trigger user;
update public.inc_celdas c set relacion_laboral_id = public.inc_relacion_en(c.personal_id, pe.empresa_id, c.fecha)
  from public.inc_periodos pe where pe.id = c.periodo_id and c.relacion_laboral_id is null;
update public.inc_cantidades q set relacion_laboral_id = public.inc_relacion_en(q.personal_id, pe.empresa_id, q.fecha)
  from public.inc_periodos pe where pe.id = q.periodo_id and q.relacion_laboral_id is null;
alter table public.inc_celdas enable trigger user;
alter table public.inc_cantidades enable trigger user;

-- ---------------------------------------------------------------------
-- 7. Permisos
-- ---------------------------------------------------------------------
grant delete on public.inc_celdas, public.inc_cantidades, public.inc_observaciones, public.inc_tarifas_area to authenticated;
revoke all on function public.inc_relacion_en(uuid,uuid,date) from public, anon, authenticated;
revoke all on function public.inc_esquemas_dia(uuid,uuid,date,text) from public, anon, authenticated;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;
revoke all on function public.inc_personas_hoja(uuid) from public, anon;
grant execute on function public.inc_personas_hoja(uuid) to authenticated;

commit;
