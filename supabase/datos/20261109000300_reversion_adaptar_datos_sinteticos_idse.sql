-- =====================================================================
-- BeeHuman · Reversión de la adaptación de datos sintéticos IDSE
-- Devuelve NSS, nombres y nombre_completo a sus valores anteriores según
-- respaldo.datos_sinteticos_idse_20261109, solo si nadie los cambió
-- después, y deja constancia en Movimientos (no borra la traza). El
-- respaldo se renombra para permitir reaplicar.
-- Nota: con 20261109000200 aplicada, los datos restaurados vuelven a quedar
-- bloqueados en la bandeja IDSE (por eso se adaptaron).
-- =====================================================================
begin;

do $$
begin
  if to_regclass('respaldo.datos_sinteticos_idse_20261109') is null then
    raise exception 'BeeHuman: la adaptación no está aplicada; nada que revertir.';
  end if;
  if exists (select 1 from respaldo.datos_sinteticos_idse_20261109 r join public.personal p on p.id = r.id
              where p.nss is distinct from r.nss_nuevo or p.nombres is distinct from r.nombres_nuevo
                 or p.nombre_completo is distinct from r.nombre_completo_nuevo) then
    raise exception 'BeeHuman: algún dato cambió después de la adaptación; revisa caso por caso.';
  end if;
  update public.personal p set nss = r.nss_anterior, nombres = r.nombres_anterior, nombre_completo = r.nombre_completo_anterior
    from respaldo.datos_sinteticos_idse_20261109 r where p.id = r.id;
end $$;

set local session_replication_role = replica;
do $$
begin
  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
  select id, tenant_id, x.campo, x.antes, x.despues, 'sistema · reversión adaptación datos sintéticos IDSE 20261109', null, now()
    from respaldo.datos_sinteticos_idse_20261109,
         lateral (values ('nss', nss_nuevo, nss_anterior), ('nombres', nombres_nuevo, nombres_anterior),
                         ('nombre_completo', nombre_completo_nuevo, nombre_completo_anterior)) x(campo, antes, despues)
   where x.antes is distinct from x.despues;
  execute format('alter table respaldo.datos_sinteticos_idse_20261109 rename to %I',
                 'datos_sinteticos_idse_20261109_revertida_' || to_char(now(), 'YYYYMMDDHH24MISS'));
end $$;

commit;
