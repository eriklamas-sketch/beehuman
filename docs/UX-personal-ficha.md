# UX · Personal y ficha (línea de desarrollo `integracion/app`)

Commit: `6b64d33`. Alcance aprobado en `claude/UX-personal-ficha-alcance.md` (proyecto). Solo `app/index.html`.

## Cambios
| Zona | Cambio | Tipo |
|---|---|---|
| Tabla de Personal | Clases por columna (ID discreto, nombre destacado, secundarias en gris); estatus con color por clase; esquemas como badges (`claseBadgeEsquema`, `badgeEsquemaHTML`) | Plantilla de fila + CSS |
| Ficha | Siete apartados: columna lateral fija (≥ 900 px) o tira horizontal fija (< 900 px); el apartado activo se centra en la tira y la ficha regresa al inicio del apartado | CSS + 10 líneas en `cambiarSeccionDetalle` |
| Registros de pago | Tarjeta por registro; «Vigentes» y «Históricos» (plegable, recuerda su estado) | `renderRegistrosPagoDetalle`; acciones con `accionesRegistroPagoHTML` sin cambios |
| Cambios sin guardar | Al cerrar: compara los campos de la ficha con su estado al abrir o tras guardar, y el formulario de registro de pago con su estado al empezar a usarlo; si difieren, `confirm` (cancelar regresa, aceptar descarta) | `cerrarDetalle` + funciones nuevas |

Estilos en el bloque `@@UX_PERSONAL_FICHA` al final de la hoja; se puede retirar completo.

## Pruebas (base local con permisos de beehuman-pruebas, datos ficticios)
`supabase/verificacion/ux/ux_pruebas.py` con `semilla_ux.sql`, ejecutado antes (da7119b) y después (6b64d33):
- Idénticos antes/después: conteo, paginación (50 + 13), filtro por estatus, búsqueda, orden por ID, CSV de personal (todo y filtrado), CSV de esquemas (Administrador y Nómina) byte por byte, guardado de campos en dos apartados distintos tras navegar, registro de movimientos, cerrar / reactivar / editar registro de pago, columnas de Consulta, sin desborde en móvil, sin errores de JavaScript.
- Envíos de escritura a la base idénticos antes/después (5 operaciones).
- Única diferencia, la esperada: con cambios sin guardar, cerrar pide confirmación; cancelar conserva lo escrito; aceptar descarta (no se guarda nada). Sin cambios, o cambiando y regresando al valor original, no avisa.
- Regresión: pantallas Ola 1 33/33; inicio de sesión sin cambios.
