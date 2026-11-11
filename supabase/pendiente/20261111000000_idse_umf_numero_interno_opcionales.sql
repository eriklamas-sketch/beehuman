-- =====================================================================
-- BeeHuman · IDSE: número interno y UMF opcionales · 11-nov-2026
--   1. idse_validar deja de exigir «Número interno (clave del trabajador)»
--      (08, 02, 07) y «UMF» (08). Los demás requisitos no cambian.
--   2. idse_linea_alta / _baja / _modificacion: si faltan, las posiciones
--      van en blanco, sin valores ficticios:
--        127-129 UMF (solo alta) → 3 espacios;
--        139-148 clave del trabajador → 10 espacios.
--      La línea sigue midiendo 168 posiciones; con los datos capturados el
--      renglón es idéntico al de antes.
-- Requiere 20261109000200_idse_validadores_guia.
-- Originales en respaldo.idse_opcionales_20261111.
-- Reversión: supabase/reversion/20261111000000_reversion_idse_umf_numero_interno_opcionales.sql
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.idse_opcionales_20261111') is not null then
    raise exception 'BeeHuman: la migración idse_umf_numero_interno_opcionales ya está aplicada.';
  end if;
  if to_regprocedure('public.es_nss_imss_valido(text)') is null then
    raise exception 'BeeHuman: falta la migración 20261109000200_idse_validadores_guia; aplícala primero.';
  end if;
  if pg_get_functiondef('public.idse_validar(uuid,text)'::regprocedure) !~ 'Número interno \(clave del trabajador\)'
     or pg_get_functiondef('public.idse_validar(uuid,text)'::regprocedure) !~ 'es_nss_imss_valido' then
    raise exception 'BeeHuman: idse_validar no es la versión esperada (20261109000200).';
  end if;
  if to_regprocedure('public.idse_linea_alta(uuid,text)') is null or to_regprocedure('public.idse_linea_baja(uuid,text)') is null
     or to_regprocedure('public.idse_linea_modificacion(uuid,text)') is null then
    raise exception 'BeeHuman: faltan las funciones de línea IDSE (migraciones 20261104–20261105).';
  end if;
end $$;

create schema if not exists respaldo;
revoke all on schema respaldo from public;
create table respaldo.idse_opcionales_20261111 (objeto text primary key, original text not null, md5_aplicada text);
insert into respaldo.idse_opcionales_20261111 (objeto, original)
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array['public.idse_validar(uuid,text)',
    'public.idse_linea_alta(uuid,text)', 'public.idse_linea_baja(uuid,text)', 'public.idse_linea_modificacion(uuid,text)']) x;

-- 1. Validación de la bandeja (igual a 20261109000200 sin los dos requisitos) --
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
      -- alta y modificación llevan CURP, SBC y tipos; la baja lleva la causa.
      -- Número interno (clave del trabajador) y UMF son opcionales: vacíos van en blanco.
      case when p_tipo in ('08','07') and not public.es_curp_valida(nullif(p.curp, '')) then 'CURP válida' end,
      case when p_tipo in ('08','07') and m.sbc is null then 'SBC' end,
      case when p_tipo in ('08','07') and rl.tipo_trabajador is null then 'Tipo de trabajador' end,
      case when p_tipo in ('08','07') and rl.tipo_salario is null then 'Tipo de salario' end,
      case when p_tipo in ('08','07') and rl.jornada is null then 'Jornada' end,
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

-- 2. Líneas: posiciones opcionales en blanco ------------------------------
create or replace function public.idse_linea_alta(p_movimiento_id uuid, p_guia text)
returns text
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
      || rpad(coalesce(rl.umf, ''), 3, ' ')                          -- 127-129: UMF o en blanco
      || repeat(' ', 2)
      || '08' || p_guia
      || lpad(upper(btrim(coalesce(rl.numero_interno, ''))), 10, ' ') -- 139-148: clave o en blanco
      || ' '
      || p.curp
      || '9'
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.empresas_registros_patronales rp on rp.id = m.registro_patronal_id
  join public.personal p on p.id = rl.personal_id
  where m.id = p_movimiento_id;
$$;

create or replace function public.idse_linea_baja(p_movimiento_id uuid, p_guia text)
returns text
language sql stable security definer set search_path to '' as $$
  select rpad(upper(rp.registro_patronal), 11, ' ')
      || p.nss
      || public.idse_texto(p.primer_apellido, 27)
      || public.idse_texto(p.segundo_apellido, 27)
      || public.idse_texto(p.nombres, 27)
      || repeat('0', 15)                       -- 104-118: sin SBC ni tipos en la baja
      || to_char(m.fecha_movimiento, 'DDMMYYYY')
      || repeat(' ', 5)                        -- 127-131: sin UMF
      || '02' || p_guia
      || lpad(upper(btrim(coalesce(rl.numero_interno, ''))), 10, ' ') -- 139-148: clave o en blanco
      || m.causa_baja                          -- 149: causa de baja del IMSS
      || repeat(' ', 18)                       -- 150-167: sin CURP
      || '9'
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.empresas_registros_patronales rp on rp.id = m.registro_patronal_id
  join public.personal p on p.id = rl.personal_id
  where m.id = p_movimiento_id and m.tipo_movimiento = '02';
$$;

create or replace function public.idse_linea_modificacion(p_movimiento_id uuid, p_guia text)
returns text
language sql stable security definer set search_path to '' as $$
  select rpad(upper(rp.registro_patronal), 11, ' ')
      || p.nss
      || public.idse_texto(p.primer_apellido, 27)
      || public.idse_texto(p.segundo_apellido, 27)
      || public.idse_texto(p.nombres, 27)
      || lpad((round(m.sbc * 100))::bigint::text, 6, '0')   -- 104-109: SBC nuevo
      || repeat(' ', 6)
      || rl.tipo_trabajador || rl.tipo_salario || rl.jornada
      || to_char(m.fecha_movimiento, 'DDMMYYYY')
      || repeat(' ', 5)                                     -- 127-131: sin UMF
      || '07' || p_guia
      || lpad(upper(btrim(coalesce(rl.numero_interno, ''))), 10, ' ') -- 139-148: clave o en blanco
      || ' '
      || p.curp
      || '9'
  from public.idse_movimientos m
  join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
  join public.empresas_registros_patronales rp on rp.id = m.registro_patronal_id
  join public.personal p on p.id = rl.personal_id
  where m.id = p_movimiento_id and m.tipo_movimiento = '07';
$$;

update respaldo.idse_opcionales_20261111 set md5_aplicada = md5(pg_get_functiondef(to_regprocedure(objeto)));

commit;
