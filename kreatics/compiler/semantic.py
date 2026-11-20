"""
semantic.py - Phase 3: Semantic Analysis.

Walks the AST with a scoped symbol table, checks the language's type rules and
annotates every expression node with its type (`node.type`) for phase 4.
All errors are collected (not just the first one).
"""
from .ast_nodes import (VarDecl, Assign, If, While, For, Show, Break, Block, BinaryOp,
                        IntLiteral, StringLiteral, BoolLiteral, Identifier)
from .errors import CompilerError
from .language import INT_T, STR_T, BOOL_T, ARITH_OPS, ORDER_OPS, EQUALITY_OPS
from .symbol_table import SymbolTable


class SemanticAnalyzer:
    def __init__(self):
        self.table = SymbolTable()
        self.errors = []
        self.loop_depth = 0

    def _error(self, node, message, hint=""):
        self.errors.append(CompilerError("Semantic", node.line, node.column, message, hint))

    # ----------------------------------------------------------- entry point
    def analyze(self, program):
        for stmt in program.statements:
            self.visit(stmt)
        return self.table, self.errors

    def visit(self, node):
        getattr(self, "visit_" + type(node).__name__)(node)

    def _body(self, block, scope_kind):
        """Visit a block's statements inside a new scope."""
        self.table.enter_scope(scope_kind)
        for s in block.statements:
            self.visit(s)
        self.table.exit_scope()

    # ----------------------------------------------------------- statements
    def visit_VarDecl(self, node):
        init_type = self.expr(node.init) if node.init else None   # init is checked BEFORE the name exists
        existing = self.table.lookup(node.name)
        if existing:
            self._error(node, f"Duplicate declaration: variable '{node.name}' is already declared "
                              f"as {existing.dtype} at line {existing.line} (scope {existing.scope}).",
                        "Use a different name, or assign to the existing variable instead.")
        else:
            self.table.declare(node.name, node.dtype, node.line, node.column, node.init is not None)
        if init_type and init_type != node.dtype:
            self._error(node, f"Type mismatch: cannot initialise '{node.name}' (type {node.dtype}) "
                              f"with a value of type {init_type}.",
                        f"The value must be of type {node.dtype}.")

    def visit_Assign(self, node):
        value_type = self.expr(node.value)
        sym = self.table.lookup(node.name)
        if sym is None:
            self._error(node, f"Undeclared variable '{node.name}': it is assigned before being declared.",
                        f"Declare it first, e.g. hold {value_type or 'numb'} {node.name} => ...;")
        elif value_type and value_type != sym.dtype:
            self._error(node, f"Type mismatch: cannot assign a value of type {value_type} "
                              f"to variable '{node.name}' of type {sym.dtype}.",
                        f"'{node.name}' only accepts {sym.dtype} values.")

    def _check_condition(self, cond, keyword):
        t = self.expr(cond)
        if t and t != BOOL_T:
            self._error(cond, f"The condition of '{keyword}' must be a decision (Boolean) "
                              f"but this expression has type {t}.",
                        "Use a comparison such as x >? 5, or a decision variable / yes / no.")

    def visit_If(self, node):
        self._check_condition(node.cond, "maybe")
        self._body(node.then_block, "maybe")
        if node.else_block:
            self._body(node.else_block, "otherwise")

    def visit_While(self, node):
        self._check_condition(node.cond, "wheel")
        self.loop_depth += 1
        self._body(node.body, "wheel")
        self.loop_depth -= 1

    def visit_For(self, node):
        self.table.enter_scope("spin")           # loop variable lives in the spin scope
        self.visit(node.init)
        self._check_condition(node.cond, "spin")
        self.visit(node.update)
        self.loop_depth += 1
        for s in node.body.statements:
            self.visit(s)
        self.loop_depth -= 1
        self.table.exit_scope()

    def visit_Show(self, node):
        self.expr(node.value)

    def visit_Break(self, node):
        if self.loop_depth == 0:
            self._error(node, "'stop' can only be used inside a 'wheel' or 'spin' loop.",
                        "Move 'stop' into a loop body.")

    def visit_Block(self, node):
        self._body(node, "block")

    # ----------------------------------------------------------- expressions
    def expr(self, node):
        """Return the type of an expression (or None if it contains an error)."""
        node.type = getattr(self, "type_" + type(node).__name__)(node)
        return node.type

    def type_IntLiteral(self, node):
        return INT_T

    def type_StringLiteral(self, node):
        return STR_T

    def type_BoolLiteral(self, node):
        return BOOL_T

    def type_Identifier(self, node):
        sym = self.table.lookup(node.name)
        if sym is None:
            self._error(node, f"Undeclared variable '{node.name}': it is used before being declared.",
                        f"Declare it first, e.g. hold numb {node.name} => 0;")
            return None
        return sym.dtype

    def type_BinaryOp(self, node):
        lt, rt = self.expr(node.left), self.expr(node.right)
        op = node.op
        if lt is None or rt is None:             # an operand already failed; avoid duplicate noise
            return BOOL_T if op in ORDER_OPS | EQUALITY_OPS else (INT_T if op in ARITH_OPS else None)
        if op in ARITH_OPS or op in ORDER_OPS:
            if lt != INT_T or rt != INT_T:
                kind = "Arithmetic" if op in ARITH_OPS else "Comparison"
                self._error(node, f"{kind} operator '{op}' needs two numb (integer) operands, "
                                  f"but got {lt} and {rt}.",
                            "Only numb values can be used with +. -. *. /. >? <?.")
            if op == "/." and isinstance(node.right, IntLiteral) and node.right.value == 0:
                self._error(node, "Division by zero: the right operand of '/.' is the literal 0.",
                            "Divide by a non-zero value.")
            return INT_T if op in ARITH_OPS else BOOL_T
        # equality
        if lt != rt:
            self._error(node, f"Operator '==' needs both operands to have the same type, "
                              f"but got {lt} and {rt}.",
                        "Compare numb with numb, characters with characters, decision with decision.")
        return BOOL_T
