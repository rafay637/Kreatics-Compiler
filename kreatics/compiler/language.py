"""
language.py - the single source of truth for the Kreatics language.

Everything that describes the language (keywords, types, operators, delimiters,
grammar text) lives here.  The lexer, parser, semantic analyzer, GUI grammar
panel and the editor's syntax highlighter all read from this file, so the
language is never defined in two places.
"""

# --- Data types -----------------------------------------------------------
INT_T = "numb"          # integer
STR_T = "characters"    # string
BOOL_T = "decision"     # boolean

TYPE_KEYWORDS = {
    INT_T:  "Integer (whole numbers)",
    STR_T:  "String (text)",
    BOOL_T: "Boolean (yes / no)",
}

# --- Statement keywords (from the Assignment 1 sheet) ----------------------
STATEMENT_KEYWORDS = {
    "hold":      "Variable declaration",
    "shout":     "Print / output",
    "maybe":     "If condition",
    "otherwise": "Else condition",
    "spin":      "Loop (for)",
    "wheel":     "Loop (while)",
    "stop":      "Loop break",
}

KEYWORDS = {**STATEMENT_KEYWORDS, **TYPE_KEYWORDS}

# Boolean literals
BOOLEAN_LITERALS = {"yes": True, "no": False}

# --- Operators ---------------------------------------------------------------
OPERATORS = {
    "=>": "Assignment",
    "+.": "Addition",
    "-.": "Subtraction",
    "*.": "Multiplication",
    "/.": "Division",
    ">?": "Greater than",
    "<?": "Less than",
    "==": "Equal comparison",
}
TWO_CHAR_OPERATORS = {"=>", "==", ">?", "<?", "+.", "-.", "*.", "/."}   # always matched BEFORE single chars
ARITH_OPS = {"+.", "-.", "*.", "/."}
ORDER_OPS = {">?", "<?"}
EQUALITY_OPS = {"=="}
REL_OPS = ORDER_OPS | EQUALITY_OPS

# --- Delimiters --------------------------------------------------------------
DELIMITERS = {
    ";": "Ends a statement",
    "{": "Starts a block",
    "}": "Ends a block",
    "(": "Opens a condition",
    ")": "Closes a condition",
}

# --- Grammar (shown in the GUI, implemented by parser.py) -------------------------
GRAMMAR_TEXT = """\
Program     → StmtList EOF
StmtList    → { Statement }
Block       → { StmtList }

Statement   → Declaration
            | Assignment
            | Conditional
            | WhileLoop
            | ForLoop
            | Output
            | Break

Declaration → hold Type ID [ => Expr ] ;
Assignment  → ID => Expr ;
Conditional → maybe ( Expr ) Block
              [ otherwise Block ]
WhileLoop   → wheel ( Expr ) Block
ForLoop     → spin ( ForInit ; Expr ;
                     ForStep ) Block
ForInit     → hold Type ID => Expr
            | ID => Expr
ForStep     → ID => Expr
Output      → shout Expr ;
Break       → stop ;
Type        → numb | characters | decision

Expr        → RelExpr
RelExpr     → AddExpr { RelOp AddExpr }
RelOp       → >? | <? | ==
AddExpr     → Term { ( +. | -. ) Term }
Term        → Factor { ( *. | /. ) Factor }
Factor      → INTEGER | STRING | yes | no
            | ID | ( Expr )"""

LEXICAL_RULES = [
    "Source is read character by character.",
    "ID: letter or _ followed by letters, digits, _",
    "INTEGER: one or more digits",
    "STRING: text between double quotes on one line",
    "Two-character operators (=> == >? <? +. -. *. /.) are matched before single characters, so == is never read as two = signs.",
    "Anything else is a lexical error (reported with line and column).",
    "Every token list ends with an EOF token.",
]

SEMANTIC_RULES = [
    "Declare a variable before using it.",
    "No duplicate declarations (a name that is already visible cannot be declared again).",
    "Assigned / initial value type must match the variable type.",
    "+. -. *. /. and >? <? need numb operands.",
    "== needs both operands of the same type.",
    "Conditions of maybe, wheel and spin must be decision (Boolean).",
    "stop is only allowed inside wheel or spin.",
    "Division (/.) by the literal 0 is rejected.",
]
