-- BeeHuman · Excel canónico V1 (oficial) y reporte preliminar de acumulado · 24-nov-2026
-- Diseño: claude/Excel-canonico-V1-diseno-funcional-24nov.md (fuente de verdad). Autorización de Erik 24-nov 16:35:
-- implementación local y aplicación SOLO en beehuman-pruebas.
--
-- Solo agrega funciones; no modifica tablas, funciones, políticas ni datos existentes.
--  * inc__exportacion_datos(periodo, modalidad)  interna, STABLE: toda la lectura sale de UNA instantánea (la de la
--    sentencia que la llama): concentrado, canónico, huella, firma, faltantes, evento procesado y datos descriptivos.
--    Arma las hojas, los totales de control, las validaciones y las huellas (serialización §4.1 del diseño).
--  * inc_exportacion_canonica(periodo)    pública: B05, B07, B08, B01–B04, B06; registra evento «exportacion» (oficial).
--  * inc_exportacion_preliminar(periodo)  pública: BP1–BP3; registra evento «exportacion» (preliminar).
--  * Utilidades inmutables de serialización: inc__exp_t/_imp/_num/_fecha/_ts/_linea.
-- Exportar no cambia la firma, la huella del concentrado, el estado del periodo ni la bandeja B6: los eventos no
-- forman parte del documento canónico y B6 solo lee eventos «envio»/«complemento».
-- El evento guarda en inc_eventos.huella (jsonb, ya existente) la modalidad, formato, huellas y conteos; nunca RFC,
-- CURP, NSS ni nombres. No se agrega ninguna columna (V-4).
-- Reversión: reversion/20261125000000_reversion_excel_canonico_v1.sql (no borra eventos ya registrados: son inmutables).
begin;
do $$
begin
  if to_regprocedure('public.inc_exportacion_canonica(uuid)') is not null then
    raise exception 'BeeHuman: el Excel canónico V1 ya está aplicado.';
  end if;
  if to_regprocedure('public.inc__concentrado_base(uuid)') is null or to_regprocedure('public.inc__envios_base(uuid)') is null then
    raise exception 'BeeHuman: requiere B-a (concentrado y firma del periodo) y B6 (bandeja de envíos).';
  end if;
end $$;

-- ---------- Serialización canónica (diseño §4.1) ----------
create function public.inc__exp_t(t text) returns text language sql immutable set search_path to '' as $$
  select normalize(nullif(t, ''), NFC) $$;
create function public.inc__exp_imp(n numeric) returns text language sql immutable set search_path to '' as $$
  select case when n is null then null else round(n, 2)::numeric(38,2)::text end $$;
create function public.inc__exp_num(n numeric) returns text language sql immutable set search_path to '' as $$
  select case when n is null then null else trim_scale(n)::text end $$;
create function public.inc__exp_fecha(d date) returns text language sql immutable set search_path to '' as $$
  select to_char(d, 'YYYY-MM-DD') $$;
-- Fecha y hora en America/Mexico_City con el desplazamiento vigente en ese instante.
create function public.inc__exp_ts(t timestamptz) returns text language sql immutable set search_path to '' as $$
  select case when t is null then null else
    to_char(t at time zone 'America/Mexico_City', 'YYYY-MM-DD"T"HH24:MI:SS') ||
    (select case when s < 0 then '-' else '+' end || lpad((abs(s) / 3600)::text, 2, '0') || ':' || lpad(((abs(s) % 3600) / 60)::text, 2, '0')
       from (select extract(epoch from (t at time zone 'America/Mexico_City') - (t at time zone 'UTC'))::int s) x) end $$;
-- Un registro = arreglo JSON en una línea, sin espacios; los escapes son los de PostgreSQL (iguales a JSON.stringify).
create function public.inc__exp_linea(a jsonb) returns text language sql immutable set search_path to '' as $$
  select '[' || coalesce((select string_agg(e::text, ',' order by o) from jsonb_array_elements(a) with ordinality x(e, o)), '') || ']' $$;

-- ---------- Constructor (interno) ----------
create function public.inc__exportacion_datos(p_periodo uuid, p_modalidad text)
returns jsonb language plpgsql stable security definer set search_path to '' as $$
declare
  b jsonb; dd jsonb; cc jsonb; h jsonb; f jsonb; pe record; v_proc record;
  v_estado text; v_falt jsonb := '[]'; v_firma_h text; v_firma_nom text; v_firma_en timestamptz;
  v_dmap jsonb; v_hmap jsonb; v_pmap jsonb; v_kmap jsonb;
  f_per jsonb; f_esq jsonb; f_inc jsonb; f_can jsonb; f_imp jsonb; f_des jsonb; f_mov jsonb; f_cat jsonb; f_val jsonb;
  v_conf jsonb; v_ctrl jsonb; v_avisos jsonb; v_res jsonb; v_hojas jsonb;
  v_pre boolean := (p_modalidad = 'preliminar'); v_px text; v_fmt text; v_ref text;
  v_ser_d text; v_ser_a text; v_pd_imp int; v_pd_des int;
begin
  if p_modalidad is null or p_modalidad not in ('oficial','preliminar') then raise exception 'BeeHuman: modalidad no válida.'; end if;
  b := public.inc__concentrado_base(p_periodo);                       -- valida rol (Administrador/Nómina) y tenant
  select * into pe from public.inc_periodos x where x.id = p_periodo;
  dd := b->'datos'; cc := b->'canonico';
  h := public.inc__huella_de(cc);
  f := public.inc_firma_periodo_estado(p_periodo, h);
  select e.* into v_proc from public.inc_eventos e where e.periodo_id = pe.id and e.tipo = 'procesado' order by e.creado_en desc limit 1;
  if pe.procesado_en is not null then v_estado := 'procesado';
  else
    select coalesce(jsonb_agg(jsonb_build_object('tipo', x.tipo, 'detalle', x.detalle) order by x.tipo, x.detalle), '[]') into v_falt
      from public.inc__faltantes_con_firma(p_periodo, f) x;
    v_estado := case when jsonb_array_length(v_falt) = 0 then 'listo' else 'preliminar' end;
  end if;
  if f->'firma'->>'evento_id' is not null then
    select e.huella->>'total', e.nombre, e.creado_en into v_firma_h, v_firma_nom, v_firma_en
      from public.inc_eventos e where e.id = (f->'firma'->>'evento_id')::uuid;
  end if;
  v_px := case when v_pre then 'PRELIM ' else '' end;
  v_fmt := case when v_pre then 'beehuman.preliminar' else 'beehuman.canonico' end;

  -- Mapas auxiliares
  select coalesce(jsonb_object_agg(y->>'personal_id', y), '{}') into v_dmap from jsonb_array_elements(dd->'personas') y;
  select coalesce(jsonb_object_agg(y->>'hoja_id', y || jsonb_build_object('posterior', coalesce((select (z->>'posterior')::boolean
           from jsonb_array_elements(dd->'hojas') z where z->>'hoja_id' = y->>'hoja_id'), false))), '{}')
    into v_hmap from jsonb_array_elements(cc->'hojas') y;
  select coalesce(jsonb_object_agg(k.id::text, jsonb_build_object('abrev', k.abreviatura, 'nombre', k.nombre, 'tipo', k.tipo,
           'unidad', k.unidad, 'modo', k.modo)), '{}') into v_kmap
    from public.inc_conceptos k where k.empresa_id = pe.empresa_id;

  -- ===== Personas (orden de persona: numero_interno, nombre, id; comparación binaria) =====
  with base as (
    select (x->>'personal_id')::uuid pid, x cp, v_dmap->(x->>'personal_id') dp, p.rfc, p.curp, p.nss, rl.*
      from jsonb_array_elements(cc->'personas') x
      join public.personal p on p.id = (x->>'personal_id')::uuid
      left join lateral (
        select r.id rel_id, r.numero_interno ni, r.fecha_ingreso, r.fecha_baja from public.relaciones_laborales r
         where r.id in (select (z->>'relacion_id')::uuid from jsonb_array_elements(x->'relaciones') z)
         order by (r.registro_patronal_id is not null) desc, r.fecha_ingreso desc nulls last, r.creado_en desc limit 1) rl on true),
  ord as (select base.*, row_number() over (order by public.inc__exp_t(ni) collate "C" nulls last,
            public.inc__exp_t(dp->>'nombre_completo') collate "C", pid) rk from base)
  select coalesce(jsonb_agg(jsonb_build_array(
           public.inc__exp_t(ni), public.inc__exp_t(dp->>'nombre_completo'), public.inc__exp_t(rfc), public.inc__exp_t(curp), public.inc__exp_t(nss),
           public.inc__exp_t(dp->>'registro_patronal'), public.inc__exp_fecha(fecha_ingreso), public.inc__exp_fecha(fecha_baja),
           public.inc__exp_fecha((cp->>'alta_en_periodo')::date), public.inc__exp_fecha((cp->>'baja_en_periodo')::date),
           (cp->>'dias_vigentes')::int::text, jsonb_array_length(cp->'relaciones')::text,
           (select count(*) from jsonb_array_elements(cc->'esquemas') e where e->>'personal_id' = pid::text)::text,
           public.inc__exp_t(dp->>'proyecto'),
           public.inc__exp_t((select string_agg(c, ' · ' order by o) from jsonb_array_elements_text(coalesce(dp->'coordinadores', '[]')) with ordinality z(c, o))),
           coalesce((dp->>'con_incidencias')::boolean, false), pid::text, rel_id::text) order by rk), '[]'),
         coalesce(jsonb_object_agg(pid::text, jsonb_build_object('rk', rk, 'ni', public.inc__exp_t(ni), 'nom', public.inc__exp_t(dp->>'nombre_completo'),
           'dias', (cp->>'dias_vigentes')::int, 'rels', jsonb_array_length(cp->'relaciones'), 'alta', cp->>'alta_en_periodo', 'baja', cp->>'baja_en_periodo',
           'esq', (select count(*) from jsonb_array_elements(cc->'esquemas') e where e->>'personal_id' = pid::text))), '{}')
    into f_per, v_pmap from ord;

  -- ===== Esquemas =====
  select coalesce(jsonb_agg(jsonb_build_array(
           v_pmap->(e->>'personal_id')->>'ni', v_pmap->(e->>'personal_id')->>'nom',
           public.inc__exp_t(cl.nombre), public.inc__exp_t(e->>'modalidad'), public.inc__exp_imp((e->>'sueldo')::numeric),
           public.inc__exp_num((e->>'dias_periodo')::numeric), public.inc__exp_fecha((e->>'fecha_inicio')::date), public.inc__exp_fecha((e->>'fecha_fin')::date),
           (e->>'activo')::boolean, public.inc__exp_t(erp.registro_patronal), e->>'personal_id', e->>'registro_pago_id', e->>'relacion_laboral_id')
         order by (v_pmap->(e->>'personal_id')->>'rk')::int, e->>'fecha_inicio', e->>'registro_pago_id'), '[]')
    into f_esq
    from jsonb_array_elements(cc->'esquemas') e
    left join public.clasificaciones_personal cl on cl.id = (e->>'clasificacion_id')::uuid
    left join public.empresas_registros_patronales erp on erp.id = (e->>'registro_patronal_id')::uuid;

  -- ===== Incidencias =====
  select coalesce(jsonb_agg(jsonb_build_array(
           v_pmap->(d->>'personal_id')->>'ni', v_pmap->(d->>'personal_id')->>'nom', d->>'fecha', d->>'codigo',
           case d->>'codigo' when 'F' then 'Falta' when 'I' then 'Incapacidad' when 'D' then 'Descanso' when 'V' then 'Vacaciones' when 'P' then 'Permiso' end,
           public.inc__exp_t(c->>'proyecto'), public.inc__exp_t(c->>'centro_costo'),
           v_hmap->(d->>'hoja_id')->>'tipo', v_hmap->(d->>'hoja_id')->>'version', d->>'personal_id', d->>'hoja_id', pe.id::text)
         order by (v_pmap->(d->>'personal_id')->>'rk')::int, d->>'fecha', d->>'hoja_id'), '[]')
    into f_inc
    from jsonb_array_elements(cc->'dias') d
    left join lateral (select z from jsonb_array_elements(coalesce(v_dmap->(d->>'personal_id')->'celdas', '[]')) z
                        where z->>'fecha' = d->>'fecha' and z->>'hoja_id' = d->>'hoja_id' limit 1) cz(c) on true;

  -- ===== Cantidades (sin conceptos de unidad «importe»: su cantidad es dinero) =====
  select coalesce(jsonb_agg(jsonb_build_array(
           v_pmap->(q->>'personal_id')->>'ni', v_pmap->(q->>'personal_id')->>'nom', q->>'fecha',
           public.inc__exp_t(v_kmap->(q->>'concepto_id')->>'abrev'), v_kmap->(q->>'concepto_id')->>'unidad',
           public.inc__exp_num((q->>'cantidad')::numeric), q->>'tipo_linea',
           v_hmap->(q->>'hoja_id')->>'tipo', v_hmap->(q->>'hoja_id')->>'version', q->>'personal_id', q->>'concepto_id', q->>'hoja_id', pe.id::text)
         order by (v_pmap->(q->>'personal_id')->>'rk')::int, q->>'fecha', q->>'concepto_id', q->>'hoja_id', q->>'tipo_linea'), '[]')
    into f_can
    from jsonb_array_elements(cc->'cantidades') q
   where v_kmap->(q->>'concepto_id')->>'unidad' <> 'importe';
  -- V-3: concepto de unidad «importe» con modo «sin_importe»: su dinero no tendría línea de importe.
  select coalesce(jsonb_agg(distinct v_kmap->(q->>'concepto_id')->>'nombre'), '[]') into v_conf
    from jsonb_array_elements(cc->'cantidades') q
   where v_kmap->(q->>'concepto_id')->>'unidad' = 'importe' and v_kmap->(q->>'concepto_id')->>'modo' = 'sin_importe';

  -- ===== Importes =====
  select coalesce(jsonb_agg(jsonb_build_array(
           v_pmap->(i->>'personal_id')->>'ni', v_pmap->(i->>'personal_id')->>'nom',
           public.inc__exp_t(v_kmap->(i->>'concepto_id')->>'abrev'),
           case when v_kmap->(i->>'concepto_id')->>'tipo' = 'descuento' then 'deduccion' else 'percepcion' end,
           public.inc__exp_t(cl.nombre), i->>'modalidad',
           case when i->>'estado' = 'decidido' then public.inc__exp_imp((i->>'final')::numeric) end,
           v_hmap->(i->>'hoja_id')->>'tipo', v_hmap->(i->>'hoja_id')->>'version',
           i->>'personal_id', i->>'concepto_id', i->>'hoja_id', i->>'relacion_laboral_id', i->>'registro_pago_id', pe.id::text)
         || case when v_pre then jsonb_build_array(i->>'estado', case when i->>'estado' = 'por_decidir' then ii.origen end,
                                                   case when i->>'estado' = 'por_decidir' then public.inc__exp_imp(ii.sugerido) end) else '[]'::jsonb end
         order by (v_pmap->(i->>'personal_id')->>'rk')::int, i->>'concepto_id', i->>'hoja_id', i->>'relacion_laboral_id' nulls first, i->>'registro_pago_id' nulls first), '[]')
    into f_imp
    from jsonb_array_elements(cc->'importes') i
    left join public.inc_versiones v on v.hoja_id = (i->>'hoja_id')::uuid and v.numero = (v_hmap->(i->>'hoja_id')->>'version')::int
    left join public.inc_importes ii on ii.version_id = v.id and ii.personal_id = (i->>'personal_id')::uuid and ii.concepto_id = (i->>'concepto_id')::uuid
          and ii.relacion_laboral_id is not distinct from (i->>'relacion_laboral_id')::uuid and ii.registro_pago_id is not distinct from (i->>'registro_pago_id')::uuid
    left join public.personal_registros_pago rp on rp.id = (i->>'registro_pago_id')::uuid
    left join public.clasificaciones_personal cl on cl.id = rp.clasificacion_id
   where i->>'estado' = 'decidido' or (v_pre and i->>'estado' = 'por_decidir');
  select count(*) filter (where i->>'estado' = 'por_decidir') into v_pd_imp from jsonb_array_elements(cc->'importes') i;
  select count(*) filter (where d->>'estado' = 'por_decidir') into v_pd_des from jsonb_array_elements(cc->'descuentos') d;

  -- ===== Descuentos (descuento del periodo + informativos) =====
  select coalesce(jsonb_agg(fila order by clase, rk, cred, des), '[]') into f_des from (
    select 'descuento' clase, (v_pmap->(d->>'personal_id')->>'rk')::int rk, d->>'credito_id' cred, d->>'descuento_id' des,
           jsonb_build_array('descuento', v_pmap->(d->>'personal_id')->>'ni', v_pmap->(d->>'personal_id')->>'nom', c.tipo,
             public.inc__exp_t(public.cred_etiqueta(c)), public.inc__exp_t(c.referencia),
             case when d->>'estado' = 'decidido' then public.inc__exp_imp((d->>'final')::numeric) end,
             null, null, null, null, d->>'personal_id', d->>'credito_id', d->>'descuento_id')
           || case when v_pre then jsonb_build_array(d->>'estado', case when d->>'estado' = 'por_decidir' then public.inc__exp_imp(cd.sugerido) end) else '[]'::jsonb end fila
      from jsonb_array_elements(cc->'descuentos') d
      join public.cred_creditos c on c.id = (d->>'credito_id')::uuid
      left join public.cred_descuentos cd on cd.id = (d->>'descuento_id')::uuid
     where d->>'estado' = 'decidido' or v_pre
    union all
    select 'informativo', (v_pmap->(n->>'personal_id')->>'rk')::int, n->>'credito_id', null,
           jsonb_build_array('informativo', v_pmap->(n->>'personal_id')->>'ni', v_pmap->(n->>'personal_id')->>'nom', n->>'tipo',
             public.inc__exp_t(public.cred_etiqueta(c)), public.inc__exp_t(c.referencia), null,
             n->>'infonavit_tipo', public.inc__exp_num((n->>'infonavit_valor')::numeric), n->>'pension_forma', public.inc__exp_num((n->>'pension_valor')::numeric),
             n->>'personal_id', n->>'credito_id', null)
           || case when v_pre then jsonb_build_array(null, null) else '[]'::jsonb end
      from jsonb_array_elements(cc->'informativos') n
      join public.cred_creditos c on c.id = (n->>'credito_id')::uuid) x;

  -- ===== Movimientos =====
  select coalesce(jsonb_agg(jsonb_build_array(
           v_pmap->(m->>'personal_id')->>'ni', v_pmap->(m->>'personal_id')->>'nom', m->>'tipo', m->>'fecha_efectiva', public.inc__exp_t(m->>'causa'),
           m->>'personal_id', m->>'evento_id')
         order by (v_pmap->(m->>'personal_id')->>'rk')::int, m->>'fecha_efectiva', m->>'tipo', m->>'evento_id'), '[]')
    into f_mov from jsonb_array_elements(cc->'movimientos') m;

  -- ===== Catálogos: solo valores usados en el archivo =====
  select coalesce(jsonb_agg(jsonb_build_array(cat, clave, abrev, nom, tip, uni, modo, nat, null, null) order by cat collate "C", clave collate "C"), '[]')
    into f_cat from (
    select distinct 'concepto' cat, k.id::text clave, public.inc__exp_t(k.abreviatura) abrev, public.inc__exp_t(k.nombre) nom, k.tipo tip, k.unidad uni, k.modo,
           case when k.tipo = 'descuento' then 'deduccion' else 'percepcion' end nat
      from public.inc_conceptos k
     where k.id in (select (r->>10)::uuid from jsonb_array_elements(f_can) r union select (r->>10)::uuid from jsonb_array_elements(f_imp) r)
    union
    select distinct 'codigo_dia', r->>3, r->>3, r->>4, null, null, null, null from jsonb_array_elements(f_inc) r
    union
    select distinct 'tipo_credito', r->>3, null,
           case r->>3 when 'infonavit' then 'INFONAVIT' when 'fonacot' then 'FONACOT' when 'prestamo' then 'Préstamo' when 'anticipo' then 'Anticipo'
                      when 'pension' then 'Pensión alimenticia' else 'Otro' end, null, null, null, null from jsonb_array_elements(f_des) r
    union
    select distinct 'tipo_movimiento', r->>2, null,
           case r->>2 when 'ingreso' then 'Ingreso' when 'reingreso' then 'Reingreso' when 'baja' then 'Baja'
                      when 'modificacion_salario' then 'Modificación de salario' when 'cambio_esquema_pago' then 'Cambio de esquema de pago'
                      when 'cambio_puesto' then 'Cambio de puesto' when 'cambio_jefe' then 'Cambio de jefe' when 'cambio_organizacion' then 'Cambio de organización'
                      when 'cambio_registro_patronal' then 'Cambio de registro patronal' when 'cambio_empresa' then 'Cambio de empresa'
                      when 'correccion_datos' then 'Corrección de datos' else r->>2 end, null, null, null, null from jsonb_array_elements(f_mov) r
    union
    select distinct 'clasificacion', cl.id::text, null, public.inc__exp_t(cl.nombre), null, null, null, null
      from public.clasificaciones_personal cl
     where cl.id in (select (e->>'clasificacion_id')::uuid from jsonb_array_elements(cc->'esquemas') e
                     union select rp.clasificacion_id from public.personal_registros_pago rp where rp.id in (select (r->>13)::uuid from jsonb_array_elements(f_imp) r))) c;

  -- ===== Totales de control (diseño §6) =====
  select jsonb_build_object(
    'personas', jsonb_array_length(f_per) = coalesce((dd->'totales'->>'personas')::int, 0),
    'dias', coalesce((select jsonb_object_agg(cod, n) from (select r->>3 cod, count(*) n from jsonb_array_elements(f_inc) r group by 1) x), '{}')
            = coalesce(dd->'totales'->'dias', '{}'),
    'cantidades', not exists (
       select 1 from (
         select cid, sum(t) t from (
           select r->>10 cid, (r->>5)::numeric t from jsonb_array_elements(f_can) r
           union all select key, -(value::text)::numeric from jsonb_each(coalesce(dd->'totales'->'cantidades', '{}'))
            where v_kmap->key->>'unidad' <> 'importe') y group by cid) z where t <> 0),
    'importes', not exists (
       select 1 from (
         select cid, mods, sum(t) t from (
           select r->>10 cid, coalesce(r->>5, 'sin_modalidad') mods, (r->>6)::numeric t from jsonb_array_elements(f_imp) r where r->>6 is not null
           union all select k1.key, k2.key, -(k2.value::text)::numeric
             from jsonb_each(coalesce(dd->'totales'->'importes', '{}')) k1, jsonb_each(k1.value) k2) y group by cid, mods) z where t <> 0),
    'descuentos', not exists (
       select 1 from (
         select tipo, sum(t) t from (
           select r->>3 tipo, (r->>6)::numeric t from jsonb_array_elements(f_des) r where r->>0 = 'descuento' and r->>6 is not null
           union all select key, -(value::text)::numeric from jsonb_each(coalesce(dd->'totales'->'descuentos', '{}'))) y group by tipo) z where t <> 0),
    -- 25-nov: los faltantes de importe del preliminar se arman desde las líneas (para distinguir el esquema);
    -- deben ser exactamente tantos como los del concentrado, o el reporte no se genera (BP3).
    'faltantes', not v_pre or (select count(*) from jsonb_array_elements(v_falt) x where x->>'tipo' = 'importe')
                             = (select count(*) from jsonb_array_elements(f_imp) r where r->>15 = 'por_decidir'))
    into v_ctrl;

  -- ===== Advertencias e informativos (A02–A10, I01–I03; A01 solo en el oficial) =====
  select coalesce(jsonb_agg(jsonb_build_object('codigo', codigo, 'nivel', nivel, 'hoja', hoja, 'pid', pid, 'ref', ref, 'msg', msg)
           order by case nivel when 'advertencia' then 1 else 2 end, codigo, coalesce((v_pmap->pid->>'rk')::int, 0), ref collate "C"), '[]')
    into v_avisos from (
    select 'A01' codigo, 'advertencia' nivel, 'Resumen' hoja, null pid, y->>'hoja_id' ref,
           'Complemento posterior al procesamiento de ' || coalesce(y->>'coordinador', '—') || ' (v' || (y->>'version') || ', enviado ' ||
           to_char((y->>'enviada_en')::timestamptz at time zone 'America/Mexico_City', 'DD/MM/YYYY HH24:MI') || '): no se incluye en este periodo. Estado en Envíos: ' ||
           coalesce((select eb.estado from public.inc__envios_base(pe.empresa_id) eb where eb.hoja_id = (y->>'hoja_id')::uuid and eb.version_numero = eb.version_actual limit 1), '—') msg
      from jsonb_array_elements(dd->'hojas') y where (y->>'posterior')::boolean and not v_pre
    union all select 'A02', 'advertencia', 'Personas', key, null, 'Sin esquema de pago vigente en el periodo.' from jsonb_each(v_pmap) where (value->>'esq')::int = 0
    union all select 'A03', 'advertencia', 'Personas', key, null, 'Sin días vigentes en el periodo.' from jsonb_each(v_pmap) where (value->>'dias')::int = 0
    union all select 'A04', 'advertencia', 'Personas', key, null, 'Tiene ' || (value->>'rels') || ' relaciones laborales en el periodo.' from jsonb_each(v_pmap) where (value->>'rels')::int > 1
    union all select 'A05', 'advertencia', 'Personas', key, null, coalesce(value->>'nom', '—') || ' — sin número interno.' from jsonb_each(v_pmap) where value->>'ni' is null
    union all select 'A05', 'advertencia', 'Personas', key, null, coalesce(value->>'nom', '—') || ' — número interno repetido: ' || (value->>'ni') || '.'
      from jsonb_each(v_pmap) where value->>'ni' in (select value->>'ni' from jsonb_each(v_pmap) where value->>'ni' is not null group by 1 having count(*) > 1)
    union all select 'A06', 'advertencia', 'Importes', r->>9, r->>10, 'Importe decidido en 0 (' || coalesce(r->>2, '') || ').' from jsonb_array_elements(f_imp) r where r->>6 = '0.00'
    -- A07 (25-nov): solo percepciones fuera de un esquema bruto. Una deducción sin esquema NO es A07: el adaptador la
    -- dirige al único esquema fiscal (bruto) de la persona; si no hay exactamente uno, el destino es ambiguo (A11).
    union all select 'A07', 'advertencia', 'Importes', pid, null,
           'Tiene percepciones ' || string_agg(distinct case coalesce(mo, '') when 'neto' then 'en el esquema neto' when 'manual' then 'manuales'
                                                         else 'sin esquema' end, ', ')
           || ': no van a la nómina fiscal (esquema bruto).'
      from (select r->>9 pid, r->>5 mo from jsonb_array_elements(f_imp) r where r->>3 = 'percepcion' and coalesce(r->>5, '') <> 'bruto') x group by pid
    union all select 'A07', 'advertencia', 'Importes', r->>9, r->>10, 'La deducción ' || coalesce(r->>2, '') || ' está en el esquema ' || (r->>5) || ': no va a la nómina fiscal.'
      from jsonb_array_elements(f_imp) r where r->>3 = 'deduccion' and r->>5 is not null and r->>5 <> 'bruto'
    union all select 'A11', 'advertencia', 'Importes', r->>9, r->>10,
           'La deducción ' || coalesce(r->>2, '') || ' no tiene esquema y la persona tiene ' || n.nb || ' esquemas fiscales (bruto) en el periodo: el adaptador no podrá decidir el destino.'
      from jsonb_array_elements(f_imp) r
      cross join lateral (select count(*) nb from jsonb_array_elements(cc->'esquemas') e where e->>'personal_id' = r->>9 and e->>'modalidad' = 'bruto') n
     where r->>3 = 'deduccion' and r->>13 is null and n.nb <> 1
    union all select 'A08', 'advertencia', 'Descuentos', pid, null, 'Tiene un concepto de descuento en la hoja y un crédito con descuento en el periodo: revisa que no se descuente dos veces.'
      from (select r->>9 pid from jsonb_array_elements(f_imp) r where r->>3 = 'deduccion'
            intersect select r->>11 from jsonb_array_elements(f_des) r where r->>0 = 'descuento') x
    union all select 'A09', 'advertencia', 'Personas', y->>'personal_id', null, 'Aparece en una hoja pero no tiene relación laboral en el periodo.'
      from jsonb_array_elements(dd->'personas') y where (y->>'sin_relacion')::boolean
    union all select 'A10', 'advertencia', 'Incidencias', r->>9, r->>10, 'Código ' || (r->>3) || ' el ' || to_char((r->>2)::date, 'DD/MM/YYYY') || ', fecha en que no está vigente.'
      from jsonb_array_elements(f_inc) r
     where not exists (select 1 from public.relaciones_laborales rl where rl.personal_id = (r->>9)::uuid and rl.tenant_id = pe.tenant_id
                         and rl.empresa_id = pe.empresa_id and rl.estado <> 'anulada' and coalesce(rl.fecha_ingreso, '-infinity'::date) <= (r->>2)::date
                         and ((rl.estado = 'vigente' and rl.fecha_baja is null) or (r->>2)::date <= rl.fecha_baja))
    union all select 'I01', 'informativo', 'Descuentos', r->>11, r->>12, 'Crédito informativo (' || (r->>3) || '): lo calcula el sistema de nómina.'
      from jsonb_array_elements(f_des) r where r->>0 = 'informativo'
    union all select 'I02', 'informativo', 'Personas', y.key, o->>'hoja_id', 'Observación de ' || coalesce(o->>'coordinador', '—') || ': ' || public.inc__exp_t(o->>'texto')
      from jsonb_each(v_dmap) y, jsonb_array_elements(coalesce(y.value->'observaciones', '[]')) o
     where not coalesce((v_hmap->(o->>'hoja_id')->>'posterior')::boolean, true)
    union all select 'I03', 'informativo', 'Personas', key, null,
           concat_ws(' · ', case when value->>'alta' is not null then 'Alta el ' || to_char((value->>'alta')::date, 'DD/MM/YYYY') end,
                            case when value->>'baja' is not null then 'Baja el ' || to_char((value->>'baja')::date, 'DD/MM/YYYY') end)
      from jsonb_each(v_pmap) where value->>'alta' is not null or value->>'baja' is not null) x;

  -- ===== Validaciones (oficial) o Faltantes (preliminar) =====
  if v_pre then
    -- Faltantes del concentrado (texto de inc__faltantes_con_firma, sin cambios) con la persona a la que se refieren:
    -- el nombre al inicio del texto («Persona · …» en importes y descuentos; «Coordinador: …» en hojas y firmas),
    -- identificado solo si es único en el tenant. La firma de Nómina del periodo no es de una persona.
    select coalesce(jsonb_agg(fila order by o1, o2, o3 collate "C"), '[]') into f_val from (
      select 1 o1, x->>'tipo' o2, x->>'detalle' o3,
             jsonb_build_array(x->>'tipo', null, v_pmap->(pp.pid::text)->>'ni', public.inc__exp_t(pp.nom), pp.pid::text, null, public.inc__exp_t(x->>'detalle')) fila
        from jsonb_array_elements(v_falt) x
        left join lateral (
          select min(p.id::text)::uuid pid, min(p.nombre_completo) nom from public.personal p
           where p.tenant_id = pe.tenant_id
             and p.nombre_completo = case when x->>'tipo' in ('importe','descuento') then split_part(x->>'detalle', ' · ', 1) else split_part(x->>'detalle', ': ', 1) end
          having count(*) = 1) pp on true
       where x->>'tipo' <> 'importe'
      -- Importes por decidir, una fila por línea, con el esquema (clasificación / modalidad) para distinguir dos esquemas de la misma persona.
      union all select 1, 'importe', m, jsonb_build_array('importe', null, r->>0, r->>1, r->>9, r->>11, m)
        from jsonb_array_elements(f_imp) r
        left join public.inc_hojas h on h.id = (r->>11)::uuid
        left join public.personal co on co.id = h.coordinador_id
        cross join lateral (select public.inc__exp_t(coalesce(r->>1, '—') || ' · ' || coalesce(v_kmap->(r->>10)->>'nombre', r->>2)
             || case when r->>13 is not null then ' — ' || coalesce(r->>4, 'sin clasificación') || ' / ' || coalesce(r->>5, 'sin modalidad') else '' end || ': '
             || case r->>16 when 'sin_sueldo' then 'sin sueldo (captura el sueldo diario manual o escribe el importe)'
                            when 'por_asignar' then 'esquema de pago por asignar' else 'importe por decidir' end
             || ' — hoja de ' || coalesce(co.nombre_completo, '—')) m) mm
       where r->>15 = 'por_decidir'
      union all select 2, 'configuracion', n, jsonb_build_array('configuracion', null, null, null, null, null,
             'El concepto «' || n || '» captura importes pero está configurado «Sin importe»: su dinero no aparece en Importes. Revisa la configuración del concepto.')
        from jsonb_array_elements_text(v_conf) n
      union all select case a->>'nivel' when 'advertencia' then 3 else 4 end, a->>'codigo', coalesce(lpad(v_pmap->(a->>'pid')->>'rk', 8, '0'), '') || coalesce(a->>'ref', ''),
             jsonb_build_array(a->>'nivel', a->>'codigo', v_pmap->(a->>'pid')->>'ni', v_pmap->(a->>'pid')->>'nom', a->>'pid', a->>'ref', public.inc__exp_t(a->>'msg'))
        from jsonb_array_elements(v_avisos) a) z;
  else
    -- Orden (25-nov): advertencias, informativos y, al final, los ocho bloqueos superados como evidencia.
    select coalesce(jsonb_agg(fila order by o1, o2, o3 collate "C"), '[]') into f_val from (
      select case a->>'nivel' when 'advertencia' then 1 else 2 end o1, a->>'codigo' o2, coalesce(lpad(v_pmap->(a->>'pid')->>'rk', 8, '0'), '') || coalesce(a->>'ref', '') o3,
             jsonb_build_array(a->>'codigo', a->>'nivel', 'aviso', a->>'hoja', v_pmap->(a->>'pid')->>'ni', v_pmap->(a->>'pid')->>'nom', a->>'pid', a->>'ref', public.inc__exp_t(a->>'msg')) fila
        from jsonb_array_elements(v_avisos) a
      union all select 3, c, '', jsonb_build_array(c, 'bloqueo', case when c = 'B07' and v_estado <> 'procesado' then 'no_aplica' else 'superada' end,
                                                    null, null, null, null, null,
                                                    case when c = 'B07' and v_estado <> 'procesado' then 'No aplica: el periodo aún no ha sido procesado.' else m end)
        from (values ('B01','Firma de Nómina vigente.'), ('B02','Huella del concentrado igual a la firmada.'), ('B03','Sin importes por decidir.'),
                     ('B04','Sin descuentos por decidir.'), ('B05','Usuario con permiso en el tenant del periodo.'), ('B06','Totales de control iguales al concentrado.'),
                     ('B07','Sin cambios después del procesamiento.'), ('B08','Periodo listo o procesado.')) v(c, m)) z;
  end if;

  -- ===== Resumen (sin la sección «archivo», que agrega la función pública) =====
  v_ref := case when v_pre then h->>'total' else v_firma_h end;
  select coalesce(jsonb_agg(r order by o), '[]') into v_res from (
    select 1 o, jsonb_build_array('periodo', 'empresa', null, null, public.inc__exp_t(dd->'periodo'->>'empresa'), null) r
    union all select 2, jsonb_build_array('periodo', 'empresa_id', null, null, pe.empresa_id::text, null)
    union all select 3, jsonb_build_array('periodo', 'periodo_id', null, null, pe.id::text, null)
    union all select 4, jsonb_build_array('periodo', 'inicio', null, null, public.inc__exp_fecha(pe.inicio), null)
    union all select 5, jsonb_build_array('periodo', 'fin', null, null, public.inc__exp_fecha(pe.fin), null)
    union all select 6, jsonb_build_array('periodo', 'dias', null, null, (pe.fin - pe.inicio + 1)::text, 'dias')
    union all select 7, jsonb_build_array('periodo', 'estado', null, null, v_estado, null)
    union all select 8, jsonb_build_array('periodo', 'procesado_en', null, null, public.inc__exp_ts(pe.procesado_en), null)
    union all select 9, jsonb_build_array('firma', 'firma_estado', null, null, f->>'estado', null)
    union all select 10, jsonb_build_array('firma', 'firmado_por', null, null, public.inc__exp_t(v_firma_nom), null) where not v_pre
    union all select 11, jsonb_build_array('firma', 'firmado_en', null, null, public.inc__exp_ts(v_firma_en), null) where not v_pre
    union all select 12, jsonb_build_array('firma', 'huella_firma', null, null, v_firma_h, null) where not v_pre
    union all select 13, jsonb_build_array('firma', case when v_pre then 'huella_concentrado_actual' else 'huella_concentrado' end, null, null, h->>'total', null)
    union all select 20, jsonb_build_array('conteo', k, null, null, v::text, u) from (values
        ('personas', jsonb_array_length(f_per), 'personas'), ('esquemas', jsonb_array_length(f_esq), 'filas'),
        ('filas_incidencias', jsonb_array_length(f_inc), 'filas'), ('filas_cantidades', jsonb_array_length(f_can), 'filas'),
        ('filas_importes', jsonb_array_length(f_imp), 'filas'), ('filas_descuentos', jsonb_array_length(f_des), 'filas'),
        ('filas_movimientos', jsonb_array_length(f_mov), 'filas'),
        ('advertencias', (select count(*) from jsonb_array_elements(v_avisos) a where a->>'nivel' = 'advertencia')::int, 'filas')) t(k, v, u)
    union all select 21, jsonb_build_array('conteo', 'importes_por_decidir', null, null, v_pd_imp::text, 'filas') where v_pre
    union all select 22, jsonb_build_array('conteo', 'descuentos_por_decidir', null, null, v_pd_des::text, 'filas') where v_pre
    union all select 30, jsonb_build_array('total_dias', key, null, null, value::text, 'dias') from jsonb_each(coalesce(dd->'totales'->'dias', '{}'))
    union all select 31, jsonb_build_array('total_cantidades', v_kmap->key->>'abrev', key, null, public.inc__exp_num((value::text)::numeric), v_kmap->key->>'unidad')
      from jsonb_each(coalesce(dd->'totales'->'cantidades', '{}')) where v_kmap->key->>'unidad' <> 'importe'
    union all select 32, jsonb_build_array('total_importes', v_kmap->k1.key->>'abrev', k1.key, k2.key, public.inc__exp_imp((k2.value::text)::numeric), 'MXN')
      from jsonb_each(coalesce(dd->'totales'->'importes', '{}')) k1, jsonb_each(k1.value) k2
    union all select 33, jsonb_build_array('total_descuentos', key, null, null, public.inc__exp_imp((value::text)::numeric), 'MXN')
      from jsonb_each(coalesce(dd->'totales'->'descuentos', '{}'))) x;

  -- ===== Hojas de datos con su contrato de columnas (n = nombre, t = tipo, ro = solo lectura) =====
  v_hojas := jsonb_build_array(
    jsonb_build_object('entidad', 'Personas', 'nombre', v_px || 'Personas', 'filas', f_per, 'columnas', '[
      {"n":"numero_interno","t":"texto"},{"n":"nombre_completo","t":"texto"},{"n":"rfc","t":"texto"},{"n":"curp","t":"texto"},{"n":"nss","t":"texto"},
      {"n":"registro_patronal","t":"texto"},{"n":"fecha_ingreso","t":"fecha"},{"n":"fecha_baja","t":"fecha"},{"n":"alta_en_periodo","t":"fecha"},
      {"n":"baja_en_periodo","t":"fecha"},{"n":"dias_vigentes","t":"entero"},{"n":"relaciones_en_periodo","t":"entero"},{"n":"esquemas_en_periodo","t":"entero"},
      {"n":"proyecto","t":"texto"},{"n":"coordinadores","t":"texto"},{"n":"con_incidencias","t":"booleano"},{"n":"persona_id","t":"texto"},
      {"n":"relacion_laboral_id","t":"texto"}]'::jsonb),
    jsonb_build_object('entidad', 'Esquemas', 'nombre', v_px || 'Esquemas', 'filas', f_esq, 'columnas', '[
      {"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"clasificacion","t":"texto"},{"n":"modalidad","t":"texto"},
      {"n":"sueldo","t":"importe"},{"n":"dias_periodo","t":"numero"},{"n":"fecha_inicio","t":"fecha"},{"n":"fecha_fin","t":"fecha"},{"n":"activo","t":"booleano"},
      {"n":"registro_patronal","t":"texto"},{"n":"persona_id","t":"texto"},{"n":"registro_pago_id","t":"texto"},{"n":"relacion_laboral_id","t":"texto"}]'::jsonb),
    jsonb_build_object('entidad', 'Incidencias', 'nombre', v_px || 'Incidencias', 'filas', f_inc, 'columnas', '[
      {"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"fecha","t":"fecha"},{"n":"codigo","t":"texto"},
      {"n":"codigo_nombre","t":"texto"},{"n":"proyecto","t":"texto"},{"n":"centro_costo","t":"texto"},{"n":"hoja_tipo","t":"texto"},{"n":"version_hoja","t":"entero"},
      {"n":"persona_id","t":"texto"},{"n":"hoja_id","t":"texto"},{"n":"periodo_origen_id","t":"texto"}]'::jsonb),
    jsonb_build_object('entidad', 'Cantidades', 'nombre', v_px || 'Cantidades', 'filas', f_can, 'columnas', '[
      {"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"fecha","t":"fecha"},{"n":"concepto_clave","t":"texto","ro":true},
      {"n":"unidad","t":"texto"},{"n":"cantidad","t":"numero"},{"n":"tipo_linea","t":"texto"},{"n":"hoja_tipo","t":"texto"},{"n":"version_hoja","t":"entero"},
      {"n":"persona_id","t":"texto"},{"n":"concepto_id","t":"texto"},{"n":"hoja_id","t":"texto"},{"n":"periodo_origen_id","t":"texto"}]'::jsonb),
    jsonb_build_object('entidad', 'Importes', 'nombre', v_px || 'Importes', 'filas', f_imp, 'columnas', '[
      {"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"concepto_clave","t":"texto","ro":true},
      {"n":"naturaleza","t":"texto"},{"n":"clasificacion","t":"texto"},{"n":"modalidad","t":"texto"},{"n":"importe","t":"importe"},{"n":"hoja_tipo","t":"texto"},
      {"n":"version_hoja","t":"entero"},{"n":"persona_id","t":"texto"},{"n":"concepto_id","t":"texto"},{"n":"hoja_id","t":"texto"},
      {"n":"relacion_laboral_id","t":"texto"},{"n":"registro_pago_id","t":"texto"},{"n":"periodo_origen_id","t":"texto"}]'::jsonb
      || case when v_pre then '[{"n":"estado","t":"texto"},{"n":"motivo_pendiente","t":"texto"},{"n":"importe_sugerido","t":"importe"}]'::jsonb else '[]'::jsonb end),
    jsonb_build_object('entidad', 'Descuentos', 'nombre', v_px || 'Descuentos', 'filas', f_des, 'columnas', '[
      {"n":"clase","t":"texto"},{"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"tipo_credito","t":"texto"},
      {"n":"etiqueta","t":"texto"},{"n":"referencia_credito","t":"texto"},{"n":"importe","t":"importe"},{"n":"infonavit_tipo","t":"texto"},
      {"n":"infonavit_valor","t":"numero"},{"n":"pension_forma","t":"texto"},{"n":"pension_valor","t":"numero"},{"n":"persona_id","t":"texto"},
      {"n":"credito_id","t":"texto"},{"n":"descuento_id","t":"texto"}]'::jsonb
      || case when v_pre then '[{"n":"estado","t":"texto"},{"n":"importe_sugerido","t":"importe"}]'::jsonb else '[]'::jsonb end),
    jsonb_build_object('entidad', 'Movimientos', 'nombre', v_px || 'Movimientos', 'filas', f_mov, 'columnas', '[
      {"n":"numero_interno","t":"texto","ro":true},{"n":"nombre_completo","t":"texto","ro":true},{"n":"tipo","t":"texto"},{"n":"fecha_efectiva","t":"fecha"},
      {"n":"causa","t":"texto"},{"n":"persona_id","t":"texto"},{"n":"evento_id","t":"texto"}]'::jsonb),
    jsonb_build_object('entidad', 'Catalogos', 'nombre', v_px || 'Catálogos', 'filas', f_cat, 'columnas', '[
      {"n":"catalogo","t":"texto"},{"n":"clave_beehuman","t":"texto"},{"n":"abreviatura","t":"texto"},{"n":"nombre","t":"texto"},{"n":"tipo","t":"texto"},
      {"n":"unidad","t":"texto"},{"n":"modo","t":"texto"},{"n":"naturaleza","t":"texto"},{"n":"sistema_externo","t":"texto"},{"n":"clave_externa","t":"texto"}]'::jsonb));

  -- ===== Huellas (diseño §4.2, §4.3 y §12.5): sobre texto canónico, nunca sobre el .xlsx =====
  select public.inc__exp_linea(jsonb_build_array(v_fmt, '1.0')) || E'\n' ||
         public.inc__exp_linea(jsonb_build_array('periodo', pe.id::text, v_ref)) || E'\n' ||
         string_agg(
           public.inc__exp_linea(jsonb_build_array('#entidad', hj->>'entidad')) || E'\n' ||
           public.inc__exp_linea((select jsonb_agg(c->'n' order by o) from jsonb_array_elements(hj->'columnas') with ordinality z(c, o) where not coalesce((c->>'ro')::boolean, false))) || E'\n' ||
           coalesce((select string_agg(public.inc__exp_linea((select coalesce(jsonb_agg(e order by o2), '[]') from jsonb_array_elements(r) with ordinality y(e, o2)
                              where not coalesce((hj->'columnas'->(o2::int - 1)->>'ro')::boolean, false))) || E'\n', '' order by o1)
                       from jsonb_array_elements(hj->'filas') with ordinality w(r, o1)), ''), '' order by ho)
    into v_ser_d from jsonb_array_elements(v_hojas) with ordinality g(hj, ho);
  if not v_pre then
    select public.inc__exp_linea(jsonb_build_array(v_fmt, '1.0')) || E'\n' ||
           string_agg(
             public.inc__exp_linea(jsonb_build_array('#hoja', hj->>'nombre')) || E'\n' ||
             public.inc__exp_linea((select jsonb_agg(c->'n' order by o) from jsonb_array_elements(hj->'columnas') with ordinality z(c, o))) || E'\n' ||
             coalesce((select string_agg(public.inc__exp_linea(r) || E'\n', '' order by o1) from jsonb_array_elements(hj->'filas') with ordinality w(r, o1)), ''),
             '' order by ho)
      into v_ser_a from jsonb_array_elements(v_hojas) with ordinality g(hj, ho);
  end if;

  return jsonb_build_object(
    'modalidad', p_modalidad, 'formato', v_fmt, 'version_formato', '1.0',
    'periodo', jsonb_build_object('id', pe.id, 'tenant_id', pe.tenant_id, 'empresa_id', pe.empresa_id, 'empresa', dd->'periodo'->>'empresa',
                                  'inicio', pe.inicio, 'fin', pe.fin, 'procesado_en', pe.procesado_en),
    'estado', v_estado, 'firma_estado', f->>'estado', 'huella_firma', v_firma_h, 'huella_concentrado', h->>'total',
    'huella_procesado', v_proc.huella->>'total', 'importes_por_decidir', v_pd_imp, 'descuentos_por_decidir', v_pd_des,
    'controles', v_ctrl, 'config_importe_sin_importe', v_conf,
    'resumen', v_res, 'hojas', v_hojas,
    'validaciones', jsonb_build_object('entidad', case when v_pre then 'Faltantes' else 'Validaciones' end,
       'nombre', v_px || case when v_pre then 'Faltantes' else 'Validaciones' end, 'filas', f_val,
       'columnas', case when v_pre then '[{"n":"tipo","t":"texto"},{"n":"codigo","t":"texto"},{"n":"numero_interno","t":"texto"},{"n":"nombre_completo","t":"texto"},{"n":"persona_id","t":"texto"},
                                           {"n":"referencia_id","t":"texto"},{"n":"mensaje","t":"texto"}]'::jsonb
                        else '[{"n":"codigo","t":"texto"},{"n":"nivel","t":"texto"},{"n":"resultado","t":"texto"},{"n":"hoja","t":"texto"},{"n":"numero_interno","t":"texto"},{"n":"nombre_completo","t":"texto"},
                               {"n":"persona_id","t":"texto"},{"n":"referencia_id","t":"texto"},{"n":"mensaje","t":"texto"}]'::jsonb end),
    'huella_datos_exportados', encode(sha256(convert_to(v_ser_d, 'UTF8')), 'hex'),
    'huella_archivo', case when v_ser_a is null then null else encode(sha256(convert_to(v_ser_a, 'UTF8')), 'hex') end);
end $$;

-- Nombre de archivo seguro: sin acentos ni espacios.
create function public.inc__exp_slug(t text) returns text language sql immutable set search_path to '' as $$
  select coalesce(nullif(trim(both '-' from regexp_replace(regexp_replace(normalize(coalesce(t, ''), NFD), '[̀-ͯ]', '', 'g'), '[^A-Za-z0-9]+', '-', 'g')), ''), 'empresa') $$;

-- Registro del evento y armado final (común a las dos modalidades).
create function public.inc__exportacion_registrar(d jsonb) returns jsonb
language plpgsql security definer set search_path to '' as $$
declare v_pre boolean := d->>'modalidad' = 'preliminar'; n int; v_ant text; v_ahora timestamptz := now(); v_nombre text; v_arch jsonb; v_filas jsonb;
begin
  perform pg_advisory_xact_lock(hashtext('inc_exportacion:' || (d->'periodo'->>'id')));
  select count(*) + 1 into n from public.inc_eventos e
   where e.periodo_id = (d->'periodo'->>'id')::uuid and e.tipo = 'exportacion' and e.huella->>'modalidad' = d->>'modalidad'
     and (v_pre or e.huella->>'huella_firma' = d->>'huella_firma');
  if not v_pre then
    select e.huella->>'huella_datos_exportados' into v_ant from public.inc_eventos e
     where e.periodo_id = (d->'periodo'->>'id')::uuid and e.tipo = 'exportacion' and e.huella->>'modalidad' = 'oficial'
       and e.huella->>'huella_firma' = d->>'huella_firma' order by e.creado_en desc limit 1;
  end if;
  select jsonb_object_agg(hj->>'entidad', jsonb_array_length(hj->'filas')) into v_filas from jsonb_array_elements(d->'hojas') hj;
  insert into public.inc_eventos (tenant_id, periodo_id, tipo, usuario_id, nombre, huella)
  values ((d->'periodo'->>'tenant_id')::uuid, (d->'periodo'->>'id')::uuid, 'exportacion', auth.uid(), public.inc_nombre_usuario(),
          jsonb_strip_nulls(jsonb_build_object('modalidad', d->>'modalidad', 'formato', d->>'formato', 'version_formato', d->>'version_formato',
            'estado_periodo', d->>'estado', 'firma_estado', d->>'firma_estado', 'huella_firma', case when v_pre then null else d->>'huella_firma' end,
            'huella_concentrado', d->>'huella_concentrado', 'huella_datos_exportados', d->>'huella_datos_exportados',
            'huella_archivo', d->>'huella_archivo', 'exportacion_numero', n, 'filas', v_filas,
            'por_decidir', case when v_pre then (d->>'importes_por_decidir')::int + (d->>'descuentos_por_decidir')::int end)));
  v_nombre := case when v_pre
    then 'PRELIMINAR_BeeHuman_' || public.inc__exp_slug(d->'periodo'->>'empresa') || '_' || (d->'periodo'->>'inicio') || '_' || (d->'periodo'->>'fin') || '_'
         || to_char(v_ahora at time zone 'America/Mexico_City', 'YYYYMMDD-HH24MI') || '.xlsx'
    else 'BeeHuman_' || public.inc__exp_slug(d->'periodo'->>'empresa') || '_' || (d->'periodo'->>'inicio') || '_' || (d->'periodo'->>'fin') || '_exp-' || n || '.xlsx' end;
  v_arch := case when v_pre then jsonb_build_array(
      jsonb_build_array('aviso', 'estado_documento', null, null, 'PRELIMINAR — NO AUTORIZADO. Los datos pueden cambiar mientras los coordinadores y RH continúan trabajando. No usar para alimentar sistemas de nómina.', null))
    else '[]'::jsonb end
    || jsonb_build_array(
      jsonb_build_array('archivo', 'formato', null, null, d->>'formato', null),
      jsonb_build_array('archivo', 'version_formato', null, null, d->>'version_formato', null),
      jsonb_build_array('archivo', 'generado_en', null, null, public.inc__exp_ts(v_ahora), null),
      jsonb_build_array('archivo', 'generado_por', null, null, public.inc_nombre_usuario(), null),
      jsonb_build_array('archivo', 'exportacion_numero', null, null, n::text, null),
      jsonb_build_array('archivo', 'huella_datos_exportados', null, null, d->>'huella_datos_exportados', null))
    || case when v_pre then '[]'::jsonb else jsonb_build_array(
      jsonb_build_array('archivo', 'huella_datos_exportados_anterior', null, null, v_ant, null),
      jsonb_build_array('archivo', 'huella_archivo', null, null, d->>'huella_archivo', null)) end;
  return jsonb_build_object('modalidad', d->>'modalidad', 'formato', d->>'formato', 'version_formato', d->>'version_formato',
    'nombre_archivo', v_nombre, 'exportacion_numero', n, 'generado_en', public.inc__exp_ts(v_ahora),
    'huella_datos_exportados', d->>'huella_datos_exportados', 'huella_archivo', d->>'huella_archivo',
    'huella_datos_exportados_anterior', v_ant, 'estado', d->>'estado',
    'resumen', jsonb_build_object('entidad', 'Resumen', 'nombre', case when v_pre then 'PRELIM Resumen' else 'Resumen' end,
       'columnas', '[{"n":"seccion","t":"texto"},{"n":"clave","t":"texto"},{"n":"concepto_id","t":"texto"},{"n":"modalidad","t":"texto"},{"n":"valor","t":"mixto"},{"n":"unidad","t":"texto"}]'::jsonb,
       'filas', v_arch || (d->'resumen')),
    'hojas', d->'hojas', 'validaciones', d->'validaciones');
end $$;

-- ---------- Excel canónico oficial ----------
create function public.inc_exportacion_canonica(p_periodo uuid) returns jsonb
language plpgsql security definer set search_path to '' as $$
declare d jsonb; c jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso. (B05)'; end if;
  d := public.inc__exportacion_datos(p_periodo, 'oficial');          -- UNA sentencia: la instantánea de toda la lectura
  if d->>'estado' = 'procesado' and d->>'huella_procesado' is not null and d->>'huella_procesado' <> d->>'huella_concentrado' then
    raise exception 'BeeHuman: el periodo se procesó y después cambió. La versión 1 no puede reproducir lo procesado. (B07)';
  end if;
  if d->>'estado' = 'preliminar' then
    raise exception 'BeeHuman: el periodo sigue en preparación. Puedes descargar el reporte preliminar, pero el Excel canónico oficial estará disponible cuando el periodo esté listo y tenga la firma de Nómina vigente. (B08)';
  end if;
  if d->>'firma_estado' is distinct from 'vigente' then
    raise exception 'BeeHuman: el periodo no tiene una firma de Nómina vigente. Firma el concentrado para exportar. (B01)';
  end if;
  if d->>'huella_firma' is distinct from d->>'huella_concentrado' then
    raise exception 'BeeHuman: el concentrado cambió después de la firma. Vuelve a firmar. (B02)';
  end if;
  if (d->>'importes_por_decidir')::int > 0 then raise exception 'BeeHuman: hay % importes por decidir. (B03)', d->>'importes_por_decidir'; end if;
  if (d->>'descuentos_por_decidir')::int > 0 then raise exception 'BeeHuman: hay % descuentos por decidir. (B04)', d->>'descuentos_por_decidir'; end if;
  c := d->'controles';
  if not ((c->>'personas')::boolean and (c->>'dias')::boolean and (c->>'cantidades')::boolean and (c->>'importes')::boolean and (c->>'descuentos')::boolean) then
    raise exception 'BeeHuman: el archivo no cuadra con el concentrado firmado; no se generó. (B06: %)', c::text;
  end if;
  if jsonb_array_length(d->'config_importe_sin_importe') > 0 then
    raise exception 'BeeHuman: el archivo no cuadra con el concentrado firmado; no se generó. El concepto «%» captura importes pero está configurado «Sin importe». (B06)',
      (select string_agg(x, '», «') from jsonb_array_elements_text(d->'config_importe_sin_importe') x);
  end if;
  return public.inc__exportacion_registrar(d);
end $$;

-- ---------- Reporte preliminar de acumulado ----------
create function public.inc_exportacion_preliminar(p_periodo uuid) returns jsonb
language plpgsql security definer set search_path to '' as $$
declare d jsonb; c jsonb;
begin
  if not public.tiene_rol('administrador','nomina') then raise exception 'BeeHuman: sin permiso. (BP1)'; end if;
  d := public.inc__exportacion_datos(p_periodo, 'preliminar');
  if d->>'estado' <> 'preliminar' then
    if d->>'estado' = 'procesado' and d->>'huella_procesado' is not null and d->>'huella_procesado' <> d->>'huella_concentrado' then
      raise exception 'BeeHuman: el periodo se procesó y después cambió; no hay exportación disponible en la versión 1. (BP2)';
    end if;
    raise exception 'BeeHuman: el periodo ya está %: descarga el Excel canónico oficial. (BP2)', d->>'estado';
  end if;
  c := d->'controles';
  if not ((c->>'personas')::boolean and (c->>'dias')::boolean and (c->>'cantidades')::boolean and (c->>'importes')::boolean and (c->>'descuentos')::boolean and (c->>'faltantes')::boolean) then
    raise exception 'BeeHuman: el reporte no cuadra con el concentrado; no se generó. (BP3: %)', c::text;
  end if;
  return public.inc__exportacion_registrar(d);
end $$;

-- ---------- Permisos ----------
revoke all on function public.inc__exp_t(text), public.inc__exp_imp(numeric), public.inc__exp_num(numeric), public.inc__exp_fecha(date),
  public.inc__exp_ts(timestamptz), public.inc__exp_linea(jsonb), public.inc__exp_slug(text),
  public.inc__exportacion_datos(uuid, text), public.inc__exportacion_registrar(jsonb) from public, anon, authenticated;
revoke all on function public.inc_exportacion_canonica(uuid), public.inc_exportacion_preliminar(uuid) from public, anon;
grant execute on function public.inc_exportacion_canonica(uuid), public.inc_exportacion_preliminar(uuid) to authenticated;
commit;
