import sys
from src.lexer import lexer, errores_lexicos


def analizar_texto(texto):
    errores_lexicos.clear()
    lexer.lineno = 1
    lexer.input(texto)

    tokens = []
    for tok in lexer:
        tokens.append(tok)

    return tokens


def analizar_archivo(ruta):
    if not ruta.endswith('.smart'):
        print(f"[ERROR] El archivo debe tener extensión .smart (recibido: '{ruta}')")
        return

    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            texto = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Archivo no encontrado: '{ruta}'")
        return

    tokens = analizar_texto(texto)
    _imprimir_resultado(tokens)


def _imprimir_resultado(tokens):
    print("\n--- Tokens reconocidos ---")
    for tok in tokens:
        print(f"  {tok.type:<22} | valor: {str(tok.value):<30} | línea: {tok.lineno}")

    if errores_lexicos:
        print("\n--- Errores léxicos ---")
        for e in errores_lexicos:
            print(f"  {e['mensaje']}")
    else:
        print("\n  Sin errores léxicos.")
    print()


def modo_interactivo():
    print("=== Intérprete SMART HOME — Modo interactivo ===")
    print("Escriba sentencias SMART HOME. Línea vacía para analizar.")
    print("Escriba 'salir' para terminar.\n")

    while True:
        lineas = []
        try:
            while True:
                linea = input(">> ")
                if linea.strip().lower() == 'salir':
                    sys.exit(0)
                if linea.strip() == '':
                    break
                lineas.append(linea)
        except EOFError:
            break

        texto = '\n'.join(lineas)
        if not texto.strip():
            continue

        tokens = analizar_texto(texto)
        _imprimir_resultado(tokens)



if __name__ == '__main__':
    if len(sys.argv) == 2:
        analizar_archivo(sys.argv[1])
    else:
        modo_interactivo()
