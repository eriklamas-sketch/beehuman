-- =====================================================================
-- BeeHuman · Adaptación de datos SINTÉTICOS a los validadores IDSE
-- 9-nov-2026 · Solo beehuman-pruebas, tenant «PILOTO SINTETICO 500».
-- Acompaña a 20261109000200_idse_validadores_guia (NSS con dígito
-- verificador; nombres sin dígitos). NO es para producción.
--
-- Qué cambia (y nada más):
--   · personal.nss  — solo los NSS de 11 dígitos con dígito verificador
--     incorrecto. Nuevo NSS = '9900' + número del empleado_id (6 dígitos)
--     + dígito verificador. Único por construcción (empleado_id es único);
--     el script comprueba que no choque con ningún NSS existente.
--     Los NSS válidos y los vacíos se quedan como están.
--   · personal.nombres y personal.nombre_completo — dígitos → letras
--     (0→A … 9→J): «PERSONA 0007» → «PERSONA AAAH». Misma longitud,
--     sin duplicados (el script lo comprueba).
-- Qué NO cambia: id, empleado_id, tenant, relaciones laborales, eventos,
-- movimientos IDSE, archivos IDSE, esquemas de pago. El script compara la
-- huella de esas tablas antes y después y aborta si algo cambió.
-- Trazabilidad: respaldo.datos_sinteticos_idse_20261109 (valor anterior y
-- nuevo por persona) y una fila en Movimientos por campo cambiado
-- (usuario «sistema · adaptación datos sintéticos IDSE 20261109»).
-- Los archivos IDSE ya generados conservan los datos anteriores (histórico).
-- ANTES DE EJECUTAR: confirmar los conteos del precheck (9-nov: 300 NSS,
-- 500 nombres). Si no coinciden, no cambia nada.
-- Reversión: 20261109000300_reversion_adaptar_datos_sinteticos_idse.sql
-- =====================================================================
begin;

do $$
declare
  c_tenant   constant text := 'PILOTO SINTETICO 500';
  c_nss      constant int := 300;     -- ← NSS a corregir según el precheck
  c_nombres  constant int := 500;     -- ← nombres con dígitos según el precheck
  v_tenant uuid; n_nss int; n_nom int;
begin
  select id into v_tenant from public.tenants where nombre = c_tenant;
  if v_tenant is null then raise exception 'BeeHuman: no existe el tenant %; ¿es el entorno correcto?', c_tenant; end if;
  if to_regclass('respaldo.datos_sinteticos_idse_20261109') is not null then
    raise exception 'BeeHuman: esta adaptación ya se aplicó en este entorno.';
  end if;
  if to_regprocedure('public.es_nss_imss_valido(text)') is null then
    raise exception 'BeeHuman: falta la migración 20261109000200_idse_validadores_guia.';
  end if;

  -- Huella de lo que NO debe cambiar
  create temporary table _huella_antes on commit drop as
  select 'relaciones_laborales' t, md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) h from public.relaciones_laborales x
  union all select 'eventos_laborales', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.eventos_laborales x
  union all select 'idse_movimientos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_movimientos x
  union all select 'idse_archivos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_archivos x
  union all select 'personal_registros_pago', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal_registros_pago x
  union all select 'personal (ids, empleado_id, tenant)', md5(coalesce(string_agg(x.id || x.empleado_id || x.tenant_id, '' order by x.id), '')) from public.personal x
  union all select 'personal de otros tenants', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal x where x.tenant_id <> v_tenant;

  create temporary table _plan on commit drop as
  select p.id, p.tenant_id, p.empleado_id, p.nss as nss_anterior,
         case when p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss)
              then (select b || ((10 - (select sum(((substr(b, i, 1)::int * (2 - i % 2)) / 10) + ((substr(b, i, 1)::int * (2 - i % 2)) % 10))
                                         from generate_series(1, 10) g(i)) % 10) % 10)::text
                      from (select '9900' || split_part(p.empleado_id, '-', 2) as b) z)
              else p.nss end as nss_nuevo,
         p.nombres as nombres_anterior, translate(p.nombres, '0123456789', 'ABCDEFGHIJ') as nombres_nuevo,
         p.nombre_completo as nombre_completo_anterior, translate(p.nombre_completo, '0123456789', 'ABCDEFGHIJ') as nombre_completo_nuevo
    from public.personal p
   where p.tenant_id = v_tenant
     and ((p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss))
          or concat(p.nombres, p.nombre_completo) ~ '[0-9]');

  select count(*) filter (where nss_nuevo is distinct from nss_anterior), count(*) filter (where nombres_nuevo is distinct from nombres_anterior)
    into n_nss, n_nom from _plan;
  if n_nss <> c_nss or n_nom <> c_nombres then
    raise exception 'BeeHuman: el plan da % NSS y % nombres; se esperaban % y %. No se cambió nada.', n_nss, n_nom, c_nss, c_nombres;
  end if;
  if exists (select 1 from _plan where nss_nuevo is distinct from nss_anterior
               and (split_part(empleado_id, '-', 2) !~ '^[0-9]{6}$' or char_length(nss_nuevo) <> 11 or not public.es_nss_imss_valido(nss_nuevo))) then
    raise exception 'BeeHuman: algún NSS nuevo no es válido (revisa el formato del empleado_id).';
  end if;
  if exists (select nss_nuevo from _plan where nss_nuevo is distinct from nss_anterior group by 1 having count(*) > 1)
     or exists (select 1 from _plan a join public.personal o on o.nss = a.nss_nuevo and o.id <> a.id where a.nss_nuevo is distinct from a.nss_anterior) then
    raise exception 'BeeHuman: algún NSS nuevo se repite o ya existe; no se cambió nada.';
  end if;
  if exists (select 1 from (select p.id, coalesce(pl.nombre_completo_nuevo, p.nombre_completo) nc from public.personal p
                              left join _plan pl on pl.id = p.id where p.tenant_id = v_tenant) x group by nc having count(*) > 1) then
    raise exception 'BeeHuman: algún nombre nuevo duplicaría a otra persona; no se cambió nada.';
  end if;

  create table respaldo.datos_sinteticos_idse_20261109 as select *, now() as aplicado_en from _plan;
  alter table respaldo.datos_sinteticos_idse_20261109 add primary key (id);
  revoke all on respaldo.datos_sinteticos_idse_20261109 from public;

  -- Con todos los validadores de la ficha activos (el NSS nuevo se valida al guardarse)
  update public.personal p set nss = pl.nss_nuevo, nombres = pl.nombres_nuevo, nombre_completo = pl.nombre_completo_nuevo
    from _plan pl where p.id = pl.id;
end $$;

-- Movimientos: el sellado exige un usuario autenticado; aquí actúa el sistema.
set local session_replication_role = replica;
do $$
declare c_marca constant text := 'sistema · adaptación datos sintéticos IDSE 20261109';
  r record;
begin
  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
  select id, tenant_id, x.campo, x.antes, x.despues, c_marca, null, now()
    from respaldo.datos_sinteticos_idse_20261109,
         lateral (values ('nss', nss_anterior, nss_nuevo), ('nombres', nombres_anterior, nombres_nuevo),
                         ('nombre_completo', nombre_completo_anterior, nombre_completo_nuevo)) x(campo, antes, despues)
   where x.antes is distinct from x.despues;

  for r in
    select 'relaciones_laborales' t, md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) h from public.relaciones_laborales x
    union all select 'eventos_laborales', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.eventos_laborales x
    union all select 'idse_movimientos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_movimientos x
    union all select 'idse_archivos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_archivos x
    union all select 'personal_registros_pago', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal_registros_pago x
    union all select 'personal (ids, empleado_id, tenant)', md5(coalesce(string_agg(x.id || x.empleado_id || x.tenant_id, '' order by x.id), '')) from public.personal x
    union all select 'personal de otros tenants', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal x
     where x.tenant_id <> (select id from public.tenants where nombre = 'PILOTO SINTETICO 500')
  loop
    if r.h is distinct from (select h from _huella_antes where t = r.t) then
      raise exception 'BeeHuman: % cambió durante la adaptación; se revierte todo.', r.t;
    end if;
  end loop;
  if exists (select 1 from public.personal p join public.tenants t on t.id = p.tenant_id
              where t.nombre = 'PILOTO SINTETICO 500'
                and ((p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss)) or concat(p.nombres, p.primer_apellido, p.segundo_apellido) ~ '[0-9]')) then
    raise exception 'BeeHuman: quedaron NSS o nombres sin adaptar.';
  end if;
end $$;

commit;
