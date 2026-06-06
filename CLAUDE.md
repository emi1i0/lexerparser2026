# CLAUDE.md — Proyecto SMART HOME (analizador léxico)

> Contexto del proyecto para asistencia con Claude Code. En español.

## Qué es

Analizador léxico (lexer) en **PLY** para un lenguaje de dominio específico (DSL)
de domótica llamado **SMART HOME**. Es el TPI de *Sintaxis y Semántica de Lenguajes*
(UTN-FRRe, 2026). El nombre del proyecto es `lexerparser2026`, pero **por ahora solo
existe el lexer; el parser todavía no está implementado** (siguiente etapa).

Documentos de referencia en `doc/`:
- `doc/consigna.pdf` — enunciado del TPI (lenguaje, tokens, traducción a HTML, control de errores).
- `doc/gramatica.md` — **gramática vigente** (fuente de verdad, consistente con el lexer). Usar esta.
- `doc/gramatica.pdf` — versión original del enunciado; quedó desactualizada (ver `doc/gramatica.md` §0).

Entregas: **lexer = 07/06/2026**, trabajo completo (lexer+parser+traductor HTML) = 05/07/2026.
Para la entrega del lexer alcanza con reconocer los tokens y los dos modos de ejecución.

## Cómo ejecutar

Desde la raíz del proyecto (los fuentes están en `src/`):

```powershell
python src\main.py archivo.smart   # analiza un archivo (extensión .smart obligatoria)
python src\main.py                 # modo interactivo (línea vacía = analizar; 'salir' = terminar)
```

- Dependencia: **PLY** (`pip install ply`). Entorno verificado: Python 3.14.5, ply 3.11.
- `src/main.py` es el único punto de entrada; `src/lexer.py` solo define el lexer (sin `__main__`).

## Estructura

| Ruta             | Rol |
|------------------|-----|
| `src/lexer.py`   | Definición completa del lexer PLY (tokens, reglas, errores). Sin `__main__`. |
| `src/main.py`    | Punto de entrada único: modo archivo `.smart` o modo interactivo. |
| `doc/gramatica.md` | Gramática vigente (fuente de verdad) + apéndice con prompt para maquetar. |
| `doc/` (PDFs)    | `consigna.pdf` y `gramatica.pdf` (enunciado original). |
| `prueba/`        | Ejemplos `.smart` (5: 4 válidos + 1 con errores léxicos). |

## El lenguaje SMART HOME (categorías de tokens)

- **Palabras reservadas / estructura:** `WHEN`, `EVERY`, `IF`, `THEN`, `ELSE`, `DO`,
  `END`, `AND`, `OR`, `NOT`.
- **Sensores:** `sensor_temp`, `sensor_humedad`, `sensor_luz`, `sensor_movimiento`,
  `sensor_humo`.
- **Dispositivos (actuadores):** un identificador que empieza con un prefijo de actuador
  (`foco_`, `aire_`, `persiana_`, `cerradura_`, `reloj_`, `altavoz_`, `alarma_`) se reconoce
  como **un único token `ID_DISPOSITIVO`** (la especificación va incluida, p. ej.
  `foco_entrada`, `aire_acondicionado`). La lista de prefijos vive en `PREFIJOS_DISP`.
- **Atributos:** `estado`, `brillo`, `color`, `modo`, `temp_obj`, `temp_act`,
  `posicion`, `volumen`, `mute`, `mensaje`, `email_notif`, `activada`, `hora`, `fecha`.
- **Valores booleanos / discretos:** `BOOLEANO_SENSOR` (true/false),
  `BOOLEANO_DISP` (on/off), `LIT_COLOR` (blanco/rojo/azul), `LIT_MODO` (frio/calor/vent).
- **Valores con unidad (tokens compuestos):** `TOKEN_TEMP` (`25°C`, `-5°C`),
  `TOKEN_PORC` (`80%`), `TOKEN_LUX` (`250lux`), `TOKEN_TIEMPO` (`30m`/`10s`/`1h`),
  `TOKEN_HORA` (`22:00`), `TOKEN_FECHA` (`21/04/2026`), `TOKEN_EMAIL`,
  `TOKEN_CADENA` (`"..."`, sin comillas en `.value`), `TOKEN_NUMERO` (entero, `.value` es `int`),
  `TOKEN_ID_ESP` (identificador genérico). `TOKEN_PORC` solo acepta 0–100 (`101%` → número + error).
- **Operadores relacionales:** `==`, `!=`, `>=`, `<=`, `>`, `<`.
- **Asignación / puntuación:** `=` (ASIG), `.` (PUNTO), `_` (GUION), `(` (L_PAR), `)` (R_PAR).

## Mecanismo clave (importante al editar)

- **Reclasificación case-insensitive:** un identificador genérico se captura con la
  regla `t_TOKEN_ID_ESP` y luego se reclasifica buscando su forma en minúsculas en las
  tablas `KEYWORDS`, `SENSORES`, `ATRIBUTOS`, `BOOL_SENSOR`, `BOOL_DISP`, `LIT_COLORES`,
  `LIT_MODOS`. Si no coincide con ninguna pero **empieza** con un prefijo de
  `PREFIJOS_DISP` → `ID_DISPOSITIVO`; en caso contrario → `TOKEN_ID_ESP`. Para agregar una
  palabra reservada/sensor/atributo, basta con sumarla a la tabla correspondiente (y a la
  tupla `tokens` si es un tipo nuevo).
- **Orden de las reglas:** en PLY, las reglas definidas como funciones se evalúan en el
  orden del archivo. Los **tokens compuestos con unidad van ANTES** que `t_TOKEN_ID_ESP`
  y `t_TOKEN_NUMERO` para que `25°C` no se parta en número + texto. No reordenar sin cuidado.
- **Errores léxicos:** `t_error` acumula los caracteres ilegales en la lista global
  `errores_lexicos` (con línea, posición y mensaje) y continúa con `skip(1)` — el análisis
  **no se detiene** ante un error. La lista se limpia (`.clear()`) al inicio de cada análisis.

## Convenciones

- Código y mensajes en **español** (incluido el `print` de tokens y errores).
- Comentarios del DSL: `//` hasta fin de línea (token `t_COMENTARIO`, se ignora).
- Espacios y tabs se ignoran; `t_newline` lleva la cuenta de líneas.
- `TOKEN_CADENA` usa **solo comillas rectas** (`"..."`). Las tipográficas (`“ ”`) son
  carácter ilegal a propósito (la cátedra las mete para verificar el reporte de errores —
  ver `prueba/00_ej_consigna.smart`).
- Los archivos de entrada deben terminar en `.smart`.

## Conformidad con la consigna (entrega del lexer)

Cumple lo exigido para la 2da entrega: reconoce todos los tokens de `doc/consigna.pdf`
(palabras reservadas, sensores, atributos, literales con unidad, operadores, email,
comentarios) y ofrece los dos modos de ejecución (interactivo y archivo `.smart`).
El control de errores reporta carácter, línea y posición.

## Consistencia lexer ↔ gramática (RESUELTO — ver `doc/gramatica.md`)

Se eligió el modelo de **token único `ID_DISPOSITIVO`** y se alinearon ambos lados:
- **Lexer:** `foco_entrada.estado` → `[ID_DISPOSITIVO 'foco_entrada', PUNTO, ATTR_ESTADO]`.
- **Gramática (`doc/gramatica.md`):** `IDENTIFICADOR_COMPUESTO → ID_DISPOSITIVO PUNTO ID_ASIGNABLE`.
  Se eliminó `ESPECIFICACION` y el terminal `_`; los prefijos `foco|aire|…` ya no son terminales.

También se corrigió en `doc/gramatica.md` el **bug de atributos de solo lectura**: `temp_act`,
`hora`, `fecha` ahora se pueden **leer** en condiciones vía `ACCESO_DISPOSITIVO → ID_DISPOSITIVO
PUNTO ID_LEGIBLE`, pero **no** asignar (`IDENTIFICADOR_COMPUESTO` solo admite `ID_ASIGNABLE`).

## Desfasajes pendientes en los ejemplos de la consigna (informativo)

Los ejemplos de `doc/consigna.pdf` usan formas que el lenguaje **no** acepta (caen a
`TOKEN_ID_ESP`, no son error léxico): `reloj.hora`/`alarma.estado` (sin prefijo de
dispositivo), `color = blue` (en inglés; válidos: `blanco/rojo/azul`), `temp_objetivo`
(es `temp_obj`), `sensor_temp_int` (sensor inexistente). No es un problema del lexer;
conviene corregir los ejemplos propios o, si se quiere, ampliar el lenguaje.

## Pendientes y mejoras de calidad

- **Falta el parser** (`parser.py` con `ply.yacc`) y el **traductor a HTML** (sección 5 de
  la consigna): ambos para la entrega final del 05/07.
- `prueba/` ya tiene 5 ejemplos `.smart` (4 válidos + 1 con errores léxicos). La consigna
  menciona `.json` para los ejemplos pero el resto usa `.smart` — aclarar con la cátedra
  cuál extensión esperan.
- No es repo git todavía; conviene `git init` para versionar (ya no hay copias manuales
  tipo `resguardo`).

Ya resuelto: token único `ID_DISPOSITIVO` (lexer+gramática), atributos de solo lectura en
condiciones (gramática), regex redundante `_?` de `t_TOKEN_ID_ESP`, ejemplos en `prueba/`,
eliminación de `resguardo` y del bloque `__main__` duplicado de `lexer.py`.
