-- =====================================================================
-- Importación masiva v2 (26-nov-2026): persona + relación laboral + formas de pago
-- por fila, en una sola operación, con simulación sin persistencia.
--   1. laboral__ingreso_nucleo: el cuerpo de laboral_registrar_ingreso con dos
--      parámetros más (generar 08, origen). laboral_registrar_ingreso queda como
--      envoltura con la MISMA firma y el MISMO comportamiento (08 y origen pantalla).
--   2. imp_alta_personas: alta por fila en subtransacción; p_confirmar = false
--      ejecuta todo y lo deshace (simulación).
-- Solo funciones: no cambia tablas, datos, políticas ni permisos de tablas.
-- =====================================================================
begin;

create function public.laboral__ingreso_nucleo(p_personal_id uuid, p_empresa_id uuid, p_registro_patronal_id uuid, p_fecha_ingreso date, p_fecha_reconocimiento_antiguedad date, p_sbc numeric, p_sdi numeric, p_tipo_trabajador text, p_tipo_salario text, p_jornada text, p_umf text, p_numero_interno text, p_motivo text, p_generar_08 boolean, p_origen text)
returns uuid language plpgsql security definer set search_path to '' as $nucleo$

declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  v_rel uuid; v_ev uuid; v_tipo text; v_nss text;
begin
  if p_origen not in ('pantalla', 'importacion') then raise exception 'BeeHuman: origen no permitido.'; end if;
  if p_generar_08 is null then raise exception 'BeeHuman: indica si se genera el alta ante el IMSS.'; end if;
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
    p_origen, auth.uid()
  from public.relaciones_laborales r where r.id = v_rel
  returning id into v_ev;

  if p_registro_patronal_id is not null and p_generar_08 then
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
end 

$nucleo$;
revoke all on function public.laboral__ingreso_nucleo(uuid, uuid, uuid, date, date, numeric, numeric, text, text, text, text, text, text, boolean, text) from public, anon;
grant execute on function public.laboral__ingreso_nucleo(uuid, uuid, uuid, date, date, numeric, numeric, text, text, text, text, text, text, boolean, text) to authenticated, service_role;
comment on function public.laboral__ingreso_nucleo(uuid, uuid, uuid, date, date, numeric, numeric, text, text, text, text, text, text, boolean, text) is
  'BeeHuman: núcleo del ingreso/reingreso. La pantalla lo usa con 08 y origen pantalla; la importación masiva con origen importacion y 08 solo en «Altas nuevas».';

create or replace function public.laboral_registrar_ingreso(p_personal_id uuid, p_empresa_id uuid, p_registro_patronal_id uuid, p_fecha_ingreso date,
  p_fecha_reconocimiento_antiguedad date default null, p_sbc numeric default null, p_sdi numeric default null, p_tipo_trabajador text default null,
  p_tipo_salario text default null, p_jornada text default null, p_umf text default null, p_numero_interno text default null, p_motivo text default null)
returns uuid language plpgsql security definer set search_path to '' as $$
begin
  return public.laboral__ingreso_nucleo(p_personal_id, p_empresa_id, p_registro_patronal_id, p_fecha_ingreso,
    p_fecha_reconocimiento_antiguedad, p_sbc, p_sdi, p_tipo_trabajador, p_tipo_salario, p_jornada, p_umf, p_numero_interno, p_motivo,
    true, 'pantalla');
end $$;

-- ---------------------------------------------------------------------
-- imp_alta_personas
--   p_filas: arreglo (máx. 100) de objetos ya validados por la pantalla:
--     { id, linea, coordinador_ref, persona: {…columnas de personal…},
--       relacion: null | { empresa_id, registro_patronal_id, fecha_ingreso, fecha_antiguedad,
--                          sdi, tipo_trabajador, tipo_salario, jornada, umf, numero_interno },
--       esquemas: [ { clasificacion_id, periodicidad_id, modalidad, sueldo } ] }
--   p_tipo_carga: 'carga_inicial' (sin 08) | 'altas_nuevas' (08 pendiente si hay RP)
--   p_confirmar: false = simulación (todo se deshace al final)
--   p_curps_pendientes: CURP de filas válidas del archivo que van en otros bloques;
--     en simulación, un coordinador con esa CURP se da por resuelto.
-- SECURITY INVOKER: aplica la RLS, los disparadores y los permisos del usuario,
-- igual que el alta desde pantalla.
-- ---------------------------------------------------------------------
create function public.imp_alta_personas(p_filas jsonb, p_tipo_carga text default 'carga_inicial',
  p_confirmar boolean default false, p_curps_pendientes text[] default '{}')
returns jsonb language plpgsql security invoker set search_path to '' as $$
declare
  v_res jsonb := '[]'; v_n int; v_pend int[]; v_sig int[]; v_i int; f jsonb; p jsonb; r jsonb; e jsonb;
  v_ref text; v_coord uuid; v_cnt int; v_msg text; v_con text; v_id uuid; v_rel uuid; v_sbc numeric; v_uma numeric; v_rp uuid;
  v_req boolean; v_cls text; v_esq int; v_curps_err text[] := '{}'; v_avance boolean; v_dup text; v_08 boolean;
  v_refs jsonb; v_dups jsonb; v_emp_id text; v_k text;
begin
  if not public.tiene_rol('administrador', 'nomina') then raise exception 'BeeHuman: solo Administrador o Nómina pueden importar personal.'; end if;
  if p_tipo_carga is null or p_tipo_carga not in ('carga_inicial', 'altas_nuevas') then raise exception 'BeeHuman: tipo de carga no válido.'; end if;
  if p_confirmar is null then raise exception 'BeeHuman: indica si es simulación o carga.'; end if;
  if jsonb_typeof(p_filas) <> 'array' then raise exception 'BeeHuman: formato de filas no válido.'; end if;
  v_n := jsonb_array_length(p_filas);
  if v_n > 100 then raise exception 'BeeHuman: máximo 100 filas por envío.'; end if;
  v_08 := (p_tipo_carga = 'altas_nuevas');
  -- Identificadores de las personas visibles para el usuario (RLS): una sola lectura por envío.
  --   v_refs: ID BEH- y CURP → [{id, baja}] (coordinadores); v_dups: 'RFC:…', 'CURP:…', 'NSS:…' → «BEH-… NOMBRE».
  with base as (select x.id, upper(x.empleado_id) emp, upper(nullif(btrim(x.curp), '')) curp, upper(nullif(btrim(x.rfc), '')) rfc,
                       nullif(btrim(x.nss), '') nss, x.nombre_completo nom, (x.estatus = 'Baja' or x.fecha_baja is not null) baja
                  from public.personal x)
  select (select coalesce(jsonb_object_agg(k, v), '{}') from (select k, jsonb_agg(jsonb_build_object('id', id, 'baja', baja)) v
            from (select emp k, id, baja from base where emp is not null union all select curp, id, baja from base where curp is not null) a group by k) b),
         (select coalesce(jsonb_object_agg(k, v), '{}') from (select k, min(v) v from (
            select 'RFC:' || rfc k, coalesce(emp, 'sin ID') || ' ' || coalesce(nom, '') v from base where rfc is not null union all
            select 'CURP:' || curp, coalesce(emp, 'sin ID') || ' ' || coalesce(nom, '') from base where curp is not null union all
            select 'NSS:' || nss, coalesce(emp, 'sin ID') || ' ' || coalesce(nom, '') from base where nss is not null) a group by k) b)
    into v_refs, v_dups
    from (select 1) uno;

  begin  -- bloque que la simulación deshace completo
    v_pend := (select coalesce(array_agg(g), '{}') from generate_series(0, v_n - 1) g);
    loop
      v_sig := '{}'; v_avance := false;
      foreach v_i in array v_pend loop
        f := p_filas -> v_i; p := f -> 'persona'; r := f -> 'relacion';
        v_id := (f ->> 'id')::uuid; v_coord := null; v_msg := null;
        v_ref := upper(nullif(btrim(f ->> 'coordinador_ref'), ''));
        if v_ref is not null then
          -- ¿el coordinador es otra fila de este envío que todavía no se procesa?
          if not (v_refs ? v_ref) and exists (select 1 from unnest(v_pend) k where k <> v_i
                       and upper(p_filas -> k -> 'persona' ->> 'curp') = v_ref) then
            v_sig := v_sig || v_i; continue;
          end if;
          v_cnt := coalesce(jsonb_array_length(v_refs -> v_ref), 0);
          v_coord := case when v_cnt = 1 then (v_refs -> v_ref -> 0 ->> 'id')::uuid end;
          if v_cnt = 0 then
            v_coord := null;
            if v_ref = any(v_curps_err) then v_msg := format('El coordinador %s viene en el archivo, pero su fila tiene error; corrígela primero.', v_ref);
            elsif not p_confirmar and v_ref = any(select upper(u) from unnest(p_curps_pendientes) u) then v_msg := null;
            else v_msg := format('El coordinador %s no existe: usa el ID BEH- o la CURP de una persona registrada o de otra fila del archivo.', v_ref);
            end if;
          elsif v_cnt > 1 then v_msg := format('El coordinador %s es ambiguo: coincide con %s personas.', v_ref, v_cnt); v_coord := null;
          elsif (v_refs -> v_ref -> 0 ->> 'baja')::boolean then
            v_msg := format('El coordinador %s está dado de baja.', v_ref); v_coord := null;
          end if;
        end if;
        v_avance := true;
        if v_msg is not null then
          v_curps_err := v_curps_err || upper(coalesce(p ->> 'curp', ''));
          v_res := v_res || jsonb_build_object('linea', f -> 'linea', 'id', v_id, 'estado', 'error', 'mensaje', v_msg);
          continue;
        end if;

        begin  -- una fila = una subtransacción: todo o nada
          if exists (select 1 from public.personal x where x.id = v_id) then
            v_res := v_res || jsonb_build_object('linea', f -> 'linea', 'id', v_id, 'estado', 'ya_estaba',
              'empleado_id', (select x.empleado_id from public.personal x where x.id = v_id));
          else
            -- Posible persona existente (RFC, CURP y NSS no tienen índice único).
            select format('El %s %s ya está registrado: %s.', d.t, d.v, v_dups ->> (d.t || ':' || d.v)) into v_dup
              from (values (1, 'RFC', upper(nullif(btrim(p ->> 'rfc'), ''))), (2, 'CURP', upper(nullif(btrim(p ->> 'curp'), ''))), (3, 'NSS', nullif(btrim(p ->> 'nss'), ''))) d(o, t, v)
             where d.v is not null and v_dups ? (d.t || ':' || d.v)
             order by d.o limit 1;
            if v_dup is not null then raise exception 'BeeHuman: posible persona existente. %', v_dup; end if;

            insert into public.personal (id, empleado_id, nombres, primer_apellido, segundo_apellido, nombre_completo, rfc, curp, nss, cp_fiscal,
              empresa_id, proyecto_id, puesto_id, area_id, departamento_id, localidad_id, centro_costo_id, registro_patronal_id,
              coordinador_id, coordinador_externo, tipo_empleado, turno, fecha_inicio_contrato, fecha_vencimiento_contrato)
            values (v_id, case when p_confirmar then null else 'SIM-' || lpad(coalesce(f ->> 'linea', '0'), 6, '0') end,
              p ->> 'nombres', p ->> 'primer_apellido', nullif(p ->> 'segundo_apellido', ''), p ->> 'nombre_completo',
              nullif(p ->> 'rfc', ''), nullif(p ->> 'curp', ''), nullif(p ->> 'nss', ''), nullif(p ->> 'cp_fiscal', ''),
              (p ->> 'empresa_id')::uuid, (p ->> 'proyecto_id')::uuid, (p ->> 'puesto_id')::uuid, (p ->> 'area_id')::uuid,
              (p ->> 'departamento_id')::uuid, (p ->> 'localidad_id')::uuid, (p ->> 'centro_costo_id')::uuid,
              (coalesce(r ->> 'registro_patronal_id', p ->> 'registro_patronal_id'))::uuid,
              v_coord, nullif(p ->> 'coordinador_externo', ''), p ->> 'tipo_empleado', p ->> 'turno',
              (p ->> 'fecha_inicio_contrato')::date, (p ->> 'fecha_vencimiento_contrato')::date);

            v_rel := null; v_esq := 0;
            if r is not null and jsonb_typeof(r) = 'object' then
              v_rp := (r ->> 'registro_patronal_id')::uuid;
              if (r ->> 'empresa_id')::uuid is distinct from (p ->> 'empresa_id')::uuid then
                raise exception 'BeeHuman: la empresa de la relación laboral debe ser la de la persona.';
              end if;
              v_sbc := null;
              if v_rp is not null then
                if (r ->> 'sdi') is null then raise exception 'BeeHuman: falta el SDI: la relación lleva registro patronal.'; end if;
                v_uma := public.parametro_vigente('UMA_DIARIA', (r ->> 'fecha_ingreso')::date);
                v_sbc := case when v_uma is not null and (r ->> 'sdi')::numeric > round(v_uma * 25, 2) then round(v_uma * 25, 2) else (r ->> 'sdi')::numeric end;
              end if;
              v_rel := public.laboral__ingreso_nucleo(v_id, (r ->> 'empresa_id')::uuid, v_rp, (r ->> 'fecha_ingreso')::date,
                (r ->> 'fecha_antiguedad')::date, v_sbc, case when v_rp is null then null else (r ->> 'sdi')::numeric end,
                case when v_rp is null then null else r ->> 'tipo_trabajador' end, case when v_rp is null then null else r ->> 'tipo_salario' end,
                case when v_rp is null then null else r ->> 'jornada' end, case when v_rp is null then null else nullif(r ->> 'umf', '') end,
                nullif(r ->> 'numero_interno', ''),
                case when v_08 then 'Importación masiva: alta nueva' else 'Importación masiva: carga inicial (ya registrado ante el IMSS)' end,
                v_08, 'importacion');
              for e in select * from jsonb_array_elements(coalesce(f -> 'esquemas', '[]')) loop
                select c.nombre, c.requiere_nss into v_cls, v_req from public.clasificaciones_personal c where c.id = (e ->> 'clasificacion_id')::uuid;
                if v_cls is null then raise exception 'BeeHuman: la forma de pago no existe.'; end if;
                if v_req and v_rp is null then
                  raise exception 'BeeHuman: la forma de pago «%» es de nómina IMSS: la fila necesita registro patronal.', v_cls;
                end if;
                insert into public.personal_registros_pago (personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo,
                  empresa_id, registro_patronal_id, fecha_inicio, relacion_laboral_id)
                values (v_id, (e ->> 'clasificacion_id')::uuid, (e ->> 'periodicidad_id')::uuid, (e ->> 'sueldo')::numeric, e ->> 'modalidad',
                  (r ->> 'empresa_id')::uuid, case when v_req then v_rp else null end, (r ->> 'fecha_ingreso')::date, v_rel);
                v_esq := v_esq + 1;
              end loop;
            elsif jsonb_array_length(coalesce(f -> 'esquemas', '[]')) > 0 then
              raise exception 'BeeHuman: las formas de pago requieren la fecha de ingreso (relación laboral).';
            end if;

            select x.empleado_id into v_emp_id from public.personal x where x.id = v_id;
            v_k := upper(nullif(btrim(p ->> 'curp'), ''));
            if v_k is not null then
              v_refs := jsonb_set(v_refs, array[v_k], coalesce(v_refs -> v_k, '[]') || jsonb_build_array(jsonb_build_object('id', v_id, 'baja', false)));
              v_dups := v_dups || jsonb_build_object('CURP:' || v_k, v_emp_id || ' ' || coalesce(p ->> 'nombre_completo', ''));
            end if;
            if nullif(btrim(p ->> 'rfc'), '') is not null then v_dups := v_dups || jsonb_build_object('RFC:' || upper(btrim(p ->> 'rfc')), v_emp_id || ' ' || coalesce(p ->> 'nombre_completo', '')); end if;
            if nullif(btrim(p ->> 'nss'), '') is not null then v_dups := v_dups || jsonb_build_object('NSS:' || btrim(p ->> 'nss'), v_emp_id || ' ' || coalesce(p ->> 'nombre_completo', '')); end if;
            v_res := v_res || jsonb_build_object('linea', f -> 'linea', 'id', v_id,
              'estado', case when p_confirmar then 'creada' else 'se_crearia' end,
              'empleado_id', case when p_confirmar then v_emp_id end,
              'relacion', v_rel is not null, 'esquemas', v_esq,
              'movimiento_08', v_rel is not null and v_08 and v_rp is not null,
              'coordinador', v_coord is not null or (v_ref is not null and not p_confirmar));
          end if;
        exception when others then
          get stacked diagnostics v_msg = message_text, v_con = constraint_name;
          v_msg := regexp_replace(v_msg, '^BeeHuman: ', '');
          if v_con in ('relaciones_laborales_numero_interno_uq', 'personal_numero_interno_rp_uq') then
            v_msg := format('El número interno %s ya está en uso en ese registro patronal.', coalesce(r ->> 'numero_interno', ''));
          end if;
          v_curps_err := v_curps_err || upper(coalesce(p ->> 'curp', ''));
          v_res := v_res || jsonb_build_object('linea', f -> 'linea', 'id', v_id, 'estado', 'error', 'mensaje', v_msg);
        end;
      end loop;
      exit when cardinality(v_sig) = 0;
      if not v_avance then
        foreach v_i in array v_sig loop
          v_res := v_res || jsonb_build_object('linea', p_filas -> v_i -> 'linea', 'id', p_filas -> v_i ->> 'id', 'estado', 'error',
            'mensaje', 'Referencia circular de coordinadores: cada fila espera a la otra.');
        end loop;
        exit;
      end if;
      v_pend := v_sig;
    end loop;
    if not p_confirmar then raise exception using errcode = 'BHS01', message = 'simulación'; end if;
  exception when sqlstate 'BHS01' then
    null;  -- simulación: todo lo anterior se deshizo
  end;
  return (select jsonb_agg(x order by (x ->> 'linea')::int) from jsonb_array_elements(v_res) x);
end $$;
revoke all on function public.imp_alta_personas(jsonb, text, boolean, text[]) from public, anon;
grant execute on function public.imp_alta_personas(jsonb, text, boolean, text[]) to authenticated, service_role;
comment on function public.imp_alta_personas(jsonb, text, boolean, text[]) is
  'BeeHuman: importación masiva v2. Por fila: persona + relación laboral + hasta 2 formas de pago, todo o nada. p_confirmar = false es simulación.';

commit;
