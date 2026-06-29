# Analizador sintactico (parser LALR con ply.yacc) del lenguaje SMART HOME.
#
# Implementa exactamente las producciones de doc/gramatica.md. La traduccion a
# HTML se hace EN LA MISMA PASADA del analisis: cada accion semantica (las
# funciones p_*) se ejecuta en el momento en que yacc reduce esa produccion y
# va registrando el estado de sensores y dispositivos en los acumuladores
# _sensores/_dispositivos. Al reducirse el simbolo inicial PROGRAMA se
# serializa el documento HTML (renderizar, al final de este archivo). No se
# construye AST ni se recorre nada por segunda vez.
#
# La generacion del HTML (seccion 5 de la consigna) vive en este mismo archivo
# (parte "GENERACION DE HTML" mas abajo): parser y traductor juntos para que la
# pasada unica quede toda en un solo modulo.

import ply.yacc as yacc

try:
    # Ejecucion como modulo (python -m src.main) o desde el .exe de PyInstaller.
    from src.lexer import tokens, PREFIJOS_DISP  # noqa: F401  (yacc busca tokens por nombre)
except ModuleNotFoundError:
    # Ejecucion directa (python src/main.py): src/ ya esta en sys.path.
    from lexer import tokens, PREFIJOS_DISP      # noqa: F401


errores_sintacticos = []

# ------------------------------------------------------------------
# Estado del traductor (se llena DURANTE el parseo y se limpia en
# analizar_programa). Dicts comunes: en Python 3.7+ conservan el orden
# de insercion = orden de aparicion en el script.
# ------------------------------------------------------------------
_sensores = {}        # nombre -> texto del valor comparado (o None)
_dispositivos = {}    # nombre -> {atributo: (tipo, texto)}
_titulo = 'programa SMART HOME'


def _registrar_sensor(nombre, valor=None):
    # un valor concreto pisa a "sin valor", pero no al reves
    if valor is not None or nombre not in _sensores:
        _sensores[nombre] = valor


def _registrar_dispositivo(nombre):
    _dispositivos.setdefault(nombre, {})


def _registrar_atributo(dispositivo, atributo, valor):
    _registrar_dispositivo(dispositivo)
    _dispositivos[dispositivo][atributo] = valor


def _registrar_comparacion(izq, der):
    """Si un sensor o un atributo de dispositivo se compara contra un valor
    literal, ese valor es el unico dato que el script aporta sobre su estado:
    se usa para el dashboard (p. ej. 'sensor_luz < 250lux' -> sensor_luz: 250lux)."""
    valor = der[2] if der[0] == 'valor' else None
    if izq[0] == 'sensor':
        _registrar_sensor(izq[1], valor)
    elif izq[0] == 'acceso':
        dispositivo, atributo = izq[1], izq[2]
        # Solo se muestra el valor leido si el atributo es valido para el
        # dispositivo (uno invalido ya se reporto como error y no debe salir
        # en el HTML). Una asignacion posterior tiene prioridad sobre esto.
        if (valor is not None and _atributo_valido(dispositivo, atributo)
                and atributo not in _dispositivos.get(dispositivo, {})):
            _registrar_atributo(dispositivo, atributo, ('VAL', valor))
        else:
            _registrar_dispositivo(dispositivo)


# ==================================================================
# VALIDACION SEMANTICA (consigna §4, tabla de la pag. 6)
#
# La gramatica NO puede distinguir foco_ de aire_ (ambos son el mismo
# terminal ID_DISPOSITIVO: el prefijo viaja en el VALOR del token, no en
# su tipo). Por eso la correspondencia atributo<->dispositivo, la
# compatibilidad valor<->atributo y los rangos numericos se controlan en
# las acciones semanticas del parser (analisis semantico), no con reglas.
# Los hallazgos se reportan en la misma lista errores_sintacticos.
# ==================================================================

# Clases de valor que produce la regla VALOR (etiqueta de la tupla (clase, texto)).
CLASES_VALOR = {
    'BOOL_DISP', 'BOOL_SENSOR', 'COLOR', 'MODO', 'TEMP', 'PORC',
    'LUX', 'NUMERO', 'CADENA', 'HORA', 'FECHA', 'EMAIL',
}

# Etiqueta legible de cada clase, para los mensajes de error.
_NOMBRE_CLASE = {
    'BOOL_DISP': 'on/off', 'BOOL_SENSOR': 'true/false',
    'COLOR': 'blanco/rojo/azul', 'MODO': 'frio/calor/vent',
    'TEMP': 'temperatura (ej. 25°C)', 'PORC': 'porcentaje (ej. 50%)',
    'LUX': 'iluminancia (ej. 250lux)', 'NUMERO': 'numero entero',
    'CADENA': 'texto entre comillas', 'HORA': 'hora HH:MM',
    'FECHA': 'fecha DD/MM/AAAA', 'EMAIL': 'email',
}

# prefijo de actuador -> atributo -> clases de valor admitidas (consigna pag. 6).
# Incluye los atributos de solo lectura (temp_act/hora/fecha) para validar
# tambien los accesos de LECTURA en condiciones; la gramatica ya impide
# asignarlos (no estan en ID_ASIGNABLE).
ESPEC_ACTUADORES = {
    'foco_':      {'estado': {'BOOL_DISP'}, 'brillo': {'PORC'}, 'color': {'COLOR'}},
    'aire_':      {'estado': {'BOOL_DISP'}, 'modo': {'MODO'},
                   'temp_obj': {'TEMP'}, 'temp_act': {'TEMP'}},
    'persiana_':  {'posicion': {'PORC'}},
    'cerradura_': {'estado': {'BOOL_DISP'}},
    'reloj_':     {'hora': {'HORA'}, 'fecha': {'FECHA'}},
    'altavoz_':   {'volumen': {'PORC'}, 'mute': {'BOOL_DISP'},
                   'mensaje': {'CADENA'}, 'email_notif': {'EMAIL'}},
    'alarma_':    {'estado': {'BOOL_DISP'}, 'activada': {'BOOL_DISP'}},
}

# Rangos numericos que el lexer NO controla (TOKEN_PORC ya limita 0-100;
# TOKEN_TEMP acepta cualquier valor, asi que temp_obj se valida aca).
_RANGOS = {
    ('aire_', 'temp_obj'): (16, 30),   # °C
}


def _error_semantico(linea, cadena, detalle):
    errores_sintacticos.append({
        'linea':   linea,
        'cadena':  cadena,
        'mensaje': f"[ERROR] {detalle} (línea {linea})",
    })


def _prefijo_de(dispositivo):
    for pref in PREFIJOS_DISP:
        if dispositivo.startswith(pref):
            return pref
    return None


def _num_de(texto):
    """Extrae el numero de un literal de temperatura ('25°C', '-5°C', '25.5°C')."""
    crudo = texto.replace('°C', '').replace('°', '').strip()
    try:
        return float(crudo)
    except ValueError:
        return None


def _atributo_valido(dispositivo, atributo):
    """Predicado puro (no reporta): el atributo corresponde al dispositivo."""
    return atributo in ESPEC_ACTUADORES.get(_prefijo_de(dispositivo), {})


def _atributo_pertenece(dispositivo, atributo, linea):
    """True si `atributo` corresponde al tipo de `dispositivo`. Si no, reporta."""
    if not _atributo_valido(dispositivo, atributo):
        _error_semantico(linea, f'{dispositivo}.{atributo}',
                         f"el atributo '{atributo}' no existe para dispositivos "
                         f"'{_prefijo_de(dispositivo)}'")
        return False
    return True


def _validar_asignacion(dispositivo, atributo, valor, linea):
    """Valida dispositivo.atributo = valor contra la tabla de la consigna.
    Devuelve True si es valida (y por lo tanto se registra en el HTML)."""
    if not _atributo_pertenece(dispositivo, atributo, linea):
        return False

    pref = _prefijo_de(dispositivo)
    clases_ok = ESPEC_ACTUADORES[pref][atributo]
    clase_val, texto = valor
    if clase_val not in clases_ok:
        esperado = ' o '.join(_NOMBRE_CLASE.get(c, c) for c in sorted(clases_ok))
        _error_semantico(linea, texto,
                         f"valor '{texto}' incompatible con {dispositivo}."
                         f"{atributo}: se esperaba {esperado}")
        return False

    rango = _RANGOS.get((pref, atributo))
    if rango is not None:
        n = _num_de(texto)
        if n is not None and not (rango[0] <= n <= rango[1]):
            _error_semantico(linea, texto,
                             f"valor '{texto}' fuera de rango para {dispositivo}."
                             f"{atributo} (permitido: {rango[0]}°C a {rango[1]}°C)")
            return False
    return True


# ------------------------------------------------------------------
# Precedencias: resuelven la ambiguedad de EXPRESION_LOGICA
# (ver nota en doc/gramatica.md §1).
# ------------------------------------------------------------------
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
)


# ------------------------------------------------------------------
# Estructura general
# ------------------------------------------------------------------

def p_programa(p):
    '''PROGRAMA : LISTA_INSTRUCCIONES'''
    # Reduccion del simbolo inicial: aca "termina" la unica pasada y se
    # serializa todo lo acumulado como documento HTML.
    p[0] = renderizar(_titulo, _sensores, _dispositivos)


def p_lista_instrucciones(p):
    '''LISTA_INSTRUCCIONES : INSTRUCCION
                           | INSTRUCCION LISTA_INSTRUCCIONES'''
    pass


def p_instruccion(p):
    '''INSTRUCCION : BLOQUE_WHEN
                   | BLOQUE_EVERY
                   | CONDICIONAL
                   | ASIGNACION'''
    pass


def p_instruccion_error(p):
    '''INSTRUCCION : error END'''
    # Recuperacion en modo panico: ante un error dentro de un bloque se
    # descartan tokens hasta el proximo END y se sigue analizando el resto
    # del programa (permite reportar varios errores por archivo).
    # errok(): da por completada la recuperacion, asi el proximo error se
    # reporta de inmediato (sin esperar los 3 tokens validos que yacc exige
    # por defecto para evitar cascadas).
    p.parser.errok()


# ------------------------------------------------------------------
# Bloques de control
# ------------------------------------------------------------------

def p_bloque_when(p):
    '''BLOQUE_WHEN : WHEN EXPRESION_LOGICA DO LISTA_ACCIONES END'''
    pass


def p_bloque_every(p):
    '''BLOQUE_EVERY : EVERY TOKEN_TIEMPO DO LISTA_ACCIONES END'''
    pass


def p_condicional(p):
    '''CONDICIONAL : IF EXPRESION_LOGICA THEN LISTA_ACCIONES OTRA_RAMA'''
    pass


def p_otra_rama(p):
    '''OTRA_RAMA : ELSE LISTA_ACCIONES END
                 | END'''
    pass


def p_lista_acciones(p):
    '''LISTA_ACCIONES : ACCION
                      | ACCION LISTA_ACCIONES'''
    pass


def p_accion(p):
    '''ACCION : ASIGNACION
              | CONDICIONAL'''
    pass


# ------------------------------------------------------------------
# Asignacion y dispositivos
# ------------------------------------------------------------------

def p_asignacion(p):
    '''ASIGNACION : IDENTIFICADOR_COMPUESTO ASIG VALOR'''
    dispositivo, atributo, linea = p[1]
    # Solo se registra en el HTML si la asignacion es semanticamente valida
    # (atributo del dispositivo + valor del tipo correcto + en rango).
    if _validar_asignacion(dispositivo, atributo, p[3], linea):
        _registrar_atributo(dispositivo, atributo, p[3])


def p_identificador_compuesto(p):
    '''IDENTIFICADOR_COMPUESTO : ID_DISPOSITIVO PUNTO ID_ASIGNABLE'''
    p[0] = (p[1], p[3], p.lineno(1))


def p_acceso_dispositivo(p):
    '''ACCESO_DISPOSITIVO : ID_DISPOSITIVO PUNTO ID_LEGIBLE'''
    # Lectura en condicion: el atributo igual debe corresponder al dispositivo.
    _atributo_pertenece(p[1], p[3], p.lineno(1))
    _registrar_dispositivo(p[1])
    p[0] = ('acceso', p[1], p[3])


def p_id_asignable(p):
    '''ID_ASIGNABLE : ATTR_ESTADO
                    | ATTR_BRILLO
                    | ATTR_COLOR
                    | ATTR_MODO
                    | ATTR_TEMP_OBJ
                    | ATTR_POSICION
                    | ATTR_VOLUMEN
                    | ATTR_MUTE
                    | ATTR_MENSAJE
                    | ATTR_EMAIL_NOTIF
                    | ATTR_ACTIVADA'''
    p[0] = p[1]


def p_id_legible(p):
    '''ID_LEGIBLE : ID_ASIGNABLE
                  | ATTR_TEMP_ACT
                  | ATTR_HORA
                  | ATTR_FECHA'''
    p[0] = p[1]


# ------------------------------------------------------------------
# Expresiones logicas
# ------------------------------------------------------------------

def p_expresion_logica(p):
    '''EXPRESION_LOGICA : CONDICION_SIMPLE
                        | L_PAR EXPRESION_LOGICA R_PAR
                        | NOT EXPRESION_LOGICA
                        | EXPRESION_LOGICA AND EXPRESION_LOGICA
                        | EXPRESION_LOGICA OR EXPRESION_LOGICA'''
    pass


def p_condicion_simple_rel(p):
    '''CONDICION_SIMPLE : OPERANDO OP_RELACIONAL OPERANDO'''
    _registrar_comparacion(p[1], p[3])
    _registrar_comparacion(p[3], p[1])


def p_condicion_simple_bool(p):
    '''CONDICION_SIMPLE : OPERANDO_BOOL'''
    operando = p[1]
    if operando[0] == 'sensor':
        _registrar_sensor(operando[1])
    elif operando[0] == 'acceso':
        _registrar_dispositivo(operando[1])


def p_op_relacional(p):
    '''OP_RELACIONAL : OP_EQ
                     | OP_NEQ
                     | OP_GT
                     | OP_LT
                     | OP_GTE
                     | OP_LTE'''
    p[0] = p[1]


# ------------------------------------------------------------------
# Operandos
# ------------------------------------------------------------------

def p_operando(p):
    '''OPERANDO : ACCESO_DISPOSITIVO
                | ID_SENSOR
                | VALOR'''
    p[0] = _como_operando(p[1])


def p_operando_bool(p):
    '''OPERANDO_BOOL : ACCESO_DISPOSITIVO
                     | ID_SENSOR
                     | VALOR_BOOL'''
    p[0] = _como_operando(p[1])


def _como_operando(simbolo):
    """Normaliza los tres origenes posibles a una tupla etiquetada."""
    if isinstance(simbolo, tuple) and simbolo and simbolo[0] == 'acceso':
        return simbolo                                  # ('acceso', disp, attr)
    if isinstance(simbolo, tuple) and simbolo and simbolo[0] in CLASES_VALOR:
        return ('valor', simbolo[0], simbolo[1])        # ('valor', clase, texto)
    return ('sensor', simbolo)                          # nombre de sensor


def p_id_sensor(p):
    '''ID_SENSOR : SENSOR_TEMP
                 | SENSOR_HUMEDAD
                 | SENSOR_LUZ
                 | SENSOR_MOVIMIENTO
                 | SENSOR_HUMO'''
    p[0] = p[1]


# ------------------------------------------------------------------
# Valores y literales
# ------------------------------------------------------------------

# Cada VALOR se etiqueta con su CLASE (BOOL_DISP, COLOR, TEMP, ...): la
# necesita la validacion semantica (valor<->atributo) y el traductor solo
# distingue EMAIL del resto. La clase se deduce del tipo de token (p.slice).
_CLASE_POR_TOKEN = {
    'TOKEN_CADENA': 'CADENA', 'TOKEN_HORA': 'HORA', 'TOKEN_FECHA': 'FECHA',
    'LIT_COLOR': 'COLOR', 'LIT_MODO': 'MODO',
    'TOKEN_TEMP': 'TEMP', 'TOKEN_PORC': 'PORC', 'TOKEN_LUX': 'LUX',
    'TOKEN_NUMERO': 'NUMERO',
}


def p_valor(p):
    '''VALOR : VALOR_NUMERICO
             | VALOR_BOOL
             | TOKEN_CADENA
             | TOKEN_HORA
             | TOKEN_FECHA
             | LIT_COLOR
             | LIT_MODO'''
    # VALOR_NUMERICO/VALOR_BOOL ya llegan como tupla (clase, texto);
    # los terminales directos se etiquetan por su tipo de token.
    if isinstance(p[1], tuple):
        p[0] = p[1]
    else:
        p[0] = (_CLASE_POR_TOKEN[p.slice[1].type], str(p[1]))


def p_valor_email(p):
    '''VALOR : TOKEN_EMAIL'''
    # se etiqueta distinto para traducirlo como <a href="mailto:..."> (consigna §5)
    p[0] = ('EMAIL', p[1])


def p_valor_numerico(p):
    '''VALOR_NUMERICO : TOKEN_TEMP
                      | TOKEN_PORC
                      | TOKEN_LUX
                      | TOKEN_NUMERO'''
    p[0] = (_CLASE_POR_TOKEN[p.slice[1].type], str(p[1]))


def p_valor_bool(p):
    '''VALOR_BOOL : BOOLEANO_SENSOR
                  | BOOLEANO_DISP'''
    clase = 'BOOL_SENSOR' if p.slice[1].type == 'BOOLEANO_SENSOR' else 'BOOL_DISP'
    p[0] = (clase, p[1])


# ------------------------------------------------------------------
# Errores sintacticos
# ------------------------------------------------------------------

def p_error(tok):
    if tok is None:
        errores_sintacticos.append({
            'linea':   None,
            'cadena':  '<EOF>',
            'mensaje': "[ERROR SINTACTICO] Fin de entrada inesperado "
                       "(¿falta un END o quedo un bloque sin cerrar?)",
        })
        return
    errores_sintacticos.append({
        'linea':   tok.lineno,
        'cadena':  str(tok.value),
        'mensaje': (f"[ERROR SINTACTICO] Token inesperado {tok.type} "
                    f"('{tok.value}') en línea {tok.lineno}"),
    })


# ==================================================================
# GENERACION DE HTML (consigna §5)
#
# Sin estado propio: recibe el "estado de la casa" que las acciones
# semanticas de arriba fueron acumulando DURANTE el parseo (traduccion
# dirigida por sintaxis, una sola pasada) y lo serializa como texto HTML.
# No recorre ningun arbol.
#
# Formato exigido por la consigna:
#   - <div> borde 1px verde, padding 20px  -> estado de sensores
#   - sensores entre <h2>, con valor y unidad
#   - cada actuador en un <div> borde 1px gris, padding 20px
#   - nombre del actuador entre <h1>
#   - atributos como lista <ul>/<li>
#   - emails como <a href="mailto:...">Contactar a <usuario></a>
# ==================================================================

def _item_atributo(atributo, valor):
    """Un <li> por atributo. valor es una tupla (tipo, texto) que arma el parser."""
    tipo, texto = valor
    if tipo == 'EMAIL':
        usuario = texto.split('@', 1)[0]
        return (f'      <li>{atributo}: '
                f'<a href="mailto:{texto}">'
                f'Contactar a {usuario}</a></li>')
    return f'      <li>{atributo}: {texto}</li>'


def renderizar(titulo, sensores, dispositivos):
    """Arma el documento HTML completo.

    sensores:      dict ordenado  nombre -> texto del valor (o None si no se conoce)
    dispositivos:  dict ordenado  nombre -> dict ordenado atributo -> (tipo, texto)
    """
    lineas = [
        '<!DOCTYPE html>',
        '<html lang="es">',
        '<head>',
        '  <meta charset="utf-8">',
        f'  <title>{titulo}</title>',
        '</head>',
        '<body>',
        f'  <h1>SMART HOME &mdash; {titulo}</h1>',
    ]

    # --- estado de sensores (div verde) ---
    if sensores:
        lineas.append('  <div style="border: 1px solid green; padding: 20px;">')
        for nombre, valor in sensores.items():
            if valor is None:
                lineas.append(f'    <h2>{nombre}</h2>')
            else:
                lineas.append(f'    <h2>{nombre}: {valor}</h2>')
        lineas.append('  </div>')

    # --- un div gris por actuador ---
    for nombre, atributos in dispositivos.items():
        lineas.append('  <div style="border: 1px solid gray; padding: 20px;">')
        lineas.append(f'    <h1>{nombre}</h1>')
        if atributos:
            lineas.append('    <ul>')
            for atributo, valor in atributos.items():
                lineas.append(_item_atributo(atributo, valor))
            lineas.append('    </ul>')
        lineas.append('  </div>')

    lineas.append('</body>')
    lineas.append('</html>')
    return '\n'.join(lineas) + '\n'


# ------------------------------------------------------------------
# Construccion del parser y API publica
# ------------------------------------------------------------------

# write_tables=False: no genera parser.out/parsetab.py (nada que ignorar en git).
# errorlog=NullLogger: silencia los avisos por GUION/TOKEN_ID_ESP, que estan en
# el lexer pero a proposito no aparecen en ninguna produccion (gramatica.md §2).
# Se verifico construyendo con el log normal que la gramatica no tiene conflictos.
parser = yacc.yacc(debug=False, write_tables=False, errorlog=yacc.NullLogger())


class _LexerDeLista:
    """Adaptador: le da a yacc una lista de tokens ya emitidos por el lexer.
    Asi el texto se tokeniza UNA sola vez y la misma lista sirve para
    mostrar la tabla de tokens y para parsear (una sola pasada real)."""

    def __init__(self, lista):
        self._iterador = iter(lista)

    def token(self):
        return next(self._iterador, None)


def analizar_programa(lista_tokens, titulo='programa SMART HOME'):
    """Parsea la lista de tokens y devuelve el HTML traducido (str) o None.

    Deja los errores en `errores_sintacticos`. El HTML solo es confiable si
    al terminar no hay errores sintacticos (y el llamador debe chequear
    tambien los lexicos).
    """
    global _titulo
    errores_sintacticos.clear()
    _sensores.clear()
    _dispositivos.clear()
    _titulo = titulo

    if not lista_tokens:
        errores_sintacticos.append({
            'linea':   None,
            'cadena':  '',
            'mensaje': "[ERROR SINTACTICO] Programa vacío: se esperaba al menos una instrucción",
        })
        return None

    html = parser.parse(lexer=_LexerDeLista(lista_tokens))
    if html is None:
        # parse() devuelve None cuando el parser no llego a reducir PROGRAMA
        # (un error no recuperable hasta el final del archivo, donde se llama a
        # renderizar). Pero las acciones semanticas ya registraron en los
        # acumuladores todo lo que se pudo procesar ANTES del fallo: se serializa
        # ese estado parcial igual, para generar la traduccion "hasta donde se
        # pudo" aun con errores. El llamador decide que hacer segun haya errores.
        html = renderizar(_titulo, _sensores, _dispositivos)
    return html
