-- =====================================================================
-- BeeHuman · Reversión de la adaptación de datos sintéticos IDSE
-- Devuelve NSS, nombres, nombre_completo y la autoría (actualizado_por /
-- actualizado_en) a sus valores exactos anteriores según
-- respaldo.datos_sinteticos_idse_20261109, solo si:
--   · todas las personas del respaldo siguen existiendo, y
--   · nadie cambió después ninguno de esos datos.
-- Deja constancia en Movimientos (no borra la traza). El respaldo se renombra
-- para permitir reaplicar. Una sola transacción.
-- Nota: con 20261109000200 aplicada, los datos restaurados vuelven a quedar
-- bloqueados en la bandeja IDSE (por eso se adaptaron).
-- =====================================================================
begin;
-- Sin disparadores: restaura también la autoría tal como estaba.
set local session_replication_role = replica;

do $$
declare
  c_rev constant text := 'sistema · reversión adaptación datos sintéticos IDSE 20261109';
  n int; n_resp int;
begin
  if to_regclass('respaldo.datos_sinteticos_idse_20261109') is null then
    raise exception 'BeeHuman: la adaptación no está aplicada; nada que revertir.';
  end if;
  select count(*) into n_resp from respaldo.datos_sinteticos_idse_20261109;
  if (select count(*) from respaldo.datos_sinteticos_idse_20261109 r join public.personal p on p.id = r.id and p.tenant_id = r.tenant_id) <> n_resp then
    raise exception 'BeeHuman: alguna persona del respaldo ya no existe o cambió de tenant; revisa caso por caso.';
  end if;
  if exists (select 1 from respaldo.datos_sinteticos_idse_20261109 r join public.personal p on p.id = r.id
              where p.nss is distinct from r.nss_nuevo or p.nombres is distinct from r.nombres_nuevo
                 or p.nombre_completo is distinct from r.nombre_completo_nuevo
                 or p.actualizado_por is distinct from r.actualizado_por or p.actualizado_en is distinct from r.actualizado_en) then
    raise exception 'BeeHuman: algún dato cambió después de la adaptación; revisa caso por caso.';
  end if;

  update public.personal p set nss = r.nss_anterior, nombres = r.nombres_anterior, nombre_completo = r.nombre_completo_anterior,
         actualizado_por = r.actualizado_por, actualizado_en = r.actualizado_en
    from respaldo.datos_sinteticos_idse_20261109 r where p.id = r.id;
  get diagnostics n = row_count;
  if n <> n_resp then raise exception 'BeeHuman: se restauraron % personas y el respaldo tiene %.', n, n_resp; end if;

  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
  select id, tenant_id, x.campo, x.antes, x.despues, c_rev, null, now()
    from respaldo.datos_sinteticos_idse_20261109,
         lateral (values ('nss', nss_nuevo, nss_anterior), ('nombres', nombres_nuevo, nombres_anterior),
                         ('nombre_completo', nombre_completo_nuevo, nombre_completo_anterior)) x(campo, antes, despues)
   where x.antes is distinct from x.despues;

  execute format('alter table respaldo.datos_sinteticos_idse_20261109 rename to %I',
                 'datos_sinteticos_idse_20261109_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
  raise notice 'BeeHuman: % personas restauradas a sus valores anteriores.', n;
end $$;

commit;
