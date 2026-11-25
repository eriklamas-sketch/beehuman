# Excel canónico V1: ajustes de revisión y roadmap (25-nov-2026)

**Autorización:** Erik, 25-nov 09:04 (ronda 1) y 09:14 (ronda 2).
**Diseño:** `docs/Excel-canonico-V1-diseno.md`.

## Ronda 1 (09:04)

| Punto | Cambio |
|---|---|
| A05 | El mensaje lleva el nombre: «ROSA LUNA MORA — sin número interno.» |
| Validaciones y Faltantes | Columna nueva `nombre_completo` |
| PRELIM Faltantes | `numero_interno`, `nombre_completo` y `persona_id` |
| Orden de Validaciones | Advertencias, luego informativos y al final los bloqueos |
| A07 | Solo percepciones fuera de bruto y deducciones asignadas a un esquema que no es bruto. Una deducción sin esquema ya no genera A07 |
| A11 (nuevo) | Deducción sin esquema cuando la persona tiene 0 o más de 1 esquema `bruto` |

## Ronda 2 (09:14)

| Punto | Cambio |
|---|---|
| B07 en `listo` | `no_aplica`: «No aplica: el periodo aún no ha sido procesado.» En `procesado` sigue siendo `superada` |
| Faltantes de importe | Una fila por línea por decidir, con su esquema («— IMSS / bruto», «— EFECTIVO / neto»), su `persona_id` exacto y `referencia_id` = `hoja_id`. Si el conteo no es igual al del concentrado, BP3 |

**Por qué se arman desde las líneas:** el texto del concentrado viene de `inc__faltantes_base` (B-a, ya en `main`) y no trae el esquema. Cambiar esa función modificaría también la pantalla del Concentrado.

## Evidencia

- **Pruebas de base:** 77/77 (`supabase/verificacion/ola1/evidencia_pruebas_excel_canonico.txt`).
- **Pruebas de pantalla:** 37/37 (`evidencia_ui_excel_canonico.txt`).
- **Muestras:** Erik revisó los archivos de preliminar y oficial de Constructora Demo (datos ficticios).
- **`beehuman-pruebas`:** conserva la versión del 24-nov. Actualizarla es una decisión aparte.

## Roadmap

### Adaptador NOI: criterios obligatorios (diseño §14)

- **NOI-CA1 a NOI-CA4 (antes CA24):**
  - identificar el formato;
  - rechazar `beehuman.preliminar` de forma explícita;
  - no importar nada, ni parcialmente;
  - aceptar solo un `beehuman.canonico` válido.
- **Deducciones sin esquema:**
  - enviarlas al único esquema fiscal (bruto) de la persona, si el concepto tiene mapeo para NOI;
  - bloquear si hay 0 o más de 1 esquema fiscal, o si el concepto no tiene mapeo;
  - nunca asignar el destino cuando hay ambigüedad.

### Configuración de conceptos (V-3)

Impedir que un concepto de unidad «importe» se configure «sin importe». Hoy no hay casos, y B06 ya lo bloquea en el oficial. No es urgente.
