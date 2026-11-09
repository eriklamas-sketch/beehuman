-- =====================================================================
-- BeeHuman · Corrección de datos: fecha_asignacion un día adelantada (UTC)
-- 9-nov-2026 · Acompaña a la migración 20261109000000_fechas_hora_mexico.
--
-- personal.fecha_asignacion se llenaba por omisión con current_date (UTC):
-- quien se dio de alta entre las 18:00 y las 23:59 de México quedó con el
-- día siguiente. No es bitácora: se corrige en su lugar (−1 día) y cada
-- cambio queda en Movimientos (usuario «sistema»), con el valor anterior.
--
-- Regla (la misma de la auditoría): fecha_asignacion = fecha UTC del alta
-- y = fecha de México del alta + 1. La fecha no se captura en pantalla.
--
-- ANTES DE EJECUTAR: fijar v_esperado con el conteo del precheck del
-- entorno (pruebas 9-nov-2026: 6). Si no coincide, no cambia nada.
-- Reversión: supabase/datos/20261109000100_reversion_corregir_fecha_asignacion_utc.sql
-- =====================================================================
begin;
-- Sin disparadores en esta transacción: el sellado de Movimientos exige un
-- usuario autenticado y aquí actúa el sistema (se registra explícitamente).
set local session_replication_role = replica;

do $$
declare
  v_esperado constant int := 6;   -- ← conteo del precheck de ESTE entorno
  v_marca constant text := 'sistema · corrección zona horaria UTC 20261109';
  n int;
begin
  if exists (select 1 from public.movimientos where usuario = v_marca) then
    raise exception 'BeeHuman: esta corrección ya se aplicó en este entorno.';
  end if;
  create temporary table _fa on commit drop as
    select p.id, p.tenant_id, p.fecha_asignacion as anterior, (p.created_at at time zone 'America/Mexico_City')::date as correcta
      from public.personal p
     where p.fecha_asignacion = (p.created_at at time zone 'UTC')::date
       and p.fecha_asignacion = (p.created_at at time zone 'America/Mexico_City')::date + 1;
  select count(*) into n from _fa;
  if n <> v_esperado then
    raise exception 'BeeHuman: se encontraron % fechas de asignación adelantadas y se esperaban %; no se cambió nada.', n, v_esperado;
  end if;

  update public.personal p set fecha_asignacion = f.correcta from _fa f where p.id = f.id;
  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
    select f.id, f.tenant_id, 'fecha_asignacion', f.anterior::text, f.correcta::text, v_marca, null, now() from _fa f;

  if exists (select 1 from public.personal p
              where p.fecha_asignacion = (p.created_at at time zone 'UTC')::date
                and p.fecha_asignacion = (p.created_at at time zone 'America/Mexico_City')::date + 1) then
    raise exception 'BeeHuman: quedaron fechas sin corregir.';
  end if;
  raise notice 'BeeHuman: % fechas de asignación corregidas; constan en Movimientos como «%».', n, v_marca;
end $$;

commit;
