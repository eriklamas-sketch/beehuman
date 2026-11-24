-- BeeHuman · B6 bandeja de envíos para Nómina · 24-nov-2026
-- Propuesta: claude/B6-bandeja-envios-propuesta-24nov.md. Autorización de Erik (24-nov 09:37): solo local.
--
-- Qué hace (solo añade; no modifica tablas, funciones ni datos existentes):
--  * inc_envio_seguimiento: una fila por evento de envío (tipo «envio» o «complemento») con la primera apertura
--    por Nómina y la atención (manual con quién, cuándo y nota; o automática con motivo y sin usuario).
--    Lo ya registrado no se edita ni se borra (disparador).
--  * Estados de cada envío (se calculan; solo apertura y atención se guardan):
--      atendido           atención registrada (manual o automática)
--      reemplazado        llegó una versión posterior de la misma hoja (el seguimiento de la anterior se cierra; su historial queda)
--      devuelto           la hoja se devolvió y espera reenvío
--      cerrado_procesado  hoja original o complemento ANTERIOR al procesamiento, en un periodo procesado
--                         (los complementos posteriores al procesamiento nunca se cierran así)
--      en_revision        alguien de Nómina la abrió y nadie la ha atendido
--      nuevo              nadie de Nómina la ha abierto
--    Indicador calculado aparte: lineas_por_decidir (en pantalla «Importes resueltos» cuando es 0).
--  * inc_bandeja_envios, inc_envios_pendientes, inc_envio_abrir, inc_envio_atender: solo Administrador y Nómina.
--    Abrir NUNCA atiende.
--  * Carga inicial: en periodos ya procesados, los envíos de hojas originales y de complementos enviados ANTES del
--    procesamiento quedan atendidos de forma automática con motivo «Periodo procesado antes de activar B6», sin usuario.
--    Los complementos posteriores al procesamiento quedan pendientes.
--  * La tabla nueva no entra en el concentrado ni en su huella: abrir o atender no invalida firmas ni reabre periodos.
-- Reversión: reversion/20261124000000_reversion_b6_bandeja_envios.sql (borra el seguimiento registrado).
begin;
do $$
begin
  if to_regclass('public.inc_envio_seguimiento') is not null then
    raise exception 'BeeHuman: B6 (bandeja de envíos) ya está aplicada.';
  end if;
  if to_regprocedure('public.inc_concentrado_huella(uuid)') is null then
    raise exception 'BeeHuman: requiere B3 + firma del periodo (opción B).';
  end if;
end $$;

create table public.inc_envio_seguimiento (
  evento_id           uuid primary key references public.inc_eventos(id),
  tenant_id           uuid not null references public.tenants(id),
  abierta_por         uuid,
  abierta_por_nombre  text,
  abierta_en          timestamptz,
  atendida_por        uuid,
  atendida_por_nombre text,
  atendida_en         timestamptz,
  atencion_tipo       text check (atencion_tipo in ('manual','automatica')),
  motivo_atencion     text,
  nota_atencion       text check (length(nota_atencion) <= 500),
  check ((abierta_en is null) = (abierta_por is null)),
  check ((atendida_en is null) = (atencion_tipo is null)),
  check (atencion_tipo is distinct from 'manual' or atendida_por is not null),
  check (atencion_tipo is distinct from 'automatica'
         or (atendida_por is null and atendida_por_nombre is null and length(trim(coalesce(motivo_atencion,''))) > 0))
);
comment on table public.inc_envio_seguimiento is 'B6: primera apertura y atención de cada envío por Nómina. No forma parte del concentrado ni de su huella.';
create index inc_eventos_envios on public.inc_eventos (tenant_id, creado_en desc) where tipo in ('envio','complemento');

-- Solo eventos de envío del mismo tenant.
create function public.inc_envio_seguimiento_validar() returns trigger
language plpgsql security definer set search_path to '' as $$
begin
  if not exists (select 1 from public.inc_eventos e where e.id = new.evento_id and e.tenant_id = new.tenant_id
                 and e.tipo in ('envio','complemento')) then
    raise exception 'BeeHuman: el seguimiento solo aplica a envíos de hojas.';
  end if;
  return new;
end $$;
-- La apertura y la atención ya registradas no se cambian; el seguimiento no se borra.
create function public.inc_envio_seguimiento_proteger() returns trigger
language plpgsql set search_path to '' as $$
begin
  if tg_op = 'DELETE' then raise exception 'BeeHuman: el seguimiento de envíos es histórico y no se borra.'; end if;
  if new.evento_id <> old.evento_id or new.tenant_id <> old.tenant_id
     or (old.abierta_en is not null and (new.abierta_en, new.abierta_por, new.abierta_por_nombre)
                                        is distinct from (old.abierta_en, old.abierta_por, old.abierta_por_nombre))
     or (old.atendida_en is not null and (new.atendida_en, new.atendida_por, new.atendida_por_nombre, new.atencion_tipo, new.motivo_atencion, new.nota_atencion)
                                         is distinct from (old.atendida_en, old.atendida_por, old.atendida_por_nombre, old.atencion_tipo, old.motivo_atencion, old.nota_atencion)) then
    raise exception 'BeeHuman: la apertura o la atención ya registradas no se modifican.';
  end if;
  return new;
end $$;
create trigger trg_inc_envio_seg_validar before insert on public.inc_envio_seguimiento for each row execute function public.inc_envio_seguimiento_validar();
create trigger trg_inc_envio_seg_proteger before update or delete on public.inc_envio_seguimiento for each row execute function public.inc_envio_seguimiento_proteger();

-- Todos los envíos del tenant con su estado (interna; las funciones públicas comprueban el rol).
create function public.inc__envios_base(p_empresa uuid)
returns table (evento_id uuid, tipo_evento text, empresa_id uuid, empresa text, periodo_id uuid, periodo_inicio date, periodo_fin date,
  periodo_procesado_en timestamptz, hoja_id uuid, hoja_tipo text, posterior_procesamiento boolean, hoja_estado text,
  version_id uuid, version_numero integer, version_actual integer, coordinador_id uuid, coordinador text,
  enviado_por text, enviado_en timestamptz, estado text,
  abierta_por text, abierta_en timestamptz, atendida_por text, atendida_en timestamptz, atencion_tipo text,
  motivo_atencion text, nota_atencion text, lineas_por_decidir integer, firma_rh_requerida boolean, firma_rh boolean)
language sql stable security definer set search_path to '' as $$
  select e.id, e.tipo, pe.empresa_id, em.nombre, pe.id, pe.inicio, pe.fin, pe.procesado_en,
         h.id, h.tipo, h.posterior_procesamiento, h.estado, v.id, v.numero, h.version_actual,
         h.coordinador_id, co.nombre_completo, e.nombre, e.creado_en,
         case when s.atendida_en is not null then 'atendido'
              when v.numero < h.version_actual then 'reemplazado'
              when h.estado = 'devuelta' then 'devuelto'
              when h.estado = 'procesada' and not h.posterior_procesamiento then 'cerrado_procesado'
              when s.abierta_en is not null then 'en_revision'
              else 'nuevo' end,
         s.abierta_por_nombre, s.abierta_en, s.atendida_por_nombre, s.atendida_en, s.atencion_tipo, s.motivo_atencion, s.nota_atencion,
         (select count(*)::integer from public.inc_importes i where i.version_id = v.id and i.origen in ('pendiente','sin_sueldo','por_asignar')),
         prm.responsable_rh_user is not null,
         exists (select 1 from public.inc_eventos f where f.version_id = v.id and f.tipo = 'firma_rh')
  from public.inc_eventos e
  join public.inc_hojas h on h.id = e.hoja_id
  join public.inc_versiones v on v.id = e.version_id
  join public.inc_periodos pe on pe.id = e.periodo_id
  join public.empresas em on em.id = pe.empresa_id
  left join public.personal co on co.id = h.coordinador_id
  left join public.inc_parametros prm on prm.empresa_id = pe.empresa_id
  left join public.inc_envio_seguimiento s on s.evento_id = e.id
  where e.tenant_id = public.current_tenant_id() and e.tipo in ('envio','complemento')
    and (p_empresa is null or pe.empresa_id = p_empresa)
$$;

-- Bandeja: todo lo pendiente (nuevo y en revisión) y lo cerrado de los últimos p_dias_atendidos días.
create function public.inc_bandeja_envios(p_empresa uuid default null, p_dias_atendidos integer default 30)
returns setof jsonb language plpgsql stable security definer set search_path to '' as $$
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  return query
    select to_jsonb(b) from public.inc__envios_base(p_empresa) b
    where b.estado in ('nuevo','en_revision')
       or coalesce(case when b.atencion_tipo = 'manual' then b.atendida_en end, b.enviado_en)
          >= now() - make_interval(days => greatest(coalesce(p_dias_atendidos, 30), 0))
    order by b.enviado_en desc
    limit 500;
end $$;

-- Aviso: cuántos envíos esperan a Nómina.
create function public.inc_envios_pendientes()
returns jsonb language plpgsql stable security definer set search_path to '' as $$
declare r jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select jsonb_build_object('nuevos', count(*) filter (where estado = 'nuevo'),
                            'en_revision', count(*) filter (where estado = 'en_revision'),
                            'total', count(*) filter (where estado in ('nuevo','en_revision')))
    into r from public.inc__envios_base(null);
  return r;
end $$;

-- Primera apertura por Nómina. Idempotente. NO atiende.
create function public.inc_envio_abrir(p_evento uuid)
returns text language plpgsql security definer set search_path to '' as $$
declare e record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into e from public.inc_eventos where id = p_evento and tenant_id = public.current_tenant_id() and tipo in ('envio','complemento');
  if e.id is null then raise exception 'BeeHuman: envío no encontrado.'; end if;
  insert into public.inc_envio_seguimiento as s (evento_id, tenant_id, abierta_por, abierta_por_nombre, abierta_en)
  values (e.id, e.tenant_id, auth.uid(), public.inc_nombre_usuario(), now())
  on conflict (evento_id) do update set abierta_por = excluded.abierta_por, abierta_por_nombre = excluded.abierta_por_nombre,
                                        abierta_en = excluded.abierta_en
    where s.abierta_en is null;
  return (select b.estado from public.inc__envios_base(null) b where b.evento_id = p_evento);
end $$;

-- Atención manual: quién, cuándo y nota opcional. Idempotente: si ya estaba atendido no cambia nada.
create function public.inc_envio_atender(p_evento uuid, p_nota text default null)
returns text language plpgsql security definer set search_path to '' as $$
declare e record; b record; n int; v_nota text := nullif(btrim(coalesce(p_nota,'')), '');
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into e from public.inc_eventos where id = p_evento and tenant_id = public.current_tenant_id() and tipo in ('envio','complemento');
  if e.id is null then raise exception 'BeeHuman: envío no encontrado.'; end if;
  if length(v_nota) > 500 then raise exception 'BeeHuman: la nota admite hasta 500 caracteres.'; end if;
  perform 1 from public.inc_hojas where id = e.hoja_id for update;   -- serializa con un reenvío o una devolución simultáneos
  select * into b from public.inc__envios_base(null) x where x.evento_id = p_evento;
  if b.estado = 'atendido' then
    return 'Ya estaba atendido' || coalesce(' por ' || b.atendida_por, '') || ' el ' || to_char(b.atendida_en at time zone 'America/Mexico_City', 'DD/MM/YYYY HH24:MI') || '; no se registró de nuevo.';
  end if;
  if b.estado not in ('nuevo','en_revision') then
    raise exception 'BeeHuman: este envío ya está cerrado (%); no requiere atención.',
      case b.estado when 'reemplazado' then 'llegó la versión ' || b.version_actual
                    when 'devuelto' then 'se devolvió y espera reenvío'
                    else 'el periodo ya se procesó' end;
  end if;
  insert into public.inc_envio_seguimiento as s (evento_id, tenant_id, atendida_por, atendida_por_nombre, atendida_en, atencion_tipo, nota_atencion)
  values (e.id, e.tenant_id, auth.uid(), public.inc_nombre_usuario(), now(), 'manual', v_nota)
  on conflict (evento_id) do update set atendida_por = excluded.atendida_por, atendida_por_nombre = excluded.atendida_por_nombre,
         atendida_en = excluded.atendida_en, atencion_tipo = 'manual', nota_atencion = excluded.nota_atencion
    where s.atendida_en is null;
  get diagnostics n = row_count;
  if n = 0 then return 'Ya estaba atendido; no se registró de nuevo.'; end if;
  return 'Envío marcado como atendido.';
end $$;

-- Carga inicial: originales y complementos anteriores al procesamiento de periodos ya procesados,
-- atendidos de forma automática y sin usuario. Los complementos posteriores quedan pendientes.
do $$
declare n int;
begin
  insert into public.inc_envio_seguimiento (evento_id, tenant_id, atendida_en, atencion_tipo, motivo_atencion)
  select e.id, e.tenant_id, now(), 'automatica', 'Periodo procesado antes de activar B6'
  from public.inc_eventos e
  join public.inc_hojas h on h.id = e.hoja_id
  join public.inc_periodos pe on pe.id = e.periodo_id
  where e.tipo in ('envio','complemento') and not h.posterior_procesamiento and pe.procesado_en is not null;
  get diagnostics n = row_count;
  raise notice 'B6: % envíos (originales y complementos anteriores al procesamiento) de periodos procesados quedan atendidos de forma automática.', n;
end $$;

-- Permisos: la tabla solo se toca desde las funciones; anon nada.
alter table public.inc_envio_seguimiento enable row level security;
revoke all on public.inc_envio_seguimiento from public, anon, authenticated;
revoke all on function public.inc_envio_seguimiento_validar(), public.inc_envio_seguimiento_proteger(),
  public.inc__envios_base(uuid) from public, anon, authenticated;
revoke all on function public.inc_bandeja_envios(uuid, integer), public.inc_envios_pendientes(),
  public.inc_envio_abrir(uuid), public.inc_envio_atender(uuid, text) from public, anon;
grant execute on function public.inc_bandeja_envios(uuid, integer), public.inc_envios_pendientes(),
  public.inc_envio_abrir(uuid), public.inc_envio_atender(uuid, text) to authenticated;
commit;
