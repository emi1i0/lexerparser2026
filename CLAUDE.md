# CLAUDE.md — Proyecto SMART HOME (lexer + parser + traductor HTML)

> Contexto del proyecto para asistencia con Claude Code. En español.

## Qué es

Intérprete en **PLY** (lex + yacc) para un lenguaje de dominio específico (DSL)
de domótica llamado **SMART HOME**. Es el TPI de *Sintaxis y Semántica de Lenguajes*
(UTN-FRRe, 2026). Están implementados el **lexer**, el **parser LALR**, la
**validación semántica** (atributo↔dispositivo, valor↔atributo, rangos) y el
**traductor a HTML** (todo en la misma pasada del parseo), más una
**interfaz gráfica tkinter** con editor de código.

El proyecto está en **tres archivos fuente**: `src/lexer.py`, `src/parser.py`
(parser + validación semántica + traductor HTML) y `src/main.py` (CLI + consola +
GUI). No se usa la librería estándar `html` (decisión de la cátedra): el escape
no se aplica, el texto va crudo en el HTML.

Documentos de referencia en `doc/`:
- `doc/consigna.pdf` — enunciado del TPI (lenguaje, tokens, traducción a HTML, control de errores).
- `doc/gramatica.md` — **gramática vigente** (fuente de verdad, implementada 1:1 en `src/parser.py`). Usar esta.
- `doc/gramatica.pdf` — versión original del enunciado; quedó desactualizada (ver `doc/gramatica.md` §0).
- `doc/cambios_parser_gui.md` — registro detallado de los cambios de la etapa parser+GUI (insumo del informe técnico).

Entregas: **lexer = 07/06/2026 (entregado)**, trabajo completo (lexer+parser+traductor HTML) = **05/07/2026**.

## Cómo ejecutar

Desde la raíz del proyecto (los fuentes están en `src/`):

```powershell
python -m src.main archivo.smart   # analiza un archivo y genera archivo.html si es válido
python -m src.main carpeta\        # analiza todos los .smart de una carpeta
python -m src.main                 # interfaz gráfica (editor + análisis + HTML)
python -m src.main --consola       # REPL de terminal (el modo de la entrega del lexer)
python src\main.py archivo.smart   # también funciona (fallback de import)
```

- `main.py` importa con `from src.X import ...` y, si falla (al correr
  `python src\main.py`, donde `src/` queda en el path), cae a `from X import ...`.
  Por eso **andan las dos formas**; la forma `-m` es la canónica (y la que usa PyInstaller).
- **GUI (default sin argumentos):** editor con números de línea, F5 analiza, pestañas
  Tokens/Errores/HTML, doble click en un error salta a la línea, botones para guardar
  el HTML o abrirlo en el navegador.
- **Modo consola (`--consola`):** se escribe una sentencia, **línea vacía = analizar**;
  `/cargar` abre un selector gráfico de archivos; se sale con **Ctrl+C**.
- Dependencias: **PLY** (`pip install ply`) y **tkinter** (viene con CPython estándar).
  Entorno verificado: Python 3.14.5, ply 3.11.
- `src/main.py` es el único punto de entrada; `lexer.py` y `parser.py` no tienen `__main__` operativo propio.

### Ejecutable (PyInstaller)

```powershell
build.bat                          # compila con PyInstaller → bin\win\main.exe
bin\win\main.exe archivo.smart     # corre sin Python instalado
```

`build.bat` invoca `python -m PyInstaller --onefile --noconfirm --paths=. --distpath bin\win --workpath build src/main.py`.
Los binarios (`bin/win/main.exe` y `bin/linux/main`) **se versionan en git** (se entregan
junto al código). En cambio `build.bat`, `main.spec` y `build/` son **helpers locales no
versionados** (están en `.gitignore`). Si modificás algo de `src/`, **recompilá** para que
el `.exe` quede al día.

## Estructura

| Ruta             | Rol |
|------------------|-----|
| `src/lexer.py`   | Lexer PLY completo (tokens, reglas, errores léxicos). Sin `__main__`. |
| `src/parser.py`  | Parser LALR (`ply.yacc`): gramática 1:1 con `doc/gramatica.md` + **validación semántica** (tabla `ESPEC_ACTUADORES`) + **traducción a HTML** (función `renderizar`) en las acciones semánticas + errores sintácticos/semánticos. |
| `src/main.py`    | Punto de entrada: despacho CLI / `--consola` / GUI (toda la GUI tkinter vive dentro de `ejecutar_gui()`), impresión de resultados, escritura del `.html`. |
| `doc/gramatica.md` | Gramática vigente (fuente de verdad) + apéndice con prompt para maquetar. |
| `doc/cambios_parser_gui.md` | Registro de los cambios de la etapa parser+GUI (histórico; anterior a la fusión de archivos y a la validación semántica). |
| `doc/` (PDFs)    | `consigna.pdf` y `gramatica.pdf` (enunciado original). |
| `prueba/`        | Ejemplos `.smart` (8: el de la consigna + 4 válidos + 1 c/errores léxicos + 1 c/errores sintácticos + 1 c/errores semánticos) y los `.html` generados. |
| `bin/win/`, `bin/linux/` | Ejecutables empaquetados (versionados en git). |
| `build.bat`      | Helper local (no versionado): compila el `.exe` con PyInstaller. |
| `main.spec`      | Helper local (no versionado): spec de PyInstaller generado. |

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
- `GUION` y `TOKEN_ID_ESP` existen en el lexer pero **no aparecen en la gramática**:
  el parser los rechaza como error sintáctico (sirven para mensajes de error claros).

## Mecanismos clave (importante al editar)

### Lexer
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

### Parser y traducción (una sola pasada)
- **Traducción dirigida por sintaxis:** no hay AST ni segunda recorrida. Las acciones
  semánticas de cada `p_*` registran sensores/atributos en los acumuladores
  `_sensores`/`_dispositivos` en el momento de cada reducción; al reducir `PROGRAMA`
  se serializa con `renderizar(...)` (función en el mismo `parser.py`, sección
  "GENERACION DE HTML") y **`parser.parse()` devuelve el HTML**.
- **Una sola tokenización:** `analizar_programa(lista_tokens, titulo)` recibe la lista
  de tokens ya emitida (adaptador `_LexerDeLista`); la misma lista alimenta la tabla
  de tokens en pantalla y el parseo.
- **Precedencias** `(('left','OR'), ('left','AND'), ('right','NOT'))` resuelven la
  ambigüedad de `EXPRESION_LOGICA`. La gramática no tiene conflictos (verificado).
- **Errores sintácticos:** lista global `errores_sintacticos` (línea, cadena, mensaje).
  Recuperación en modo pánico con `INSTRUCCION : error END` + `p.parser.errok()` al
  reducirla (sin el `errok()`, yacc suprime errores consecutivos por la regla
  anti-cascada de 3 tokens). Se reportan varios errores por archivo.
- **El HTML se genera SIEMPRE "hasta donde se pudo"**, aunque haya errores. Las
  asignaciones inválidas (semánticas) no se registran; lo válido sí se traduce. Si
  `parse()` no llega a reducir `PROGRAMA` (error no recuperable), `analizar_programa`
  igual serializa los acumuladores parciales. `main.py`/GUI escriben/muestran ese HTML
  y avisan si es parcial. (Antes el HTML se suprimía ante cualquier error; cambió por
  pedido de la cátedra.)
- `yacc.yacc(debug=False, write_tables=False, errorlog=NullLogger)`: no genera
  `parser.out`/`parsetab.py`; el NullLogger silencia los avisos esperados por
  `GUION`/`TOKEN_ID_ESP` sin usar. Si tocás la gramática, **rehacé la verificación
  de conflictos** construyendo una vez sin `errorlog`.

### Validación semántica (en `parser.py`)
- La gramática **no puede** distinguir `foco_` de `aire_`: ambos son el mismo terminal
  `ID_DISPOSITIVO` (el prefijo viaja en el *valor* del token, no en su *tipo*). Por eso
  las restricciones de la tabla de la consigna (pág. 6) se controlan en las **acciones
  semánticas**, no con reglas.
- **`ESPEC_ACTUADORES`**: tabla `prefijo → atributo → clases de valor admitidas`
  (transcripción 1:1 de la pág. 6, incluye los de solo lectura para validar lecturas).
  **`_RANGOS`**: rangos que el lexer no controla (hoy solo `temp_obj` 16–30 °C; los `%`
  ya los limita `TOKEN_PORC` a 0–100).
- Tres chequeos: **atributo↔dispositivo** (en asignación y lectura, `_atributo_pertenece`),
  **valor↔atributo** y **rango** (solo en asignación, `_validar_asignacion`). Cada `VALOR`
  lleva su **clase** (`BOOL_DISP`, `COLOR`, `TEMP`…) deducida del tipo de token (`p.slice`);
  el conjunto está en `CLASES_VALOR`.
- Los errores semánticos se **mezclan en `errores_sintacticos`** (no hay lista aparte) con
  prefijo de mensaje `[ERROR]`, línea y cadena. Una asignación inválida no aparece en el HTML.
- Pendiente como ampliación: chequeo de tipos en **comparaciones** (p. ej. `foco_x.estado
  == azul`), hoy solo se valida valor↔atributo en asignaciones.

### GUI (dentro de `main.py`)
- Toda la GUI tkinter (clases `TextoConEventos`, `NumerosDeLinea`, `VentanaPrincipal`)
  se define **dentro de `ejecutar_gui()`**, junto con el `import tkinter` local. Es a
  propósito: así los modos CLI/consola no pagan el import de tkinter ni fallan si no está
  instalado (las clases heredan de `tk.*`, por eso deben definirse después del import).
- `TextoConEventos` usa el patrón **widget proxy** (renombra el comando Tcl interno del
  `tk.Text`) para emitir `<<CambioEditor>>` en cada cambio/scroll: de ahí se redibujan
  los números de línea. No tocar ese mecanismo sin probar tipeo+pegado+scroll+resize.
- La GUI no duplica lógica de análisis: usa `analizar_completo` y las listas de errores
  de lexer/parser (todo en el mismo `main.py`).

## Convenciones

- Código y mensajes en **español** (incluido el `print` de tokens y errores).
- Comentarios del DSL: `//` hasta fin de línea (token `t_COMENTARIO`, se ignora).
- Espacios y tabs se ignoran; `t_newline` lleva la cuenta de líneas.
- `TOKEN_CADENA` usa **solo comillas rectas** (`"..."`). Las tipográficas (`“ ”`) son
  carácter ilegal a propósito (la cátedra las mete para verificar el reporte de errores —
  ver `prueba/00_ej_consigna.smart`).
- Los archivos de entrada deben terminar en `.smart`.
- **No usar la librería estándar `html`** (restricción de la cátedra). El traductor
  interpola el texto crudo en los f-strings; no se hace escape de `<`/`&`/`"`.

## Conformidad con la consigna

- **2da entrega (lexer):** cumplida — todos los tokens + dos modos de ejecución +
  control de errores con carácter, línea y posición.
- **3ra entrega (final):** parser LALR según `doc/gramatica.md`, **validación semántica**
  (tabla de la consigna pág. 6), traducción a HTML **mientras se parsea** (consigna §5:
  div verde de sensores con `<h2>`, un div gris por actuador con `<h1>` + `<ul>/<li>`,
  emails como `<a href="mailto:...">Contactar a usuario</a>`, salida `<fuente>.html`),
  control de errores léxicos/sintácticos/semánticos con tipo/línea/cadena, generación de
  HTML parcial aun con errores, y modos de ejecución archivo + interactivo + GUI.
  Falta solo la **documentación de entrega** (informe técnico, video).

## Historia: desalineación lexer ↔ gramática (resuelta DOS veces)

El modelo de **token único `ID_DISPOSITIVO`** se implementó originalmente, pero una
reescritura posterior del lexer ("el maestro del lexer lo hizo de nuevo") lo pisó y
volvió a los tokens `PREF_*` (con los que `foco_entrada` caía a `TOKEN_ID_ESP`).
Se re-corrigió el 10/06/2026 al empezar el parser (ver `doc/cambios_parser_gui.md` §1).
**Moraleja:** si se reescribe el lexer, verificar con `foco_entrada.estado` que salga
`[ID_DISPOSITIVO, PUNTO, ATTR_ESTADO]`.

## Desfasajes en los ejemplos de la consigna (informativo)

Los ejemplos de `doc/consigna.pdf` usan formas que el lenguaje **no** acepta:
`reloj.hora`/`alarma.estado` (sin prefijo de dispositivo), `color = blue` (válidos:
`blanco/rojo/azul`), `temp_objetivo` (es `temp_obj`), `sensor_temp_int` (inexistente),
`.email` (es `email_notif`). Caen a `TOKEN_ID_ESP` y ahora el **parser los reporta
como errores sintácticos** con línea y lexema (ver `prueba/00_ej_consigna.smart`).

## Pendientes

- **Informe técnico y video** para la entrega final del 05/07 (la consigna §7).
  `doc/cambios_parser_gui.md` es insumo directo (pero está **desactualizado**: no incluye
  la fusión de archivos, la quita de la librería `html`, el HTML parcial ni la validación
  semántica; conviene regenerarlo o complementarlo antes del informe).
- Ampliación: validación de tipos en **comparaciones** (hoy valor↔atributo solo en
  asignaciones) y rangos de **sensores** (`sensor_temp` −10..50, etc.).
- La consigna menciona `.json` para los ejemplos pero el resto usa `.smart` —
  aclarar con la cátedra cuál extensión esperan.

Ya resuelto: parser + traductor HTML en una pasada + GUI (10/06/2026), token único
`ID_DISPOSITIVO` (lexer+gramática, dos veces), atributos de solo lectura en
condiciones (gramática y parser), **validación semántica** (atributo↔dispositivo,
valor↔atributo, rango `temp_obj`), **HTML parcial aun con errores**, **fusión a 3
archivos** (parser+htmlgen, main+gui) **sin la librería `html`**, ejemplos en `prueba/`
(8, con léxicos/sintácticos/semánticos), recuperación de errores sintácticos múltiples.
