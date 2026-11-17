-- BeeHuman · B5 · FONACOT convertido: avisar cuándo está completo y listo para activar · 17-nov-2026
--
-- Diagnóstico (revisión manual de Erik, 17-nov): un FONACOT convertido de
-- «No. FONACOT» nace «incompleto». Al editarlo, cred_guardar guarda los datos
-- pero nunca cambia el estado: por diseño de B5 la activación es una acción
-- explícita (cred_cambiar_estado incompleto → activo, con fecha efectiva,
-- motivo e historia «activacion»), porque desde ese momento el crédito
-- propone descuentos. La pantalla no lo explicaba: decía «Incompleto: sin
-- descuento hasta completarlo» aunque ya estuviera completo, y mostraba
-- «Activar» igual con datos completos o sin ellos.
--
-- Cambio: la ficha recibe, para cada crédito incompleto, qué le falta para
-- activarse (la MISMA validación que aplica cred_cambiar_estado, sin
-- duplicar reglas). null = datos completos. La activación sigue siendo
-- explícita y el estado no cambia solo. No modifica datos.
begin;
do $$
begin
  if to_regclass('respaldo.b5_fonacot_completo_20261117') is not null then
    raise exception 'BeeHuman: esta corrección ya está aplicada.';
  end if;
  if to_regclass('respaldo.b5_creditos_20261113') is null then
    raise exception 'BeeHuman: esta corrección requiere B5 (20261113000000).';
  end if;
end $$;

create table respaldo.b5_fonacot_completo_20261117 (objeto text primary key, original text not null);
insert into respaldo.b5_fonacot_completo_20261117
  select x, pg_get_functiondef(to_regprocedure(x)) from unnest(array['public.cred_creditos_persona(uuid)']) x;
revoke all on table respaldo.b5_fonacot_completo_20261117 from public;

-- Qué falta para activar un crédito: ejecuta cred_validar como si pasara a
-- «activo» y devuelve el mensaje (sin el prefijo BeeHuman). null = completo.
create function public.cred_falta_para_activar(c public.cred_creditos) returns text
language plpgsql stable security definer set search_path to '' as $$
declare v public.cred_creditos := c;
begin
  v.estado := 'activo';
  perform public.cred_validar(v);
  return null;
exception when others then
  return regexp_replace(sqlerrm, '^BeeHuman:\s*', '');
end $$;
revoke all on function public.cred_falta_para_activar(public.cred_creditos) from public, anon, authenticated;

create or replace function public.cred_creditos_persona(p_personal uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
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
      -- Solo para incompletos: qué falta para poder activarlo (null = datos completos).
      'falta_para_activar', case when c.estado = 'incompleto' then public.cred_falta_para_activar(c) end,
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
end $function$;

commit;
