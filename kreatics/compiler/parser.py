"""
parser.py - Phase 2: Syntax Analysis (recursive descent, one function per rule).

Grammar (see language.GRAMMAR_TEXT):
    Program -> StmtList EOF
    Statement -> Declaration | Assignment | Conditional | WhileLoop | ForLoop | Output | Break
    Expr -> RelExpr -> AddExpr -> Term -> Factor

Error strategy
  * A missing ';' is a *soft* error: it is recorded at the end of the previous
    token and parsing continues, so several missing semicolons are all reported.
  * Any other problem is a *hard* error: it is recorded and parsing stops, which
    avoids a flood of misleading follow-up errors.
"""
from .ast_nodes import (Program, Block, VarDecl, Assign, If, While, For, Show, Break,
                        BinaryOp, IntLiteral, StringLiteral, BoolLiteral, Identifier)
from .errors import CompilerError
from .language import TYPE_KEYWORDS, REL_OPS
from .lexer import (KEYWORD, IDENTIFIER, INTEGER_LITERAL, STRING_LITERAL,
                    BOOLEAN_LITERAL, OPERATOR, EOF)


class ParseError(Exception):
    """Raised for a hard syntax error; carries the CompilerError."""

    def __init__(self, error):
        super().__init__(error.message)
        self.error = error


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errors = []

    # ------------------------------------------------------------ utilities
    @property
    def tok(self):
        return self.tokens[self.pos]

    def advance(self):
        t = self.tokens[self.pos]
        if t.type != EOF:
            self.pos += 1
        return t

    def check(self, lexeme):
        """Is the current token exactly this keyword / operator / delimiter?"""
        return self.tok.type != EOF and self.tok.lexeme == lexeme and \
            self.tok.type not in (IDENTIFIER, STRING_LITERAL, INTEGER_LITERAL, BOOLEAN_LITERAL)

    @staticmethod
    def _desc(tok):
        if tok.type == EOF:
            return "the end of the file"
        if tok.type == STRING_LITERAL:
            return f"the string {tok.lexeme}"
        return f"'{tok.lexeme}'"

    def _fail(self, message, hint="", tok=None):
        tok = tok or self.tok
        raise ParseError(CompilerError("Syntax", tok.line, tok.column, message, hint))

    def expect(self, lexeme, context, hint=""):
        """Consume `lexeme` or raise a hard error mentioning `context`."""
        if self.check(lexeme):
            return self.advance()
        self._fail(f"Expected '{lexeme}' {context} but found {self._desc(self.tok)}.", hint)

    def expect_semicolon(self, what):
        """Soft error: report the missing ';' right after the previous token."""
        if self.check(";"):
            self.advance()
            return
        prev = self.tokens[self.pos - 1] if self.pos > 0 else self.tok
        self.errors.append(CompilerError(
            "Syntax", prev.line, prev.column + len(prev.lexeme),
            f"Missing ';' at the end of {what}.",
            f"Add ';' right after '{prev.lexeme}'. Every declaration, assignment and shout must end with ';'."))

    # ------------------------------------------------------------ entry point
    def parse(self):
        """Return (Program or None, errors)."""
        try:
            stmts = self.parse_statement_list(in_block=False)
            if self.tok.type != EOF:                       # defensive; should not happen
                self._fail(f"Unexpected {self._desc(self.tok)}.")
            program = Program(stmts)
        except ParseError as e:
            self.errors.append(e.error)
            program = None
        if self.errors:
            return None, self.errors
        return program, []

    # ------------------------------------------------------------ statements
    def parse_statement_list(self, in_block):
        stmts = []
        while self.tok.type != EOF:
            if in_block and self.check("}"):
                break
            stmts.append(self.parse_statement())
        return stmts

    def parse_block(self, context):
        open_tok = self.expect("{", f"to start the block {context}",
                               "Blocks are written as { ... }.")
        stmts = self.parse_statement_list(in_block=True)
        if not self.check("}"):
            self._fail(f"Missing '}}': the block opened at line {open_tok.line}, "
                       f"column {open_tok.column} is never closed.",
                       "Add a closing '}' for every opening '{'.")
        self.advance()
        return Block(stmts, open_tok.line, open_tok.column)

    def parse_statement(self):
        t = self.tok
        if t.type == KEYWORD:
            if t.lexeme == "hold":
                return self.parse_declaration()
            if t.lexeme == "shout":
                return self.parse_show()
            if t.lexeme == "maybe":
                return self.parse_if()
            if t.lexeme == "wheel":
                return self.parse_while()
            if t.lexeme == "spin":
                return self.parse_for()
            if t.lexeme == "stop":
                self.advance()
                self.expect_semicolon("'stop'")
                return Break(t.line, t.column)
            if t.lexeme == "otherwise":
                self._fail("'otherwise' has no matching 'maybe' before it.",
                           "'otherwise' must directly follow the closing '}' of a 'maybe' block.")
            if t.lexeme in TYPE_KEYWORDS:
                self._fail(f"A declaration must start with 'hold' before the type '{t.lexeme}'.",
                           f"Example: hold {t.lexeme} x => ...;")
        if t.type == IDENTIFIER:
            node = self.parse_assignment_core()
            self.expect_semicolon("the assignment")
            return node
        if self.check("}"):
            self._fail("Unexpected '}': there is no matching '{'.",
                       "Remove this '}' or add the missing '{'.")
        self._fail(f"Expected a statement (hold, shout, maybe, wheel, spin, stop or a variable name) "
                   f"but found {self._desc(t)}.")

    # -- declaration / assignment ------------------------------------------
    def parse_declaration_core(self):
        """hold Type ID [ => Expr ]  (without the ';')"""
        self.expect("hold", "to start a declaration")
        if not (self.tok.type == KEYWORD and self.tok.lexeme in TYPE_KEYWORDS):
            self._fail(f"Expected a data type (numb, characters or decision) after 'hold' "
                       f"but found {self._desc(self.tok)}.")
        dtype = self.advance().lexeme
        if self.tok.type != IDENTIFIER:
            self._fail(f"Expected a variable name after '{dtype}' but found {self._desc(self.tok)}.",
                       "Example: hold numb age => 20;")
        name_tok = self.advance()
        init = None
        if self.check("=>"):
            self.advance()
            init = self.parse_expression()
        return VarDecl(dtype, name_tok.lexeme, init, name_tok.line, name_tok.column)

    def parse_declaration(self):
        node = self.parse_declaration_core()
        self.expect_semicolon("the declaration")
        return node

    def parse_assignment_core(self):
        """ID => Expr  (without the ';')"""
        name_tok = self.advance()
        if not self.check("=>"):
            self._fail(f"Expected '=>' after '{name_tok.lexeme}' (assignment) but found {self._desc(self.tok)}.",
                       f"Assignments look like: {name_tok.lexeme} => 5;")
        self.advance()
        value = self.parse_expression()
        return Assign(name_tok.lexeme, value, name_tok.line, name_tok.column)

    # -- output ------------------------------------------------------------------
    def parse_show(self):
        kw = self.advance()
        value = self.parse_expression()
        self.expect_semicolon("the 'shout' statement")
        return Show(value, kw.line, kw.column)

    # -- conditional / loops -----------------------------------------------------
    def parse_condition(self, keyword):
        self.expect("(", f"after '{keyword}'", f"Write the condition in brackets: {keyword} (condition) {{ ... }}")
        cond = self.parse_expression()
        self.expect(")", f"to close the condition of '{keyword}'")
        return cond

    def parse_if(self):
        kw = self.advance()
        cond = self.parse_condition("maybe")
        then_block = self.parse_block("after the 'maybe' condition")
        else_block = None
        if self.check("otherwise"):
            self.advance()
            else_block = self.parse_block("after 'otherwise'")
        return If(cond, then_block, else_block, kw.line, kw.column)

    def parse_while(self):
        kw = self.advance()
        cond = self.parse_condition("wheel")
        body = self.parse_block("after the 'wheel' condition")
        return While(cond, body, kw.line, kw.column)

    def parse_for(self):
        kw = self.advance()
        self.expect("(", "after 'spin'", "Format: spin (hold numb i => 0; i <? 5; i => i + 1) { ... }")
        if self.check("hold"):
            init = self.parse_declaration_core()
        elif self.tok.type == IDENTIFIER:
            init = self.parse_assignment_core()
        else:
            self._fail(f"Expected a loop initialiser (e.g. hold numb i => 0) but found {self._desc(self.tok)}.")
        self.expect(";", "after the spin initialiser")
        cond = self.parse_expression()
        self.expect(";", "after the spin condition")
        if self.tok.type != IDENTIFIER:
            self._fail(f"Expected a loop update (e.g. i => i + 1) but found {self._desc(self.tok)}.")
        update = self.parse_assignment_core()
        self.expect(")", "to close the spin header")
        body = self.parse_block("after the 'spin' header")
        return For(init, cond, update, body, kw.line, kw.column)

    # ------------------------------------------------------------ expressions
    def parse_expression(self):
        return self.parse_relational()

    def parse_relational(self):
        left = self.parse_additive()
        while self.tok.type == OPERATOR and self.tok.lexeme in REL_OPS:
            op = self.advance()
            right = self.parse_additive()
            left = BinaryOp(op.lexeme, left, right, op.line, op.column)
        return left

    def parse_additive(self):
        left = self.parse_term()
        while self.tok.type == OPERATOR and self.tok.lexeme in ("+.", "-."):
            op = self.advance()
            right = self.parse_term()
            left = BinaryOp(op.lexeme, left, right, op.line, op.column)
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.tok.type == OPERATOR and self.tok.lexeme in ("*.", "/."):
            op = self.advance()
            right = self.parse_factor()
            left = BinaryOp(op.lexeme, left, right, op.line, op.column)
        return left

    def parse_factor(self):
        t = self.tok
        if t.type == INTEGER_LITERAL:
            self.advance()
            return IntLiteral(t.value, t.line, t.column)
        if t.type == STRING_LITERAL:
            self.advance()
            return StringLiteral(t.value, t.line, t.column)
        if t.type == BOOLEAN_LITERAL:
            self.advance()
            return BoolLiteral(t.value, t.line, t.column)
        if t.type == IDENTIFIER:
            self.advance()
            return Identifier(t.lexeme, t.line, t.column)
        if self.check("("):
            self.advance()
            inner = self.parse_expression()
            self.expect(")", "to close the bracketed expression")
            return inner
        self._fail(f"Expected an expression (number, string, yes/no, variable or '(') "
                   f"but found {self._desc(t)}.")


def parse(tokens):
    """Convenience wrapper: returns (Program or None, errors)."""
    return Parser(tokens).parse()
