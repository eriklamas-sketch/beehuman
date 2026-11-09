-- =====================================================================
-- BeeHuman · Adaptación de datos SINTÉTICOS a los validadores IDSE
-- 9-nov-2026 · Solo beehuman-pruebas, tenant «PILOTO SINTETICO 500».
-- Acompaña a 20261109000200_idse_validadores_guia (NSS con dígito
-- verificador; nombres sin dígitos). NO es para producción.
--
-- Qué cambia (y nada más, ni siquiera la autoría de la ficha):
--   · personal.nss  — solo los NSS de 11 dígitos con dígito verificador
--     incorrecto. Nuevo NSS = '9900' + número del empleado_id (6 dígitos)
--     + dígito verificador. Único por construcción (empleado_id es único);
--     el script comprueba que no choque con ningún NSS de la base.
--     Los NSS válidos y los vacíos se quedan como están.
--   · personal.nombres y personal.nombre_completo — dígitos → letras
--     (0→A … 9→J): «PERSONA 0007» → «PERSONA AAAH». Misma longitud,
--     sin duplicados (el script lo comprueba).
-- Qué NO cambia: ninguna otra columna de personal (ni actualizado_por /
-- actualizado_en: la actualización corre sin disparadores y el propio script
-- valida el NSS con la regla más estricta), relaciones laborales, eventos,
-- movimientos y archivos IDSE, esquemas de pago, ni nada de otros tenants.
-- El script compara huellas antes y después y aborta si algo más cambió.
-- Trazabilidad: respaldo.datos_sinteticos_idse_20261109 (valores anteriores y
-- nuevos, incluida la autoría) y una fila en Movimientos por campo cambiado
-- (usuario «sistema · adaptación datos sintéticos IDSE 20261109»); el script
-- comprueba que sean exactamente una por cambio real.
-- Los archivos IDSE ya generados conservan los datos anteriores (histórico).
-- ANTES DE EJECUTAR: confirmar los conteos del precheck (9-nov: 300 NSS,
-- 500 nombres, 500 nombres completos). Si no coinciden, no cambia nada.
-- Todo ocurre en UNA transacción: cualquier error la revierte completa
-- (incluida la tabla de respaldo).
-- Reversión: 20261109000300_reversion_adaptar_datos_sinteticos_idse.sql
-- =====================================================================
begin;
-- Sin disparadores: así solo cambian las 3 columnas (los disparadores de la
-- ficha sobrescribirían actualizado_por/actualizado_en; el de Movimientos exige
-- un usuario autenticado). Las validaciones las hace este script.
set local session_replication_role = replica;

do $$
declare
  c_tenant   constant text := 'PILOTO SINTETICO 500';
  c_nss      constant int := 300;     -- ← NSS a corregir según el precheck
  c_nombres  constant int := 500;     -- ← nombres con dígitos según el precheck
  c_completo constant int := 500;     -- ← nombres completos con dígitos según el precheck
  c_marca    constant text := 'sistema · adaptación datos sintéticos IDSE 20261109';
  v_tenant uuid; n int; n_nss int; n_nom int; n_nc int; r record;
begin
  -- 1. Entorno y doble ejecución
  if (select count(*) from public.tenants where nombre = c_tenant) <> 1 then
    raise exception 'BeeHuman: debe existir exactamente un tenant «%»; no se cambió nada.', c_tenant;
  end if;
  select id into v_tenant from public.tenants where nombre = c_tenant;
  -- (tras una reversión el respaldo queda renombrado y se puede volver a aplicar)
  if to_regclass('respaldo.datos_sinteticos_idse_20261109') is not null then
    raise exception 'BeeHuman: esta adaptación ya se aplicó en este entorno.';
  end if;
  if to_regprocedure('public.es_nss_imss_valido(text)') is null then
    raise exception 'BeeHuman: falta la migración 20261109000200_idse_validadores_guia.';
  end if;

  -- 2. Huella de lo que NO debe cambiar
  create temporary table _huella on commit drop as
  select 'relaciones_laborales' t, md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) h from public.relaciones_laborales x
  union all select 'eventos_laborales', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.eventos_laborales x
  union all select 'idse_movimientos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_movimientos x
  union all select 'idse_archivos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_archivos x
  union all select 'idse_archivo_renglones', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.archivo_id, x.linea), '')) from public.idse_archivo_renglones x
  union all select 'personal_registros_pago', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal_registros_pago x
  union all select 'personal de otros tenants', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal x where x.tenant_id <> v_tenant
  union all select 'personal del piloto sin nss/nombres/nombre_completo',
            md5(coalesce(string_agg((to_jsonb(x) - 'nss' - 'nombres' - 'nombre_completo')::text, '' order by x.id), '')) from public.personal x where x.tenant_id = v_tenant
  union all select 'movimientos existentes', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.movimientos x;

  -- 3. Plan
  create temporary table _plan on commit drop as
  select p.id, p.tenant_id, p.empleado_id, p.nss as nss_anterior,
         case when p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss)
              then (select b || ((10 - (select sum(((substr(b, i, 1)::int * (2 - i % 2)) / 10) + ((substr(b, i, 1)::int * (2 - i % 2)) % 10))
                                         from generate_series(1, 10) g(i)) % 10) % 10)::text
                      from (select '9900' || split_part(p.empleado_id, '-', 2) as b) z)
              else p.nss end as nss_nuevo,
         p.nombres as nombres_anterior, translate(p.nombres, '0123456789', 'ABCDEFGHIJ') as nombres_nuevo,
         p.nombre_completo as nombre_completo_anterior, translate(p.nombre_completo, '0123456789', 'ABCDEFGHIJ') as nombre_completo_nuevo,
         p.actualizado_por, p.actualizado_en
    from public.personal p
   where p.tenant_id = v_tenant
     and ((p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss))
          or concat(p.nombres, p.nombre_completo) ~ '[0-9]');

  -- 4. Validaciones del plan (cualquier falla: no cambia nada)
  select count(*) filter (where nss_nuevo is distinct from nss_anterior), count(*) filter (where nombres_nuevo is distinct from nombres_anterior),
         count(*) filter (where nombre_completo_nuevo is distinct from nombre_completo_anterior)
    into n_nss, n_nom, n_nc from _plan;
  if n_nss <> c_nss or n_nom <> c_nombres or n_nc <> c_completo then
    raise exception 'BeeHuman: el plan da % NSS, % nombres y % nombres completos; se esperaban %, % y %. No se cambió nada.',
      n_nss, n_nom, n_nc, c_nss, c_nombres, c_completo;
  end if;
  if exists (select 1 from _plan where tenant_id <> v_tenant) then
    raise exception 'BeeHuman: el plan incluye personas de otro tenant; no se cambió nada.';
  end if;
  if exists (select 1 from _plan where nss_nuevo is distinct from nss_anterior
               and (split_part(empleado_id, '-', 2) !~ '^[0-9]{6}$' or nss_nuevo !~ '^[0-9]{11}$' or not public.es_nss_imss_valido(nss_nuevo))) then
    raise exception 'BeeHuman: algún NSS nuevo no es válido (revisa el formato del empleado_id).';
  end if;
  if exists (select nss_nuevo from _plan where nss_nuevo is distinct from nss_anterior group by 1 having count(*) > 1)
     or exists (select 1 from _plan a join public.personal o on o.nss = a.nss_nuevo and o.id <> a.id where a.nss_nuevo is distinct from a.nss_anterior) then
    raise exception 'BeeHuman: algún NSS nuevo se repite o ya existe en la base; no se cambió nada.';
  end if;
  if exists (select 1 from _plan where nombres_nuevo ~ '[0-9]' or nombre_completo_nuevo ~ '[0-9]'
                or char_length(nombres_nuevo) <> char_length(nombres_anterior) or char_length(nombre_completo_nuevo) <> char_length(nombre_completo_anterior)
                or regexp_replace(nombres_anterior, '\D', '', 'g') <> regexp_replace(nombre_completo_anterior, '\D', '', 'g')) then
    raise exception 'BeeHuman: algún nombre no se transforma de forma consistente con su nombre completo; no se cambió nada.';
  end if;
  if exists (select 1 from (select coalesce(pl.nombre_completo_nuevo, p.nombre_completo) nc from public.personal p
                              left join _plan pl on pl.id = p.id where p.tenant_id = v_tenant) x group by nc having count(*) > 1)
     or exists (select 1 from (select coalesce(pl.nombres_nuevo, p.nombres) nb, p.primer_apellido, p.segundo_apellido from public.personal p
                              left join _plan pl on pl.id = p.id where p.tenant_id = v_tenant) x group by x.nb, x.primer_apellido, x.segundo_apellido having count(*) > 1) then
    raise exception 'BeeHuman: algún nombre nuevo duplicaría a otra persona; no se cambió nada.';
  end if;

  -- 5. Respaldo y cambio
  create table respaldo.datos_sinteticos_idse_20261109 as select *, now() as aplicado_en from _plan;
  alter table respaldo.datos_sinteticos_idse_20261109 add primary key (id);
  revoke all on respaldo.datos_sinteticos_idse_20261109 from public, anon, authenticated;

  update public.personal p set nss = pl.nss_nuevo, nombres = pl.nombres_nuevo, nombre_completo = pl.nombre_completo_nuevo
    from _plan pl where p.id = pl.id and p.tenant_id = v_tenant;
  get diagnostics n = row_count;
  if n <> (select count(*) from _plan) then raise exception 'BeeHuman: se actualizaron % personas y el plan tiene %.', n, (select count(*) from _plan); end if;

  -- 6. Trazabilidad: una fila por campo realmente cambiado
  insert into public.movimientos (personal_id, tenant_id, campo, valor_anterior, valor_nuevo, usuario, usuario_id, fecha)
  select id, tenant_id, x.campo, x.antes, x.despues, c_marca, null, now()
    from respaldo.datos_sinteticos_idse_20261109,
         lateral (values ('nss', nss_anterior, nss_nuevo), ('nombres', nombres_anterior, nombres_nuevo),
                         ('nombre_completo', nombre_completo_anterior, nombre_completo_nuevo)) x(campo, antes, despues)
   where x.antes is distinct from x.despues;
  get diagnostics n = row_count;
  if n <> c_nss + c_nombres + c_completo then
    raise exception 'BeeHuman: se registraron % movimientos y se esperaban %.', n, c_nss + c_nombres + c_completo;
  end if;
  if exists (select 1 from public.movimientos m join public.personal p on p.id = m.personal_id
              where m.usuario = c_marca and m.fecha = now() and m.valor_nuevo is distinct from
                    case m.campo when 'nss' then p.nss when 'nombres' then p.nombres when 'nombre_completo' then p.nombre_completo end
                 or m.valor_anterior is not distinct from m.valor_nuevo) then
    raise exception 'BeeHuman: algún registro de Movimientos no corresponde a un cambio real.';
  end if;

  -- 7. Nada más cambió (incluidos los movimientos que ya existían)
  for r in
    select 'relaciones_laborales' t, md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) h from public.relaciones_laborales x
    union all select 'eventos_laborales', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.eventos_laborales x
    union all select 'idse_movimientos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_movimientos x
    union all select 'idse_archivos', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.idse_archivos x
    union all select 'idse_archivo_renglones', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.archivo_id, x.linea), '')) from public.idse_archivo_renglones x
    union all select 'personal_registros_pago', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal_registros_pago x
    union all select 'personal de otros tenants', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.personal x where x.tenant_id <> v_tenant
    union all select 'personal del piloto sin nss/nombres/nombre_completo',
              md5(coalesce(string_agg((to_jsonb(x) - 'nss' - 'nombres' - 'nombre_completo')::text, '' order by x.id), '')) from public.personal x where x.tenant_id = v_tenant
    union all select 'movimientos existentes', md5(coalesce(string_agg(to_jsonb(x)::text, '' order by x.id), '')) from public.movimientos x where not (x.usuario = c_marca and x.fecha = now())
  loop
    if r.h is distinct from (select h from _huella where t = r.t) then
      raise exception 'BeeHuman: % cambió durante la adaptación; se revierte todo.', r.t;
    end if;
  end loop;
  if exists (select 1 from public.personal p where p.tenant_id = v_tenant
                and ((p.nss ~ '^[0-9]{11}$' and not public.es_nss_imss_valido(p.nss)) or concat(p.nombres, p.primer_apellido, p.segundo_apellido, p.nombre_completo) ~ '[0-9]')) then
    raise exception 'BeeHuman: quedaron NSS o nombres sin adaptar.';
  end if;
  raise notice 'BeeHuman: % personas adaptadas (% NSS, % nombres, % nombres completos); % filas en Movimientos.', (select count(*) from _plan), n_nss, n_nom, n_nc, n;
end $$;

commit;
