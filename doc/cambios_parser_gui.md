# Registro de cambios — Parser + Traductor HTML + Interfaz gráfica

> Fecha: 10/06/2026 · Sesión de desarrollo asistida con Claude Code.
> Este documento explica **todos** los cambios hechos en esta etapa, archivo por
> archivo, con el porqué de cada decisión. Sirve de insumo directo para el
> informe técnico de la entrega final (05/07/2026).

## Resumen ejecutivo

Se implementó la **3ra entrega completa**: analizador sintáctico (parser LALR con
`ply.yacc`) que valida los scripts contra la gramática de `doc/gramatica.md` y que
**traduce a HTML en la misma pasada del análisis** (traducción dirigida por
sintaxis, sin AST ni segunda recorrida), más una **interfaz gráfica tkinter** con
editor de código con números de línea. Antes de eso hubo que **corregir el lexer**,
que había quedado desalineado respecto de la gramática documentada.

Archivos tocados/creados:

| Archivo | Acción |
|---|---|
| `src/lexer.py` | **Modificado**: token único `ID_DISPOSITIVO` (corrección de desalineación). |
| `src/parser.py` | **Nuevo**: parser LALR + acciones semánticas que traducen a HTML. |
| `src/htmlgen.py` | **Nuevo**: serialización del HTML según §5 de la consigna. |
| `src/main.py` | **Modificado**: integra el parser, escribe el `.html`, despacha CLI/consola/GUI. |
| `src/gui.py` | **Nuevo**: interfaz gráfica completa (editor + tokens + errores + HTML). |
| `prueba/06_errores_sintacticos.smart` | **Nuevo**: ejemplo con errores sintácticos puros. |
| `prueba/0X_*.html` | **Generados**: traducciones de los 4 ejemplos válidos. |
| `CLAUDE.md` | **Modificado**: actualizado al nuevo estado del proyecto. |
| `bin/win/main.exe` | **Recompilado** con PyInstaller (incluye parser y GUI). |
| `build.bat` (local, no versionado) | **Modificado**: `--distpath bin\win` para respetar el nuevo layout `bin/win` + `bin/linux` introducido por los commits "build linux"; antes dejaba el exe en `bin/` directo. También se agregó `--noconfirm`. |

---

## 1. `src/lexer.py` — corrección: token único `ID_DISPOSITIVO`

**Problema encontrado.** `CLAUDE.md` y `doc/gramatica.md` daban por resuelto el
modelo de "dispositivo como un único token", pero el código en disco seguía con el
modelo viejo: tokens `PREF_FOCO`, `PREF_AIRE`, … y un dict `PREFIJOS` con claves
exactas (`'foco_'`). Como `t_TOKEN_ID_ESP` matchea por *maximal munch*,
`foco_entrada` se capturaba entero, no estaba en `PREFIJOS` (que solo tenía el
prefijo solo) y **caía a `TOKEN_ID_ESP`**. Con eso la gramática (que usa el
terminal `ID_DISPOSITIVO`) era inimplementable. Probablemente una reescritura
posterior del lexer pisó el cambio.

**Cambios concretos:**

1. En la tupla `tokens`: se eliminaron los 7 tokens `PREF_*` y se agregó
   `ID_DISPOSITIVO`.
2. El dict `PREFIJOS` pasó a ser la tupla `PREFIJOS_DISP` (solo los prefijos,
   sin mapeo a tipos, porque ahora todos producen el mismo tipo de token).
3. En `t_TOKEN_ID_ESP`, la rama `elif lower in PREFIJOS` se reemplazó por una
   nueva rama **al final** de la cadena de reclasificación:
   `elif lower.startswith(PREFIJOS_DISP)` → `ID_DISPOSITIVO`. Va al final a
   propósito: las palabras reservadas/sensores/atributos tienen prioridad
   (ninguna empieza con un prefijo de actuador hoy, pero el orden lo blinda).
4. Se quitó el `_?` final del regex de `t_TOKEN_ID_ESP`
   (`[a-zA-Z][a-zA-Z0-9_]*_?` → `[a-zA-Z][a-zA-Z0-9_]*`): era redundante porque
   `_` ya está dentro de la clase repetida.

**Resultado:** `foco_entrada.estado` → `[ID_DISPOSITIVO 'foco_entrada', PUNTO,
ATTR_ESTADO]`, exactamente lo que la gramática espera. El token `GUION` se
mantiene en el lexer (un `_` suelto sigue sin ser error léxico) aunque ninguna
producción lo use: si aparece, el **parser** lo rechaza como error de sintaxis.

---

## 2. `src/parser.py` — parser LALR con traducción en UNA pasada (nuevo)

### Gramática

Implementa **textualmente** las producciones de `doc/gramatica.md` §1, una función
`p_*` por producción, con los nombres reales de los terminales. La ambigüedad de
`EXPRESION_LOGICA` se resuelve como anticipaba la gramática, con precedencias y no
reescribiendo reglas:

```python
precedence = (('left','OR'), ('left','AND'), ('right','NOT'))
```

Se verificó construyendo con el log normal de yacc que **no hay conflictos
shift/reduce ni reduce/reduce**. Los únicos avisos eran por `GUION` y
`TOKEN_ID_ESP` (tokens del lexer intencionalmente fuera de la gramática), por eso
el `yacc.yacc(...)` final usa `errorlog=yacc.NullLogger()`. También se usa
`write_tables=False` para que no se generen `parser.out`/`parsetab.py` (nada que
ensuciar ni que agregar al `.gitignore`).

### Traducción a HTML en la misma pasada (el requisito clave)

La consigna pide que "*a medida que analiza el script deberá transformar el
contenido en un documento HTML*". Se implementó como **traducción dirigida por
sintaxis**: las acciones semánticas de cada `p_*` se ejecutan en el instante en
que el autómata LALR reduce esa producción, y ahí mismo registran información en
dos acumuladores a nivel de módulo:

- `_sensores`: `nombre → texto del valor` (p. ej. `sensor_luz → '250lux'`).
- `_dispositivos`: `nombre → {atributo → (tipo, texto)}` (dicts de Python 3.7+,
  que conservan el orden de aparición en el script).

Qué registra cada reducción:

- `p_asignacion` (`ID_DISPOSITIVO . attr = VALOR`): guarda el atributo con su
  valor; si el mismo atributo se asigna dos veces, **gana la última** (es el
  "estado final" que muestra el dashboard).
- `p_condicion_simple_rel` (`OPERANDO op OPERANDO`): si un sensor (o un atributo
  leído de un dispositivo) se compara contra un literal, ese literal es el único
  dato que el script aporta sobre su estado y se usa para el dashboard
  (`sensor_luz < 250lux` → el `<h2>` del sensor dice `sensor_luz: 250lux`).
  Una asignación explícita posterior siempre tiene prioridad sobre esto.
- `p_condicion_simple_bool` y `p_acceso_dispositivo`: registran el sensor o
  dispositivo aunque no haya valor, para que igual aparezca en el HTML.
- `p_programa` (símbolo inicial): al reducirse —fin de la única pasada— llama a
  `htmlgen.renderizar(...)` y **devuelve el documento HTML como resultado del
  `parser.parse()`**. No se construye AST y no hay segunda recorrida.

Los valores viajan por las producciones como tuplas etiquetadas
(`('VAL', texto)` / `('EMAIL', dirección)`): la etiqueta `EMAIL` existe porque la
consigna exige traducir los emails como link `mailto:` (ver §4).

### Una sola tokenización, una sola pasada

`analizar_programa(lista_tokens, titulo)` recibe la **lista de tokens ya emitida**
por el lexer y se la da a yacc mediante el adaptador `_LexerDeLista` (una clase
con método `token()` que consume la lista). Así el texto se tokeniza **una sola
vez** y la misma lista sirve para la tabla de tokens en pantalla y para el parseo.

### Control de errores sintácticos

- Lista global `errores_sintacticos` (espejo de `errores_lexicos`): cada entrada
  tiene `linea`, `cadena` (el lexema ofensor) y `mensaje`, como exige §6 de la
  consigna (tipo de error, línea y cadena).
- `p_error` registra el token inesperado; si es fin de entrada, sugiere que falta
  un `END`.
- **Recuperación en modo pánico** con la producción `INSTRUCCION : error END`:
  ante un error se descartan tokens hasta el próximo `END` y se sigue analizando,
  lo que permite reportar varios errores por archivo. Al reducirse esa regla se
  llama `p.parser.errok()`: sin eso, yacc suprime errores nuevos hasta haber
  shifteado 3 tokens válidos (anti-cascada) y se "comía" errores reales
  consecutivos (verificado con `prueba/06_errores_sintacticos.smart`, donde el
  error del `WHEN DO` de la línea 10 no se reportaba).
- Programa vacío → error sintáctico explícito ("se esperaba al menos una
  instrucción"), sin invocar a yacc.

---

## 3. `src/htmlgen.py` — serializador HTML (nuevo)

Módulo separado y sin estado: recibe `(titulo, sensores, dispositivos)` y devuelve
el documento como string. Cumple punto por punto el formato de la consigna §5:

- Un `<div style="border: 1px solid green; padding: 20px;">` con el estado de los
  sensores; cada sensor en `<h2>nombre: valor-con-unidad</h2>`.
- Un `<div style="border: 1px solid gray; padding: 20px;">` **por actuador**, con
  el nombre en `<h1>` y los atributos como `<ul>`/`<li>`.
- Los emails se traducen como
  `<a href="mailto:dir">Contactar a usuario</a>` (usuario = parte antes de la
  `@`), p. ej. `Contactar a bomberos`.
- Todo texto pasa por `html.escape()` (las cadenas del script podrían contener
  `<`, `&`, etc.).

El nombre del archivo de salida lo decide el llamador (`main.py`/GUI): igual al
fuente con extensión `.html`, como pide la consigna.

---

## 4. `src/main.py` — integración y despacho de modos (modificado)

- **Nueva función `analizar_completo(texto, titulo)`**: tokeniza una vez y parsea
  (que a su vez traduce). Devuelve `(tokens, html)`. Es la única puerta de
  entrada al análisis que usan la CLI, el REPL y la GUI.
- **`analizar_archivo`** ahora, además de la tabla de tokens: imprime errores
  léxicos **y sintácticos**, y el veredicto final. Si no hubo ningún error,
  escribe la traducción en `<mismo nombre>.html` junto al fuente e informa la
  ruta. Si hubo errores, lo dice y **no genera HTML** (consigna §8: la salida
  debe indicar éxito o los errores).
- **`_imprimir_resultado`** ganó la sección de errores sintácticos y los mensajes
  "Análisis exitoso…" / "Análisis finalizado con N error(es)".
- **Despacho en `__main__`** (antes: archivo o REPL; ahora tres modos):

  | Invocación | Modo |
  |---|---|
  | `python -m src.main archivo.smart` / `carpeta\` | CLI por archivo (obligatorio entrega final) |
  | `python -m src.main --consola` | REPL de terminal (el modo de la entrega del lexer, se conserva) |
  | `python -m src.main` (sin args) | **Interfaz gráfica** (la consigna admite "abierto por opciones gráficas") |

  Ojo: el modo interactivo de terminal ya **no** es el default; ahora es la GUI.
- El `import tkinter` de `abrir_selector_archivos` se movió adentro de la función
  (solo se paga si se usa).
- El REPL también parsea ahora: muestra tokens + errores de ambos tipos y el
  veredicto (no escribe `.html`; para eso están el modo archivo y la GUI).

---

## 5. `src/gui.py` — interfaz gráfica tkinter (nuevo)

Sin dependencias nuevas (tkinter/ttk estándar). Estructura: toolbar, panel
dividido vertical (editor arriba, resultados abajo), barra de estado.

### Editor de código con números de línea

- `TextoConEventos(tk.Text)`: implementa el patrón **widget proxy** — se renombra
  el comando Tcl interno del widget y se intercepta cada llamada; ante
  `insert`/`delete`/`replace`/`yview`/`xview`/movimiento del cursor se emite el
  evento virtual `<<CambioEditor>>`. Es la única forma de que los números de
  línea queden sincronizados con **cualquier** cambio (tipeo, pegado, undo,
  scroll con rueda, arrastre de scrollbar, resize).
- `NumerosDeLinea(tk.Canvas)`: en cada `<<CambioEditor>>`/`<Configure>` se
  redibuja iterando solo las líneas visibles (`text.index("@0,0")` +
  `dlineinfo`), así el costo no depende del tamaño del archivo.
- Editable con undo (`Ctrl+Z`), pegado nativo (`Ctrl+V`), `Ctrl+A` selecciona
  todo, fuente `Consolas 11`.
- **Resaltado de sintaxis liviano** con tags del propio `Text` y `re`: palabras
  reservadas (azul, en negrita — la lista se importa de `KEYWORDS` del lexer,
  única fuente de verdad), comentarios `//` (gris) y cadenas (bordó). Se aplica
  con *debounce* de 150 ms tras cada tecla para no recalcular en cada pulsación.

### Análisis y resultados

- **Analizar (botón o F5)** llama a `analizar_completo` sobre el contenido del
  editor y llena el notebook:
  - *Tokens*: `ttk.Treeview` con tipo / valor / línea.
  - *Errores*: léxicos y sintácticos juntos, con tipo, línea, cadena y mensaje.
    **Doble click en un error salta a esa línea** en el editor; las líneas con
    error se pintan de rojo suave (tag `linea_error`).
  - *HTML*: la traducción generada (solo lectura). Si el análisis fue exitoso la
    GUI selecciona esta pestaña y habilita los botones **Guardar HTML…**
    (sugiere `<archivo>.html`) y **Ver en navegador** (archivo temporal +
    `webbrowser.open`); si hubo errores selecciona *Errores* y los deshabilita.
- **Abrir…** carga un `.smart` (con confirmación si hay cambios sin guardar) y lo
  analiza automáticamente; **Guardar** escribe el `.smart`; **Limpiar** vacía
  todo. El título de la ventana muestra el archivo y un `*` si está modificado.
- Barra de estado: `Ln/Col` del cursor + resultado del último análisis.

---

## 6. `prueba/` — nuevo ejemplo y salidas generadas

- **`06_errores_sintacticos.smart` (nuevo):** léxicamente perfecto pero con tres
  errores de sintaxis: asignación a atributo de **solo lectura**
  (`reloj_sala.hora = 22:00` — la gramática solo admite `ID_ASIGNABLE` a la
  izquierda de `=`), `WHEN` sin condición, y asignación con el valor a la
  izquierda. Cierra con una instrucción válida para demostrar que la
  recuperación de errores no corta el análisis. Salida verificada: los 3 errores
  reportados con su línea y el resumen "3 error(es). No se genera HTML".
- **`0X_*.html` (generados):** traducciones de los 4 ejemplos válidos, producidas
  por `python -m src.main prueba`. Se versionan como muestra de la salida del
  traductor.
- Verificado también `00_ej_consigna.smart`: reporta sus 5 errores léxicos
  (comillas tipográficas, coma) **más** 4 sintácticos nuevos que antes pasaban
  desapercibidos (`blue`, `sensor_temp_int`, `reloj`, `temp_objetivo` caen a
  `TOKEN_ID_ESP` y el parser los rechaza con línea y lexema), tal como anticipaba
  la sección "Desfasajes pendientes" de `CLAUDE.md`.

---

## 7. Decisiones de diseño (para defender en la exposición)

1. **¿Por qué no hay AST?** La consigna pide traducir *mientras* se analiza. En
   un parser LALR las acciones semánticas se ejecutan al reducir cada
   producción: registrar ahí el estado de la casa y serializar al reducir
   `PROGRAMA` es literalmente una pasada (esquema de traducción dirigida por
   sintaxis, atributos sintetizados). Un AST + recorrido sería una segunda
   pasada innecesaria.
2. **¿Por qué acumuladores y no emitir HTML token a token?** Porque el formato
   pedido agrupa por dispositivo (un `<div>` por actuador con *todos* sus
   atributos), y las asignaciones a un mismo dispositivo aparecen dispersas por
   el script. Los acumuladores se llenan durante el parseo; no hay re-análisis.
3. **¿Por qué `parser.parse()` devuelve el HTML?** Hace explícito que la
   traducción es el atributo sintetizado del símbolo inicial.
4. **HTML solo sin errores:** un script inválido no representa una casa válida;
   además §8 exige indicar éxito o errores. La GUI deshabilita los botones de
   HTML en ese caso.
5. **`errok()` en la regla de error:** sin él, yacc suprimía errores reales
   (anti-cascada de 3 tokens). Con la sincronización en `END` el riesgo de
   cascada ya está contenido, así que conviene reportar todo.

## 8. Cómo probar rápido

```powershell
python -m src.main prueba              # analiza los 7 ejemplos; genera 4 .html
python -m src.main                     # GUI: pegar código, F5, ver pestañas
python -m src.main --consola           # REPL clásico de la entrega del lexer
bin\win\main.exe prueba\01_basico.smart  # ejecutable empaquetado (recompilado)
```

## 9. Pendientes que quedan

- El parser cubre la **validación sintáctica**; la validación **semántica**
  (que `foco_x` no use `.modo`, rangos 16–30 °C de `temp_obj`, etc.) la consigna
  la marca como deseable ("ampliación") y queda fuera de esta etapa — la
  gramática ya lo aclara en §1.
- La consigna menciona ejemplos `.json` en §2 pero todo el resto usa `.smart`:
  sigue pendiente aclararlo con la cátedra.
- Informe técnico y video (entrega 05/07): este documento es insumo directo.
