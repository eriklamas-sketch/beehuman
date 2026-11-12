-- =====================================================================
-- BeeHuman · Fase 2 · B1.1: valor por hora configurable (12-nov-2026).
-- Solo beehuman-pruebas. Criterios: claude/B1-1-valor-hora-criterios-aceptacion-12nov.md
-- y precisiones de Erik (10:47).
--
-- Cambios delimitados (B1 y B2 no se reabren; solo se tocan las funciones
-- que esta etapa necesita, con su original en respaldo):
--   1. Empresa: factor_doble (2 por omisión) y umbral semanal de dobles que
--      puede quedar vacío (= sin triples, todas dobles).
--   2. Concepto: tipo nuevo «horas» (horas sencillas, × 1) y esquema
--      preferido opcional (clasificacion_pago_id) para conceptos por tarifa.
--   3. Cálculo (inc_calcular_version):
--      - Valor por hora = tarifa fija, o sueldo diario del esquema ÷ horas
--        de jornada. Horas extra = dobles hasta el umbral SEMANAL (acumulado
--        por persona y semana lunes–domingo, sumando todos los días y todos
--        los conceptos de horas extra) y triples después.
--      - La tarifa fija también genera dobles y triples en horas extra.
--      - Horas sencillas (o cualquier concepto en horas que no sea extra ni
--        domingo) con valor del sueldo: cantidad × sueldo diario ÷ jornada
--        (antes multiplicaba por el sueldo diario completo).
--      - Línea por tarifa: un importe ligado a un esquema solo con certeza:
--          a) asignación manual de Nómina que siga siendo válida;
--          b) esquema preferido del concepto, si la persona tiene exactamente
--             uno de esa clasificación vigente en todas las fechas;
--          c) sin preferido, si la persona tiene exactamente un esquema
--             vigente en todas las fechas.
--        Si no, origen «por_asignar» (importe calculado, sin esquema).
--      - El detalle guarda valor por hora, factores, dobles y triples.
--      - Un periodo procesado no se recalcula.
--   4. inc_asignar_esquema: Nómina liga una línea por tarifa a un esquema
--      vigente de esa persona en esa empresa y fechas.
--   5. inc_importes_ajustes: bitácora sin edición ni borrado (también para
--      el dueño de la base). Modificar un importe exige motivo y registro en
--      la bitácora; la base lo verifica con un disparador.
--   6. Importes de una hoja procesada: ni INSERT ni UPDATE, desde ningún
--      rol (disparador). inc_capturar_sueldo_manual ya no recalcula hojas
--      procesadas.
--   7. inc_decidir_importe agrega p_motivo (obligatorio al modificar) y no
--      decide líneas por asignar. inc_faltantes_procesar incluye las líneas
--      por asignar.
-- Originales en respaldo.b1_1_valor_hora_20261112.
-- Reversión: supabase/reversion/20261112000200_reversion_b1_1_valor_hora.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.b1_1_valor_hora_20261112') is not null then
    raise exception 'BeeHuman: la migración B1.1 ya está aplicada.';
  end if;
  if to_regclass('respaldo.b1_revision_20261112') is null then
    raise exception 'BeeHuman: B1.1 requiere B1 (20261112000100).';
  end if;
end $$;

create table respaldo.b1_1_valor_hora_20261112 (objeto text primary key, original text not null);
insert into respaldo.b1_1_valor_hora_20261112
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array[
    'public.inc_calcular_version(uuid)', 'public.inc_decidir_importe(uuid,numeric)',
    'public.inc_faltantes_procesar(uuid)', 'public.inc_capturar_sueldo_manual(uuid,uuid,numeric)']) x;
revoke all on table respaldo.b1_1_valor_hora_20261112 from public;

-- ---------------------------------------------------------------------
-- 1. Parámetros por empresa y conceptos
-- ---------------------------------------------------------------------
alter table public.inc_parametros add column factor_doble numeric(6,3) not null default 2 check (factor_doble > 0);
alter table public.inc_parametros alter column umbral_triples_semana drop not null;
comment on column public.inc_parametros.factor_doble is 'Factor de las horas extra dobles (× valor por hora). Por empresa.';
comment on column public.inc_parametros.umbral_triples_semana is 'Horas extra dobles por semana (lunes a domingo) antes de pagar triples. Vacío = sin triples.';

alter table public.inc_conceptos drop constraint inc_conceptos_tipo_check;
alter table public.inc_conceptos add constraint inc_conceptos_tipo_check
  check (tipo in ('horas_extra','horas','domingo','turno','descuento','otro'));
alter table public.inc_conceptos add column clasificacion_pago_id uuid references public.clasificaciones_personal(id);
comment on column public.inc_conceptos.clasificacion_pago_id is 'Conceptos por tarifa: esquema de pago preferido (clasificación). Se asigna solo si la persona tiene exactamente uno vigente.';

-- ---------------------------------------------------------------------
-- 2. Importes: por asignar, quién asignó el esquema
-- ---------------------------------------------------------------------
alter table public.inc_importes drop constraint inc_importes_origen_check;
alter table public.inc_importes add constraint inc_importes_origen_check
  check (origen in ('pendiente','aceptado','modificado','sin_sueldo','sin_importe','descartado','por_asignar'));
alter table public.inc_importes add column esquema_asignado_por uuid;
alter table public.inc_importes add column esquema_asignado_en  timestamptz;
comment on column public.inc_importes.esquema_asignado_por is 'Nómina asignó el esquema de esta línea por tarifa (null: asignación automática o sin esquema).';

-- ---------------------------------------------------------------------
-- 3. Bitácora de ajustes (sin edición ni borrado)
-- ---------------------------------------------------------------------
create table public.inc_importes_ajustes (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references public.tenants(id),
  importe_id       uuid not null references public.inc_importes(id),
  tipo             text not null check (tipo in ('importe','esquema')),
  anterior         numeric(14,2),
  nuevo            numeric(14,2),
  origen_anterior  text,
  origen_nuevo     text,
  esquema_anterior uuid,
  esquema_nuevo    uuid,
  motivo           text,
  usuario_id       uuid not null,
  nombre           text,
  creado_en        timestamptz not null default now(),
  check (tipo <> 'importe' or length(trim(coalesce(motivo,''))) > 0)
);
create index inc_importes_ajustes_importe on public.inc_importes_ajustes (importe_id, creado_en);
create trigger trg_inc_ajustes_inmutables before update or delete on public.inc_importes_ajustes
  for each row execute function public.inc_bloquear_cambios();
create trigger trg_inc_ajustes_sin_truncate before truncate on public.inc_importes_ajustes
  for each statement execute function public.inc_bloquear_cambios();
alter table public.inc_importes_ajustes enable row level security;
revoke all on public.inc_importes_ajustes from public, anon, authenticated;
grant select on public.inc_importes_ajustes to authenticated;
create policy inc_ajustes_select on public.inc_importes_ajustes for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));

-- ---------------------------------------------------------------------
-- 4. Protección de importes: hoja procesada y ajustes con bitácora
-- ---------------------------------------------------------------------
create function public.inc_importes_proteger() returns trigger
language plpgsql set search_path to '' as $$
begin
  if exists (select 1 from public.inc_versiones v join public.inc_hojas h on h.id = v.hoja_id
              where v.id = new.version_id and h.estado = 'procesada') then
    raise exception 'BeeHuman: el periodo ya se procesó; sus importes no se modifican ni se recalculan.';
  end if;
  if tg_op = 'UPDATE' and new.final is distinct from old.final
     and (new.origen = 'modificado' or old.origen = 'modificado')
     and not exists (select 1 from public.inc_importes_ajustes a
                      where a.importe_id = new.id and a.tipo = 'importe' and a.creado_en = now()
                        and a.nuevo is not distinct from new.final) then
    raise exception 'BeeHuman: un ajuste de importe requiere su registro en la bitácora con motivo.';
  end if;
  return new;
end $$;
create trigger trg_inc_importes_proteger before insert or update on public.inc_importes
  for each row execute function public.inc_importes_proteger();

-- ---------------------------------------------------------------------
-- 5. Esquemas vigentes de una persona en una empresa en TODAS las fechas
-- ---------------------------------------------------------------------
create function public.inc_esquemas_vigentes(p_personal uuid, p_empresa uuid, p_fechas date[], p_base text)
returns table (registro_pago_id uuid, relacion_laboral_id uuid, modalidad text, clasificacion_id uuid, clasificacion text)
language sql stable security definer set search_path to '' as $$
  select r.id, r.relacion_laboral_id, r.modalidad_sueldo, r.clasificacion_id, c.nombre
    from public.personal_registros_pago r
    join public.relaciones_laborales rl on rl.id = r.relacion_laboral_id
    left join public.clasificaciones_personal c on c.id = r.clasificacion_id
   where r.personal_id = p_personal and rl.empresa_id = p_empresa and rl.estado <> 'anulada'
     and (coalesce(p_base, 'mixto') = 'mixto' or r.modalidad_sueldo = p_base)
     and cardinality(p_fechas) > 0
     and not exists (
       select 1 from unnest(p_fechas) f
        where not (coalesce(rl.fecha_ingreso, '-infinity'::date) <= f
                   and ((rl.estado = 'vigente' and rl.fecha_baja is null) or f <= rl.fecha_baja)
                   and r.fecha_inicio <= f
                   and f <= coalesce(r.fecha_fin, case when r.activo then 'infinity'::date end)))
   order by r.modalidad_sueldo, c.nombre, r.id
$$;
comment on function public.inc_esquemas_vigentes(uuid,uuid,date[],text) is
  'BeeHuman: esquemas de pago de la persona con la empresa vigentes en todas las fechas dadas (base mixto = todos).';

-- ---------------------------------------------------------------------
-- 6. Cálculo con valor por hora
-- ---------------------------------------------------------------------
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
  delete from _inc_lineas;

  create temp table if not exists _inc_dias (pid uuid, cid uuid, f date, cant numeric, rid uuid) on commit drop;
  delete from _inc_dias;
  insert into _inc_dias
  select (q->>'personal_id')::uuid, (q->>'concepto_id')::uuid, (q->>'fecha')::date, (q->>'cantidad')::numeric,
         coalesce((q->>'relacion_laboral_id')::uuid,
                  public.inc_relacion_en((q->>'personal_id')::uuid, pe.empresa_id, (q->>'fecha')::date))
    from jsonb_array_elements(ve.datos->'cantidades') q;

  -- Horas extra: dobles hasta el umbral de la SEMANA (lunes a domingo) y
  -- triples después, acumulando por persona todos los días y todos los
  -- conceptos de horas extra con importe, en orden de fecha y de columna.
  create temp table if not exists _inc_he (pid uuid, cid uuid, f date, rid uuid, cant numeric, dobles numeric, triples numeric) on commit drop;
  delete from _inc_he;
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
        v_origen := case when v_rp is null then 'por_asignar' when v_asig = 'manual' then 'pendiente' else 'aceptado' end;
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

-- ---------------------------------------------------------------------
-- 7. Decidir importe: motivo obligatorio al modificar (bitácora)
-- ---------------------------------------------------------------------
drop function public.inc_decidir_importe(uuid, numeric);
create function public.inc_decidir_importe(p_importe uuid, p_final numeric, p_motivo text default null)
returns void language plpgsql security definer set search_path to '' as $$
declare i record; v_nuevo numeric; v_origen text;
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
  if i.origen = 'por_asignar' then
    raise exception 'BeeHuman: asigna primero el esquema de pago de esta línea.';
  end if;
  if p_final is null and i.sugerido is null then raise exception 'BeeHuman: no hay sugerencia que aceptar.'; end if;
  if p_final is not null and p_final < 0 then raise exception 'BeeHuman: el importe no puede ser negativo.'; end if;
  v_nuevo  := coalesce(round(p_final, 2), i.sugerido);
  v_origen := case when p_final is null or round(p_final, 2) = i.sugerido then 'aceptado' else 'modificado' end;
  if (v_origen = 'modificado' or i.origen = 'modificado') and v_nuevo is distinct from i.final then
    if length(trim(coalesce(p_motivo, ''))) = 0 then
      raise exception 'BeeHuman: escribe el motivo del ajuste; queda en la bitácora.';
    end if;
    insert into public.inc_importes_ajustes (tenant_id, importe_id, tipo, anterior, nuevo, origen_anterior, origen_nuevo,
                                             esquema_anterior, esquema_nuevo, motivo, usuario_id, nombre)
    values (i.tenant_id, i.id, 'importe', coalesce(i.final, i.sugerido), v_nuevo, i.origen, v_origen,
            i.registro_pago_id, i.registro_pago_id, trim(p_motivo), auth.uid(), public.inc_nombre_usuario());
  end if;
  update public.inc_importes
     set final = v_nuevo, origen = v_origen, decidido_por = auth.uid(), decidido_en = now()
   where id = p_importe;
end $$;
revoke all on function public.inc_decidir_importe(uuid,numeric,text) from public, anon;
grant execute on function public.inc_decidir_importe(uuid,numeric,text) to authenticated;

-- ---------------------------------------------------------------------
-- 8. Asignar esquema (Nómina)
-- ---------------------------------------------------------------------
create function public.inc_esquemas_asignables(p_version uuid)
returns table (linea_id uuid, registro_pago_id uuid, modalidad text, clasificacion text, registro_patronal text)
language plpgsql stable security definer set search_path to '' as $$
#variable_conflict use_column
declare ve record; pe record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select v.* into ve from public.inc_versiones v where v.id = p_version and v.tenant_id = public.current_tenant_id();
  if ve.id is null then raise exception 'BeeHuman: versión no encontrada.'; end if;
  select p.* into pe from public.inc_periodos p join public.inc_hojas h on h.periodo_id = p.id where h.id = ve.hoja_id;
  return query
  select i.id, e.registro_pago_id, e.modalidad, e.clasificacion, rp.registro_patronal
    from public.inc_importes i
    cross join lateral public.inc_esquemas_vigentes(i.personal_id, pe.empresa_id,
           (select array_agg(x::date) from jsonb_array_elements_text(i.detalle->'fechas') x), ve.datos->'parametros'->>'base_calculo') e
    left join public.relaciones_laborales rl on rl.id = e.relacion_laboral_id
    left join public.empresas_registros_patronales rp on rp.id = rl.registro_patronal_id
   where i.version_id = p_version and not i.usa_sueldo and i.detalle->>'origen_valor' = 'tarifa'
     and (i.origen = 'por_asignar' or (i.esquema_asignado_por is not null and i.origen in ('pendiente','aceptado')))
   order by i.id, e.modalidad, e.clasificacion;
end $$;

create function public.inc_asignar_esquema(p_importe uuid, p_registro_pago uuid, p_motivo text default null)
returns void language plpgsql security definer set search_path to '' as $$
declare i record; pe record; ve record; e record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into i from public.inc_importes where id = p_importe and tenant_id = public.current_tenant_id() for update;
  if i.id is null then raise exception 'BeeHuman: importe no encontrado.'; end if;
  select v.* into ve from public.inc_versiones v join public.inc_hojas h on h.id = v.hoja_id
   where v.id = i.version_id and v.numero = h.version_actual and h.estado = 'enviada';
  if ve.id is null then raise exception 'BeeHuman: solo se asignan esquemas en la versión vigente de una hoja enviada.'; end if;
  if i.usa_sueldo or coalesce(i.detalle->>'origen_valor', '') <> 'tarifa' then
    raise exception 'BeeHuman: solo las líneas por tarifa llevan un esquema elegido por Nómina.';
  end if;
  if not (i.origen = 'por_asignar' or (i.esquema_asignado_por is not null and i.origen in ('pendiente','aceptado'))) then
    raise exception 'BeeHuman: esta línea ya tiene su esquema de pago y no está por asignar.';
  end if;
  select p.* into pe from public.inc_periodos p join public.inc_hojas h on h.periodo_id = p.id where h.id = ve.hoja_id;
  select * into e from public.inc_esquemas_vigentes(i.personal_id, pe.empresa_id,
           (select array_agg(x::date) from jsonb_array_elements_text(i.detalle->'fechas') x), ve.datos->'parametros'->>'base_calculo') x
   where x.registro_pago_id = p_registro_pago;
  if e.registro_pago_id is null then
    raise exception 'BeeHuman: ese esquema no es de esta persona en esta empresa o no está vigente en las fechas de la línea.';
  end if;
  insert into public.inc_importes_ajustes (tenant_id, importe_id, tipo, anterior, nuevo, origen_anterior, origen_nuevo,
                                           esquema_anterior, esquema_nuevo, motivo, usuario_id, nombre)
  values (i.tenant_id, i.id, 'esquema', i.sugerido, i.sugerido, i.origen, 'pendiente',
          i.registro_pago_id, p_registro_pago, nullif(trim(coalesce(p_motivo, '')), ''), auth.uid(), public.inc_nombre_usuario());
  begin
    update public.inc_importes
       set registro_pago_id = p_registro_pago, modalidad = e.modalidad, origen = 'pendiente', final = null,
           decidido_por = null, decidido_en = null,
           esquema_asignado_por = auth.uid(), esquema_asignado_en = now(),
           detalle = (detalle - 'motivo') || jsonb_build_object('asignacion', 'manual', 'clasificacion', e.clasificacion)
     where id = p_importe;
  exception when unique_violation then
    raise exception 'BeeHuman: ya existe una línea de este concepto con ese esquema para la persona.';
  end;
end $$;
revoke all on function public.inc_esquemas_vigentes(uuid,uuid,date[],text) from public, anon, authenticated;
revoke all on function public.inc_esquemas_asignables(uuid) from public, anon;
revoke all on function public.inc_asignar_esquema(uuid,uuid,text) from public, anon;
grant execute on function public.inc_esquemas_asignables(uuid), public.inc_asignar_esquema(uuid,uuid,text) to authenticated;
revoke all on function public.inc_importes_proteger() from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- 9. Faltantes para procesar: también las líneas por asignar
-- ---------------------------------------------------------------------
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
-- 10. Sueldo manual: no recalcula hojas procesadas
-- ---------------------------------------------------------------------
create or replace function public.inc_capturar_sueldo_manual(p_periodo uuid, p_personal uuid, p_sueldo numeric)
returns void language plpgsql security definer set search_path to '' as $$
declare v record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  insert into public.inc_sueldos_manuales (tenant_id, periodo_id, personal_id, sueldo_diario, capturado_por)
  select tenant_id, id, p_personal, p_sueldo, auth.uid() from public.inc_periodos
  where id = p_periodo and tenant_id = public.current_tenant_id()
  on conflict (periodo_id, personal_id) do update set sueldo_diario = excluded.sueldo_diario,
     capturado_por = excluded.capturado_por, capturado_en = now();
  for v in select ve.id from public.inc_versiones ve join public.inc_hojas h on h.id = ve.hoja_id
           where h.periodo_id = p_periodo and ve.numero = h.version_actual and h.estado <> 'procesada' loop
    perform public.inc_calcular_version(v.id);
  end loop;
end $$;

commit;
