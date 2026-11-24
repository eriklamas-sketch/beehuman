-- BeeHuman · Reversión de 20261123000000_b3_concentrado_firma_periodo (opción B).
-- Restaura inc_faltantes_procesar, inc_marcar_procesado e inc_firmar_hoja tal como estaban antes (B5 + «Mis hojas»),
-- elimina las funciones nuevas y la columna inc_eventos.huella. Los eventos de firma del periodo ya registrados se
-- conservan (inmutables) pero pierden su huella y dejan de contar.
begin;
do $$
begin
  if to_regprocedure('public.inc_concentrado_huella(uuid)') is null then
    raise exception 'BeeHuman: B3 + firma del periodo (opción B) no está aplicada.';
  end if;
end $$;
CREATE OR REPLACE FUNCTION public.inc_faltantes_procesar(p_periodo uuid)
 RETURNS TABLE(tipo text, detalle text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
#variable_conflict use_column
declare pe record; prm record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  select * into prm from public.inc_parametros x where x.empresa_id = pe.empresa_id;
  return query
  select f.tipo, f.detalle from (
    select 1 as orden, 'hoja'::text as tipo, t.coordinador || ': ' || case t.estado
             when 'sin_abrir' then 'no ha abierto su hoja' when 'borrador' then 'no ha enviado su hoja'
             else 'su hoja está devuelta y no la ha reenviado' end as detalle
      from public.inc_tablero_periodo(p_periodo) t where t.estado in ('sin_abrir','borrador','devuelta')
       -- Corrección D2 (16-nov): no bloquea una hoja normal en borrador, nunca
       -- enviada, cuyo coordinador no tiene personal en el periodo y que no tiene
       -- ninguna captura ni observación.
       and not (t.estado = 'borrador' and coalesce(t.version_actual, 0) = 0 and t.hoja_id is not null
                and public.inc_hoja_vacia_sin_personal(t.hoja_id))
    union all
    select 1, 'hoja', co.nombre_completo || ': tiene un complemento ' || case h.estado when 'borrador' then 'sin enviar' else 'devuelto sin reenviar' end
      from public.inc_hojas h join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.tipo = 'complemento' and h.estado in ('borrador','devuelta')
    union all
    select 2, 'importe', p.nombre_completo || ' · ' || k.nombre || ': ' ||
             case i.origen when 'sin_sueldo' then 'sin sueldo (captura el sueldo diario manual o escribe el importe)'
                           when 'por_asignar' then 'esquema de pago por asignar'
                           else 'importe por decidir' end
             || ' — hoja de ' || co.nombre_completo
      from public.inc_importes i
      join public.inc_versiones v on v.id = i.version_id
      join public.inc_hojas h on h.id = v.hoja_id and v.numero = h.version_actual
      join public.personal p on p.id = i.personal_id
      join public.inc_conceptos k on k.id = i.concepto_id
      join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.estado = 'enviada' and i.origen in ('pendiente','sin_sueldo','por_asignar')
    union all
    -- B5: descuentos de créditos por decidir, que exceden el saldo o sin generar
    select 2, 'descuento', p.nombre_completo || ' · ' || public.cred_etiqueta(c) || ': ' ||
             case when d.origen = 'pendiente' then 'descuento por decidir'
                  else 'el descuento ($' || to_char(d.final, 'FM999,999,990.00') || ') excede el saldo disponible del crédito ($'
                       || to_char(greatest(public.cred_disponible(c.id, pe.id), 0), 'FM999,999,990.00') || ')' end
      from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id join public.personal p on p.id = d.personal_id
     where d.periodo_id = pe.id and (d.origen = 'pendiente'
            or (d.origen in ('aceptado','modificado') and c.monto_total is not null and d.final > public.cred_disponible(c.id, pe.id)))
    union all
    select 2, 'descuento', p.nombre_completo || ' · ' || public.cred_etiqueta(c) || ': descuento del periodo sin revisar (abre «Descuentos del periodo»)'
      from public.cred_propuestas(pe.id) x join public.cred_creditos c on c.id = x.credito_id join public.personal p on p.id = x.personal_id
     where pe.procesado_en is null
       and not exists (select 1 from public.cred_descuentos d where d.periodo_id = pe.id and d.credito_id = x.credito_id and d.origen <> 'descartado')
    union all
    select 3, 'firma', 'Designa al responsable de Nómina (Incidencias → Configuración): su firma es obligatoria para procesar'
     where prm.responsable_nomina_user is null
       and exists (select 1 from public.inc_hojas h where h.periodo_id = pe.id and h.estado = 'enviada')
    union all
    select 3, 'firma', co.nombre_completo || ': falta la firma de ' || a.nombre || ' (versión ' || h.version_actual || ')'
      from public.inc_hojas h
      join public.inc_versiones v on v.hoja_id = h.id and v.numero = h.version_actual
      join public.personal co on co.id = h.coordinador_id
      cross join (values ('nomina', 'Nómina', prm.responsable_nomina_user), ('rh', 'RH', prm.responsable_rh_user)) a(area, nombre, resp)
     where h.periodo_id = pe.id and h.estado = 'enviada' and a.resp is not null
       and not exists (select 1 from public.inc_eventos e where e.version_id = v.id and e.tipo = 'firma_' || a.area)
  ) f
  order by f.orden, f.detalle;
end $function$;
CREATE OR REPLACE FUNCTION public.inc_marcar_procesado(p_periodo uuid)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare pe record; v_falta text; v_n integer; r record; v_saldo numeric;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos where id = p_periodo and tenant_id = public.current_tenant_id() for update;
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  if pe.procesado_en is not null then
    return 'Ya estaba procesado el ' || to_char(pe.procesado_en, 'YYYY-MM-DD HH24:MI') || '; no se registró de nuevo.';
  end if;
  -- B5: bloquear los créditos involucrados (procesados concurrentes de otros
  -- periodos esperan) y recalcular las propuestas con el saldo real.
  perform 1 from public.cred_creditos c
   where c.id in (select x.credito_id from public.cred_propuestas(p_periodo) x
                  union select d.credito_id from public.cred_descuentos d where d.periodo_id = p_periodo)
   order by c.id for update;
  perform public.cred_sincronizar_periodo(p_periodo);
  select count(*), string_agg(f.detalle, '; ') into v_n, v_falta from public.inc_faltantes_procesar(p_periodo) f;
  if v_n > 0 then
    raise exception 'BeeHuman: no se puede procesar; faltan % pendiente(s): %', v_n, left(v_falta, 1500);
  end if;
  update public.inc_periodos set procesado_en = now(), procesado_por = auth.uid() where id = p_periodo;
  update public.inc_hojas set estado = 'procesada' where periodo_id = p_periodo and estado = 'enviada';
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre)
  values (pe.tenant_id, p_periodo, 'procesado', auth.uid(), public.inc_nombre_usuario());
  -- B5: el saldo baja aquí y solo aquí, una vez por crédito y periodo.
  for r in select d.id, d.credito_id, d.final from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id
            where d.periodo_id = p_periodo and d.origen in ('aceptado','modificado') and c.monto_total is not null and d.final > 0
            order by d.credito_id loop
    v_saldo := public.cred_saldo_actual(r.credito_id);
    if r.final > public.cred_disponible(r.credito_id, p_periodo) then
      raise exception 'BeeHuman: el descuento excede el saldo disponible del crédito; no se procesó.';
    end if;
    insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo, usuario_id)
    values (pe.tenant_id, r.credito_id, p_periodo, r.id, r.final, v_saldo, v_saldo - r.final, auth.uid());
    if v_saldo - r.final = 0 then
      insert into public.cred_historia (tenant_id, credito_id, evento, antes, despues, fecha_efectiva, motivo, usuario_id, nombre)
      select pe.tenant_id, c.id, 'terminacion_saldo', to_jsonb(c), to_jsonb(c) || jsonb_build_object('estado', 'terminado', 'fecha_fin', pe.fin),
             pe.fin, 'Saldo liquidado al procesar el periodo ' || pe.inicio || ' – ' || pe.fin, auth.uid(), public.inc_nombre_usuario()
        from public.cred_creditos c where c.id = r.credito_id and c.estado <> 'terminado';
      update public.cred_creditos set estado = 'terminado', fecha_fin = least(coalesce(fecha_fin, pe.fin), pe.fin), actualizado_en = now()
       where id = r.credito_id and estado <> 'terminado';
    end if;
  end loop;
  return 'Periodo marcado como procesado.';
end $function$;
CREATE OR REPLACE FUNCTION public.inc_firmar_hoja(p_hoja uuid, p_area text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
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
end $function$;
drop function public.inc_concentrado_periodo(uuid);
drop function public.inc_firmar_periodo(uuid, text);
drop function public.inc__faltantes_con_firma(uuid, jsonb);
drop function public.inc_faltantes_bloqueantes(uuid);
drop function public.inc__faltantes_base(uuid);
drop function public.inc_firma_periodo_estado(uuid, jsonb);
drop function public.inc_concentrado_huella(uuid);
drop function public.inc__huella_de(jsonb);
drop function public.inc__concentrado_base(uuid);
alter table public.inc_eventos drop column huella;
commit;
