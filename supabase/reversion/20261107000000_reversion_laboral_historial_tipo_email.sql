-- Reversión de 20261107000000_laboral_historial_tipo_email: devuelve
-- laboral_historial exactamente a la definición de la v3 (20261104000000).
-- No toca datos. Al revertir vuelve el error 42804 en Supabase.
begin;

create or replace function public.laboral_historial(p_personal_id uuid)
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

commit;
