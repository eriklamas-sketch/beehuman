-- =====================================================================
-- BeeHuman · MIGRACIÓN BASE V1 (esquema de producción reconstruido)
-- Archivo: supabase/migrations/20261001173928_base_v1_esquema_reconstruido.sql
-- Fuente: catálogo de producción (vovyvvpwtjdlswerfjqb), leído el 19-oct-2026
--         en modo solo lectura. Huella de esquema esperada al terminar:
--         03e98353d5e19d32ad52fd84b464f608 (supabase/verificacion/huella_esquema.sql)
--
-- QUÉ ES: una sola migración que crea desde cero el esquema público que hoy
-- tiene producción (V1, hasta 7D-6a inclusive): 19 tablas, 1 vista,
-- 1 secuencia, 19 funciones, 46 triggers, 21 políticas, permisos y RLS.
-- Sustituye, para entornos nuevos, la estructura creada a mano en el panel
-- (personal, empresas, proyectos, combos…) más las 11 migraciones
-- registradas en producción (20260928222644 … 20261001173928).
--
-- QUÉ NO ES:
--   * No contiene datos (ni tenants, ni usuarios, ni catálogos).
--   * No debe ejecutarse en producción: producción ya tiene este esquema.
--     Lleva un candado que aborta si public.personal ya existe.
--   * La versión 20261001173928 coincide a propósito con la última
--     migración ya registrada en producción, para que producción la
--     considere aplicada (ver docs/V2.0-migraciones.md, «historial»).
--
-- REQUISITOS DEL ENTORNO (los da cualquier proyecto Supabase; para una
-- base PostgreSQL aislada, ejecutar antes supabase/verificacion/shim_supabase_local.sql):
--   roles anon, authenticated, service_role; esquema auth con auth.users(id)
--   y auth.uid(); PostgreSQL 17.
-- =====================================================================
begin;

do $$
begin
  if to_regclass('public.personal') is not null then
    raise exception 'DETENIDO: public.personal ya existe. Esta migración base solo es para una base vacía; no se aplicó nada.';
  end if;
end $$;

set local check_function_bodies = off;
set local search_path = public, extensions;

-- 1. Secuencia ---------------------------------------------------------
create sequence public.personal_empleado_id_seq as bigint start with 1 increment by 1 minvalue 1 maxvalue 9223372036854775807 cache 1 no cycle;

-- 2. Tablas (columnas, valores por defecto y NOT NULL) ----------------
create table public.areas (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activo boolean DEFAULT true NOT NULL
);
create table public.centros_costo (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activo boolean DEFAULT true NOT NULL
);
create table public.clasificaciones_personal (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  nombre text NOT NULL,
  activo boolean DEFAULT true NOT NULL,
  requiere_rfc boolean DEFAULT false NOT NULL,
  requiere_curp boolean DEFAULT false NOT NULL,
  requiere_nss boolean DEFAULT false NOT NULL,
  requiere_cp_fiscal boolean DEFAULT false NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);
create table public.combo_conceptos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  combo_id uuid,
  concepto_id uuid,
  tenant_id uuid NOT NULL
);
create table public.combos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL
);
create table public.conceptos_percepcion (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  suma_a_bruto boolean DEFAULT false NOT NULL,
  tenant_id uuid NOT NULL
);
create table public.departamentos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activo boolean DEFAULT true NOT NULL
);
create table public.empresas (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  registro_patronal text,
  created_at timestamp with time zone DEFAULT now(),
  tenant_id uuid NOT NULL,
  razon_social text,
  rfc text,
  codigo_postal text,
  estado text,
  municipio text,
  colonia text,
  calle text,
  numero_exterior text,
  numero_interior text,
  activo boolean DEFAULT true NOT NULL
);
create table public.empresas_registros_patronales (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  empresa_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  registro_patronal text NOT NULL,
  activo boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);
create table public.localidades (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activo boolean DEFAULT true NOT NULL
);
create table public.movimientos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  personal_id uuid,
  campo text NOT NULL,
  valor_anterior text,
  valor_nuevo text,
  usuario text,
  fecha timestamp with time zone DEFAULT now(),
  tenant_id uuid NOT NULL
);
create table public.periodicidades (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  dias_default numeric NOT NULL,
  tenant_id uuid NOT NULL
);
create table public.personal (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre_completo text NOT NULL,
  primer_apellido text,
  segundo_apellido text,
  curp text,
  rfc text,
  nss text,
  sexo text,
  fecha_nacimiento date,
  lugar_nacimiento text,
  nacionalidad text,
  foto_url text,
  empresa_id uuid,
  area text,
  puesto text,
  estatus text DEFAULT 'Activo'::text,
  fecha_antiguedad date,
  fecha_alta_imss date,
  fecha_baja date,
  comentario_baja text,
  tipo_contrato text,
  tipo_pago_1 text,
  tipo_pago_2 text,
  tipo_pago_3 text,
  noi text,
  banco text,
  cuenta text,
  clabe text,
  sueldo_bruto numeric,
  sd numeric,
  sdi_imss numeric,
  sueldo_neto_pactado numeric,
  calle_numero text,
  colonia text,
  poblacion text,
  codigo_postal text,
  entidad_federativa text,
  cp_fiscal text,
  telefono_casa text,
  telefono_celular text,
  correo_electronico text,
  nivel_estudios text,
  profesion text,
  estado_civil text,
  contacto_emergencia_nombre text,
  contacto_emergencia_telefono text,
  contacto_emergencia_parentesco text,
  licencia_manejo text,
  licencia_vigencia date,
  proyecto_id uuid,
  coordinador text,
  fecha_asignacion date DEFAULT CURRENT_DATE,
  created_at timestamp with time zone DEFAULT now(),
  tipo_empleado text,
  fecha_inicio_contrato date,
  fecha_vencimiento_contrato date,
  tipo_jornada text,
  turno text,
  dias_descanso text,
  no_fonacot text,
  contacto_emergencia_direccion text,
  restricciones_salud text,
  subcontratacion boolean DEFAULT false,
  salario_por_hora numeric,
  horas_por_dia numeric,
  periodicidad_id uuid,
  dias_periodo numeric,
  combo_id uuid,
  nombres text,
  empleado_id text,
  tenant_id uuid NOT NULL,
  area_id uuid,
  departamento_id uuid,
  puesto_id uuid,
  localidad_id uuid,
  centro_costo_id uuid,
  coordinador_id uuid,
  jefe_id uuid,
  coordinador_externo text,
  registro_patronal_id uuid,
  clasificacion_id uuid
);
create table public.personal_percepciones (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  personal_id uuid,
  concepto_id uuid,
  monto numeric DEFAULT 0,
  tenant_id uuid NOT NULL
);
create table public.personal_registros_pago (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  personal_id uuid NOT NULL,
  clasificacion_id uuid NOT NULL,
  periodicidad_id uuid NOT NULL,
  sueldo numeric(12,2) NOT NULL,
  modalidad_sueldo text NOT NULL,
  dias_periodo numeric(6,2),
  empresa_id uuid,
  registro_patronal_id uuid,
  fecha_inicio date DEFAULT CURRENT_DATE NOT NULL,
  fecha_fin date,
  activo boolean DEFAULT true NOT NULL,
  notas text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);
create table public.proyectos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  tenant_id uuid NOT NULL
);
create table public.puestos (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  activo boolean DEFAULT true NOT NULL
);
create table public.tenants (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  nombre text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);
create table public.usuarios_tenant (
  user_id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- 3. Funciones (texto literal de pg_get_functiondef) -------------------
CREATE OR REPLACE FUNCTION public.asignar_tenant_automatico()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
  v_tenant uuid;
begin
  v_tenant := public.current_tenant_id();
  if v_tenant is null then
    raise exception 'No se pudo determinar el tenant del usuario autenticado; el alta fue rechazada';
  end if;
  new.tenant_id := v_tenant;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.bloquear_borrado_registro_pago()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
  begin
    raise exception 'Los registros de pago no se eliminan. Ciérralos marcándolos como inactivos.';
  end; $function$;

CREATE OR REPLACE FUNCTION public.bloquear_cambio_persona_registro_pago()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
  begin
    if new.personal_id is distinct from old.personal_id then
      raise exception 'Un registro de pago no puede reasignarse a otra persona. Ciérralo y crea uno nuevo.';
    end if;
    return new;
  end; $function$;

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

CREATE OR REPLACE FUNCTION public.current_tenant_id()
 RETURNS uuid
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select tenant_id from public.usuarios_tenant where user_id = auth.uid();
$function$;

CREATE OR REPLACE FUNCTION public.es_cp_valido(v text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
  select v is not null and v ~ '^[0-9]{5}$' and v !~ '^00';
$function$;

CREATE OR REPLACE FUNCTION public.es_curp_valida(v text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
  select v is not null and char_length(v) = 18
    and v ~ '^[A-Z][AEIOUX][A-Z]{2}[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])[HM](AS|BC|BS|CC|CS|CH|CL|CM|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QO|QR|SP|SL|SR|TC|TL|TS|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9][0-9]$';
$function$;

CREATE OR REPLACE FUNCTION public.es_nss_valido(v text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
  select v is not null and v ~ '^[0-9]{11}$';
$function$;

CREATE OR REPLACE FUNCTION public.es_rfc_persona_valido(v text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
  select v is not null and char_length(v) = 13
    and v ~ '^[A-ZÑ&]{4}[0-9]{6}[A-Z0-9]{3}$'
    and public.fecha_aammdd_valida(substring(v from 7 for 2), substring(v from 9 for 2));
$function$;

CREATE OR REPLACE FUNCTION public.fecha_aammdd_valida(p_mm text, p_dd text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO ''
AS $function$
  select case
    when p_mm !~ '^[0-9]{2}$' or p_dd !~ '^[0-9]{2}$' then false
    when p_mm::int not between 1 and 12 then false
    else p_dd::int between 1 and (case p_mm::int
      when 2 then 29
      when 4 then 30 when 6 then 30 when 9 then 30 when 11 then 30
      else 31 end)
  end;
$function$;

-- generar_empleado_id(): el original contiene saltos de línea Windows (CRLF); se crea
-- con una cadena E'' para conservarlos byte a byte.
do $base$ begin
  execute E'CREATE OR REPLACE FUNCTION public.generar_empleado_id()\n RETURNS trigger\n LANGUAGE plpgsql\nAS $function$\r\nbegin\r\n  if new.empleado_id is null then\r\n    new.empleado_id := ''BEH-'' || lpad(nextval(''personal_empleado_id_seq'')::text, 6, ''0'');\r\n  end if;\r\n  return new;\r\nend;\r\n$function$';
end $base$;

CREATE OR REPLACE FUNCTION public.validar_curp_persona()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare v_debe_validar boolean;
begin
  if tg_op = 'INSERT' then v_debe_validar := true;
  else v_debe_validar := (new.curp is distinct from old.curp); end if;
  if v_debe_validar and new.curp is not null and new.curp <> '' and not public.es_curp_valida(new.curp) then
    raise exception 'La CURP "%" no tiene una estructura válida de 18 caracteres.', new.curp;
  end if;
  return new;
end; $function$;

CREATE OR REPLACE FUNCTION public.validar_formato_registro_patronal()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
  v_debe_validar boolean;
begin
  if tg_op = 'INSERT' then
    v_debe_validar := true;
  else
    v_debe_validar := (new.registro_patronal is distinct from old.registro_patronal);
  end if;

  if v_debe_validar and new.registro_patronal !~ '^[A-Z][0-9]{10}$' then
    raise exception 'El registro patronal "%" no tiene el formato de 11 caracteres (1 letra + 10 dígitos, formato IMSS).', new.registro_patronal;
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.validar_nss_cp_persona()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare v_nss boolean; v_cp boolean;
begin
  if tg_op = 'INSERT' then v_nss := true; v_cp := true;
  else
    v_nss := (new.nss is distinct from old.nss);
    v_cp := (new.cp_fiscal is distinct from old.cp_fiscal);
  end if;
  if v_nss and new.nss is not null and new.nss <> '' and not public.es_nss_valido(new.nss) then
    raise exception 'El NSS "%" debe tener exactamente 11 dígitos.', new.nss;
  end if;
  if v_cp and new.cp_fiscal is not null and new.cp_fiscal <> '' and not public.es_cp_valido(new.cp_fiscal) then
    raise exception 'El código postal fiscal "%" debe tener 5 dígitos (01000 a 99999).', new.cp_fiscal;
  end if;
  return new;
end; $function$;

CREATE OR REPLACE FUNCTION public.validar_requisitos_clasificacion()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
  c record;
  v_todo boolean;
  faltan text[] := '{}';
begin
  if new.clasificacion_id is null then return new; end if;
  select nombre, requiere_rfc, requiere_curp, requiere_nss, requiere_cp_fiscal into c
    from public.clasificaciones_personal
   where id = new.clasificacion_id and tenant_id = new.tenant_id;
  if not found then return new; end if; -- la FK compuesta se encarga de la integridad

  v_todo := (tg_op = 'INSERT') or (new.clasificacion_id is distinct from old.clasificacion_id);

  if c.requiere_rfc and (v_todo or new.rfc is distinct from old.rfc)
     and not public.es_rfc_persona_valido(nullif(new.rfc, '')) then faltan := faltan || 'RFC'::text; end if;
  if c.requiere_curp and (v_todo or new.curp is distinct from old.curp)
     and not public.es_curp_valida(nullif(new.curp, '')) then faltan := faltan || 'CURP'::text; end if;
  if c.requiere_nss and (v_todo or new.nss is distinct from old.nss)
     and not public.es_nss_valido(nullif(new.nss, '')) then faltan := faltan || 'NSS'::text; end if;
  if c.requiere_cp_fiscal and (v_todo or new.cp_fiscal is distinct from old.cp_fiscal)
     and not public.es_cp_valido(nullif(new.cp_fiscal, '')) then faltan := faltan || 'Código postal fiscal'::text; end if;

  if array_length(faltan, 1) > 0 then
    raise exception 'La clasificación "%" requiere estos campos completos y con formato válido: %.', c.nombre, array_to_string(faltan, ', ')
      using errcode = 'P0001', hint = 'requisitos_clasificacion';
  end if;
  return new;
end; $function$;

CREATE OR REPLACE FUNCTION public.validar_requisitos_expediente()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
  declare
    r record;
    faltan text[] := '{}';
  begin
    if tg_op <> 'UPDATE' then
      return new;
    end if;
    if  new.rfc       is not distinct from old.rfc
    and new.curp      is not distinct from old.curp
    and new.nss       is not distinct from old.nss
    and new.cp_fiscal is not distinct from old.cp_fiscal then
      return new;
    end if;

    select coalesce(bool_or(c.requiere_rfc), false)       as req_rfc,
           coalesce(bool_or(c.requiere_curp), false)      as req_curp,
           coalesce(bool_or(c.requiere_nss), false)       as req_nss,
           coalesce(bool_or(c.requiere_cp_fiscal), false) as req_cp,
           string_agg(distinct c.nombre, ', ')            as clasificaciones
      into r
      from public.personal_registros_pago rp
      join public.clasificaciones_personal c
        on c.id = rp.clasificacion_id and c.tenant_id = rp.tenant_id
     where rp.personal_id = new.id
       and rp.tenant_id  = new.tenant_id
       and rp.activo;

    if r.req_rfc  and new.rfc       is distinct from old.rfc       and not public.es_rfc_persona_valido(nullif(new.rfc, ''))  then faltan := faltan || 'RFC'::text; end if;
    if r.req_curp and new.curp      is distinct from old.curp      and not public.es_curp_valida(nullif(new.curp, ''))        then faltan := faltan || 'CURP'::text; end if;
    if r.req_nss  and new.nss       is distinct from old.nss       and not public.es_nss_valido(nullif(new.nss, ''))          then faltan := faltan || 'NSS'::text; end if;
    if r.req_cp   and new.cp_fiscal is distinct from old.cp_fiscal and not public.es_cp_valido(nullif(new.cp_fiscal, ''))     then faltan := faltan || 'Código postal fiscal'::text; end if;

    if array_length(faltan, 1) > 0 then
      raise exception 'No se puede dejar vacío o inválido: %. Lo exige(n) el/los registro(s) de pago activo(s): %.',
        array_to_string(faltan, ', '), r.clasificaciones
        using errcode = 'P0001', hint = 'requisitos_expediente';
    end if;
    return new;
  end; $function$;

CREATE OR REPLACE FUNCTION public.validar_requisitos_registro_pago()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
  declare
    v_revisar boolean;
    c record;
    p record;
    faltan text[] := '{}';
  begin
    if not new.activo then
      return new;
    end if;

    if tg_op = 'INSERT' then
      v_revisar := true;
    else
      v_revisar := (new.clasificacion_id is distinct from old.clasificacion_id)
                or (not old.activo);
    end if;
    if not v_revisar then
      return new;
    end if;

    select nombre, requiere_rfc, requiere_curp, requiere_nss, requiere_cp_fiscal
      into c
      from public.clasificaciones_personal
     where id = new.clasificacion_id and tenant_id = new.tenant_id;
    if not found then
      return new; -- la FK compuesta rechaza la clasificación inexistente o de otro tenant
    end if;
    if not (c.requiere_rfc or c.requiere_curp or c.requiere_nss or c.requiere_cp_fiscal) then
      return new;
    end if;

    -- Coordinación con cambios concurrentes al expediente: se actualiza la
    -- fila de la persona SIN cambiar ningún valor. Un simple bloqueo
    -- (FOR UPDATE / FOR NO KEY UPDATE) no basta: en REPEATABLE READ o
    -- SERIALIZABLE, una transacción concurrente que vacíe RFC/CURP/NSS/CP
    -- con su foto de datos anterior no detecta un bloqueo, pero sí una fila
    -- modificada (recibe 40001). En READ COMMITTED, la transacción que
    -- espera vuelve a evaluar la fila y su trigger ve este registro.
    -- Efectos: nueva versión física de la fila; posible evento UPDATE de
    -- Realtime (si está habilitado en personal). Ningún valor cambia.
    update public.personal
       set nombre_completo = nombre_completo
     where id = new.personal_id and tenant_id = new.tenant_id;

    select rfc, curp, nss, cp_fiscal
      into p
      from public.personal
     where id = new.personal_id and tenant_id = new.tenant_id;
    if not found then
      return new; -- la FK compuesta rechaza la persona inexistente o de otro tenant
    end if;

    if c.requiere_rfc       and not public.es_rfc_persona_valido(nullif(p.rfc, ''))  then faltan := faltan || 'RFC'::text; end if;
    if c.requiere_curp      and not public.es_curp_valida(nullif(p.curp, ''))        then faltan := faltan || 'CURP'::text; end if;
    if c.requiere_nss       and not public.es_nss_valido(nullif(p.nss, ''))          then faltan := faltan || 'NSS'::text; end if;
    if c.requiere_cp_fiscal and not public.es_cp_valido(nullif(p.cp_fiscal, ''))     then faltan := faltan || 'Código postal fiscal'::text; end if;

    if array_length(faltan, 1) > 0 then
      raise exception 'Para un registro de pago "%", el expediente debe tener completos y con formato válido: %.',
        c.nombre, array_to_string(faltan, ', ')
        using errcode = 'P0001', hint = 'requisitos_registro_pago';
    end if;
    return new;
  end; $function$;

CREATE OR REPLACE FUNCTION public.validar_rfc_empresa()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
  v_debe_validar boolean;
begin
  if tg_op = 'INSERT' then
    v_debe_validar := true;
  else
    v_debe_validar := (new.rfc is distinct from old.rfc);
  end if;

  if v_debe_validar and new.rfc is not null and new.rfc <> '' then
    if char_length(new.rfc) <> 12
       or new.rfc !~ '^[A-ZÑ&]{3}[0-9]{6}[A-Z0-9]{3}$'
       or not public.fecha_aammdd_valida(substring(new.rfc from 6 for 2), substring(new.rfc from 8 for 2))
    then
      raise exception 'El RFC "%" no tiene el formato válido de persona moral (12 caracteres: 3 letras, 6 dígitos de fecha AAMMDD y 3 de homoclave).', new.rfc;
    end if;
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.validar_rfc_persona()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare v_debe_validar boolean;
begin
  if tg_op = 'INSERT' then v_debe_validar := true;
  else v_debe_validar := (new.rfc is distinct from old.rfc); end if;
  if v_debe_validar and new.rfc is not null and new.rfc <> '' and not public.es_rfc_persona_valido(new.rfc) then
    raise exception 'El RFC "%" no tiene el formato válido de persona física (13 caracteres: 4 letras, 6 dígitos de fecha AAMMDD y 3 de homoclave).', new.rfc;
  end if;
  return new;
end; $function$;

-- 4. Restricciones: llaves primarias y únicas, luego CHECK, luego foráneas
ALTER TABLE ONLY public.areas ADD CONSTRAINT areas_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.centros_costo ADD CONSTRAINT centros_costo_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.clasificaciones_personal ADD CONSTRAINT clasificaciones_personal_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.combo_conceptos ADD CONSTRAINT combo_conceptos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.combos ADD CONSTRAINT combos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.conceptos_percepcion ADD CONSTRAINT conceptos_percepcion_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.departamentos ADD CONSTRAINT departamentos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.empresas ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.localidades ADD CONSTRAINT localidades_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.movimientos ADD CONSTRAINT movimientos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.periodicidades ADD CONSTRAINT periodicidades_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.personal_percepciones ADD CONSTRAINT personal_percepciones_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT personal_registros_pago_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.proyectos ADD CONSTRAINT proyectos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.puestos ADD CONSTRAINT puestos_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.tenants ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.usuarios_tenant ADD CONSTRAINT usuarios_tenant_pkey PRIMARY KEY (user_id);
ALTER TABLE ONLY public.areas ADD CONSTRAINT areas_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.centros_costo ADD CONSTRAINT centros_costo_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.clasificaciones_personal ADD CONSTRAINT clasificaciones_personal_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.combos ADD CONSTRAINT combos_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.conceptos_percepcion ADD CONSTRAINT conceptos_percepcion_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.departamentos ADD CONSTRAINT departamentos_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.empresas ADD CONSTRAINT empresas_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_empresa_id_id_tenant_id_key UNIQUE (empresa_id, id, tenant_id);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_empresa_id_registro_patronal_key UNIQUE (empresa_id, registro_patronal);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.localidades ADD CONSTRAINT localidades_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.periodicidades ADD CONSTRAINT periodicidades_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_empleado_id_key UNIQUE (empleado_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT personal_registros_pago_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.proyectos ADD CONSTRAINT proyectos_id_tenant_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.puestos ADD CONSTRAINT puestos_id_tenant_id_key UNIQUE (id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_coordinador_excluyente CHECK ((NOT ((coordinador_id IS NOT NULL) AND (coordinador_externo IS NOT NULL))));
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_dias_periodo_positivo CHECK (((dias_periodo IS NULL) OR (dias_periodo > (0)::numeric)));
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_fechas_coherentes CHECK (((fecha_fin IS NULL) OR (fecha_fin >= fecha_inicio)));
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_modalidad_valida CHECK ((modalidad_sueldo = ANY (ARRAY['bruto'::text, 'neto'::text])));
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_registro_patronal_con_empresa CHECK (((registro_patronal_id IS NULL) OR (empresa_id IS NOT NULL)));
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_sueldo_mayor_cero CHECK ((sueldo > (0)::numeric));
ALTER TABLE ONLY public.areas ADD CONSTRAINT areas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.centros_costo ADD CONSTRAINT centros_costo_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.clasificaciones_personal ADD CONSTRAINT clasificaciones_personal_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.combo_conceptos ADD CONSTRAINT combo_conceptos_combo_id_tenant_fkey FOREIGN KEY (combo_id, tenant_id) REFERENCES combos(id, tenant_id) ON DELETE CASCADE;
ALTER TABLE ONLY public.combo_conceptos ADD CONSTRAINT combo_conceptos_concepto_id_tenant_fkey FOREIGN KEY (concepto_id, tenant_id) REFERENCES conceptos_percepcion(id, tenant_id);
ALTER TABLE ONLY public.combo_conceptos ADD CONSTRAINT combo_conceptos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.combos ADD CONSTRAINT combos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.conceptos_percepcion ADD CONSTRAINT conceptos_percepcion_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.departamentos ADD CONSTRAINT departamentos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.empresas ADD CONSTRAINT empresas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_empresa_id_tenant_id_fkey FOREIGN KEY (empresa_id, tenant_id) REFERENCES empresas(id, tenant_id);
ALTER TABLE ONLY public.empresas_registros_patronales ADD CONSTRAINT empresas_registros_patronales_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.localidades ADD CONSTRAINT localidades_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.movimientos ADD CONSTRAINT movimientos_personal_id_tenant_fkey FOREIGN KEY (personal_id, tenant_id) REFERENCES personal(id, tenant_id);
ALTER TABLE ONLY public.movimientos ADD CONSTRAINT movimientos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.periodicidades ADD CONSTRAINT periodicidades_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_area_id_tenant_fkey FOREIGN KEY (area_id, tenant_id) REFERENCES areas(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_centro_costo_id_tenant_fkey FOREIGN KEY (centro_costo_id, tenant_id) REFERENCES centros_costo(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_clasificacion_id_tenant_fkey FOREIGN KEY (clasificacion_id, tenant_id) REFERENCES clasificaciones_personal(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_combo_id_tenant_fkey FOREIGN KEY (combo_id, tenant_id) REFERENCES combos(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_coordinador_id_tenant_fkey FOREIGN KEY (coordinador_id, tenant_id) REFERENCES personal(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_departamento_id_tenant_fkey FOREIGN KEY (departamento_id, tenant_id) REFERENCES departamentos(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_empresa_id_tenant_fkey FOREIGN KEY (empresa_id, tenant_id) REFERENCES empresas(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_jefe_id_tenant_fkey FOREIGN KEY (jefe_id, tenant_id) REFERENCES personal(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_localidad_id_tenant_fkey FOREIGN KEY (localidad_id, tenant_id) REFERENCES localidades(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_periodicidad_id_tenant_fkey FOREIGN KEY (periodicidad_id, tenant_id) REFERENCES periodicidades(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_proyecto_id_tenant_fkey FOREIGN KEY (proyecto_id, tenant_id) REFERENCES proyectos(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_puesto_id_tenant_fkey FOREIGN KEY (puesto_id, tenant_id) REFERENCES puestos(id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_registro_patronal_empresa_fkey FOREIGN KEY (empresa_id, registro_patronal_id, tenant_id) REFERENCES empresas_registros_patronales(empresa_id, id, tenant_id);
ALTER TABLE ONLY public.personal ADD CONSTRAINT personal_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.personal_percepciones ADD CONSTRAINT personal_percepciones_concepto_id_tenant_fkey FOREIGN KEY (concepto_id, tenant_id) REFERENCES conceptos_percepcion(id, tenant_id);
ALTER TABLE ONLY public.personal_percepciones ADD CONSTRAINT personal_percepciones_personal_id_tenant_fkey FOREIGN KEY (personal_id, tenant_id) REFERENCES personal(id, tenant_id) ON DELETE CASCADE;
ALTER TABLE ONLY public.personal_percepciones ADD CONSTRAINT personal_percepciones_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT personal_registros_pago_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_clasificacion_fkey FOREIGN KEY (clasificacion_id, tenant_id) REFERENCES clasificaciones_personal(id, tenant_id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_empresa_fkey FOREIGN KEY (empresa_id, tenant_id) REFERENCES empresas(id, tenant_id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_periodicidad_fkey FOREIGN KEY (periodicidad_id, tenant_id) REFERENCES periodicidades(id, tenant_id);
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_personal_fkey FOREIGN KEY (personal_id, tenant_id) REFERENCES personal(id, tenant_id) ON DELETE RESTRICT;
ALTER TABLE ONLY public.personal_registros_pago ADD CONSTRAINT prp_registro_patronal_fkey FOREIGN KEY (empresa_id, registro_patronal_id, tenant_id) REFERENCES empresas_registros_patronales(empresa_id, id, tenant_id);
ALTER TABLE ONLY public.proyectos ADD CONSTRAINT proyectos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.puestos ADD CONSTRAINT puestos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.usuarios_tenant ADD CONSTRAINT usuarios_tenant_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE ONLY public.usuarios_tenant ADD CONSTRAINT usuarios_tenant_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 5. Índices que no respaldan restricciones --------------------------
CREATE INDEX prp_clasificacion_idx ON public.personal_registros_pago USING btree (clasificacion_id);
CREATE INDEX prp_empresa_rp_idx ON public.personal_registros_pago USING btree (empresa_id, registro_patronal_id);
CREATE INDEX prp_periodicidad_idx ON public.personal_registros_pago USING btree (periodicidad_id);
CREATE INDEX prp_personal_activo_idx ON public.personal_registros_pago USING btree (tenant_id, personal_id) WHERE activo;
CREATE INDEX prp_personal_idx ON public.personal_registros_pago USING btree (personal_id);

-- 6. Vista ------------------------------------------------------------
CREATE VIEW public.v_personal_registros_pago WITH (security_invoker=true) AS  SELECT rp.id,
    rp.tenant_id,
    rp.personal_id,
    rp.clasificacion_id,
    rp.periodicidad_id,
    rp.sueldo,
    rp.modalidad_sueldo,
    rp.dias_periodo,
    rp.empresa_id,
    rp.registro_patronal_id,
    rp.fecha_inicio,
    rp.fecha_fin,
    rp.activo,
    rp.notas,
    rp.created_at,
    COALESCE(rp.dias_periodo, pe.dias_default) AS dias_periodo_efectivo,
    pe.nombre AS periodicidad_nombre,
    c.nombre AS clasificacion_nombre
   FROM ((personal_registros_pago rp
     JOIN periodicidades pe ON (((pe.id = rp.periodicidad_id) AND (pe.tenant_id = rp.tenant_id))))
     JOIN clasificaciones_personal c ON (((c.id = rp.clasificacion_id) AND (c.tenant_id = rp.tenant_id))));

-- 7. Triggers ---------------------------------------------------------
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.areas FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.centros_costo FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.clasificaciones_personal FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.combo_conceptos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.combos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.conceptos_percepcion FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.departamentos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.empresas FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.empresas_registros_patronales FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.localidades FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.movimientos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.periodicidades FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.personal FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.personal_percepciones FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.personal_registros_pago FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.proyectos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_asignar_tenant_automatico BEFORE INSERT ON public.puestos FOR EACH ROW EXECUTE FUNCTION asignar_tenant_automatico();
CREATE TRIGGER trg_bloquear_borrado BEFORE DELETE ON public.personal_registros_pago FOR EACH ROW EXECUTE FUNCTION bloquear_borrado_registro_pago();
CREATE TRIGGER trg_bloquear_cambio_persona BEFORE UPDATE ON public.personal_registros_pago FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_persona_registro_pago();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.areas FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.centros_costo FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.clasificaciones_personal FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.combo_conceptos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.combos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.conceptos_percepcion FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.departamentos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.empresas FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.empresas_registros_patronales FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.localidades FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.movimientos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.periodicidades FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.personal_percepciones FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.personal_registros_pago FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.proyectos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_cambio_tenant BEFORE UPDATE ON public.puestos FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_tenant();
CREATE TRIGGER trg_bloquear_truncate BEFORE TRUNCATE ON public.personal_registros_pago FOR EACH STATEMENT EXECUTE FUNCTION bloquear_borrado_registro_pago();
CREATE TRIGGER trg_generar_empleado_id BEFORE INSERT ON public.personal FOR EACH ROW EXECUTE FUNCTION generar_empleado_id();
CREATE TRIGGER trg_validar_curp_personal BEFORE INSERT OR UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION validar_curp_persona();
CREATE TRIGGER trg_validar_formato_registro_patronal BEFORE INSERT OR UPDATE ON public.empresas_registros_patronales FOR EACH ROW EXECUTE FUNCTION validar_formato_registro_patronal();
CREATE TRIGGER trg_validar_nss_cp_personal BEFORE INSERT OR UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION validar_nss_cp_persona();
CREATE TRIGGER trg_validar_requisitos_clasificacion BEFORE INSERT OR UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION validar_requisitos_clasificacion();
CREATE TRIGGER trg_validar_requisitos_expediente BEFORE UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION validar_requisitos_expediente();
CREATE TRIGGER trg_validar_requisitos_registro_pago BEFORE INSERT OR UPDATE ON public.personal_registros_pago FOR EACH ROW EXECUTE FUNCTION validar_requisitos_registro_pago();
CREATE TRIGGER trg_validar_rfc_empresa BEFORE INSERT OR UPDATE ON public.empresas FOR EACH ROW EXECUTE FUNCTION validar_rfc_empresa();
CREATE TRIGGER trg_validar_rfc_personal BEFORE INSERT OR UPDATE ON public.personal FOR EACH ROW EXECUTE FUNCTION validar_rfc_persona();

-- 8. Row Level Security -----------------------------------------------
alter table public.areas enable row level security;
alter table public.centros_costo enable row level security;
alter table public.clasificaciones_personal enable row level security;
alter table public.combo_conceptos enable row level security;
alter table public.combos enable row level security;
alter table public.conceptos_percepcion enable row level security;
alter table public.departamentos enable row level security;
alter table public.empresas enable row level security;
alter table public.empresas_registros_patronales enable row level security;
alter table public.localidades enable row level security;
alter table public.movimientos enable row level security;
alter table public.periodicidades enable row level security;
alter table public.personal enable row level security;
alter table public.personal_percepciones enable row level security;
alter table public.personal_registros_pago enable row level security;
alter table public.proyectos enable row level security;
alter table public.puestos enable row level security;
alter table public.tenants enable row level security;
alter table public.usuarios_tenant enable row level security;

-- 9. Políticas --------------------------------------------------------
CREATE POLICY tenant_acceso_areas ON public.areas AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_centros_costo ON public.centros_costo AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_clasificaciones_personal ON public.clasificaciones_personal AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_combo_conceptos ON public.combo_conceptos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_combos ON public.combos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_conceptos ON public.conceptos_percepcion AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_departamentos ON public.departamentos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_empresas ON public.empresas AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_empresas_registros_patronales ON public.empresas_registros_patronales AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_localidades ON public.localidades AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_movimientos ON public.movimientos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_periodicidades ON public.periodicidades AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_personal ON public.personal AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_personal_percepciones ON public.personal_percepciones AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_proyectos ON public.proyectos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_acceso_puestos ON public.puestos AS PERMISSIVE FOR ALL TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_insert_personal_registros_pago ON public.personal_registros_pago AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_select_personal_registros_pago ON public.personal_registros_pago AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_update_personal_registros_pago ON public.personal_registros_pago AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ver_propio_vinculo ON public.usuarios_tenant AS PERMISSIVE FOR SELECT TO public USING ((user_id = auth.uid()));
CREATE POLICY ver_tenant_propio ON public.tenants AS PERMISSIVE FOR SELECT TO public USING ((id IN ( SELECT usuarios_tenant.tenant_id
   FROM usuarios_tenant
  WHERE (usuarios_tenant.user_id = auth.uid()))));

-- 10. Comentarios -----------------------------------------------------
comment on table public.personal_registros_pago is '7D-6a: registros de pago de un expediente (N por persona). Sin borrado físico: se cierran con activo=false.';
comment on column public.personal_registros_pago.sueldo is 'Importe correspondiente a la periodicidad seleccionada (por periodo), en la modalidad indicada. Mayor que cero.';
comment on column public.personal_registros_pago.dias_periodo is 'Días del periodo. NULL = usar periodicidades.dias_default vigente (ver v_personal_registros_pago.dias_periodo_efectivo).';
comment on column public.personal_registros_pago.fecha_fin is 'Informativa. No cierra el registro automáticamente.';
comment on column public.personal_registros_pago.activo is 'Única fuente de verdad de vigencia y de exigencia de requisitos del expediente.';
comment on view public.v_personal_registros_pago is '7D-6a: lectura de registros de pago con dias_periodo_efectivo = coalesce(dias_periodo, periodicidades.dias_default). security_invoker: respeta RLS.';

-- 11. Permisos (resultado idéntico al de producción) -------------------
-- Las concesiones se hacen explícitas para que el resultado no dependa de
-- los privilegios por defecto del entorno. En Supabase ya existen por
-- defecto y estas sentencias no los alteran ni cambian su orden.
grant all on table public.areas to anon, authenticated, service_role;
grant all on table public.centros_costo to anon, authenticated, service_role;
grant all on table public.clasificaciones_personal to anon, authenticated, service_role;
grant all on table public.combo_conceptos to anon, authenticated, service_role;
grant all on table public.combos to anon, authenticated, service_role;
grant all on table public.conceptos_percepcion to anon, authenticated, service_role;
grant all on table public.departamentos to anon, authenticated, service_role;
grant all on table public.empresas to anon, authenticated, service_role;
grant all on table public.empresas_registros_patronales to anon, authenticated, service_role;
grant all on table public.localidades to anon, authenticated, service_role;
grant all on table public.movimientos to anon, authenticated, service_role;
grant all on table public.periodicidades to anon, authenticated, service_role;
grant all on table public.personal to anon, authenticated, service_role;
grant all on table public.personal_percepciones to anon, authenticated, service_role;
grant all on table public.proyectos to anon, authenticated, service_role;
grant all on table public.puestos to anon, authenticated, service_role;
grant all on table public.tenants to anon, authenticated, service_role;
grant all on table public.usuarios_tenant to anon, authenticated, service_role;
grant all on sequence public.personal_empleado_id_seq to anon, authenticated, service_role;
-- personal_registros_pago: igual que 7D-6a (sin anon; authenticated solo lee, inserta y actualiza)
revoke all on table public.personal_registros_pago from anon, authenticated;
grant all on table public.personal_registros_pago to service_role;
grant select, insert, update on table public.personal_registros_pago to authenticated;
-- v_personal_registros_pago: igual que 7D-6a (sin anon; authenticated solo lee)
revoke all on table public.v_personal_registros_pago from anon, authenticated;
grant all on table public.v_personal_registros_pago to service_role;
grant select on table public.v_personal_registros_pago to authenticated;
grant execute on function public.asignar_tenant_automatico() to anon, authenticated, service_role;
grant execute on function public.bloquear_borrado_registro_pago() to anon, authenticated, service_role;
grant execute on function public.bloquear_cambio_persona_registro_pago() to anon, authenticated, service_role;
grant execute on function public.bloquear_cambio_tenant() to anon, authenticated, service_role;
grant execute on function public.current_tenant_id() to anon, authenticated, service_role;
grant execute on function public.es_cp_valido(v text) to anon, authenticated, service_role;
grant execute on function public.es_curp_valida(v text) to anon, authenticated, service_role;
grant execute on function public.es_nss_valido(v text) to anon, authenticated, service_role;
grant execute on function public.es_rfc_persona_valido(v text) to anon, authenticated, service_role;
grant execute on function public.fecha_aammdd_valida(p_mm text, p_dd text) to anon, authenticated, service_role;
grant execute on function public.generar_empleado_id() to anon, authenticated, service_role;
grant execute on function public.validar_curp_persona() to anon, authenticated, service_role;
grant execute on function public.validar_formato_registro_patronal() to anon, authenticated, service_role;
grant execute on function public.validar_nss_cp_persona() to anon, authenticated, service_role;
grant execute on function public.validar_requisitos_clasificacion() to anon, authenticated, service_role;
grant execute on function public.validar_requisitos_expediente() to anon, authenticated, service_role;
grant execute on function public.validar_requisitos_registro_pago() to anon, authenticated, service_role;
grant execute on function public.validar_rfc_empresa() to anon, authenticated, service_role;
grant execute on function public.validar_rfc_persona() to anon, authenticated, service_role;

-- 12. Verificación: el esquema debe quedar idéntico al de producción ----
do $$
declare h text;
begin

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
    raise exception 'Verificación: el esquema creado no es idéntico al de producción V1 (huella %). No se aplicó nada.', h;
  end if;
  raise notice 'Base V1 creada: esquema idéntico a producción (03e98353d5e19d32ad52fd84b464f608).';
end $$;

commit;
