-- Importación masiva v2 · pruebas SQL I7 (regresión del ingreso desde pantalla), I8 (uso real en
-- Incidencias e IDSE) e I9 (permisos y aislamiento). Todo dentro de un bloque que SIEMPRE termina
-- en error forzado: no deja nada. Variables psql: :ten (tenant con la importación), :adm, :coord, :cons
-- (usuarios administrador, coordinador y consulta de ese tenant).
do $t$
declare
  res text[] := '{}'; v_p uuid := gen_random_uuid(); v_rel uuid; v_n int; v_m int; v_imp record; v_per uuid; v_h uuid; v_x jsonb;
  v_t2 uuid := gen_random_uuid(); v_u2 uuid := gen_random_uuid(); v_coord_ant uuid; v_msg text;
  v_curp_t1 text;
begin
  -- ===== I7: ingreso desde pantalla sigue generando su 08 (origen pantalla) =====
  perform set_config('request.jwt.claims', json_build_object('sub', :'adm')::text, true); execute 'set local role authenticated';
  insert into public.personal (id, nombres, primer_apellido, nombre_completo, empresa_id, nss, curp, rfc, cp_fiscal)
    values (v_p, 'REGRESION', 'PANTALLA', 'REGRESION PANTALLA', '0e100000-0000-4000-8000-000000000001', '99999999990', 'REPA800101HDFGNTA1', 'REPA800101AB1', '01010');
  select count(*) into v_n from public.idse_movimientos where tipo_movimiento = '08';
  v_rel := public.laboral_registrar_ingreso(v_p, '0e100000-0000-4000-8000-000000000001', '0e200000-0000-4000-8000-000000000001', public.hoy_mx(),
    null, 400, 400, '1', '0', '0', null, null, 'regresión');
  select count(*) into v_m from public.idse_movimientos where tipo_movimiento = '08';
  res := res || format('%s I7 Ingreso desde pantalla con RP genera su 08 (antes %s, después %s)', case when v_m = v_n + 1 then 'PASA' else 'FALLA' end, v_n, v_m);
  res := res || format('%s I7 El evento del ingreso desde pantalla conserva origen «pantalla»',
    case when (select origen from public.eventos_laborales where relacion_laboral_id = v_rel and tipo = 'ingreso') = 'pantalla' then 'PASA' else 'FALLA' end);
  begin
    perform public.laboral__ingreso_nucleo(v_p, '0e100000-0000-4000-8000-000000000003', null, public.hoy_mx(), null, null, null, null, null, null, null, null, null, false, 'otro');
    res := res || 'FALLA I7 El núcleo rechaza un origen no permitido'::text;
  exception when others then res := res || 'PASA I7 El núcleo rechaza un origen no permitido'::text; end;
  execute 'reset role';

  -- ===== I8: los importados funcionan en Incidencias e IDSE =====
  select p.id, p.empresa_id, p.coordinador_id, rl.id rel into v_imp
    from public.personal p join public.relaciones_laborales rl on rl.personal_id = p.id and rl.estado = 'vigente'
   where p.empresa_id = '0e100000-0000-4000-8000-000000000001' and p.coordinador_id is not null and rl.registro_patronal_id is not null
   order by p.empleado_id limit 1;
  select count(*) into v_n from public.inc_esquemas_vigentes(v_imp.id, v_imp.empresa_id, array[public.hoy_mx()], 'mixto');
  res := res || format('%s I8 Un importado tiene forma de pago vigente para Incidencias (%s)', case when v_n >= 1 then 'PASA' else 'FALLA' end, v_n);
  -- El usuario coordinador queda ligado al coordinador importado (solo en esta prueba, se deshace).
  select personal_id into v_coord_ant from public.usuarios_tenant where user_id = :'coord';
  update public.usuarios_tenant set personal_id = v_imp.coordinador_id where user_id = :'coord';
  perform set_config('request.jwt.claims', json_build_object('sub', :'adm')::text, true); execute 'set local role authenticated';
  v_per := public.inc_crear_periodo(v_imp.empresa_id, (select id from public.periodicidades where lower(nombre) = 'semanal' limit 1), public.hoy_mx(), public.hoy_mx() + 6);
  execute 'reset role';
  perform set_config('request.jwt.claims', json_build_object('sub', :'coord')::text, true); execute 'set local role authenticated';
  v_h := public.inc_abrir_hoja(v_per);
  select count(distinct personal_id) into v_n from public.inc_personas_hoja(v_h);
  execute 'reset role';
  select count(*) into v_m from public.personal where coordinador_id = v_imp.coordinador_id and empresa_id = v_imp.empresa_id;
  res := res || format('%s I8 La hoja del coordinador importado muestra a sus personas importadas de la empresa (%s de %s)', case when v_n = v_m and v_n > 0 then 'PASA' else 'FALLA' end, v_n, v_m);
  perform set_config('request.jwt.claims', json_build_object('sub', :'adm')::text, true); execute 'set local role authenticated';
  select count(*) into v_n from public.idse_movimientos where relacion_laboral_id = v_imp.rel;
  perform public.laboral_registrar_baja(v_imp.rel, public.hoy_mx(), '2', 'prueba de baja de un importado');
  select count(*) into v_m from public.idse_movimientos where relacion_laboral_id = v_imp.rel and tipo_movimiento = '02';
  res := res || format('%s I8 Un importado con carga inicial no tenía 08 y su baja genera el 02 en IDSE (08 previos: %s, 02: %s)', case when v_n = 0 and v_m = 1 then 'PASA' else 'FALLA' end, v_n, v_m);
  execute 'reset role';
  update public.usuarios_tenant set personal_id = v_coord_ant where user_id = :'coord';

  -- ===== I9: permisos y aislamiento =====
  foreach v_msg in array array[:'cons', :'coord'] loop
    perform set_config('request.jwt.claims', json_build_object('sub', v_msg)::text, true); execute 'set local role authenticated';
    begin
      perform public.imp_alta_personas('[]'::jsonb, 'carga_inicial', false, '{}');
      res := res || format('FALLA I9 %s no puede importar', (select rol from public.usuarios_tenant where user_id = v_msg::uuid));
    exception when others then
      res := res || format('PASA I9 %s no puede importar («%s»)', (select rol from public.usuarios_tenant where user_id = v_msg::uuid), left(sqlerrm, 60));
    end;
    execute 'reset role';
  end loop;
  res := res || format('%s I9 anon no tiene permiso de ejecutar la importación ni el núcleo',
    case when not has_function_privilege('anon', 'public.imp_alta_personas(jsonb, text, boolean, text[])', 'execute')
          and not has_function_privilege('anon', 'public.laboral__ingreso_nucleo(uuid, uuid, uuid, date, date, numeric, numeric, text, text, text, text, text, text, boolean, text)', 'execute')
         then 'PASA' else 'FALLA' end);
  -- Otro tenant: su administrador no ve ni usa personas o catálogos del primero.
  select curp into v_curp_t1 from public.personal where id = v_imp.coordinador_id;
  insert into public.tenants (id, nombre) values (v_t2, 'TENANT AISLAMIENTO IMP');
  insert into auth.users (id, email) values (v_u2, 'imp-aislamiento@beehuman.invalid');
  insert into public.usuarios_tenant (user_id, tenant_id, rol) values (v_u2, v_t2, 'administrador');
  perform set_config('request.jwt.claims', json_build_object('sub', v_u2)::text, true); execute 'set local role authenticated';
  select count(*) into v_n from public.personal;
  v_x := public.imp_alta_personas(jsonb_build_array(
      jsonb_build_object('id', gen_random_uuid(), 'linea', 2, 'coordinador_ref', v_curp_t1,
        'persona', jsonb_build_object('nombres', 'AISLADA', 'primer_apellido', 'UNO', 'nombre_completo', 'AISLADA UNO', 'tipo_empleado', 'Base', 'turno', 'Matutino'),
        'relacion', null, 'esquemas', '[]'::jsonb),
      jsonb_build_object('id', gen_random_uuid(), 'linea', 3, 'coordinador_ref', null,
        'persona', jsonb_build_object('nombres', 'AISLADA', 'primer_apellido', 'DOS', 'nombre_completo', 'AISLADA DOS', 'empresa_id', '0e100000-0000-4000-8000-000000000001', 'tipo_empleado', 'Base', 'turno', 'Matutino'),
        'relacion', null, 'esquemas', '[]'::jsonb)), 'carga_inicial', false, '{}');
  execute 'reset role';
  res := res || format('%s I9 Otro tenant no ve personas del primero (%s visibles)', case when v_n = 0 then 'PASA' else 'FALLA' end, v_n);
  res := res || format('%s I9 Otro tenant no puede usar como coordinador a una persona del primero («%s»)',
    case when v_x -> 0 ->> 'estado' = 'error' and v_x -> 0 ->> 'mensaje' like '%no existe%' then 'PASA' else 'FALLA' end, left(v_x -> 0 ->> 'mensaje', 50));
  res := res || format('%s I9 Otro tenant no puede usar una empresa del primero («%s»)',
    case when v_x -> 1 ->> 'estado' = 'error' then 'PASA' else 'FALLA' end, left(coalesce(v_x -> 1 ->> 'mensaje', v_x -> 1 ->> 'estado'), 70));

  raise exception using message = 'BEEHUMAN_IMP' || chr(10) || array_to_string(res, chr(10));
end $t$;
