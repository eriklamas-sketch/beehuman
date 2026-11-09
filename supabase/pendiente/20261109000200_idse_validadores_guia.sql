-- =====================================================================
-- BeeHuman · IDSE: validadores de NSS y nombres, y guía 00000 · 9-nov-2026
--   1. public.es_nss_imss_valido(text): 11 dígitos y dígito verificador
--      (algoritmo de Luhn sobre los 10 primeros; comprobado con los 5 NSS de
--      los archivos reales de NOI: alta aceptada, bajas y modificaciones).
--   2. idse_validar: dos ERRORES nuevos que impiden generar el archivo
--      (NSS con dígito verificador inválido; nombre o apellidos con dígitos)
--      y deja de exigir la guía.
--   3. idse_generar_archivo: sin guía configurada usa 00000 (lo que llevan
--      los archivos reales). El Administrador puede capturar otra.
-- No cambia es_nss_valido (la usan las validaciones del expediente).
-- Requiere 20261109000000_fechas_hora_mexico (idse_validar usa hoy_mx()).
-- Originales de cada entorno en respaldo.idse_validadores_guia_20261109.
-- Reversión: supabase/reversion/20261109000200_reversion_idse_validadores_guia.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.idse_validadores_guia_20261109') is not null then
    raise exception 'BeeHuman: la migración idse_validadores_guia ya está aplicada.';
  end if;
  if to_regprocedure('public.hoy_mx()') is null then
    raise exception 'BeeHuman: falta la migración 20261109000000_fechas_hora_mexico; aplícala primero.';
  end if;
  if to_regprocedure('public.idse_validar(uuid,text)') is null or to_regprocedure('public.idse_generar_archivo(uuid,text,uuid[])') is null then
    raise exception 'BeeHuman: faltan las funciones IDSE (migraciones 20261104–20261105).';
  end if;
  if pg_get_functiondef('public.idse_validar(uuid,text)'::regprocedure) !~ 'no tiene número de guía IDSE'
     or pg_get_functiondef('public.idse_validar(uuid,text)'::regprocedure) !~ 'public\.hoy_mx\(\)' then
    raise exception 'BeeHuman: idse_validar no es la versión esperada (20261105000100 + fechas_hora_mexico).';
  end if;
  if pg_get_functiondef('public.idse_generar_archivo(uuid,text,uuid[])'::regprocedure) !~ 'v_rp\.guia_idse' then
    raise exception 'BeeHuman: idse_generar_archivo no es la versión esperada (20261105000100).';
  end if;
end $$;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
create table respaldo.idse_validadores_guia_20261109 (objeto text primary key, original text not null, md5_aplicada text);
insert into respaldo.idse_validadores_guia_20261109 (objeto, original)
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array['public.idse_validar(uuid,text)', 'public.idse_generar_archivo(uuid,text,uuid[])']) x;

-- 1. NSS con dígito verificador ---------------------------------------
create function public.es_nss_imss_valido(v text) returns boolean
language sql immutable set search_path to '' as $$
  select v is not null and v ~ '^[0-9]{11}$'
     and (10 - (select sum(((substr(v, i, 1)::int * (2 - i % 2)) / 10) + ((substr(v, i, 1)::int * (2 - i % 2)) % 10))
                  from generate_series(1, 10) as g(i)) % 10) % 10 = substr(v, 11, 1)::int
$$;
comment on function public.es_nss_imss_valido(text) is 'BeeHuman: NSS de 11 dígitos con dígito verificador correcto (posiciones pares ×2, Luhn).';

-- 2. Validación de la bandeja -------------------------------------------
create or replace function public.idse_validar(p_registro_patronal_id uuid, p_tipo text default '08')
returns table (movimiento_id uuid, personal_id uuid, nombre text, fecha_movimiento date, errores text[], avisos text[])
language plpgsql stable security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
begin
  if p_tipo not in ('08','02','07') then
    raise exception 'BeeHuman: tipo de movimiento IDSE no válido (%).', p_tipo;
  end if;
  perform 1 from public.empresas_registros_patronales where id = p_registro_patronal_id and tenant_id = v_tenant;
  if not found then raise exception 'BeeHuman: registro patronal no encontrado.'; end if;
  return query
  select m.id, p.id, p.nombre_completo, m.fecha_movimiento,
    array_remove(array[
      -- la guía ya no es obligatoria: sin guía configurada el archivo lleva 00000
      case when not public.es_nss_valido(nullif(p.nss, '')) then 'NSS de 11 dígitos'
           when not public.es_nss_imss_valido(p.nss) then 'NSS inválido: el dígito verificador no corresponde; revisa los 11 dígitos' end,
      case when coalesce(btrim(p.primer_apellido), '') = '' then 'Primer apellido' end,
      case when coalesce(btrim(p.nombres), '') = '' then 'Nombre(s) separado del apellido' end,
      case when concat(p.primer_apellido, p.segundo_apellido, p.nombres) ~ '[0-9]' then 'Nombre con dígitos: el IMSS no acepta números en el nombre ni en los apellidos' end,
      case when rl.numero_interno is null then 'Número interno (clave del trabajador)' end,
      -- alta y modificación llevan CURP, SBC y tipos; la UMF solo el alta; la baja lleva la causa
      case when p_tipo in ('08','07') and not public.es_curp_valida(nullif(p.curp, '')) then 'CURP válida' end,
      case when p_tipo in ('08','07') and m.sbc is null then 'SBC' end,
      case when p_tipo in ('08','07') and rl.tipo_trabajador is null then 'Tipo de trabajador' end,
      case when p_tipo in ('08','07') and rl.tipo_salario is null then 'Tipo de salario' end,
      case when p_tipo in ('08','07') and rl.jornada is null then 'Jornada' end,
      case when p_tipo = '08' and rl.umf is null then 'UMF' end,
      case when p_tipo = '02' and m.causa_baja is null then 'Causa de baja' end
    ], null),
    array_remove(array[
      case when concat(p.primer_apellido, p.segundo_apellido, p.nombres) ~ '[Ññ]' then 'Contiene Ñ: se escribe como # (regla provisional)' end,
      case when m.fecha_movimiento < public.hoy_mx() - 5 then 'Fecha con más de 5 días: revisa el plazo de presentación' end,
      case when m.estado = 'rechazado' then 'Reenvío de un movimiento rechazado: ' || coalesce(m.motivo_rechazo, '') end
    ], null)
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.personal p on p.id = rl.personal_id
  where m.tenant_id = v_tenant and m.registro_patronal_id = p_registro_patronal_id and m.tipo_movimiento = p_tipo
    and m.estado in ('pendiente','rechazado') and public.en_alcance_persona(p.id)
  order by m.fecha_movimiento, p.primer_apellido, p.segundo_apellido, p.nombres;
end $$;

-- 3. Generación: guía 00000 si no hay guía configurada --------------------
create or replace function public.idse_generar_archivo(p_registro_patronal_id uuid, p_tipo text default '08', p_movimientos uuid[] default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  v_rp record; v_ids uuid[]; v_lineas text[]; v_err text; v_contenido text; v_arch uuid; i int; v_linea text; v_guia text;
begin
  select * into v_rp from public.empresas_registros_patronales where id = p_registro_patronal_id and tenant_id = v_tenant;
  if not found then raise exception 'BeeHuman: registro patronal no encontrado.'; end if;
  -- Sin guía configurada: 00000, como los archivos reales aceptados. Se confirma con la subdelegación.
  v_guia := coalesce(nullif(btrim(v_rp.guia_idse), ''), '00000');
  if v_guia !~ '^[0-9]{5}$' then raise exception 'BeeHuman: la guía IDSE del registro patronal debe tener 5 dígitos.'; end if;
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
    v_linea := case p_tipo when '08' then public.idse_linea_alta(v_ids[i], v_guia)
                           when '02' then public.idse_linea_baja(v_ids[i], v_guia)
                           when '07' then public.idse_linea_modificacion(v_ids[i], v_guia) end;
    if v_linea is null or char_length(v_linea) <> 168 then
      raise exception 'BeeHuman: la línea del movimiento % no mide 168 posiciones (%).', v_ids[i], coalesce(char_length(v_linea), 0);
    end if;
    v_lineas := v_lineas || v_linea;
  end loop;
  -- renglón final: 13 asteriscos, número de movimientos (pos. 57-62), guía (134-138), '9'
  v_contenido := array_to_string(v_lineas, E'\r\n') || E'\r\n'
    || rpad('*************', 56, ' ') || lpad(cardinality(v_ids)::text, 6, '0') || repeat(' ', 71) || v_guia
    || repeat(' ', 29) || '9' || E'\r\n';

  perform set_config('beehuman.laboral', 'on', true);
  insert into public.idse_archivos (tenant_id, empresa_id, registro_patronal_id, tipo_movimiento, guia, nombre_archivo,
    num_registros, contenido, hash_sha256, generado_por)
  values (v_tenant, v_rp.empresa_id, v_rp.id, p_tipo, v_guia,
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

update respaldo.idse_validadores_guia_20261109 set md5_aplicada = md5(pg_get_functiondef(to_regprocedure(objeto)));

commit;
