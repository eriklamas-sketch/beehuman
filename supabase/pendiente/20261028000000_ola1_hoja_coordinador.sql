-- =====================================================================
-- BeeHuman · Ola 1 · Hoja semanal del coordinador
-- Archivo: supabase/migrations/20261028000000_ola1_hoja_coordinador.sql
-- DESTINO: SOLO beehuman-pruebas (sflvpgkmtaxzogpgetxn). NO producción.
-- Aplicada en beehuman-pruebas con autorización de Erik (27-oct-2026).
--
-- Qué hace:
--   * 13 tablas nuevas con prefijo inc_ (no modifica tablas existentes).
--   * 2 disparadores nuevos sobre public.personal (solo registran el
--     historial de asignación de coordinador; no cambian datos de personal).
--   * Políticas por rol, funciones de flujo y función de cálculo.
-- Principios:
--   * Ningún rol escribe directamente estados, versiones, importes ni
--     eventos: solo a través de funciones con reglas explícitas.
--   * Importes derivados del sueldo: solo los leen Administrador y Nómina.
--   * Versiones y eventos no se pueden editar ni borrar (ni siquiera el
--     dueño de la tabla mediante UPDATE/DELETE: lo impide un disparador).
-- =====================================================================
begin;

do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'public')
     and exists (select 1 from information_schema.tables where table_schema='public' and table_name='inc_hojas') then
    raise exception 'DETENIDO: la Ola 1 ya está aplicada en esta base.';
  end if;
end $$;

-- btree_gist permite la restricción de "sin traslapes" por persona.
create extension if not exists btree_gist with schema extensions;

-- ---------------------------------------------------------------------
-- 1. Configuración por empresa
-- ---------------------------------------------------------------------
create table public.inc_parametros (
  empresa_id              uuid primary key references public.empresas(id),
  tenant_id               uuid not null references public.tenants(id),
  base_calculo            text not null default 'mixto' check (base_calculo in ('mixto','bruto','neto')),
  jornada_horas           numeric(5,2) not null default 8 check (jornada_horas > 0),
  umbral_triples_semana   numeric(5,2) not null default 9 check (umbral_triples_semana >= 0),
  factor_triple           numeric(6,3) not null default 3 check (factor_triple > 0),
  aviso_horas_dia         numeric(5,2) not null default 3,
  aviso_dias_semana       integer not null default 3,
  prima_dominical_pct     numeric(6,3) not null default 25 check (prima_dominical_pct >= 0),
  responsable_nomina_user uuid references auth.users(id),
  responsable_rh_user     uuid references auth.users(id),
  -- Primer día desde el que BeeHuman tiene historial de asignaciones de
  -- coordinador para esta empresa. No se crean hojas que empiecen antes.
  inicio_historial        date not null default current_date,
  actualizado_por         uuid,
  actualizado_en          timestamptz not null default now()
);

create table public.inc_conceptos (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id),
  empresa_id  uuid not null references public.empresas(id),
  nombre      text not null,
  abreviatura text not null,
  unidad      text not null check (unidad in ('horas','turnos','dias','importe')),
  tipo        text not null check (tipo in ('horas_extra','domingo','turno','descuento','otro')),
  modo        text not null check (modo in ('beehuman','tarifa','sin_importe')),
  tarifa      numeric(12,2) check (tarifa is null or tarifa >= 0),   -- tarifa general de la empresa
  factor      numeric(8,4),          -- horas extra: 2 (doble). turno en % de prima: 0.25
  activo      boolean not null default true,
  orden       integer not null default 0,
  creado_en   timestamptz not null default now(),
  unique (empresa_id, abreviatura),
  check (modo <> 'tarifa' or tarifa is not null),
  check (tipo <> 'descuento' or (unidad = 'importe' and modo = 'tarifa' and tarifa = 1))
);

create table public.inc_tarifas_area (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id),
  concepto_id uuid not null references public.inc_conceptos(id),
  area_id     uuid not null references public.areas(id),
  tarifa      numeric(12,2) not null check (tarifa >= 0),
  unique (concepto_id, area_id)
);

-- ---------------------------------------------------------------------
-- 2. Historial de asignación de coordinador (bloqueante 1)
--    Un renglón = la persona estuvo asignada a ese coordinador del día
--    "desde" al día "hasta" (inclusive; hasta nulo = vigente).
--    La restricción EXCLUDE impide traslapes: una persona nunca tiene dos
--    coordinadores el mismo día.
-- ---------------------------------------------------------------------
create table public.inc_asignaciones (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references public.tenants(id),
  personal_id    uuid not null references public.personal(id),
  coordinador_id uuid not null references public.personal(id),
  desde          date not null,
  hasta          date,
  origen         text not null check (origen in ('carga_inicial','cambio_expediente','registro_nomina')),
  nota           text,
  registrado_por uuid,
  registrado_en  timestamptz not null default now(),
  check (hasta is null or hasta >= desde),
  check (personal_id <> coordinador_id),
  exclude using gist (personal_id with =, daterange(desde, hasta, '[]') with &&)
);
create index on public.inc_asignaciones (coordinador_id, desde);

-- ---------------------------------------------------------------------
-- 3. Periodos, hojas y captura (el "borrador vivo")
-- ---------------------------------------------------------------------
create table public.inc_periodos (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references public.tenants(id),
  empresa_id      uuid not null references public.empresas(id),
  periodicidad_id uuid references public.periodicidades(id),
  inicio          date not null,
  fin             date not null,
  procesado_en    timestamptz,
  procesado_por   uuid,
  creado_por      uuid,
  creado_en       timestamptz not null default now(),
  check (fin >= inicio and fin - inicio <= 31),
  exclude using gist (empresa_id with =, daterange(inicio, fin, '[]') with &&)
);

create table public.inc_hojas (
  id                      uuid primary key default gen_random_uuid(),
  tenant_id               uuid not null references public.tenants(id),
  periodo_id              uuid not null references public.inc_periodos(id),
  coordinador_id          uuid not null references public.personal(id),
  tipo                    text not null default 'normal' check (tipo in ('normal','complemento')),
  hoja_raiz_id            uuid not null references public.inc_hojas(id),  -- normal: ella misma
  posterior_procesamiento boolean not null default false,
  estado                  text not null default 'borrador' check (estado in ('borrador','enviada','devuelta','procesada')),
  version_actual          integer not null default 0,
  observacion_general     text,
  creado_por              uuid,
  creado_en               timestamptz not null default now(),
  check ((tipo = 'normal') = (hoja_raiz_id = id)),
  check (tipo = 'complemento' or not posterior_procesamiento)
);
-- Una sola hoja normal por coordinador y periodo.
create unique index inc_hojas_una_normal on public.inc_hojas (periodo_id, coordinador_id) where tipo = 'normal';

-- Códigos del día y proyecto/centro de costo del día. Solo se guardan días
-- con algo distinto de "asistencia normal en el proyecto de la ficha".
create table public.inc_celdas (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references public.tenants(id),
  hoja_id         uuid not null references public.inc_hojas(id),
  hoja_raiz_id    uuid not null references public.inc_hojas(id),
  periodo_id      uuid not null references public.inc_periodos(id),
  es_normal       boolean not null,
  personal_id     uuid not null references public.personal(id),
  fecha           date not null,
  codigo          text check (codigo in ('F','I','D','V','P')),
  proyecto_id     uuid references public.proyectos(id),
  centro_costo_id uuid references public.centros_costo(id),
  check (codigo is not null or proyecto_id is not null or centro_costo_id is not null)
);
-- (a) Dentro de una hoja: un renglón por persona y día.
create unique index inc_celdas_hoja_dia on public.inc_celdas (hoja_id, personal_id, fecha);
-- (b) Entre hojas normales del mismo periodo: una persona-día en una sola hoja.
create unique index inc_celdas_periodo_dia on public.inc_celdas (periodo_id, personal_id, fecha) where es_normal;
-- (c) Entre la hoja normal y sus complementos: un complemento no repite un día ya registrado.
create unique index inc_celdas_raiz_dia on public.inc_celdas (hoja_raiz_id, personal_id, fecha);

create table public.inc_cantidades (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id),
  hoja_id               uuid not null references public.inc_hojas(id),
  hoja_raiz_id          uuid not null references public.inc_hojas(id),
  periodo_id            uuid not null references public.inc_periodos(id),
  es_normal             boolean not null,
  personal_id           uuid not null references public.personal(id),
  fecha                 date not null,
  concepto_id           uuid not null references public.inc_conceptos(id),
  cantidad              numeric(12,2) not null,
  tipo_linea            text not null default 'captura' check (tipo_linea in ('captura','ajuste')),
  linea_corregida_id    uuid references public.inc_cantidades(id),
  motivo                text,
  conformidad_declarada boolean,
  conformidad_por       uuid,
  conformidad_en        timestamptz,
  check (tipo_linea = 'captura' or linea_corregida_id is not null),
  check (tipo_linea = 'ajuste' or cantidad > 0)
);
-- (d) Captura: persona + día + concepto una sola vez entre la hoja normal y
--     todos sus complementos (no se paga dos veces lo mismo).
create unique index inc_cant_captura on public.inc_cantidades (hoja_raiz_id, personal_id, fecha, concepto_id) where tipo_linea = 'captura';
-- (e) Entre hojas normales del periodo: persona + día + concepto en una sola hoja.
create unique index inc_cant_periodo on public.inc_cantidades (periodo_id, personal_id, fecha, concepto_id) where es_normal and tipo_linea = 'captura';
-- (f) Ajuste posterior: una sola corrección por línea original en cada complemento.
create unique index inc_cant_ajuste on public.inc_cantidades (hoja_id, linea_corregida_id) where tipo_linea = 'ajuste';

create table public.inc_observaciones (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id),
  hoja_id     uuid not null references public.inc_hojas(id),
  personal_id uuid not null references public.personal(id),
  texto       text not null,
  unique (hoja_id, personal_id)
);

-- ---------------------------------------------------------------------
-- 4. Versiones congeladas, sueldos manuales, importes y eventos
-- ---------------------------------------------------------------------
create table public.inc_versiones (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references public.tenants(id),
  hoja_id    uuid not null references public.inc_hojas(id),
  numero     integer not null check (numero >= 1),
  datos      jsonb not null,     -- celdas, cantidades, observaciones y configuración vigente (sin sueldos)
  creada_por uuid,
  creada_en  timestamptz not null default now(),
  unique (hoja_id, numero)
);

create table public.inc_sueldos_manuales (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.tenants(id),
  periodo_id    uuid not null references public.inc_periodos(id),
  personal_id   uuid not null references public.personal(id),
  sueldo_diario numeric(12,2) not null check (sueldo_diario > 0),
  capturado_por uuid,
  capturado_en  timestamptz not null default now(),
  unique (periodo_id, personal_id)
);

create table public.inc_importes (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.tenants(id),
  version_id    uuid not null references public.inc_versiones(id),
  personal_id   uuid not null references public.personal(id),
  concepto_id   uuid not null references public.inc_conceptos(id),
  cantidad      numeric(12,2) not null,
  sugerido      numeric(14,2),
  final         numeric(14,2),
  origen        text not null check (origen in ('pendiente','aceptado','modificado','sin_sueldo','sin_importe')),
  usa_sueldo    boolean not null,
  base_calculo  text,
  detalle       jsonb not null default '{}'::jsonb,
  decidido_por  uuid,
  decidido_en   timestamptz,
  unique (version_id, personal_id, concepto_id)
);

create table public.inc_eventos (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references public.tenants(id),
  hoja_id    uuid references public.inc_hojas(id),
  periodo_id uuid not null references public.inc_periodos(id),
  version_id uuid references public.inc_versiones(id),
  tipo       text not null check (tipo in ('envio','firma_nomina','firma_rh','devolucion','exportacion','procesado','complemento')),
  usuario_id uuid not null,
  nombre     text,               -- nombre de quien actuó, congelado en ese momento
  motivo     text,
  creado_en  timestamptz not null default now(),
  check (tipo <> 'devolucion' or length(trim(coalesce(motivo,''))) > 0)
);
create unique index inc_eventos_firma_unica on public.inc_eventos (version_id, tipo) where tipo in ('firma_nomina','firma_rh');
create unique index inc_eventos_procesado_unico on public.inc_eventos (periodo_id) where tipo = 'procesado' and hoja_id is null;

-- ---------------------------------------------------------------------
-- 5. Inmutabilidad: versiones y eventos no se editan ni se borran;
--    importes no se borran. Aplica a cualquier rol, incluido el dueño.
-- ---------------------------------------------------------------------
create function public.inc_bloquear_cambios() returns trigger
language plpgsql set search_path to '' as $$
begin
  raise exception 'BeeHuman: % es un registro histórico y no se puede % .', tg_table_name, lower(tg_op);
end $$;
create trigger trg_inc_versiones_inmutables before update or delete on public.inc_versiones for each row execute function public.inc_bloquear_cambios();
create trigger trg_inc_eventos_inmutables   before update or delete on public.inc_eventos   for each row execute function public.inc_bloquear_cambios();
create trigger trg_inc_importes_sin_borrar  before delete on public.inc_importes            for each row execute function public.inc_bloquear_cambios();

-- ---------------------------------------------------------------------
-- 6. Funciones auxiliares
-- ---------------------------------------------------------------------
-- Coordinador vigente de una persona en una fecha (null si no hay historial).
create function public.inc_coordinador_en(p_personal uuid, p_fecha date) returns uuid
language sql stable security definer set search_path to '' as $$
  select a.coordinador_id from public.inc_asignaciones a
  where a.personal_id = p_personal and p_fecha >= a.desde and (a.hasta is null or p_fecha <= a.hasta)
$$;

-- ¿La hoja admite cambios del coordinador? (borrador o devuelta)
create function public.inc_hoja_editable(p_hoja uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select exists (select 1 from public.inc_hojas h where h.id = p_hoja and h.estado in ('borrador','devuelta'))
$$;

-- ¿El coordinador indicado soy yo? (sin exponer current_personal_id, que en
-- beehuman-pruebas no es ejecutable por authenticated)
create function public.inc_soy(p_personal uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select public.tiene_rol('coordinador') and public.current_personal_id() is not null
         and public.current_personal_id() = p_personal
$$;

-- ¿Es mía la hoja? (coordinador dueño)
create function public.inc_es_mi_hoja(p_hoja uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select exists (select 1 from public.inc_hojas h
                 where h.id = p_hoja and h.tenant_id = public.current_tenant_id()
                   and public.tiene_rol('coordinador')
                   and h.coordinador_id = public.current_personal_id())
$$;

-- Consulta ve hojas cuyo personal está en su alcance.
create function public.inc_hoja_en_alcance(p_hoja uuid) returns boolean
language sql stable security definer set search_path to '' as $$
  select exists (select 1 from public.inc_hojas h join public.inc_periodos pe on pe.id = h.periodo_id
                 join public.usuario_alcances a on a.tenant_id = h.tenant_id and a.user_id = auth.uid()
                   and (a.empresa_id is null or a.empresa_id = pe.empresa_id)
                 where h.id = p_hoja and h.tenant_id = public.current_tenant_id())
$$;

-- Validación de cada renglón capturado (celdas y cantidades): fecha dentro
-- del periodo, persona de la empresa, asignada a ese coordinador ese día,
-- sin baja previa, y hoja editable. Rellena columnas de control.
create function public.inc_validar_captura() returns trigger
language plpgsql security definer set search_path to '' as $$
declare h record; pe record; p record; c record;
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
  select * into p from public.personal where id = new.personal_id;
  new.tenant_id := h.tenant_id; new.hoja_raiz_id := h.hoja_raiz_id;
  new.periodo_id := h.periodo_id; new.es_normal := (h.tipo = 'normal');
  if new.fecha < pe.inicio or new.fecha > pe.fin then
    raise exception 'BeeHuman: la fecha % está fuera del periodo.', new.fecha;
  end if;
  if p.empresa_id is distinct from pe.empresa_id then
    raise exception 'BeeHuman: la persona no pertenece a la empresa del periodo.';
  end if;
  if public.inc_coordinador_en(new.personal_id, new.fecha) is distinct from h.coordinador_id then
    raise exception 'BeeHuman: la persona no estaba asignada a este coordinador el %.', new.fecha;
  end if;
  if p.fecha_baja is not null and new.fecha > p.fecha_baja then
    raise exception 'BeeHuman: la persona causó baja el %.', p.fecha_baja;
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
create trigger trg_inc_celdas_validar before insert or update or delete on public.inc_celdas
  for each row execute function public.inc_validar_captura();
create trigger trg_inc_cantidades_validar before insert or update or delete on public.inc_cantidades
  for each row execute function public.inc_validar_captura();
create function public.inc_validar_observacion() returns trigger
language plpgsql security definer set search_path to '' as $$
begin
  if not public.inc_hoja_editable(coalesce(new.hoja_id, old.hoja_id)) then
    raise exception 'BeeHuman: la hoja ya fue enviada; corrige con devolución o complemento.';
  end if;
  if tg_op = 'DELETE' then return old; end if;
  new.tenant_id := (select tenant_id from public.inc_hojas where id = new.hoja_id);
  return new;
end $$;
create trigger trg_inc_observaciones_validar before insert or update or delete on public.inc_observaciones
  for each row execute function public.inc_validar_observacion();

-- ---------------------------------------------------------------------
-- 7. Registro de asignaciones (bloqueante 1)
-- ---------------------------------------------------------------------
-- Núcleo: cierra el tramo vigente el día anterior a p_desde y abre uno nuevo.
-- Rechaza fechas que choquen con días ya enviados a otro coordinador.
create function public.inc_registrar_asignacion_nucleo(
  p_personal uuid, p_coordinador uuid, p_desde date, p_origen text, p_nota text)
returns void language plpgsql security definer set search_path to '' as $$
declare v_tenant uuid; v_actual record;
begin
  select tenant_id into v_tenant from public.personal where id = p_personal;
  if exists (
    select 1 from public.inc_celdas c join public.inc_hojas h on h.id = c.hoja_id
    where c.personal_id = p_personal and c.fecha >= p_desde and h.estado in ('enviada','procesada')
      and h.coordinador_id is distinct from p_coordinador
    union all
    select 1 from public.inc_cantidades q join public.inc_hojas h on h.id = q.hoja_id
    where q.personal_id = p_personal and q.fecha >= p_desde and h.estado in ('enviada','procesada')
      and h.coordinador_id is distinct from p_coordinador) then
    raise exception 'BeeHuman: hay hojas enviadas de otro coordinador desde el %; la fecha efectiva no puede ser anterior.', p_desde;
  end if;
  -- Tramos que empiezan en o después de p_desde: se reemplazan.
  delete from public.inc_asignaciones where personal_id = p_personal and desde >= p_desde;
  -- Tramo que cubre p_desde: se cierra el día anterior.
  update public.inc_asignaciones set hasta = p_desde - 1
   where personal_id = p_personal and desde < p_desde and (hasta is null or hasta >= p_desde);
  if p_coordinador is not null then
    insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota, registrado_por)
    values (v_tenant, p_personal, p_coordinador, p_desde, p_origen, p_nota, auth.uid());
  end if;
end $$;
revoke all on function public.inc_registrar_asignacion_nucleo(uuid,uuid,date,text,text) from public, anon, authenticated;

-- Cambio de coordinador desde el expediente: la app no envía fecha efectiva,
-- así que la fecha efectiva es el día en que se guardó el cambio.
create function public.inc_asignacion_desde_expediente() returns trigger
language plpgsql security definer set search_path to '' as $$
begin
  if tg_op = 'INSERT' and new.coordinador_id is null then return new; end if;
  -- Una persona que se asigna a sí misma no entra al historial (no se bloquea el guardado).
  if new.coordinador_id = new.id then return new; end if;
  if tg_op = 'UPDATE' and new.coordinador_id is not distinct from old.coordinador_id then return new; end if;
  if new.coordinador_id is null and not exists
     (select 1 from public.inc_asignaciones where personal_id = new.id) then return new; end if;
  perform public.inc_registrar_asignacion_nucleo(new.id, new.coordinador_id, current_date,
          'cambio_expediente', 'Fecha efectiva = fecha de registro del cambio en el expediente');
  return new;
end $$;
create trigger trg_inc_asignacion_alta   after insert on public.personal
  for each row execute function public.inc_asignacion_desde_expediente();
create trigger trg_inc_asignacion_cambio after update of coordinador_id on public.personal
  for each row execute function public.inc_asignacion_desde_expediente();

-- Registro explícito con fecha efectiva (Nómina/Administrador). Sirve para
-- cambios con fecha distinta a hoy y para cargar historial anterior a la
-- migración cuando Nómina lo conozca. No modifica public.personal.
create function public.inc_registrar_asignacion(p_personal uuid, p_coordinador uuid, p_desde date, p_nota text)
returns void language plpgsql security definer set search_path to '' as $$
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  if not exists (select 1 from public.personal where id = p_personal and tenant_id = public.current_tenant_id()) then
    raise exception 'BeeHuman: persona fuera de tu organización.';
  end if;
  if p_coordinador is not null and not exists (select 1 from public.personal where id = p_coordinador and tenant_id = public.current_tenant_id()) then
    raise exception 'BeeHuman: coordinador fuera de tu organización.';
  end if;
  if length(trim(coalesce(p_nota,''))) = 0 then raise exception 'BeeHuman: indica el motivo o la fuente de la fecha.'; end if;
  perform public.inc_registrar_asignacion_nucleo(p_personal, p_coordinador, p_desde, 'registro_nomina', p_nota);
end $$;

-- Carga inicial: NO se asume que la asignación actual sea la histórica.
-- Cada persona con coordinador recibe un tramo que empieza HOY (día de la
-- migración). Lo anterior queda "sin historial": no se crean hojas de esos
-- días salvo que Nómina registre la asignación con inc_registrar_asignacion.
insert into public.inc_asignaciones (tenant_id, personal_id, coordinador_id, desde, origen, nota)
select p.tenant_id, p.id, p.coordinador_id, current_date, 'carga_inicial',
       'Asignación vigente al instalar la Ola 1. fecha_asignacion registrada en la ficha: '
       || coalesce(p.fecha_asignacion::text, 'sin dato') || '. No se usa como historial.'
from public.personal p
where p.coordinador_id is not null and p.coordinador_id <> p.id;

-- ---------------------------------------------------------------------
-- 8. Flujo de la hoja
-- ---------------------------------------------------------------------
create function public.inc_nombre_usuario() returns text
language sql stable security definer set search_path to '' as $$
  select coalesce((select p.nombre_completo from public.usuarios_tenant u join public.personal p on p.id = u.personal_id
                   where u.user_id = auth.uid()),
                  (select email from auth.users where id = auth.uid()))
$$;

-- Nómina crea el periodo.
create function public.inc_crear_periodo(p_empresa uuid, p_periodicidad uuid, p_inicio date, p_fin date)
returns uuid language plpgsql security definer set search_path to '' as $$
declare v_id uuid;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  if not exists (select 1 from public.empresas where id = p_empresa and tenant_id = public.current_tenant_id()) then
    raise exception 'BeeHuman: empresa fuera de tu organización.';
  end if;
  insert into public.inc_parametros (empresa_id, tenant_id) values (p_empresa, public.current_tenant_id())
  on conflict (empresa_id) do nothing;
  if p_inicio < (select inicio_historial from public.inc_parametros where empresa_id = p_empresa) then
    raise exception 'BeeHuman: no hay historial de asignaciones antes del %; no se puede crear el periodo.',
      (select inicio_historial from public.inc_parametros where empresa_id = p_empresa);
  end if;
  insert into public.inc_periodos (tenant_id, empresa_id, periodicidad_id, inicio, fin, creado_por)
  values (public.current_tenant_id(), p_empresa, p_periodicidad, p_inicio, p_fin, auth.uid()) returning id into v_id;
  return v_id;
end $$;

-- El coordinador abre su hoja (o su complemento) del periodo.
create function public.inc_abrir_hoja(p_periodo uuid, p_complemento_de uuid default null)
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

-- Personas y días que corresponden a una hoja (para precargar la cuadrícula).
create function public.inc_personas_hoja(p_hoja uuid)
returns table (personal_id uuid, nombre_completo text, empleado_id text, area_id uuid, proyecto_id uuid, centro_costo_id uuid, fecha date)
language sql stable security definer set search_path to '' as $$
  select p.id, p.nombre_completo, p.empleado_id, p.area_id, p.proyecto_id, p.centro_costo_id, d::date
  from public.inc_hojas h
  join public.inc_periodos pe on pe.id = h.periodo_id
  cross join generate_series(pe.inicio, pe.fin, interval '1 day') d
  join public.inc_asignaciones a on a.coordinador_id = h.coordinador_id
       and d::date >= a.desde and (a.hasta is null or d::date <= a.hasta)
  join public.personal p on p.id = a.personal_id and p.empresa_id = pe.empresa_id
       and (p.fecha_baja is null or d::date <= p.fecha_baja)
  where h.id = p_hoja
    and (public.inc_es_mi_hoja(p_hoja) or public.tiene_rol('administrador','nomina'))
  order by p.nombre_completo, d
$$;

-- Envío: congela una versión nueva, registra la firma del coordinador y calcula.
create function public.inc_enviar_hoja(p_hoja uuid, p_observacion_general text default null)
returns uuid language plpgsql security definer set search_path to '' as $$
declare h record; v_ver uuid; v_num int;
begin
  if not public.inc_es_mi_hoja(p_hoja) then raise exception 'BeeHuman: solo el coordinador de la hoja la envía.'; end if;
  select * into h from public.inc_hojas where id = p_hoja for update;
  if h.estado not in ('borrador','devuelta') then raise exception 'BeeHuman: la hoja ya fue enviada.'; end if;
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
end $$;

-- Devolución con motivo (Nómina o Administrador). La versión enviada queda
-- intacta; el coordinador corrige el borrador y al reenviar nace la versión n+1.
create function public.inc_devolver_hoja(p_hoja uuid, p_motivo text, p_area text)
returns void language plpgsql security definer set search_path to '' as $$
declare h record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso para devolver.'; end if;
  if p_area not in ('nomina','rh') then raise exception 'BeeHuman: área inválida.'; end if;
  if length(trim(coalesce(p_motivo,''))) = 0 then raise exception 'BeeHuman: la devolución requiere motivo.'; end if;
  select * into h from public.inc_hojas where id = p_hoja and tenant_id = public.current_tenant_id() for update;
  if h.estado <> 'enviada' then raise exception 'BeeHuman: solo se devuelve una hoja enviada y no procesada.'; end if;
  update public.inc_hojas set estado = 'devuelta' where id = p_hoja;
  insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre, motivo)
  values (h.tenant_id, p_hoja, h.periodo_id,
          (select id from public.inc_versiones where hoja_id = p_hoja and numero = h.version_actual),
          'devolucion', auth.uid(), public.inc_nombre_usuario() || ' (' || p_area || ')', p_motivo);
end $$;

-- Firma: solo el responsable designado del área, sobre la versión vigente.
create function public.inc_firmar_hoja(p_hoja uuid, p_area text)
returns void language plpgsql security definer set search_path to '' as $$
declare h record; prm record; v_ver uuid;
begin
  select h0.* into h from public.inc_hojas h0 where h0.id = p_hoja and h0.tenant_id = public.current_tenant_id();
  if h.id is null or h.estado not in ('enviada','procesada') then raise exception 'BeeHuman: solo se firma una hoja enviada.'; end if;
  select x.* into prm from public.inc_parametros x join public.inc_periodos pe on pe.empresa_id = x.empresa_id where pe.id = h.periodo_id;
  if not public.tiene_rol('administrador','nomina')
     or (p_area = 'nomina' and prm.responsable_nomina_user is distinct from auth.uid())
     or (p_area = 'rh'     and prm.responsable_rh_user     is distinct from auth.uid())
     or p_area not in ('nomina','rh') then
    raise exception 'BeeHuman: solo el responsable designado de % puede firmar.', p_area;
  end if;
  select id into v_ver from public.inc_versiones where hoja_id = p_hoja and numero = h.version_actual;
  insert into public.inc_eventos (tenant_id, hoja_id, periodo_id, version_id, tipo, usuario_id, nombre)
  values (h.tenant_id, p_hoja, h.periodo_id, v_ver, 'firma_' || p_area, auth.uid(), public.inc_nombre_usuario());
end $$;

-- Registro de exportación (no cambia estados).
create function public.inc_registrar_exportacion(p_periodo uuid, p_detalle text)
returns void language plpgsql security definer set search_path to '' as $$
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre, motivo)
  select tenant_id, id, 'exportacion', auth.uid(), public.inc_nombre_usuario(), p_detalle
  from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id();
end $$;

-- Procesado en NOI: marca el periodo y las hojas enviadas. Idempotente:
-- si ya estaba procesado, informa y no crea otro evento.
create function public.inc_marcar_procesado(p_periodo uuid)
returns text language plpgsql security definer set search_path to '' as $$
declare pe record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id() for update;
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  if pe.procesado_en is not null then
    return 'Ya estaba procesado el ' || to_char(pe.procesado_en, 'YYYY-MM-DD HH24:MI') || '; no se registró de nuevo.';
  end if;
  if exists (select 1 from public.inc_hojas where periodo_id = p_periodo and estado = 'devuelta') then
    raise exception 'BeeHuman: hay hojas devueltas sin reenviar.';
  end if;
  update public.inc_periodos set procesado_en = now(), procesado_por = auth.uid() where id = p_periodo;
  update public.inc_hojas set estado = 'procesada' where periodo_id = p_periodo and estado = 'enviada';
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre)
  values (pe.tenant_id, p_periodo, 'procesado', auth.uid(), public.inc_nombre_usuario());
  return 'Periodo marcado como procesado.';
end $$;

-- Nómina acepta (p_final = null) o modifica el importe sugerido.
create function public.inc_decidir_importe(p_importe uuid, p_final numeric)
returns void language plpgsql security definer set search_path to '' as $$
declare i record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into i from public.inc_importes where id = p_importe and tenant_id = public.current_tenant_id() for update;
  if i.id is null then raise exception 'BeeHuman: importe no encontrado.'; end if;
  if p_final is null and i.sugerido is null then raise exception 'BeeHuman: no hay sugerencia que aceptar.'; end if;
  update public.inc_importes
     set final = coalesce(round(p_final, 2), sugerido),
         origen = case when p_final is null or round(p_final,2) = sugerido then 'aceptado' else 'modificado' end,
         decidido_por = auth.uid(), decidido_en = now()
   where id = p_importe;
end $$;

-- Sueldo diario manual para personas sin esquema (Nómina) y recálculo.
create function public.inc_capturar_sueldo_manual(p_periodo uuid, p_personal uuid, p_sueldo numeric)
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
           where h.periodo_id = p_periodo and ve.numero = h.version_actual loop
    perform public.inc_calcular_version(v.id);
  end loop;
end $$;

-- ---------------------------------------------------------------------
-- 9. Cálculo (se ejecuta en el servidor; valores exactos, redondeo final)
-- ---------------------------------------------------------------------
-- Sueldo diario según la base de la empresa. Mixto = todos los esquemas.
create function public.inc_sueldo_diario(p_personal uuid, p_periodo uuid, p_base text)
returns numeric language sql stable security definer set search_path to '' as $$
  select coalesce(
    (select m.sueldo_diario from public.inc_sueldos_manuales m where m.periodo_id = p_periodo and m.personal_id = p_personal),
    (select sum(r.sueldo / coalesce(nullif(r.dias_periodo,0), nullif(pz.dias_default,0)))
       from public.personal_registros_pago r
       join public.periodicidades pz on pz.id = r.periodicidad_id
       join public.inc_periodos pe on pe.id = p_periodo
      where r.personal_id = p_personal and r.activo
        and r.fecha_inicio <= pe.fin and (r.fecha_fin is null or r.fecha_fin >= pe.inicio)
        and (p_base = 'mixto' or r.modalidad_sueldo = p_base)
     having count(*) > 0))
$$;
revoke all on function public.inc_sueldo_diario(uuid,uuid,text) from public, anon, authenticated;

create function public.inc_calcular_version(p_version uuid)
returns void language plpgsql security definer set search_path to '' as $$
declare
  ve record; h record; pe record; prm record; r record;
  v_sd numeric; v_hora numeric; v_sug numeric; v_tarifa numeric; v_det jsonb; v_usa boolean; v_origen text;
  v_dobles numeric; v_triples numeric;
begin
  select * into ve from public.inc_versiones where id = p_version;
  select * into h  from public.inc_hojas where id = ve.hoja_id;
  select * into pe from public.inc_periodos where id = h.periodo_id;
  select * into prm from public.inc_parametros where empresa_id = pe.empresa_id;
  if prm.empresa_id is null then
    insert into public.inc_parametros (empresa_id, tenant_id) values (pe.empresa_id, pe.tenant_id) returning * into prm;
  end if;
  for r in
    select (q->>'personal_id')::uuid pid, (q->>'concepto_id')::uuid cid,
           sum((q->>'cantidad')::numeric) cant,
           jsonb_agg(jsonb_build_object('fecha', q->>'fecha', 'cantidad', (q->>'cantidad')::numeric)) dias
    from jsonb_array_elements(ve.datos->'cantidades') q
    group by 1, 2
  loop
    -- configuración congelada en la versión (no la vigente)
    declare k jsonb; ta numeric;
    begin
      select c into k from jsonb_array_elements(ve.datos->'conceptos') c where (c->>'id')::uuid = r.cid;
      select (t->>'tarifa')::numeric into ta from jsonb_array_elements(ve.datos->'tarifas_area') t
        where (t->>'concepto_id')::uuid = r.cid
          and (t->>'area_id')::uuid = (select area_id from public.personal where id = r.pid);
      v_sug := null; v_usa := false; v_origen := 'pendiente'; v_det := '{}'::jsonb; v_sd := null;
      if k->>'modo' = 'sin_importe' then
        v_origen := 'sin_importe';
      elsif k->>'tipo' = 'descuento' then
        v_sug := round(r.cant, 2);   -- importe capturado; Nómina decide si se aplica
        v_det := jsonb_build_object('regla','descuento_operativo');
      elsif k->>'tipo' = 'domingo' and (ta is not null or k->>'tarifa' is not null) then
        v_tarifa := coalesce(ta, (k->>'tarifa')::numeric);
        v_sug := round(r.cant * v_tarifa, 2);
        v_det := jsonb_build_object('regla', case when ta is not null then 'tarifa_area' else 'tarifa_empresa' end, 'tarifa', v_tarifa);
      elsif k->>'modo' = 'tarifa' then
        v_tarifa := coalesce(ta, (k->>'tarifa')::numeric);
        v_sug := round(r.cant * v_tarifa, 2);
        v_det := jsonb_build_object('regla', case when ta is not null then 'tarifa_area' else 'tarifa_empresa' end, 'tarifa', v_tarifa);
      else
        -- modo beehuman: requiere sueldo
        v_usa := true;
        v_sd := public.inc_sueldo_diario(r.pid, pe.id, (ve.datos->'parametros'->>'base_calculo'));
        if v_sd is null then
          v_origen := 'sin_sueldo';
        elsif k->>'tipo' = 'horas_extra' then
          v_hora := v_sd / (ve.datos->'parametros'->>'jornada_horas')::numeric;
          select coalesce(sum(least(s.h, (ve.datos->'parametros'->>'umbral_triples_semana')::numeric)),0),
                 coalesce(sum(greatest(s.h - (ve.datos->'parametros'->>'umbral_triples_semana')::numeric, 0)),0)
            into v_dobles, v_triples
            from (select date_trunc('week', (d->>'fecha')::date) sem, sum((d->>'cantidad')::numeric) h
                  from jsonb_array_elements(r.dias) d group by 1) s;
          v_sug := round(v_hora * (v_dobles * coalesce((k->>'factor')::numeric, 2)
                                 + v_triples * (ve.datos->'parametros'->>'factor_triple')::numeric), 2);
          v_det := jsonb_build_object('regla','horas_extra','horas_dobles',v_dobles,'horas_triples',v_triples);
        elsif k->>'tipo' = 'domingo' then
          v_sug := round(r.cant * v_sd * (ve.datos->'parametros'->>'prima_dominical_pct')::numeric / 100, 2);
          v_det := jsonb_build_object('regla','prima_dominical','pct',(ve.datos->'parametros'->>'prima_dominical_pct')::numeric);
        else
          v_sug := round(r.cant * v_sd * coalesce((k->>'factor')::numeric, 1), 2);
          v_det := jsonb_build_object('regla','porcentaje_sueldo','factor',(k->>'factor')::numeric);
        end if;
      end if;
      insert into public.inc_importes (tenant_id, version_id, personal_id, concepto_id, cantidad, sugerido, final,
                                       origen, usa_sueldo, base_calculo, detalle)
      values (ve.tenant_id, p_version, r.pid, r.cid, r.cant, v_sug,
              case when v_usa or k->>'tipo' = 'descuento' then null else v_sug end,
              case when v_origen in ('sin_sueldo','sin_importe') then v_origen
                   when v_usa or k->>'tipo' = 'descuento' then 'pendiente' else 'aceptado' end,
              v_usa, case when v_usa then ve.datos->'parametros'->>'base_calculo' end, v_det)
      on conflict (version_id, personal_id, concepto_id) do update
        set cantidad = excluded.cantidad, sugerido = excluded.sugerido,
            final = case when public.inc_importes.origen = 'modificado' then public.inc_importes.final else excluded.final end,
            origen = case when public.inc_importes.origen = 'modificado' then 'modificado' else excluded.origen end,
            base_calculo = excluded.base_calculo, detalle = excluded.detalle;
    end;
  end loop;
end $$;
revoke all on function public.inc_calcular_version(uuid) from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- 10. Seguridad por renglón (RLS). Escrituras de estado solo por funciones.
-- ---------------------------------------------------------------------
alter table public.inc_parametros      enable row level security;
alter table public.inc_conceptos       enable row level security;
alter table public.inc_tarifas_area    enable row level security;
alter table public.inc_asignaciones    enable row level security;
alter table public.inc_periodos        enable row level security;
alter table public.inc_hojas           enable row level security;
alter table public.inc_celdas          enable row level security;
alter table public.inc_cantidades      enable row level security;
alter table public.inc_observaciones   enable row level security;
alter table public.inc_versiones       enable row level security;
alter table public.inc_sueldos_manuales enable row level security;
alter table public.inc_importes        enable row level security;
alter table public.inc_eventos         enable row level security;

-- anon no tiene nada que hacer aquí.
revoke all on public.inc_parametros, public.inc_conceptos, public.inc_tarifas_area, public.inc_asignaciones,
  public.inc_periodos, public.inc_hojas, public.inc_celdas, public.inc_cantidades, public.inc_observaciones,
  public.inc_versiones, public.inc_sueldos_manuales, public.inc_importes, public.inc_eventos from anon;
-- authenticated solo puede escribir donde una política lo permite (captura y configuración).
revoke insert, update, delete, truncate on public.inc_asignaciones, public.inc_periodos, public.inc_hojas,
  public.inc_versiones, public.inc_sueldos_manuales, public.inc_importes, public.inc_eventos from authenticated;
revoke truncate on public.inc_parametros, public.inc_conceptos, public.inc_tarifas_area,
  public.inc_celdas, public.inc_cantidades, public.inc_observaciones from authenticated;

-- Configuración: la leen todos los usuarios de la organización (no contiene
-- sueldos); solo el Administrador la cambia.
create policy inc_parametros_select on public.inc_parametros for select to authenticated using (tenant_id = public.current_tenant_id());
create policy inc_parametros_write  on public.inc_parametros for all to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'))
  with check (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'));
create policy inc_conceptos_select on public.inc_conceptos for select to authenticated using (tenant_id = public.current_tenant_id());
create policy inc_conceptos_write  on public.inc_conceptos for all to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'))
  with check (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'));
create policy inc_tarifas_select on public.inc_tarifas_area for select to authenticated using (tenant_id = public.current_tenant_id());
create policy inc_tarifas_write  on public.inc_tarifas_area for all to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'))
  with check (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador'));

create policy inc_asignaciones_select on public.inc_asignaciones for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_soy(coordinador_id)));

create policy inc_periodos_select on public.inc_periodos for select to authenticated using (tenant_id = public.current_tenant_id());

create policy inc_hojas_select on public.inc_hojas for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_es_mi_hoja(id)
              or (public.tiene_rol('consulta') and public.inc_hoja_en_alcance(id))));

-- Captura: lectura igual que la hoja; escritura solo del coordinador dueño y
-- solo mientras la hoja es editable (el disparador lo vuelve a comprobar).
create policy inc_celdas_select on public.inc_celdas for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_es_mi_hoja(hoja_id)
              or (public.tiene_rol('consulta') and public.inc_hoja_en_alcance(hoja_id))));
create policy inc_celdas_write on public.inc_celdas for all to authenticated
  using (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id))
  with check (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id));
create policy inc_cantidades_select on public.inc_cantidades for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_es_mi_hoja(hoja_id)
              or (public.tiene_rol('consulta') and public.inc_hoja_en_alcance(hoja_id))));
create policy inc_cantidades_write on public.inc_cantidades for all to authenticated
  using (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id))
  with check (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id));
create policy inc_observaciones_select on public.inc_observaciones for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_es_mi_hoja(hoja_id)
              or (public.tiene_rol('consulta') and public.inc_hoja_en_alcance(hoja_id))));
create policy inc_observaciones_write on public.inc_observaciones for all to authenticated
  using (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id))
  with check (public.inc_es_mi_hoja(hoja_id) and public.inc_hoja_editable(hoja_id));

create policy inc_versiones_select on public.inc_versiones for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or public.inc_es_mi_hoja(hoja_id)
              or (public.tiene_rol('consulta') and public.inc_hoja_en_alcance(hoja_id))));
create policy inc_eventos_select on public.inc_eventos for select to authenticated
  using (tenant_id = public.current_tenant_id()
         and (public.tiene_rol('administrador','nomina') or (hoja_id is not null and public.inc_es_mi_hoja(hoja_id))));

-- Importes y sueldos manuales: SOLO Administrador y Nómina. Ni Coordinador
-- ni Consulta tienen política de lectura: RLS devuelve cero renglones.
create policy inc_importes_select on public.inc_importes for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));
create policy inc_sueldos_select on public.inc_sueldos_manuales for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));

-- Funciones nuevas: nunca para anon ni public; authenticated solo las de la
-- API y las que usan las políticas. (No se tocan funciones existentes.)
do $$
declare f record;
begin
  for f in select p.oid::regprocedure sig from pg_proc p
           where p.pronamespace = 'public'::regnamespace and p.proname like 'inc\_%' loop
    execute format('revoke execute on function %s from public, anon, authenticated', f.sig);
  end loop;
end $$;
-- usadas dentro de políticas (se evalúan con los permisos de quien consulta)
grant execute on function public.inc_soy(uuid), public.inc_es_mi_hoja(uuid), public.inc_hoja_editable(uuid),
  public.inc_hoja_en_alcance(uuid) to authenticated;
-- API
grant execute on function public.inc_crear_periodo(uuid,uuid,date,date), public.inc_abrir_hoja(uuid,uuid),
  public.inc_personas_hoja(uuid), public.inc_enviar_hoja(uuid,text), public.inc_devolver_hoja(uuid,text,text),
  public.inc_firmar_hoja(uuid,text), public.inc_registrar_exportacion(uuid,text), public.inc_marcar_procesado(uuid),
  public.inc_decidir_importe(uuid,numeric), public.inc_capturar_sueldo_manual(uuid,uuid,numeric),
  public.inc_registrar_asignacion(uuid,uuid,date,text) to authenticated;

commit;
