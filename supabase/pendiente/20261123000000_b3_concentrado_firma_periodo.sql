-- BeeHuman · B3 concentrado + firma única de Nómina por periodo (opción B) · 23-nov-2026
-- Diseño aprobado: claude/B1-opcion-B-firma-periodo-diseno-23nov.md (v3.1). Autorización B-a de Erik (23-nov 13:50): solo local.
-- Reemplaza las dos migraciones locales del 20-nov (b1_2_firma_periodo y b3_concentrado_periodo), que nunca se aplicaron
-- fuera de la base local.
--
-- Qué hace:
--  * inc_eventos.huella (jsonb): huella guardada en la firma de Nómina del periodo y en el procesado.
--  * inc__concentrado_base: contenido del concentrado y documento canónico v1, en UNA sentencia (misma instantánea).
--  * inc__huella_de / inc_concentrado_huella: SHA-256 total y por sección (9 secciones).
--  * inc_firma_periodo_estado: sin_firma / vigente / invalidada (con secciones) / definicion_anterior, contra la huella ACTUAL.
--  * inc__faltantes_base, inc_faltantes_bloqueantes, inc__faltantes_con_firma, inc_faltantes_procesar:
--    Nómina firma el periodo (no cada hoja); RH sigue por hoja y versión; designar responsable de Nómina es obligatorio siempre.
--  * inc_concentrado_periodo: datos + estado + faltantes + huella + firma + aviso «cambió después de procesarse».
--  * inc_firmar_periodo(periodo, huella_revisada): firma única, bloquea el periodo, una sola lectura consistente.
--  * inc_marcar_procesado: faltantes y huella de la misma instantánea; guarda la huella del procesado.
--  * inc_firmar_hoja: rechaza el área Nómina (las firmas antiguas por hoja quedan como historial).
-- Todas las funciones de lectura son STABLE (instantánea de la consulta que las llama). Sin tablas nuevas.
-- No crea, borra ni modifica datos existentes. Reversión: reversion/20261123000000_reversion_b3_concentrado_firma_periodo.sql
begin;
do $$
begin
  if to_regprocedure('public.inc_concentrado_huella(uuid)') is not null then
    raise exception 'BeeHuman: B3 + firma del periodo (opción B) ya está aplicada.';
  end if;
  if to_regprocedure('public.inc_hoja_vacia_sin_personal(uuid)') is null or to_regclass('public.cred_descuentos') is null then
    raise exception 'BeeHuman: requiere B5 y la corrección «Mis hojas».';
  end if;
end $$;

alter table public.inc_eventos add column huella jsonb;
comment on column public.inc_eventos.huella is 'Huella del concentrado (v, total, secciones) en la firma de Nómina del periodo y en el procesado.';

-- Contenido del concentrado (pantalla) y documento canónico de la huella, en UNA sola sentencia:
-- ambos salen de la misma instantánea (función STABLE; diseño v3.1 §3.0).
create function public.inc__concentrado_base(p_periodo uuid) returns jsonb
language plpgsql stable security definer set search_path to '' as $$
declare pe record; v_emp text; v_res jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  select nombre into v_emp from public.empresas where id = pe.empresa_id;
  with
  dias as (select d::date as f from generate_series(pe.inicio, pe.fin, interval '1 day') d),
  rels as (
    select rl.* from public.relaciones_laborales rl
     where rl.tenant_id = pe.tenant_id and rl.empresa_id = pe.empresa_id and rl.estado <> 'anulada'
       and coalesce(rl.fecha_ingreso, '-infinity'::date) <= pe.fin
       and ((rl.estado = 'vigente' and rl.fecha_baja is null) or rl.fecha_baja >= pe.inicio)),
  -- Hojas incluidas: enviadas o procesadas, versión vigente.
  hojas as (
    select h.id hoja_id, h.tipo, h.posterior_procesamiento posterior, h.estado, h.coordinador_id,
           co.nombre_completo coordinador, v.id version_id, v.numero version, v.datos, v.creada_en
      from public.inc_hojas h
      join public.inc_versiones v on v.hoja_id = h.id and v.numero = h.version_actual
      join public.personal co on co.id = h.coordinador_id
     where h.periodo_id = pe.id and h.estado in ('enviada','procesada') and h.version_actual > 0),
  celdas as (
    select (c->>'personal_id')::uuid pid, (c->>'fecha')::date f, c->>'codigo' codigo,
           (c->>'proyecto_id')::uuid proyecto_id, (c->>'centro_costo_id')::uuid centro_costo_id, h.hoja_id, h.posterior
      from hojas h cross join lateral jsonb_array_elements(coalesce(h.datos->'celdas', '[]')) c),
  cant as (
    select (q->>'personal_id')::uuid pid, (q->>'fecha')::date f, (q->>'concepto_id')::uuid cid,
           (q->>'cantidad')::numeric cantidad, coalesce(q->>'tipo_linea', 'captura') tipo_linea, h.hoja_id, h.posterior
      from hojas h cross join lateral jsonb_array_elements(coalesce(h.datos->'cantidades', '[]')) q),
  obs as (
    select (o->>'personal_id')::uuid pid, o->>'texto' texto, h.hoja_id, h.coordinador
      from hojas h cross join lateral jsonb_array_elements(coalesce(h.datos->'observaciones', '[]')) o),
  imp as (
    select i.*, h.hoja_id, h.posterior, h.coordinador, h.version, h.tipo tipo_hoja,
           cl.nombre clasificacion
      from public.inc_importes i
      join hojas h on h.version_id = i.version_id
      left join public.personal_registros_pago rp on rp.id = i.registro_pago_id
      left join public.clasificaciones_personal cl on cl.id = rp.clasificacion_id
     where i.origen <> 'descartado'),
  descu as (
    select d.*, c.tipo tipo_credito, public.cred_etiqueta(c) etiqueta
      from public.cred_descuentos d join public.cred_creditos c on c.id = d.credito_id
     where d.periodo_id = pe.id and d.origen <> 'descartado'),
  info as (
    select c.*, public.cred_etiqueta(c) etiqueta from public.cred_creditos c
     where c.tenant_id = pe.tenant_id and c.estado = 'activo' and not public.cred_es_calculable(c)
       and c.tipo in ('infonavit','pension')
       and c.relacion_laboral_id in (select id from rels)
       and c.fecha_inicio <= pe.fin and (c.fecha_fin is null or c.fecha_fin >= pe.inicio)),
  movs as (
    select e.id evento_id, e.personal_id pid, e.tipo, e.fecha_efectiva, e.causa from public.eventos_laborales e
     where e.estado = 'vigente' and e.relacion_laboral_id in (select id from rels)
       and e.fecha_efectiva between pe.inicio and pe.fin),
  esq as (
    select rp.*, cl.nombre clasificacion from public.personal_registros_pago rp
      left join public.clasificaciones_personal cl on cl.id = rp.clasificacion_id
     where rp.tenant_id = pe.tenant_id
       and (rp.empresa_id = pe.empresa_id or rp.relacion_laboral_id in (select id from rels))
       and rp.fecha_inicio <= pe.fin and (rp.fecha_fin is null or rp.fecha_fin >= pe.inicio)),
  -- Personas: con relación en el periodo, más (por seguridad) cualquiera que aparezca en una hoja incluida.
  ids as (
    select personal_id pid from rels
    union select pid from celdas union select pid from cant union select personal_id from imp union select pid from obs),
  vig as (
    select i.pid, count(distinct d.f) dias_vigentes
      from ids i join rels rl on rl.personal_id = i.pid
      join dias d on coalesce(rl.fecha_ingreso, '-infinity'::date) <= d.f and ((rl.estado = 'vigente' and rl.fecha_baja is null) or d.f <= rl.fecha_baja)
     group by i.pid),
  rel_pri as (
    select distinct on (rl.personal_id) rl.personal_id pid, rl.id, rl.numero_interno, rl.registro_patronal_id, rl.fecha_ingreso, rl.fecha_baja
      from rels rl order by rl.personal_id, (rl.registro_patronal_id is not null) desc, rl.fecha_ingreso desc nulls last, rl.creado_en desc),
  altas_bajas as (
    select rl.personal_id pid,
           min(rl.fecha_ingreso) filter (where rl.fecha_ingreso between pe.inicio and pe.fin) alta,
           max(rl.fecha_baja) filter (where rl.fecha_baja between pe.inicio and pe.fin) baja
      from rels rl group by rl.personal_id),
  proy as (
    select pid, proyecto_id from (
      select i.pid, coalesce(c.proyecto_id, p.proyecto_id) proyecto_id, count(*) n,
             row_number() over (partition by i.pid order by count(*) desc, coalesce(c.proyecto_id, p.proyecto_id) = p.proyecto_id desc) rn
        from ids i join public.personal p on p.id = i.pid
        join rels rl on rl.personal_id = i.pid
        join dias d on coalesce(rl.fecha_ingreso, '-infinity'::date) <= d.f and ((rl.estado = 'vigente' and rl.fecha_baja is null) or d.f <= rl.fecha_baja)
        left join celdas c on c.pid = i.pid and c.f = d.f and not c.posterior
       group by i.pid, coalesce(c.proyecto_id, p.proyecto_id), p.proyecto_id) x
     where rn = 1),
  coords as (
    select pid, jsonb_agg(distinct coordinador) nombres from (
      select c.pid, h.coordinador from celdas c join hojas h using (hoja_id)
      union select q.pid, h.coordinador from cant q join hojas h using (hoja_id)
      union select i.personal_id, i.coordinador from imp i
      union select o.pid, o.coordinador from obs o) x group by pid),
  origen as (
    select pid, jsonb_agg(jsonb_build_object('hoja_id', h.hoja_id, 'tipo', h.tipo, 'coordinador', h.coordinador, 'version', h.version,
                                             'posterior', h.posterior) order by h.coordinador, h.tipo desc, h.version) hojas
      from (select pid, hoja_id from celdas union select pid, hoja_id from cant union select personal_id, hoja_id from imp
            union select pid, hoja_id from obs) x join hojas h using (hoja_id) group by pid),
  p_dias as (
    select pid, jsonb_object_agg(codigo, n) por_codigo from (
      select pid, codigo, count(*) n from celdas where not posterior and codigo is not null group by pid, codigo) x group by pid),
  p_dia_det as (
    select pid, jsonb_agg(jsonb_build_object('fecha', f, 'codigo', codigo, 'proyecto', pr.nombre, 'centro_costo', cc.nombre,
                                             'hoja_id', hoja_id, 'posterior', posterior) order by f) celdas
      from celdas c left join public.proyectos pr on pr.id = c.proyecto_id left join public.centros_costo cc on cc.id = c.centro_costo_id
     group by pid),
  p_cant as (
    select pid, jsonb_object_agg(cid, total) totales from (
      select pid, cid, sum(cantidad) total from cant where not posterior group by pid, cid) x group by pid),
  p_cant_det as (
    select pid, jsonb_agg(jsonb_build_object('fecha', f, 'concepto_id', cid, 'cantidad', cantidad, 'tipo_linea', tipo_linea,
                                             'hoja_id', hoja_id, 'posterior', posterior) order by f, cid) lineas
      from cant group by pid),
  p_imp as (
    select personal_id pid,
           jsonb_agg(jsonb_build_object('concepto_id', concepto_id, 'registro_pago_id', registro_pago_id, 'clasificacion', clasificacion,
                     'modalidad', modalidad, 'cantidad', cantidad, 'sugerido', sugerido,
                     'final', case when origen in ('aceptado','modificado') then final end, 'origen', origen,
                     'estado', case when origen in ('aceptado','modificado') then 'decidido'
                                    when origen = 'sin_importe' then 'sin_importe' else 'por_decidir' end,
                     'decidido_en', decidido_en, 'hoja_id', hoja_id, 'coordinador', coordinador, 'version', version,
                     'complemento', tipo_hoja = 'complemento', 'posterior', posterior)
                     order by posterior, concepto_id, modalidad nulls last, clasificacion) lineas,
           count(*) filter (where not posterior and origen in ('pendiente','sin_sueldo','por_asignar')) por_decidir
      from imp group by personal_id),
  p_imp_tot as (
    select pid, jsonb_object_agg(cid, mods) totales from (
      select personal_id pid, concepto_id cid, jsonb_object_agg(coalesce(modalidad, 'sin_modalidad'), total) mods from (
        select personal_id, concepto_id, modalidad, sum(final) total from imp
         where not posterior and origen in ('aceptado','modificado') group by 1, 2, 3) y group by 1, 2) x group by pid),
  p_desc as (
    select personal_id pid,
           jsonb_agg(jsonb_build_object('descuento_id', id, 'credito_id', credito_id, 'tipo', tipo_credito, 'etiqueta', etiqueta,
                     'sugerido', sugerido, 'final', case when origen in ('aceptado','modificado') then final end, 'origen', origen,
                     'estado', case when origen in ('aceptado','modificado') then 'decidido' else 'por_decidir' end) order by etiqueta) lineas,
           sum(final) filter (where origen in ('aceptado','modificado')) total_decidido,
           count(*) filter (where origen = 'pendiente') por_decidir
      from descu group by personal_id),
  p_info as (
    select personal_id pid, jsonb_agg(jsonb_build_object('credito_id', id, 'tipo', tipo, 'etiqueta', etiqueta,
             'infonavit_tipo', infonavit_tipo, 'infonavit_valor', infonavit_valor, 'pension_forma', pension_forma,
             'pension_valor', pension_valor) order by etiqueta) lineas
      from info group by personal_id),
  p_movs as (
    select pid, jsonb_agg(jsonb_build_object('tipo', tipo, 'fecha', fecha_efectiva, 'causa', causa) order by fecha_efectiva, tipo) lineas
      from movs group by pid),
  p_obs as (
    select pid, jsonb_agg(jsonb_build_object('texto', texto, 'coordinador', coordinador, 'hoja_id', hoja_id)) lineas from obs group by pid),
  p_esq as (
    select personal_id pid, jsonb_agg(jsonb_build_object('registro_pago_id', id, 'clasificacion', clasificacion, 'modalidad', modalidad_sueldo,
             'sueldo', sueldo, 'dias_periodo', dias_periodo, 'fecha_inicio', fecha_inicio, 'fecha_fin', fecha_fin, 'activo', activo)
             order by fecha_inicio, id) lineas
      from esq where personal_id in (select pid from ids) group by personal_id),
  personas as (
    select p.id pid, p.nombre_completo, p.empleado_id, rp.numero_interno, erp.registro_patronal, pr.nombre proyecto,
           coalesce(v.dias_vigentes, 0) dias_vigentes, ab.alta, ab.baja,
           coalesce(c.nombres, '[]') coordinadores, coalesce(o.hojas, '[]') origen, coalesce(pd.por_codigo, '{}') dias, coalesce(dd.celdas, '[]') celdas,
           coalesce(pc.totales, '{}') cantidades, coalesce(cd.lineas, '[]') cantidades_detalle,
           coalesce(pi.lineas, '[]') importes, coalesce(pit.totales, '{}') importes_decididos, coalesce(pi.por_decidir, 0) importes_por_decidir,
           coalesce(pdsc.lineas, '[]') descuentos, coalesce(pdsc.total_decidido, 0) descuentos_decididos, coalesce(pdsc.por_decidir, 0) descuentos_por_decidir,
           coalesce(pin.lineas, '[]') informativos, coalesce(pes.lineas, '[]') esquemas, coalesce(pm.lineas, '[]') movimientos, coalesce(pob.lineas, '[]') observaciones,
           (pd.pid is not null or pc.pid is not null or pi.pid is not null or pob.pid is not null) con_incidencias,
           (rp.pid is null) sin_relacion
      from ids i join public.personal p on p.id = i.pid
      left join rel_pri rp on rp.pid = i.pid
      left join public.empresas_registros_patronales erp on erp.id = rp.registro_patronal_id
      left join proy py on py.pid = i.pid left join public.proyectos pr on pr.id = py.proyecto_id
      left join vig v on v.pid = i.pid left join altas_bajas ab on ab.pid = i.pid
      left join coords c on c.pid = i.pid left join origen o on o.pid = i.pid
      left join p_dias pd on pd.pid = i.pid left join p_dia_det dd on dd.pid = i.pid
      left join p_cant pc on pc.pid = i.pid left join p_cant_det cd on cd.pid = i.pid
      left join p_imp pi on pi.pid = i.pid left join p_imp_tot pit on pit.pid = i.pid
      left join p_desc pdsc on pdsc.pid = i.pid left join p_info pin on pin.pid = i.pid
      left join p_movs pm on pm.pid = i.pid left join p_obs pob on pob.pid = i.pid
      left join p_esq pes on pes.pid = i.pid)
  select jsonb_build_object(
  'datos', jsonb_build_object(
    'periodo', jsonb_build_object('id', pe.id, 'empresa_id', pe.empresa_id, 'empresa', v_emp, 'inicio', pe.inicio, 'fin', pe.fin,
                                  'procesado_en', pe.procesado_en, 'dias', pe.fin - pe.inicio + 1),
    'avisos', jsonb_build_object(
       'complementos_posteriores', (select count(*) from hojas where posterior),
       'personas_sin_relacion', (select count(*) from personas where sin_relacion)),
    'hojas', (select coalesce(jsonb_agg(jsonb_build_object('hoja_id', hoja_id, 'tipo', tipo, 'coordinador', coordinador, 'version', version,
                                                           'estado', estado, 'posterior', posterior, 'enviada_en', creada_en)
                                        order by coordinador, tipo desc, creada_en), '[]') from hojas),
    'conceptos', (select coalesce(jsonb_agg(jsonb_build_object('id', k.id, 'nombre', k.nombre, 'abreviatura', k.abreviatura, 'unidad', k.unidad,
                                                               'tipo', k.tipo, 'modo', k.modo, 'activo', k.activo) order by k.orden, k.nombre), '[]')
                    from public.inc_conceptos k
                   where k.empresa_id = pe.empresa_id and (k.activo or k.id in (select cid from cant) or k.id in (select concepto_id from imp))),
    'personas', (select coalesce(jsonb_agg(to_jsonb(x) - 'pid' || jsonb_build_object('personal_id', x.pid) order by x.nombre_completo, x.pid), '[]') from personas x),
    'totales', jsonb_build_object(
       'personas', (select count(*) from personas),
       'con_incidencias', (select count(*) from personas where con_incidencias),
       'dias', (select coalesce(jsonb_object_agg(codigo, n), '{}') from (select codigo, count(*) n from celdas where not posterior and codigo is not null group by codigo) x),
       'cantidades', (select coalesce(jsonb_object_agg(cid, t), '{}') from (select cid, sum(cantidad) t from cant where not posterior group by cid) x),
       'importes', (select coalesce(jsonb_object_agg(cid, mods), '{}') from (
                      select concepto_id cid, jsonb_object_agg(coalesce(modalidad, 'sin_modalidad'), t) mods from (
                        select concepto_id, modalidad, sum(final) t from imp where not posterior and origen in ('aceptado','modificado') group by 1, 2) y group by 1) x),
       'importes_por_modalidad', (select coalesce(jsonb_object_agg(coalesce(modalidad, 'sin_modalidad'), t), '{}') from (
                      select modalidad, sum(final) t from imp where not posterior and origen in ('aceptado','modificado') group by 1) x),
       'importes_por_decidir', (select count(*) from imp where not posterior and origen in ('pendiente','sin_sueldo','por_asignar')),
       'descuentos', (select coalesce(jsonb_object_agg(tipo_credito, t), '{}') from (
                      select tipo_credito, sum(final) t from descu where origen in ('aceptado','modificado') group by 1) x),
       'descuentos_por_decidir', (select count(*) from descu where origen = 'pendiente'),
       'informativos', (select count(*) from info),
       'movimientos', (select coalesce(jsonb_object_agg(tipo, n), '{}') from (select tipo, count(*) n from movs group by tipo) x))
  ),
  -- ===== Documento canónico v1 (diseño v3.1 §1.2): solo contenido material, orden explícito, números normalizados =====
  -- Sin nombres, datos personales, proyecto, observaciones, fechas de decisión, origen aceptado/modificado,
  -- sugeridos, ids internos de línea de importe ni complementos posteriores al procesamiento.
  'canonico', jsonb_build_object(
    'v', 1,
    'periodo', jsonb_build_object('id', pe.id, 'empresa_id', pe.empresa_id, 'inicio', pe.inicio, 'fin', pe.fin),
    'hojas', (select coalesce(jsonb_agg(jsonb_build_object('hoja_id', hoja_id, 'tipo', tipo, 'version', version) order by hoja_id), '[]')
                from hojas where not posterior),
    'personas', (select coalesce(jsonb_agg(jsonb_build_object(
                    'personal_id', i.pid,
                    'relaciones', (select coalesce(jsonb_agg(jsonb_build_object('relacion_id', rl.id, 'numero_interno', rl.numero_interno,
                                     'registro_patronal_id', rl.registro_patronal_id) order by rl.id), '[]') from rels rl where rl.personal_id = i.pid),
                    'dias_vigentes', coalesce(v.dias_vigentes, 0), 'alta_en_periodo', ab.alta, 'baja_en_periodo', ab.baja) order by i.pid), '[]')
                   from ids i left join vig v on v.pid = i.pid left join altas_bajas ab on ab.pid = i.pid),
    'dias', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', pid, 'fecha', f, 'codigo', codigo, 'hoja_id', hoja_id)
                order by pid, f, hoja_id, codigo), '[]') from celdas where not posterior and codigo is not null),
    'cantidades', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', pid, 'fecha', f, 'concepto_id', cid,
                     'cantidad', trim_scale(cantidad), 'tipo_linea', tipo_linea, 'hoja_id', hoja_id)
                     order by pid, hoja_id, f, cid, tipo_linea, cantidad), '[]') from cant where not posterior),
    -- Identidad de la línea = la llave única de inc_importes sin la versión: persona, hoja, concepto, relación y esquema
    -- (inc_importes_linea_uq, con COALESCE de relación y esquema: dos NULL cuentan como iguales). Una hoja aporta solo su
    -- versión vigente, así que hoja ↔ versión y la identidad es única. La modalidad es atributo, no llave.
    -- Las líneas «sin_importe» no entran (opción A): no llevan dinero y su cantidad ya está en «cantidades».
    'importes', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', personal_id, 'hoja_id', hoja_id, 'concepto_id', concepto_id,
                   'relacion_laboral_id', relacion_laboral_id, 'registro_pago_id', registro_pago_id, 'modalidad', modalidad,
                   'cantidad', trim_scale(cantidad),
                   'estado', case when origen in ('aceptado','modificado') then 'decidido' when origen = 'sin_importe' then 'sin_importe' else 'por_decidir' end,
                   'final', case when origen in ('aceptado','modificado') then trim_scale(final) end)
                   order by personal_id, hoja_id, concepto_id, relacion_laboral_id nulls first, registro_pago_id nulls first), '[]')
                   from imp where not posterior and origen <> 'sin_importe'),   -- opción A (23-nov): sin dinero, su cantidad ya está en «cantidades»
    'esquemas', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', personal_id, 'registro_pago_id', id,
                   'relacion_laboral_id', relacion_laboral_id, 'registro_patronal_id', registro_patronal_id, 'clasificacion_id', clasificacion_id,
                   'modalidad', modalidad_sueldo, 'sueldo', trim_scale(sueldo), 'dias_periodo', trim_scale(dias_periodo),
                   'fecha_inicio', fecha_inicio, 'fecha_fin', fecha_fin, 'activo', activo) order by personal_id, id), '[]')
                   from esq where personal_id in (select pid from ids)),
    'descuentos', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', personal_id, 'descuento_id', id, 'credito_id', credito_id,
                     'estado', case when origen in ('aceptado','modificado') then 'decidido' else 'por_decidir' end,
                     'final', case when origen in ('aceptado','modificado') then trim_scale(final) end)
                     order by personal_id, credito_id, id), '[]') from descu),
    'informativos', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', personal_id, 'credito_id', id, 'tipo', tipo,
                       'infonavit_tipo', infonavit_tipo, 'infonavit_valor', trim_scale(infonavit_valor),
                       'pension_forma', pension_forma, 'pension_valor', trim_scale(pension_valor)) order by personal_id, id), '[]') from info),
    'movimientos', (select coalesce(jsonb_agg(jsonb_build_object('personal_id', pid, 'evento_id', evento_id, 'tipo', tipo,
                      'fecha_efectiva', fecha_efectiva, 'causa', causa) order by pid, fecha_efectiva, tipo, evento_id), '[]') from movs)
  )
  ) into v_res;
  return v_res;
end $$;

-- Huella SHA-256 del documento canónico: total y por sección (diseño v3.1 §1.1).
create function public.inc__huella_de(p_canonico jsonb) returns jsonb
language sql stable set search_path to '' as $$
  select jsonb_build_object(
    'v', (p_canonico->>'v')::int,
    'total', encode(sha256(convert_to(p_canonico::text, 'UTF8')), 'hex'),
    'secciones', (select jsonb_object_agg(s, encode(sha256(convert_to(coalesce(p_canonico->s, 'null'::jsonb)::text, 'UTF8')), 'hex'))
                    from unnest(array['hojas','personas','dias','cantidades','importes','esquemas','descuentos','informativos','movimientos']) s))
$$;

create function public.inc_concentrado_huella(p_periodo uuid) returns jsonb
language sql stable security definer set search_path to '' as $$
  select public.inc__huella_de(public.inc__concentrado_base(p_periodo)->'canonico')
$$;

-- Estado de la firma de Nómina del periodo, SIEMPRE contra la huella actual (diseño v3.1 §2).
-- p_huella: la huella ya calculada en la misma sentencia (para no recalcular); si es nula, se calcula.
create function public.inc_firma_periodo_estado(p_periodo uuid, p_huella jsonb default null) returns jsonb
language plpgsql stable security definer set search_path to '' as $$
declare pe record; f record; h jsonb; v_cambio jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  h := coalesce(p_huella, public.inc_concentrado_huella(p_periodo));
  select e.* into f from public.inc_eventos e
   where e.periodo_id = pe.id and e.hoja_id is null and e.tipo = 'firma_nomina'
   order by e.creado_en desc, e.id desc limit 1;
  if f.id is null then
    return jsonb_build_object('estado', 'sin_firma', 'firma', null, 'secciones_cambiadas', '[]'::jsonb, 'huella_actual', h);
  end if;
  if f.huella is null or (f.huella->>'v') is distinct from (h->>'v') then
    return jsonb_build_object('estado', 'definicion_anterior', 'secciones_cambiadas', '[]'::jsonb, 'huella_actual', h,
      'firma', jsonb_build_object('evento_id', f.id, 'nombre', f.nombre, 'usuario_id', f.usuario_id, 'creado_en', f.creado_en));
  end if;
  select coalesce(jsonb_agg(s order by o), '[]') into v_cambio
    from unnest(array['hojas','personas','dias','cantidades','importes','esquemas','descuentos','informativos','movimientos']) with ordinality u(s, o)
   where (f.huella->'secciones'->>s) is distinct from (h->'secciones'->>s);
  return jsonb_build_object(
    'estado', case when f.huella->>'total' = h->>'total' then 'vigente' else 'invalidada' end,
    'secciones_cambiadas', v_cambio, 'huella_actual', h,
    'firma', jsonb_build_object('evento_id', f.id, 'nombre', f.nombre, 'usuario_id', f.usuario_id, 'creado_en', f.creado_en));
end $$;

-- Faltantes sin la firma de Nómina del periodo. RH sigue firmando cada hoja enviada en su versión vigente.
create function public.inc__faltantes_base(p_periodo uuid) returns table(orden integer, tipo text, detalle text)
language plpgsql stable security definer set search_path to '' as $$
#variable_conflict use_column
declare pe record; prm record;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id();
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  select * into prm from public.inc_parametros x where x.empresa_id = pe.empresa_id;
  return query
  select f.orden, f.tipo, f.detalle from (
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
     where prm.responsable_nomina_user is null   -- opción B: siempre, haya o no hojas enviadas
    union all
    select 3, 'firma', co.nombre_completo || ': falta la firma de ' || a.nombre || ' (versión ' || h.version_actual || ')'
      from public.inc_hojas h
      join public.inc_versiones v on v.hoja_id = h.id and v.numero = h.version_actual
      join public.personal co on co.id = h.coordinador_id
      cross join (values ('rh', 'RH', prm.responsable_rh_user)) a(area, nombre, resp)   -- opción B: Nómina ya no firma por hoja
     where h.periodo_id = pe.id and h.estado = 'enviada' and a.resp is not null
       and not exists (select 1 from public.inc_eventos e where e.version_id = v.id and e.tipo = 'firma_' || a.area)
  ) f
  order by f.orden, f.detalle;
end $$;

-- Pendientes que BLOQUEAN la firma de Nómina (diseño v3.1 §4): hojas, importes, descuentos y la falta de responsable
-- de Nómina. Las firmas de RH no bloquean.
create function public.inc_faltantes_bloqueantes(p_periodo uuid) returns table(tipo text, detalle text)
language sql stable security definer set search_path to '' as $$
  select f.tipo, f.detalle from public.inc__faltantes_base(p_periodo) f
   where f.tipo in ('hoja','importe','descuento') or f.detalle like 'Designa al responsable de Nómina%'
   order by f.orden, f.detalle
$$;

-- Faltantes completos con la firma de Nómina del periodo según un estado de firma dado (de la misma instantánea).
create function public.inc__faltantes_con_firma(p_periodo uuid, p_firma jsonb) returns table(tipo text, detalle text)
language plpgsql stable security definer set search_path to '' as $$
declare v_resp uuid; v_linea text; v_f jsonb := p_firma->'firma';
begin
  select x.responsable_nomina_user into v_resp from public.inc_parametros x join public.inc_periodos pe on pe.empresa_id = x.empresa_id
   where pe.id = p_periodo;
  if v_resp is not null then
    v_linea := case p_firma->>'estado'
      when 'vigente' then null
      when 'sin_firma' then 'Falta la firma de Nómina del periodo'
      when 'invalidada' then 'La firma de Nómina de ' || coalesce(v_f->>'nombre', '—') || ' del '
             || to_char((v_f->>'creado_en')::timestamptz at time zone 'America/Mexico_City', 'DD/MM/YYYY HH24:MI')
             || ' ya no es vigente: el concentrado cambió después de firmar (cambió: '
             || (select string_agg(s, ', ') from jsonb_array_elements_text(p_firma->'secciones_cambiadas') s) || ')'
      else 'La firma de Nómina de ' || coalesce(v_f->>'nombre', '—') || ' se hizo con una definición anterior; vuelve a firmar el periodo' end;
  end if;
  return query
  select x.tipo, x.detalle from (
    select b.orden, b.tipo, b.detalle from public.inc__faltantes_base(p_periodo) b
    union all select 3, 'firma', v_linea where v_linea is not null) x
  order by x.orden, x.detalle;
end $$;

create or replace function public.inc_faltantes_procesar(p_periodo uuid) returns table(tipo text, detalle text)
language sql stable security definer set search_path to '' as $$
  select f.tipo, f.detalle from public.inc__faltantes_con_firma(p_periodo, public.inc_firma_periodo_estado(p_periodo)) f
$$;

create function public.inc_concentrado_periodo(p_periodo uuid) returns jsonb
language plpgsql stable security definer set search_path to '' as $$
declare pe record; b jsonb; h jsonb; f jsonb; v_falt jsonb := '[]'; v_estado text; v_proc record; v_post jsonb := null;
begin
  -- Todo en una función STABLE: una sola instantánea para datos, huella, firma y faltantes.
  b := public.inc__concentrado_base(p_periodo);   -- valida permisos y tenant
  select * into pe from public.inc_periodos x where x.id = p_periodo;
  h := public.inc__huella_de(b->'canonico');
  f := public.inc_firma_periodo_estado(p_periodo, h);
  if pe.procesado_en is not null then
    v_estado := 'procesado';
    select e.* into v_proc from public.inc_eventos e where e.periodo_id = pe.id and e.tipo = 'procesado' order by e.creado_en desc limit 1;
    if v_proc.huella is not null and v_proc.huella->>'total' is distinct from h->>'total' then
      v_post := jsonb_build_object('procesado_en', pe.procesado_en, 'secciones', (
        select coalesce(jsonb_agg(s order by o), '[]')
          from unnest(array['hojas','personas','dias','cantidades','importes','esquemas','descuentos','informativos','movimientos']) with ordinality u(s, o)
         where (v_proc.huella->'secciones'->>s) is distinct from (h->'secciones'->>s)));
    end if;
  else
    select coalesce(jsonb_agg(jsonb_build_object('tipo', x.tipo, 'detalle', x.detalle)), '[]') into v_falt
      from public.inc__faltantes_con_firma(p_periodo, f) x;
    v_estado := case when jsonb_array_length(v_falt) = 0 then 'listo' else 'preliminar' end;
  end if;
  return (b->'datos') || jsonb_build_object(
    'estado', v_estado, 'faltantes', v_falt, 'huella', h, 'firma', f,
    'avisos', (b->'datos'->'avisos') || jsonb_build_object(
      'hojas_no_incluidas', (select coalesce(jsonb_agg(x->>'detalle'), '[]') from jsonb_array_elements(v_falt) x where x->>'tipo' = 'hoja'),
      'cambio_posterior_procesado', v_post));
end $$;

-- Firma única de Nómina del periodo (diseño v3.1 §3.1). p_huella_revisada: la huella total que la pantalla mostraba.
create function public.inc_firmar_periodo(p_periodo uuid, p_huella_revisada text) returns text
language plpgsql security definer set search_path to '' as $$
declare pe record; prm record; v_h jsonb; v_b jsonb; v_f jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: solo el responsable designado de Nómina puede firmar el periodo.'; end if;
  select * into pe from public.inc_periodos x where x.id = p_periodo and x.tenant_id = public.current_tenant_id() for update;
  if pe.id is null then raise exception 'BeeHuman: periodo no encontrado.'; end if;
  select * into prm from public.inc_parametros x where x.empresa_id = pe.empresa_id;
  if prm.responsable_nomina_user is null or prm.responsable_nomina_user is distinct from auth.uid() then
    raise exception 'BeeHuman: solo el responsable designado de Nómina puede firmar el periodo.';
  end if;
  if pe.procesado_en is not null then raise exception 'BeeHuman: el periodo ya está procesado.'; end if;
  -- UNA sola sentencia: huella, pendientes que bloquean y estado de la firma salen de la misma instantánea (§3.0).
  select s.h, s.b, public.inc_firma_periodo_estado(p_periodo, s.h) into v_h, v_b, v_f
    from (select public.inc_concentrado_huella(p_periodo) h,
                 (select coalesce(jsonb_agg(x.detalle), '[]') from public.inc_faltantes_bloqueantes(p_periodo) x) b) s;
  if jsonb_array_length(v_b) > 0 then
    raise exception 'BeeHuman: no se puede firmar el periodo; faltan % pendiente(s): %', jsonb_array_length(v_b),
      left((select string_agg(x, '; ') from jsonb_array_elements_text(v_b) x), 1500);
  end if;
  if p_huella_revisada is distinct from v_h->>'total' then
    raise exception 'BeeHuman: el concentrado cambió mientras lo revisabas; vuelve a cargarlo antes de firmar.';
  end if;
  if v_f->>'estado' = 'vigente' then return 'El periodo ya tiene la firma de Nómina vigente.'; end if;
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre, huella)
  values (pe.tenant_id, pe.id, 'firma_nomina', auth.uid(), public.inc_nombre_usuario(), v_h);
  return 'Firma de Nómina del periodo registrada.';
end $$;

create or replace function public.inc_marcar_procesado(p_periodo uuid)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare pe record; v_falta text; v_n integer; r record; v_saldo numeric; v_h jsonb;
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
  -- Opción B (§3.3): faltantes (con la firma por huella) y huella en UNA sentencia: misma instantánea.
  select s.h, x.n, x.t into v_h, v_n, v_falta
    from (select public.inc_concentrado_huella(p_periodo) h) s
    cross join lateral (select count(*) n, string_agg(f.detalle, '; ') t
                          from public.inc__faltantes_con_firma(p_periodo, public.inc_firma_periodo_estado(p_periodo, s.h)) f) x;
  if v_n > 0 then
    raise exception 'BeeHuman: no se puede procesar; faltan % pendiente(s): %', v_n, left(v_falta, 1500);
  end if;
  update public.inc_periodos set procesado_en = now(), procesado_por = auth.uid() where id = p_periodo;
  update public.inc_hojas set estado = 'procesada' where periodo_id = p_periodo and estado = 'enviada';
  -- Se guarda la huella de la instantánea validada (no se recalcula): base del aviso «cambió después de procesarse».
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre, huella)
  values (pe.tenant_id, p_periodo, 'procesado', auth.uid(), public.inc_nombre_usuario(), v_h);
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

create or replace function public.inc_firmar_hoja(p_hoja uuid, p_area text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare h record; prm record; v_ver uuid;
begin
  if p_area = 'nomina' then
    raise exception 'BeeHuman: Nómina firma el periodo completo (Revisión del periodo), no cada hoja.';
  end if;
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

-- Permisos: solo se exponen las funciones que usa la pantalla; las internas no.
revoke all on function public.inc__concentrado_base(uuid), public.inc__huella_de(jsonb), public.inc_concentrado_huella(uuid),
  public.inc__faltantes_base(uuid), public.inc_faltantes_bloqueantes(uuid), public.inc__faltantes_con_firma(uuid, jsonb)
  from public, anon, authenticated;
revoke all on function public.inc_concentrado_periodo(uuid), public.inc_firma_periodo_estado(uuid, jsonb), public.inc_firmar_periodo(uuid, text)
  from public, anon;
grant execute on function public.inc_concentrado_periodo(uuid), public.inc_firma_periodo_estado(uuid, jsonb), public.inc_firmar_periodo(uuid, text)
  to authenticated;
commit;
