-- Solo para la base LOCAL: reproduce los permisos de ejecución de funciones
-- observados en beehuman-pruebas el 27-oct-2026 (has_function_privilege).
do $$
declare f record;
begin
  for f in select p.oid::regprocedure sig, p.proname from pg_proc p where p.pronamespace='public'::regnamespace loop
    execute format('revoke execute on function %s from public, anon, authenticated', f.sig);
    if f.proname in ('coincidencias_numero_interno','current_tenant_id','en_alcance_persona','equipo_coordinador',
       'es_cp_valido','es_curp_valida','es_nss_valido','es_rfc_persona_valido','fecha_aammdd_valida',
       'personal_organizacional','resumen_agregado','tiene_rol') then
      execute format('grant execute on function %s to authenticated', f.sig);
    end if;
  end loop;
end $$;
