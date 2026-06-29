
import ply.lex as lex

errores_lexicos = []


#  listado de tokens 
tokens = (
    # reservadas
    'WHEN', 'EVERY', 'IF', 'THEN', 'ELSE', 'DO', 'END',
    'AND', 'OR', 'NOT',

    # sensores
    'SENSOR_TEMP', 'SENSOR_HUMEDAD', 'SENSOR_LUZ',
    'SENSOR_MOVIMIENTO', 'SENSOR_HUMO',

    # actuadores: identificador completo con prefijo (foco_entrada, aire_living, ...)
    'ID_DISPOSITIVO',

    # atributos
    'ATTR_ESTADO', 'ATTR_BRILLO', 'ATTR_COLOR', 'ATTR_MODO',
    'ATTR_TEMP_OBJ', 'ATTR_TEMP_ACT', 'ATTR_POSICION',
    'ATTR_VOLUMEN', 'ATTR_MUTE', 'ATTR_MENSAJE', 'ATTR_EMAIL_NOTIF',
    'ATTR_ACTIVADA', 'ATTR_HORA', 'ATTR_FECHA',

    # booleanos y discretos
    'BOOLEANO_SENSOR',   # true / false
    'BOOLEANO_DISP',     # on  / off
    'LIT_COLOR',         # blanco / rojo / azul
    'LIT_MODO',          # frio / calor / vent

    # tokens compuestos con unidad
    'TOKEN_TEMP',        # 25°C  -5°C
    'TOKEN_PORC',        # 80%
    'TOKEN_LUX',         # 250lux
    'TOKEN_TIEMPO',      # 30m  10s  1h
    'TOKEN_HORA',        # 22:00
    'TOKEN_FECHA',       # 21/04/2026
    'TOKEN_EMAIL',       # felipe@smart-home.com.ar
    'TOKEN_CADENA',      # "texto entre comillas"
    'TOKEN_NUMERO',      # 42
    'TOKEN_ID_ESP',      # entrada  acondicionado y lo que pinte todo cae aca menos caracteres invalidos y los otros tokens

    # op relacionales
    'OP_EQ', 'OP_NEQ', 'OP_GTE', 'OP_LTE', 'OP_GT', 'OP_LT',

    # asignación y puntuación
    'ASIG',
    'PUNTO',
    'GUION',
    'L_PAR',
    'R_PAR',
)


# case insensitive
KEYWORDS = {
    'when': 'WHEN', 'every': 'EVERY', 'if': 'IF',
    'then': 'THEN', 'else': 'ELSE', 'do': 'DO', 'end': 'END',
    'and':  'AND',  'or':   'OR',    'not': 'NOT',
}

SENSORES = {
    'sensor_movimiento': 'SENSOR_MOVIMIENTO',
    'sensor_humedad':    'SENSOR_HUMEDAD',
    'sensor_temp':       'SENSOR_TEMP',
    'sensor_luz':        'SENSOR_LUZ',
    'sensor_humo':       'SENSOR_HUMO',
}

# prefijos de actuador: si un identificador EMPIEZA con uno de estos,
# se emite como un unico token ID_DISPOSITIVO (ver doc/gramatica.md §0)
PREFIJOS_DISP = (
    'cerradura_',
    'persiana_',
    'altavoz_',
    'alarma_',
    'reloj_',
    'foco_',
    'aire_',
)

ATRIBUTOS = {
    'temp_obj':    'ATTR_TEMP_OBJ',
    'temp_act':    'ATTR_TEMP_ACT',
    'email_notif': 'ATTR_EMAIL_NOTIF',
    'activada':    'ATTR_ACTIVADA',
    'posicion':    'ATTR_POSICION',
    'mensaje':     'ATTR_MENSAJE',
    'volumen':     'ATTR_VOLUMEN',
    'estado':      'ATTR_ESTADO',
    'brillo':      'ATTR_BRILLO',
    'color':       'ATTR_COLOR',
    'fecha':       'ATTR_FECHA',
    'hora':        'ATTR_HORA',
    'modo':        'ATTR_MODO',
    'mute':        'ATTR_MUTE',
}

BOOL_SENSOR = {'true', 'false'}
BOOL_DISP   = {'on', 'off'}
LIT_COLORES = {'blanco', 'rojo', 'azul'}
LIT_MODOS   = {'frio', 'calor', 'vent'}



# tokens q van antes del identificador genérico
def t_TOKEN_TEMP(t):
    r'-?[0-9]+(\.[0-9]+)?\xb0C'
    return t

def t_TOKEN_PORC(t):
    r'(100|[0-9]{1,2})%'
    return t

def t_TOKEN_LUX(t):
    r'[0-9]{1,4}lux'
    return t

def t_TOKEN_TIEMPO(t):
    r'[0-9]+(s|m|h)'
    return t

def t_TOKEN_HORA(t):
    r'([01][0-9]|2[0-3]):[0-5][0-9]'
    return t

def t_TOKEN_FECHA(t):
    r'(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/(19[0-9]{2}|20[0-9]{2})'
    return t

def t_TOKEN_EMAIL(t):
    r'[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,4}'
    return t

def t_TOKEN_CADENA(t):
    r'"(?:[^"\\\n]|\\.)*"'
    t.value = t.value[1:-1]
    return t

def t_TOKEN_NUMERO(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t


# id generico

def t_TOKEN_ID_ESP(t):
    r'[a-zA-Z][a-zA-Z0-9_]*'
    lower = t.value.lower()

    if lower in KEYWORDS:
        t.type  = KEYWORDS[lower]
        t.value = lower.upper()
    elif lower in SENSORES:
        t.type  = SENSORES[lower]
        t.value = lower
    elif lower in ATRIBUTOS:
        t.type  = ATRIBUTOS[lower]
        t.value = lower
    elif lower in BOOL_SENSOR:
        t.type  = 'BOOLEANO_SENSOR'
        t.value = lower.upper()
    elif lower in BOOL_DISP:
        t.type  = 'BOOLEANO_DISP'
        t.value = lower.upper()
    elif lower in LIT_COLORES:
        t.type  = 'LIT_COLOR'
        t.value = lower
    elif lower in LIT_MODOS:
        t.type  = 'LIT_MODO'
        t.value = lower.upper()
    elif lower.startswith(PREFIJOS_DISP):
        t.type  = 'ID_DISPOSITIVO'
        t.value = lower
    else:
        t.type  = 'TOKEN_ID_ESP'
        t.value = lower

    return t


#  op relacioanles
def t_OP_EQ(t):
    r'=='
    return t

def t_OP_NEQ(t):
    r'!='
    return t

def t_OP_GTE(t):
    r'>='
    return t

def t_OP_LTE(t):
    r'<='
    return t

def t_OP_GT(t):
    r'>'
    return t

def t_OP_LT(t):
    r'<'
    return t


#  aisignación y puntuación
def t_ASIG(t):
    r'='
    return t

def t_PUNTO(t):
    r'\.'
    return t

def t_GUION(t):
    r'_'
    return t

def t_L_PAR(t):
    r'\('
    return t

def t_R_PAR(t):
    r'\)'
    return t


# comentarios conteo de linea e ignores

def t_COMENTARIO(t):
    r'//[^\n]*'
    pass

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')


# errorres

def t_error(t):
    mensaje = (
        f"[ERROR LÉXICO] Carácter ilegal '{t.value[0]}' "
        f"en línea {t.lineno}, posición {t.lexpos}"
    )
    errores_lexicos.append({
        'linea':    t.lineno,
        'posicion': t.lexpos,
        'cadena':   t.value[0],
        'mensaje':  mensaje
    })
    t.lexer.skip(1)

# crea el lexer
lexer = lex.lex()
