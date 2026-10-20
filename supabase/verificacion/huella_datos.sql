-- =====================================================================
-- BeeHuman V2.0 · Huella de DATOS por tabla (SOLO LECTURA)
-- Filas y md5 del contenido de cada tabla, sin las columnas que agrega
-- V2.0 (rol, personal_id, numero_interno_trabajador, autoría, usuario_id).
-- Da el mismo resultado antes y después de migrar si ningún dato cambió.
-- Línea base de producción tomada el 17-oct-2026 (ver cierre).
-- =====================================================================
with x as (
  select 'personal' tabla, t.id::text k, to_jsonb(t) j from public.personal t
  union all select 'personal_registros_pago', t.id::text, to_jsonb(t) from public.personal_registros_pago t
  union all select 'movimientos', t.id::text, to_jsonb(t) from public.movimientos t
  union all select 'empresas', t.id::text, to_jsonb(t) from public.empresas t
  union all select 'empresas_registros_patronales', t.id::text, to_jsonb(t) from public.empresas_registros_patronales t
  union all select 'usuarios_tenant', t.user_id::text, to_jsonb(t) from public.usuarios_tenant t
  union all select 'tenants', t.id::text, to_jsonb(t) from public.tenants t
  union all select 'proyectos', t.id::text, to_jsonb(t) from public.proyectos t
  union all select 'periodicidades', t.id::text, to_jsonb(t) from public.periodicidades t
  union all select 'clasificaciones_personal', t.id::text, to_jsonb(t) from public.clasificaciones_personal t
  union all select 'areas', t.id::text, to_jsonb(t) from public.areas t
  union all select 'departamentos', t.id::text, to_jsonb(t) from public.departamentos t
  union all select 'puestos', t.id::text, to_jsonb(t) from public.puestos t
  union all select 'localidades', t.id::text, to_jsonb(t) from public.localidades t
  union all select 'centros_costo', t.id::text, to_jsonb(t) from public.centros_costo t
  union all select 'combos', t.id::text, to_jsonb(t) from public.combos t
  union all select 'combo_conceptos', t.id::text, to_jsonb(t) from public.combo_conceptos t
  union all select 'conceptos_percepcion', t.id::text, to_jsonb(t) from public.conceptos_percepcion t
  union all select 'personal_percepciones', t.id::text, to_jsonb(t) from public.personal_percepciones t
)
select tabla, count(*) filas,
       -- personal_id solo se excluye en usuarios_tenant (en otras tablas es una columna de V1).
       md5(string_agg((j - 'rol' - (case when tabla = 'usuarios_tenant' then 'personal_id' else '' end)
                         - 'numero_interno_trabajador' - 'creado_por'
                         - 'actualizado_por' - 'actualizado_en' - 'usuario_id')::text, '|' order by k)) huella
from x group by tabla order by tabla;
