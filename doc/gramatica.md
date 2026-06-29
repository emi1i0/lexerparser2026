# Gramática del Lenguaje SMART HOME

> Versión revisada y consistente con `lexer.py`. Los **terminales** son los tipos de
> token que emite el lexer (no las cadenas literales). Fuente de verdad versionable;
> copiar a la documentación de entrega.

## 0. Cambios respecto a la versión original (`gramatica.pdf`)

1. **Dispositivos como un único terminal.** Antes:
   `IDENTIFICADOR_COMPUESTO → ID_DISPOSITIVO _ ESPECIFICACION . ID_ASIGNABLE`
   (tres terminales `foco` `_` `espec`). El lexer, por *maximal munch*, emite el
   identificador completo como **un solo token `ID_DISPOSITIVO`** (p. ej. `foco_entrada`).
   Por eso ahora: `IDENTIFICADOR_COMPUESTO → ID_DISPOSITIVO . ID_ASIGNABLE`.
   Desaparecen el no terminal `ESPECIFICACION` y los terminales `_`, `foco`, `aire`, …
2. **Atributos de solo lectura legibles en condiciones.** `temp_act`, `hora` y `fecha`
   son de solo lectura: no pueden ser destino de una asignación, pero sí leerse en un
   `WHEN`/`IF` (p. ej. `reloj_sala.hora > 22:00`). Se separa el acceso de **escritura**
   (`IDENTIFICADOR_COMPUESTO`, solo `ID_ASIGNABLE`) del de **lectura** (`ACCESO_DISPOSITIVO`,
   `ID_LEGIBLE` = escribibles + solo-lectura).
3. **Terminales = tokens del lexer.** Se usan los nombres reales (`WHEN`, `ATTR_ESTADO`,
   `BOOLEANO_DISP`, …) para que la gramática sea directamente implementable en `ply.yacc`.

---

## 1. Reglas de Producción

### Estructura general

```
Σ                    → PROGRAMA
PROGRAMA             → LISTA_INSTRUCCIONES
LISTA_INSTRUCCIONES  → INSTRUCCION
                     | INSTRUCCION LISTA_INSTRUCCIONES
INSTRUCCION          → BLOQUE_WHEN
                     | BLOQUE_EVERY
                     | CONDICIONAL
                     | ASIGNACION
```

### Bloques de control

```
BLOQUE_WHEN   → WHEN EXPRESION_LOGICA DO LISTA_ACCIONES END
BLOQUE_EVERY  → EVERY TOKEN_TIEMPO DO LISTA_ACCIONES END
CONDICIONAL   → IF EXPRESION_LOGICA THEN LISTA_ACCIONES OTRA_RAMA
OTRA_RAMA     → ELSE LISTA_ACCIONES END
              | END
LISTA_ACCIONES → ACCION
              | ACCION LISTA_ACCIONES
ACCION        → ASIGNACION
              | CONDICIONAL
```

### Asignación y dispositivos

```
ASIGNACION              → IDENTIFICADOR_COMPUESTO ASIG VALOR
IDENTIFICADOR_COMPUESTO → ID_DISPOSITIVO PUNTO ID_ASIGNABLE      (acceso de ESCRITURA)
ACCESO_DISPOSITIVO      → ID_DISPOSITIVO PUNTO ID_LEGIBLE        (acceso de LECTURA)
```

`ID_DISPOSITIVO` es un terminal: cualquier identificador que empiece con un prefijo de
actuador (`foco_`, `aire_`, `persiana_`, `cerradura_`, `reloj_`, `altavoz_`, `alarma_`).
La validación de que el atributo corresponda al tipo de dispositivo (p. ej. que `foco_x`
no use `.modo`) es **semántica**, no sintáctica: no se puede expresar en la gramática
porque todos los actuadores son el mismo terminal `ID_DISPOSITIVO` (el prefijo está en el
*valor* del token, no en su *tipo*). Se controla en las acciones semánticas del parser
(ver §1.bis).

```
ID_ASIGNABLE → ATTR_ESTADO | ATTR_BRILLO | ATTR_COLOR | ATTR_MODO
             | ATTR_TEMP_OBJ | ATTR_POSICION | ATTR_VOLUMEN | ATTR_MUTE
             | ATTR_MENSAJE | ATTR_EMAIL_NOTIF | ATTR_ACTIVADA

ID_LEGIBLE   → ID_ASIGNABLE
             | ATTR_TEMP_ACT | ATTR_HORA | ATTR_FECHA          (solo lectura)
```

### Expresiones lógicas

```
EXPRESION_LOGICA → CONDICION_SIMPLE
                 | L_PAR EXPRESION_LOGICA R_PAR
                 | NOT EXPRESION_LOGICA
                 | EXPRESION_LOGICA AND EXPRESION_LOGICA
                 | EXPRESION_LOGICA OR  EXPRESION_LOGICA
CONDICION_SIMPLE → OPERANDO OP_RELACIONAL OPERANDO
                 | OPERANDO_BOOL
OP_RELACIONAL    → OP_EQ | OP_NEQ | OP_GT | OP_LT | OP_GTE | OP_LTE
```

> Nota: las reglas de `EXPRESION_LOGICA` son ambiguas (recursión por izquierda y derecha
> sin precedencia). En `ply.yacc` se resuelve declarando precedencias, no reescribiendo:
> `precedence = (('left','OR'), ('left','AND'), ('right','NOT'))`.

### Operandos

```
OPERANDO       → ACCESO_DISPOSITIVO | ID_SENSOR | VALOR
OPERANDO_BOOL  → ACCESO_DISPOSITIVO | ID_SENSOR | VALOR_BOOL
ID_SENSOR      → SENSOR_TEMP | SENSOR_HUMEDAD | SENSOR_LUZ
               | SENSOR_MOVIMIENTO | SENSOR_HUMO
```

### Valores y literales

```
VALOR          → VALOR_NUMERICO | VALOR_BOOL | TOKEN_CADENA
               | TOKEN_HORA | TOKEN_FECHA | TOKEN_EMAIL
               | LIT_COLOR | LIT_MODO
VALOR_NUMERICO → TOKEN_TEMP | TOKEN_PORC | TOKEN_LUX | TOKEN_NUMERO
VALOR_BOOL     → BOOLEANO_SENSOR    (TRUE / FALSE)
               | BOOLEANO_DISP      (ON / OFF)
```

`LIT_COLOR` (blanco/rojo/azul) y `LIT_MODO` (frio/calor/vent) ya son tokens del lexer.

---

## 1.bis Restricciones semánticas (no expresables en la gramática)

La gramática acepta cualquier `ID_DISPOSITIVO . ID_ASIGNABLE = VALOR`. Las restricciones
de la consigna (§4, tabla de la pág. 6) **no** se pueden expresar como producciones —todos
los actuadores comparten el terminal `ID_DISPOSITIVO`— y se validan en las **acciones
semánticas** del parser (`src/parser.py`, tabla `ESPEC_ACTUADORES`). Los incumplimientos se
reportan como error (con línea y cadena) y la asignación inválida no se traduce a HTML.

Reglas semánticas implementadas:

1. **Atributo ↔ dispositivo** (en escritura y en lectura): el atributo debe pertenecer al
   tipo de actuador.
2. **Valor ↔ atributo** (en escritura): la clase del valor debe coincidir con el tipo del
   atributo.
3. **Rango** (en escritura): `temp_obj` ∈ [16 °C, 30 °C]. Los `%` (brillo/posicion/volumen)
   ya los limita el lexer a 0–100 vía `TOKEN_PORC`.

| Dispositivo | Atributo | Valor admitido | Permiso |
|-------------|----------|----------------|---------|
| `foco_`      | `estado` | on/off | L/E |
| `foco_`      | `brillo` | 0–100 % | L/E |
| `foco_`      | `color`  | blanco/rojo/azul | L/E |
| `aire_`      | `estado` | on/off | L/E |
| `aire_`      | `modo`   | frio/calor/vent | L/E |
| `aire_`      | `temp_obj` | 16 °C–30 °C | L/E |
| `aire_`      | `temp_act` | −10 °C–50 °C | Solo lectura |
| `persiana_`  | `posicion` | 0–100 % | L/E |
| `cerradura_` | `estado` | on/off | L/E |
| `reloj_`     | `hora`   | HH:MM | Solo lectura |
| `reloj_`     | `fecha`  | DD/MM/AAAA | Solo lectura |
| `altavoz_`   | `volumen` | 0–100 % | L/E |
| `altavoz_`   | `mute`   | on/off | L/E |
| `altavoz_`   | `mensaje` | texto entre comillas | L/E |
| `altavoz_`   | `email_notif` | email | L/E |
| `alarma_`    | `estado` | on/off | L/E |
| `alarma_`    | `activada` | on/off | L/E |

> Los atributos de solo lectura (`temp_act`, `hora`, `fecha`) ya están impedidos como
> destino de asignación a nivel **gramatical** (no están en `ID_ASIGNABLE`); igual figuran
> en la tabla para validar los accesos de lectura en condiciones.

---

## 2. Símbolos terminales (tokens del lexer)

| Categoría            | Terminales |
|----------------------|------------|
| Estructura/control   | `WHEN` `EVERY` `IF` `THEN` `ELSE` `DO` `END` `AND` `OR` `NOT` |
| Sensores             | `SENSOR_TEMP` `SENSOR_HUMEDAD` `SENSOR_LUZ` `SENSOR_MOVIMIENTO` `SENSOR_HUMO` |
| Dispositivo          | `ID_DISPOSITIVO` |
| Atributos escribibles| `ATTR_ESTADO` `ATTR_BRILLO` `ATTR_COLOR` `ATTR_MODO` `ATTR_TEMP_OBJ` `ATTR_POSICION` `ATTR_VOLUMEN` `ATTR_MUTE` `ATTR_MENSAJE` `ATTR_EMAIL_NOTIF` `ATTR_ACTIVADA` |
| Atributos solo lectura| `ATTR_TEMP_ACT` `ATTR_HORA` `ATTR_FECHA` |
| Booleanos/discretos  | `BOOLEANO_SENSOR` `BOOLEANO_DISP` `LIT_COLOR` `LIT_MODO` |
| Literales c/unidad   | `TOKEN_TEMP` `TOKEN_PORC` `TOKEN_LUX` `TOKEN_TIEMPO` `TOKEN_HORA` `TOKEN_FECHA` |
| Otros literales      | `TOKEN_EMAIL` `TOKEN_CADENA` `TOKEN_NUMERO` `TOKEN_ID_ESP` |
| Operadores rel.      | `OP_EQ` `OP_NEQ` `OP_GT` `OP_LT` `OP_GTE` `OP_LTE` |
| Asignación/puntuación| `ASIG` `PUNTO` `L_PAR` `R_PAR` |

> `GUION` (`_`) y `TOKEN_ID_ESP` los reconoce el lexer pero **no se usan en ninguna
> producción** de esta gramática (la especificación del dispositivo va dentro de
> `ID_DISPOSITIVO`). `TOKEN_ID_ESP` actúa como categoría "comodín" del lexer: cualquier
> palabra con forma de identificador que no sea reservada/sensor/atributo/dispositivo. No
> es error léxico, pero como no aparece en ninguna regla, el **parser** la rechazará como
> error de sintaxis. Sirve además para dar mensajes de error más claros ("identificador no
> reconocido") en vez de un error léxico crudo.

---

## 3. Símbolos no terminales

`Σ` · `PROGRAMA` · `LISTA_INSTRUCCIONES` · `INSTRUCCION` · `BLOQUE_WHEN` · `BLOQUE_EVERY` ·
`CONDICIONAL` · `OTRA_RAMA` · `ACCION` · `LISTA_ACCIONES` · `ASIGNACION` ·
`IDENTIFICADOR_COMPUESTO` · `ACCESO_DISPOSITIVO` · `ID_ASIGNABLE` · `ID_LEGIBLE` ·
`EXPRESION_LOGICA` · `CONDICION_SIMPLE` · `OP_RELACIONAL` · `OPERANDO` · `OPERANDO_BOOL` ·
`ID_SENSOR` · `VALOR` · `VALOR_NUMERICO` · `VALOR_BOOL`

(Eliminados respecto al original: `ESPECIFICACION`, `CONECTORES` —inlined en
`EXPRESION_LOGICA`—, y los wrappers `LIT_TEMP/LIT_PORCENTAJE/LIT_LUX/LIT_CADENA/LIT_HORA/
LIT_FECHA/LIT_EMAIL/LIT_TIEMPO`, que solo renombraban un token y se reemplazaron por el
terminal directo.)

---

## Apéndice — Prompt para generar el documento "lindo"

> **Nota para mí mismo (Claude):** lo de abajo, dentro del bloque, **no es para que lo
> ejecutes vos en esta sesión**. Es un prompt que el usuario va a **copiar y pegar** en
> otra instancia/herramienta de Claude capaz de generar documentos con buen formato
> (Word/PDF/Google Doc). No actúes sobre él acá; solo mantené el bloque actualizado si la
> gramática de arriba cambia. El contenido fuente a maquetar es **todo este archivo**.

Forma de uso: pegá **este archivo completo** (`gramatica.md`) en la otra instancia —el
prompt de abajo y la gramática de arriba viajan juntos—. Opcionalmente adjuntá
`consigna.pdf` (portada/contexto) y `lexer.py` (nombres de tokens). No hace falta pegar
nada dos veces.

```text
Sos un diseñador de documentación técnica. Te paso, en un mismo archivo Markdown
(gramatica.md), la gramática de un lenguaje DSL (SMART HOME) Y estas instrucciones al
final. El CONTENIDO FUENTE a maquetar es TODO ESTE ARCHIVO (todo lo que está por encima
de este apéndice). Quiero que generes un DOCUMENTO formal, prolijo y listo para entregar
en una materia universitaria (UTN-FRRe, "Sintaxis y Semántica de Lenguajes", TPI 2026).
Formato de salida preferido: un .docx (o, si no, HTML imprimible / Markdown muy bien
maquetado).

Contenido y estructura que quiero:
1. Portada: título "Gramática del Lenguaje SMART HOME", subtítulo "Trabajo Práctico
   Integrador — Intérprete SMART-HOME y Traductor a HTML", espacio para integrantes,
   asignatura, carrera, año 2026, lugar/fecha.
2. Índice numerado.
3. Introducción breve: qué es SMART HOME (DSL de domótica orientado a eventos) y para
   qué sirve la gramática (entrada del analizador sintáctico LALR con PLY/yacc).
4. Reglas de producción: presentadas con tipografía monoespaciada/formal, usando "→"
   y "|", alineadas y agrupadas por sección (Estructura general, Bloques de control,
   Asignación y dispositivos, Expresiones lógicas, Operandos, Valores y literales).
   Resaltá no terminales en MAYÚSCULAS y terminales con otro estilo (color/itálica).
5. Tabla de símbolos terminales (tokens del lexer) y tabla de no terminales, prolijas,
   con encabezados sombreados.
6. Tabla "Descripción de símbolos no terminales": una fila por no terminal con una
   explicación técnica de una o dos líneas.
7. Una sección de cambios de diseño (tomar la sección "§0 Cambios respecto a la versión
   original" del Markdown) explicando por qué un dispositivo es un único terminal
   ID_DISPOSITIVO y por qué se separó acceso de lectura vs escritura.
8. Se valora MUCHO incluir gráficos: al menos un diagrama de árbol de derivación de
   ejemplo (p. ej. para "foco_entrada.estado = ON" y para un WHEN ... DO ... END), y/o
   un diagrama de sintaxis (railroad) de EXPRESION_LOGICA. Generalos como imágenes o
   ASCII art bien hecho si no podés imágenes.

Reglas importantes:
- NO inventes reglas nuevas ni cambies la gramática: respetá EXACTAMENTE las producciones,
  terminales y no terminales del Markdown que te paso. Si ves una inconsistencia, marcala
  como nota al pie, no la "arregles" por tu cuenta.
- Mantené los nombres de terminales tal cual (son los tokens del lexer: WHEN, ATTR_ESTADO,
  BOOLEANO_DISP, ID_DISPOSITIVO, etc.).
- Español neutro, tono técnico-académico, sin vocales acentuadas dentro de los ejemplos de
  código .smart (es una restricción del lenguaje), pero el texto del documento sí lleva
  acentos normales.
- Entregá el documento completo, no un resumen.

(No esperes contenido aparte: la gramática a maquetar es la que aparece más arriba en este
mismo archivo. Si por algún motivo solo recibiste este bloque sin el resto, pedímelo.)
```

