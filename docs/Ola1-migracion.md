# Ola 1 · Incidencias — estado de la migración

| Entorno | Estado |
|---|---|
| beehuman-pruebas (`sflvpgkmtaxzogpgetxn`) | **Aplicada** el 28-oct-2026, registrada como `20261028002647 ola1_hoja_coordinador` |
| Producción (`vovyvvpwtjdlswerfjqb`) | **No aplicada.** Requiere autorización expresa de Erik |

La app trae el interruptor `OLA1_ACTIVA = false` en `app/index.html`. Mientras esté apagado,
la pestaña Incidencias no se muestra y `app/incidencias.js` no se carga. Encenderlo en
producción exige antes aplicar la migración en producción.

## Archivos

| Archivo | Uso | SHA-256 |
|---|---|---|
| `supabase/pendiente/20261028000000_ola1_hoja_coordinador.sql` | Migración (13 tablas `inc_`, 19 políticas, 24 funciones, 8 disparadores, carga inicial) | `c05bc0d5…2103` |
| `supabase/reversion/20261028000000_reversion_ola1.sql` | Reversión completa | `bb2ff5a6…d4e9` |
| `supabase/verificacion/ola1/pruebas_ola1.py` | 90 pruebas de base (local, Postgres 16) | |
| `supabase/verificacion/ola1/evidencia_pruebas_ola1.txt` | Resultado de las pruebas de base | |
| `supabase/verificacion/ola1/espejo_permisos_pruebas.sql` | Reproduce en local los permisos de beehuman-pruebas | |
| `supabase/verificacion/ola1/ui_ola1.py`, `semilla_ui.sql`, `montar_ui.sh`, `servicios.sh` | 33 pruebas de pantallas (Playwright + PostgREST local, datos ficticios) | |

Está en `supabase/pendiente/` y no en `supabase/migrations/` a propósito: así ninguna
herramienta la aplica a producción por accidente. Al aplicarla en producción se mueve a
`supabase/migrations/` con la versión que registre Supabase.

## Pruebas

- Base: 90/90 en local y 28 comprobaciones en vivo en beehuman-pruebas.
- Pantallas: 33/33 en local. Pendiente: vista previa contra beehuman-pruebas.

## Pendientes de base (autorización aparte, primero en pruebas)

- Función de catálogos (proyectos) para el coordinador.
- Función que liste responsables.
- Fechas del servidor en America/Mexico_City.
