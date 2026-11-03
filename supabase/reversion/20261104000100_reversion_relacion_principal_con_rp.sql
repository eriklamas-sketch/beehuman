-- Reversión de 20261104000100_relacion_principal_con_rp.sql: regresa la regla de la v3.
begin;
create or replace function public.laboral_relacion_principal(p_personal_id uuid) returns uuid
language sql stable security definer set search_path to '' as $$
  select r.id from public.relaciones_laborales r
  join public.personal p on p.id = r.personal_id
   where r.personal_id = p_personal_id and r.estado = 'vigente'
   order by (r.empresa_id is not distinct from p.empresa_id
             and r.registro_patronal_id is not distinct from p.registro_patronal_id) desc,
            (r.registro_patronal_id is not null) desc, r.fecha_ingreso desc nulls last, r.creado_en desc
   limit 1;
$$;
revoke all on function public.laboral_relacion_principal(uuid) from public, anon, authenticated;
commit;
