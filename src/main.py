import sys
import os
import tkinter as tk
from tkinter import filedialog
try:
    # Ejecución como módulo (python -m src.main) o desde el .exe de PyInstaller.
    from src.lexer import lexer, errores_lexicos
except ModuleNotFoundError:
    # Ejecución directa (python src/main.py): src/ ya está en sys.path.
    from lexer import lexer, errores_lexicos


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

    print(f"\n  Total de tokens reconocidos: {len(tokens)}")

    if errores_lexicos:
        print(f"\n--- Errores léxicos ({len(errores_lexicos)}) ---")
        for e in errores_lexicos:
            print(f"  {e['mensaje']}")
    else:
        print("\n  Sin errores léxicos.")
    print()


def abrir_selector_archivos():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo .smart",
            filetypes=[("Archivos SMART HOME (*.smart)", "*.smart"), ("Todos los archivos", "*.*")]
        )
        root.destroy()
        return ruta
    except Exception as e:
        print(f"[ERROR] No se pudo abrir el selector gráfico: {e}")
        return ""


def procesar_ruta(ruta):
    if os.path.isdir(ruta):
        archivos = [os.path.join(ruta, f) for f in os.listdir(ruta) if f.endswith('.smart')]
        if not archivos:
            print(f"No se encontraron archivos con extensión .smart en el directorio: '{ruta}'")
        else:
            for archivo in sorted(archivos):
                print(f"\n==========================================")
                print(f"Analizando archivo: {archivo}")
                print(f"==========================================")
                analizar_archivo(archivo)
    else:
        analizar_archivo(ruta)


def modo_interactivo():
    print("=== Intérprete SMART HOME || MISSING ; ===")
    print("Escriba sentencias SMART HOME.")
    print("Para cargar un archivo escriba: /cargar y presione enter.")
    print("Presione Ctrl+C para salir.\n")
    print("Inserte línea vacía para analizar.")

    try:
        while True:
            lineas = []
            es_comando = False
            try:
                while True:
                    linea = input(">> ")
                    linea_clean = linea.strip()
                    if linea_clean == "/cargar":
                        ruta = abrir_selector_archivos()
                        if ruta:
                            procesar_ruta(ruta)
                        else:
                            print("Selección de archivo cancelada.")
                            
                        es_comando = True
                        break
                    if linea.strip() == '':
                        break
                    lineas.append(linea)
            except EOFError:
                break

            if es_comando:
                continue

            texto = '\n'.join(lineas)
            if not texto.strip():
                continue

            tokens = analizar_texto(texto)
            _imprimir_resultado(tokens)
    except KeyboardInterrupt:
        print("\n\nSaliendo del intérprete SMART HOME...")
        sys.exit(0)



if __name__ == '__main__':
    if len(sys.argv) == 2:
        procesar_ruta(sys.argv[1])
    else:
        modo_interactivo()
