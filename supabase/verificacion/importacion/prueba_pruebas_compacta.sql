do $imp$
declare
  res text[] := '{}'; b jsonb; acc jsonb; v_r jsonb; h0 text; h1 text; v_seq0 bigint; v_called0 boolean;
  t uuid := gen_random_uuid(); adm uuid := gen_random_uuid(); con uuid := gen_random_uuid();
  e1 uuid := gen_random_uuid(); e2 uuid := gen_random_uuid(); e3 uuid := gen_random_uuid(); rp1 uuid := gen_random_uuid(); rp2 uuid := gen_random_uuid();
  ci uuid := gen_random_uuid(); ce uuid := gen_random_uuid(); ps uuid := gen_random_uuid(); pq uuid := gen_random_uuid();
  filas jsonb; curps text[]; esq_esp int; t0 timestamptz; v_max numeric := 0; n1 int; n2 int; n3 int; n4 int; n5 int; n6 int;
begin
  select last_value, is_called into v_seq0, v_called0 from public.personal_empleado_id_seq;
  insert into auth.users (id, email) values (adm, 'imp-v2-admin@beehuman.invalid'), (con, 'imp-v2-consulta@beehuman.invalid');
  insert into public.tenants (id, nombre) values (t, 'IMP V2 PRUEBA');
  insert into public.usuarios_tenant (user_id, tenant_id, rol) values (adm, t, 'administrador'), (con, t, 'consulta');
  execute 'set local session_replication_role = replica';
  insert into public.empresas (id, tenant_id, nombre, activo) values (e1, t, 'IMPORTA NORTE DEMO', true), (e2, t, 'IMPORTA SUR DEMO', true), (e3, t, 'IMPORTA CENTRO DEMO', true);
  insert into public.empresas_registros_patronales (id, empresa_id, tenant_id, registro_patronal, activo) values (rp1, e1, t, 'A0000000001', true), (rp2, e2, t, 'B0000000002', true);
  insert into public.clasificaciones_personal (id, tenant_id, nombre, activo, requiere_rfc, requiere_curp, requiere_nss, requiere_cp_fiscal) values
    (ci, t, 'Base / IMSS', true, true, true, true, true), (ce, t, 'Efectivo', true, false, false, false, false);
  insert into public.periodicidades (id, tenant_id, nombre, dias_default) values (ps, t, 'Semanal', 7), (pq, t, 'Quincenal', 15);
  execute 'set local session_replication_role = origin';
  -- 450 filas como las arma la pantalla: 20 coordinadores + 430 coordinados por CURP del mismo archivo;
  -- NORTE y SUR con registro patronal (Base / IMSS, 1 de cada 4 con complemento en efectivo); CENTRO sin RP (efectivo).
  with g as (
    select i, (array[e1, e2, e3])[i % 3 + 1] emp, (array[rp1, rp2, null])[i % 3 + 1] rp,
           'PAFA' || lpad((80 + i % 20)::text, 2, '0') || lpad((1 + i % 12)::text, 2, '0') || lpad((1 + i % 28)::text, 2, '0') || 'HDF'
             || substr('BCDFGHJKLMNPQRSTVWXZ', 1 + i % 20, 1) || substr('BCDFGHJKLMNPQRSTVWXZ', 1 + (i / 20) % 20, 1) || 'X'
             || substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 1 + i / 400, 1) || (i % 10)::text curp
      from generate_series(0, 449) i)
  select jsonb_agg(jsonb_build_object('id', gen_random_uuid(), 'linea', i + 2,
           'coordinador_ref', case when i >= 20 then (select g2.curp from g g2 where g2.i = g.i % 20) end,
           'persona', jsonb_build_object('nombres', 'IMP' || i, 'primer_apellido', 'PRUEBA', 'segundo_apellido', 'FICTICIO' || i, 'nombre_completo', 'IMP' || i || ' PRUEBA FICTICIO' || i,
              'rfc', substr(curp, 1, 10) || substr(curp, 14, 2) || substr(curp, 17, 1), 'curp', curp, 'nss', lpad((90000000000 + i)::text, 11, '0'), 'cp_fiscal', lpad((10000 + i)::text, 5, '0'),
              'empresa_id', emp, 'registro_patronal_id', rp, 'tipo_empleado', 'Base', 'turno', 'Matutino'),
           'relacion', jsonb_build_object('empresa_id', emp, 'registro_patronal_id', rp, 'fecha_ingreso', '2025-' || lpad((1 + i % 12)::text, 2, '0') || '-' || lpad((1 + i % 28)::text, 2, '0'),
              'numero_interno', (1000 + i)::text, 'sdi', case when rp is not null then 350 end, 'tipo_trabajador', case when rp is not null then '1' end,
              'tipo_salario', case when rp is not null then '0' end, 'jornada', case when rp is not null then '0' end),
           'esquemas', case when rp is null then jsonb_build_array(jsonb_build_object('clasificacion_id', ce, 'periodicidad_id', ps, 'modalidad', 'neto', 'sueldo', 2500))
                            when i % 4 = 0 then jsonb_build_array(jsonb_build_object('clasificacion_id', ci, 'periodicidad_id', pq, 'modalidad', 'bruto', 'sueldo', 4100),
                                                                  jsonb_build_object('clasificacion_id', ce, 'periodicidad_id', pq, 'modalidad', 'neto', 'sueldo', 800))
                            else jsonb_build_array(jsonb_build_object('clasificacion_id', ci, 'periodicidad_id', ps, 'modalidad', 'bruto', 'sueldo', 3200)) end) order by i),
         array_agg(curp), sum(case when rp is not null and i % 4 = 0 then 2 else 1 end)
    into filas, curps, esq_esp from g;
  perform set_config('request.jwt.claims', json_build_object('sub', adm)::text, true);

  -- I1 simulación de 450: huella de 6 tablas (todos los tenants) + secuencia BEH antes y después
  select md5(string_agg(h, '|')) || ' seq=' || (select last_value from public.personal_empleado_id_seq) into h0 from (
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) h from public.personal x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.relaciones_laborales x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.personal_registros_pago x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.eventos_laborales x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.idse_movimientos x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.inc_asignaciones x) s;
  execute 'set local role authenticated';
  acc := '[]';
  for n1 in 0..8 loop acc := acc || public.imp_alta_personas((select jsonb_agg(v) from jsonb_array_elements(filas) with ordinality a(v, o) where o > n1 * 50 and o <= (n1 + 1) * 50), 'carga_inicial', false, curps); end loop;
  execute 'reset role';
  select md5(string_agg(h, '|')) || ' seq=' || (select last_value from public.personal_empleado_id_seq) into h1 from (
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) h from public.personal x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.relaciones_laborales x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.personal_registros_pago x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.eventos_laborales x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.idse_movimientos x union all
    select md5(coalesce(string_agg(x::text, '' order by x.id), '')) from public.inc_asignaciones x) s;
  select count(*) filter (where e ->> 'estado' = 'se_crearia'), count(*) filter (where e ->> 'estado' = 'error') into n1, n2 from jsonb_array_elements(acc) e;
  res := res || format('%s I1 Simulación de 450: %s se crearían, %s con error%s', case when n1 = 450 and n2 = 0 then 'PASA' else 'FALLA' end, n1, n2,
    coalesce(' · primer error: ' || (select e ->> 'mensaje' from jsonb_array_elements(acc) e where e ->> 'estado' = 'error' limit 1), ''));
  res := res || format('%s I1 Huella antes = después de la simulación (%s / %s)', case when h0 = h1 then 'PASA' else 'FALLA' end, left(h0, 8) || substr(h0, 33), left(h1, 8) || substr(h1, 33));

  -- I2 carga inicial de 450 (+ I10 tiempo)
  n6 := extract(epoch from clock_timestamp())::int;
  execute 'set local role authenticated';
  acc := '[]';
  for n1 in 0..8 loop
    t0 := clock_timestamp();
    acc := acc || public.imp_alta_personas((select jsonb_agg(v) from jsonb_array_elements(filas) with ordinality a(v, o) where o > n1 * 50 and o <= (n1 + 1) * 50), 'carga_inicial', true, '{}');
    v_max := greatest(v_max, extract(epoch from clock_timestamp() - t0));
  end loop;
  execute 'reset role';
  n6 := extract(epoch from clock_timestamp())::int - n6;
  res := res || format('%s I10 Carga de 450 en beehuman-pruebas: %s s en total; envío más lento de 50 filas: %s s (límite por envío de la API: 8 s)',
    case when n6 < 120 and v_max < 4 then 'PASA' else 'FALLA' end, n6, round(v_max, 2));
  select count(*) filter (where e ->> 'estado' = 'creada') into n1 from jsonb_array_elements(acc) e;
  select count(*) into n2 from public.relaciones_laborales where tenant_id = t and estado = 'vigente';
  select count(*) into n3 from public.personal_registros_pago where tenant_id = t and activo and relacion_laboral_id is not null;
  select count(*) into n4 from public.idse_movimientos where tenant_id = t;
  select count(*) into n5 from public.eventos_laborales where tenant_id = t and origen = 'importacion' and tipo = 'ingreso';
  select count(*) into n6 from public.inc_asignaciones where tenant_id = t;
  res := res || format('%s I2 Carga inicial: %s creadas · %s relaciones · %s de %s formas de pago ligadas · %s movimientos IDSE · %s eventos de importación · %s asignaciones%s',
    case when (n1, n2, n3, n4, n5, n6) = (450, 450, esq_esp, 0, 450, 430) then 'PASA' else 'FALLA' end, n1, n2, n3, esq_esp, n4, n5, n6,
    coalesce(' · primer error: ' || (select e ->> 'mensaje' from jsonb_array_elements(acc) e where e ->> 'estado' <> 'creada' limit 1), ''));
  select count(*) into n1 from public.personal p where p.tenant_id = t and p.coordinador_id is not null;
  select count(*) into n2 from public.personal p where p.tenant_id = t and not exists (select 1 from public.relaciones_laborales r where r.personal_id = p.id);
  res := res || format('%s I2 Coordinadores del mismo archivo resueltos por CURP (%s) y ninguna persona sin relación (%s)', case when n1 = 430 and n2 = 0 then 'PASA' else 'FALLA' end, n1, n2);

  -- I3 errores que solo detecta la base
  execute 'set local role authenticated';
  v_r := public.imp_alta_personas(jsonb_build_array(
    jsonb_set(jsonb_set(jsonb_set(jsonb_set(jsonb_set(jsonb_set(filas -> 3, '{id}', to_jsonb(gen_random_uuid())), '{persona,curp}', '"PAFA990101HDFBBXZ9"'),
      '{persona,rfc}', '"PAFA990101ZZ9"'), '{persona,nss}', '"77000000001"'), '{relacion,numero_interno}', '"N1"'), '{relacion,sdi}', '100') - 'coordinador_ref',
    jsonb_set(jsonb_set(jsonb_set(jsonb_set(filas -> 4, '{id}', to_jsonb(gen_random_uuid())), '{persona,curp}', '"PAFA990102HDFBBXZ8"'),
      '{persona,rfc}', '"PAFA990102ZZ8"'), '{relacion,numero_interno}', '"N2"') - 'coordinador_ref',
    jsonb_set(jsonb_set(jsonb_set(jsonb_set(filas -> 6, '{id}', to_jsonb(gen_random_uuid())), '{persona,curp}', '"PAFA990103HDFBBXZ7"'),
      '{persona,rfc}', '"PAFA990103ZZ7"'), '{persona,nss}', '"77000000003"') - 'coordinador_ref'), 'carga_inicial', false, '{}');
  execute 'reset role';
  res := res || format('%s I3 La base rechaza: SBC bajo el mínimo («%s») · NSS ya registrado («%s») · número interno en uso («%s»)',
    case when v_r -> 0 ->> 'mensaje' like '%salario mínimo%' and v_r -> 1 ->> 'mensaje' like 'posible persona existente. El NSS%' and v_r -> 2 ->> 'mensaje' like 'El número interno%' then 'PASA' else 'FALLA' end,
    left(v_r -> 0 ->> 'mensaje', 40), left(v_r -> 1 ->> 'mensaje', 40), left(v_r -> 2 ->> 'mensaje', 60));

  -- I4 reimportar: mismos id = «ya estaba»; id nuevos = posible persona existente
  execute 'set local role authenticated';
  acc := '[]';
  for n1 in 0..8 loop acc := acc || public.imp_alta_personas((select jsonb_agg(v) from jsonb_array_elements(filas) with ordinality a(v, o) where o > n1 * 50 and o <= (n1 + 1) * 50), 'carga_inicial', true, '{}'); end loop;
  select count(*) filter (where e ->> 'estado' = 'ya_estaba') into n1 from jsonb_array_elements(acc) e;
  acc := '[]';
  for n3 in 0..8 loop acc := acc || public.imp_alta_personas((select jsonb_agg(jsonb_set(v, '{id}', to_jsonb(gen_random_uuid()))) from jsonb_array_elements(filas) with ordinality a(v, o) where o > n3 * 50 and o <= (n3 + 1) * 50), 'carga_inicial', true, '{}'); end loop;
  select count(*) filter (where e ->> 'estado' = 'error' and e ->> 'mensaje' like 'posible persona existente%') into n2 from jsonb_array_elements(acc) e;
  execute 'reset role';
  select count(*) into n3 from public.personal where tenant_id = t;
  res := res || format('%s I4 Reimportación: %s «ya estaba» (mismos id) · %s rechazadas como existentes (id nuevos) · %s personas en total',
    case when n1 = 450 and n2 = 450 and n3 = 450 then 'PASA' else 'FALLA' end, n1, n2, n3);

  -- I6 altas nuevas: 10 personas nuevas con RP → 10 movimientos 08 pendientes
  execute 'set local role authenticated';
  v_r := public.imp_alta_personas((select jsonb_agg(
            (jsonb_set(jsonb_set(jsonb_set(jsonb_set(filas -> (k * 3), '{id}', to_jsonb(gen_random_uuid())),
              '{persona,curp}', to_jsonb('PAFA9' || k || '0101HDFBBXQ' || k)), '{persona,rfc}', to_jsonb('PAFA9' || k || '0101AB' || k)),
              '{persona,nss}', to_jsonb('8800000000' || k)) #- '{relacion,numero_interno}'::text[]) - 'coordinador_ref'::text)
          from generate_series(0, 9) k), 'altas_nuevas', true, '{}');
  execute 'reset role';
  select count(*) into n1 from public.idse_movimientos where tenant_id = t and tipo_movimiento = '08' and estado = 'pendiente';
  res := res || format('%s I6 Altas nuevas: %s movimientos 08 pendientes%s', case when n1 = 10 then 'PASA' else 'FALLA' end, n1,
    coalesce(' · ' || (select e ->> 'mensaje' from jsonb_array_elements(v_r) e where e ->> 'estado' = 'error' limit 1), ''));

  -- I9 permisos: consulta no puede importar
  perform set_config('request.jwt.claims', json_build_object('sub', con)::text, true); execute 'set local role authenticated';
  begin
    perform public.imp_alta_personas('[]', 'carga_inicial', false, '{}');
    res := res || 'FALLA I9 Consulta no puede importar'::text;
  exception when others then res := res || format('PASA I9 Consulta no puede importar («%s»)', left(sqlerrm, 55)); end;
  execute 'reset role';

  perform setval('public.personal_empleado_id_seq', v_seq0, v_called0);  -- la secuencia no es transaccional: se restaura
  raise exception using message = 'BEEHUMAN_IMP_PRUEBAS' || chr(10) || array_to_string(res, chr(10));
end $imp$;
