import tkinter as tk
from tkinter import messagebox
from nltk import CFG, ChartParser
from nltk.tree import Tree
import re, math

# ── PALETA ──
C = {
    "bg": "#1e1e2e", "bg_alt": "#282839", "surface": "#313244",
    "surface_hl": "#45475a", "text": "#cdd6f4", "text_dim": "#a6adc8",
    "accent": "#89b4fa", "accent_hover": "#74c7ec",
    "green": "#a6e3a1", "green_hover": "#94e2d5",
    "mauve": "#cba6f7", "mauve_hover": "#b4befe",
    "red": "#f38ba8", "yellow": "#f9e2af",
    "peach": "#fab387", "teal": "#94e2d5",
    "node_nt": "#89b4fa", "node_t": "#a6e3a1", "edge": "#585b70",
}


# ── LÓGICA ──
class AnalizadorGramatical:
    def __init__(self, texto):
        try:
            self.gramatica = CFG.fromstring(texto)
            self.parser = ChartParser(self.gramatica)
        except Exception as e:
            raise ValueError(f"Error al cargar la gramática:\n{e}")

    def obtener_arbol(self, expr):
        try:
            arboles = list(self.parser.parse(expr.split()))
            return arboles[0] if arboles else None
        except ValueError as e:
            raise ValueError(f"Símbolos no definidos: {e}")

    def derivacion(self, arbol, tipo="Izquierda"):
        reglas = arbol.productions() if tipo == "Izquierda" else self._prod_der(arbol)
        s = str(arbol.label()); cadena = [s]; pasos = [f"=> {s}"]
        for r in reglas:
            lhs = str(r.lhs()); rhs = [str(x).replace("'","") for x in r.rhs()]
            rng = enumerate(cadena) if tipo == "Izquierda" else reversed(list(enumerate(cadena)))
            for i, x in rng:
                if x == lhs:
                    cadena = cadena[:i] + rhs + cadena[i+1:]; break
            pasos.append(f"=> {' '.join(cadena).ljust(25)} ({r})")
        return pasos

    def _prod_der(self, t):
        if not isinstance(t, Tree): return []
        p = [t.productions()[0]]
        for h in reversed(t):
            if isinstance(h, Tree): p.extend(self._prod_der(h))
        return p

    def simplificar_ast(self, t):
        if not isinstance(t, Tree): return t
        if len(t) == 1 and isinstance(t[0], Tree): return self.simplificar_ast(t[0])
        return Tree(t.label(), [self.simplificar_ast(h) for h in t])


# ── VISUALIZADOR DE ÁRBOLES ──
class TreeVisualizer(tk.Toplevel):
    H_SPACE = 64   # horizontal spacing between leaves
    V_GAP = 70     # vertical gap between levels
    NODE_R = 18    # node circle radius
    ANIM_DELAY = 55

    def __init__(self, master, tree, title="Árbol", accent=C["accent"]):
        super().__init__(master)
        self.title(title)
        self.configure(bg=C["bg"])
        self.accent = accent
        self.nodes = []   # (x, y, label, is_leaf)
        self.edges = []   # (px, py, cx, cy)
        self._anim_idx = 0
        self._leaf_counter = 0

        depth = self._depth(tree)
        n_leaves = self._count_leaves(tree)
        canvas_w = max(n_leaves * self.H_SPACE + 80, 380)
        canvas_h = max(depth * self.V_GAP + 80, 280)

        self.geometry(f"{canvas_w}x{canvas_h + 44}")
        self.minsize(340, 240)

        # Header
        hdr = tk.Frame(self, bg=C["bg_alt"], pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"✦  {title}", font=("Segoe UI", 12, "bold"),
                 fg=accent, bg=C["bg_alt"]).pack(side=tk.LEFT, padx=16)
        # Legend
        tk.Label(hdr, text="● No-terminal   ● Terminal",
                 font=("Segoe UI", 9), fg=C["text_dim"], bg=C["bg_alt"]
                 ).pack(side=tk.RIGHT, padx=16)

        # Scrollable canvas
        frame = tk.Frame(self, bg=C["bg"])
        frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(frame, bg=C["bg"], highlightthickness=0,
                                scrollregion=(0, 0, canvas_w, canvas_h))
        sx = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        sy = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Compute positions (BFS-like: assign x based on leaf index)
        self._leaf_counter = 0
        self._layout(tree, 0, 40, canvas_w)
        self._animate()

    @staticmethod
    def _depth(t):
        if not isinstance(t, Tree): return 1
        return 1 + max(TreeVisualizer._depth(c) for c in t)

    @staticmethod
    def _count_leaves(t):
        if not isinstance(t, Tree): return 1
        return sum(TreeVisualizer._count_leaves(c) for c in t)

    def _leaf_width(self, t):
        """Return number of leaves under t."""
        if not isinstance(t, Tree): return 1
        return sum(self._leaf_width(c) for c in t)

    def _layout(self, t, level, x_start, x_end):
        """Recursively position nodes. Each subtree gets a proportional x-range."""
        label = str(t.label()) if isinstance(t, Tree) else str(t)
        is_leaf = not isinstance(t, Tree)
        cx = (x_start + x_end) / 2
        cy = 30 + level * self.V_GAP
        self.nodes.append((cx, cy, label, is_leaf))

        if isinstance(t, Tree):
            total_leaves = self._leaf_width(t)
            child_x = x_start
            for child in t:
                child_leaves = self._leaf_width(child)
                child_x_end = child_x + (child_leaves / total_leaves) * (x_end - x_start)
                child_cx = (child_x + child_x_end) / 2
                child_cy = 30 + (level + 1) * self.V_GAP
                self.edges.append((cx, cy + self.NODE_R,
                                   child_cx, child_cy - self.NODE_R))
                self._layout(child, level + 1, child_x, child_x_end)
                child_x = child_x_end

    def _animate(self):
        idx = self._anim_idx
        r = self.NODE_R
        # Draw edge
        if idx < len(self.edges):
            px, py, ex, ey = self.edges[idx]
            mid_y = (py + ey) / 2
            self.canvas.create_line(px, py, px, mid_y, ex, mid_y, ex, ey,
                                    fill=C["edge"], width=2, smooth=True)
        # Draw node
        if idx < len(self.nodes):
            x, y, label, is_leaf = self.nodes[idx]
            col = C["node_t"] if is_leaf else self.accent
            # Outer glow
            for g in range(3, 0, -1):
                self.canvas.create_oval(x-r-g*2, y-r-g*2, x+r+g*2, y+r+g*2,
                                        fill="", outline=col, width=1,
                                        stipple="gray12")
            # Filled node
            self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                    fill=C["surface"], outline=col, width=2)
            self.canvas.create_text(x, y, text=label, fill=col,
                                    font=("Cascadia Code", 11, "bold"))
        self._anim_idx += 1
        if self._anim_idx <= max(len(self.nodes), len(self.edges)):
            self.after(self.ANIM_DELAY, self._animate)


# ── WIDGETS ──
class StyledButton(tk.Button):
    def __init__(self, parent, text, command, bg, bg_hover, fg="#1e1e2e",
                 width=14, **kw):
        super().__init__(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=bg_hover, activeforeground=fg,
                         font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                         borderwidth=0, cursor="hand2", width=width, pady=6, **kw)
        self._bg, self._bg_hover = bg, bg_hover
        self.bind("<Enter>", lambda e: self.config(bg=self._bg_hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))


class StyledText(tk.Frame):
    def __init__(self, parent, height=10, readonly=False, font_cfg=None):
        super().__init__(parent, bg=C["bg_alt"])
        ft = font_cfg or ("Cascadia Code", 10)
        self.text = tk.Text(self, height=height, wrap=tk.WORD, bg=C["surface"],
                            fg=C["text"], insertbackground=C["accent"],
                            selectbackground=C["accent"], selectforeground=C["bg"],
                            font=ft, relief=tk.FLAT, borderwidth=0, padx=12, pady=10)
        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview,
                          bg=C["surface"], troughcolor=C["surface"],
                          activebackground=C["surface_hl"])
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        if readonly: self.text.config(state=tk.DISABLED)
        self.text.tag_configure("rule", foreground=C["accent"])
        self.text.tag_configure("step", foreground=C["green"])
        self.text.tag_configure("header", foreground=C["mauve"],
                                font=(ft[0], ft[1], "bold"))

    def get_content(self):
        return self.text.get("1.0", tk.END).strip()


# ── APP PRINCIPAL ──
class AplicacionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("✦  Analizador Sintáctico  —  Generador de Árboles")
        self.root.geometry("820x740")
        self.root.minsize(720, 640)
        self.root.configure(bg=C["bg"])
        self.root.attributes("-alpha", 0.0)

        self._ft_title = ("Segoe UI", 16, "bold")
        self._ft_sub = ("Segoe UI", 10, "bold")
        self._ft_body = ("Segoe UI", 10)
        self._ft_mono = ("Cascadia Code", 10)
        self._ft_sm = ("Segoe UI", 9)

        # main container for fade-in
        self._main = tk.Frame(root, bg=C["bg"])
        self._main.pack(fill=tk.BOTH, expand=True)

        self._build_header()
        self._build_grammar()
        self._build_expression()
        self._build_controls()
        self._build_results()
        self._build_status()

        # Fade-in animation
        self._fade_alpha = 0.0
        self._fade_in()

    def _fade_in(self):
        self._fade_alpha = min(self._fade_alpha + 0.08, 1.0)
        self.root.attributes("-alpha", self._fade_alpha)
        if self._fade_alpha < 1.0:
            self.root.after(20, self._fade_in)

    def _build_header(self):
        h = tk.Frame(self._main, bg=C["bg_alt"], pady=14)
        h.pack(fill=tk.X)
        tk.Label(h, text="✦  Generador de Árboles Sintácticos",
                 font=self._ft_title, fg=C["accent"], bg=C["bg_alt"]
                 ).pack(side=tk.LEFT, padx=20)
        tk.Label(h, text="Paradigma Orientado a Objetos",
                 font=self._ft_sm, fg=C["text_dim"], bg=C["bg_alt"]
                 ).pack(side=tk.RIGHT, padx=20)

    def _build_grammar(self):
        s = tk.Frame(self._main, bg=C["bg"], padx=20, pady=6)
        s.pack(fill=tk.X)
        tk.Label(s, text="① Gramática  (soporta [a-z], [A-Z], [0-9])",
                 font=self._ft_sub, fg=C["text"], bg=C["bg"], anchor="w"
                 ).pack(fill=tk.X, pady=(0,4))
        self.text_gram = StyledText(s, height=7, font_cfg=self._ft_mono)
        self.text_gram.pack(fill=tk.X)
        self.text_gram.text.insert(tk.END,
            "E -> E '+' T | E '-' T | T\n"
            "T -> T '*' F | T '/' F | F\n"
            "F -> '(' E ')' | [a-z]")

    def _build_expression(self):
        s = tk.Frame(self._main, bg=C["bg"], padx=20, pady=6)
        s.pack(fill=tk.X)
        tk.Label(s, text="② Expresión a evaluar  (separada por espacios)",
                 font=self._ft_sub, fg=C["text"], bg=C["bg"], anchor="w"
                 ).pack(fill=tk.X, pady=(0,4))
        ef = tk.Frame(s, bg=C["surface"], padx=12, pady=8)
        ef.pack(fill=tk.X)
        self.entry_expr = tk.Entry(ef, font=self._ft_mono, bg=C["surface"],
                                   fg=C["text"], insertbackground=C["accent"],
                                   selectbackground=C["accent"],
                                   selectforeground=C["bg"],
                                   relief=tk.FLAT, borderwidth=0)
        self.entry_expr.pack(fill=tk.X)
        self.entry_expr.insert(0, "x + y * z")

    def _build_controls(self):
        ctrl = tk.Frame(self._main, bg=C["bg"], padx=20, pady=8)
        ctrl.pack(fill=tk.X)
        rf = tk.Frame(ctrl, bg=C["bg"]); rf.pack(side=tk.LEFT)
        self.tipo_der = tk.StringVar(value="Izquierda")
        for txt, val in [("◀  Izquierda","Izquierda"),("Derecha  ▶","Derecha")]:
            tk.Radiobutton(rf, text=txt, variable=self.tipo_der, value=val,
                           font=self._ft_body, fg=C["text"], bg=C["bg"],
                           selectcolor=C["surface"], activebackground=C["bg"],
                           activeforeground=C["accent"]
                           ).pack(side=tk.LEFT, padx=(0,12))
        bf = tk.Frame(ctrl, bg=C["bg"]); bf.pack(side=tk.RIGHT)
        StyledButton(bf, "⚡ Derivación", self._do_derivacion,
                     C["green"], C["green_hover"], width=14).pack(side=tk.LEFT, padx=4)
        StyledButton(bf, "🌳 Árbol", self._do_arbol,
                     C["accent"], C["accent_hover"], width=10).pack(side=tk.LEFT, padx=4)
        StyledButton(bf, "✦ AST", self._do_ast,
                     C["mauve"], C["mauve_hover"], width=8).pack(side=tk.LEFT, padx=4)

    def _build_results(self):
        s = tk.Frame(self._main, bg=C["bg"], padx=20, pady=6)
        s.pack(fill=tk.BOTH, expand=True)
        tk.Label(s, text="③ Resultados", font=self._ft_sub,
                 fg=C["text"], bg=C["bg"], anchor="w").pack(fill=tk.X, pady=(0,4))
        self.text_res = StyledText(s, height=12, readonly=True, font_cfg=self._ft_mono)
        self.text_res.pack(fill=tk.BOTH, expand=True)

    def _build_status(self):
        self.status_var = tk.StringVar(value="Listo — ingresa una gramática y una expresión.")
        bar = tk.Frame(self.root, bg=C["surface_hl"], height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM); bar.pack_propagate(False)
        self.status_lbl = tk.Label(bar, textvariable=self.status_var,
                                   font=self._ft_sm, fg=C["text_dim"],
                                   bg=C["surface_hl"], anchor="w", padx=16)
        self.status_lbl.pack(fill=tk.X)

    def _status(self, msg, col=None):
        self.status_var.set(msg)
        self.status_lbl.config(fg=col or C["text_dim"])

    # ── Procesar ──
    def _procesar(self):
        gram = self.text_gram.get_content()
        expr = self.entry_expr.get().strip()
        if not gram or not expr:
            messagebox.showwarning("Advertencia", "Ingresa la gramática y la expresión.")
            self._status("⚠  Campos vacíos.", C["yellow"]); return None, None
        tokens = expr.split()
        for pat in set(re.findall(r'\[.*?\]', gram)):
            matches = [t for t in tokens if re.fullmatch(f"^{pat}$", t)]
            repl = " | ".join(f"'{c}'" for c in set(matches)) if matches else "'__NONE__'"
            gram = gram.replace(pat, repl)
        try:
            a = AnalizadorGramatical(gram)
            t = a.obtener_arbol(expr)
            if t is None:
                messagebox.showerror("Error", "Expresión no válida para la gramática.")
                self._status("✖  Expresión no válida.", C["red"]); return None, None
            return a, t
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._status("✖  Error de sintaxis.", C["red"]); return None, None

    # ── Typewriter animation ──
    def _typewriter(self, lines, idx=0):
        if idx >= len(lines): return
        txt, tag = lines[idx]
        r = self.text_res.text
        r.config(state=tk.NORMAL)
        r.insert(tk.END, txt + "\n", tag)
        r.see(tk.END)
        r.config(state=tk.DISABLED)
        self.root.after(50, self._typewriter, lines, idx + 1)

    def _do_derivacion(self):
        a, t = self._procesar()
        if not a: return
        tipo = self.tipo_der.get()
        pasos = a.derivacion(t, tipo)
        r = self.text_res.text
        r.config(state=tk.NORMAL); r.delete("1.0", tk.END); r.config(state=tk.DISABLED)
        lines = [
            (f"  Derivación por la {tipo}", "header"),
            ("  " + "─" * 50, ""),
            ("", ""),
        ]
        for i, p in enumerate(pasos):
            tag = "step" if i == 0 or i == len(pasos) - 1 else ""
            lines.append((f"  {p}", tag))
        self._typewriter(lines)
        self._status(f"✔  Derivación {tipo} — {len(pasos)} pasos.", C["green"])

    def _do_arbol(self):
        _, t = self._procesar()
        if not t: return
        TreeVisualizer(self.root, t, "Árbol de Derivación", C["accent"])
        self._status("✔  Árbol de derivación generado.", C["accent"])

    def _do_ast(self):
        a, t = self._procesar()
        if not a: return
        ast = a.simplificar_ast(t)
        TreeVisualizer(self.root, ast, "Abstract Syntax Tree (AST)", C["mauve"])
        self._status("✔  AST generado.", C["mauve"])


if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionGUI(root)
    root.mainloop()
