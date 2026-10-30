# Alertas de aniversario para revisar el SBC (30-oct-2026)

Solo aviso: no genera, presenta ni marca movimientos ante el IMSS. El aniversario no siempre implica modificar el SBC.

## Regla
- Fecha base, en este orden: fecha de antigüedad → fecha de alta IMSS → fecha de ingreso (inicio de contrato). La pantalla muestra cuál se usó.
- Ventana: 30 días antes y 30 días después del aniversario (`ANIVERSARIO_DIAS_ANTES/DESPUES`).
- Una alerta por persona y aniversario (cada aniversario está a 365 días del siguiente; nunca caen dos en la ventana).
- 29 de febrero → 28 de febrero en años no bisiestos. Personas en Baja: sin alerta. Antes del primer año: sin alerta.
- Sin ninguna fecha válida → «sin fecha» (se señala aparte). Fechas inválidas se tratan como faltantes.
- Fecha de hoy: la local del navegador (no UTC).

## Dónde aparece
- Resumen → «Para revisar»: tabla con persona, empresa, aniversario, años cumplidos, cuándo (en N días / cumple hoy / hace N días) y fecha base; y la lista de personas sin fecha.
- Personal → filtro «Pendientes de RH»: «Aniversario para revisar SBC (±30 días)» y «Sin fecha de antigüedad, alta IMSS ni ingreso».
- No cambia la tarjeta «Pendientes» del tablero.

## Pruebas
- Lógica: `supabase/verificacion/aniversarios/pruebas_aniversario.js` — 22/22 (futuro, límites de 30 días, del día, pasado, cambio de año en ambos sentidos, 29 de febrero en año bisiesto y no bisiesto, primer año, prioridad de fuentes, datos incompletos e inválidos, fecha con hora, persona en Baja, sin duplicados). Evidencia en `evidencia_pruebas.txt`.
- Pantalla: `ui_aniversarios.py` con `semilla_aniversarios.sql` (fechas relativas a hoy): 3 alertas correctas, 5 personas sin fecha, filtros 3 y 5, sin errores, sin desborde en móvil.
- Regresión: Personal y ficha idénticas; Ola 1 33/33.

## Siguiente
Cuando exista el registro de movimientos IDSE, una modificación de salario con fecha posterior al aniversario podrá cerrar la alerta.
