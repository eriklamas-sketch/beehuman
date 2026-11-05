# BeeHuman — Etapa 1: pantallas de Historia laboral e IDSE (3-nov-2026)

**Estado:** construidas y probadas en la base local, con datos ficticios. **No se ha aplicado nada en beehuman-pruebas ni se ha hecho commit.** Los archivos están en `integracion/app`, sin confirmar.

## Qué se construyó

Todo vive en `app/laboral.js`, un archivo aparte, como la Ola 1. En `index.html` solo cambian 24 líneas:
- la pestaña de la ficha;
- la pestaña IDSE;
- dos enganches: al abrir la ficha y después del alta;
- el interruptor `LABORAL_ACTIVO`, que está encendido solo en la vista previa y **debe ir en false al publicar** hasta que la migración exista en producción.

### 1. Ficha · 08 Historia laboral (Administrador y Nómina)
- Una tarjeta por relación laboral: empresa, RP (o «sin registro patronal, sin IDSE»), estado, ingreso, antigüedad reconocida (por separado), baja con causa, SBC, tipos IMSS, UMF y número interno. También muestra los pendientes de la migración: sin fecha de ingreso, baja sin fecha y empleo anterior por reconstruir.
- Línea de tiempo por relación: fecha efectiva, tipo, cambios «antes → después», motivo, quién y cuándo lo registró, estado IDSE y anulados tachados.
- Acciones:
  - Registrar ingreso o reingreso;
  - Modificar salario (solo con RP);
  - Dar de baja (con causa IMSS);
  - Corregir datos (la fecha de ingreso y el SBC solo en datos migrados);
  - Anular (solo el último movimiento, y solo si su IDSE no se ha presentado).
- **Esquemas sin relación:** un recuadro lista los que la base no asignó por ser ambiguos, para que Nómina elija la relación de cada uno. En beehuman-pruebas son 26 (19 activos).
- **Campos bloqueados en la ficha** cuando la persona ya tiene historial: empresa, RP, número interno, fecha y comentario de baja, y la opción «Baja» del estatus. Un aviso lleva a Historia laboral.
- Cada operación llama a la función del servidor y vuelve a abrir la ficha, para que muestre lo que dejó la base.

### 2. Pestaña IDSE (Administrador y Nómina; Consulta y Coordinador no la ven)
- Selector de registro patronal. La guía IDSE y la zona de salario mínimo las edita solo el Administrador.
- **Altas y reingresos pendientes:** revisión por persona con lo que falta (en rojo) y los avisos (Ñ, fuera de plazo, reenvío). Solo se pueden seleccionar los movimientos listos.
- «Generar archivo con los seleccionados»: el servidor arma el `.dat` y se descarga.
- Archivos generados: descargar, marcar como presentado (lote y fecha), registrar resultado (rechazados con motivo, folio y fecha del acuse) y cancelar si no se ha presentado.
- Las bajas y modificaciones pendientes se cuentan, con la nota de que su archivo se habilita al confirmar el formato.

### 3. Alta de personal
Campo nuevo «Fecha de ingreso (alta IMSS)». Con empresa y esa fecha, el alta llama a `laboral_registrar_ingreso`. Sin fecha, el mensaje pide registrar el ingreso en Historia laboral.

## Hallazgo funcional: v3.1 (corregida tras la revisión)
Al probar el flujo apareció un caso que la regla de la v3 resolvía mal. Si alguien solo tenía relación de efectivo (en pruebas son 168) y después recibía su alta IMSS, la ficha seguía mostrando la relación sin RP, sin alta ni SDI. Esos datos los usan la exportación a NOI y las alertas.

La primera v3.1 lo resolvía, pero, como señaló la revisión, podía cambiar la ficha de empresa: con efectivo vigente en A y una relación con RP en B, la ficha saltaba a B.

**Regla corregida** de `laboral_relacion_principal`:
1. La ficha se queda en la empresa que ya muestra; un movimiento en otra empresa nunca la cambia.
2. Dentro de esa empresa, primero la relación con RP.
3. Luego la que coincide con el RP de la ficha y, al final, la más reciente.

Si la empresa de la ficha se queda sin relaciones vigentes (por una baja), la ficha pasa a otra empresa, prefiriendo la relación con RP.

Va como **migración aparte** (`20261104000100_relacion_principal_con_rp.sql`, con su reversión). El archivo principal sigue siendo exactamente la v3 del ensayo.

Pruebas de la v3.1:

| Caso | Resultado |
|---|---|
| Efectivo + alta IMSS en la misma empresa | La ficha muestra la relación con RP |
| Efectivo vigente en A + RP en B | La ficha **no** cambia de empresa |
| Baja de A con B vigente | La ficha pasa a B con su RP y alta |
| Reversión de la v3.1 | Restaura exactamente la función de la v3 (md5 de la definición) |

Además se comprobó que la prueba de dos empresas **falla con la v3.1 anterior** y pasa con la corregida.

## Pruebas (base local)

| Batería | Resultado |
|---|---|
| Base de datos, etapa 1 (`pruebas_eventos.py`) | **140/140** (134 anteriores + 6 de la v3.1, incluidas las dos empresas y su reversión) |
| Pantallas, etapa 1 (`ui_eventos.py`, Playwright) | **30/30** (repetidas con la v3.1 corregida) |
| Ola 1, base de datos | **90/90** |
| Ola 1, pantallas, con la migración y las pantallas nuevas activas | **33/33** |

Las 30 pruebas de pantalla cubren:
- relación migrada y bloqueo de la ficha;
- corrección con antes → después;
- esquema ambiguo asignado por Nómina;
- ingreso IMSS de quien solo tenía efectivo (la ficha pasa a la relación con RP);
- modificación y anulación;
- baja sin causa explicada;
- bandeja sin guía → con guía → archivo `.dat` (168 posiciones, CRLF, Ñ → #, SBC y clave en su posición) → presentado → resultado con acuse → confirmado en la ficha y ya no anulable;
- alta con ingreso;
- móvil (390 px) sin desbordes;
- Nómina sin edición del RP;
- Consulta y Coordinador sin la pestaña IDSE;
- ningún error de JavaScript.

## Pendientes
- **Comparación byte a byte** del primer archivo generado contra el `reingres.dat` aceptado, antes de subir algo real al IMSS.
- La barra «Guardar cambios» de la ficha sigue visible en Historia laboral por una regla de estilo anterior; también pasa en Compensación. No afecta: Historia laboral guarda con sus propios botones.

## Siguiente paso (requiere autorización)
1. Aplicar en beehuman-pruebas la v3 (mismo texto del ensayo, comprobado por md5) y la v3.1.
2. Hacer commit y push de `integracion/app` para la vista previa contra beehuman-pruebas.

## Aplicación en beehuman-pruebas (3-nov-2026, autorizada)
- **v3:** se aplicó como migración `eventos_laborales_idse`, usando el mismo texto del ensayo. La propia migración revisó que el md5 fuera `0b2fa2c2…` antes de ejecutarse.
- **v3.1 corregida:** se aplicó como migración `relacion_principal_con_rp`.
- **Verificación posterior:**
  - cada migración quedó registrada una sola vez (14 en total) y la función contiene la regla nueva;
  - la base tiene 537 relaciones, 83 en baja, 7 relaciones históricas, 201 sin fecha de ingreso, 620 eventos y 0 movimientos IDSE;
  - las fichas y los esquemas de pago tienen el mismo md5 que en la línea base;
  - quedan 19 esquemas activos pendientes de relación;
  - las 8 tablas tienen RLS; los usuarios de la app no pueden escribir en ellas y los usuarios sin sesión no tienen acceso;
  - hay 14 funciones de API; las internas no quedan expuestas;
  - la tabla temporal se borró.
- **Commit** `8a7cec7` en `integracion/app`, con push. La vista previa de Vercel quedó lista contra beehuman-pruebas.
- **Producción no se tocó.** `LABORAL_ACTIVO` debe ir en false en `main` hasta que la migración exista allí. El `.dat` no se presenta con datos reales hasta compararlo byte a byte con el archivo aceptado.

## Cierre de la validación funcional (3-nov-2026, tarde)

### Cuentas de prueba (solo datos de beehuman-pruebas; no cambian las reglas)
- **Causa:** Nómina, Consulta y Coordinador estaban en el tenant sintético chico (12 personas), no en «PILOTO SINTETICO 500», donde están el Administrador y la historia migrada. Además, Consulta no tenía empresa asignada y Coordinador no tenía a nadie asignado.
- **Cambio:** las tres cuentas pasaron al piloto de 500.
  - Consulta quedó con el ámbito EMPRESA PILOTO E (30 personas).
  - Coordinador quedó vinculado a PERSONA 0016, que coordina a 21 personas tanto en la ficha como en las asignaciones de Incidencias.
  - Respaldo: `respaldo.usuarios_prueba_20261103` y `respaldo.alcances_prueba_20261103`.
- **Comprobado con las reglas de acceso reales:**

  | Cuenta | Qué ve |
  |---|---|
  | Administrador y Nómina | 500 personas |
  | Consulta | 30 personas, solo de EMPRESA PILOTO E, y nada de «Mi equipo» |
  | Coordinador | Su equipo de 21 y nada de la vista de Consulta |

### Encabezado
- El bloque de usuario queda alineado a la derecha en los cuatro roles. Al Coordinador se le oculta la búsqueda y el bloque se iba a la izquierda.
- La flecha «⌄» se cambió por un botón «⏻ Cerrar sesión» («Salir» en móvil). Antes, en móvil no había forma de salir.
- Si no hay red, el cierre de sesión igual borra la sesión del navegador.

### Sesión: cómo funcionaba
- La app usa `supabase-js` con sus valores por defecto: la sesión se guarda en el navegador y se renueva sola cada hora.
- No había límite por inactividad ni por duración. En beehuman-pruebas hay una sesión abierta desde el 13-oct que sigue vigente.
- Quien deja abierta la pestaña o cierra el navegador y vuelve días después entra directo a los datos.

### Sesión: cierre por inactividad (nuevo)
- Se cierra a los **30 minutos sin actividad**. El aviso «¿Sigues ahí?» aparece 2 minutos antes, con cuenta regresiva y dos botones: «Seguir trabajando» y «Cerrar sesión».
- Escribir, hacer clic, desplazarse o mover el ratón cuenta como actividad, así que a quien está trabajando nunca le aparece el aviso.
- La actividad se comparte entre pestañas.
- Quien vuelve con más de 30 minutos sin actividad entra al inicio de sesión, con el mensaje «Tu sesión se cerró por inactividad».
- **Límite:** es un control del navegador. El límite del lado del servidor (tiempo de inactividad de Supabase Auth) queda como opción para producción y depende del plan.

### Pruebas
| Batería | Resultado |
|---|---|
| Sesión y encabezado (`ui_sesion.py`, nueva) | **25/25**, tres corridas seguidas |
| Etapa 1, pantallas | **30/30** |
| Ola 1, pantallas | **33/33** |

Al probar aparecieron y se corrigieron dos fallas del aviso:
1. Acercar el ratón lo cerraba.
2. Al presionar «Cerrar sesión» dentro del aviso, el aviso desaparecía antes del clic y la sesión seguía abierta.

### Pendiente
- Commit y push: autorizados por Erik (3-nov, 17:35).
- ~~Guardar el `.dat` de alta aceptado~~ → hecho (ver la sección siguiente).

## Archivo IDSE de alta aceptado por el IMSS (referencia de formato, 3-nov-2026)
- El IMSS ya **aceptó** el alta. Su archivo queda como referencia de formato.
  - El original, con datos reales, está solo en el proyecto: `claude/eventos/referencia/IDSE_alta_aceptada_20261103.dat`, sha256 `e8d4c5e1…68832`.
  - **No se sube al repositorio** porque contiene NSS y CURP.
- **Comparación byte a byte:** se tomaron los datos de ese archivo y se generó el alta con el código de la etapa 1 (`laboral_registrar_ingreso` → `idse_generar_archivo`), en una base local que se borró al terminar.
  - Resultado: **idénticos**, 340 bytes (renglón de alta, renglón final y CRLF).
  - Script: `supabase/verificacion/eventos/compara_dat.py`. Lee los datos del archivo que recibe y no guarda ninguno.
- Formato confirmado (168 posiciones más CRLF; las posiciones empiezan en 1):

| Posiciones | Campo |
|---|---|
| 1–11 | Registro patronal |
| 12–22 | NSS |
| 23–49 | Primer apellido |
| 50–76 | Segundo apellido |
| 77–103 | Nombre(s) |
| 104–109 | SBC, sin punto (2 decimales implícitos) |
| 110–115 | Espacios |
| 116 | Tipo de trabajador |
| 117 | Tipo de salario |
| 118 | Jornada |
| 119–126 | Fecha DDMMAAAA |
| 127–129 | UMF |
| 130–131 | Espacios |
| 132–133 | `08` |
| 134–138 | Guía |
| 139–148 | Clave del trabajador, alineada a la derecha |
| 149 | Espacio |
| 150–167 | CURP |
| 168 | `9` |

- **Renglón final:** 13 `*`, número de registros (6 dígitos) en las posiciones 57–62, guía en 134–138 y `9` en 168.
- **Sigue pendiente:** la regla de la Ñ (este archivo no la contiene) y los formatos de baja (02) y modificación (07).

## Archivo IDSE de bajas (02) (4-nov-2026)
**Referencia.** Erik compartió un archivo con 2 bajas presentadas con el formato que ya usa. Al 4-nov el IMSS todavía lo estaba procesando.
- El original, con datos reales, quedó solo en el proyecto: `claude/eventos/referencia/IDSE_bajas_referencia_20261104.dat` (sha256 `761e5eac…19bea2`).
- No se sube al repositorio.

**Formato.** Es el mismo renglón de 168 posiciones del alta, con estas diferencias:

| Posiciones | Alta | Baja |
|---|---|---|
| 104–118 | SBC, espacios, tipos de trabajador, salario y jornada | 15 ceros |
| 127–131 | UMF y 2 espacios | 5 espacios |
| 132–133 | `08` | `02` |
| 149 | Espacio | Causa de baja |
| 150–167 | CURP | 18 espacios |

Lo demás no cambia: RP, NSS, apellidos, nombre(s), fecha DDMMAAAA, guía, clave alineada a la derecha y `9` final. El renglón final es igual que en el alta.

**Migración `20261105000000_idse_bajas.sql`.** Solo cambia funciones; no toca tablas ni datos. Tiene su reversión.
1. Nueva función interna `idse_linea_baja`.
2. `idse_validar` acepta `02`.
   - La baja exige NSS, primer apellido, nombre(s), clave del trabajador y causa.
   - CURP, SBC, tipos y UMF siguen siendo requisitos solo del alta.
   - Los renglones se ordenan por fecha del movimiento y luego por apellidos; el archivo de referencia viene en ese orden.
3. `idse_generar_archivo` arma cada renglón según el tipo.
4. Las modificaciones (07) siguen bloqueadas hasta tener su archivo de referencia.

**Comparación byte a byte** (`compara_dat.py`, ahora para alta y baja):

| Archivo | Resultado |
|---|---|
| Bajas, 2 renglones | **Idénticos**, 510 bytes; mismo orden y causa en la posición 149 |
| Alta aceptada, con la migración nueva | Sigue **idéntico**, 340 bytes |

**Pantalla.** La bandeja IDSE tiene una sección «Bajas pendientes».
- Muestra fecha de baja, causa con su descripción, revisión, selección y el botón «Generar archivo de bajas».
- Si la base todavía no habilita un tipo de movimiento, la sección lo explica sin marcarlo como error.

**Pruebas:**

| Batería | Resultado |
|---|---|
| Base de datos | **163/163**: 140 anteriores, 18 de bajas y 5 de reversión |
| Pantallas | **36/36**: 30 anteriores y 6 del recorrido de bajas (registrar baja → bandeja → `.dat` → archivos generados) |

Las 23 pruebas nuevas de base cubren:
- requisitos de la baja (CURP no, clave sí);
- aviso de la Ñ;
- un alta mezclada en la selección de bajas;
- bloqueo de las modificaciones;
- que Consulta y Coordinador no generen bajas;
- posiciones del renglón y renglón final;
- orden y nombre del archivo;
- que una baja en archivo no se anule;
- presentación y resultado;
- que la reversión restaure exactamente las funciones de la v3 y conserve el archivo ya generado.

**Aplicado** en beehuman-pruebas y en commit (autorizado el 4-nov, 9:25).
### Aplicación en beehuman-pruebas (4-nov-2026, autorizada)
- Migración `idse_bajas` aplicada y registrada una sola vez (15 en total).
- Las funciones en pruebas tienen la misma huella que las que pasaron la comparación byte a byte en local:

  | Función | Huella |
  |---|---|
  | `idse_validar` + `idse_generar_archivo` | `87f6a362…` |
  | `idse_linea_baja` | `3df8bb42…` |
  | `idse_linea_alta` (sin cambios) | `91699cec…` |

  Por eso el alta sigue generando los mismos 340 bytes y las bajas los 510 del archivo de referencia. Los datos reales no se cargaron en pruebas.
- `idse_linea_baja` no queda expuesta: ni authenticated ni anon pueden llamarla.
- **Ensayo en pruebas con una persona sintética.** Se deshizo todo al terminar.
  - Generó un alta de 340 bytes y una baja con todas sus posiciones correctas.
  - Los dos movimientos quedaron `en_archivo`, ligados a su archivo, con su renglón de traza y una huella SHA-256 válida.
  - La reversión quitó `idse_linea_baja` y conservó los dos archivos.
- **Precisión sobre la reversión.** El código que restaura es idéntico al de la v3, pero el texto de la función no es idéntico al que hay en pruebas.
  - La razón: en pruebas la v3 se aplicó en versión compacta, sin líneas de comentario, y la reversión trae 3 comentarios y 3 líneas en blanco dentro de las funciones.
  - El comportamiento no cambia.
  - En una base donde la v3 se aplicó desde el archivo completo, la restauración es exacta byte a byte; así lo comprueba `pruebas_eventos.py`.

## Archivo IDSE de modificaciones de salario (07) (4-nov-2026)
**Referencia.** Erik compartió un archivo verificado con 2 modificaciones.
- El original, con datos reales, quedó solo en el proyecto: `claude/eventos/referencia/IDSE_modificaciones_referencia_20261104.dat`.
- No se sube al repositorio.

**Formato.** Es el renglón del alta con dos diferencias:
- **127–129:** en blanco, porque la modificación no lleva UMF.
- **132–133:** `07`.

El SBC de las posiciones 104–109 es el nuevo. Tipos de trabajador, salario y jornada, fecha, guía, clave y CURP van igual que en el alta, y el renglón final también.

**Migración `20261105000100_idse_modificaciones.sql`.** Se aplica sobre la de bajas, solo cambia funciones y tiene su reversión.
1. Nueva función interna `idse_linea_modificacion`.
2. `idse_validar` acepta `07` y exige lo mismo que el alta, salvo la UMF. Un tipo inexistente se rechaza.
3. `idse_generar_archivo` arma el renglón `07`.

Con esto quedan habilitados los tres tipos: alta, baja y modificación.

**Comparación byte a byte:**

| Archivo | Resultado |
|---|---|
| Modificaciones | **Idénticas**, 510 bytes |
| Bajas | **Idénticas**, 510 bytes |
| Alta | **Idéntica**, 340 bytes |

**Pantalla.** La bandeja IDSE tiene una sección «Modificaciones de salario pendientes», con fecha, SBC nuevo, revisión y el botón «Generar archivo de modificaciones».

**Pruebas:**

| Batería | Resultado |
|---|---|
| Base de datos | **179/179** |
| Pantallas | **41/41**: registrar modificación → bandeja → `.dat` → sale de pendientes |

Las pruebas nuevas de base cubren:
- la modificación no pide UMF, pero sí CURP;
- una baja mezclada en la selección de modificaciones;
- un tipo inexistente;
- que Consulta no genere modificaciones;
- las posiciones del renglón, el orden y el nombre del archivo;
- el estado `en_archivo` y que una modificación en archivo no se anule;
- que la reversión restaure exactamente la versión de bajas y conserve el archivo generado.

**Sigue abierta la regla de la Ñ.** Ninguno de los tres archivos de referencia contiene Ñ.

### Aplicación en beehuman-pruebas (5-nov-2026, autorizada)
- La migración `idse_modificaciones` se aplicó sobre la versión de bajas (`87f6a362…`) y quedó registrada una sola vez (16 en total).
- Las cuatro funciones en pruebas tienen la misma huella que en la base local donde los tres archivos de referencia acaban de salir **idénticos byte a byte**:

  | Función | Huella |
  |---|---|
  | `idse_validar` + `idse_generar_archivo` | `6ad49a60…` |
  | `idse_linea_modificacion` | `a88bea73…` |
  | `idse_linea_baja` | `3df8bb42…` |
  | `idse_linea_alta` | `91699cec…` |

  Resultado: modificaciones 510 bytes, bajas 510 y alta 340. No se cargaron datos reales en pruebas.
- `idse_linea_modificacion` no queda expuesta, y anon no puede generar archivos.
- **Ensayo en pruebas con una persona sintética** (alta → modificación → baja). Se deshizo todo al terminar.
  - Generó tres archivos con sus posiciones correctas.
  - Cada movimiento quedó `en_archivo` y ligado a su archivo, con 3 renglones de traza y huellas válidas.
  - La reversión restauró **exactamente** la versión de bajas (`87f6a362…`), quitó `idse_linea_modificacion` y conservó los tres archivos.
- Después del ensayo, pruebas no tiene ningún archivo, movimiento ni persona de ensayo.

**Estado:**

| Movimiento | Formato |
|---|---|
| Alta (08) | Verificado |
| Baja (02) | Verificado |
| Modificación (07) | Verificado |

Los tres se generan en la vista previa. La regla de la Ñ sigue provisional (`#`).
