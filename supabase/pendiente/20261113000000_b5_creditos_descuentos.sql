-- =====================================================================
-- BeeHuman · Fase 2 · B5: créditos y descuentos (13-nov-2026).
-- Solo beehuman-pruebas. Diseño aprobado por Erik (13-nov 13:42):
-- claude/B5-creditos-descuentos-diseno-tecnico-13nov.md
--
-- Registrar un crédito NO es descontarlo:
--   - Informativos (no generan importes ni pendientes): INFONAVIT (se
--     registra para NOI; el cálculo es B6), pensión porcentual y todo
--     crédito «incompleto» (p. ej. FONACOT convertido de personal.no_fonacot).
--   - Calculables: FONACOT (retención por periodo de la cédula, sin
--     prorrateo), préstamo, anticipo, otro y pensión fija. Proponen UNA
--     línea por periodo y crédito, «por decidir», solo si el periodo es de la
--     empresa de la relación ligada, la relación está vigente, la vigencia del
--     crédito se cruza con el periodo y la periodicidad del periodo es la del
--     crédito.
--   - Saldo (préstamo, anticipo y FONACOT con monto total) = monto total −
--     movimientos. Se descuenta SOLO al procesar el periodo, en la misma
--     transacción, una vez (índice único crédito-periodo); con saldo cero el
--     crédito se termina en esa transacción.
--   - Saldo disponible (cred_disponible) = saldo real − lo comprometido en
--     otros periodos abiertos (anteriores: propuesto o decidido; posteriores:
--     solo decidido). Proponer, aceptar, modificar, faltantes y procesar lo
--     respetan, con el crédito bloqueado (concurrencia serializada).
--   - Datos sensibles: RLS solo Administrador y Nómina; la aplicación no
--     escribe directo (solo funciones que validan rol y organización).
--   - Historia, bitácora y movimientos sin edición ni borrado.
--   - Periodo procesado: sus descuentos no se insertan, cambian ni recalculan.
-- Cambia (originales en respaldo.b5_creditos_20261113):
--   inc_faltantes_procesar (agrega descuentos) e inc_marcar_procesado
--   (sincroniza, valida saldo, aplica movimientos y termina préstamos).
-- Convierte personal.no_fonacot en créditos FONACOT «incompletos» (el campo
-- no se borra; la conversión queda en la historia).
-- Reversión: supabase/reversion/20261113000000_reversion_b5_creditos_descuentos.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.b5_creditos_20261113') is not null then
    raise exception 'BeeHuman: la migración B5 ya está aplicada.';
  end if;
  if to_regclass('respaldo.b1_1b_delete_con_where_20261112') is null then
    raise exception 'BeeHuman: B5 requiere B1.1b (20261112000400).';
  end if;
end $$;

create table respaldo.b5_creditos_20261113 (objeto text primary key, original text not null);
insert into respaldo.b5_creditos_20261113
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array[
    'public.inc_faltantes_procesar(uuid)', 'public.inc_marcar_procesado(uuid)']) x;
revoke all on table respaldo.b5_creditos_20261113 from public;

-- ---------------------------------------------------------------------
-- 1. Tablas
-- ---------------------------------------------------------------------
create table public.cred_creditos (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id),
  personal_id           uuid not null references public.personal(id),
  relacion_laboral_id   uuid references public.relaciones_laborales(id),
  tipo                  text not null check (tipo in ('infonavit','fonacot','prestamo','anticipo','pension','otro')),
  concepto              text,
  referencia            text,
  estado                text not null default 'activo' check (estado in ('incompleto','activo','suspendido','terminado')),
  fecha_inicio          date,
  fecha_fin             date,
  periodicidad_id       uuid references public.periodicidades(id),
  importe_periodo       numeric(14,2) check (importe_periodo > 0),
  monto_total           numeric(14,2) check (monto_total > 0),
  infonavit_tipo        text check (infonavit_tipo in ('cuota_fija','porcentaje','factor_vsm_uma')),
  infonavit_valor       numeric(14,4) check (infonavit_valor > 0),
  infonavit_fecha_aviso date,
  pension_forma         text check (pension_forma in ('fijo','porcentaje')),
  pension_valor         numeric(14,4) check (pension_valor > 0),
  pension_beneficiario  text,
  notas                 text,
  origen                text not null default 'captura' check (origen in ('captura','conversion_no_fonacot')),
  creado_por            uuid,
  creado_en             timestamptz not null default now(),
  actualizado_en        timestamptz,
  check (estado = 'incompleto' or relacion_laboral_id is not null),
  check (estado = 'incompleto' or fecha_inicio is not null),
  check (fecha_fin is null or fecha_inicio is null or fecha_fin >= fecha_inicio),
  check (tipo <> 'otro' or length(trim(coalesce(concepto, ''))) > 0),
  check (tipo <> 'infonavit' or (importe_periodo is null and monto_total is null)),
  check (not (tipo = 'pension' and pension_forma = 'porcentaje') or importe_periodo is null),
  check (tipo not in ('prestamo','anticipo') or monto_total is not null),
  check (monto_total is null or importe_periodo is null or importe_periodo <= monto_total)
);
create index cred_creditos_persona on public.cred_creditos (personal_id);
create index cred_creditos_relacion on public.cred_creditos (relacion_laboral_id);

create table public.cred_historia (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references public.tenants(id),
  credito_id     uuid not null references public.cred_creditos(id),
  evento         text not null check (evento in ('alta','cambio','suspension','reactivacion','terminacion','activacion','conversion','terminacion_saldo')),
  antes          jsonb,
  despues        jsonb,
  fecha_efectiva date,
  motivo         text,
  usuario_id     uuid,
  nombre         text,
  creado_en      timestamptz not null default now()
);
create index cred_historia_credito on public.cred_historia (credito_id, creado_en);

create table public.cred_descuentos (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references public.tenants(id),
  periodo_id          uuid not null references public.inc_periodos(id),
  credito_id          uuid not null references public.cred_creditos(id),
  personal_id         uuid not null references public.personal(id),
  relacion_laboral_id uuid references public.relaciones_laborales(id),
  sugerido            numeric(14,2),
  final               numeric(14,2) check (final >= 0),
  origen              text not null default 'pendiente' check (origen in ('pendiente','aceptado','modificado','descartado')),
  decidido_por        uuid,
  decidido_en         timestamptz,
  detalle             jsonb not null default '{}'::jsonb,
  creado_en           timestamptz not null default now(),
  unique (periodo_id, credito_id)
);
create index cred_descuentos_credito on public.cred_descuentos (credito_id);

create table public.cred_descuentos_ajustes (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references public.tenants(id),
  descuento_id uuid not null references public.cred_descuentos(id),
  anterior     numeric(14,2),
  nuevo        numeric(14,2),
  origen_anterior text,
  origen_nuevo text,
  motivo       text not null check (length(trim(motivo)) > 0),
  usuario_id   uuid not null,
  nombre       text,
  creado_en    timestamptz not null default now()
);
create index cred_ajustes_descuento on public.cred_descuentos_ajustes (descuento_id, creado_en);

create table public.cred_movimientos (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references public.tenants(id),
  credito_id     uuid not null references public.cred_creditos(id),
  periodo_id     uuid not null references public.inc_periodos(id),
  descuento_id   uuid not null references public.cred_descuentos(id),
  importe        numeric(14,2) not null check (importe > 0),
  saldo_anterior numeric(14,2) not null,
  saldo_nuevo    numeric(14,2) not null check (saldo_nuevo >= 0),
  usuario_id     uuid,
  creado_en      timestamptz not null default now(),
  unique (credito_id, periodo_id),
  check (saldo_nuevo = saldo_anterior - importe)
);

-- Sin edición ni borrado: historia, bitácora y movimientos.
create trigger trg_cred_historia_inmutable  before update or delete on public.cred_historia for each row execute function public.inc_bloquear_cambios();
create trigger trg_cred_historia_sin_trunc  before truncate on public.cred_historia for each statement execute function public.inc_bloquear_cambios();
create trigger trg_cred_ajustes_inmutables  before update or delete on public.cred_descuentos_ajustes for each row execute function public.inc_bloquear_cambios();
create trigger trg_cred_ajustes_sin_trunc   before truncate on public.cred_descuentos_ajustes for each statement execute function public.inc_bloquear_cambios();
create trigger trg_cred_mov_inmutables      before update or delete on public.cred_movimientos for each row execute function public.inc_bloquear_cambios();
create trigger trg_cred_mov_sin_trunc       before truncate on public.cred_movimientos for each statement execute function public.inc_bloquear_cambios();
-- Créditos y descuentos no se borran (se terminan o se descartan).
create trigger trg_cred_creditos_sin_borrar before delete on public.cred_creditos for each row execute function public.inc_bloquear_cambios();
create trigger trg_cred_creditos_sin_trunc  before truncate on public.cred_creditos for each statement execute function public.inc_bloquear_cambios();
create trigger trg_cred_desc_sin_borrar     before delete on public.cred_descuentos for each row execute function public.inc_bloquear_cambios();
create trigger trg_cred_desc_sin_trunc      before truncate on public.cred_descuentos for each statement execute function public.inc_bloquear_cambios();

-- Descuentos: periodo procesado intocable; un ajuste exige su bitácora.
create function public.cred_descuentos_proteger() returns trigger
language plpgsql set search_path to '' as $$
begin
  if exists (select 1 from public.inc_periodos p where p.id = new.periodo_id and p.procesado_en is not null) then
    raise exception 'BeeHuman: el periodo ya se procesó; sus descuentos no se modifican ni se recalculan.';
  end if;
  if tg_op = 'UPDATE' and new.origen <> 'descartado' and new.final is distinct from old.final
     and (new.origen = 'modificado' or old.origen = 'modificado')
     and not exists (select 1 from public.cred_descuentos_ajustes a
                      where a.descuento_id = new.id and a.creado_en = now() and a.nuevo is not distinct from new.final) then
    raise exception 'BeeHuman: un ajuste de descuento requiere su registro en la bitácora con motivo.';
  end if;
  return new;
end $$;
create trigger trg_cred_descuentos_proteger before insert or update on public.cred_descuentos
  for each row execute function public.cred_descuentos_proteger();

-- ---------------------------------------------------------------------
-- 2. Permisos: datos sensibles solo para Administrador y Nómina
-- ---------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['cred_creditos','cred_historia','cred_descuentos','cred_descuentos_ajustes','cred_movimientos'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public, anon, authenticated', t);
    execute format('grant select on public.%I to authenticated', t);
    execute format('create policy %I on public.%I for select to authenticated using (tenant_id = public.current_tenant_id() and public.tiene_rol(''administrador'',''nomina''))', t || '_select', t);
  end loop;
end $$;

-- ---------------------------------------------------------------------
-- 3. Reglas
-- ---------------------------------------------------------------------
-- Calculable: genera un descuento propuesto. Informativo: no.
create function public.cred_es_calculable(c public.cred_creditos) returns boolean
language sql immutable set search_path to '' as $$
  select c.estado <> 'incompleto' and c.importe_periodo is not null and c.periodicidad_id is not null
     and (c.tipo in ('fonacot','prestamo','anticipo','otro') or (c.tipo = 'pension' and c.pension_forma = 'fijo'))
$$;

-- Saldo = monto total − movimientos (null si el crédito no controla saldo).
create function public.cred_saldo_actual(p_credito uuid) returns numeric
language sql stable security definer set search_path to '' as $$
  select c.monto_total - coalesce((select sum(m.importe) from public.cred_movimientos m where m.credito_id = c.id), 0)
    from public.cred_creditos c where c.id = p_credito
$$;

-- ¿El crédito propone descuento en el periodo? (activo, calculable, empresa
-- de su relación, relación vigente en el periodo, vigencia y periodicidad).
create function public.cred_aplica(c public.cred_creditos, pe public.inc_periodos) returns boolean
language sql stable security definer set search_path to '' as $$
  select c.estado = 'activo' and public.cred_es_calculable(c) and c.tenant_id = pe.tenant_id
     and pe.periodicidad_id is not null and pe.periodicidad_id = c.periodicidad_id
     and c.fecha_inicio <= pe.fin and (c.fecha_fin is null or c.fecha_fin >= pe.inicio)
     and exists (select 1 from public.relaciones_laborales rl
                  where rl.id = c.relacion_laboral_id and rl.personal_id = c.personal_id
                    and rl.empresa_id = pe.empresa_id and rl.estado <> 'anulada'
                    and coalesce(rl.fecha_ingreso, '-infinity'::date) <= pe.fin
                    and ((rl.estado = 'vigente' and rl.fecha_baja is null) or rl.fecha_baja >= pe.inicio))
$$;

-- Saldo DISPONIBLE del crédito para un periodo: saldo real menos lo
-- comprometido en los OTROS periodos abiertos (no procesados, línea no
-- descartada):
--   - periodos anteriores: su importe decidido o, si aún no se decide, el
--     propuesto (tienen prioridad);
--   - periodos posteriores: solo su importe ya decidido (aceptado/modificado).
-- Es la única regla para proponer, aceptar, modificar, listar faltantes y
-- procesar; quien escribe la usa con el crédito bloqueado (FOR UPDATE), así
-- dos operaciones concurrentes sobre el mismo crédito se serializan y la
-- segunda ve lo que comprometió la primera. Null si el crédito no controla
-- saldo (sin monto total).
create function public.cred_disponible(p_credito uuid, p_periodo uuid) returns numeric
language sql stable security definer set search_path to '' as $$
  select public.cred_saldo_actual(c.id) - coalesce((
           select sum(case when p2.inicio < pe.inicio then coalesce(d.final, d.sugerido)
                           when d.origen in ('aceptado','modificado') then d.final
                           else 0 end)
             from public.cred_descuentos d join public.inc_periodos p2 on p2.id = d.periodo_id
            where d.credito_id = c.id and d.periodo_id <> pe.id and d.origen <> 'descartado'
              and p2.procesado_en is null), 0)
    from public.cred_creditos c, public.inc_periodos pe
   where c.id = p_credito and pe.id = p_periodo and c.monto_total is not null
$$;

-- Propuestas del periodo (sin escribir): nunca más que el saldo disponible.
create function public.cred_propuestas(p_periodo uuid)
returns table (credito_id uuid, personal_id uuid, relacion_laboral_id uuid, sugerido numeric, detalle jsonb)
language sql stable security definer set search_path to '' as $$
  with pe as (select p from public.inc_periodos p where p.id = p_periodo),
  base as (
    select c.*, public.cred_saldo_actual(c.id) saldo, public.cred_disponible(c.id, (pe.p).id) disponible
      from public.cred_creditos c cross join pe
     where public.cred_aplica(c, pe.p)
  )
  select b.id, b.personal_id, b.relacion_laboral_id,
         case when b.monto_total is null then b.importe_periodo
              else least(b.importe_periodo, b.disponible) end,
         jsonb_strip_nulls(jsonb_build_object(
           'importe_periodo', b.importe_periodo, 'monto_total', b.monto_total, 'saldo', b.saldo,
           'disponible', b.disponible,
           'comprometido_otros_periodos', case when b.saldo - b.disponible > 0 then b.saldo - b.disponible end,
           'tope_saldo', case when b.monto_total is not null and b.disponible < b.importe_periodo then true end))
    from base b
   where b.monto_total is null or b.disponible > 0
$$;

-- Sincroniza las líneas del periodo (no hace nada si está procesado).
-- Respeta lo modificado y lo aceptado con el mismo sugerido; descarta sin
-- borrar lo que ya no aplica.
create function public.cred_sincronizar_periodo(p_periodo uuid) returns void
language plpgsql security definer set search_path to '' as $$
declare pe record;
begin
  select * into pe from public.inc_periodos where id = p_periodo;
  if pe.id is null or pe.procesado_en is not null then return; end if;
  -- Bloquea los créditos involucrados (en orden, sin abrazos mortales): el
  -- recálculo de un periodo espera a quien esté decidiendo o procesando el
  -- mismo crédito en otro.
  perform 1 from public.cred_creditos c
   where c.id in (select x.credito_id from public.cred_propuestas(p_periodo) x
                  union select d.credito_id from public.cred_descuentos d where d.periodo_id = p_periodo)
   order by c.id for update;
  insert into public.cred_descuentos (tenant_id, periodo_id, credito_id, personal_id, relacion_laboral_id, sugerido, origen, detalle)
  select pe.tenant_id, p_periodo, x.credito_id, x.personal_id, x.relacion_laboral_id, x.sugerido, 'pendiente', x.detalle
    from public.cred_propuestas(p_periodo) x
  on conflict (periodo_id, credito_id) do update
    set sugerido = excluded.sugerido, relacion_laboral_id = excluded.relacion_laboral_id, detalle = excluded.detalle,
        origen = case when public.cred_descuentos.origen = 'modificado' then 'modificado'
                      when public.cred_descuentos.origen = 'aceptado' and public.cred_descuentos.sugerido = excluded.sugerido then 'aceptado'
                      else 'pendiente' end,
        final  = case when public.cred_descuentos.origen = 'modificado' then public.cred_descuentos.final
                      when public.cred_descuentos.origen = 'aceptado' and public.cred_descuentos.sugerido = excluded.sugerido then public.cred_descuentos.final
                      end
  where public.cred_descuentos.sugerido is distinct from excluded.sugerido
     or public.cred_descuentos.origen = 'descartado'
     or public.cred_descuentos.detalle is distinct from excluded.detalle;
  update public.cred_descuentos d set origen = 'descartado', final = null,
         detalle = d.detalle || jsonb_build_object('descartado_en', now(), 'origen_previo', d.origen)
   where d.periodo_id = p_periodo and d.origen <> 'descartado'
     and not exists (select 1 from public.cred_propuestas(p_periodo) x where x.credito_id = d.credito_id);
end $$;

-- ---------------------------------------------------------------------
-- 4. Registro de créditos
-- ---------------------------------------------------------------------
-- Valida los datos de un crédito según su tipo y el estado al que va.
create function public.cred_validar(c public.cred_creditos) returns void
language plpgsql stable security definer set search_path to '' as $$
begin
  if c.estado = 'incompleto' then
    if c.tipo <> 'fonacot' then raise exception 'BeeHuman: solo un FONACOT convertido puede quedar incompleto.'; end if;
    return;
  end if;
  if c.relacion_laboral_id is null then raise exception 'BeeHuman: elige la relación laboral (empresa) del crédito.'; end if;
  if not exists (select 1 from public.relaciones_laborales rl where rl.id = c.relacion_laboral_id and rl.personal_id = c.personal_id
                  and rl.tenant_id = c.tenant_id and rl.estado <> 'anulada') then
    raise exception 'BeeHuman: la relación laboral no es de esta persona o está anulada.';
  end if;
  if c.fecha_inicio is null then raise exception 'BeeHuman: captura la fecha de inicio del crédito.'; end if;
  if c.periodicidad_id is not null and not exists (select 1 from public.periodicidades p where p.id = c.periodicidad_id and p.tenant_id = c.tenant_id) then
    raise exception 'BeeHuman: periodicidad fuera de tu organización.';
  end if;
  if c.tipo = 'infonavit' then
    if coalesce(trim(c.referencia), '') = '' or c.infonavit_tipo is null or c.infonavit_valor is null then
      raise exception 'BeeHuman: INFONAVIT requiere número de crédito, tipo de descuento y valor (se registra para NOI; no genera descuento).';
    end if;
    if c.importe_periodo is not null or c.monto_total is not null then
      raise exception 'BeeHuman: INFONAVIT se registra para NOI y no genera descuento en BeeHuman todavía; no captures importe por periodo ni monto.';
    end if;
  elsif c.tipo = 'pension' then
    if c.pension_forma is null then raise exception 'BeeHuman: indica si la pensión es monto fijo o porcentaje.'; end if;
    if c.pension_forma = 'porcentaje' and (c.pension_valor is null or c.pension_valor > 100) then
      raise exception 'BeeHuman: captura el porcentaje de la pensión (hasta 100).';
    end if;
    if c.pension_forma = 'porcentaje' and c.importe_periodo is not null then
      raise exception 'BeeHuman: la pensión porcentual se calcula sobre el neto (motor de nómina); no captures importe por periodo.';
    end if;
    if c.pension_forma = 'fijo' and (c.importe_periodo is null or c.periodicidad_id is null) then
      raise exception 'BeeHuman: la pensión fija requiere el importe por periodo y su periodicidad.';
    end if;
  else
    if c.tipo = 'fonacot' and coalesce(trim(c.referencia), '') = '' then raise exception 'BeeHuman: FONACOT requiere el número de crédito.'; end if;
    if c.importe_periodo is null or c.periodicidad_id is null then
      raise exception 'BeeHuman: captura el descuento por periodo y su periodicidad%.',
        case when c.tipo = 'fonacot' then ' (retención de la cédula, sin prorratear)' else '' end;
    end if;
  end if;
end $$;

create function public.cred_guardar(p_id uuid, p_datos jsonb, p_motivo text default null)
returns uuid language plpgsql security definer set search_path to '' as $$
declare v_antes public.cred_creditos; v_c public.cred_creditos; v_tenant uuid := public.current_tenant_id();
  v_datos jsonb := coalesce(p_datos, '{}'::jsonb) - 'id' - 'tenant_id' - 'personal_id' - 'tipo' - 'estado' - 'origen' - 'creado_por' - 'creado_en' - 'actualizado_en';
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  if p_id is null then
    if not exists (select 1 from public.personal where id = (p_datos->>'personal_id')::uuid and tenant_id = v_tenant) then
      raise exception 'BeeHuman: persona fuera de tu organización.';
    end if;
    v_c := jsonb_populate_record(null::public.cred_creditos, v_datos || jsonb_build_object(
      'id', gen_random_uuid(), 'tenant_id', v_tenant, 'personal_id', p_datos->>'personal_id', 'tipo', p_datos->>'tipo',
      'estado', 'activo', 'origen', 'captura', 'creado_por', auth.uid(), 'creado_en', now()));
    perform public.cred_validar(v_c);
    insert into public.cred_creditos select v_c.*;
    insert into public.cred_historia (tenant_id, credito_id, evento, despues, fecha_efectiva, motivo, usuario_id, nombre)
    values (v_tenant, v_c.id, 'alta', to_jsonb(v_c), v_c.fecha_inicio, nullif(trim(coalesce(p_motivo, '')), ''), auth.uid(), public.inc_nombre_usuario());
    return v_c.id;
  end if;
  select * into v_antes from public.cred_creditos where id = p_id and tenant_id = v_tenant for update;
  if v_antes.id is null then raise exception 'BeeHuman: crédito no encontrado.'; end if;
  if v_antes.estado = 'terminado' then raise exception 'BeeHuman: un crédito terminado no se modifica.'; end if;
  if length(trim(coalesce(p_motivo, ''))) = 0 then raise exception 'BeeHuman: escribe el motivo del cambio; queda en la historia.'; end if;
  v_c := jsonb_populate_record(v_antes, v_datos || jsonb_build_object('actualizado_en', now()));
  if v_c.monto_total is distinct from v_antes.monto_total and exists (select 1 from public.cred_movimientos where credito_id = p_id) then
    raise exception 'BeeHuman: el monto total no cambia una vez aplicados descuentos (afectaría el saldo).';
  end if;
  if v_c.monto_total is not null and v_c.monto_total - coalesce((select sum(importe) from public.cred_movimientos where credito_id = p_id), 0) < 0 then
    raise exception 'BeeHuman: el monto total no puede ser menor a lo ya descontado.';
  end if;
  perform public.cred_validar(v_c);
  update public.cred_creditos set
    relacion_laboral_id = v_c.relacion_laboral_id, concepto = v_c.concepto, referencia = v_c.referencia,
    fecha_inicio = v_c.fecha_inicio, fecha_fin = v_c.fecha_fin, periodicidad_id = v_c.periodicidad_id,
    importe_periodo = v_c.importe_periodo, monto_total = v_c.monto_total,
    infonavit_tipo = v_c.infonavit_tipo, infonavit_valor = v_c.infonavit_valor, infonavit_fecha_aviso = v_c.infonavit_fecha_aviso,
    pension_forma = v_c.pension_forma, pension_valor = v_c.pension_valor, pension_beneficiario = v_c.pension_beneficiario,
    notas = v_c.notas, actualizado_en = v_c.actualizado_en
   where id = p_id;
  insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, fecha_efectiva, motivo, usuario_id, nombre)
  values (v_tenant, p_id, 'cambio', to_jsonb(v_antes), to_jsonb(v_c),
          coalesce((p_datos->>'fecha_efectiva')::date, (now() at time zone 'America/Mexico_City')::date),
          trim(p_motivo), auth.uid(), public.inc_nombre_usuario());
  return p_id;
end $$;

create function public.cred_cambiar_estado(p_id uuid, p_estado text, p_fecha date, p_motivo text)
returns void language plpgsql security definer set search_path to '' as $$
declare v_antes public.cred_creditos; v_c public.cred_creditos; v_evento text;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into v_antes from public.cred_creditos where id = p_id and tenant_id = public.current_tenant_id() for update;
  if v_antes.id is null then raise exception 'BeeHuman: crédito no encontrado.'; end if;
  if length(trim(coalesce(p_motivo, ''))) = 0 then raise exception 'BeeHuman: escribe el motivo; queda en la historia.'; end if;
  if p_fecha is null then raise exception 'BeeHuman: indica la fecha efectiva.'; end if;
  v_evento := case
    when v_antes.estado = 'activo' and p_estado = 'suspendido' then 'suspension'
    when v_antes.estado = 'suspendido' and p_estado = 'activo' then 'reactivacion'
    when v_antes.estado = 'incompleto' and p_estado = 'activo' then 'activacion'
    when v_antes.estado in ('activo','suspendido','incompleto') and p_estado = 'terminado' then 'terminacion' end;
  if v_evento is null then
    raise exception 'BeeHuman: no se puede pasar de «%» a «%».', v_antes.estado, p_estado;
  end if;
  v_c := v_antes; v_c.estado := p_estado;
  if p_estado = 'terminado' then
    v_c.fecha_fin := least(coalesce(v_antes.fecha_fin, p_fecha), p_fecha);
    if v_c.fecha_inicio is not null and v_c.fecha_fin < v_c.fecha_inicio then v_c.fecha_fin := v_c.fecha_inicio; end if;
  end if;
  if p_estado = 'activo' then perform public.cred_validar(v_c); end if;
  update public.cred_creditos set estado = v_c.estado, fecha_fin = v_c.fecha_fin, actualizado_en = now() where id = p_id;
  insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, fecha_efectiva, motivo, usuario_id, nombre)
  values (v_antes.tenant_id, p_id, v_evento, to_jsonb(v_antes), to_jsonb(v_c), p_fecha, trim(p_motivo), auth.uid(), public.inc_nombre_usuario());
end $$;

-- Créditos de una persona con saldo, historia y movimientos (ficha).
create function public.cred_creditos_persona(p_personal uuid)
returns jsonb language plpgsql stable security definer set search_path to '' as $$
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  return coalesce((
    select jsonb_agg(jsonb_build_object(
      'credito', to_jsonb(c),
      'calculable', public.cred_es_calculable(c),
      'saldo', public.cred_saldo_actual(c.id),
      'empresa', e.nombre,
      'registro_patronal', rp.registro_patronal,
      'periodicidad', pz.nombre,
      'historia', (select coalesce(jsonb_agg(to_jsonb(h) order by h.creado_en desc), '[]') from public.cred_historia h where h.credito_id = c.id),
      'movimientos', (select coalesce(jsonb_agg(jsonb_build_object('importe', m.importe, 'saldo_anterior', m.saldo_anterior, 'saldo_nuevo', m.saldo_nuevo,
                         'creado_en', m.creado_en, 'periodo', p.inicio || ' – ' || p.fin) order by m.creado_en desc), '[]')
                        from public.cred_movimientos m join public.inc_periodos p on p.id = m.periodo_id where m.credito_id = c.id))
      order by (c.estado = 'terminado'), c.creado_en)
      from public.cred_creditos c
      left join public.relaciones_laborales rl on rl.id = c.relacion_laboral_id
      left join public.empresas e on e.id = rl.empresa_id
      left join public.empresas_registros_patronales rp on rp.id = rl.registro_patronal_id
      left join public.periodicidades pz on pz.id = c.periodicidad_id
     where c.personal_id = p_personal and c.tenant_id = public.current_tenant_id()), '[]'::jsonb);
end $$;

-- ---------------------------------------------------------------------
-- 5. Descuentos del periodo (Revisión de Nómina)
-- ---------------------------------------------------------------------
create function public.cred_descuentos_periodo(p_periodo uuid)
returns jsonb language plpgsql security definer set search_path to '' as $$
declare pe record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  perform public.cred_sincronizar_periodo(p_periodo);
  return jsonb_build_object(
    'procesado', pe.procesado_en is not null,
    'sin_periodicidad', pe.periodicidad_id is null,
    'lineas', (select coalesce(jsonb_agg(jsonb_build_object(
        'id', d.id, 'credito_id', d.credito_id, 'persona', p.nombre_completo, 'empleado_id', p.empleado_id,
        'tipo', c.tipo, 'concepto', c.concepto, 'referencia', c.referencia,
        'sugerido', d.sugerido, 'final', d.final, 'origen', d.origen, 'detalle', d.detalle,
        'saldo', public.cred_saldo_actual(c.id), 'monto_total', c.monto_total,
        'disponible', case when d.origen <> 'descartado' then public.cred_disponible(c.id, d.periodo_id) end,
        'ajustes', (select coalesce(jsonb_agg(jsonb_build_object('anterior', a.anterior, 'nuevo', a.nuevo, 'motivo', a.motivo, 'nombre', a.nombre, 'creado_en', a.creado_en) order by a.creado_en), '[]')
                      from public.cred_descuentos_ajustes a where a.descuento_id = d.id))
        order by (d.origen = 'descartado'), p.nombre_completo, c.tipo), '[]')
      from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id join public.personal p on p.id = d.personal_id
     where d.periodo_id = p_periodo),
    'informativos', (select coalesce(jsonb_agg(jsonb_build_object(
        'persona', p.nombre_completo, 'empleado_id', p.empleado_id, 'tipo', c.tipo, 'referencia', c.referencia, 'estado', c.estado,
        'infonavit_tipo', c.infonavit_tipo, 'infonavit_valor', c.infonavit_valor, 'infonavit_fecha_aviso', c.infonavit_fecha_aviso,
        'pension_forma', c.pension_forma, 'pension_valor', c.pension_valor)
        order by p.nombre_completo, c.tipo), '[]')
      from public.cred_creditos c join public.personal p on p.id = c.personal_id
     where c.tenant_id = pe.tenant_id and c.estado in ('activo','incompleto') and not public.cred_es_calculable(c)
       and (c.fecha_inicio is null or c.fecha_inicio <= pe.fin) and (c.fecha_fin is null or c.fecha_fin >= pe.inicio)
       and (exists (select 1 from public.relaciones_laborales rl where rl.id = c.relacion_laboral_id and rl.empresa_id = pe.empresa_id)
            or (c.relacion_laboral_id is null and public.inc_relacion_en(c.personal_id, pe.empresa_id, pe.inicio) is not null))),
    'avisos', (select coalesce(jsonb_agg(jsonb_build_object('persona', p.nombre_completo, 'tipo', c.tipo, 'referencia', c.referencia, 'aviso', a.aviso)
        order by p.nombre_completo), '[]')
      from public.cred_creditos c join public.personal p on p.id = c.personal_id
      join public.relaciones_laborales rl on rl.id = c.relacion_laboral_id
      cross join lateral (select case
          when rl.estado = 'anulada' or (rl.fecha_baja is not null and rl.fecha_baja < pe.inicio)
            then 'La relación laboral del crédito terminó; confirma si el crédito debe terminarse'
          when public.cred_es_calculable(c) and c.monto_total is not null and public.cred_saldo_actual(c.id) <= 0
            then 'Saldo en cero'
          when public.cred_es_calculable(c) and (pe.periodicidad_id is null or pe.periodicidad_id <> c.periodicidad_id)
            then 'La periodicidad del crédito no coincide con la del periodo; no se propone descuento'
        end aviso) a
     where c.tenant_id = pe.tenant_id and c.estado = 'activo' and rl.empresa_id = pe.empresa_id and a.aviso is not null
       and c.fecha_inicio <= pe.fin and (c.fecha_fin is null or c.fecha_fin >= pe.inicio)));
end $$;

create function public.cred_decidir_descuento(p_id uuid, p_final numeric, p_motivo text default null)
returns void language plpgsql security definer set search_path to '' as $$
declare d record; v_nuevo numeric; v_origen text; v_disp numeric;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  -- Primero el crédito y después la línea (mismo orden que el recálculo y el
  -- procesado): una segunda operación sobre el mismo crédito espera aquí y,
  -- al seguir, ve lo que la primera comprometió.
  perform 1 from public.cred_creditos c
   where c.id = (select x.credito_id from public.cred_descuentos x where x.id = p_id and x.tenant_id = public.current_tenant_id())
   for update;
  select * into d from public.cred_descuentos where id = p_id and tenant_id = public.current_tenant_id() for update;
  if d.id is null then raise exception 'BeeHuman: descuento no encontrado.'; end if;
  if exists (select 1 from public.inc_periodos where id = d.periodo_id and procesado_en is not null) then
    raise exception 'BeeHuman: el periodo ya se procesó; sus descuentos no se modifican.';
  end if;
  if d.origen = 'descartado' then raise exception 'BeeHuman: este descuento ya no aplica en el periodo.'; end if;
  if p_final is not null and p_final < 0 then raise exception 'BeeHuman: el descuento no puede ser negativo.'; end if;
  v_nuevo  := coalesce(round(p_final, 2), d.sugerido);
  v_origen := case when p_final is null or round(p_final, 2) = d.sugerido then 'aceptado' else 'modificado' end;
  -- Aceptar o modificar: nunca más que el saldo disponible (saldo real menos
  -- lo comprometido en otros periodos abiertos).
  v_disp := public.cred_disponible(d.credito_id, d.periodo_id);
  if v_disp is not null and v_nuevo > v_disp then
    raise exception 'BeeHuman: el descuento no puede exceder el saldo disponible del crédito ($%: saldo $% menos $% comprometidos en otros periodos abiertos).',
      to_char(greatest(v_disp, 0), 'FM999,999,990.00'), to_char(public.cred_saldo_actual(d.credito_id), 'FM999,999,990.00'),
      to_char(public.cred_saldo_actual(d.credito_id) - v_disp, 'FM999,999,990.00');
  end if;
  if (v_origen = 'modificado' or d.origen = 'modificado') and v_nuevo is distinct from d.final then
    if length(trim(coalesce(p_motivo, ''))) = 0 then
      raise exception 'BeeHuman: escribe el motivo del ajuste; queda en la bitácora.';
    end if;
    insert into public.cred_descuentos_ajustes (tenant_id, descuento_id, anterior, nuevo, origen_anterior, origen_nuevo, motivo, usuario_id, nombre)
    values (d.tenant_id, d.id, coalesce(d.final, d.sugerido), v_nuevo, d.origen, v_origen, trim(p_motivo), auth.uid(), public.inc_nombre_usuario());
  end if;
  update public.cred_descuentos set final = v_nuevo, origen = v_origen, decidido_por = auth.uid(), decidido_en = now() where id = p_id;
end $$;

create function public.cred_aceptar_descuentos(p_periodo uuid) returns integer
language plpgsql security definer set search_path to '' as $$
declare v_n integer;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  if not exists (select 1 from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id() and procesado_en is null) then
    raise exception 'BeeHuman: periodo no encontrado o ya procesado.';
  end if;
  perform 1 from public.cred_creditos c
   where c.id in (select d.credito_id from public.cred_descuentos d where d.periodo_id = p_periodo and d.origen = 'pendiente')
   order by c.id for update;
  -- Solo las que caben en el saldo disponible; las demás quedan por decidir.
  update public.cred_descuentos d set final = sugerido, origen = 'aceptado', decidido_por = auth.uid(), decidido_en = now()
   where d.periodo_id = p_periodo and d.origen = 'pendiente' and d.sugerido is not null
     and (public.cred_disponible(d.credito_id, p_periodo) is null or d.sugerido <= public.cred_disponible(d.credito_id, p_periodo));
  get diagnostics v_n = row_count;
  return v_n;
end $$;

-- ---------------------------------------------------------------------
-- 6. Faltantes y procesado (cambian; originales en respaldo)
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

create or replace function public.inc_marcar_procesado(p_periodo uuid)
returns text language plpgsql security definer set search_path to '' as $$
declare pe record; v_falta text; v_n integer; r record; v_saldo numeric;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id() for update;
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  if pe.procesado_en is not null then
    return 'Ya estaba procesado el ' || to_char(pe.procesado_en, 'YYYY-MM-DD HH24:MI') || '; no se registró de nuevo.';
  end if;
  -- B5: bloquear los créditos involucrados (procesados concurrentes de otros
  -- periodos esperan) y recalcular las propuestas con el saldo real.
  perform 1 from public.cred_creditos c
   where c.id in (select x.credito_id from public.cred_propuestas(p_periodo) x
                  union select d.credito_id from public.cred_descuentos d where d.periodo_id = p_periodo)
   order by c.id for update;
  perform public.cred_sincronizar_periodo(p_periodo);
  select count(*), string_agg(f.detalle, '; ') into v_n, v_falta from public.inc_faltantes_procesar(p_periodo) f;
  if v_n > 0 then
    raise exception 'BeeHuman: no se puede procesar; faltan % pendiente(s): %', v_n, left(v_falta, 1500);
  end if;
  update public.inc_periodos set procesado_en = now(), procesado_por = auth.uid() where id = p_periodo;
  update public.inc_hojas set estado = 'procesada' where periodo_id = p_periodo and estado = 'enviada';
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre)
  values (pe.tenant_id, p_periodo, 'procesado', auth.uid(), public.inc_nombre_usuario());
  -- B5: el saldo baja aquí y solo aquí, una vez por crédito y periodo.
  for r in select d.id, d.credito_id, d.final from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id
            where d.periodo_id = p_periodo and d.origen in ('aceptado','modificado') and c.monto_total is not null and d.final > 0
            order by d.credito_id loop
    v_saldo := public.cred_saldo_actual(r.credito_id);
    if r.final > public.cred_disponible(r.credito_id, p_periodo) then
      raise exception 'BeeHuman: el descuento excede el saldo disponible del crédito; no se procesó.';
    end if;
    insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo, usuario_id)
    values (pe.tenant_id, r.credito_id, p_periodo, r.id, r.final, v_saldo, v_saldo - r.final, auth.uid());
    if v_saldo - r.final = 0 then
      insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, fecha_efectiva, motivo, usuario_id, nombre)
      select pe.tenant_id, c.id, 'terminacion_saldo', to_jsonb(c), to_jsonb(c) || jsonb_build_object('estado', 'terminado', 'fecha_fin', pe.fin),
             pe.fin, 'Saldo liquidado al procesar el periodo ' || pe.inicio || ' – ' || pe.fin, auth.uid(), public.inc_nombre_usuario()
        from public.cred_creditos c where c.id = r.credito_id and c.estado <> 'terminado';
      update public.cred_creditos set estado = 'terminado', fecha_fin = least(coalesce(fecha_fin, pe.fin), pe.fin), actualizado_en = now()
       where id = r.credito_id and estado <> 'terminado';
    end if;
  end loop;
  return 'Periodo marcado como procesado.';
end $$;

-- Etiqueta corta de un crédito (faltantes y pantallas).
create function public.cred_etiqueta(c public.cred_creditos) returns text
language sql immutable set search_path to '' as $$
  select case c.tipo when 'infonavit' then 'INFONAVIT' when 'fonacot' then 'FONACOT' when 'prestamo' then 'Préstamo'
                     when 'anticipo' then 'Anticipo' when 'pension' then 'Pensión alimenticia' else coalesce(c.concepto, 'Descuento') end
         || coalesce(' ' || nullif(trim(c.referencia), ''), '')
$$;

-- ---------------------------------------------------------------------
-- 7. Permisos de funciones
-- ---------------------------------------------------------------------
revoke all on function public.cred_es_calculable(public.cred_creditos), public.cred_saldo_actual(uuid),
  public.cred_disponible(uuid, uuid), public.cred_aplica(public.cred_creditos, public.inc_periodos), public.cred_propuestas(uuid),
  public.cred_sincronizar_periodo(uuid), public.cred_validar(public.cred_creditos),
  public.cred_etiqueta(public.cred_creditos), public.cred_descuentos_proteger()
  from public, anon, authenticated;
revoke all on function public.cred_guardar(uuid, jsonb, text), public.cred_cambiar_estado(uuid, text, date, text),
  public.cred_creditos_persona(uuid), public.cred_descuentos_periodo(uuid),
  public.cred_decidir_descuento(uuid, numeric, text), public.cred_aceptar_descuentos(uuid)
  from public, anon;
grant execute on function public.cred_guardar(uuid, jsonb, text), public.cred_cambiar_estado(uuid, text, date, text),
  public.cred_creditos_persona(uuid), public.cred_descuentos_periodo(uuid),
  public.cred_decidir_descuento(uuid, numeric, text), public.cred_aceptar_descuentos(uuid)
  to authenticated;

-- ---------------------------------------------------------------------
-- 8. Conversión de personal.no_fonacot (el campo no se borra)
-- ---------------------------------------------------------------------
with origen as (
  select p.id personal_id, p.tenant_id, trim(p.no_fonacot) referencia,
         (select case when count(*) = 1 then min(rl.id::text)::uuid end from public.relaciones_laborales rl
           where rl.personal_id = p.id and rl.estado = 'vigente' and rl.fecha_baja is null) relacion
    from public.personal p where coalesce(trim(p.no_fonacot), '') <> ''
), nuevos as (
  insert into public.cred_creditos (tenant_id, personal_id, relacion_laboral_id, tipo, referencia, estado, origen, notas)
  select o.tenant_id, o.personal_id, o.relacion, 'fonacot', o.referencia, 'incompleto', 'conversion_no_fonacot',
         'Convertido del campo «No. FONACOT» del expediente. Completa relación, periodicidad y retención de la cédula para activarlo.'
    from origen o
  returning *
)
insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, motivo, nombre)
select n.tenant_id, n.id, 'conversion', jsonb_build_object('personal.no_fonacot', n.referencia), to_jsonb(n),
       'Conversión del campo No. FONACOT del expediente (B5). El valor original se conserva en personal.no_fonacot.', 'BeeHuman (migración B5)'
  from nuevos n;

commit;
