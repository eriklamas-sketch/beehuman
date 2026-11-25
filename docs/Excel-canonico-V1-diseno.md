# Excel canónico de BeeHuman V1 y reporte preliminar de acumulado: diseño funcional (24-nov-2026, actualizado 25-nov)

**Autorizaciones de Erik:**
- 24-nov 15:59: diseño.
- 24-nov 16:21: revisión final (E-1 a E-6, correcciones A–D).
- 24-nov 16:29: ajuste P-1, que crea dos modalidades de exportación.
- 24-nov 16:35: implementación.
- **25-nov 09:04:** cuatro ajustes de presentación, criterio de A07 para deducciones, regla de deducciones para NOI y CA24 como requisito del adaptador (§3.11, §7.2, §12.4 y §14).
- **25-nov 09:14:** B07 «no_aplica» en periodos no procesados y faltantes de importe por línea, con su esquema (§3.11 y §12.4).

**Estado:** implementado en `integracion/app`. `beehuman-pruebas` conserva la versión del 24-nov. Producción no tiene nada.

**Contrato:** los cambios del 25-nov entran en la versión **1.0**, porque el formato todavía no se ha liberado ni lo consume ningún adaptador:
- la columna `nombre_completo` en Validaciones y en Faltantes;
- el aviso A11;
- el orden de Validaciones;
- el valor `no_aplica`.

**Base verificada en el repositorio:**
- `inc__concentrado_base`, `inc_concentrado_periodo`, `inc__huella_de`, `inc_firma_periodo_estado` e `inc_firmar_periodo`, de la migración B-a (`20261123000000`);
- los índices únicos de Ola 1;
- las tablas `inc_conceptos`, `inc_importes`, `inc_eventos`, `cred_creditos`, `personal` y `eventos_laborales`.

---

## 0. Dos modalidades de exportación

| | **Excel canónico oficial** | **Reporte preliminar de acumulado** |
|---|---|---|
| Para qué | Entregar lo autorizado. Es el **único** archivo válido para los adaptadores de nómina | Que Nómina revise avances, detecte faltantes y anticipe datos **mientras el periodo se prepara** |
| Cuándo está disponible | Periodo en estado `listo` o `procesado` | Periodo en estado `preliminar` |
| Firma de Nómina | **Obligatoria y vigente**; huella actual = huella firmada | **No se requiere.** Se informa su estado, sin exigirlo |
| Garantía | Reproduce exactamente el concentrado firmado | Ninguna: son datos que **pueden cambiar** |
| Identificador del formato | `beehuman.canonico` 1.0 | `beehuman.preliminar` 1.0 |
| Huellas | `huella_firma`, `huella_datos_exportados`, `huella_archivo` (§4) | `huella_concentrado_actual` y `huella_datos_exportados` (§12.5) |
| Bloqueos | B01–B08 | BP1–BP3 (§12.6) |
| Efecto en firma, huella o estado | Ninguno | Ninguno |
| Registro | Evento `exportacion` con modalidad `oficial` | Evento `exportacion` con modalidad `preliminar` |

**Organización del documento:**
- Las secciones 1 a 11 describen el **Excel oficial**.
- La sección 12 describe el **reporte preliminar** y cómo reutiliza lo anterior.
- La sección 14 fija los requisitos del adaptador NOI que dependen de este formato.

---

## 0.1 Decisiones vigentes

| # | Decisión | Estado |
|---|---|---|
| — | Solo las personas del periodo | Aprobada |
| — | Oficial solo con la firma de Nómina vigente; si se invalida, no se exporta hasta volver a firmar | Aprobada |
| — | NOI es el primer adaptador; CONTPAQi va después. Ningún archivo calcula nómina ni lleva reglas de NOI | Aprobada |
| E-1 | Hoja aparte «Esquemas» | Aprobada |
| E-2 | RFC, CURP y NSS en Personas, fuera de la firma | Aprobada |
| E-3 | Validación y registro de la exportación en el servidor | Aprobada |
| E-4 | Formato `.xlsx` | Aprobada |
| E-5 | B07 bloquea un periodo procesado que cambió después | Aprobada |
| E-6 | Observaciones de los coordinadores como informativas, fuera de la firma | Aprobada |
| P-1 | El oficial solo en `listo` o `procesado` (B08). En `preliminar` se ofrece el reporte preliminar de acumulado | Aprobada |
| R-1 | **25-nov:** avisos y faltantes muestran el nombre de la persona; Validaciones ordena advertencias → informativos → bloqueos | Aprobada |
| R-2 | **25-nov:** una deducción sin esquema **no** es A07. Es válida, y el adaptador la dirige al único esquema fiscal de la persona; si no hay exactamente uno, A11 | Aprobada |
| R-3 | **25-nov:** CA24 pasa a criterio obligatorio del adaptador NOI (§14) | Aprobada |
| R-4 | **25-nov:** V-3 (concepto «importe» configurado «sin importe») queda en el roadmap; B06 ya impide exportarlo en el oficial | Aprobada |
| R-5 | **25-nov:** B07 se informa como `no_aplica` si el periodo no está procesado; los faltantes de importe del preliminar van uno por línea, con su esquema | Aprobada |

---

## 1. Principios del Excel oficial

1. **Reproduce lo firmado y no recalcula la nómina.** Las filas materiales salen del documento canónico (`canonico.*`). El servidor lo arma en el mismo momento en que comprueba que su huella es igual a la firmada.
2. **Hay tres huellas distintas** (§4): `huella_firma`, `huella_datos_exportados` y `huella_archivo`. Los datos descriptivos (nombres, RFC, CURP, NSS, proyecto, coordinadores) **nunca** entran en la firma.
3. **Cantidades e importes van en hojas separadas, y bruto y neto nunca se suman.**
4. **Los complementos posteriores al procesamiento no entran.** Las hojas de detalle llevan `periodo_origen_id` para el traslado futuro.
5. **El formato es neutral y versionado.** NOI es un adaptador.

---

## 2. Reglas generales del archivo oficial

| Regla | Definición |
|---|---|
| Formato | `.xlsx` (Office Open XML). El adaptador NOI producirá aparte su `.xls` 97-2003 |
| Nombre del archivo | `BeeHuman_<empresa>_<inicio aaaa-mm-dd>_<fin aaaa-mm-dd>_exp-<n>.xlsx`, sin acentos ni espacios. `n` = número de exportación oficial de esa firma (§4.4) |
| Hojas, en este orden | Resumen, Personas, Esquemas, Incidencias, Cantidades, Importes, Descuentos, Movimientos, Catálogos, Validaciones |
| Encabezado | Fila 1. Nombres de columna exactos, en `snake_case` y sin acentos; **esos nombres son el contrato**. Cada encabezado lleva una nota de Excel con su descripción, que no forma parte del contrato |
| Datos | Desde la fila 2. Una fila por registro, sin filas de total, sin celdas combinadas y **sin fórmulas** |
| Texto | **Siempre como celda de texto explícita** (tipo cadena de OOXML). Un texto que empiece con `=`, `+`, `-` o `@` se escribe como texto, sin evaluarse y sin agregarle caracteres |
| Fecha sin hora | Celda de fecha de Excel, con formato visible `dd/mm/aaaa` |
| Fecha con hora | Solo en Resumen y Validaciones, como texto ISO 8601 en la zona **`America/Mexico_City`**, con el desplazamiento que corresponda a esa fecha y hora (por ejemplo `2026-11-24T16:21:00-06:00`) |
| Importes | Número con 2 decimales exactos; formato visible `#,##0.00` |
| Cantidades | Número tal como se capturó; formato visible `0.####` |
| Booleanos | Valor lógico de Excel |
| Identificadores | UUID como texto, en las columnas `*_id` |
| Vacío y cero | **Vacío** = no aplica o no existe. **Cero** = valor real capturado o decidido. Nunca se escribe 0 para decir «no hay» |
| Solo lectura | `numero_interno` y `nombre_completo` fuera de Personas, y `concepto_clave`, son de referencia. Los adaptadores relacionan por `*_id` |
| Confidencialidad | La propiedad «Confidencial» es **solo un metadato**. No cifra ni protege el archivo |

**Columnas comunes de trazabilidad** en Incidencias, Cantidades e Importes: `hoja_id`, `hoja_tipo` (`normal` o `complemento`), `version_hoja` y `periodo_origen_id`. En V1, `periodo_origen_id` siempre es el periodo del archivo.

---

## 3. Especificación por hoja (Excel oficial)

**Abreviaturas de las tablas:**
- **Obl.:** S = siempre; C = condicional; N = puede ir vacío.
- **Firma:** ✓ = está en el documento canónico firmado; — = descriptivo.
- **Origen:** `canonico.*` y `datos.*` son secciones de `inc__concentrado_base`. «Tabla» = lectura directa de la función de exportación.

### 3.1 Relación entre hojas

```
Resumen ── metadatos, huellas y totales de control
Personas (persona_id) ─┬─ Esquemas      (registro_pago_id)          ◄── Importes.registro_pago_id
                       ├─ Incidencias   (persona_id, fecha, hoja_id)
                       ├─ Cantidades    (hoja_id, persona_id, fecha, concepto_id, tipo_linea)
                       ├─ Importes      (persona_id, hoja_id, concepto_id, relacion_laboral_id, registro_pago_id)
                       ├─ Descuentos    (descuento_id | credito_id)
                       ├─ Movimientos   (evento_id)
                       └─ Validaciones  (persona_id opcional)
Catálogos (catalogo, clave_beehuman) ◄── codigo, concepto_id, tipo_credito, tipo de movimiento, clasificación
```

Los datos de la persona solo viven en Personas y los del concepto solo en Catálogos. Ninguna hoja de detalle guarda totales.

### 3.2 Resumen

**Una fila por dato.** Columnas: `seccion` (S), `clave` (S), `concepto_id` (C), `modalidad` (C), `valor` (S) y `unidad` (C).

| sección | clave | valor | Origen |
|---|---|---|---|
| archivo | `formato` / `version_formato` | `beehuman.canonico` / `1.0` | constantes (§8) |
| archivo | `generado_en` / `generado_por` | fecha y hora en `America/Mexico_City` / correo | servidor; `inc_nombre_usuario()` |
| archivo | `exportacion_numero` | n-ésima exportación **oficial** de esta firma | eventos `exportacion` con modalidad `oficial` (§4.4) |
| archivo | `huella_datos_exportados` / `huella_datos_exportados_anterior` | SHA-256 (§4.2) / la de la exportación oficial anterior de la misma firma, o vacío | servidor y evento anterior |
| archivo | `huella_archivo` | SHA-256 (§4.3) | servidor; la pantalla la recalcula |
| periodo | `empresa`, `empresa_id`, `periodo_id`, `inicio`, `fin`, `dias` | — | `datos.periodo` |
| periodo | `estado` | `listo` o `procesado` | `inc_concentrado_periodo().estado` |
| periodo | `procesado_en` | vacío si no está procesado | `datos.periodo.procesado_en` |
| firma | `firma_estado` | siempre `vigente` | `inc_firma_periodo_estado` |
| firma | `firmado_por` / `firmado_en` | — | evento `firma_nomina` (`nombre`, `creado_en`) |
| firma | `huella_firma` | huella total firmada | `inc_eventos.huella->>'total'` del evento `firma_nomina` |
| firma | `huella_concentrado` | recalculada al exportar; **igual a `huella_firma`** | `inc__huella_de(canonico)` |
| conteo | `personas`, `esquemas`, `filas_incidencias`, `filas_cantidades`, `filas_importes`, `filas_descuentos`, `filas_movimientos`, `advertencias` | número | conteo de las hojas |
| total_dias | código | días | `datos.totales.dias` |
| total_cantidades | `concepto_id` | suma | `datos.totales.cantidades`, sin conceptos de unidad `importe` (§3.6) |
| total_importes | `concepto_id` + `modalidad` | suma | `datos.totales.importes`; la modalidad vacía aparece como `sin_modalidad` |
| total_descuentos | tipo de crédito | suma | `datos.totales.descuentos` |

### 3.3 Personas

**Una fila por persona del periodo** (`canonico.personas`): las que tienen relación laboral en el periodo, más cualquiera que aparezca en una hoja incluida.

| Columna | Tipo | Obl. | Firma | Origen | Regla |
|---|---|---|---|---|---|
| `numero_interno` | texto | C | ✓ | relación principal | Vacío → A05 |
| `nombre_completo` | texto | S | — | `datos.personas[].nombre_completo` | — |
| `rfc` / `curp` / `nss` | texto | N | — | Tabla `personal` | Vacío si no está capturado |
| `registro_patronal` | texto | C | — | `datos.personas[].registro_patronal` | De la relación principal |
| `fecha_ingreso` / `fecha_baja` | fecha | C / N | — | Tabla `relaciones_laborales`, relación principal | — |
| `alta_en_periodo` / `baja_en_periodo` | fecha | N | ✓ | `canonico.personas[]` | Solo dentro del periodo |
| `dias_vigentes` | entero | S | ✓ | `canonico.personas[].dias_vigentes` | 0 es válido (A03) |
| `relaciones_en_periodo` | entero | S | ✓ | número de `canonico.personas[].relaciones` | Más de 1 → A04 |
| `esquemas_en_periodo` | entero | S | ✓ | filas de la persona en `canonico.esquemas` | 0 → A02 |
| `proyecto` | texto | N | — | `datos.personas[].proyecto` | — |
| `coordinadores` | texto | N | — | `datos.personas[].coordinadores`, unidos con « · » | — |
| `con_incidencias` | booleano | S | — | `datos.personas[].con_incidencias` | — |
| `persona_id` | texto | S | ✓ | `canonico.personas[].personal_id` | **Llave** |
| `relacion_laboral_id` | texto | C | ✓ | relación principal | — |

- **La relación principal** sigue la regla `rel_pri` del concentrado: primero la que tiene registro patronal, luego el ingreso más reciente y luego el registro más reciente.
- **Orden de filas:** `numero_interno` (vacíos al final), luego `nombre_completo`, luego `persona_id`, con comparación binaria UTF-8.

### 3.4 Esquemas

**Una fila por esquema de pago vigente en el periodo** (`canonico.esquemas`).

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `clasificacion` | texto | S | ✓ (`clasificacion_id`) | `clasificaciones_personal.nombre` |
| `modalidad` | texto | S | ✓ | `modalidad_sueldo`: `bruto` o `neto` |
| `sueldo` | número de 2 decimales | S | ✓ | canónico |
| `dias_periodo` | número | S | ✓ | canónico |
| `fecha_inicio` / `fecha_fin` | fecha | S / N | ✓ | canónico |
| `activo` | booleano | S | ✓ | canónico |
| `registro_patronal` | texto | C | ✓ (`registro_patronal_id`) | `empresas_registros_patronales.registro_patronal` |
| `persona_id` / `registro_pago_id` / `relacion_laboral_id` | texto | S / S / C | ✓ | canónico |

- **Llave:** `registro_pago_id`.
- **Orden:** el de persona, luego `fecha_inicio`, luego `registro_pago_id`.
- **El archivo no recalcula el salario diario.**

### 3.5 Incidencias

**Una fila por persona, día y hoja con un código** (`canonico.dias`).

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `fecha` | fecha | S | ✓ | canónico |
| `codigo` | texto | S | ✓ | `F`, `I`, `D`, `V` o `P` |
| `codigo_nombre` | texto | S | — | Falta, Incapacidad, Descanso, Vacaciones o Permiso |
| `proyecto` / `centro_costo` | texto | N | — | celdas de hojas no posteriores |
| `hoja_tipo` / `version_hoja` | texto / entero | S | ✓ | `canonico.hojas` |
| `persona_id` / `hoja_id` | texto | S | ✓ | canónico |
| `periodo_origen_id` | texto | S | — | el periodo |

- **Llave:** (`persona_id`, `fecha`, `hoja_id`).
- **Los días se escriben uno por uno.** Los adaptadores forman los rangos.
- **Orden:** el de persona, luego `fecha`, luego `hoja_id`.

### 3.6 Cantidades

**Una fila por línea de cantidad** (`canonico.cantidades`), **solo de conceptos con unidad `horas`, `turnos` o `dias`.**

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `fecha` | fecha | S | ✓ | canónico |
| `concepto_clave` / `unidad` | texto | S | — | `inc_conceptos` |
| `cantidad` | número | S | ✓ | canónico; un ajuste puede ser negativo |
| `tipo_linea` | texto | S | ✓ | `captura` o `ajuste` |
| `hoja_tipo` / `version_hoja` | texto / entero | S | ✓ | `canonico.hojas` |
| `persona_id` / `concepto_id` / `hoja_id` | texto | S | ✓ | canónico |
| `periodo_origen_id` | texto | S | — | el periodo |

- **Llave:** (`hoja_id`, `persona_id`, `fecha`, `concepto_id`, `tipo_linea`).
- **Conceptos de unidad `importe`:** la cantidad **es dinero**. Esas líneas **no van aquí**: su dinero está en Importes. Si un concepto `importe` está configurado `sin_importe`, el oficial se bloquea con B06 (V-3).
- **Ceros:** se escriben solo si están así en lo firmado.
- **Orden:** el de persona, luego `fecha`, `concepto_id`, `hoja_id` y `tipo_linea`.

### 3.7 Importes

**Una fila por línea decidida** (`canonico.importes` con `estado = 'decidido'`).

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `concepto_clave` | texto | S | — | `inc_conceptos.abreviatura` |
| `naturaleza` | texto | S | — | `deduccion` si `inc_conceptos.tipo = 'descuento'`; si no, `percepcion` |
| `clasificacion` | texto | C | — | del esquema; vacío si no hay esquema |
| `modalidad` | texto | C | ✓ | `bruto`, `neto`, `manual` o vacío. **Nunca se suman entre sí** |
| `importe` | número de 2 decimales | S | ✓ | `canonico.importes[].final` |
| `hoja_tipo` / `version_hoja` | texto / entero | S | ✓ | canónico |
| `persona_id` / `concepto_id` / `hoja_id` | texto | S | ✓ | canónico |
| `relacion_laboral_id` / `registro_pago_id` | texto | C | ✓ | canónico |
| `periodo_origen_id` | texto | S | — | el periodo |

- **Llave:** (`persona_id`, `hoja_id`, `concepto_id`, `relacion_laboral_id`, `registro_pago_id`).
- **Excluidas:**
  - `sin_importe`: su cantidad va en Cantidades;
  - `descartado`;
  - las de complementos posteriores;
  - `por_decidir`: impide firmar, B03.
- **Varios esquemas:** una línea por esquema. Un adaptador fiscal solo toma las percepciones de modalidad `bruto`.
- **Deducciones sin esquema:** una deducción (por ejemplo, descuento de herramienta) normalmente no tiene `registro_pago_id` ni `modalidad`, y **es una línea válida**. El archivo no le asigna esquema; el adaptador la dirige según §14.2. Solo se avisa (A11) cuando la persona no tiene exactamente un esquema `bruto` en el periodo.
- **Orden:** el de persona, luego `concepto_id`, `hoja_id`, `relacion_laboral_id` y `registro_pago_id` (vacíos primero).

### 3.8 Descuentos

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `clase` | texto | S | — | `descuento` o `informativo` |
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `tipo_credito` | texto | S | ✓ (informativo) / — | tipo del crédito |
| `etiqueta` | texto | S | — | `cred_etiqueta(c)` |
| `referencia_credito` | texto | N | — | `cred_creditos.referencia` |
| `importe` | número de 2 decimales | C | ✓ | `canonico.descuentos[].final`; solo en `descuento` |
| `infonavit_tipo` / `infonavit_valor` | texto / número | C | ✓ | `canonico.informativos` |
| `pension_forma` / `pension_valor` | texto / número | C | ✓ | `canonico.informativos` |
| `persona_id` / `credito_id` | texto | S | ✓ | canónico |
| `descuento_id` | texto | C | ✓ | solo en `descuento` |

- **Llave:** `descuento_id` en `descuento` y `credito_id` en `informativo`.
- **Sin duplicados:** un crédito es calculable o informativo según `cred_es_calculable`. Si la persona también tiene un concepto `descuento` en una hoja, se emite A08.
- **Orden:** `clase`, luego el de persona, `credito_id` y `descuento_id`.

### 3.9 Movimientos

| Columna | Tipo | Obl. | Firma | Origen |
|---|---|---|---|---|
| `numero_interno` / `nombre_completo` | texto | — | — | Personas |
| `tipo` | texto | S | ✓ | tipo del evento laboral |
| `fecha_efectiva` | fecha | S | ✓ | canónico |
| `causa` | texto | N | ✓ | canónico |
| `persona_id` / `evento_id` | texto | S | ✓ | canónico |

- **Llave:** `evento_id`.
- **El salario nuevo no se repite:** está en Esquemas.
- **Orden:** el de persona, luego `fecha_efectiva`, `tipo` y `evento_id`.

### 3.10 Catálogos

| Columna | Tipo | Obl. | Regla |
|---|---|---|---|
| `catalogo` | texto | S | `concepto`, `codigo_dia`, `tipo_credito`, `tipo_movimiento` o `clasificacion` |
| `clave_beehuman` | texto | S | `concepto_id`, el código o el tipo |
| `abreviatura` | texto | C | conceptos y códigos |
| `nombre` | texto | S | — |
| `tipo` / `unidad` / `modo` | texto | C | Solo conceptos |
| `naturaleza` | texto | C | conceptos |
| `sistema_externo` / `clave_externa` | texto | N | **Vacíos en V1.** Nunca se inventa una equivalencia |

- **Llave:** (`catalogo`, `clave_beehuman`).
- **Contenido:** solo los valores que aparecen en el archivo.
- **Orden:** `catalogo`, luego `clave_beehuman`.

### 3.11 Validaciones

| Columna | Tipo | Obl. | Regla |
|---|---|---|---|
| `codigo` | texto | S | B01–B08, A01–A11 o I01–I03 |
| `nivel` | texto | S | `bloqueo`, `advertencia` o `informativo` |
| `resultado` | texto | S | `superada`, `aviso` o `no_aplica` |
| `hoja` | texto | N | hoja relacionada |
| `numero_interno` | texto | N | de Personas |
| `nombre_completo` | texto | N | nombre de la persona, para que Nómina la localice sin el identificador |
| `persona_id` / `referencia_id` | texto | N | — |
| `mensaje` | texto | S | En español, accionable |

- **Bloqueos de un archivo oficial generado:** los ocho aparecen como `superada`, salvo B07 en un periodo `listo`.
  - En `listo`, B07 va como **`no_aplica`**, con el mensaje «No aplica: el periodo aún no ha sido procesado.»
  - En `procesado`, B07 va como `superada`: «Sin cambios después del procesamiento.»
- **Orden:**
  1. las advertencias;
  2. los informativos;
  3. **al final, los ocho bloqueos**, como evidencia.
- **Dentro de cada grupo:** `codigo`, orden de persona y `referencia_id`.

---

## 4. Huellas y serialización (Excel oficial)

### 4.1 Reglas de serialización

**La huella nunca se calcula sobre los bytes del `.xlsx`.** Se calcula sobre este texto canónico:

| Aspecto | Regla |
|---|---|
| Codificación | UTF-8 sin BOM. Los textos se normalizan a **NFC**. No se recortan espacios |
| Registros | Un arreglo JSON (RFC 8259) por línea. Solo se escapan `"`, `\` y los controles U+0000–U+001F: con las formas cortas `\b`, `\f`, `\n`, `\r` y `\t`, y con `\u00xx` en minúsculas para el resto. Son iguales en PostgreSQL y en JSON.stringify. Los caracteres no ASCII van literales y no se escapa `/` |
| Vacío / nulo | `null`. Una cadena vacía `""` se normaliza a `null` |
| Cero | `"0"` en una cantidad y `"0.00"` en un importe; **distinto de `null`** |
| Importes | Cadena con **exactamente 2 decimales**, punto decimal, sin miles ni `+`. `-0.00` se normaliza a `"0.00"` |
| Otros números | Decimal sin ceros sobrantes (`trim_scale`) ni exponente |
| Enteros | `"7"` |
| Fecha sin hora | `"aaaa-mm-dd"` |
| Fecha con hora | `"aaaa-mm-ddThh:mm:ss±hh:mm"` en `America/Mexico_City`. No aparece en las hojas de datos |
| Booleanos | `true` / `false` |
| UUID | En minúsculas con guiones |
| Orden de hojas, columnas y filas | El de §2 y §3. Comparación binaria UTF-8 (intercalación `C`) |
| Fin de línea | `\n`, incluida después de la última línea |
| Algoritmo | SHA-256, en hexadecimal en minúsculas |
| Versión | Primera línea: `["beehuman.canonico","1.0"]` |

### 4.2 `huella_datos_exportados`

- **Qué cubre:** los datos lógicos de las 8 hojas de datos, más `periodo_id` y `huella_firma`.
- **Qué no cubre:** las columnas de solo lectura, el Resumen y Validaciones.
- **Construcción:**
  1. la línea de versión;
  2. `["periodo", periodo_id, huella_firma]`;
  3. por cada entidad: `["#entidad","<nombre>"]`, la línea de nombres de campo (sin los de solo lectura) y una línea por registro.

### 4.3 `huella_archivo`

- **Qué cubre:** las mismas 8 hojas **tal como se escriben**, con su nombre, sus encabezados y todas sus columnas.
- **Construcción:**
  1. la línea de versión;
  2. por cada hoja: `["#hoja","<nombre>"]`, la línea de encabezados y una línea por fila.
- **Verificación:** la calcula el servidor y la recalcula la pantalla. Si difieren, no hay descarga (B06).

### 4.4 Cambio de un dato descriptivo después de firmar

- **La firma sigue vigente**, porque `huella_firma` no cambia.
- **Al volver a exportar:** cambian `huella_datos_exportados` y `huella_archivo`, y sube `exportacion_numero`.
- **Avisos:** el Resumen muestra `huella_datos_exportados_anterior`, y la pantalla avisa «Los datos descriptivos cambiaron desde la exportación n».

---

## 5. Permisos (ambas modalidades)

- **Pueden exportar:** solo **Administrador** y **Nómina** del tenant del periodo. El servidor valida el rol con `tiene_rol` y el tenant en `inc__concentrado_base`.
- **No pueden:** Coordinador, Consulta, `anon` ni otro tenant. A otro tenant se le responde «periodo no encontrado».
- **La pantalla solo muestra u oculta los botones.**
- **Las funciones internas** (`inc__*`) no tienen permiso para `authenticated`.

---

## 6. Totales de control (ambas modalidades)

| Control | Debe ser igual a |
|---|---|
| Filas de Personas | `datos.totales.personas` |
| Incidencias por `codigo` | `datos.totales.dias` |
| Cantidades por `concepto_id` | `datos.totales.cantidades`, de conceptos con unidad distinta de `importe` |
| Importes **decididos** por (`concepto_id`, `modalidad`; vacío = `sin_modalidad`) | `datos.totales.importes` |
| Descuentos `descuento` **decididos** por `tipo_credito` | `datos.totales.descuentos` |
| **Solo en el preliminar:** número de faltantes de importe | Número de líneas por decidir |

**Compara dos lecturas del mismo dato; no recalcula la nómina.**

---

## 7. Validaciones del Excel oficial

### 7.1 Bloqueos: no se generan datos ni archivo

| Código | Condición | Mensaje |
|---|---|---|
| B01 | La firma del periodo no está `vigente`. Incluye los periodos procesados con la regla anterior a B-a | «El periodo no tiene una firma de Nómina vigente. Firma el concentrado para exportar.» |
| B02 | La huella recalculada es distinta de `huella_firma` | «El concentrado cambió después de la firma. Vuelve a firmar.» |
| B03 | Hay importes por decidir | «Hay n importes por decidir.» |
| B04 | Hay descuentos por decidir | «Hay n descuentos por decidir.» |
| B05 | Sin rol de Administrador o Nómina, o el periodo es de otro tenant | «Sin permiso.» / «Periodo no encontrado.» |
| B06 | Un total de control no cuadra, un concepto «importe» está configurado «sin importe» (V-3), o la `huella_archivo` de la pantalla no es igual a la del servidor | «El archivo no cuadra con el concentrado firmado; no se generó.» |
| B07 | Periodo procesado cuya huella actual es distinta de la de su evento `procesado` | «El periodo se procesó y después cambió. La versión 1 no puede reproducir lo procesado.» |
| B08 | Periodo en estado `preliminar` | «El periodo sigue en preparación. Puedes descargar el reporte preliminar, pero el Excel canónico oficial estará disponible cuando el periodo esté listo y tenga la firma de Nómina vigente.» |

**Orden de evaluación:** B05 → B07 (si está procesado) → B08 (si está `preliminar`) → B01 → B02 → B03 → B04 → B06.

### 7.2 Advertencias: el archivo se genera y las lista

| Código | Condición | Mensaje |
|---|---|---|
| A01 | Complementos posteriores al procesamiento: no se incluyen | — |
| A02 | Persona sin esquema de pago vigente | — |
| A03 | Persona con 0 días vigentes | — |
| A04 | Persona con más de una relación laboral en el periodo | — |
| A05 | `numero_interno` vacío o repetido | Con el nombre: «ROSA LUNA MORA — sin número interno.» / «… — número interno repetido: 0101.» |
| A06 | Importe decidido en 0 | — |
| A07 | **Percepciones** de modalidad `neto`, `manual` o sin esquema; o una **deducción asignada a un esquema que no es bruto** | «Tiene percepciones en el esquema neto: no van a la nómina fiscal (esquema bruto).» Una deducción sin esquema no genera A07 |
| A08 | Concepto `descuento` en una hoja y crédito de la misma persona en el periodo | — |
| A09 | Persona sin relación laboral que aparece en una hoja | — |
| A10 | Código de día en una fecha en que la persona no está vigente | — |
| A11 | Deducción sin esquema y la persona tiene 0 o más de 1 esquema `bruto` en el periodo | «La deducción DES no tiene esquema y la persona tiene n esquemas fiscales (bruto) en el periodo: el adaptador no podrá decidir el destino.» |

### 7.3 Informativos

| Código | Condición |
|---|---|
| I01 | Créditos informativos: los calcula el sistema de nómina |
| I02 | Observaciones de los coordinadores, de hojas no posteriores. **Fuera de la firma** |
| I03 | Altas y bajas en el periodo |

---

## 8. Versionado y contrato con los adaptadores

- **Identificación:** `formato` y `version_formato` (`MAYOR.MENOR`) van en el Resumen, en las propiedades del documento y en la primera línea de la serialización.
- **Cambio menor:** columnas al final, hojas nuevas, valores de catálogo nuevos o códigos de validación nuevos.
- **Cambio mayor:** renombrar, quitar o reordenar columnas; cambiar significados, tipos o llaves; cambiar una regla de serialización.
- **Los adaptadores:**
  - **solo aceptan `formato = beehuman.canonico`**, y rechazan `beehuman.preliminar` y cualquier otro (obligatorio, §14.1);
  - leen por nombre de columna;
  - ignoran columnas y hojas desconocidas;
  - rechazan una versión mayor distinta de la suya.

---

## 9. Complementos posteriores y traslado (roadmap)

**V1:** los complementos posteriores no entran en el oficial y se listan en A01.

**V1.x, reservado sin construir:**
- acción «Llevar al periodo…», con `periodo_origen_id`; el formato sube a 1.1;
- instantánea histórica para retirar B07.

---

## 10. Implementación

**Servidor:** migración aditiva `supabase/pendiente/20261125000000_excel_canonico_v1.sql`. La reversión está en `supabase/reversion/`.
- **`inc__exportacion_datos(p_periodo, p_modalidad)`** (interna): arma todo en una sola instantánea.
- **`inc_exportacion_canonica(p_periodo)`** (pública): valida B05, B07, B08, B01–B04 y B06, y registra el evento `oficial`.
- **`inc_exportacion_preliminar(p_periodo)`** (pública): valida BP1–BP3 y registra el evento `preliminar`.

**Pantalla (Concentrado, `app/incidencias.js`):**
- En `preliminar`: «Descargar reporte preliminar» y el texto de B08.
- En `listo` o `procesado`: «Exportar Excel oficial».
- Nunca se muestran los dos.
- El oficial recalcula `huella_archivo` antes de descargar.
- El archivo se arma con ExcelJS 4.4.0, cargado con SRI.

**Pruebas:**
- de base: `supabase/verificacion/ola1/pruebas_excel_canonico.py`;
- de pantalla: `ui_excel_canonico.py`;
- con su evidencia.

**Producción:** nada hasta la etapa 2.

---

## 11. Criterios de aceptación

| # | Criterio |
|---|---|
| CA1 | **Oficial**, en `listo` o `procesado` con firma `vigente`: un `.xlsx` con las 10 hojas y las columnas exactas, en el orden de §2 y §3 |
| CA2 | **Oficial:** en `preliminar` → B08; con `sin_firma`, `invalidada`, `definicion_anterior` o una huella distinta → B01 o B02. En ningún caso hay datos ni archivo |
| CA3 | Ciclo en un periodo no procesado. Firmar hasta `listo` y exportar el oficial. Cambiar un dato material: la firma se invalida, el oficial queda bloqueado (B08) y el preliminar disponible. Volver a firmar: el oficial funciona con nuevas huellas |
| CA4 | Oficial: `huella_concentrado` = `huella_firma` |
| CA5 | Los controles de §6 cuadran en ambas modalidades |
| CA6 | Ningún total suma bruto con neto |
| CA7 | Cantidades no lleva dinero ni conceptos de unidad `importe`; Importes no lleva cantidades |
| CA8 | Oficial: los complementos anteriores están en los datos y los posteriores solo en A01 |
| CA9 | Una persona con 2 esquemas tiene 1 fila en Personas, 2 en Esquemas y una línea de importe por esquema |
| CA10 | FONACOT da 1 fila `descuento`; INFONAVIT informativo da 1 fila `informativo` sin importe; ninguna llave se repite |
| CA11 | Misma firma y mismos datos dan las mismas huellas. Si solo cambia un dato descriptivo, la firma sigue vigente, las huellas cambian y sube `exportacion_numero` |
| CA12 | **Ninguna modalidad** cambia la firma, la huella del concentrado ni el estado del periodo |
| CA13 | Coordinador, Consulta, `anon` y otro tenant no pueden usar ninguna modalidad, ni con un llamado directo |
| CA14 | `clave_externa` vacía en ambas modalidades |
| CA15 | Vacío y cero se distinguen en la celda y en la serialización |
| CA16 | Con 500 personas, cada modalidad tarda menos de 5 s |
| CA17 | Un texto que empieza con `=` se escribe como texto |
| CA18 | Procesado que cambió después: oficial B07 y preliminar BP2 |
| CA19 | Preliminar en `preliminar`, sin firma: se genera |
| CA20 | Firma de Nómina vigente con RH pendiente: oficial → B08; preliminar disponible |
| CA21 | Preliminar en `listo` o `procesado` → BP2 |
| CA22 | El preliminar se distingue: `PRELIMINAR_…`, hojas `PRELIM `, `beehuman.preliminar`, aviso en el Resumen y en las propiedades, y sin `huella_firma` ni `huella_archivo` |
| CA23 | El preliminar incluye lo por decidir, con `importe` vacío, `estado` e `importe_sugerido`, sin sumarlo |
| CA24 | **Trasladado al adaptador NOI, obligatorio** (§14.1). Las señales visuales del preliminar son advertencias para personas, no una barrera técnica |
| CA25 | El preliminar registra un evento `exportacion` con modalidad `preliminar` |
| CA26 | Dos preliminares sin cambios dan la misma huella; después de que un coordinador envía una hoja, cambia |
| CA27 | «Sin cambios desde el preliminar del dd/mm» cuando la firma tiene la misma huella que el último preliminar |
| CA28 | A05 y las filas de Validaciones y Faltantes muestran el nombre de la persona |
| CA29 | Deducción sin esquema: sin A07; A11 solo si la persona no tiene exactamente un esquema `bruto` |
| CA30 | Validaciones: advertencias, informativos y al final los bloqueos |
| CA31 | B07 es `no_aplica` en un periodo `listo` y `superada` en uno `procesado` sin cambios |
| CA32 | Cada importe por decidir tiene su propia fila en Faltantes, con su esquema. Dos esquemas de la misma persona se distinguen. Hay tantas filas como líneas por decidir |

---

## 12. Reporte preliminar de acumulado

### 12.1 Propósito y límites

- **Propósito:** que Nómina revise avances, detecte faltantes y anticipe datos mientras los coordinadores y RH siguen trabajando.
- **No es información autorizada ni definitiva.**
- **No sirve como entrada de ningún adaptador:** lo rechazan (§14.1).
- **No firma ni modifica la firma, la huella ni el estado del concentrado.**

### 12.2 Disponibilidad

| Estado del periodo | Preliminar | Oficial |
|---|---|---|
| `preliminar` | **Disponible** | Bloqueado (B08) |
| `listo` | No disponible (BP2) | Disponible |
| `procesado` | No disponible (BP2) | Disponible, salvo B07 |

### 12.3 Estructura

| Aspecto | Oficial | Preliminar |
|---|---|---|
| Nombre del archivo | `BeeHuman_<empresa>_<inicio>_<fin>_exp-<n>.xlsx` | `PRELIMINAR_BeeHuman_<empresa>_<inicio>_<fin>_<aaaammdd-hhmm>.xlsx` |
| Nombres de hoja | Resumen, Personas… | `PRELIM Resumen`, …, `PRELIM Faltantes` |
| Resumen, fila 1 | `formato` | aviso «PRELIMINAR — NO AUTORIZADO…» |
| Propiedades | Confidencial | Confidencial, más título y asunto con «PRELIMINAR — no autorizado» |
| Identificación visual | — | Pestañas naranja y encabezado de impresión. El encabezado de columnas sigue en la fila 1 |
| `formato` | `beehuman.canonico` | `beehuman.preliminar` |
| Personas, Esquemas, Incidencias, Cantidades, Movimientos, Catálogos | §3 | **Iguales** |
| Importes | Solo `decidido` | Todas las líneas, con `estado`, `motivo_pendiente` e `importe_sugerido`; `importe` vacío si están por decidir |
| Descuentos | Decididos más informativos | Todos, con `estado` e `importe_sugerido` |
| Validaciones | §3.11 | **`PRELIM Faltantes`** (§12.4) |

### 12.4 Hoja `PRELIM Faltantes`

| Columna | Tipo | Regla |
|---|---|---|
| `tipo` | texto | `hoja`, `importe`, `descuento`, `firma`, `configuracion` (V-3), `advertencia` o `informativo` |
| `codigo` | texto | Vacío en los faltantes; A02–A11 o I01–I03 en el resto |
| `numero_interno` | texto | De la persona, si está en el periodo |
| `nombre_completo` | texto | La persona a la que se refiere la fila |
| `persona_id` | texto | En faltantes de hoja, importe, descuento y firma de RH, y en los avisos |
| `referencia_id` | texto | `hoja_id` en los faltantes de importe; en avisos, cuando aplica |
| `mensaje` | texto | El texto del faltante o del aviso |

- **Faltantes de importe:** una fila por línea por decidir, armada desde los datos del reporte. Ejemplos:
  - «JUAN PÉREZ LÓPEZ · Horas extra — IMSS / bruto: importe por decidir — hoja de MARTA RÍOS SALAZAR»;
  - «JUAN PÉREZ LÓPEZ · Horas extra — EFECTIVO / neto: …».
  - Las líneas con «esquema por asignar» y las deducciones sin esquema no muestran esquema.
  - Si el número de estas filas no es igual al de los faltantes de importe del concentrado, el reporte no se genera (BP3).
- **Faltantes de hoja, descuento y firma de RH:** el texto del concentrado, sin cambios. La persona se identifica por el nombre al inicio del texto («Persona · …» o «Coordinador: …»), solo si ese nombre es **único en el tenant**.
- **La firma de Nómina del periodo** no se refiere a una persona.

### 12.5 Huellas del preliminar

| Huella | ¿Aplica? | Definición |
|---|---|---|
| `huella_firma` | No | Solo se informa `firma_estado` |
| `huella_concentrado_actual` | Sí | `inc__huella_de(canonico)` al generar |
| `huella_datos_exportados` | Sí, con otra semilla | Primera línea `["beehuman.preliminar","1.0"]` y segunda `["periodo", periodo_id, huella_concentrado_actual]`. Nunca coincide con la de un oficial |
| `huella_archivo` | No | El preliminar no alimenta adaptadores |

### 12.6 Bloqueos del preliminar

| Código | Condición | Mensaje |
|---|---|---|
| BP1 | Sin rol o periodo de otro tenant | «Sin permiso.» / «Periodo no encontrado.» |
| BP2 | El periodo no está en `preliminar` | «El periodo ya está listo [o procesado]: descarga el Excel canónico oficial.» Si aplica B07: «El periodo se procesó y después cambió; no hay exportación disponible en la versión 1.» |
| BP3 | Un control de §6 no cuadra | «El reporte no cuadra con el concentrado; no se generó.» |

### 12.7 Registro de eventos

- **Qué se registra:** cada exportación es un evento `inc_eventos` de tipo `exportacion`, con su modalidad, su formato, el estado del periodo y la firma, sus huellas, los conteos y el número de exportación.
- **Qué no guarda:** RFC, CURP, NSS ni nombres.
- **Garantías:** el evento es inmutable y no toca la firma, la huella ni B6.

---

## 13. Pendientes de verificación: resolución

| # | Resolución |
|---|---|
| V-1 | Relación principal con la regla `rel_pri`, con prueba de igualdad contra el concentrado |
| V-2 | `modalidad_sueldo`: solo `bruto` y `neto`; se exporta tal cual |
| V-3 | Oficial: B06. Preliminar: faltante «configuracion». **Roadmap:** bloquear la combinación en la configuración del concepto |
| V-4 | Se reutiliza `inc_eventos.huella`; el comentario no cambió |
| V-5 | `modalidad` vacía: se trata como `sin_modalidad`; en deducciones es lo normal |
| V-6 | Encabezado en la fila 1; la leyenda va en Resumen, pestañas, propiedades y encabezado de impresión |
| V-7 | `faltantes[].tipo`: `hoja`, `importe`, `descuento`, `firma` (+ `configuracion`) |

---

## 14. Requisitos del adaptador NOI que dependen de este formato

Decididos por Erik el 25-nov. Son **criterios de aceptación obligatorios** del adaptador NOI, que todavía no existe.

### 14.1 Rechazo del preliminar (antes CA24)

- **NOI-CA1:** identificar el formato con `formato` en el Resumen y en las propiedades del documento.
- **NOI-CA2:** si es `beehuman.preliminar`, **rechazarlo de forma explícita**.
- **NOI-CA3:** no importar ningún registro, **ni parcialmente**.
- **NOI-CA4:** aceptar únicamente un `beehuman.canonico` compatible que cumpla las validaciones del adaptador.

### 14.2 Destino de las deducciones sin esquema

Una deducción debe poder llegar a NOI aunque su línea no tenga modalidad. Ejemplo: «DES — Descuento de herramienta», $120.00, de una persona con esquema IMSS bruto.

**Regla del adaptador:**
1. Identificar el esquema fiscal de la persona en el periodo, es decir, sus filas `bruto` en Esquemas.
2. Comprobar que el concepto de deducción tiene mapeo para NOI.
3. Si hay **exactamente un** esquema fiscal y el concepto está mapeado, enviar la deducción a ese esquema.
4. **Bloquear** si no puede determinarse el destino: 0 esquemas fiscales, más de uno, o un concepto sin mapeo.

**Límites:**
- No se obliga a asignar modalidad a cada deducción.
- Nunca se asigna automáticamente cuando hay ambigüedad.
- El Excel canónico anticipa el caso ambiguo con A11.
