-- =====================================================================
-- BeeHuman · Reversión de la corrección de fecha_asignacion (UTC)
-- Devuelve cada fecha a su valor anterior según Movimientos, solo si nadie
-- la cambió después, y deja constancia en Movimientos (no borra la traza).
-- =====================================================================
begin;
set local session_replication_role = replica;

do $$
declare
  v_marca constant text := 'sistema · corrección zona horaria UTC 20261109';
  v_rev constant text := 'sistema · reversión corrección zona horaria UTC 20261109';
  n int;
begin
  if not exists (select 1 from public.movimientos where usuario = v_marca) then
    raise exception 'BeeHuman: la corrección no está aplicada; nada que revertir.';
  end if;
  if exists (select 1 from public.movimientos where usuario = v_rev) then
    raise exception 'BeeHuman: la corrección ya se revirtió.';
  end if;
  if exists (select 1 from public.movimientos m join public.personal p on p.id = m.personal_id
              where m.usuario = v_marca and p.fecha_asignacion::text is distinct from m.valor_nuevo) then
    raise exception 'BeeHuman: alguna fecha de asignación cambió después de la corrección; revisa caso por caso.';
  end if;
  update public.personal p set fecha_asignacion = m.valor_anterior::date
    from public.movimientos m where m.usuario = v_marca and m.campo = 'fecha_asignacion' and p.id = m.personal_id;
  get diagnostics n = row_count;
  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
    select m.personal_id, m.tenant_id, 'fecha_asignacion', m.valor_nuevo, m.valor_anterior, v_rev, null, now()
      from public.movimientos m where m.usuario = v_marca;
  raise notice 'BeeHuman: % fechas de asignación devueltas a su valor anterior.', n;
end $$;

commit;
