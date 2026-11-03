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
