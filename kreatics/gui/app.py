"""
app.py - Kreatics Compiler Studio (Tkinter GUI).

This file only DISPLAYS things.  Every table, tree, symbol and instruction on
screen comes from kreatics.compiler (CompilerPipeline); nothing is hard-coded.
"""
import tkinter as tk
from tkinter import ttk, font as tkfont

from ..compiler.examples import EXAMPLES
from ..compiler.language import (STATEMENT_KEYWORDS, TYPE_KEYWORDS, OPERATORS, DELIMITERS,
                                 GRAMMAR_TEXT, LEXICAL_RULES, SEMANTIC_RULES, KEYWORDS)
from ..compiler.lexer import (Lexer, KEYWORD, IDENTIFIER, INTEGER_LITERAL, STRING_LITERAL,
                              BOOLEAN_LITERAL, OPERATOR, DELIMITER)
from ..compiler.pipeline import CompilerPipeline, PHASE_NAMES, PHASE_SHORT

# ----------------------------------------------------------------- colours
UI = dict(bg="#f3f4f6", panel="#ffffff", header="#1e1b4b", header_fg="#ffffff",
          accent="#4f46e5", accent_dark="#4338ca", text="#111827", muted="#6b7280",
          border="#d1d5db", row_alt="#f9fafb")
ED = dict(bg="#1e1e2e", fg="#cdd6f4", gutter="#181825", gutter_fg="#6c7086", cursor="#f5e0dc",
          select="#45475a", keyword="#cba6f7", type="#89dceb", boolean="#fab387",
          number="#f9e2af", string="#a6e3a1", ident="#89b4fa", operator="#f38ba8",
          bracket="#f5c2e7", delim="#9399b2", errline="#4a2230", errtok="#f38ba8")
STATUS = {  # state -> (background, foreground, label)
    "idle":    ("#e5e7eb", "#4b5563", "not run"),
    "ok":      ("#16a34a", "#ffffff", "passed"),
    "fail":    ("#dc2626", "#ffffff", "failed"),
    "blocked": ("#f59e0b", "#1f2937", "skipped"),
}


# =========================================================== reusable widgets
class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container (used for the grammar panel)."""

    def __init__(self, parent, bg):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=bg)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_wheel, add="+")

    def _on_wheel(self, event):
        w = self.winfo_containing(event.x_root, event.y_root)
        while w is not None and w is not self:       # only scroll when the pointer is over this panel
            w = w.master
        if w is None:
            return
        if event.num == 4:
            step = -2
        elif event.num == 5:
            step = 2
        else:
            step = -1 * (event.delta // 120 or (1 if event.delta > 0 else -1)) * 2
        self.canvas.yview_scroll(step, "units")


class Section(tk.Frame):
    """Collapsible section: a header button that shows / hides a read-only Text."""

    def __init__(self, parent, title, mono, fill_fn, expanded=True):
        super().__init__(parent, bg=UI["bg"])
        self.title, self.expanded = title, expanded
        self._extra = 0
        self.btn = tk.Button(self, anchor="w", relief="flat", bd=0, padx=10, pady=5,
                             bg=UI["accent"], fg="white", activebackground=UI["accent_dark"],
                             activeforeground="white", font=(mono.actual("family"), 10, "bold"),
                             cursor="hand2", command=self.toggle)
        self.btn.pack(fill="x", pady=(6, 0))
        self.text = tk.Text(self, wrap="word", height=3, font=mono, bg=UI["panel"], fg=UI["text"],
                            relief="flat", padx=8, pady=6, bd=0, cursor="arrow", highlightthickness=0)
        self.text.tag_configure("name", foreground="#7c3aed", font=(mono.actual("family"), mono.actual("size"), "bold"))
        self.text.tag_configure("type", foreground="#0e7490", font=(mono.actual("family"), mono.actual("size"), "bold"))
        self.text.tag_configure("dim", foreground=UI["muted"])
        fill_fn(self.text)
        self.text.configure(state="disabled")
        self.text.bind("<Configure>", self._fit)
        self._refresh()

    def _fit(self, _event=None):
        """Make the Text exactly as tall as its content so the whole panel scrolls as one."""
        try:
            n = self.text.count("1.0", "end-1c", "displaylines")
            if not n:
                return
            target = n[0] + self._extra
            if int(self.text.cget("height")) != target:
                self.text.configure(height=target)
            elif self.text.yview()[1] < 0.999:      # still clipped -> add a line
                self._extra += 1
                self.text.configure(height=target + 1)
        except tk.TclError:
            pass

    def toggle(self):
        self.expanded = not self.expanded
        self._refresh()

    def _refresh(self):
        self.btn.configure(text=("▼  " if self.expanded else "▶  ") + self.title)
        if self.expanded:
            self.text.pack(fill="x")
            self.after(20, self._fit)
        else:
            self.text.pack_forget()


# ================================================================ main window
class KreaticsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kreatics Compiler Studio")
        self.geometry(f"{min(1480, self.winfo_screenwidth() - 30)}x{min(900, self.winfo_screenheight() - 70)}+5+5")
        self.minsize(1000, 620)
        self.configure(bg=UI["bg"])
        self.pipeline = CompilerPipeline()
        self._stale = False
        self._hl_job = None

        self._setup_fonts()
        self._setup_style()
        self._build_header()
        self._build_toolbar()
        self._build_status_strip()
        self._build_body()
        self._build_footer()

        self.bind("<F5>", lambda e: self.run_selected())
        self.bind("<F6>", lambda e: self.run_all())
        self.bind("<F7>", lambda e: self.run_program())
        self.example_combo.current(0)
        self.load_example()
        for ms in (200, 600, 1200):
            self.after(ms, self._place_sashes)

    # ------------------------------------------------------------- setup
    def _setup_fonts(self):
        families = set(tkfont.families())
        mono_name = next((f for f in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo",
                                      "Liberation Mono", "Courier New") if f in families), "TkFixedFont")
        ui_name = next((f for f in ("Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial") if f in families),
                       "TkDefaultFont")
        self.mono = tkfont.Font(family=mono_name, size=11)
        self.mono_small = tkfont.Font(family=mono_name, size=10)
        self.ui = tkfont.Font(family=ui_name, size=10)
        self.ui_bold = tkfont.Font(family=ui_name, size=10, weight="bold")
        self.title_font = tkfont.Font(family=ui_name, size=15, weight="bold")

    def _setup_style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", font=self.ui, background=UI["bg"])
        st.configure("TButton", padding=(12, 6), font=self.ui)
        st.configure("Accent.TButton", background=UI["accent"], foreground="white", font=self.ui_bold)
        st.map("Accent.TButton", background=[("active", UI["accent_dark"]), ("pressed", UI["accent_dark"])])
        st.configure("Treeview", rowheight=24, font=self.mono_small, background=UI["panel"],
                     fieldbackground=UI["panel"], bordercolor=UI["border"])
        st.configure("Treeview.Heading", font=self.ui_bold, background="#e0e7ff", foreground=UI["header"])
        st.configure("TNotebook.Tab", padding=(14, 7), font=self.ui_bold)
        st.map("TNotebook.Tab", background=[("selected", UI["accent"])], foreground=[("selected", "white")])
        st.configure("TPanedwindow", background=UI["bg"])

    def _build_header(self):
        bar = tk.Frame(self, bg=UI["header"])
        bar.pack(fill="x")
        tk.Label(bar, text="Kreatics Compiler Studio", bg=UI["header"], fg=UI["header_fg"],
                 font=self.title_font, padx=16, pady=10).pack(side="left")
        tk.Label(bar, text="Lexical  →  Syntax  →  Semantic  →  Intermediate Code", bg=UI["header"],
                 fg="#a5b4fc", font=self.ui, padx=10).pack(side="left")
        tk.Label(bar, text="F7 run program   ·   F5 run selected phase   ·   F6 run all", bg=UI["header"], fg="#a5b4fc",
                 font=self.ui, padx=16).pack(side="right")

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=UI["bg"], pady=8, padx=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Run Program (F7)", style="Accent.TButton",
                   command=self.run_program).pack(side="left", padx=(0, 10))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=(0, 12))
        tk.Label(bar, text="Compiler phase:", bg=UI["bg"], font=self.ui_bold).pack(side="left")
        self.phase_combo = ttk.Combobox(bar, values=PHASE_NAMES, state="readonly", width=30, font=self.ui)
        self.phase_combo.current(0)
        self.phase_combo.pack(side="left", padx=(6, 8))
        ttk.Button(bar, text="Run Selected Phase", style="Accent.TButton",
                   command=self.run_selected).pack(side="left", padx=3)
        ttk.Button(bar, text="Run All Phases", style="Accent.TButton",
                   command=self.run_all).pack(side="left", padx=3)
        ttk.Button(bar, text="Reset Compiler", command=self.reset_compiler).pack(side="left", padx=3)
        self.show_grammar = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Grammar panel", variable=self.show_grammar,
                        command=self._toggle_grammar).pack(side="right", padx=6)

    def _build_status_strip(self):
        strip = tk.Frame(self, bg=UI["bg"], padx=10)
        strip.pack(fill="x", pady=(0, 6))
        tk.Label(strip, text="Pipeline:", bg=UI["bg"], font=self.ui_bold).pack(side="left")
        self.chips = []
        for i, name in enumerate(PHASE_SHORT):
            lbl = tk.Label(strip, font=self.ui_bold, padx=12, pady=4, bd=0)
            lbl.pack(side="left", padx=(8, 0))
            self.chips.append(lbl)
            if i < 3:
                tk.Label(strip, text="→", bg=UI["bg"], fg=UI["muted"], font=self.ui_bold).pack(side="left", padx=(8, 0))
        self.current_label = tk.Label(strip, bg=UI["bg"], fg=UI["text"], font=self.ui_bold, anchor="w")
        self.current_label.pack(side="left", padx=20)
        self._render_chips()
        self._set_current("Current phase: none yet")

    # ------------------------------------------------------------- body
    def _build_body(self):
        self.body = ttk.PanedWindow(self, orient="horizontal")
        self.body.pack(fill="both", expand=True, padx=10)
        self.grammar_panel = self._build_grammar_panel(self.body)
        self.body.add(self.grammar_panel, weight=0)
        self.right = ttk.PanedWindow(self.body, orient="vertical")
        self.body.add(self.right, weight=1)
        self.right.add(self._build_editor(self.right), weight=3)
        self.right.add(self._build_outputs(self.right), weight=3)

    def _place_sashes(self):
        """Give the editor ~45% of the right side and the grammar panel a sensible width.
        Uses real window sizes so it also works on high-DPI Windows screens."""
        try:
            self.update_idletasks()
            h = self.right.winfo_height()
            w = self.body.winfo_width()
            if h > 100:
                self.right.sashpos(0, int(h * 0.45))
            if w > 400 and self.show_grammar.get():
                self.body.sashpos(0, min(int(w * 0.26), 420))
        except tk.TclError:
            pass

    def _toggle_grammar(self):
        if self.show_grammar.get():
            self.body.insert(0, self.grammar_panel, weight=0)
            self.after(50, self._place_sashes)
        else:
            self.body.forget(self.grammar_panel)

    # ---- grammar reference panel
    def _build_grammar_panel(self, parent):
        outer = tk.Frame(parent, bg=UI["bg"], width=360)
        tk.Label(outer, text="Language Grammar Reference", bg=UI["bg"], font=self.ui_bold,
                 anchor="w").pack(fill="x", pady=(0, 2))
        sf = ScrollableFrame(outer, UI["bg"])
        sf.pack(fill="both", expand=True)

        def table(pairs, tag):
            def fill(t):
                for left, right in pairs:
                    t.insert("end", f"{left:<11}", tag)
                    t.insert("end", f"{right}\n")
                t.delete("end-2c", "end-1c")
            return fill

        def lines(items):
            def fill(t):
                t.insert("end", "\n".join(f"• {x}" for x in items))
            return fill

        def plain(text):
            def fill(t):
                t.insert("end", text)
            return fill

        def literals(t):
            rows = [("yes / no", "Boolean literals (true / false)"),
                    ("123", "INTEGER literal (digits)"),
                    ('"text"', "STRING literal (double quotes)"),
                    ("name", "IDENTIFIER (letter or _, then letters / digits / _)")]
            for l, r in rows:
                t.insert("end", f"{l:<11}", "name")
                t.insert("end", f"{r}\n")
            t.delete("end-2c", "end-1c")

        sections = [
            ("Keywords", table(list(STATEMENT_KEYWORDS.items()), "name"), True),
            ("Data types", table(list(TYPE_KEYWORDS.items()), "type"), True),
            ("Operators", table(list(OPERATORS.items()), "name"), True),
            ("Delimiters", table(list(DELIMITERS.items()), "name"), True),
            ("Literals & names", literals, False),
            ("Grammar (productions)", plain(GRAMMAR_TEXT), True),
            ("Lexical rules", lines(LEXICAL_RULES), False),
            ("Semantic rules", lines(SEMANTIC_RULES), False),
            ("Example", plain("hold numb x => 5;\nmaybe (x >? 3) {\n    shout \"big\";\n} otherwise {\n    shout \"small\";\n}"), False),
        ]
        # grammar text is wide -> never wrap it
        for title, fn, expanded in sections:
            sec = Section(sf.inner, title, self.mono_small, fn, expanded)
            if title.startswith("Grammar") or title == "Example":
                sec.text.configure(wrap="none")
            sec.pack(fill="x", padx=(0, 4))
        return outer

    # ---- editor
    def _build_editor(self, parent):
        frame = tk.Frame(parent, bg=UI["bg"])
        head = tk.Frame(frame, bg=UI["bg"])
        head.pack(fill="x")
        tk.Label(head, text="Source Code Editor  (Kreatics)", bg=UI["bg"], font=self.ui_bold).pack(side="left")
        self.cursor_label = tk.Label(head, text="Ln 1, Col 1", bg=UI["bg"], fg=UI["muted"], font=self.ui)
        self.cursor_label.pack(side="right", padx=(8, 0))
        ttk.Button(head, text="Clear Editor", command=self.clear_editor).pack(side="right", padx=3)
        ttk.Button(head, text="Load Example", command=self.load_example).pack(side="right", padx=3)
        self.example_combo = ttk.Combobox(head, values=[e[0] for e in EXAMPLES], state="readonly",
                                          width=40, font=self.ui)
        self.example_combo.pack(side="right", padx=3)

        box = tk.Frame(frame, bg=ED["bg"], highlightthickness=1, highlightbackground=UI["border"])
        box.pack(fill="both", expand=True)
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(1, weight=1)

        self.linenos = tk.Text(box, width=4, font=self.mono, bg=ED["gutter"], fg=ED["gutter_fg"],
                               relief="flat", bd=0, padx=6, pady=6, state="disabled", takefocus=0,
                               cursor="arrow", highlightthickness=0, wrap="none")
        self.linenos.tag_configure("right", justify="right")
        self.code = tk.Text(box, wrap="none", undo=True, font=self.mono, bg=ED["bg"], fg=ED["fg"],
                            insertbackground=ED["cursor"], selectbackground=ED["select"], relief="flat",
                            bd=0, padx=8, pady=6, highlightthickness=0, tabs=("1c",))
        vsb = self.editor_vsb = ttk.Scrollbar(box, orient="vertical", command=self._yview)
        hsb = ttk.Scrollbar(box, orient="horizontal", command=self.code.xview)
        self.code.configure(yscrollcommand=self._on_yscroll, xscrollcommand=hsb.set)
        self.linenos.grid(row=0, column=0, sticky="ns")
        self.code.grid(row=0, column=1, sticky="nsew")
        vsb.grid(row=0, column=2, sticky="ns")
        hsb.grid(row=1, column=1, sticky="ew")

        # syntax-highlight tags (custom language - no other language's rules are used)
        for tag, colour in (("t_keyword", ED["keyword"]), ("t_type", ED["type"]),
                            ("t_boolean", ED["boolean"]), ("t_number", ED["number"]),
                            ("t_string", ED["string"]), ("t_ident", ED["ident"]),
                            ("t_operator", ED["operator"]), ("t_bracket", ED["bracket"]),
                            ("t_delim", ED["delim"])):
            self.code.tag_configure(tag, foreground=colour)
        bold = (self.mono.actual("family"), self.mono.actual("size"), "bold")
        self.code.tag_configure("t_keyword", font=bold)
        self.code.tag_configure("t_type", font=bold)
        self.code.tag_configure("errline", background=ED["errline"])
        self.code.tag_configure("errtok", underline=True, foreground=ED["errtok"])
        self.code.tag_lower("errline")

        self.code.bind("<<Modified>>", self._on_modified)
        self.code.bind("<KeyRelease>", self._update_cursor)
        self.code.bind("<ButtonRelease-1>", self._update_cursor)
        self.code.bind("<Tab>", self._on_tab)
        self.code.bind("<Return>", self._on_return)
        return frame

    def _yview(self, *args):
        self.code.yview(*args)
        self.linenos.yview(*args)

    def _on_yscroll(self, first, last):
        self.editor_vsb.set(first, last)
        self.linenos.yview_moveto(first)

    def _on_tab(self, _e):
        self.code.insert("insert", "    ")
        return "break"

    def _on_return(self, _e):
        line = self.code.get("insert linestart", "insert")
        indent = line[:len(line) - len(line.lstrip(" "))]
        if line.rstrip().endswith("{"):
            indent += "    "
        self.code.insert("insert", "\n" + indent)
        self.code.see("insert")
        return "break"

    def _update_cursor(self, _e=None):
        line, col = self.code.index("insert").split(".")
        self.cursor_label.configure(text=f"Ln {line}, Col {int(col) + 1}")

    def _update_linenos(self):
        n = int(self.code.index("end-1c").split(".")[0])
        self.linenos.configure(state="normal", width=max(3, len(str(n)) + 1))
        self.linenos.delete("1.0", "end")
        self.linenos.insert("1.0", "\n".join(str(i) for i in range(1, n + 1)), "right")
        self.linenos.configure(state="disabled")
        self.linenos.yview_moveto(self.code.yview()[0])

    def _on_modified(self, _e=None):
        if not self.code.edit_modified():
            return
        self.code.edit_modified(False)
        self._update_linenos()
        self._update_cursor()
        if self._hl_job:
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(60, self._highlight)
        self._invalidate_results()

    def _highlight(self):
        """Colour tokens using the real lexer (error markers are kept separate)."""
        self._hl_job = None
        for tag in self.code.tag_names():
            if tag.startswith("t_"):
                self.code.tag_remove(tag, "1.0", "end")
        tokens, _ = Lexer(self.code.get("1.0", "end-1c")).tokenize()
        for t in tokens:
            if t.type == "EOF":
                continue
            if t.type == KEYWORD:
                tag = "t_type" if t.lexeme in TYPE_KEYWORDS else "t_keyword"
            elif t.type == BOOLEAN_LITERAL:
                tag = "t_boolean"
            elif t.type == INTEGER_LITERAL:
                tag = "t_number"
            elif t.type == STRING_LITERAL:
                tag = "t_string"
            elif t.type == IDENTIFIER:
                tag = "t_ident"
            elif t.type == OPERATOR:
                tag = "t_operator"
            elif t.type == DELIMITER:
                tag = "t_delim" if t.lexeme == ";" else "t_bracket"
            else:
                continue
            start = f"{t.line}.{t.column - 1}"
            self.code.tag_add(tag, start, f"{start}+{len(t.lexeme)}c")

    # ---- output tabs
    def _build_outputs(self, parent):
        frame = tk.Frame(parent, bg=UI["bg"])
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)
        self.views = []
        builders = [self._view_lexical, self._view_syntax, self._view_semantic, self._view_icg]
        for i, build in enumerate(builders):
            page = tk.Frame(self.notebook, bg=UI["panel"])
            self.notebook.add(page, text=f"  {i + 1}. {PHASE_NAMES[i]}  ")
            banner = tk.Label(page, anchor="w", padx=12, pady=6, font=self.ui_bold)
            banner.pack(fill="x")
            view = {"banner": banner}
            err_frame = tk.Frame(page, bg=UI["panel"])
            err_frame.pack(side="bottom", fill="x")
            tk.Label(err_frame, text="Errors", bg="#fee2e2", fg="#991b1b", font=self.ui_bold,
                     anchor="w", padx=12).pack(fill="x")
            err = tk.Text(err_frame, height=4, font=self.mono_small, bg="#fffafa", relief="flat",
                          padx=10, pady=4, wrap="word", state="disabled", highlightthickness=0)
            err.tag_configure("pos", foreground="#b91c1c", font=(self.mono_small.actual("family"),
                                                                  self.mono_small.actual("size"), "bold"))
            err.tag_configure("hint", foreground=UI["muted"])
            err.tag_configure("good", foreground="#15803d")
            err.pack(fill="x")
            view["errors"] = err
            build(page, view)
            self.views.append(view)
        self._build_output_tab()
        for i in range(4):
            self._render_phase(i)
        return frame

    def _build_output_tab(self):
        """Fifth tab: the real output of the program (what 'shout' prints)."""
        page = tk.Frame(self.notebook, bg=UI["panel"])
        self.notebook.add(page, text="  ▶ Program Output  ")
        self.out_banner = tk.Label(page, anchor="w", padx=12, pady=6, font=self.ui_bold)
        self.out_banner.pack(fill="x")
        wrap, self.out_text = self._make_text(page, bg="#0f172a")
        self.out_text.configure(fg="#e2e8f0", font=self.mono)
        self.out_text.tag_configure("err", foreground="#fca5a5")
        self.out_text.tag_configure("dim", foreground="#94a3b8")
        wrap.pack(fill="both", expand=True)
        self._reset_output("Press 'Run Program' (F7) to compile and run your code. "
                           "You do not need to open any phase tab.")

    def _reset_output(self, message):
        self.out_banner.configure(text=message, bg="#e5e7eb", fg="#374151")
        self._fill_text(self.out_text, [("", None)])

    def _make_tree(self, parent, columns, widths):
        wrap = tk.Frame(parent, bg=UI["panel"])
        tree = ttk.Treeview(wrap, columns=[c for c, _ in columns], show="headings", selectmode="browse")
        for (cid, title), w in zip(columns, widths):
            tree.heading(cid, text=title)
            tree.column(cid, width=w, anchor="w", stretch=True)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        tree.tag_configure("alt", background=UI["row_alt"])
        return wrap, tree

    def _make_text(self, parent, bg=None):
        wrap = tk.Frame(parent, bg=UI["panel"])
        txt = tk.Text(wrap, font=self.mono, bg=bg or UI["panel"], fg=UI["text"], relief="flat", padx=12,
                      pady=8, wrap="none", state="disabled", highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=txt.yview)
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        txt.pack(side="left", fill="both", expand=True)
        return wrap, txt

    def _view_lexical(self, page, view):
        wrap, tree = self._make_tree(page, [("no", "Token No."), ("lexeme", "Lexeme"), ("type", "Token Type"),
                                            ("line", "Line"), ("col", "Column")], (80, 220, 200, 80, 80))
        wrap.pack(fill="both", expand=True)
        view["tree"] = tree

    def _view_syntax(self, page, view):
        wrap, txt = self._make_text(page)
        wrap.pack(fill="both", expand=True)
        view["text"] = txt

    def _view_semantic(self, page, view):
        wrap, tree = self._make_tree(page, [("name", "Variable"), ("type", "Data Type"), ("scope", "Scope"),
                                            ("line", "Declared at line"), ("col", "Column"),
                                            ("init", "Initial value")], (180, 130, 120, 130, 80, 140))
        wrap.pack(fill="both", expand=True)
        view["tree"] = tree

    def _view_icg(self, page, view):
        summary = tk.Label(page, anchor="w", padx=12, pady=3, bg="#eef2ff", fg=UI["header"], font=self.mono_small)
        summary.pack(side="bottom", fill="x")
        view["summary"] = summary
        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.pack(fill="both", expand=True)
        left_wrap, txt = self._make_text(pane, bg="#fbfbff")
        txt.configure(width=34)
        txt.tag_configure("label", foreground="#b45309", font=(self.mono.actual("family"), self.mono.actual("size"), "bold"))
        txt.tag_configure("num", foreground=UI["muted"])
        right_wrap, tree = self._make_tree(pane, [("no", "No."), ("op", "Operation"), ("a1", "Arg 1"),
                                                  ("a2", "Arg 2"), ("res", "Result")], (50, 80, 90, 80, 80))
        pane.add(left_wrap, weight=1)
        pane.add(right_wrap, weight=1)
        view["text"], view["tree"] = txt, tree

    # ---- footer
    def _build_footer(self):
        self.footer = tk.Label(self, text="Ready.", anchor="w", bg="#e5e7eb", fg=UI["text"], padx=12, pady=4,
                               font=self.ui)
        self.footer.pack(fill="x", side="bottom", pady=(6, 0))

    # =============================================================== actions
    def _source(self):
        return self.code.get("1.0", "end-1c")

    def run_selected(self):
        idx = self.phase_combo.current()
        self.pipeline.run_phase(idx, self._source())
        res = self.pipeline.results[idx]
        if res.status == "ok":
            msg = f"{PHASE_NAMES[idx]} passed - {res.summary}"
        elif res.status == "fail":
            msg = f"{PHASE_NAMES[idx]} FAILED - {res.summary} Later phases cannot run until this is fixed."
        else:
            msg = f"{PHASE_NAMES[idx]} was NOT executed - {PHASE_NAMES[res.blocked_by]} failed. Fix those errors first."
        self._after_run(idx, msg)

    def run_program(self):
        """Compile everything silently, execute the program and show only its output."""
        res = self.pipeline.run_program(self._source())
        self._stale = False
        for i in range(4):
            self._render_phase(i)
        self._render_chips()
        self._mark_errors()
        segs = []
        if res.status == "ok":
            self.out_banner.configure(
                text=f"✔  Program finished - {len(res.output)} line(s) of output.", bg="#dcfce7", fg="#166534")
            segs = [(line + "\n", None) for line in res.output] or [("(the program printed nothing)", "dim")]
            state, msg, colour = "OK", "Program ran successfully. See the Program Output tab.", "#dcfce7"
        elif res.status == "runtime_error":
            self.out_banner.configure(text="✘  Runtime error - the program stopped.", bg="#fee2e2", fg="#991b1b")
            segs = [(line + "\n", None) for line in res.output]
            segs.append(("\n" + res.message, "err"))
            state, msg, colour = "RUNTIME ERROR", res.message, "#fee2e2"
        else:
            self.out_banner.configure(text=f"✘  {res.message}", bg="#fee2e2", fg="#991b1b")
            segs = [("Fix these errors and run again:\n\n", "dim")]
            for e in res.errors:
                segs.append((f"Line {e.line}, Column {e.column}:  {e.message}\n", "err"))
                if e.hint:
                    segs.append((f"      Hint: {e.hint}\n", "dim"))
            state, msg, colour = "COMPILE ERROR", res.message, "#fee2e2"
        self._fill_text(self.out_text, segs)
        self.notebook.select(4)
        self._set_current(f"Program output  ·  {state}")
        self.footer.configure(text=msg, bg=colour)

    def run_all(self):
        res = self.pipeline.run_all(self._source())
        failed = next((r for r in res if r.status == "fail"), None)
        if failed:
            skipped = sum(1 for r in res if r.status == "blocked")
            msg = (f"{PHASE_NAMES[failed.index]} FAILED - {failed.summary} "
                   f"{skipped} later phase(s) were skipped.")
            self._after_run(failed.index, msg)
        else:
            self._after_run(3, "All four phases completed successfully - intermediate code generated.")

    def _after_run(self, shown_tab, message):
        self._stale = False
        for i in range(4):
            self._render_phase(i)
        self._render_chips()
        self._mark_errors()
        self.notebook.select(shown_tab)
        res = self.pipeline.results[shown_tab]
        state = {"ok": "PASSED", "fail": "FAILED", "blocked": "SKIPPED"}[res.status]
        self._set_current(f"Current phase: {PHASE_NAMES[shown_tab]}  ·  {state}")
        self.footer.configure(text=message,
                              bg={"ok": "#dcfce7", "fail": "#fee2e2", "blocked": "#fef3c7"}[res.status])

    def load_example(self):
        title, src = EXAMPLES[self.example_combo.current()][:2]
        self.code.delete("1.0", "end")
        self.code.insert("1.0", src)
        self.code.edit_reset()
        self.footer.configure(text=f"Loaded example: {title}", bg="#e5e7eb")

    def clear_editor(self):
        self.code.delete("1.0", "end")
        self.footer.configure(text="Editor cleared.", bg="#e5e7eb")
        self.code.focus_set()

    def reset_compiler(self):
        """Forget all results and error markers but keep the source code."""
        self.pipeline.reset()
        self._stale = False
        self._reset_output("Press 'Run Program' (F7) to compile and run your code.")
        self._clear_error_marks()
        for i in range(4):
            self._render_phase(i)
        self._render_chips()
        self._set_current("Current phase: none yet")
        self.footer.configure(text="Compiler reset. Source code kept.", bg="#e5e7eb")

    def _invalidate_results(self):
        """Source changed -> every previous result is outdated."""
        had = any(r is not None for r in self.pipeline.results)
        self.pipeline.invalidate()
        if hasattr(self, "out_text"):
            self._reset_output("Source code changed - run the program again.")
        self._clear_error_marks()
        if had:
            self._stale = True
            for i in range(4):
                self._render_phase(i)
            self._render_chips()
            self._set_current("Current phase: none (source changed)")
            self.footer.configure(text="Source code changed - previous results were cleared. Run a phase again.",
                                  bg="#fef3c7")

    # =============================================================== rendering
    def _set_current(self, text):
        self.current_label.configure(text=text)

    def _render_chips(self):
        for i, lbl in enumerate(self.chips):
            r = self.pipeline.results[i]
            state = "idle" if r is None else r.status
            bg, fg, word = STATUS[state]
            lbl.configure(text=f"{i + 1} {PHASE_SHORT[i]}: {word}", bg=bg, fg=fg)

    @staticmethod
    def _fill_text(widget, segments):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for text, tag in segments:
            widget.insert("end", text, tag) if tag else widget.insert("end", text)
        widget.configure(state="disabled")

    def _render_phase(self, i):
        view, res = self.views[i], self.pipeline.results[i]
        banner, err = view["banner"], view["errors"]
        if res is None:
            msg = ("Source code changed - run this phase again." if self._stale
                   else "Not run yet. Choose this phase and press 'Run Selected Phase'.")
            banner.configure(text=msg, bg="#e5e7eb", fg="#374151")
            self._fill_text(err, [("", None)])
            self._clear_view(view)
            return
        if res.status == "blocked":
            banner.configure(text=f"⚠  Skipped - {PHASE_NAMES[res.blocked_by]} failed. Fix its errors first.",
                             bg="#fef3c7", fg="#92400e")
            self._fill_text(err, [("This phase was not executed because a previous phase failed.", "hint")])
            self._clear_view(view)
            return
        if res.status == "ok":
            banner.configure(text=f"✔  {PHASE_NAMES[i]} passed - {res.summary}", bg="#dcfce7", fg="#166534")
            self._fill_text(err, [("No errors.", "good")])
        else:
            banner.configure(text=f"✘  {PHASE_NAMES[i]} failed - {res.summary}", bg="#fee2e2", fg="#991b1b")
            segs = []
            for e in res.errors:
                segs.append((f"Line {e.line}, Column {e.column}:  ", "pos"))
                segs.append((e.message + "\n", None))
                if e.hint:
                    segs.append((f"      Hint: {e.hint}\n", "hint"))
            self._fill_text(err, segs)
        self._clear_view(view)
        [self._draw_lexical, self._draw_syntax, self._draw_semantic, self._draw_icg][i](view, res)

    def _clear_view(self, view):
        if "tree" in view:
            view["tree"].delete(*view["tree"].get_children())
        if "text" in view:
            self._fill_text(view["text"], [("", None)])
        if "summary" in view:
            view["summary"].configure(text="")

    def _draw_lexical(self, view, res):
        for n, t in enumerate(res.data["tokens"], 1):
            view["tree"].insert("", "end", values=(n, t.lexeme, t.type, t.line, t.column),
                                tags=("alt",) if n % 2 == 0 else ())

    def _draw_syntax(self, view, res):
        if res.status == "ok":
            self._fill_text(view["text"], [("Abstract Syntax Tree (AST)\n\n", None), (res.data["ast_text"], None)])
        else:
            self._fill_text(view["text"], [("No syntax tree: the program does not follow the grammar.\n"
                                            "See the errors below.", None)])

    def _draw_semantic(self, view, res):
        for n, s in enumerate(res.data["symbols"]):
            view["tree"].insert("", "end", tags=("alt",) if n % 2 else (),
                                values=(s.name, s.dtype, s.scope, s.line, s.column,
                                        "yes" if s.has_init else "no (default)"))

    def _draw_icg(self, view, res):
        txt = view["text"]
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        n = 0
        for ins in res.data["code"]:
            if ins.is_label:
                txt.insert("end", ins.text() + "\n", "label")
            else:
                n += 1
                txt.insert("end", f"{n:>4}:  ", "num")
                txt.insert("end", ins.text() + "\n")
        txt.configure(state="disabled")
        n = 0
        for ins in res.data["code"]:
            op, a1, a2, r = ins.quad()
            if ins.is_label:
                view["tree"].insert("", "end", values=("", "label", "", "", r), tags=("alt",))
            else:
                n += 1
                view["tree"].insert("", "end", values=(n, op, a1, a2, r))
        temps = ", ".join(f"{t}:{ty}" for t, ty in res.data["temps"]) or "none"
        labels = ", ".join(res.data["labels"]) or "none"
        view["summary"].configure(text=f"Temporaries: {temps}      Labels: {labels}")

    # ---- error markers in the editor
    def _clear_error_marks(self):
        self.code.tag_remove("errline", "1.0", "end")
        self.code.tag_remove("errtok", "1.0", "end")

    def _mark_errors(self):
        self._clear_error_marks()
        for r in self.pipeline.results:
            if r is not None and r.status == "fail":
                for e in r.errors:
                    self.code.tag_add("errline", f"{e.line}.0", f"{e.line}.0 lineend+1c")
                    pos = f"{e.line}.{max(e.column - 1, 0)}"
                    self.code.tag_add("errtok", pos, f"{pos}+1c")
                first = r.errors[0]
                self.code.see(f"{first.line}.0")
                break
        self.code.tag_raise("errtok")
