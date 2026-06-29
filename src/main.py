import sys
import os

try:
    # Ejecucion como modulo (python -m src.main) o desde el .exe de PyInstaller.
    from src.lexer import lexer, errores_lexicos, KEYWORDS
    from src.parser import analizar_programa, errores_sintacticos
except ModuleNotFoundError:
    # Ejecucion directa (python src/main.py): src/ ya esta en sys.path.
    from lexer import lexer, errores_lexicos, KEYWORDS
    from parser import analizar_programa, errores_sintacticos


# Estilo de la interfaz grafica (no requieren tkinter para definirse).
FUENTE_CODIGO = ('Consolas', 11)
COLOR_FONDO_NUM = '#f0f0f0'
COLOR_NUMERO = '#888888'


def analizar_texto(texto):
    """Tokeniza el texto completo. Deja los errores en errores_lexicos."""
    errores_lexicos.clear()
    lexer.lineno = 1
    lexer.input(texto)

    tokens = []
    for tok in lexer:
        tokens.append(tok)

    return tokens


def analizar_completo(texto, titulo='programa SMART HOME'):
    """Corrida completa en UNA pasada: lexer + parser (que traduce a HTML
    mediante sus acciones semanticas). Devuelve (tokens, html|None)."""
    tokens = analizar_texto(texto)
    html = analizar_programa(tokens, titulo)
    return tokens, html


def hay_errores():
    return bool(errores_lexicos or errores_sintacticos)


def analizar_archivo(ruta, mostrar_tokens=True):
    if not ruta.endswith('.smart'):
        print(f"[ERROR] El archivo debe tener extensión .smart (recibido: '{ruta}')")
        return

    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            texto = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Archivo no encontrado: '{ruta}'")
        return

    titulo = os.path.splitext(os.path.basename(ruta))[0]
    tokens, html = analizar_completo(texto, titulo)
    _imprimir_resultado(tokens, mostrar_tokens=mostrar_tokens)

    # La traduccion se escribe SIEMPRE que haya algo para escribir, aunque haya
    # errores: se genera el HTML "hasta donde el analisis pudo continuar".
    if html is not None:
        ruta_html = os.path.splitext(ruta)[0] + '.html'
        with open(ruta_html, 'w', encoding='utf-8') as f:
            f.write(html)
        if hay_errores():
            print(f"  Traducción HTML parcial generada (hasta donde el análisis pudo continuar): {ruta_html}\n")
        else:
            print(f"  Traducción HTML generada: {ruta_html}\n")


def _imprimir_resultado(tokens, mostrar_tokens=True):
    if mostrar_tokens:
        print("\n--- Tokens reconocidos ---")
        for tok in tokens:
            print(f"  {tok.type:<22} | valor: {str(tok.value):<30} | línea: {tok.lineno}")
        print(f"\n  Total de tokens reconocidos: {len(tokens)}")

    if errores_lexicos:
        print(f"\n--- Errores léxicos ({len(errores_lexicos)}) ---")
        for e in errores_lexicos:
            print(f"  {e['mensaje']}")

    if errores_sintacticos:
        print(f"\n--- Errores sintácticos ({len(errores_sintacticos)}) ---")
        for e in errores_sintacticos:
            print(f"  {e['mensaje']}")

    if hay_errores():
        total = len(errores_lexicos) + len(errores_sintacticos)
        print(f"\n  Análisis finalizado con {total} error(es).\n")
    else:
        print("\n  Análisis exitoso: el programa es léxica y sintácticamente correcto.\n")


def abrir_selector_archivos():
    try:
        import tkinter as tk
        from tkinter import filedialog
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

            tokens, _ = analizar_completo(texto, 'sesion interactiva')
            _imprimir_resultado(tokens)
    except KeyboardInterrupt:
        print("\n\nSaliendo del intérprete SMART HOME...")
        sys.exit(0)


def ejecutar_gui():
    """Interfaz grafica (tkinter): editor con numeros de linea + analisis
    lexico/sintactico + traduccion a HTML en una pasada.

    tkinter se importa ACA ADENTRO (no a nivel de modulo) a proposito: los
    modos CLI/consola no pagan ese import y funcionan aunque tkinter no este
    instalado. Como las clases del editor heredan de tk.Text/tk.Tk, deben
    definirse despues del import; por eso viven dentro de esta funcion.

    Componentes:
      - TextoConEventos: tk.Text que emite <<CambioEditor>> ante cualquier
        insercion/borrado/scroll (patron "widget proxy": se renombra el comando
        Tcl interno del widget y se intercepta). Mantiene los numeros de linea
        sincronizados con edicion, scroll y resize.
      - NumerosDeLinea: canvas angosto que se redibuja con las lineas visibles.
      - VentanaPrincipal: toolbar, editor, notebook (Tokens/Errores/HTML) y
        barra de estado.
    """
    import re
    import tempfile
    import webbrowser
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    class TextoConEventos(tk.Text):
        """tk.Text que genera el evento virtual <<CambioEditor>> cada vez que el
        contenido o la vista cambian (insert/delete/replace/scroll/cursor)."""

        def __init__(self, master=None, **kwargs):
            super().__init__(master, **kwargs)
            # patron proxy: renombrar el comando Tcl del widget e interceptarlo
            self._orig = self._w + '_orig'
            self.tk.call('rename', self._w, self._orig)
            self.tk.createcommand(self._w, self._proxy)

        def _proxy(self, comando, *args):
            try:
                resultado = self.tk.call((self._orig, comando) + args)
            except tk.TclError:
                # p. ej. "delete" sin seleccion: no es un error para la app
                return ''
            if (comando in ('insert', 'delete', 'replace', 'yview', 'xview')
                    or (comando == 'mark' and len(args) >= 2 and args[0] == 'set' and args[1] == 'insert')):
                self.event_generate('<<CambioEditor>>', when='tail')
            return resultado

    class NumerosDeLinea(tk.Canvas):
        def __init__(self, master, texto, **kwargs):
            super().__init__(master, width=48, highlightthickness=0,
                             background=COLOR_FONDO_NUM, **kwargs)
            self.texto = texto

        def redibujar(self):
            self.delete('all')
            indice = self.texto.index('@0,0')
            while True:
                info = self.texto.dlineinfo(indice)
                if info is None:
                    break
                numero = indice.split('.')[0]
                self.create_text(44, info[1], anchor='ne', text=numero,
                                 font=FUENTE_CODIGO, fill=COLOR_NUMERO)
                indice = self.texto.index(f'{indice}+1line')

    class VentanaPrincipal(tk.Tk):
        def __init__(self):
            super().__init__()
            self.ruta_actual = None      # archivo .smart abierto (o None)
            self.html_generado = None    # ultima traduccion valida (o None)
            self.modificado = False
            self._tarea_resaltado = None

            self.title('SMART HOME — Intérprete (MISSING ;)')
            self.geometry('1100x720')
            self.minsize(800, 500)

            self._armar_toolbar()
            self._armar_paneles()
            self._armar_barra_estado()
            self._configurar_atajos()
            self._actualizar_titulo()

        # ------------------------------------------------------------------
        # construccion de la interfaz
        # ------------------------------------------------------------------

        def _armar_toolbar(self):
            barra = ttk.Frame(self, padding=(6, 4))
            barra.pack(side='top', fill='x')

            def boton(texto, comando):
                b = ttk.Button(barra, text=texto, command=comando)
                b.pack(side='left', padx=(0, 6))
                return b

            boton('Abrir…', self.abrir_archivo)
            boton('Guardar', self.guardar_archivo)
            boton('Analizar  (F5)', self.analizar)
            self.btn_guardar_html = boton('Guardar HTML…', self.guardar_html)
            self.btn_navegador = boton('Ver en navegador', self.abrir_en_navegador)
            boton('Limpiar', self.limpiar_editor)
            self.btn_guardar_html.state(['disabled'])
            self.btn_navegador.state(['disabled'])

        def _armar_paneles(self):
            panel = ttk.PanedWindow(self, orient='vertical')
            panel.pack(fill='both', expand=True)

            # ----- editor con numeros de linea -----
            marco_editor = ttk.Frame(panel)
            panel.add(marco_editor, weight=3)

            self.texto = TextoConEventos(
                marco_editor, font=FUENTE_CODIGO, undo=True, wrap='none',
                background='white', foreground='#1a1a1a', insertwidth=2,
                padx=6, pady=4,
            )
            self.numeros = NumerosDeLinea(marco_editor, self.texto)

            scroll_v = ttk.Scrollbar(marco_editor, orient='vertical', command=self.texto.yview)
            scroll_h = ttk.Scrollbar(marco_editor, orient='horizontal', command=self.texto.xview)
            self.texto.configure(yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set)

            self.numeros.pack(side='left', fill='y')
            scroll_v.pack(side='right', fill='y')
            scroll_h.pack(side='bottom', fill='x')
            self.texto.pack(side='left', fill='both', expand=True)

            # tags de resaltado
            self.texto.tag_configure('linea_error', background='#ffd9d9')
            self.texto.tag_configure('reservada', foreground='#0000c0', font=FUENTE_CODIGO + ('bold',))
            self.texto.tag_configure('comentario', foreground='#7a7a7a')
            self.texto.tag_configure('cadena', foreground='#a31515')

            self.texto.bind('<<CambioEditor>>', self._al_cambiar_editor)
            self.texto.bind('<Configure>', lambda e: self.numeros.redibujar())
            self.texto.bind('<KeyRelease>', lambda e: self._programar_resaltado())

            # ----- notebook de resultados -----
            self.notebook = ttk.Notebook(panel)
            panel.add(self.notebook, weight=2)

            # pestania Tokens
            marco_tokens = ttk.Frame(self.notebook)
            self.tabla_tokens = ttk.Treeview(
                marco_tokens, columns=('tipo', 'valor', 'linea'), show='headings')
            self.tabla_tokens.heading('tipo', text='Tipo de token')
            self.tabla_tokens.heading('valor', text='Valor')
            self.tabla_tokens.heading('linea', text='Línea')
            self.tabla_tokens.column('tipo', width=220, stretch=False)
            self.tabla_tokens.column('valor', width=420)
            self.tabla_tokens.column('linea', width=70, anchor='center', stretch=False)
            scroll_tokens = ttk.Scrollbar(marco_tokens, orient='vertical',
                                          command=self.tabla_tokens.yview)
            self.tabla_tokens.configure(yscrollcommand=scroll_tokens.set)
            scroll_tokens.pack(side='right', fill='y')
            self.tabla_tokens.pack(fill='both', expand=True)
            self.notebook.add(marco_tokens, text=' Tokens ')

            # pestania Errores
            marco_errores = ttk.Frame(self.notebook)
            self.tabla_errores = ttk.Treeview(
                marco_errores, columns=('tipo', 'linea', 'cadena', 'detalle'), show='headings')
            self.tabla_errores.heading('tipo', text='Tipo')
            self.tabla_errores.heading('linea', text='Línea')
            self.tabla_errores.heading('cadena', text='Cadena')
            self.tabla_errores.heading('detalle', text='Detalle')
            self.tabla_errores.column('tipo', width=110, stretch=False)
            self.tabla_errores.column('linea', width=70, anchor='center', stretch=False)
            self.tabla_errores.column('cadena', width=160, stretch=False)
            self.tabla_errores.column('detalle', width=520)
            scroll_err = ttk.Scrollbar(marco_errores, orient='vertical',
                                       command=self.tabla_errores.yview)
            self.tabla_errores.configure(yscrollcommand=scroll_err.set)
            scroll_err.pack(side='right', fill='y')
            self.tabla_errores.pack(fill='both', expand=True)
            # doble click sobre un error -> saltar a la linea en el editor
            self.tabla_errores.bind('<Double-1>', self._ir_a_error)
            self.notebook.add(marco_errores, text=' Errores ')

            # pestania HTML
            marco_html = ttk.Frame(self.notebook)
            self.vista_html = tk.Text(marco_html, font=FUENTE_CODIGO, wrap='none',
                                      state='disabled', background='#fafafa')
            scroll_html = ttk.Scrollbar(marco_html, orient='vertical',
                                        command=self.vista_html.yview)
            self.vista_html.configure(yscrollcommand=scroll_html.set)
            scroll_html.pack(side='right', fill='y')
            self.vista_html.pack(fill='both', expand=True)
            self.notebook.add(marco_html, text=' HTML ')

        def _armar_barra_estado(self):
            self._mensaje_estado = 'Listo. Pegue o escriba código SMART HOME y presione F5.'
            self.barra_estado = ttk.Label(self, anchor='w', padding=(8, 3))
            self.barra_estado.pack(side='bottom', fill='x')
            self._refrescar_barra_estado()

        def _poner_estado(self, mensaje):
            self._mensaje_estado = mensaje
            self._refrescar_barra_estado()

        def _refrescar_barra_estado(self):
            linea, columna = self.texto.index('insert').split('.')
            self.barra_estado.configure(
                text=f'Ln {linea}, Col {int(columna) + 1}  |  {self._mensaje_estado}')

        def _configurar_atajos(self):
            self.bind('<F5>', lambda e: self.analizar())
            self.bind('<Control-o>', lambda e: self.abrir_archivo())
            self.bind('<Control-s>', lambda e: self.guardar_archivo())
            self.texto.bind('<Control-a>', self._seleccionar_todo)
            self.protocol('WM_DELETE_WINDOW', self._al_cerrar)

        # ------------------------------------------------------------------
        # eventos del editor
        # ------------------------------------------------------------------

        def _al_cambiar_editor(self, _evento=None):
            self.numeros.redibujar()
            self._refrescar_barra_estado()
            if self.texto.edit_modified():
                if not self.modificado:
                    self.modificado = True
                    self._actualizar_titulo()
                self.texto.edit_modified(False)

        def _seleccionar_todo(self, _evento=None):
            self.texto.tag_add('sel', '1.0', 'end-1c')
            return 'break'

        def _actualizar_titulo(self):
            nombre = os.path.basename(self.ruta_actual) if self.ruta_actual else 'sin título'
            marca = ' *' if self.modificado else ''
            self.title(f'SMART HOME — {nombre}{marca}  (MISSING ;)')

        # ------------------------------------------------------------------
        # resaltado de sintaxis (liviano, con debounce)
        # ------------------------------------------------------------------

        def _programar_resaltado(self):
            if self._tarea_resaltado is not None:
                self.after_cancel(self._tarea_resaltado)
            self._tarea_resaltado = self.after(150, self._resaltar_sintaxis)

        def _resaltar_sintaxis(self):
            self._tarea_resaltado = None
            contenido = self.texto.get('1.0', 'end-1c')
            for tag in ('reservada', 'comentario', 'cadena'):
                self.texto.tag_remove(tag, '1.0', 'end')

            patron_reservadas = r'\b(' + '|'.join(KEYWORDS) + r')\b'
            for m in re.finditer(patron_reservadas, contenido, re.IGNORECASE):
                self.texto.tag_add('reservada', f'1.0+{m.start()}c', f'1.0+{m.end()}c')
            for m in re.finditer(r'"(?:[^"\\\n]|\\.)*"', contenido):
                self.texto.tag_add('cadena', f'1.0+{m.start()}c', f'1.0+{m.end()}c')
            for m in re.finditer(r'//[^\n]*', contenido):
                self.texto.tag_add('comentario', f'1.0+{m.start()}c', f'1.0+{m.end()}c')

        # ------------------------------------------------------------------
        # acciones de la toolbar
        # ------------------------------------------------------------------

        def abrir_archivo(self):
            if self.modificado and not messagebox.askyesno(
                    'Cambios sin guardar', '¿Descartar los cambios del editor?'):
                return
            ruta = filedialog.askopenfilename(
                title='Abrir archivo .smart',
                filetypes=[('Archivos SMART HOME (*.smart)', '*.smart'),
                           ('Todos los archivos', '*.*')])
            if not ruta:
                return
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
            except OSError as e:
                messagebox.showerror('Error', f'No se pudo abrir el archivo:\n{e}')
                return
            self.texto.delete('1.0', 'end')
            self.texto.insert('1.0', contenido)
            self.texto.edit_reset()
            self.texto.edit_modified(False)
            self.ruta_actual = ruta
            self.modificado = False
            self._actualizar_titulo()
            self._resaltar_sintaxis()
            self.analizar()

        def guardar_archivo(self):
            if self.ruta_actual is None:
                ruta = filedialog.asksaveasfilename(
                    title='Guardar como', defaultextension='.smart',
                    filetypes=[('Archivos SMART HOME (*.smart)', '*.smart')])
                if not ruta:
                    return
                self.ruta_actual = ruta
            with open(self.ruta_actual, 'w', encoding='utf-8') as f:
                f.write(self.texto.get('1.0', 'end-1c'))
            self.modificado = False
            self.texto.edit_modified(False)
            self._actualizar_titulo()

        def limpiar_editor(self):
            if self.modificado and not messagebox.askyesno(
                    'Cambios sin guardar', '¿Descartar los cambios del editor?'):
                return
            self.texto.delete('1.0', 'end')
            self.ruta_actual = None
            self.modificado = False
            self._actualizar_titulo()
            self._limpiar_resultados()

        def _limpiar_resultados(self):
            self.tabla_tokens.delete(*self.tabla_tokens.get_children())
            self.tabla_errores.delete(*self.tabla_errores.get_children())
            self.texto.tag_remove('linea_error', '1.0', 'end')
            self._mostrar_html('')
            self.html_generado = None
            self.btn_guardar_html.state(['disabled'])
            self.btn_navegador.state(['disabled'])

        # ------------------------------------------------------------------
        # analisis (lexer + parser + traduccion en una pasada)
        # ------------------------------------------------------------------

        def analizar(self):
            contenido = self.texto.get('1.0', 'end-1c')
            self._limpiar_resultados()

            if not contenido.strip():
                self._poner_estado('Nada que analizar: el editor está vacío.')
                return

            titulo = (os.path.splitext(os.path.basename(self.ruta_actual))[0]
                      if self.ruta_actual else 'editor')
            tokens, html = analizar_completo(contenido, titulo)

            for tok in tokens:
                self.tabla_tokens.insert('', 'end',
                                         values=(tok.type, str(tok.value), tok.lineno))

            for e in errores_lexicos:
                self._agregar_error('LÉXICO', e['linea'], e['cadena'], e['mensaje'])
            for e in errores_sintacticos:
                self._agregar_error('SINTÁCTICO', e['linea'], e['cadena'], e['mensaje'])

            total_errores = len(errores_lexicos) + len(errores_sintacticos)
            # El HTML se muestra SIEMPRE que se haya podido generar algo, aunque
            # haya errores (traduccion parcial "hasta donde se pudo").
            if html is not None:
                self.html_generado = html
                self._mostrar_html(html)
                self.btn_guardar_html.state(['!disabled'])
                self.btn_navegador.state(['!disabled'])

            if total_errores == 0 and html is not None:
                estado = (f'Análisis exitoso: {len(tokens)} tokens, sin errores. '
                          f'Traducción HTML lista.')
                self.notebook.select(2)   # mostrar pestania HTML
            else:
                if html is not None:
                    estado = (f'{len(tokens)} tokens  ·  {total_errores} error(es). '
                              f'Se generó HTML parcial.')
                else:
                    estado = f'{len(tokens)} tokens  ·  {total_errores} error(es).'
                self.notebook.select(1)   # mostrar pestania Errores (los errores primero)
            self._poner_estado(estado)

        def _agregar_error(self, tipo, linea, cadena, mensaje):
            self.tabla_errores.insert('', 'end', values=(tipo, linea if linea else '—',
                                                         cadena, mensaje))
            if linea:
                self.texto.tag_add('linea_error', f'{linea}.0', f'{linea}.end')

        def _ir_a_error(self, _evento=None):
            seleccion = self.tabla_errores.selection()
            if not seleccion:
                return
            linea = self.tabla_errores.item(seleccion[0], 'values')[1]
            if linea and linea != '—':
                self.texto.mark_set('insert', f'{linea}.0')
                self.texto.see(f'{linea}.0')
                self.texto.focus_set()

        # ------------------------------------------------------------------
        # salida HTML
        # ------------------------------------------------------------------

        def _mostrar_html(self, html):
            self.vista_html.configure(state='normal')
            self.vista_html.delete('1.0', 'end')
            self.vista_html.insert('1.0', html)
            self.vista_html.configure(state='disabled')

        def guardar_html(self):
            if not self.html_generado:
                return
            sugerido = (os.path.splitext(os.path.basename(self.ruta_actual))[0] + '.html'
                        if self.ruta_actual else 'salida.html')
            ruta = filedialog.asksaveasfilename(
                title='Guardar traducción HTML', defaultextension='.html',
                initialfile=sugerido,
                filetypes=[('Documento HTML (*.html)', '*.html')])
            if not ruta:
                return
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(self.html_generado)
            self._poner_estado(f'HTML guardado en: {ruta}')

        def abrir_en_navegador(self):
            if not self.html_generado:
                return
            with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False,
                                             encoding='utf-8') as f:
                f.write(self.html_generado)
                ruta = f.name
            webbrowser.open(f'file:///{ruta}')

        # ------------------------------------------------------------------

        def _al_cerrar(self):
            if self.modificado and not messagebox.askyesno(
                    'Salir', 'Hay cambios sin guardar. ¿Salir igualmente?'):
                return
            self.destroy()

    ventana = VentanaPrincipal()
    ventana.mainloop()


def modo_grafico():
    ejecutar_gui()


if __name__ == '__main__':
    # Despacho:
    #   python -m src.main archivo.smart|carpeta  -> analisis por archivo (CLI)
    #   python -m src.main --consola              -> REPL de terminal (entrega lexer)
    #   python -m src.main                        -> interfaz grafica (tkinter)
    if len(sys.argv) == 2 and sys.argv[1] != '--consola':
        procesar_ruta(sys.argv[1])
    elif len(sys.argv) == 2:
        modo_interactivo()
    else:
        modo_grafico()
