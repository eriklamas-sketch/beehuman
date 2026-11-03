-- =====================================================================
-- BeeHuman · Etapa 1 · v3.1: relación principal de la ficha
-- Hallado al construir las pantallas (3-nov-2026). Con la regla de la v3,
-- si alguien solo tenía relación de efectivo (sin RP) y después recibía su
-- alta IMSS, la ficha seguía mostrando la relación sin RP: sin fecha de alta
-- ni SDI, que usan la exportación a NOI y las alertas de aniversario.
-- Regla nueva (v3.1, ajustada tras la revisión):
--   1. La ficha se queda en la empresa que ya muestra: primero las relaciones
--      vigentes de ESA empresa. Un movimiento en otra empresa nunca la cambia.
--   2. Dentro de esa empresa, primero la relación con RP (la que trae alta y
--      SDI para NOI y alertas).
--   3. Luego la que coincide con el RP que ya muestra la ficha, y al final la
--      más reciente.
--   Si la empresa de la ficha ya no tiene relaciones vigentes (se dio de baja),
--   se pasa a otra empresa, prefiriendo la relación con RP más reciente.
-- Solo cambia esta función; no toca datos.
-- Requiere: 20261104000000_eventos_laborales_idse.sql
-- Reversión: 20261104000100_reversion_relacion_principal_con_rp.sql
-- =====================================================================
begin;
create or replace function public.laboral_relacion_principal(p_personal_id uuid) returns uuid
language sql stable security definer set search_path to '' as $$
  select r.id from public.relaciones_laborales r
  join public.personal p on p.id = r.personal_id
   where r.personal_id = p_personal_id and r.estado = 'vigente'
   order by (r.empresa_id is not distinct from p.empresa_id) desc,
            (r.registro_patronal_id is not null) desc,
            (r.registro_patronal_id is not distinct from p.registro_patronal_id) desc,
            r.fecha_ingreso desc nulls last, r.creado_en desc
   limit 1;
$$;
revoke all on function public.laboral_relacion_principal(uuid) from public, anon, authenticated;
commit;
