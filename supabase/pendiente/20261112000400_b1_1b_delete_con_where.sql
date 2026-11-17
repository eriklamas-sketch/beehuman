-- =====================================================================
-- BeeHuman · Fase 2 · B1.1b: DELETE con WHERE en inc_calcular_version
-- (12-nov-2026). Solo beehuman-pruebas.
-- Defecto: en Supabase, el rol authenticator carga la extensión safeupdate,
-- que rechaza todo DELETE/UPDATE sin WHERE («DELETE requires a WHERE
-- clause»), también dentro de funciones. inc_calcular_version vacía sus
-- tablas temporales (_inc_lineas, _inc_dias, _inc_he) con DELETE sin WHERE
-- desde B2, así que enviar una hoja (y capturar un sueldo manual) desde la
-- aplicación fallaba y la transacción completa se revertía: la hoja quedaba
-- en borrador, sin escribir nada.
-- Corrección: las tres sentencias llevan «where true». Mismo efecto (solo
-- vacían las tablas temporales de la propia sesión); ninguna otra línea
-- cambia. No toca tablas ni datos.
-- Original en respaldo.b1_1b_delete_con_where_20261112.
-- Reversión: supabase/reversion/20261112000400_reversion_b1_1b_delete_con_where.sql
-- =====================================================================
begin;

do $$
declare d text := pg_get_functiondef('public.inc_calcular_version(uuid)'::regprocedure);
begin
  if to_regclass('respaldo.b1_1b_delete_con_where_20261112') is not null then
    raise exception 'BeeHuman: la migración B1.1b ya está aplicada.';
  end if;
  if to_regclass('respaldo.b1_1a_tarifa_por_decidir_20261112') is null then
    raise exception 'BeeHuman: B1.1b requiere B1.1a (20261112000300).';
  end if;
  if d not like '%B1.1a: asignar el esquema%' or d not like '%delete from _inc_lineas;%'
     or d not like '%delete from _inc_dias;%' or d not like '%delete from _inc_he;%' then
    raise exception 'BeeHuman: inc_calcular_version no es la versión esperada de B1.1a.';
  end if;
end $$;

create table respaldo.b1_1b_delete_con_where_20261112 (objeto text primary key, original text not null);
insert into respaldo.b1_1b_delete_con_where_20261112
  values ('public.inc_calcular_version(uuid)', pg_get_functiondef('public.inc_calcular_version(uuid)'::regprocedure));
revoke all on table respaldo.b1_1b_delete_con_where_20261112 from public;

create or replace function public.inc_calcular_version(p_version uuid)
returns void language plpgsql security definer set search_path to '' as $$
declare
  ve record; h record; pe record; prm record; r record; l record; e record;
  k jsonb; ta numeric; v_tarifa numeric; v_base text; v_jornada numeric; v_umbral numeric; v_ftriple numeric;
  v_fdoble numeric; v_fd numeric; v_pct numeric; v_manual numeric; v_he boolean; v_horas boolean;
  v_pref uuid; v_rp uuid; v_mod text; v_cls text; v_asig text; v_motivo text; v_n integer;
  v_dob numeric; v_tri numeric; v_imp numeric; v_origen text; v_man_rp uuid;
begin
  select * into ve from public.inc_versiones where id = p_version;
  select * into h  from public.inc_hojas where id = ve.hoja_id;
  if h.estado = 'procesada' then
    raise exception 'BeeHuman: el periodo ya se procesó; sus importes no se recalculan.';
  end if;
  select * into pe from public.inc_periodos where id = h.periodo_id;
  select * into prm from public.inc_parametros where empresa_id = pe.empresa_id;
  if prm.empresa_id is null then
    insert into public.inc_parametros (empresa_id, tenant_id) values (pe.empresa_id, pe.tenant_id) returning * into prm;
  end if;
  -- configuración congelada en la versión (no la vigente)
  v_base    := ve.datos->'parametros'->>'base_calculo';
  v_jornada := (ve.datos->'parametros'->>'jornada_horas')::numeric;
  v_umbral  := (ve.datos->'parametros'->>'umbral_triples_semana')::numeric;   -- null = sin triples
  v_ftriple := (ve.datos->'parametros'->>'factor_triple')::numeric;
  v_fdoble  := (ve.datos->'parametros'->>'factor_doble')::numeric;            -- null en versiones anteriores a B1.1
  v_pct     := (ve.datos->'parametros'->>'prima_dominical_pct')::numeric;

  create temp table if not exists _inc_lineas (
    pid uuid, cid uuid, rid uuid, rp uuid, modalidad text, cant numeric, sug numeric, usa boolean, origen text, det jsonb
  ) on commit drop;
  delete from _inc_lineas where true;   -- B1.1b: Supabase (safeupdate) rechaza DELETE sin WHERE

  create temp table if not exists _inc_dias (pid uuid, cid uuid, f date, cant numeric, rid uuid) on commit drop;
  delete from _inc_dias where true;   -- B1.1b: Supabase (safeupdate) rechaza DELETE sin WHERE
  insert into _inc_dias
  select (q->>'personal_id')::uuid, (q->>'concepto_id')::uuid, (q->>'fecha')::date, (q->>'cantidad')::numeric,
         coalesce((q->>'relacion_laboral_id')::uuid,
                  public.inc_relacion_en((q->>'personal_id')::uuid, pe.empresa_id, (q->>'fecha')::date))
    from jsonb_array_elements(ve.datos->'cantidades') q;

  -- Horas extra: dobles hasta el umbral de la SEMANA (lunes a domingo) y
  -- triples después, acumulando por persona todos los días y todos los
  -- conceptos de horas extra con importe, en orden de fecha y de columna.
  create temp table if not exists _inc_he (pid uuid, cid uuid, f date, rid uuid, cant numeric, dobles numeric, triples numeric) on commit drop;
  delete from _inc_he where true;   -- B1.1b: Supabase (safeupdate) rechaza DELETE sin WHERE
  insert into _inc_he
  with base as (
    select d.pid, d.cid, d.f, d.rid, sum(d.cant) cant, max(coalesce((c->>'orden')::integer, 0)) orden
      from _inc_dias d
      join lateral jsonb_array_elements(ve.datos->'conceptos') c on (c->>'id')::uuid = d.cid
     where c->>'tipo' = 'horas_extra' and c->>'modo' <> 'sin_importe'
     group by d.pid, d.cid, d.f, d.rid
  ), acum as (
    select b.*, coalesce(sum(b.cant) over (partition by b.pid, date_trunc('week', b.f::timestamp)
                                           order by b.f, b.orden, b.cid, b.rid
                                           rows between unbounded preceding and 1 preceding), 0) previas
      from base b
  )
  select a.pid, a.cid, a.f, a.rid, a.cant,
         case when v_umbral is null then a.cant else greatest(least(a.cant, v_umbral - a.previas), 0) end,
         case when v_umbral is null then 0 else a.cant - greatest(least(a.cant, v_umbral - a.previas), 0) end
    from acum a;

  for r in select pid, cid from _inc_dias group by 1, 2 loop
    select c into k from jsonb_array_elements(ve.datos->'conceptos') c where (c->>'id')::uuid = r.cid;
    select (t->>'tarifa')::numeric into ta from jsonb_array_elements(ve.datos->'tarifas_area') t
      where (t->>'concepto_id')::uuid = r.cid
        and (t->>'area_id')::uuid = (select area_id from public.personal where id = r.pid);
    v_he    := k->>'tipo' = 'horas_extra';
    v_horas := k->>'unidad' = 'horas' and k->>'tipo' not in ('horas_extra','domingo');
    v_fd    := coalesce(v_fdoble, (k->>'factor')::numeric, 2);

    if k->>'modo' = 'sin_importe' then
      insert into _inc_lineas select r.pid, r.cid, d.rid, null, null, sum(d.cant), null, false, 'sin_importe', '{}'::jsonb
        from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid;

    elsif k->>'tipo' = 'descuento' then
      insert into _inc_lineas select r.pid, r.cid, d.rid, null, null, sum(d.cant), round(sum(d.cant), 2), false, 'pendiente',
             jsonb_build_object('regla','descuento_operativo')
        from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid;

    elsif k->>'modo' = 'tarifa' or (k->>'tipo' = 'domingo' and (ta is not null or k->>'tarifa' is not null)) then
      -- Tarifa fija: un importe por relación, ligado a un esquema solo con certeza.
      v_tarifa := coalesce(ta, (k->>'tarifa')::numeric);
      v_pref   := (k->>'clasificacion_pago_id')::uuid;
      for l in select d.rid, sum(d.cant) cant, array_agg(distinct d.f order by d.f) fechas
                 from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.rid loop
        if v_he then
          select coalesce(sum(x.dobles), 0), coalesce(sum(x.triples), 0) into v_dob, v_tri
            from _inc_he x where x.pid = r.pid and x.cid = r.cid and x.rid is not distinct from l.rid;
          v_imp := v_tarifa * (v_dob * v_fd + v_tri * v_ftriple);
        else
          v_dob := null; v_tri := null; v_imp := l.cant * v_tarifa;
        end if;
        v_rp := null; v_mod := null; v_cls := null; v_asig := null; v_motivo := null;
        -- a) asignación manual de Nómina que sigue siendo válida
        select i.registro_pago_id into v_man_rp from public.inc_importes i
         where i.version_id = p_version and i.personal_id = r.pid and i.concepto_id = r.cid
           and i.relacion_laboral_id is not distinct from l.rid and i.esquema_asignado_por is not null
           and i.registro_pago_id is not null and i.origen <> 'descartado'
         order by i.esquema_asignado_en desc limit 1;
        if v_man_rp is not null then
          select * into e from public.inc_esquemas_vigentes(r.pid, pe.empresa_id, l.fechas, v_base) x where x.registro_pago_id = v_man_rp;
          if e.registro_pago_id is not null then v_rp := e.registro_pago_id; v_mod := e.modalidad; v_cls := e.clasificacion; v_asig := 'manual'; end if;
        end if;
        if v_rp is null then
          select count(*) into v_n from public.inc_esquemas_vigentes(r.pid, pe.empresa_id, l.fechas, v_base) x
           where v_pref is null or x.clasificacion_id = v_pref;
          if v_n = 1 then
            select * into e from public.inc_esquemas_vigentes(r.pid, pe.empresa_id, l.fechas, v_base) x
             where v_pref is null or x.clasificacion_id = v_pref;
            v_rp := e.registro_pago_id; v_mod := e.modalidad; v_cls := e.clasificacion;
            v_asig := case when v_pref is null then 'unico' else 'preferido' end;
          else
            v_motivo := case
              when v_pref is not null and v_n = 0 then 'La persona no tiene un esquema de la clasificación preferida vigente en esas fechas'
              when v_pref is not null then 'La persona tiene ' || v_n || ' esquemas de la clasificación preferida; Nómina elige'
              when v_n = 0 then 'La persona no tiene esquemas de pago vigentes en esta empresa en esas fechas'
              else 'La persona tiene ' || v_n || ' esquemas de pago vigentes; Nómina elige' end;
          end if;
        end if;
        -- B1.1a: asignar el esquema (dónde se paga) no es aceptar el importe (cuánto):
        -- toda línea con esquema nace «por decidir»; sin esquema, «por asignar».
        v_origen := case when v_rp is null then 'por_asignar' else 'pendiente' end;
        insert into _inc_lineas values (r.pid, r.cid, l.rid, v_rp, v_mod, l.cant, round(v_imp, 2), false, v_origen,
          jsonb_strip_nulls(jsonb_build_object(
            'regla', case when ta is not null then 'tarifa_area' else 'tarifa_empresa' end,
            'tarifa', v_tarifa,
            'origen_valor', 'tarifa',
            'valor_hora', case when v_he or v_horas then v_tarifa end,
            'horas_dobles', v_dob, 'horas_triples', v_tri,
            'factor_doble', case when v_he then v_fd end, 'factor_triple', case when v_he then v_ftriple end,
            'umbral_semana', case when v_he then v_umbral end,
            'clasificacion', v_cls, 'asignacion', v_asig,
            'fechas', to_jsonb(l.fechas::text[]),
            'motivo', v_motivo)));
      end loop;

    else
      -- Del sueldo: una línea por esquema que paga cada día (B2).
      v_manual := (select m.sueldo_diario from public.inc_sueldos_manuales m where m.periodo_id = pe.id and m.personal_id = r.pid);
      for l in
        with dias as (
          select d.f, d.rid, sum(d.cant) cant from _inc_dias d where d.pid = r.pid and d.cid = r.cid group by d.f, d.rid
        ), partes as (
          select x.f, x.rid, x.cant,
                 case when v_he then coalesce((select sum(he.dobles)  from _inc_he he where he.pid = r.pid and he.cid = r.cid and he.f = x.f and he.rid is not distinct from x.rid), 0) else x.cant end dobles,
                 case when v_he then coalesce((select sum(he.triples) from _inc_he he where he.pid = r.pid and he.cid = r.cid and he.f = x.f and he.rid is not distinct from x.rid), 0) else 0 end triples
            from dias x
        ), con_esquema as (
          select p.*, e2.registro_pago_id rp, e2.relacion_laboral_id rid_esq, e2.modalidad, e2.clasificacion, e2.sueldo_diario sd
            from partes p
            left join lateral public.inc_esquemas_dia(r.pid, pe.empresa_id, p.f, v_base) e2 on true
        )
        select coalesce(rid_esq, rid) rid, rp,
               case when rp is not null then modalidad when v_manual is not null then 'manual' end modalidad,
               max(clasificacion) clasificacion,
               sum(cant) cant, sum(dobles) dobles, sum(triples) triples,
               min(coalesce(sd, v_manual)) sd_min, max(coalesce(sd, v_manual)) sd_max,
               sum(case
                     when coalesce(sd, v_manual) is null then null
                     when v_he then coalesce(sd, v_manual) / v_jornada * (dobles * v_fd + triples * v_ftriple)
                     when k->>'tipo' = 'domingo' then cant * coalesce(sd, v_manual) * v_pct / 100
                     when v_horas then cant * coalesce(sd, v_manual) / v_jornada * coalesce((k->>'factor')::numeric, 1)
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
            'regla', case when v_he then 'horas_extra' when k->>'tipo' = 'domingo' then 'prima_dominical'
                          when v_horas then 'horas_sueldo' else 'porcentaje_sueldo' end,
            'origen_valor', case when l.rp is not null then 'sueldo' when l.modalidad = 'manual' then 'manual' end,
            'horas_dobles', case when v_he then l.dobles end,
            'horas_triples', case when v_he then l.triples end,
            'factor_doble', case when v_he then v_fd end,
            'factor_triple', case when v_he then v_ftriple end,
            'umbral_semana', case when v_he then v_umbral end,
            'jornada_horas', case when v_he or v_horas then v_jornada end,
            'valor_hora', case when (v_he or v_horas) and l.sd_min = l.sd_max then round(l.sd_min / v_jornada, 4) end,
            'pct', case when k->>'tipo' = 'domingo' then v_pct end,
            'factor', case when not v_he and k->>'tipo' <> 'domingo' then (k->>'factor')::numeric end,
            'clasificacion', l.clasificacion,
            'sueldo_diario', case when l.sd_min = l.sd_max then round(l.sd_min, 4) end,
            'fechas', l.fechas,
            'motivo', case when not l.con_sueldo then 'Sin esquema de pago enlazado a la relación de esta empresa en esas fechas' end)));
      end loop;
    end if;
  end loop;

  -- Escribir las líneas: lo modificado se respeta siempre; lo aceptado,
  -- mientras el sugerido no cambie (B1). El esquema asignado por Nómina se
  -- conserva en la columna (no se toca aquí).
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
        final = case when public.inc_importes.origen = 'modificado' then public.inc_importes.final
                     when public.inc_importes.origen = 'aceptado' and public.inc_importes.sugerido is not distinct from excluded.sugerido
                          and public.inc_importes.final is not null then public.inc_importes.final
                     else excluded.final end,
        origen = case when public.inc_importes.origen = 'modificado' then 'modificado'
                      when public.inc_importes.origen = 'aceptado' and public.inc_importes.sugerido is not distinct from excluded.sugerido
                           and public.inc_importes.final is not null then 'aceptado'
                      else excluded.origen end,
        usa_sueldo = excluded.usa_sueldo, base_calculo = excluded.base_calculo, detalle = excluded.detalle;

  -- Líneas que ya no aplican: no se borran.
  update public.inc_importes i set origen = 'descartado', final = null,
         detalle = i.detalle || jsonb_build_object('descartado_en', now())
   where i.version_id = p_version and i.origen not in ('modificado','descartado')
     and not exists (select 1 from _inc_lineas x
                      where x.pid = i.personal_id and x.cid = i.concepto_id
                        and x.rid is not distinct from i.relacion_laboral_id and x.rp is not distinct from i.registro_pago_id);
end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;

commit;
