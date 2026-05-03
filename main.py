import tkinter as tk
from tkinter import messagebox
import nltk
from nltk import CFG, ChartParser
from nltk.tree import Tree
import re


# ---------------------------------------------------------
# LÓGICA DEL NEGOCIO (Paradigma Orientado a Objetos)
# ---------------------------------------------------------
class AnalizadorGramatical:
    """Clase encargada de manejar la gramática, árboles y derivaciones[cite: 1]."""

    def __init__(self, texto_gramatica):
        try:
            self.gramatica = CFG.fromstring(texto_gramatica)
            self.parser = ChartParser(self.gramatica)
        except Exception as e:
            raise ValueError(f"Error al cargar la gramática:\n{e}")

    def obtener_arbol_derivacion(self, expresion):
        tokens = expresion.split()  # La expresión debe estar separada por espacios
        try:
            arboles = list(self.parser.parse(tokens))
            if not arboles:
                return None
            return arboles[0]
        except ValueError as e:
            raise ValueError(f"La expresión contiene símbolos no definidos: {e}")

    def obtener_pasos_derivacion(self, arbol, tipo="Izquierda"):
        """Genera la secuencia de la cadena paso a paso, reemplazando los símbolos."""
        if tipo == "Izquierda":
            reglas = arbol.productions()
        else:
            reglas = self._obtener_producciones_derecha(arbol)

        simbolo_inicial = str(arbol.label())
        cadena_actual = [simbolo_inicial]
        pasos = [f"=> {simbolo_inicial}"]

        for regla in reglas:
            lhs = str(regla.lhs())
            rhs = [str(simbolo).replace("'", "") for simbolo in regla.rhs()]

            if tipo == "Izquierda":
                for i, simbolo in enumerate(cadena_actual):
                    if simbolo == lhs:
                        cadena_actual = cadena_actual[:i] + rhs + cadena_actual[i + 1:]
                        break
            else:
                for i in range(len(cadena_actual) - 1, -1, -1):
                    if cadena_actual[i] == lhs:
                        cadena_actual = cadena_actual[:i] + rhs + cadena_actual[i + 1:]
                        break

            pasos.append(f"=> {' '.join(cadena_actual).ljust(25)} (Regla: {regla})")

        return pasos

    def _obtener_producciones_derecha(self, arbol):
        if not isinstance(arbol, Tree):
            return []
        producciones = [arbol.productions()[0]]
        for hijo in reversed(arbol):
            if isinstance(hijo, Tree):
                producciones.extend(self._obtener_producciones_derecha(hijo))
        return producciones

    def simplificar_a_ast(self, arbol):
        """Generación del Abstract Syntax Tree (AST) omitiendo nodos redundantes[cite: 1]."""
        if not isinstance(arbol, Tree):
            return arbol
        if len(arbol) == 1 and isinstance(arbol[0], Tree):
            return self.simplificar_a_ast(arbol[0])
        else:
            hijos_simplificados = [self.simplificar_a_ast(hijo) for hijo in arbol]
            return Tree(arbol.label(), hijos_simplificados)


# ---------------------------------------------------------
# INTERFAZ GRÁFICA (UI)
# ---------------------------------------------------------
class AplicacionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Árboles Sintácticos (POO)")
        self.root.geometry("700x580")

        # --- Área para ingresar la Gramática ---
        tk.Label(root, text="1. Ingresa la Gramática (Puedes usar [a-z], [A-Z], [0-9]):",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        self.text_gramatica = tk.Text(root, height=10, width=80)
        self.text_gramatica.pack(padx=10)

        # Volvemos a la gramática limpia original
        gramatica_default = (
            "E -> E '+' T | E '-' T | T\n"
            "T -> T '*' F | T '/' F | F\n"
            "F -> '(' E ')' | [a-z]"
        )
        self.text_gramatica.insert(tk.END, gramatica_default)

        # --- Área para ingresar la Expresión ---
        tk.Label(root, text="2. Ingresa la Expresión a evaluar (separada por espacios):",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        self.entry_expresion = tk.Entry(root, width=80)
        self.entry_expresion.pack(padx=10)
        # Volvemos a la expresión original
        self.entry_expresion.insert(0, "x + y * z")

        # --- Opciones de Derivación ---
        self.tipo_derivacion = tk.StringVar(value="Izquierda")
        frame_radios = tk.Frame(root)
        frame_radios.pack(pady=10)
        tk.Radiobutton(frame_radios, text="Derivación por la izquierda", variable=self.tipo_derivacion,
                       value="Izquierda").pack(side=tk.LEFT)
        tk.Radiobutton(frame_radios, text="Derivación por la Derecha", variable=self.tipo_derivacion,
                       value="Derecha").pack(side=tk.LEFT)

        # --- Botones de Acción ---
        frame_botones = tk.Frame(root)
        frame_botones.pack(pady=10)
        tk.Button(frame_botones, text="Mostrar Derivación", command=self.mostrar_derivacion).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Generar Árbol de Derivación", command=self.mostrar_arbol).pack(side=tk.LEFT,
                                                                                                      padx=5)
        tk.Button(frame_botones, text="Generar AST", command=self.mostrar_ast).pack(side=tk.LEFT, padx=5)

        # --- Área de Resultados ---
        self.text_resultados = tk.Text(root, height=12, width=80, state=tk.DISABLED, font=("Courier", 9))
        self.text_resultados.pack(padx=10, pady=10)

    def _procesar_entrada(self):
        gramatica_str = self.text_gramatica.get("1.0", tk.END).strip()
        expresion_str = self.entry_expresion.get().strip()

        if not gramatica_str or not expresion_str:
            messagebox.showwarning("Advertencia", "Por favor ingresa la gramática y la expresión.")
            return None, None

        tokens = expresion_str.split()

        # Busca los corchetes (ej. '[a-z]', '[A-Z]', '[0-9]')
        patrones_corchetes = re.findall(r'\[.*?\]', gramatica_str)

        for patron in set(patrones_corchetes):
            # Evaluamos exactamente como un solo caracter usando regex
            regex_to_match = f"^{patron}$"

            # Filtramos qué tokens de la expresión cumplen con el corchete
            coincidencias = [t for t in tokens if re.fullmatch(regex_to_match, t)]

            # Reemplazamos el corchete por las letras/números reales encontrados
            if coincidencias:
                reemplazo = " | ".join([f"'{c}'" for c in set(coincidencias)])
            else:
                reemplazo = "'__SIN_COINCIDENCIA__'"

            gramatica_str = gramatica_str.replace(patron, reemplazo)

        try:
            analizador = AnalizadorGramatical(gramatica_str)
            arbol = analizador.obtener_arbol_derivacion(expresion_str)

            if arbol is None:
                messagebox.showerror("Error", "La expresión no es válida para la gramática dada.")
                return None, None

            return analizador, arbol
        except Exception as e:
            messagebox.showerror("Error de Sintaxis", str(e))
            return None, None

    def mostrar_derivacion(self):
        analizador, arbol = self._procesar_entrada()
        if analizador and arbol:
            tipo = self.tipo_derivacion.get()
            pasos = analizador.obtener_pasos_derivacion(arbol, tipo)

            self.text_resultados.config(state=tk.NORMAL)
            self.text_resultados.delete("1.0", tk.END)
            self.text_resultados.insert(tk.END, f"Derivación por la {tipo}:\n\n")
            for paso in pasos:
                self.text_resultados.insert(tk.END, paso + "\n")
            self.text_resultados.config(state=tk.DISABLED)

    def mostrar_arbol(self):
        _, arbol = self._procesar_entrada()
        if arbol:
            arbol.draw()

    def mostrar_ast(self):
        analizador, arbol = self._procesar_entrada()
        if analizador and arbol:
            ast = analizador.simplificar_a_ast(arbol)
            ast.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionGUI(root)
    root.mainloop()
