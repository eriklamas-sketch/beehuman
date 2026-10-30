# Normalización de periodicidades (30-oct-2026)

## Diagnóstico
El catálogo `periodicidades` es por tenant y no impedía nombres que solo difieren en mayúsculas.

| Base | Tenant | Situación |
|---|---|---|
| beehuman-pruebas | PILOTO SINTETICO 500 | «Quincenal» (sin uso) duplicaba «QUINCENAL» (317 esquemas) → era el duplicado visible en Incidencias |
| Producción | BeeHuman — Demo | MENSUAL (30 días), QUINCENAL, SEMANAL — sin duplicados |
| Producción | BeeHuman — Entorno inicial | Catorcenal, Mensual (30.4, sin uso), Quincenal, Semanal — sin duplicados |

En producción los nombres parecidos están en **tenants distintos**; cada usuario solo ve los de su tenant, así que no hay duplicados que unificar. Decisión de Erik: Mensual = 30 días.

## Migración
`supabase/pendiente/20261030000000_normalizar_periodicidades.sql` (reversión en `supabase/reversion/`).
- Por tenant y nombre normalizado: conserva la más usada (empate: la escrita en mayúsculas), mueve las referencias de `personal`, `personal_registros_pago` e `inc_periodos`, y borra las duplicadas. No cambia sueldos, días propios, fechas ni importes; la canónica conserva sus días.
- Respaldo de duplicadas y referencias movidas en el esquema `respaldo` (sin acceso para `anon` ni `authenticated`).
- Índice único `periodicidades_tenant_nombre_unico` (tenant, MAYÚSCULAS sin espacios): impide nuevos duplicados.

## Pruebas
- Local (`supabase/verificacion/periodicidades/escenario_local.sql`, réplica del patrón de producción con referencias en las tres tablas): 3 duplicadas unificadas; referencias completas; sueldos, días y fechas idénticos; sin sellar autoría; el índice rechaza « semanal » y «CATORCENAL» repetidos y acepta «Bimestral»; segunda corrida sin cambios; reversión deja el estado idéntico al original; volver a aplicar da el mismo resultado; pantallas de Personal y ficha sin cambios.
- beehuman-pruebas (aplicada el 30-oct, `normalizar_periodicidades`): «Quincenal» unificada en «QUINCENAL»; 646 esquemas con la misma huella de importes y fechas antes y después; autoría de `personal` sin cambios; índice creado.

## Producción
Pendiente de autorización. Efecto esperado: 0 periodicidades unificadas; solo se agrega el índice único.
