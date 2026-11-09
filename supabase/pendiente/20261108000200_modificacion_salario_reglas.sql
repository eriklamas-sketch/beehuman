-- =====================================================================
-- BeeHuman · Modificación de salario (07): reglas y mensajes (8-nov-2026)
-- Propuesta aprobada: claude/Historia-laboral-y-modificacion-salarial-propuesta.md (D2, D3, D4)
--
-- 1. laboral_modificar_salario: si el nuevo SBC es MENOR que el vigente, el
--    motivo es obligatorio (D3). Sin SBC vigente (dato migrado) no se compara.
-- 2. laboral_validar_sbc: misma regla de siempre (tope 25 UMA a la fecha
--    efectiva, D2; piso = salario mínimo de la zona del RP, D4), con mensajes
--    claros e importes con separador de miles. Cada rechazo lleva un hint
--    (sbc_tope / sbc_minimo) para que la pantalla ofrezca la corrección.
-- No cambia tablas, firmas, permisos ni datos. No toca eventos ni movimientos
-- IDSE existentes: solo aplica a movimientos nuevos.
-- Las definiciones originales de ESTE entorno se guardan en
-- respaldo.modificacion_salario_20261108; la reversión las restaura desde ahí.
-- Reversión: reversion/20261108000200_reversion_modificacion_salario_reglas.sql
-- =====================================================================
begin;

do $$
declare d text;
begin
  if to_regclass('respaldo.modificacion_salario_20261108') is not null then
    raise exception 'BeeHuman: la migración modificacion_salario_reglas ya está aplicada.';
  end if;
  d := pg_get_functiondef(to_regprocedure('public.laboral_modificar_salario(uuid,date,numeric,numeric,text,text)'));
  if d is null or position('perform public.laboral_validar_sbc(p_sbc, p_fecha_efectiva, r.registro_patronal_id);' in d) = 0
     or position('''07'', p_fecha_efectiva, p_sbc' in d) = 0 then
    raise exception 'BeeHuman: laboral_modificar_salario no tiene la forma esperada (migración de eventos); no se aplica.';
  end if;
  d := pg_get_functiondef(to_regprocedure('public.laboral_validar_sbc(numeric,date,uuid)'));
  if d is null or position('round(v_uma * 25, 2)' in d) = 0 then
    raise exception 'BeeHuman: laboral_validar_sbc no tiene la forma esperada; no se aplica.';
  end if;
end $$;

create schema if not exists respaldo;
create table respaldo.modificacion_salario_20261108 (
  objeto text primary key, original text not null, md5_aplicada text, guardado_en timestamptz not null default now());
insert into respaldo.modificacion_salario_20261108 (objeto, original)
select f, pg_get_functiondef(to_regprocedure(f))
  from unnest(array['public.laboral_modificar_salario(uuid,date,numeric,numeric,text,text)',
                    'public.laboral_validar_sbc(numeric,date,uuid)']) f;
revoke all on table respaldo.modificacion_salario_20261108 from public, anon, authenticated;

-- Importe con separador de miles y 2 decimales para los mensajes.
create function public.laboral_importe_texto(p numeric) returns text
language sql immutable set search_path to '' as $$
  select '$' || btrim(to_char(p, 'FM999,999,999,990.00'));
$$;
revoke all on function public.laboral_importe_texto(numeric) from public, anon, authenticated;

create or replace function public.laboral_validar_sbc(p_sbc numeric, p_fecha date, p_registro_patronal_id uuid) returns void
language plpgsql stable security definer set search_path to '' as $$
declare v_uma numeric; v_sm numeric; v_zona text; v_tope numeric;
begin
  if p_sbc is null or p_registro_patronal_id is null then return; end if;
  select zona_salario_minimo into v_zona from public.empresas_registros_patronales where id = p_registro_patronal_id;
  v_uma := public.parametro_vigente('UMA_DIARIA', p_fecha);
  v_sm  := public.parametro_vigente(case when v_zona = 'zlfn' then 'SALARIO_MINIMO_ZLFN' else 'SALARIO_MINIMO_GENERAL' end, p_fecha);
  v_tope := round(v_uma * 25, 2);
  -- Tope (LSS art. 28): el SBC no puede rebasar 25 UMA de la fecha efectiva.
  if v_uma is not null and p_sbc > v_tope then
    raise exception 'BeeHuman: el SBC % rebasa el tope de 25 UMA (%) vigente al %. Usa el tope como SBC y, si aplica, registra el salario diario integrado real como SDI.',
      public.laboral_importe_texto(p_sbc), public.laboral_importe_texto(v_tope), to_char(p_fecha, 'DD/MM/YYYY')
      using hint = 'sbc_tope';
  end if;
  -- Piso: salario mínimo de la zona del RP. Aplica también a jornada y semana
  -- reducidas (RACERF art. 62: si resulta inferior, se ajusta al mínimo).
  if v_sm is not null and p_sbc < v_sm then
    raise exception 'BeeHuman: el SBC % es menor al salario mínimo % (%) vigente al %. Aun con jornada o semana reducida, el SBC se ajusta al mínimo.',
      public.laboral_importe_texto(p_sbc),
      case when v_zona = 'zlfn' then 'de la zona libre de la frontera norte' else 'general' end,
      public.laboral_importe_texto(v_sm), to_char(p_fecha, 'DD/MM/YYYY')
      using hint = 'sbc_minimo';
  end if;
end $$;

create or replace function public.laboral_modificar_salario(p_relacion_id uuid, p_fecha_efectiva date, p_sbc numeric,
  p_sdi numeric default null, p_tipo_salario text default null, p_motivo text default null)
returns uuid
language plpgsql security definer set search_path to '' as $$
declare
  v_tenant uuid := public.laboral_exigir_rol(array['administrador','nomina']);
  r record; v_ev uuid; v_ultima date;
begin
  select * into r from public.relaciones_laborales where id = p_relacion_id and tenant_id = v_tenant for update;
  if not found or not public.en_alcance_persona(r.personal_id) then raise exception 'BeeHuman: relación laboral no encontrada.'; end if;
  if r.estado <> 'vigente' then raise exception 'BeeHuman: la relación laboral no está vigente.'; end if;
  if p_fecha_efectiva is null or p_sbc is null or p_sbc <= 0 then
    raise exception 'BeeHuman: la fecha efectiva y el nuevo SBC son obligatorios.';
  end if;
  if r.fecha_ingreso is null or p_fecha_efectiva < r.fecha_ingreso then
    raise exception 'BeeHuman: la modificación no puede ser anterior al ingreso de la relación.';
  end if;
  -- orden cronológico: no se intercala una modificación antes de la última
  -- vigente (una corrección histórica requerirá su propio procedimiento)
  select max(fecha_efectiva) into v_ultima from public.eventos_laborales
   where relacion_laboral_id = p_relacion_id and estado = 'vigente' and tipo = 'modificacion_salario';
  if v_ultima is not null and p_fecha_efectiva <= v_ultima then
    raise exception 'BeeHuman: la modificación debe ser posterior a la última modificación de salario vigente (%).', v_ultima;
  end if;
  if p_sbc is not distinct from r.sbc and coalesce(p_tipo_salario, r.tipo_salario) is not distinct from r.tipo_salario then
    raise exception 'BeeHuman: el SBC no cambia.';
  end if;
  -- D3: una disminución del SBC requiere justificación (sin SBC vigente no se compara).
  if r.sbc is not null and p_sbc < r.sbc and length(btrim(coalesce(p_motivo, ''))) < 5 then
    raise exception 'BeeHuman: el nuevo SBC (%) es menor que el vigente (%). Escribe la justificación en el motivo (al menos 5 caracteres).',
      public.laboral_importe_texto(p_sbc), public.laboral_importe_texto(r.sbc) using hint = 'sbc_menor_motivo';
  end if;
  perform public.laboral_validar_sbc(p_sbc, p_fecha_efectiva, r.registro_patronal_id);

  perform set_config('beehuman.laboral', 'on', true);
  insert into public.eventos_laborales (tenant_id, personal_id, relacion_laboral_id, tipo, fecha_efectiva, motivo,
    valores_anteriores, valores_nuevos, origen, creado_por)
  values (v_tenant, r.personal_id, p_relacion_id, 'modificacion_salario', p_fecha_efectiva, nullif(btrim(p_motivo), ''),
    jsonb_strip_nulls(jsonb_build_object('sbc', r.sbc, 'sdi', r.sdi, 'tipo_salario', r.tipo_salario)),
    jsonb_strip_nulls(jsonb_build_object('sbc', p_sbc, 'sdi', coalesce(p_sdi, p_sbc), 'tipo_salario', coalesce(nullif(p_tipo_salario, ''), r.tipo_salario))),
    'pantalla', auth.uid())
  returning id into v_ev;
  update public.relaciones_laborales set sbc = p_sbc, sdi = coalesce(p_sdi, p_sbc),
         tipo_salario = coalesce(nullif(p_tipo_salario, ''), tipo_salario), actualizado_por = auth.uid(), actualizado_en = now()
   where id = p_relacion_id;
  if r.registro_patronal_id is not null then
    insert into public.idse_movimientos (tenant_id, evento_id, relacion_laboral_id, registro_patronal_id, tipo_movimiento, fecha_movimiento, sbc)
    values (v_tenant, v_ev, p_relacion_id, r.registro_patronal_id, '07', p_fecha_efectiva, p_sbc);
  end if;
  perform public.laboral_sincronizar_persona(r.personal_id);
  perform set_config('beehuman.laboral', 'off', true);
  return v_ev;
end $$;

update respaldo.modificacion_salario_20261108 set md5_aplicada = md5(pg_get_functiondef(to_regprocedure(objeto)));

commit;
