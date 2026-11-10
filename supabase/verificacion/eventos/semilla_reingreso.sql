-- Datos FICTICIOS para probar el reingreso en pantalla (base LOCAL bhui; nunca Supabase).
-- Se crean con las MISMAS funciones de la aplicación, como admin de prueba.
begin;
select set_config('request.jwt.claims', '{"sub":"0b000000-0000-4000-8000-000000000001","role":"authenticated"}', true);
do $$
declare
  t uuid := '0a000000-0000-4000-8000-000000000001';
  alti uuid := '0c000000-0000-4000-8000-000000000001'; cumbre uuid := '0c000000-0000-4000-8000-000000000002';
  rp1 uuid := '0f900000-0000-4000-8000-000000000001'; rp2 uuid := '0f900000-0000-4000-8000-000000000002';
  imss uuid := '0f000000-0000-4000-8000-000000000001'; sem uuid := '0e000000-0000-4000-8000-000000000007'; men uuid := '0e000000-0000-4000-8000-000000000030';
  p uuid; r uuid; r2 uuid;
begin
  -- R1 RAMIRO: trabajó en ALTIPLANO RP1 (2022-2025), baja por separación voluntaria. Reingresa con otras condiciones.
  insert into public.personal (id, tenant_id, nombres, primer_apellido, segundo_apellido, nombre_completo, curp, rfc, nss, cp_fiscal, no_fonacot,
     contacto_emergencia_nombre, contacto_emergencia_telefono, contacto_emergencia_parentesco, empresa_id, estatus)
  values ('0a200000-0000-4000-8000-000000000001', t, 'RAMIRO', 'REYES', 'SOTO', 'RAMIRO REYES SOTO', 'RESR880808HDFYTM01', 'RESR880808AB1', '44444444440', '06600', 'F-778812',
     'LUCIA SOTO', '5550001111', 'Madre', alti, 'Activo') returning id into p;
  r := public.laboral_registrar_ingreso(p, alti, rp1, '2022-02-01', null, 400, 400, '1', '0', '0', '015', 'R01', 'Alta original (sintético)');
  insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, fecha_inicio, empresa_id, registro_patronal_id)
  values (t, p, imss, sem, 2800, 'bruto', '2022-02-01', alti, rp1);
  perform public.laboral_registrar_baja(r, '2025-05-31', '2', 'Renuncia (sintético)');

  -- R2 SOFIA: trabajó en ALTIPLANO RP1 (2021-2024); regresa al grupo en SERVICIOS CUMBRE (sin RP).
  insert into public.personal (id, tenant_id, nombres, primer_apellido, segundo_apellido, nombre_completo, curp, rfc, nss, cp_fiscal, empresa_id, estatus)
  values ('0a200000-0000-4000-8000-000000000002', t, 'SOFIA', 'TREJO', 'LUNA', 'SOFIA TREJO LUNA', 'TELS910412MDFRNF02', 'TELS910412CD2', '55555555550', '06700', alti, 'Activo') returning id into p;
  r := public.laboral_registrar_ingreso(p, alti, rp1, '2021-01-10', null, 380, 380, '1', '0', '0', '020', 'S02', null);
  insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, fecha_inicio, empresa_id, registro_patronal_id)
  values (t, p, imss, sem, 2600, 'bruto', '2021-01-10', alti, rp1);
  perform public.laboral_registrar_baja(r, '2024-12-31', '1', null);

  -- R3 TOMAS: trabajó en ALTIPLANO RP1 (2020-2023) y ya reingresó en RP1 (vigente desde 2024-01-15).
  insert into public.personal (id, tenant_id, nombres, primer_apellido, segundo_apellido, nombre_completo, curp, nss, empresa_id, estatus)
  values ('0a200000-0000-4000-8000-000000000003', t, 'TOMAS', 'UGALDE', 'VARGAS', 'TOMAS UGALDE VARGAS', 'UAVT850315HDFGRM03', '66666666660', alti, 'Activo') returning id into p;
  r := public.laboral_registrar_ingreso(p, alti, rp1, '2020-03-01', null, 350, 350, '1', '0', '0', '030', 'T03', null);
  perform public.laboral_registrar_baja(r, '2023-03-31', '2', null);
  r := public.laboral_registrar_ingreso(p, alti, rp1, '2024-01-15', null, 420, 420, '1', '0', '0', '030', 'T03', null);

  -- R4 ULISES: dos relaciones vigentes en ALTIPLANO (RP1 y sin RP) y UN solo esquema, ligado a la de RP1.
  insert into public.personal (id, tenant_id, nombres, primer_apellido, segundo_apellido, nombre_completo, curp, nss, empresa_id, estatus)
  values ('0a200000-0000-4000-8000-000000000004', t, 'ULISES', 'VIDAL', 'ROJAS', 'ULISES VIDAL ROJAS', 'VIRU900101HDFDJL04', '77777777770', alti, 'Activo') returning id into p;
  r := public.laboral_registrar_ingreso(p, alti, rp1, '2025-02-01', null, 450, 450, '1', '0', '0', '040', 'U04', null);
  r2 := public.laboral_registrar_ingreso(p, alti, null, '2025-02-01', null, null, null, null, null, null, null, null, 'Complemento en efectivo (sintético)');
  insert into public.personal_registros_pago (tenant_id, personal_id, clasificacion_id, periodicidad_id, sueldo, modalidad_sueldo, fecha_inicio, empresa_id, registro_patronal_id, relacion_laboral_id)
  values (t, p, imss, men, 15000, 'bruto', '2025-02-01', alti, rp1, r);

  -- R5 DIANA (migrada, vigente sin RP y SIN fecha de ingreso): además trabajó antes en ALTIPLANO RP2 (2018-2019).
  p := '0a100000-0000-4000-8000-000000000014';
  r := public.laboral_registrar_ingreso(p, alti, rp2, '2018-04-02', null, 300, 300, '1', '0', '0', '050', 'D05', 'Empleo anterior (sintético)');
  perform public.laboral_registrar_baja(r, '2019-06-30', '1', null);

  -- Antecedentes: todos los movimientos IDSE de estas personas ya se presentaron y
  -- tienen resultado aceptado (archivo histórico sintético por RP y tipo).
  perform set_config('beehuman.laboral', 'on', true);
  insert into public.idse_archivos (id, tenant_id, empresa_id, registro_patronal_id, tipo_movimiento, guia, nombre_archivo, num_registros, contenido, hash_sha256, estado, lote_idse, fecha_presentacion)
  select gen_random_uuid(), t, alti, m.registro_patronal_id, m.tipo_movimiento, '00000', 'HISTORICO_SINTETICO_' || m.tipo_movimiento || '.dat', count(*), 'sintético', 'sintético', 'con_resultado', 'LOTE-SINT', '2025-01-01'
    from public.idse_movimientos m join public.relaciones_laborales rl on rl.id = m.relacion_laboral_id
   where rl.personal_id::text like '0a200000%' or rl.personal_id = '0a100000-0000-4000-8000-000000000014'
   group by m.registro_patronal_id, m.tipo_movimiento;
  update public.idse_movimientos m set estado = 'confirmado', archivo_id = a.id
    from public.relaciones_laborales rl, public.idse_archivos a
   where rl.id = m.relacion_laboral_id and (rl.personal_id::text like '0a200000%' or rl.personal_id = '0a100000-0000-4000-8000-000000000014')
     and a.nombre_archivo like 'HISTORICO_SINTETICO_%' and a.registro_patronal_id = m.registro_patronal_id and a.tipo_movimiento = m.tipo_movimiento;
  perform set_config('beehuman.laboral', 'off', true);
end $$;
commit;
