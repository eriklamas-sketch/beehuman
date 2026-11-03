-- =====================================================================
-- BeeHuman · Etapa 1: relaciones laborales, historial por eventos e IDSE (altas)
-- Diseño aprobado: claude/Eventos-laborales-IDSE-diseno.md (3-nov-2026)
-- Versión 2 (3-nov-2026): corrige los hallazgos de la revisión técnica
-- (enlace de esquemas, sincronización de la ficha, bajas migradas, orden de
-- modificaciones, salario mínimo por zona, selección IDSE y reversión).
-- Versión 3 (3-nov-2026): enlace de esquemas en el ingreso con candidata
-- única, validaciones al corregir datos migrados y reversión que protege la
-- configuración capturada (prima de riesgo, guía IDSE, zona del RP).
--
-- Persona → relación laboral → registros de pago y eventos → movimientos
-- IDSE → archivos. Solo para beehuman-pruebas hasta nueva autorización.
--
-- Qué hace:
--   1. Parámetros con vigencia (UMA, salario mínimo), prima de riesgo por
--      registro patronal, catálogo de causas de baja, guía IDSE por RP.
--   2. Tablas: relaciones_laborales, eventos_laborales, idse_movimientos,
--      idse_archivos, idse_archivo_renglones; columna relacion_laboral_id
--      en personal_registros_pago.
--   3. Migración de lo existente: una relación por persona + empresa + RP,
--      con su evento de ingreso (y de baja) de origen «migracion». No se
--      generan movimientos IDSE para lo migrado y NO se modifica ninguna
--      fila de personal ni de personal_registros_pago, salvo enlazar cada
--      registro de pago con su relación.
--   4. Reglas en el servidor (índices, restricciones y disparadores).
--   5. Funciones de la API (security definer). El navegador no escribe en
--      ninguna tabla nueva.
--   6. RLS y permisos.
--
-- Reglas que no cambian:
--   * La fecha de ingreso y la de reconocimiento de antigüedad son campos
--     independientes; ninguna función altera la fecha de ingreso para
--     reconocer antigüedad.
--   * El historial no depende de esquemas de pago ni de movimientos IDSE.
-- Reversión: supabase/reversion/20261104000000_reversion_eventos_laborales_idse.sql
-- =====================================================================
begin;

create extension if not exists btree_gist with schema extensions;
create schema if not exists respaldo;
revoke all on schema respaldo from public;
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then execute 'revoke all on schema respaldo from anon'; end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then execute 'revoke all on schema respaldo from authenticated'; end if;
end $$;

-- ---------------------------------------------------------------------
-- 1. Parámetros y catálogos
-- ---------------------------------------------------------------------
create table public.parametros_generales (
  id            uuid primary key default gen_random_uuid(),
  clave         text not null check (clave in ('UMA_DIARIA','SALARIO_MINIMO_GENERAL','SALARIO_MINIMO_ZLFN')),
  valor         numeric(12,4) not null check (valor > 0),
  vigente_desde date not null,
  vigente_hasta date,
  fuente        text not null,
  creado_en     timestamptz not null default now(),
  check (vigente_hasta is null or vigente_hasta >= vigente_desde),
  exclude using gist (clave with =, daterange(vigente_desde, vigente_hasta, '[]') with &&)
);
comment on table public.parametros_generales is
  'Parámetros nacionales con vigencia. Nunca se sobrescriben: se agrega una vigencia nueva. Solo los carga el administrador de BeeHuman.';

insert into public.parametros_generales (clave, valor, vigente_desde, vigente_hasta, fuente) values
 ('UMA_DIARIA',             108.57, '2024-02-01', '2025-01-31', 'INEGI, DOF 10-ene-2024'),
 ('UMA_DIARIA',             113.14, '2025-02-01', '2026-01-31', 'INEGI, DOF 10-ene-2025'),
 ('UMA_DIARIA',             117.31, '2026-02-01', null,         'INEGI, DOF 9-ene-2026'),
 ('SALARIO_MINIMO_GENERAL', 248.93, '2024-01-01', '2024-12-31', 'CONASAMI, DOF dic-2023'),
 ('SALARIO_MINIMO_GENERAL', 278.80, '2025-01-01', '2025-12-31', 'CONASAMI, DOF dic-2024'),
 ('SALARIO_MINIMO_GENERAL', 315.04, '2026-01-01', null,         'CONASAMI, DOF dic-2025'),
 ('SALARIO_MINIMO_ZLFN',    374.89, '2024-01-01', '2024-12-31', 'CONASAMI, DOF dic-2023'),
 ('SALARIO_MINIMO_ZLFN',    419.88, '2025-01-01', '2025-12-31', 'CONASAMI, DOF dic-2024'),
 ('SALARIO_MINIMO_ZLFN',    440.87, '2026-01-01', null,         'CONASAMI, DOF dic-2025');

create function public.parametro_vigente(p_clave text, p_fecha date) returns numeric
language sql stable security definer set search_path to '' as $$
  select valor from public.parametros_generales
   where clave = p_clave and vigente_desde <= p_fecha
     and (vigente_hasta is null or vigente_hasta >= p_fecha);
$$;

create table public.causas_baja (
  codigo      text primary key,
  descripcion text not null,
  activo      boolean not null default true
);
comment on table public.causas_baja is
  'Causas de baja del IMSS. Pendiente de confirmar contra un archivo real de baja (02) antes de generar TXT de bajas.';
insert into public.causas_baja (codigo, descripcion) values
 ('1','Término de contrato'), ('2','Separación voluntaria'), ('3','Abandono de empleo'),
 ('4','Defunción'), ('5','Clausura'), ('6','Otras'), ('7','Ausentismo'),
 ('8','Rescisión de contrato'), ('9','Jubilación'), ('A','Pensión');

create table public.prima_riesgo_rp (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references public.tenants(id),
  empresa_id           uuid not null,
  registro_patronal_id uuid not null,
  prima                numeric(7,5) not null check (prima > 0 and prima <= 15),
  clase                text check (clase is null or clase in ('I','II','III','IV','V')),
  vigente_desde        date not null,
  vigente_hasta        date,
  creado_por           uuid,
  creado_en            timestamptz not null default now(),
  foreign key (empresa_id, registro_patronal_id, tenant_id)
    references public.empresas_registros_patronales (empresa_id, id, tenant_id),
  check (vigente_hasta is null or vigente_hasta >= vigente_desde),
  exclude using gist (registro_patronal_id with =, daterange(vigente_desde, vigente_hasta, '[]') with &&)
);
comment on table public.prima_riesgo_rp is 'Prima de riesgo de trabajo por registro patronal, con vigencia (cambia cada marzo).';

alter table public.empresas_registros_patronales add column guia_idse text
  check (guia_idse is null or guia_idse ~ '^[0-9]{5}$');
alter table public.empresas_registros_patronales add column zona_salario_minimo text not null default 'general'
  check (zona_salario_minimo in ('general','zlfn'));
comment on column public.empresas_registros_patronales.zona_salario_minimo is
  'Área geográfica del salario mínimo del centro de trabajo: general o zona libre de la frontera norte. Define el piso legal del SBC.';
comment on column public.empresas_registros_patronales.guia_idse is 'Número de guía de 5 dígitos que se escribe en los archivos IDSE del registro patronal.';

-- ---------------------------------------------------------------------
-- 2. Relaciones laborales y eventos
-- ---------------------------------------------------------------------
create table public.relaciones_laborales (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references public.tenants(id),
  personal_id          uuid not null,
  empresa_id           uuid not null,
  registro_patronal_id uuid,
  numero_interno       text check (numero_interno is null or char_length(btrim(numero_interno)) between 1 and 10),
  fecha_ingreso        date,
  fecha_ingreso_origen text not null default 'captura'
    check (fecha_ingreso_origen in ('captura','fecha_alta_imss','fecha_inicio_contrato','sin_dato')),
  fecha_reconocimiento_antiguedad date,
  fecha_baja           date,
  causa_baja           text references public.causas_baja(codigo),
  estado               text not null default 'vigente' check (estado in ('vigente','baja','anulada')),
  sbc                  numeric(10,2) check (sbc is null or sbc > 0),
  sdi                  numeric(10,2) check (sdi is null or sdi > 0),
  tipo_trabajador      text check (tipo_trabajador is null or tipo_trabajador in ('1','2','3','4')),
  tipo_salario         text check (tipo_salario is null or tipo_salario in ('0','1','2')),
  jornada              text check (jornada is null or jornada in ('0','1','2','3','4','5','6')),
  umf                  text check (umf is null or umf ~ '^[0-9]{3}$'),
  migrado              boolean not null default false,
  pendientes_migracion text[] not null default '{}'
    check (pendientes_migracion <@ array['sin_fecha_ingreso','baja_sin_fecha','historica_por_reconstruir']),
  creado_por           uuid,
  creado_en            timestamptz not null default now(),
  actualizado_por      uuid,
  actualizado_en       timestamptz,
  unique (id, tenant_id),
  foreign key (personal_id, tenant_id) references public.personal (id, tenant_id),
  foreign key (empresa_id, tenant_id) references public.empresas (id, tenant_id),
  foreign key (empresa_id, registro_patronal_id, tenant_id)
    references public.empresas_registros_patronales (empresa_id, id, tenant_id),
  -- sin fecha de ingreso solo se admite lo migrado sin dato
  check (fecha_ingreso is not null or fecha_ingreso_origen = 'sin_dato'),
  check (fecha_ingreso_origen <> 'sin_dato' or migrado),
  -- la baja lleva fecha (lo migrado puede venir sin ella y queda para revisar)
  check (estado <> 'baja' or fecha_baja is not null or migrado),
  check (estado <> 'vigente' or (fecha_baja is null and causa_baja is null)),
  check (migrado or fecha_baja is null or fecha_baja >= fecha_ingreso)
);
comment on table public.relaciones_laborales is
  'Periodo continuo (ingreso→baja) de una persona con una empresa y, si aplica, un registro patronal. Estado vigente: solo lo cambian las funciones laboral_*.';
comment on column public.relaciones_laborales.fecha_reconocimiento_antiguedad is
  'Independiente de fecha_ingreso: reconocer antigüedad anterior nunca altera la fecha de ingreso (que es la que va al IMSS).';

-- una sola relación vigente por persona + empresa + RP (o persona + empresa sin RP)
create unique index relaciones_laborales_vigente_uq on public.relaciones_laborales
  (tenant_id, personal_id, empresa_id, coalesce(registro_patronal_id, '00000000-0000-0000-0000-000000000000'::uuid))
  where estado = 'vigente';
-- número interno (clave del trabajador en IDSE) único por RP entre relaciones vigentes
create unique index relaciones_laborales_numero_interno_uq on public.relaciones_laborales
  (tenant_id, registro_patronal_id, upper(btrim(numero_interno)))
  where estado = 'vigente' and registro_patronal_id is not null and numero_interno is not null;
create index relaciones_laborales_persona_idx on public.relaciones_laborales (tenant_id, personal_id);

create table public.eventos_laborales (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id),
  personal_id           uuid not null,
  relacion_laboral_id   uuid not null,
  registro_pago_id      uuid,
  tipo                  text not null check (tipo in (
    'ingreso','reingreso','baja','modificacion_salario','cambio_esquema_pago','cambio_puesto',
    'cambio_jefe','cambio_organizacion','cambio_registro_patronal','cambio_empresa','correccion_datos')),
  fecha_efectiva        date,
  registrado_en         timestamptz not null default now(),
  causa                 text references public.causas_baja(codigo),
  motivo                text,
  valores_anteriores    jsonb not null default '{}'::jsonb,
  valores_nuevos        jsonb not null default '{}'::jsonb,
  evento_ligado_id      uuid references public.eventos_laborales(id),
  estado                text not null default 'vigente' check (estado in ('vigente','anulado')),
  anulado_por_evento_id uuid references public.eventos_laborales(id),
  anulado_en            timestamptz,
  anulado_por           uuid,
  motivo_anulacion      text,
  origen                text not null check (origen in ('pantalla','importacion','migracion','automatico')),
  creado_por            uuid,
  unique (id, tenant_id),
  foreign key (relacion_laboral_id, tenant_id) references public.relaciones_laborales (id, tenant_id),
  foreign key (personal_id, tenant_id) references public.personal (id, tenant_id),
  foreign key (registro_pago_id, tenant_id) references public.personal_registros_pago (id, tenant_id),
  check (fecha_efectiva is not null or origen = 'migracion'),
  check (tipo <> 'baja' or causa is not null or origen = 'migracion'),
  check (estado <> 'anulado' or (anulado_en is not null and motivo_anulacion is not null))
);
comment on table public.eventos_laborales is
  'Historial inmutable por relación laboral. Una corrección no borra: anula y registra otro evento.';
-- un solo ingreso y una sola baja vigentes por relación; sin duplicados del mismo tipo y fecha
create unique index eventos_laborales_ingreso_uq on public.eventos_laborales (relacion_laboral_id)
  where estado = 'vigente' and tipo in ('ingreso','reingreso');
create unique index eventos_laborales_baja_uq on public.eventos_laborales (relacion_laboral_id)
  where estado = 'vigente' and tipo = 'baja';
create unique index eventos_laborales_salario_fecha_uq on public.eventos_laborales (relacion_laboral_id, fecha_efectiva)
  where estado = 'vigente' and tipo = 'modificacion_salario';
create index eventos_laborales_persona_idx on public.eventos_laborales (tenant_id, personal_id, fecha_efectiva);
create index eventos_laborales_relacion_idx on public.eventos_laborales (relacion_laboral_id, registrado_en);

alter table public.personal_registros_pago add column relacion_laboral_id uuid;
alter table public.personal_registros_pago add constraint personal_registros_pago_relacion_fk
  foreign key (relacion_laboral_id, tenant_id) references public.relaciones_laborales (id, tenant_id);
create index prp_relacion_idx on public.personal_registros_pago (relacion_laboral_id);

-- ---------------------------------------------------------------------
-- 3. IDSE
-- ---------------------------------------------------------------------
create table public.idse_archivos (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references public.tenants(id),
  empresa_id           uuid not null,
  registro_patronal_id uuid not null,
  tipo_movimiento      text not null check (tipo_movimiento in ('08','02','07')),
  guia                 text not null check (guia ~ '^[0-9]{5}$'),
  nombre_archivo       text not null,
  num_registros        integer not null check (num_registros > 0),
  contenido            text not null,
  hash_sha256          text not null,
  estado               text not null default 'generado' check (estado in ('generado','presentado','con_resultado','cancelado')),
  lote_idse            text,
  fecha_presentacion   date,
  acuse_folio          text,
  acuse_fecha          date,
  motivo_cancelacion   text,
  generado_por         uuid,
  generado_en          timestamptz not null default now(),
  actualizado_por      uuid,
  actualizado_en       timestamptz,
  unique (id, tenant_id),
  foreign key (empresa_id, registro_patronal_id, tenant_id)
    references public.empresas_registros_patronales (empresa_id, id, tenant_id),
  check (estado not in ('presentado','con_resultado') or (lote_idse is not null and fecha_presentacion is not null))
);

create table public.idse_movimientos (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references public.tenants(id),
  evento_id            uuid not null,
  relacion_laboral_id  uuid not null,
  registro_patronal_id uuid not null,
  tipo_movimiento      text not null check (tipo_movimiento in ('08','02','07')),
  fecha_movimiento     date not null,
  sbc                  numeric(10,2),
  causa_baja           text references public.causas_baja(codigo),
  estado               text not null default 'pendiente'
    check (estado in ('pendiente','en_archivo','presentado','confirmado','rechazado','cancelado')),
  archivo_id           uuid,
  motivo_rechazo       text,
  creado_en            timestamptz not null default now(),
  actualizado_por      uuid,
  actualizado_en       timestamptz,
  unique (id, tenant_id),
  foreign key (evento_id, tenant_id) references public.eventos_laborales (id, tenant_id),
  foreign key (relacion_laboral_id, tenant_id) references public.relaciones_laborales (id, tenant_id),
  foreign key (archivo_id, tenant_id) references public.idse_archivos (id, tenant_id),
  check ((estado in ('en_archivo','presentado','confirmado','rechazado')) = (archivo_id is not null) or estado = 'rechazado')
);
-- un movimiento activo por evento (rechazado y cancelado no cuentan)
create unique index idse_movimientos_evento_uq on public.idse_movimientos (evento_id)
  where estado not in ('cancelado');
create index idse_movimientos_bandeja_idx on public.idse_movimientos (tenant_id, registro_patronal_id, tipo_movimiento, estado);

create table public.idse_archivo_renglones (
  archivo_id     uuid not null,
  movimiento_id  uuid not null,
  tenant_id      uuid not null,
  linea          integer not null,
  texto          text not null check (char_length(texto) = 168),
  resultado      text check (resultado is null or resultado in ('confirmado','rechazado','cancelado')),
  motivo_rechazo text,
  primary key (archivo_id, movimiento_id),
  unique (archivo_id, linea),
  foreign key (archivo_id, tenant_id) references public.idse_archivos (id, tenant_id),
  foreign key (movimiento_id, tenant_id) references public.idse_movimientos (id, tenant_id)
);
comment on table public.idse_archivo_renglones is 'Cada línea exacta de cada archivo generado y su resultado ante el IMSS: traza completa de reenvíos.';

-- ---------------------------------------------------------------------
-- 4. Migración de los datos existentes (antes de crear los disparadores)
-- ---------------------------------------------------------------------
do $$
declare
  n_rel int; n_baja int; n_sin_fecha int; n_rp_enlazados int; n_rp_sin int; n_personas_sin int; n_nss_dup int;
begin
  -- Respaldo de los campos de la ficha que pasará a controlar el historial.
  -- La migración no los cambia, pero la primera sincronización sí puede
  -- limpiarlos (por ejemplo, si un dato de la ficha no se pudo asignar a una
  -- relación). Con este respaldo nada de la ficha original se pierde.
  -- Si ya existe (migración aplicada antes y revertida) se conserva el original.
  if to_regclass('respaldo.personal_ficha_20261104') is null then
    create table respaldo.personal_ficha_20261104 as
    select id, tenant_id, empresa_id, registro_patronal_id, fecha_alta_imss, sdi_imss, numero_interno_trabajador,
           fecha_antiguedad, estatus, fecha_baja, comentario_baja, now() as respaldado_en
      from public.personal;
    alter table respaldo.personal_ficha_20261104 add primary key (id);
  end if;

  -- Grupos empresa + RP por persona: registros de pago con empresa (activos si la
  -- persona no está en Baja; todos si lo está) y la empresa/RP de la ficha.
  create temp table _grupos on commit drop as
  with base as (
    select p.id as personal_id, p.tenant_id, r.empresa_id, r.registro_patronal_id
      from public.personal p
      join public.personal_registros_pago r on r.personal_id = p.id and r.tenant_id = p.tenant_id
     where r.empresa_id is not null and (r.activo or p.estatus = 'Baja')
    union
    select p.id, p.tenant_id, p.empresa_id, p.registro_patronal_id
      from public.personal p where p.empresa_id is not null
  )
  -- un registro con empresa y sin RP se une a la relación con RP de esa empresa si existe
  , g as (
    select distinct b.* from base b
     where not (b.registro_patronal_id is null and exists (
       select 1 from base b2 where b2.personal_id = b.personal_id and b2.empresa_id = b.empresa_id
          and b2.registro_patronal_id is not null))
  )
  -- «Relación de la ficha»: la que coincide con la empresa y el RP de la ficha
  -- (o, si la ficha no tiene RP, la única de esa empresa). Solo ella recibe los
  -- datos de la ficha: alta IMSS, inicio de contrato, antigüedad, SDI, número
  -- interno y fecha de baja. Las demás quedan sin fechas inventadas.
  select g.*,
         (g.empresa_id = p.empresa_id
          and (g.registro_patronal_id is not distinct from p.registro_patronal_id
               or (p.registro_patronal_id is null
                   and count(*) over (partition by g.personal_id, g.empresa_id) = 1))) as es_ficha
    from g join public.personal p on p.id = g.personal_id;

  insert into public.relaciones_laborales (
    tenant_id, personal_id, empresa_id, registro_patronal_id, numero_interno, fecha_ingreso, fecha_ingreso_origen,
    fecha_reconocimiento_antiguedad, fecha_baja, estado, sbc, sdi, migrado, pendientes_migracion)
  select g.tenant_id, g.personal_id, g.empresa_id, g.registro_patronal_id,
         case when g.es_ficha then nullif(left(btrim(p.numero_interno_trabajador), 10), '') end,
         x.f_ing, x.origen,
         case when g.es_ficha then p.fecha_antiguedad end,
         case when p.estatus = 'Baja' and g.es_ficha then p.fecha_baja end,
         case when p.estatus = 'Baja' then 'baja' else 'vigente' end,
         case when g.es_ficha and g.registro_patronal_id is not null and p.sdi_imss > 0 then p.sdi_imss end,
         case when g.es_ficha and g.registro_patronal_id is not null and p.sdi_imss > 0 then p.sdi_imss end,
         true,
         array_remove(array[
           case when x.origen = 'sin_dato' then 'sin_fecha_ingreso' end,
           case when p.estatus = 'Baja' and g.es_ficha and p.fecha_baja is null then 'baja_sin_fecha' end,
           case when p.estatus = 'Baja' and not g.es_ficha then 'historica_por_reconstruir' end], null)
    from _grupos g
    join public.personal p on p.id = g.personal_id
    cross join lateral (select
        case when g.es_ficha and g.registro_patronal_id is not null and p.fecha_alta_imss is not null then p.fecha_alta_imss
             when g.es_ficha and p.fecha_inicio_contrato is not null then p.fecha_inicio_contrato end as f_ing,
        case when g.es_ficha and g.registro_patronal_id is not null and p.fecha_alta_imss is not null then 'fecha_alta_imss'
             when g.es_ficha and p.fecha_inicio_contrato is not null then 'fecha_inicio_contrato'
             else 'sin_dato' end as origen) x;
  get diagnostics n_rel = row_count;

  -- evento de ingreso de cada relación migrada
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo,
    valores_nuevos, origen, registrado_en)
  select rl.tenant_id, rl.personal_id, rl.id, 'ingreso', rl.fecha_ingreso, 'Migración inicial del historial',
         jsonb_strip_nulls(jsonb_build_object('empresa_id', rl.empresa_id, 'registro_patronal_id', rl.registro_patronal_id,
           'numero_interno', rl.numero_interno, 'fecha_ingreso', rl.fecha_ingreso, 'fecha_ingreso_origen', rl.fecha_ingreso_origen,
           'fecha_reconocimiento_antiguedad', rl.fecha_reconocimiento_antiguedad, 'sbc', rl.sbc, 'sdi', rl.sdi)),
         'migracion', rl.creado_en
    from public.relaciones_laborales rl where rl.migrado;

  -- evento de baja de las relaciones de personas en Baja
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo,
    valores_nuevos, origen, registrado_en)
  select rl.tenant_id, rl.personal_id, rl.id, 'baja', rl.fecha_baja,
         case when 'historica_por_reconstruir' = any(rl.pendientes_migracion)
              then 'Relación histórica: fecha de baja por reconstruir'
              else coalesce(nullif(btrim(p.comentario_baja), ''), 'Migración inicial del historial') end,
         jsonb_strip_nulls(jsonb_build_object('fecha_baja', rl.fecha_baja,
           'comentario_baja', case when 'historica_por_reconstruir' = any(rl.pendientes_migracion) then null else p.comentario_baja end)),
         'migracion', rl.creado_en + interval '1 second'
    from public.relaciones_laborales rl join public.personal p on p.id = rl.personal_id
   where rl.migrado and rl.estado = 'baja';
  get diagnostics n_baja = row_count;

  -- enlazar registros de pago con su relación (único cambio a tablas existentes).
  -- Los disparadores de usuario se apagan solo aquí para no sellar autoría
  -- ni revalidar requisitos por un enlace técnico.
  alter table public.personal_registros_pago disable trigger user;
  -- a) misma empresa y RP
  update public.personal_registros_pago r set relacion_laboral_id = rl.id
    from public.relaciones_laborales rl
   where rl.personal_id = r.personal_id and rl.tenant_id = r.tenant_id
     and r.empresa_id = rl.empresa_id and r.registro_patronal_id is not distinct from rl.registro_patronal_id
     and r.relacion_laboral_id is null;
  -- b) con empresa y sin RP: a la relación de esa empresa si es la única
  update public.personal_registros_pago r set relacion_laboral_id = x.rid
    from (select rl.personal_id, rl.empresa_id, min(rl.id::text)::uuid rid, count(*) n
            from public.relaciones_laborales rl group by 1, 2) x
   where x.personal_id = r.personal_id and x.empresa_id = r.empresa_id and x.n = 1
     and r.registro_patronal_id is null and r.relacion_laboral_id is null;
  -- c) sin empresa: a la única relación de la persona
  update public.personal_registros_pago r set relacion_laboral_id = x.rid
    from (select rl.personal_id, min(rl.id::text)::uuid rid, count(*) n
            from public.relaciones_laborales rl group by 1) x
   where x.personal_id = r.personal_id and x.n = 1
     and r.empresa_id is null and r.relacion_laboral_id is null;
  alter table public.personal_registros_pago enable trigger user;

  select count(*) into n_sin_fecha from public.relaciones_laborales where fecha_ingreso_origen = 'sin_dato';
  select count(*) filter (where relacion_laboral_id is not null), count(*) filter (where relacion_laboral_id is null)
    into n_rp_enlazados, n_rp_sin from public.personal_registros_pago;
  select count(*) into n_personas_sin from public.personal p
   where not exists (select 1 from public.relaciones_laborales rl where rl.personal_id = p.id);
  select count(*) into n_nss_dup from (
    select rl.tenant_id, rl.registro_patronal_id, p.nss from public.relaciones_laborales rl
      join public.personal p on p.id = rl.personal_id
     where rl.estado = 'vigente' and rl.registro_patronal_id is not null and coalesce(p.nss, '') <> ''
     group by 1, 2, 3 having count(distinct rl.personal_id) > 1) d;

  raise notice 'Relaciones creadas: % (de ellas en baja: %; sin fecha de ingreso: %)', n_rel, n_baja, n_sin_fecha;
  raise notice 'Bajas históricas por reconstruir (sin fecha inventada): %; bajas de la ficha sin fecha: %',
    (select count(*) from public.relaciones_laborales where 'historica_por_reconstruir' = any(pendientes_migracion)),
    (select count(*) from public.relaciones_laborales where 'baja_sin_fecha' = any(pendientes_migracion));
  raise notice 'Registros de pago enlazados: %; sin enlazar (para revisar): %', n_rp_enlazados, n_rp_sin;
  raise notice 'Personas sin relación laboral (sin empresa): %', n_personas_sin;
  raise notice 'NSS repetidos en un mismo RP entre relaciones vigentes: %', n_nss_dup;
end $$;

-- ---------------------------------------------------------------------
-- 5. Disparadores
-- ---------------------------------------------------------------------
-- Interruptor de sesión que solo activan las funciones laboral_*/idse_*
-- (transaction-local). Protege contra escrituras desde la API de la app (la
-- API REST no expone set_config y además no hay permisos de escritura). NO
-- es una barrera frente a un usuario privilegiado de PostgreSQL (editor SQL
-- de Supabase): ese usuario puede activarlo o desactivar disparadores. Para
-- él es una protección contra errores, no un control de seguridad.
create function public.laboral_en_funcion() returns boolean
language sql stable set search_path to '' as $$
  select coalesce(current_setting('beehuman.laboral', true), '') = 'on';
$$;

-- 5a. Tablas nuevas: nadie escribe fuera de las funciones; nada se borra.
create function public.laboral_proteger_tablas() returns trigger
language plpgsql set search_path to '' as $$
begin
  if tg_op in ('DELETE','TRUNCATE') then
    raise exception 'BeeHuman: % es historial y no se puede borrar.', tg_table_name;
  end if;
  if not public.laboral_en_funcion() then
    raise exception 'BeeHuman: % solo se modifica con las funciones de historial laboral e IDSE.', tg_table_name;
  end if;
  if tg_op = 'UPDATE' then
    if tg_table_name = 'eventos_laborales' then
      -- un evento solo puede pasar de vigente a anulado; nada más cambia
      if old.estado <> 'vigente' or new.estado <> 'anulado'
         or (to_jsonb(new) - array['estado','anulado_por_evento_id','anulado_en','anulado_por','motivo_anulacion'])
            is distinct from (to_jsonb(old) - array['estado','anulado_por_evento_id','anulado_en','anulado_por','motivo_anulacion']) then
        raise exception 'BeeHuman: un evento laboral no se edita; solo se anula.';
      end if;
    elsif tg_table_name = 'idse_archivos' then
      if new.contenido is distinct from old.contenido or new.hash_sha256 is distinct from old.hash_sha256
         or new.registro_patronal_id is distinct from old.registro_patronal_id
         or new.tipo_movimiento is distinct from old.tipo_movimiento or new.num_registros is distinct from old.num_registros then
        raise exception 'BeeHuman: el contenido de un archivo IDSE generado no cambia.';
      end if;
    elsif tg_table_name = 'idse_archivo_renglones' then
      if new.texto is distinct from old.texto or new.linea is distinct from old.linea then
        raise exception 'BeeHuman: las líneas de un archivo IDSE generado no cambian.';
      end if;
    end if;
  end if;
  return coalesce(new, old);
end $$;

create trigger trg_proteger before insert or update or delete on public.relaciones_laborales
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger before insert or update or delete on public.eventos_laborales
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger before insert or update or delete on public.idse_movimientos
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger before insert or update or delete on public.idse_archivos
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger before insert or update or delete on public.idse_archivo_renglones
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger before insert or update or delete on public.prima_riesgo_rp
  for each row execute function public.laboral_proteger_tablas();
create trigger trg_proteger_truncate before truncate on public.relaciones_laborales
  for each statement execute function public.laboral_proteger_tablas();
create trigger trg_proteger_truncate before truncate on public.eventos_laborales
  for each statement execute function public.laboral_proteger_tablas();
create trigger trg_proteger_truncate before truncate on public.idse_movimientos
  for each statement execute function public.laboral_proteger_tablas();
create trigger trg_proteger_truncate before truncate on public.idse_archivos
  for each statement execute function public.laboral_proteger_tablas();
create trigger trg_proteger_truncate before truncate on public.idse_archivo_renglones
  for each statement execute function public.laboral_proteger_tablas();
create trigger trg_bloquear_cambio_tenant before update on public.relaciones_laborales
  for each row execute function public.bloquear_cambio_tenant();
create trigger trg_bloquear_cambio_tenant before update on public.eventos_laborales
  for each row execute function public.bloquear_cambio_tenant();
create trigger trg_bloquear_cambio_tenant before update on public.idse_movimientos
  for each row execute function public.bloquear_cambio_tenant();
create trigger trg_bloquear_cambio_tenant before update on public.idse_archivos
  for each row execute function public.bloquear_cambio_tenant();

-- 5b. Evento ↔ relación: la persona del evento es la de su relación.
create function public.laboral_validar_evento() returns trigger
language plpgsql set search_path to '' as $$
begin
  if not exists (select 1 from public.relaciones_laborales r
                  where r.id = new.relacion_laboral_id and r.personal_id = new.personal_id and r.tenant_id = new.tenant_id) then
    raise exception 'BeeHuman: el evento no corresponde a la persona de su relación laboral.';
  end if;
  if new.registro_pago_id is not null and not exists (select 1 from public.personal_registros_pago rp
       where rp.id = new.registro_pago_id and rp.personal_id = new.personal_id) then
    raise exception 'BeeHuman: el esquema de pago del evento es de otra persona.';
  end if;
  return new;
end $$;
create trigger trg_validar_evento before insert on public.eventos_laborales
  for each row execute function public.laboral_validar_evento();

-- 5c. Ficha de la persona: los datos que ahora controla el historial no se
--     editan directamente cuando la persona ya tiene relaciones laborales.
create function public.laboral_proteger_ficha() returns trigger
language plpgsql security definer set search_path to '' as $$
begin
  if public.laboral_en_funcion() then return new; end if;
  if not exists (select 1 from public.relaciones_laborales r where r.personal_id = new.id and r.estado <> 'anulada') then
    return new;   -- persona sin historial todavía: se comporta como antes
  end if;
  if new.empresa_id is distinct from old.empresa_id
     or new.registro_patronal_id is distinct from old.registro_patronal_id
     or new.fecha_alta_imss is distinct from old.fecha_alta_imss
     or new.sdi_imss is distinct from old.sdi_imss
     or new.fecha_baja is distinct from old.fecha_baja
     or new.comentario_baja is distinct from old.comentario_baja
     or new.numero_interno_trabajador is distinct from old.numero_interno_trabajador
     or new.fecha_antiguedad is distinct from old.fecha_antiguedad
     or (new.estatus is distinct from old.estatus and 'Baja' in (coalesce(new.estatus, ''), coalesce(old.estatus, ''))) then
    raise exception 'BeeHuman: empresa, registro patronal, alta y baja, SDI, número interno y antigüedad se registran desde la Historia laboral de la persona.'
      using errcode = 'P0001', hint = 'historia_laboral';
  end if;
  return new;
end $$;
create trigger trg_laboral_proteger_ficha before update on public.personal
  for each row execute function public.laboral_proteger_ficha();

-- 5d. Cambios de organización en la ficha → evento automático en la
--     relación principal vigente (puesto, jefe, área, proyecto…).
-- Relación principal: la vigente que ya muestra la ficha (para que la ficha no
-- «salte» de empresa por un movimiento en otra relación); si ya no está
-- vigente, la vigente con RP más reciente.
create function public.laboral_relacion_principal(p_personal_id uuid) returns uuid
language sql stable security definer set search_path to '' as $$
  select r.id from public.relaciones_laborales r
  join public.personal p on p.id = r.personal_id
   where r.personal_id = p_personal_id and r.estado = 'vigente'
   order by (r.empresa_id is not distinct from p.empresa_id
             and r.registro_patronal_id is not distinct from p.registro_patronal_id) desc,
            (r.registro_patronal_id is not null) desc, r.fecha_ingreso desc nulls last, r.creado_en desc
   limit 1;
$$;

create function public.laboral_nombre_catalogo(p_tabla text, p_id uuid) returns text
language plpgsql stable security definer set search_path to '' as $$
declare v text;
begin
  if p_id is null then return null; end if;
  if p_tabla = 'personal' then
    select nombre_completo into v from public.personal where id = p_id;
  elsif p_tabla in ('puestos','areas','departamentos','localidades','centros_costo','proyectos','empresas',
                    'clasificaciones_personal','periodicidades') then
    execute format('select nombre from public.%I where id = $1', p_tabla) into v using p_id;
  elsif p_tabla = 'empresas_registros_patronales' then
    select registro_patronal into v from public.empresas_registros_patronales where id = p_id;
  end if;
  return v;
end $$;

create function public.laboral_evento_por_ficha() returns trigger
language plpgsql security definer set search_path to '' as $$
declare
  v_rel uuid; v_ing date; v_fecha date;
  c record; ant jsonb; nue jsonb; tipo text;
begin
  if public.laboral_en_funcion() then return new; end if;
  v_rel := public.laboral_relacion_principal(new.id);
  if v_rel is null then return new; end if;
  select fecha_ingreso into v_ing from public.relaciones_laborales where id = v_rel;
  v_fecha := greatest(current_date, coalesce(v_ing, current_date));
  for tipo in select unnest(array['cambio_puesto','cambio_jefe','cambio_organizacion']) loop
    ant := '{}'; nue := '{}';
    for c in select * from (values
        ('cambio_puesto','puesto_id','puestos', to_jsonb(old.puesto_id), to_jsonb(new.puesto_id)),
        ('cambio_jefe','jefe_id','personal', to_jsonb(old.jefe_id), to_jsonb(new.jefe_id)),
        ('cambio_organizacion','area_id','areas', to_jsonb(old.area_id), to_jsonb(new.area_id)),
        ('cambio_organizacion','departamento_id','departamentos', to_jsonb(old.departamento_id), to_jsonb(new.departamento_id)),
        ('cambio_organizacion','localidad_id','localidades', to_jsonb(old.localidad_id), to_jsonb(new.localidad_id)),
        ('cambio_organizacion','centro_costo_id','centros_costo', to_jsonb(old.centro_costo_id), to_jsonb(new.centro_costo_id)),
        ('cambio_organizacion','proyecto_id','proyectos', to_jsonb(old.proyecto_id), to_jsonb(new.proyecto_id)),
        ('cambio_organizacion','coordinador_id','personal', to_jsonb(old.coordinador_id), to_jsonb(new.coordinador_id)),
        ('cambio_organizacion','coordinador_externo',null, to_jsonb(old.coordinador_externo), to_jsonb(new.coordinador_externo))
      ) x(t, campo, tabla, va, vn)
      where x.t = tipo and x.va is distinct from x.vn loop
      ant := ant || jsonb_build_object(c.campo, c.va);
      nue := nue || jsonb_build_object(c.campo, c.vn);
      if c.tabla is not null then
        ant := ant || jsonb_build_object(replace(c.campo, '_id', ''), public.laboral_nombre_catalogo(c.tabla, (c.va #>> '{}')::uuid));
        nue := nue || jsonb_build_object(replace(c.campo, '_id', ''), public.laboral_nombre_catalogo(c.tabla, (c.vn #>> '{}')::uuid));
      end if;
    end loop;
    if nue <> '{}'::jsonb then
      perform set_config('beehuman.laboral', 'on', true);
      insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva,
        valores_anteriores, valores_nuevos, origen, creado_por)
      values (new.tenant_id, new.id, v_rel, tipo, v_fecha, jsonb_strip_nulls(ant), jsonb_strip_nulls(nue), 'automatico', auth.uid());
      perform set_config('beehuman.laboral', 'off', true);
    end if;
  end loop;
  return new;
end $$;
create trigger trg_laboral_evento_por_ficha after update on public.personal
  for each row execute function public.laboral_evento_por_ficha();

-- 5e. Registros de pago: se enlazan solos con su relación y sus cambios
--     quedan en el historial. Su empresa/RP debe coincidir con la relación.
create function public.laboral_enlazar_registro_pago() returns trigger
language plpgsql security definer set search_path to '' as $$
declare r record; n int;
begin
  if new.relacion_laboral_id is null and new.activo and (tg_op = 'INSERT' or old.relacion_laboral_id is null) then
    -- Solo se enlaza solo cuando hay UNA relación candidata; con varias se deja
    -- sin enlazar y Nómina elige la relación (queda en «Para revisar»).
    if new.empresa_id is not null then
      select count(*), min(id::text)::uuid into n, new.relacion_laboral_id from public.relaciones_laborales
       where personal_id = new.personal_id and tenant_id = new.tenant_id and estado = 'vigente'
         and empresa_id = new.empresa_id
         and (new.registro_patronal_id is null or registro_patronal_id = new.registro_patronal_id);
      if n <> 1 then new.relacion_laboral_id := null; end if;
    else
      select count(*), min(id::text)::uuid into n, new.relacion_laboral_id from public.relaciones_laborales
       where personal_id = new.personal_id and tenant_id = new.tenant_id and estado = 'vigente';
      if n <> 1 then new.relacion_laboral_id := null; end if;
    end if;
  end if;
  if new.relacion_laboral_id is not null then
    select * into r from public.relaciones_laborales where id = new.relacion_laboral_id;
    if r.personal_id <> new.personal_id or r.tenant_id <> new.tenant_id then
      raise exception 'BeeHuman: el esquema de pago y su relación laboral son de personas distintas.';
    end if;
    if (new.empresa_id is not null and new.empresa_id <> r.empresa_id)
       or (new.registro_patronal_id is not null and new.registro_patronal_id is distinct from r.registro_patronal_id) then
      raise exception 'BeeHuman: la empresa y el registro patronal del esquema deben ser los de su relación laboral.';
    end if;
    if new.activo and r.estado <> 'vigente' and not public.laboral_en_funcion() then
      raise exception 'BeeHuman: no se puede activar un esquema de una relación laboral dada de baja.';
    end if;
  end if;
  return new;
end $$;
create trigger trg_laboral_enlazar_registro_pago before insert or update on public.personal_registros_pago
  for each row execute function public.laboral_enlazar_registro_pago();

create function public.laboral_evento_por_registro_pago() returns trigger
language plpgsql security definer set search_path to '' as $$
declare v_ing date; v_fecha date; ant jsonb := '{}'; nue jsonb;
begin
  if public.laboral_en_funcion() or new.relacion_laboral_id is null then return new; end if;
  if tg_op = 'UPDATE' and new.sueldo is not distinct from old.sueldo
     and new.modalidad_sueldo is not distinct from old.modalidad_sueldo
     and new.periodicidad_id is not distinct from old.periodicidad_id
     and new.dias_periodo is not distinct from old.dias_periodo
     and new.clasificacion_id is not distinct from old.clasificacion_id
     and new.activo is not distinct from old.activo then
    return new;
  end if;
  select fecha_ingreso into v_ing from public.relaciones_laborales where id = new.relacion_laboral_id;
  v_fecha := case when tg_op = 'INSERT' then new.fecha_inicio
                  when old.activo and not new.activo then coalesce(new.fecha_fin, current_date)
                  else current_date end;
  v_fecha := greatest(v_fecha, coalesce(v_ing, v_fecha));
  nue := jsonb_build_object('clasificacion', public.laboral_nombre_catalogo('clasificaciones_personal', new.clasificacion_id),
           'sueldo', new.sueldo, 'modalidad_sueldo', new.modalidad_sueldo,
           'periodicidad', public.laboral_nombre_catalogo('periodicidades', new.periodicidad_id),
           'dias_periodo', new.dias_periodo, 'activo', new.activo);
  if tg_op = 'UPDATE' then
    ant := jsonb_build_object('clasificacion', public.laboral_nombre_catalogo('clasificaciones_personal', old.clasificacion_id),
           'sueldo', old.sueldo, 'modalidad_sueldo', old.modalidad_sueldo,
           'periodicidad', public.laboral_nombre_catalogo('periodicidades', old.periodicidad_id),
           'dias_periodo', old.dias_periodo, 'activo', old.activo);
  end if;
  perform set_config('beehuman.laboral', 'on', true);
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, registro_pago_id, tipo, fecha_efectiva,
    valores_anteriores, valores_nuevos, origen, creado_por)
  values (new.tenant_id, new.personal_id, new.relacion_laboral_id, new.id, 'cambio_esquema_pago', v_fecha,
    jsonb_strip_nulls(ant), jsonb_strip_nulls(nue), 'automatico', auth.uid());
  perform set_config('beehuman.laboral', 'off', true);
  return new;
end $$;
create trigger trg_laboral_evento_por_registro_pago after insert or update on public.personal_registros_pago
  for each row execute function public.laboral_evento_por_registro_pago();

-- ---------------------------------------------------------------------
-- 6. Funciones internas (sin permiso para la API)
-- ---------------------------------------------------------------------
create function public.laboral_exigir_rol(p_roles text[]) returns uuid
language plpgsql stable security definer set search_path to '' as $$
declare v_tenant uuid := public.current_tenant_id();
begin
  if v_tenant is null or not public.tiene_rol(variadic p_roles) then
    raise exception 'BeeHuman: tu rol no permite esta operación.' using errcode = '42501';
  end if;
  return v_tenant;
end $$;

-- Copia en la ficha los datos de la relación principal (compatibilidad con
-- pantallas, exportación NOI, alertas y Resumen).
-- Copia en la ficha los datos de la relación principal (compatibilidad con
-- pantallas, exportación NOI, alertas y Resumen). Regla explícita: la ficha
-- refleja SOLO la relación principal; lo que esa relación no tiene se limpia.
--   Con relación vigente: empresa, RP, número interno y antigüedad reconocida
--     de esa relación; alta IMSS y SDI solo si tiene RP (si no, vacíos);
--     estatus Baja → Activo y sin datos de baja.
--   Sin relación vigente: datos de la última relación dada de baja, estatus
--     Baja, fecha y comentario de esa baja.
--   Sin relaciones (todas anuladas): la ficha no se toca.
create function public.laboral_sincronizar_persona(p_personal_id uuid) returns void
language plpgsql security definer set search_path to '' as $$
declare r record; v_estatus text; v_fecha_baja date; v_coment text;
begin
  perform set_config('beehuman.laboral', 'on', true);
  select rl.*, null::text as causa_txt, null::text as motivo into r
    from public.relaciones_laborales rl where rl.id = public.laboral_relacion_principal(p_personal_id);
  if found then
    select case when coalesce(estatus, 'Activo') = 'Baja' then 'Activo' else estatus end into v_estatus
      from public.personal where id = p_personal_id;
    v_fecha_baja := null; v_coment := null;
  else
    select rl.*, cb.descripcion as causa_txt,
           (select e.motivo from public.eventos_laborales e where e.relacion_laboral_id = rl.id and e.tipo = 'baja' and e.estado = 'vigente') as motivo
      into r
      from public.relaciones_laborales rl left join public.causas_baja cb on cb.codigo = rl.causa_baja
     where rl.personal_id = p_personal_id and rl.estado = 'baja'
     order by rl.fecha_baja desc nulls last, rl.actualizado_en desc nulls last, rl.creado_en desc limit 1;
    if not found then
      perform set_config('beehuman.laboral', 'off', true);
      return;
    end if;
    v_estatus := 'Baja'; v_fecha_baja := r.fecha_baja;
    v_coment := nullif(concat_ws(' · ', r.causa_txt, nullif(btrim(r.motivo), '')), '');
  end if;
  update public.personal p set
    empresa_id = r.empresa_id,
    registro_patronal_id = r.registro_patronal_id,
    fecha_alta_imss = case when r.registro_patronal_id is not null then r.fecha_ingreso end,
    sdi_imss = case when r.registro_patronal_id is not null then coalesce(r.sdi, r.sbc) end,
    numero_interno_trabajador = r.numero_interno,
    fecha_antiguedad = r.fecha_reconocimiento_antiguedad,
    estatus = v_estatus, fecha_baja = v_fecha_baja, comentario_baja = v_coment
  where p.id = p_personal_id
    and (p.empresa_id, p.registro_patronal_id, p.fecha_alta_imss, p.sdi_imss, p.numero_interno_trabajador,
         p.fecha_antiguedad, p.estatus, p.fecha_baja, p.comentario_baja)
        is distinct from
        (r.empresa_id, r.registro_patronal_id,
         case when r.registro_patronal_id is not null then r.fecha_ingreso end,
         case when r.registro_patronal_id is not null then coalesce(r.sdi, r.sbc) end,
         r.numero_interno, r.fecha_reconocimiento_antiguedad, v_estatus, v_fecha_baja, v_coment);
  perform set_config('beehuman.laboral', 'off', true);
end $$;

-- Límites legales del SBC (LSS art. 28): piso = salario mínimo diario del
-- área geográfica del RP; tope = 25 UMA. No calcula la integración del SBC
-- (factor de prestaciones, variables): eso será del motor de nómina; aquí
-- solo se impide capturar un SBC fuera de los límites legales.
create function public.laboral_validar_sbc(p_sbc numeric, p_fecha date, p_registro_patronal_id uuid) returns void
language plpgsql stable security definer set search_path to '' as $$
declare v_uma numeric; v_sm numeric; v_zona text;
begin
  if p_sbc is null or p_registro_patronal_id is null then return; end if;
  select zona_salario_minimo into v_zona from public.empresas_registros_patronales where id = p_registro_patronal_id;
  v_uma := public.parametro_vigente('UMA_DIARIA', p_fecha);
  v_sm  := public.parametro_vigente(case when v_zona = 'zlfn' then 'SALARIO_MINIMO_ZLFN' else 'SALARIO_MINIMO_GENERAL' end, p_fecha);
  if v_uma is not null and p_sbc > round(v_uma * 25, 2) then
    raise exception 'BeeHuman: el SBC % rebasa el tope de 25 UMA (%) vigente al %.', p_sbc, round(v_uma * 25, 2), p_fecha;
  end if;
  if v_sm is not null and p_sbc < v_sm then
    raise exception 'BeeHuman: el SBC % es menor al salario mínimo % (%) vigente al %.', p_sbc,
      case when v_zona = 'zlfn' then 'de la zona libre de la frontera norte' else 'general' end, v_sm, p_fecha;
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 7. API: historial laboral
-- ---------------------------------------------------------------------
-- Ingreso o reingreso. Si el RP es nulo, hay historial pero no IDSE.
create function public.laboral_registrar_ingreso(
  p_personal_id uuid, p_empresa_id uuid, p_registro_patronal_id uuid, p_fecha_ingreso date,
  p_fecha_reconocimiento_antiguedad date default null, p_sbc numeric default null, p_sdi numeric default null,
  p_tipo_trabajador text default null, p_tipo_salario text default null, p_jornada text default null,
  p_umf text default null, p_numero_interno text default null, p_motivo text default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  v_rel uuid; v_ev uuid; v_tipo text; v_nss text;
begin
  if p_fecha_ingreso is null then raise exception 'BeeHuman: la fecha de ingreso es obligatoria.'; end if;
  if not exists (select 1 from public.personal where id = p_personal_id and tenant_id = v_tenant) or not public.en_alcance_persona(p_personal_id) then
    raise exception 'BeeHuman: persona no encontrada.';
  end if;
  if not exists (select 1 from public.empresas where id = p_empresa_id and tenant_id = v_tenant) then
    raise exception 'BeeHuman: empresa no encontrada.';
  end if;
  if p_registro_patronal_id is not null and not exists (select 1 from public.empresas_registros_patronales
       where id = p_registro_patronal_id and empresa_id = p_empresa_id and tenant_id = v_tenant) then
    raise exception 'BeeHuman: el registro patronal no pertenece a la empresa.';
  end if;
  if exists (select 1 from public.relaciones_laborales where personal_id = p_personal_id and empresa_id = p_empresa_id
               and registro_patronal_id is not distinct from p_registro_patronal_id and estado = 'vigente') then
    raise exception 'BeeHuman: la persona ya tiene una relación vigente con esa empresa y registro patronal.';
  end if;
  if p_registro_patronal_id is not null then
    select nullif(btrim(nss), '') into v_nss from public.personal where id = p_personal_id;
    if v_nss is not null and exists (select 1 from public.relaciones_laborales rl join public.personal p on p.id = rl.personal_id
         where rl.registro_patronal_id = p_registro_patronal_id and rl.estado = 'vigente' and p.nss = v_nss and p.id <> p_personal_id) then
      raise exception 'BeeHuman: el NSS % ya tiene una relación vigente en este registro patronal con otra ficha (posible persona duplicada).', v_nss;
    end if;
    perform public.laboral_validar_sbc(p_sbc, p_fecha_ingreso, p_registro_patronal_id);
  end if;
  if exists (select 1 from public.relaciones_laborales where personal_id = p_personal_id and empresa_id = p_empresa_id
               and registro_patronal_id is not distinct from p_registro_patronal_id and estado = 'baja') then
    v_tipo := 'reingreso';
  else
    v_tipo := 'ingreso';
  end if;

  perform set_config('beehuman.laboral', 'on', true);
  insert into public.relaciones_laborales (tenant_id, personal_id, empresa_id, registro_patronal_id, numero_interno,
    fecha_ingreso, fecha_reconocimiento_antiguedad, sbc, sdi, tipo_trabajador, tipo_salario, jornada, umf, creado_por)
  values (v_tenant, p_personal_id, p_empresa_id, p_registro_patronal_id, nullif(btrim(p_numero_interno), ''),
    p_fecha_ingreso, p_fecha_reconocimiento_antiguedad, p_sbc, coalesce(p_sdi, p_sbc),
    nullif(p_tipo_trabajador, ''), nullif(p_tipo_salario, ''), nullif(p_jornada, ''), nullif(p_umf, ''), auth.uid())
  returning id into v_rel;

  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo, valores_nuevos, origen, creado_por)
  select v_tenant, p_personal_id, v_rel, v_tipo, p_fecha_ingreso, nullif(btrim(p_motivo), ''),
    jsonb_strip_nulls(jsonb_build_object('empresa_id', r.empresa_id, 'empresa', public.laboral_nombre_catalogo('empresas', r.empresa_id),
      'registro_patronal_id', r.registro_patronal_id,
      'registro_patronal', public.laboral_nombre_catalogo('empresas_registros_patronales', r.registro_patronal_id),
      'numero_interno', r.numero_interno, 'fecha_ingreso', r.fecha_ingreso,
      'fecha_reconocimiento_antiguedad', r.fecha_reconocimiento_antiguedad, 'sbc', r.sbc, 'sdi', r.sdi,
      'tipo_trabajador', r.tipo_trabajador, 'tipo_salario', r.tipo_salario, 'jornada', r.jornada, 'umf', r.umf)),
    'pantalla', auth.uid()
  from public.relaciones_laborales r where r.id = v_rel
  returning id into v_ev;

  if p_registro_patronal_id is not null then
    insert into public.idse_movimientos (tenant_id, evento_id, relacion_laboral_id, registro_patronal_id, tipo_movimiento, fecha_movimiento, sbc)
    values (v_tenant, v_ev, v_rel, p_registro_patronal_id, '08', p_fecha_ingreso, p_sbc);
  end if;

  -- esquemas activos de la persona sin relación que coinciden; los que no traen
  -- RP solo si esta es la única relación vigente con esa empresa
  -- (misma regla de candidata única que el disparador de esquemas: con RP,
  -- coincidencia exacta; sin RP, solo si esta es la única relación vigente
  -- de la persona con esa empresa)
  update public.personal_registros_pago set relacion_laboral_id = v_rel
   where personal_id = p_personal_id and relacion_laboral_id is null and activo and empresa_id = p_empresa_id
     and case when registro_patronal_id is not null
              then registro_patronal_id = p_registro_patronal_id
              else (select count(*) from public.relaciones_laborales
                     where personal_id = p_personal_id and empresa_id = p_empresa_id and estado = 'vigente') = 1
         end;

  perform public.laboral_sincronizar_persona(p_personal_id);
  perform set_config('beehuman.laboral', 'off', true);
  return v_rel;
end $$;

create function public.laboral_registrar_baja(p_relacion_id uuid, p_fecha_baja date, p_causa text, p_motivo text default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  r record; v_ev uuid; v_ultimo date; v_rps jsonb;
begin
  select * into r from public.relaciones_laborales where id = p_relacion_id and tenant_id = v_tenant for update;
  if not found or not public.en_alcance_persona(r.personal_id) then raise exception 'BeeHuman: relación laboral no encontrada.'; end if;
  if r.estado <> 'vigente' then raise exception 'BeeHuman: la relación laboral no está vigente.'; end if;
  if p_fecha_baja is null then raise exception 'BeeHuman: la fecha de baja es obligatoria.'; end if;
  if not exists (select 1 from public.causas_baja where codigo = p_causa and activo) then
    raise exception 'BeeHuman: indica una causa de baja válida.';
  end if;
  if r.fecha_ingreso is null then
    raise exception 'BeeHuman: captura primero la fecha de ingreso de esta relación (dato migrado sin fecha).';
  end if;
  select max(fecha_efectiva) into v_ultimo from public.eventos_laborales
   where relacion_laboral_id = p_relacion_id and estado = 'vigente' and tipo in ('ingreso','reingreso','modificacion_salario');
  if p_fecha_baja < greatest(r.fecha_ingreso, coalesce(v_ultimo, r.fecha_ingreso)) then
    raise exception 'BeeHuman: la baja (%) no puede ser anterior al ingreso o a la última modificación de salario (%).',
      p_fecha_baja, greatest(r.fecha_ingreso, coalesce(v_ultimo, r.fecha_ingreso));
  end if;

  perform set_config('beehuman.laboral', 'on', true);
  select coalesce(jsonb_agg(id), '[]'::jsonb) into v_rps from public.personal_registros_pago
   where relacion_laboral_id = p_relacion_id and activo;

  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, causa, motivo,
    valores_anteriores, valores_nuevos, origen, creado_por)
  values (v_tenant, r.personal_id, p_relacion_id, 'baja', p_fecha_baja, p_causa, nullif(btrim(p_motivo), ''),
    jsonb_build_object('estado', 'vigente', 'esquemas_desactivados', v_rps),
    jsonb_build_object('estado', 'baja', 'fecha_baja', p_fecha_baja, 'causa_baja', p_causa), 'pantalla', auth.uid())
  returning id into v_ev;

  update public.relaciones_laborales set estado = 'baja', fecha_baja = p_fecha_baja, causa_baja = p_causa,
         actualizado_por = auth.uid(), actualizado_en = now()
   where id = p_relacion_id;
  update public.personal_registros_pago set activo = false, fecha_fin = coalesce(fecha_fin, p_fecha_baja)
   where relacion_laboral_id = p_relacion_id and activo;

  if r.registro_patronal_id is not null then
    insert into public.idse_movimientos (tenant_id, evento_id, relacion_laboral_id, registro_patronal_id, tipo_movimiento,
      fecha_movimiento, sbc, causa_baja)
    values (v_tenant, v_ev, p_relacion_id, r.registro_patronal_id, '02', p_fecha_baja, r.sbc, p_causa);
  end if;
  perform public.laboral_sincronizar_persona(r.personal_id);
  perform set_config('beehuman.laboral', 'off', true);
  return v_ev;
end $$;

create function public.laboral_modificar_salario(p_relacion_id uuid, p_fecha_efectiva date, p_sbc numeric,
  p_sdi numeric default null, p_tipo_salario text default null, p_motivo text default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  r record; v_ev uuid; v_ultima date;
begin
  select * into r from public.relaciones_laborales where id = p_relacion_id and tenant_id = v_tenant for update;
  if not found or not public.en_alcance_persona(r.personal_id) then raise exception 'BeeHuman: relación laboral no encontrada.'; end if;
  if r.estado <> 'vigente' then raise exception 'BeeHuman: la relación laboral no está vigente.'; end if;
  if p_fecha_efectiva is null or p_sbc is null or p_sbc <= 0 then
    raise exception 'BeeHuman: la fecha efectiva y el nuevo SBC son obligatorios.';
  end if;
  if r.fecha_ingreso is null or p_fecha_efectiva < r.fecha_ingreso then
    raise exception 'BeeHuman: la modificación no puede ser anterior al ingreso de la relación.';
  end if;
  -- orden cronológico: no se intercala una modificación antes de la última
  -- vigente (una corrección histórica requerirá su propio procedimiento)
  select max(fecha_efectiva) into v_ultima from public.eventos_laborales
   where relacion_laboral_id = p_relacion_id and estado = 'vigente' and tipo = 'modificacion_salario';
  if v_ultima is not null and p_fecha_efectiva <= v_ultima then
    raise exception 'BeeHuman: la modificación debe ser posterior a la última modificación de salario vigente (%).', v_ultima;
  end if;
  if p_sbc is not distinct from r.sbc and coalesce(p_tipo_salario, r.tipo_salario) is not distinct from r.tipo_salario then
    raise exception 'BeeHuman: el SBC no cambia.';
  end if;
  perform public.laboral_validar_sbc(p_sbc, p_fecha_efectiva, r.registro_patronal_id);

  perform set_config('beehuman.laboral', 'on', true);
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo,
    valores_anteriores, valores_nuevos, origen, creado_por)
  values (v_tenant, r.personal_id, p_relacion_id, 'modificacion_salario', p_fecha_efectiva, nullif(btrim(p_motivo), ''),
    jsonb_strip_nulls(jsonb_build_object('sbc', r.sbc, 'sdi', r.sdi, 'tipo_salario', r.tipo_salario)),
    jsonb_strip_nulls(jsonb_build_object('sbc', p_sbc, 'sdi', coalesce(p_sdi, p_sbc), 'tipo_salario', coalesce(nullif(p_tipo_salario, ''), r.tipo_salario))),
    'pantalla', auth.uid())
  returning id into v_ev;
  update public.relaciones_laborales set sbc = p_sbc, sdi = coalesce(p_sdi, p_sbc),
         tipo_salario = coalesce(nullif(p_tipo_salario, ''), tipo_salario), actualizado_por = auth.uid(), actualizado_en = now()
   where id = p_relacion_id;
  if r.registro_patronal_id is not null then
    insert into public.idse_movimientos (tenant_id, evento_id, relacion_laboral_id, registro_patronal_id, tipo_movimiento, fecha_movimiento, sbc)
    values (v_tenant, v_ev, p_relacion_id, r.registro_patronal_id, '07', p_fecha_efectiva, p_sbc);
  end if;
  perform public.laboral_sincronizar_persona(r.personal_id);
  perform set_config('beehuman.laboral', 'off', true);
  return v_ev;
end $$;

-- Corrección de datos que no son un movimiento ante el IMSS (UMF, tipos,
-- número interno, antigüedad reconocida). Fecha de ingreso y SBC solo se
-- corrigen en relaciones migradas (datos que nunca se presentaron).
create function public.laboral_corregir_datos(p_relacion_id uuid, p_cambios jsonb, p_motivo text)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  r record; v_ev uuid; k text; ant jsonb := '{}'; nue jsonb := '{}';
  permitidos text[] := array['numero_interno','fecha_reconocimiento_antiguedad','tipo_trabajador','tipo_salario','jornada','umf'];
  solo_migrado text[] := array['fecha_ingreso','sbc','sdi'];
  v_ingreso_migrado boolean;
begin
  select * into r from public.relaciones_laborales where id = p_relacion_id and tenant_id = v_tenant for update;
  if not found or not public.en_alcance_persona(r.personal_id) then raise exception 'BeeHuman: relación laboral no encontrada.'; end if;
  if r.estado = 'anulada' then raise exception 'BeeHuman: la relación laboral está anulada.'; end if;
  if coalesce(btrim(p_motivo), '') = '' then raise exception 'BeeHuman: indica el motivo de la corrección.'; end if;
  if p_cambios is null or jsonb_typeof(p_cambios) <> 'object' or p_cambios = '{}'::jsonb then
    raise exception 'BeeHuman: no hay cambios que registrar.';
  end if;
  select exists (select 1 from public.eventos_laborales where relacion_laboral_id = p_relacion_id
                  and tipo in ('ingreso','reingreso') and estado = 'vigente' and origen = 'migracion')
     and not exists (select 1 from public.eventos_laborales where relacion_laboral_id = p_relacion_id
                  and tipo = 'modificacion_salario' and estado = 'vigente')
    into v_ingreso_migrado;
  for k in select jsonb_object_keys(p_cambios) loop
    if k = any(solo_migrado) and not v_ingreso_migrado then
      raise exception 'BeeHuman: % solo se corrige en datos migrados; para un ingreso o salario reales usa anular y registrar de nuevo, o una modificación de salario.', k;
    elsif not (k = any(permitidos) or k = any(solo_migrado)) then
      raise exception 'BeeHuman: el campo % no se corrige por esta vía.', k;
    end if;
    ant := ant || jsonb_build_object(k, to_jsonb(r) -> k);
    nue := nue || jsonb_build_object(k, p_cambios -> k);
  end loop;
  if ant = nue then raise exception 'BeeHuman: los valores no cambian.'; end if;
  -- Coherencia de la corrección (la tabla no exige el orden de fechas en
  -- relaciones migradas, así que se valida aquí antes de guardar)
  if p_cambios ? 'fecha_ingreso' then
    if p_cambios->>'fecha_ingreso' is null then
      raise exception 'BeeHuman: la fecha de ingreso corregida no puede quedar vacía.';
    end if;
    if r.fecha_baja is not null and (p_cambios->>'fecha_ingreso')::date > r.fecha_baja then
      raise exception 'BeeHuman: la fecha de ingreso (%) no puede ser posterior a la baja de la relación (%).', p_cambios->>'fecha_ingreso', r.fecha_baja;
    end if;
    if exists (select 1 from public.eventos_laborales where relacion_laboral_id = p_relacion_id and estado = 'vigente'
                 and tipo = 'modificacion_salario' and fecha_efectiva < (p_cambios->>'fecha_ingreso')::date) then
      raise exception 'BeeHuman: la fecha de ingreso no puede quedar después de una modificación de salario vigente.';
    end if;
  end if;
  if p_cambios ? 'sbc' then
    if (p_cambios->>'sbc') is null or (p_cambios->>'sbc')::numeric <= 0 then
      raise exception 'BeeHuman: el SBC corregido debe ser mayor a cero.';
    end if;
    perform public.laboral_validar_sbc((p_cambios->>'sbc')::numeric,
      coalesce((p_cambios->>'fecha_ingreso')::date, r.fecha_ingreso, current_date), r.registro_patronal_id);
  end if;

  perform set_config('beehuman.laboral', 'on', true);
  update public.relaciones_laborales set
    numero_interno = case when p_cambios ? 'numero_interno' then nullif(btrim(p_cambios->>'numero_interno'), '') else numero_interno end,
    fecha_reconocimiento_antiguedad = case when p_cambios ? 'fecha_reconocimiento_antiguedad' then (p_cambios->>'fecha_reconocimiento_antiguedad')::date else fecha_reconocimiento_antiguedad end,
    tipo_trabajador = case when p_cambios ? 'tipo_trabajador' then nullif(p_cambios->>'tipo_trabajador', '') else tipo_trabajador end,
    tipo_salario = case when p_cambios ? 'tipo_salario' then nullif(p_cambios->>'tipo_salario', '') else tipo_salario end,
    jornada = case when p_cambios ? 'jornada' then nullif(p_cambios->>'jornada', '') else jornada end,
    umf = case when p_cambios ? 'umf' then nullif(p_cambios->>'umf', '') else umf end,
    fecha_ingreso = case when p_cambios ? 'fecha_ingreso' then (p_cambios->>'fecha_ingreso')::date else fecha_ingreso end,
    fecha_ingreso_origen = case when p_cambios ? 'fecha_ingreso' and p_cambios->>'fecha_ingreso' is not null then 'captura' else fecha_ingreso_origen end,
    sbc = case when p_cambios ? 'sbc' then (p_cambios->>'sbc')::numeric else sbc end,
    sdi = case when p_cambios ? 'sdi' then (p_cambios->>'sdi')::numeric when p_cambios ? 'sbc' then (p_cambios->>'sbc')::numeric else sdi end,
    actualizado_por = auth.uid(), actualizado_en = now()
  where id = p_relacion_id;
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo,
    valores_anteriores, valores_nuevos, origen, creado_por)
  values (v_tenant, r.personal_id, p_relacion_id, 'correccion_datos', greatest(current_date, coalesce((p_cambios->>'fecha_ingreso')::date, r.fecha_ingreso, current_date)),
    btrim(p_motivo), ant, nue, 'pantalla', auth.uid())
  returning id into v_ev;
  perform public.laboral_sincronizar_persona(r.personal_id);
  perform set_config('beehuman.laboral', 'off', true);
  return v_ev;
end $$;

-- Anular: solo el último evento IMSS vigente de la relación (ingreso,
-- reingreso, baja o modificación de salario) y solo si su movimiento IDSE
-- no está en un archivo ni presentado.
create function public.laboral_anular_evento(p_evento_id uuid, p_motivo text) returns void
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  e record; r record; m record; v_ultimo uuid;
begin
  if coalesce(btrim(p_motivo), '') = '' then raise exception 'BeeHuman: indica el motivo de la anulación.'; end if;
  select * into e from public.eventos_laborales where id = p_evento_id and tenant_id = v_tenant;
  if not found or not public.en_alcance_persona(e.personal_id) then raise exception 'BeeHuman: evento no encontrado.'; end if;
  if e.estado <> 'vigente' then raise exception 'BeeHuman: el evento ya está anulado.'; end if;
  if e.tipo not in ('ingreso','reingreso','baja','modificacion_salario') then
    raise exception 'BeeHuman: este evento refleja un cambio de la ficha; para corregirlo vuelve a editar el dato.';
  end if;
  if e.origen = 'migracion' then
    raise exception 'BeeHuman: los eventos migrados no se anulan; corrige sus datos con «Corregir datos».';
  end if;
  select * into r from public.relaciones_laborales where id = e.relacion_laboral_id for update;
  select id into v_ultimo from public.eventos_laborales
   where relacion_laboral_id = e.relacion_laboral_id and estado = 'vigente'
     and tipo in ('ingreso','reingreso','baja','modificacion_salario')
   order by registrado_en desc limit 1;
  if v_ultimo <> e.id then
    raise exception 'BeeHuman: solo se puede anular el último movimiento de la relación; anula primero los posteriores.';
  end if;
  select * into m from public.idse_movimientos where evento_id = e.id and estado <> 'cancelado';
  if found and m.estado not in ('pendiente','rechazado') then
    raise exception 'BeeHuman: el movimiento IDSE está %; cancela el archivo o, si ya se presentó, corrígelo ante el IMSS.', m.estado;
  end if;

  perform set_config('beehuman.laboral', 'on', true);
  update public.eventos_laborales set estado = 'anulado', anulado_en = now(), anulado_por = auth.uid(), motivo_anulacion = btrim(p_motivo)
   where id = e.id;
  if found then
    update public.idse_movimientos set estado = 'cancelado', actualizado_por = auth.uid(), actualizado_en = now(), archivo_id = null
     where evento_id = e.id and estado in ('pendiente','rechazado');
  end if;

  if e.tipo in ('ingreso','reingreso') then
    if exists (select 1 from public.eventos_laborales where relacion_laboral_id = r.id and estado = 'vigente'
                 and tipo not in ('cambio_puesto','cambio_jefe','cambio_organizacion','cambio_esquema_pago','correccion_datos')) then
      raise exception 'BeeHuman: la relación tiene otros movimientos vigentes.';
    end if;
    update public.relaciones_laborales set estado = 'anulada', actualizado_por = auth.uid(), actualizado_en = now() where id = r.id;
    update public.personal_registros_pago set relacion_laboral_id = null where relacion_laboral_id = r.id;
  elsif e.tipo = 'baja' then
    if exists (select 1 from public.relaciones_laborales where personal_id = r.personal_id and empresa_id = r.empresa_id
                 and registro_patronal_id is not distinct from r.registro_patronal_id and estado = 'vigente' and id <> r.id) then
      raise exception 'BeeHuman: ya existe un reingreso vigente en esa empresa y registro patronal; anúlalo primero.';
    end if;
    update public.relaciones_laborales set estado = 'vigente', fecha_baja = null, causa_baja = null,
           actualizado_por = auth.uid(), actualizado_en = now() where id = r.id;
    update public.personal_registros_pago rp set activo = true,
           fecha_fin = case when rp.fecha_fin = e.fecha_efectiva then null else rp.fecha_fin end
     where rp.id in (select (jsonb_array_elements_text(e.valores_anteriores->'esquemas_desactivados'))::uuid)
       and not rp.activo;
  elsif e.tipo = 'modificacion_salario' then
    update public.relaciones_laborales set sbc = (e.valores_anteriores->>'sbc')::numeric,
           sdi = (e.valores_anteriores->>'sdi')::numeric, tipo_salario = e.valores_anteriores->>'tipo_salario',
           actualizado_por = auth.uid(), actualizado_en = now() where id = r.id;
  end if;
  perform public.laboral_sincronizar_persona(r.personal_id);
  perform set_config('beehuman.laboral', 'off', true);
end $$;

-- Historial para cualquier rol con alcance. Consulta y Coordinador no ven
-- importes (SBC, SDI, sueldos).
create function public.laboral_historial(p_personal_id uuid)
returns table (relacion_id uuid, empresa text, registro_patronal text, relacion_estado text, fecha_ingreso date,
  fecha_reconocimiento_antiguedad date, fecha_baja date, evento_id uuid, tipo text, fecha_efectiva date,
  registrado_en timestamptz, causa text, causa_descripcion text, motivo text, valores_anteriores jsonb,
  valores_nuevos jsonb, estado text, origen text, registrado_por text, idse_estado text, idse_tipo text)
language plpgsql stable security definer set search_path to '' as $$
declare v_importes boolean := public.tiene_rol('administrador','nomina');
  ocultar text[] := array['sbc','sdi','sueldo'];
begin
  if public.current_tenant_id() is null or not public.tiene_rol('administrador','nomina','consulta','coordinador')
     or not public.en_alcance_persona(p_personal_id) then
    return;
  end if;
  return query
  select rl.id, em.nombre, rp.registro_patronal, rl.estado, rl.fecha_ingreso, rl.fecha_reconocimiento_antiguedad, rl.fecha_baja,
         e.id, e.tipo, e.fecha_efectiva, e.registrado_en, e.causa, cb.descripcion, e.motivo,
         case when v_importes then e.valores_anteriores else e.valores_anteriores - ocultar end,
         case when v_importes then e.valores_nuevos else e.valores_nuevos - ocultar end,
         e.estado, e.origen, coalesce(u.email, case when e.origen in ('migracion') then 'migración' else 'sistema' end),
         m.estado, m.tipo_movimiento
    from public.relaciones_laborales rl
    join public.empresas em on em.id = rl.empresa_id
    left join public.empresas_registros_patronales rp on rp.id = rl.registro_patronal_id
    join public.eventos_laborales e on e.relacion_laboral_id = rl.id
    left join public.causas_baja cb on cb.codigo = e.causa
    left join auth.users u on u.id = e.creado_por
    left join lateral (select mm.estado, mm.tipo_movimiento from public.idse_movimientos mm
                        where mm.evento_id = e.id order by mm.creado_en desc limit 1) m on true
   where rl.personal_id = p_personal_id and rl.tenant_id = public.current_tenant_id()
   order by rl.fecha_ingreso desc nulls last, rl.creado_en desc, e.fecha_efectiva desc nulls last, e.registrado_en desc;
end $$;

-- ---------------------------------------------------------------------
-- 8. API: IDSE
-- ---------------------------------------------------------------------
-- Ñ: regla provisional en un solo lugar (pendiente de confirmar con un archivo de NOI).
create function public.idse_texto(p_valor text, p_largo int) returns text
language sql immutable set search_path to '' as $$
  select rpad(left(btrim(regexp_replace(regexp_replace(
           translate(upper(coalesce(p_valor, '')), 'ÁÉÍÓÚÜÀÈÌÒÙÄËÏÖÑ', 'AEIOUUAEIOUAEIO#'),
           '[^A-Z0-9# ]', ' ', 'g'), ' +', ' ', 'g')), p_largo), p_largo, ' ');
$$;

-- Validación previa: una fila por movimiento con sus errores y avisos.
create function public.idse_validar(p_registro_patronal_id uuid, p_tipo text default '08')
returns table (movimiento_id uuid, personal_id uuid, nombre text, fecha_movimiento date, errores text[], avisos text[])
language plpgsql stable security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  v_guia text;
begin
  if p_tipo <> '08' then
    raise exception 'BeeHuman: el archivo de % se habilita cuando confirmemos el formato con un archivo real.', case p_tipo when '02' then 'bajas' else 'modificaciones' end;
  end if;
  select guia_idse into v_guia from public.empresas_registros_patronales where id = p_registro_patronal_id and tenant_id = v_tenant;
  if not found then raise exception 'BeeHuman: registro patronal no encontrado.'; end if;
  return query
  select m.id, p.id, p.nombre_completo, m.fecha_movimiento,
    array_remove(array[
      case when v_guia is null then 'El registro patronal no tiene número de guía IDSE' end,
      case when not public.es_nss_valido(nullif(p.nss, '')) then 'NSS de 11 dígitos' end,
      case when not public.es_curp_valida(nullif(p.curp, '')) then 'CURP válida' end,
      case when coalesce(btrim(p.primer_apellido), '') = '' then 'Primer apellido' end,
      case when coalesce(btrim(p.nombres), '') = '' then 'Nombre(s) separado del apellido' end,
      case when m.sbc is null then 'SBC' end,
      case when rl.tipo_trabajador is null then 'Tipo de trabajador' end,
      case when rl.tipo_salario is null then 'Tipo de salario' end,
      case when rl.jornada is null then 'Jornada' end,
      case when rl.umf is null then 'UMF' end,
      case when rl.numero_interno is null then 'Número interno (clave del trabajador)' end
    ], null),
    array_remove(array[
      case when concat(p.primer_apellido, p.segundo_apellido, p.nombres) ~ '[Ññ]' then 'Contiene Ñ: se escribe como # (regla provisional)' end,
      case when m.fecha_movimiento < current_date - 5 then 'Fecha con más de 5 días: revisa el plazo de presentación' end,
      case when m.estado = 'rechazado' then 'Reenvío de un movimiento rechazado: ' || coalesce(m.motivo_rechazo, '') end
    ], null)
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.personal p on p.id = rl.personal_id
  where m.tenant_id = v_tenant and m.registro_patronal_id = p_registro_patronal_id and m.tipo_movimiento = p_tipo
    and m.estado in ('pendiente','rechazado') and public.en_alcance_persona(p.id)
  order by p.primer_apellido, p.segundo_apellido, p.nombres;
end $$;

create function public.idse_linea_alta(p_movimiento_id uuid, p_guia text) returns text
language sql stable security definer set search_path to '' as $$
  select rpad(upper(rp.registro_patronal), 11, ' ')
      || p.nss
      || public.idse_texto(p.primer_apellido, 27)
      || public.idse_texto(p.segundo_apellido, 27)
      || public.idse_texto(p.nombres, 27)
      || lpad((round(m.sbc * 100))::bigint::text, 6, '0')
      || repeat(' ', 6)
      || rl.tipo_trabajador || rl.tipo_salario || rl.jornada
      || to_char(m.fecha_movimiento, 'DDMMYYYY')
      || rl.umf
      || repeat(' ', 2)
      || '08' || p_guia
      || lpad(upper(btrim(rl.numero_interno)), 10, ' ')
      || ' '
      || p.curp
      || '9'
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.empresas_registros_patronales rp on rp.id = m.registro_patronal_id
  join public.personal p on p.id = rl.personal_id
  where m.id = p_movimiento_id;
$$;

-- Genera el archivo en el servidor. Si cualquier movimiento tiene errores,
-- no se genera nada. Devuelve el id del archivo.
create function public.idse_generar_archivo(p_registro_patronal_id uuid, p_tipo text default '08', p_movimientos uuid[] default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  v_rp record; v_ids uuid[]; v_lineas text[]; v_err text; v_contenido text; v_arch uuid; i int; v_linea text;
begin
  select * into v_rp from public.empresas_registros_patronales where id = p_registro_patronal_id and tenant_id = v_tenant;
  if not found then raise exception 'BeeHuman: registro patronal no encontrado.'; end if;
  select string_agg(nombre || ': ' || array_to_string(errores, ', '), ' | ')
    into v_err
    from public.idse_validar(p_registro_patronal_id, p_tipo) v
   where cardinality(errores) > 0 and (p_movimientos is null or v.movimiento_id = any(p_movimientos));
  if v_err is not null then raise exception 'BeeHuman: faltan datos para el archivo IDSE — %', left(v_err, 1500); end if;

  -- la selección debe ser exacta: cada id pedido es un movimiento disponible de
  -- este RP y tipo; no se genera un archivo distinto al que Nómina eligió
  if p_movimientos is not null then
    if cardinality(p_movimientos) = 0 then raise exception 'BeeHuman: no seleccionaste movimientos.'; end if;
    if (select count(distinct x) from unnest(p_movimientos) x) <> cardinality(p_movimientos) then
      raise exception 'BeeHuman: la selección tiene movimientos repetidos.';
    end if;
    select string_agg(x::text, ', ') into v_err from unnest(p_movimientos) x
     where x not in (select v.movimiento_id from public.idse_validar(p_registro_patronal_id, p_tipo) v);
    if v_err is not null then
      raise exception 'BeeHuman: estos movimientos no están disponibles para este registro patronal y tipo: %', v_err;
    end if;
  end if;
  select array_agg(v.movimiento_id order by v.ord) into v_ids
    from public.idse_validar(p_registro_patronal_id, p_tipo)
         with ordinality as v(movimiento_id, personal_id, nombre, fecha_movimiento, errores, avisos, ord)
   where p_movimientos is null or v.movimiento_id = any(p_movimientos);
  if v_ids is null then raise exception 'BeeHuman: no hay movimientos pendientes para este archivo.'; end if;
  -- bloqueo: nadie más puede meterlos en otro archivo a la vez
  perform 1 from public.idse_movimientos where id = any(v_ids) and estado in ('pendiente','rechazado') for update;
  if (select count(*) from public.idse_movimientos where id = any(v_ids) and estado in ('pendiente','rechazado')) <> cardinality(v_ids) then
    raise exception 'BeeHuman: algún movimiento cambió de estado mientras se generaba el archivo; vuelve a intentarlo.';
  end if;

  v_lineas := '{}';
  for i in 1 .. cardinality(v_ids) loop
    v_linea := public.idse_linea_alta(v_ids[i], v_rp.guia_idse);
    if v_linea is null or char_length(v_linea) <> 168 then
      raise exception 'BeeHuman: la línea del movimiento % no mide 168 posiciones (%).', v_ids[i], coalesce(char_length(v_linea), 0);
    end if;
    v_lineas := v_lineas || v_linea;
  end loop;
  -- renglón final: 13 asteriscos, número de movimientos (pos. 57-62), guía (134-138), '9'
  v_contenido := array_to_string(v_lineas, E'\r\n') || E'\r\n'
    || rpad('*************', 56, ' ') || lpad(cardinality(v_ids)::text, 6, '0') || repeat(' ', 71) || v_rp.guia_idse
    || repeat(' ', 29) || '9' || E'\r\n';

  perform set_config('beehuman.laboral', 'on', true);
  insert into public.idse_archivos (tenant_id, empresa_id, registro_patronal_id, tipo_movimiento, guia, nombre_archivo,
    num_registros, contenido, hash_sha256, generado_por)
  values (v_tenant, v_rp.empresa_id, v_rp.id, p_tipo, v_rp.guia_idse,
    'IDSE_' || case p_tipo when '08' then 'ALTAS' when '02' then 'BAJAS' else 'MODIFICACIONES' end || '_' || upper(v_rp.registro_patronal)
      || '_' || to_char(now() at time zone 'America/Mexico_City', 'YYYYMMDD_HH24MI') || '.dat',
    cardinality(v_ids), v_contenido, encode(sha256(convert_to(v_contenido, 'UTF8')), 'hex'), auth.uid())
  returning id into v_arch;
  insert into public.idse_archivo_renglones (archivo_id, movimiento_id, tenant_id, linea, texto)
  select v_arch, v_ids[g.n], v_tenant, g.n, v_lineas[g.n] from generate_series(1, cardinality(v_ids)) as g(n);
  update public.idse_movimientos set estado = 'en_archivo', archivo_id = v_arch, motivo_rechazo = null,
         actualizado_por = auth.uid(), actualizado_en = now()
   where id = any(v_ids);
  perform set_config('beehuman.laboral', 'off', true);
  return v_arch;
end $$;

create function public.idse_cancelar_archivo(p_archivo_id uuid, p_motivo text) returns void
language plpgsql security definer set search_path to '' as $$
declare v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']); a record;
begin
  if coalesce(btrim(p_motivo), '') = '' then raise exception 'BeeHuman: indica el motivo.'; end if;
  select * into a from public.idse_archivos where id = p_archivo_id and tenant_id = v_tenant for update;
  if not found then raise exception 'BeeHuman: archivo no encontrado.'; end if;
  if a.estado <> 'generado' then raise exception 'BeeHuman: solo se cancela un archivo que no se ha presentado.'; end if;
  perform set_config('beehuman.laboral', 'on', true);
  update public.idse_archivos set estado = 'cancelado', motivo_cancelacion = btrim(p_motivo), actualizado_por = auth.uid(), actualizado_en = now()
   where id = p_archivo_id;
  update public.idse_archivo_renglones set resultado = 'cancelado' where archivo_id = p_archivo_id;
  update public.idse_movimientos set estado = 'pendiente', archivo_id = null, actualizado_por = auth.uid(), actualizado_en = now()
   where archivo_id = p_archivo_id and estado = 'en_archivo';
  perform set_config('beehuman.laboral', 'off', true);
end $$;

create function public.idse_marcar_presentado(p_archivo_id uuid, p_lote text, p_fecha date) returns void
language plpgsql security definer set search_path to '' as $$
declare v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']); a record;
begin
  if coalesce(btrim(p_lote), '') = '' or p_fecha is null then raise exception 'BeeHuman: indica el número de lote y la fecha de presentación.'; end if;
  select * into a from public.idse_archivos where id = p_archivo_id and tenant_id = v_tenant for update;
  if not found then raise exception 'BeeHuman: archivo no encontrado.'; end if;
  if a.estado <> 'generado' then raise exception 'BeeHuman: el archivo ya está %.', a.estado; end if;
  perform set_config('beehuman.laboral', 'on', true);
  update public.idse_archivos set estado = 'presentado', lote_idse = btrim(p_lote), fecha_presentacion = p_fecha,
         actualizado_por = auth.uid(), actualizado_en = now() where id = p_archivo_id;
  update public.idse_movimientos set estado = 'presentado', actualizado_por = auth.uid(), actualizado_en = now()
   where archivo_id = p_archivo_id and estado = 'en_archivo';
  perform set_config('beehuman.laboral', 'off', true);
end $$;

-- Resultado del lote: los indicados en p_rechazados ([{movimiento_id, motivo}])
-- quedan rechazados y pueden reenviarse; el resto, confirmados.
create function public.idse_registrar_resultado(p_archivo_id uuid, p_rechazados jsonb default '[]'::jsonb,
  p_acuse_folio text default null, p_acuse_fecha date default null) returns void
language plpgsql security definer set search_path to '' as $$
declare v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']); a record; x record;
begin
  select * into a from public.idse_archivos where id = p_archivo_id and tenant_id = v_tenant for update;
  if not found then raise exception 'BeeHuman: archivo no encontrado.'; end if;
  if a.estado <> 'presentado' then raise exception 'BeeHuman: primero marca el archivo como presentado.'; end if;
  if jsonb_typeof(coalesce(p_rechazados, '[]'::jsonb)) <> 'array' then raise exception 'BeeHuman: formato de rechazados inválido.'; end if;
  for x in select (j->>'movimiento_id')::uuid mid, j->>'motivo' motivo from jsonb_array_elements(coalesce(p_rechazados, '[]'::jsonb)) j loop
    if not exists (select 1 from public.idse_archivo_renglones where archivo_id = p_archivo_id and movimiento_id = x.mid) then
      raise exception 'BeeHuman: el movimiento % no está en este archivo.', x.mid;
    end if;
    if coalesce(btrim(x.motivo), '') = '' then raise exception 'BeeHuman: indica el motivo de cada rechazo.'; end if;
  end loop;
  perform set_config('beehuman.laboral', 'on', true);
  update public.idse_archivo_renglones g set
         resultado = case when j.mid is null then 'confirmado' else 'rechazado' end,
         motivo_rechazo = nullif(btrim(j.motivo), '')
    from public.idse_archivo_renglones g2
    left join (select (elem->>'movimiento_id')::uuid mid, elem->>'motivo' motivo
                 from jsonb_array_elements(coalesce(p_rechazados, '[]'::jsonb)) as t(elem)) j on j.mid = g2.movimiento_id
   where g.archivo_id = p_archivo_id and g2.archivo_id = g.archivo_id and g2.movimiento_id = g.movimiento_id;
  update public.idse_movimientos m set estado = g.resultado, motivo_rechazo = g.motivo_rechazo,
         actualizado_por = auth.uid(), actualizado_en = now()
    from public.idse_archivo_renglones g
   where g.archivo_id = p_archivo_id and g.movimiento_id = m.id and m.archivo_id = p_archivo_id and m.estado = 'presentado';
  update public.idse_archivos set estado = 'con_resultado', acuse_folio = nullif(btrim(p_acuse_folio), ''), acuse_fecha = p_acuse_fecha,
         actualizado_por = auth.uid(), actualizado_en = now() where id = p_archivo_id;
  perform set_config('beehuman.laboral', 'off', true);
end $$;

-- Prima de riesgo: nueva vigencia (cierra la anterior); nunca sobrescribe.
create function public.prima_riesgo_registrar(p_registro_patronal_id uuid, p_prima numeric, p_clase text, p_desde date)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare v_tenant uuid := public.laboral_exigir_rol(array['administrador']); v_rp record; v_ult date; v_id uuid;
begin
  select * into v_rp from public.empresas_registros_patronales where id = p_registro_patronal_id and tenant_id = v_tenant;
  if not found then raise exception 'BeeHuman: registro patronal no encontrado.'; end if;
  select max(vigente_desde) into v_ult from public.prima_riesgo_rp where registro_patronal_id = p_registro_patronal_id;
  if v_ult is not null and p_desde <= v_ult then
    raise exception 'BeeHuman: la nueva prima debe iniciar después de la vigente (%).', v_ult;
  end if;
  perform set_config('beehuman.laboral', 'on', true);
  update public.prima_riesgo_rp set vigente_hasta = p_desde - 1
   where registro_patronal_id = p_registro_patronal_id and vigente_hasta is null;
  insert into public.prima_riesgo_rp (tenant_id, empresa_id, registro_patronal_id, prima, clase, vigente_desde, creado_por)
  values (v_tenant, v_rp.empresa_id, v_rp.id, p_prima, nullif(p_clase, ''), p_desde, auth.uid()) returning id into v_id;
  perform set_config('beehuman.laboral', 'off', true);
  return v_id;
end $$;

-- ---------------------------------------------------------------------
-- 9. RLS y permisos
-- ---------------------------------------------------------------------
alter table public.parametros_generales  enable row level security;
alter table public.causas_baja           enable row level security;
alter table public.prima_riesgo_rp       enable row level security;
alter table public.relaciones_laborales  enable row level security;
alter table public.eventos_laborales     enable row level security;
alter table public.idse_movimientos      enable row level security;
alter table public.idse_archivos         enable row level security;
alter table public.idse_archivo_renglones enable row level security;

create policy parametros_generales_select on public.parametros_generales for select to authenticated using (true);
create policy causas_baja_select on public.causas_baja for select to authenticated using (true);
create policy prima_riesgo_rp_select on public.prima_riesgo_rp for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));
create policy relaciones_laborales_select on public.relaciones_laborales for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina') and public.en_alcance_persona(personal_id));
create policy eventos_laborales_select on public.eventos_laborales for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina') and public.en_alcance_persona(personal_id));
create policy idse_movimientos_select on public.idse_movimientos for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));
create policy idse_archivos_select on public.idse_archivos for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));
create policy idse_archivo_renglones_select on public.idse_archivo_renglones for select to authenticated
  using (tenant_id = public.current_tenant_id() and public.tiene_rol('administrador','nomina'));

revoke all on public.parametros_generales, public.causas_baja, public.prima_riesgo_rp, public.relaciones_laborales,
  public.eventos_laborales, public.idse_movimientos, public.idse_archivos, public.idse_archivo_renglones from anon, authenticated;
grant select on public.parametros_generales, public.causas_baja, public.prima_riesgo_rp, public.relaciones_laborales,
  public.eventos_laborales, public.idse_movimientos, public.idse_archivos, public.idse_archivo_renglones to authenticated;

-- Funciones nuevas: ninguna para anon/public; authenticated solo la API.
do $$
declare f record;
begin
  for f in select p.oid::regprocedure sig from pg_proc p
           where p.pronamespace = 'public'::regnamespace
             and (p.proname like 'laboral\_%' or p.proname like 'idse\_%' or p.proname in ('parametro_vigente','prima_riesgo_registrar')) loop
    execute format('revoke all on function %s from public, anon, authenticated', f.sig);
  end loop;
end $$;
grant execute on function
  public.laboral_registrar_ingreso(uuid,uuid,uuid,date,date,numeric,numeric,text,text,text,text,text,text),
  public.laboral_registrar_baja(uuid,date,text,text),
  public.laboral_modificar_salario(uuid,date,numeric,numeric,text,text),
  public.laboral_corregir_datos(uuid,jsonb,text),
  public.laboral_anular_evento(uuid,text),
  public.laboral_historial(uuid),
  public.idse_validar(uuid,text),
  public.idse_generar_archivo(uuid,text,uuid[]),
  public.idse_cancelar_archivo(uuid,text),
  public.idse_marcar_presentado(uuid,text,date),
  public.idse_registrar_resultado(uuid,jsonb,text,date),
  public.prima_riesgo_registrar(uuid,numeric,text,date),
  public.parametro_vigente(text,date),
  public.laboral_en_funcion()          -- solo lee el interruptor; lo usan disparadores
to authenticated;

commit;
