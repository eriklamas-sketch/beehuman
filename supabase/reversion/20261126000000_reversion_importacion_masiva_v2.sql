-- Reversión de 20261126000000_importacion_masiva_v2: restaura laboral_registrar_ingreso
-- con su cuerpo original y elimina las dos funciones nuevas. No toca datos.
begin;
drop function if exists public.imp_alta_personas(jsonb, text, boolean, text[]);
CREATE OR REPLACE FUNCTION public.laboral_registrar_ingreso(p_personal_id uuid, p_empresa_id uuid, p_registro_patronal_id uuid, p_fecha_ingreso date, p_fecha_reconocimiento_antiguedad date DEFAULT NULL::date, p_sbc numeric DEFAULT NULL::numeric, p_sdi numeric DEFAULT NULL::numeric, p_tipo_trabajador text DEFAULT NULL::text, p_tipo_salario text DEFAULT NULL::text, p_jornada text DEFAULT NULL::text, p_umf text DEFAULT NULL::text, p_numero_interno text DEFAULT NULL::text, p_motivo text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
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
end $function$

;
drop function if exists public.laboral__ingreso_nucleo(uuid, uuid, uuid, date, date, numeric, numeric, text, text, text, text, text, text, boolean, text);
commit;
