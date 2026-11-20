"""
icg.py - Phase 4: Intermediate Code Generation (three-address code).

Walks the *validated, type-annotated* AST and emits real TAC instructions:

    t1 = a + b          binary operation into a temporary
    x = t1              assignment / copy
    ifFalse t2 goto L1  conditional jump
    goto L2             unconditional jump
    L1:                 label
    print x             output (shout)
"""
from .language import INT_T, STR_T, BOOL_T


class Instr:
    """One three-address instruction (op, arg1, arg2, result)."""

    def __init__(self, op, arg1="", arg2="", result=""):
        self.op, self.arg1, self.arg2, self.result = op, arg1, arg2, result

    @property
    def is_label(self):
        return self.op == "label"

    def text(self):
        if self.op == "label":
            return f"{self.result}:"
        if self.op == "assign":
            return f"{self.result} = {self.arg1}"
        if self.op == "goto":
            return f"goto {self.result}"
        if self.op == "ifFalse":
            return f"ifFalse {self.arg1} goto {self.result}"
        if self.op == "print":
            return f"print {self.arg1}"
        return f"{self.result} = {self.arg1} {self.op} {self.arg2}"

    def quad(self):
        """(operation, arg1, arg2, result) for the quadruple table."""
        op = {"assign": "="}.get(self.op, self.op)
        return op, self.arg1, self.arg2, self.result


class IntermediateCodeGenerator:
    DEFAULTS = {INT_T: "0", STR_T: '""', BOOL_T: "no"}

    def __init__(self):
        self.code = []
        self.temps = []             # [(name, type)]
        self.labels = []
        self.break_targets = []     # stack of loop-exit labels for 'stop'

    # ------------------------------------------------------------- helpers
    def new_temp(self, type_):
        name = f"t{len(self.temps) + 1}"
        self.temps.append((name, type_ or ""))
        return name

    def new_label(self):
        name = f"L{len(self.labels) + 1}"
        self.labels.append(name)
        return name

    def emit(self, op, arg1="", arg2="", result=""):
        self.code.append(Instr(op, arg1, arg2, result))

    def label(self, name):
        self.emit("label", result=name)

    # ------------------------------------------------------------- entry
    def generate(self, program):
        for s in program.statements:
            self.stmt(s)
        return self.code, self.temps, self.labels

    def stmt(self, node):
        getattr(self, "gen_" + type(node).__name__)(node)

    # ------------------------------------------------------------- statements
    def gen_VarDecl(self, node):
        value = self.expr(node.init) if node.init else self.DEFAULTS[node.dtype]
        self.emit("assign", value, result=node.name)

    def gen_Assign(self, node):
        self.emit("assign", self.expr(node.value), result=node.name)

    def gen_Show(self, node):
        self.emit("print", self.expr(node.value))

    def gen_Break(self, node):
        self.emit("goto", result=self.break_targets[-1])

    def gen_Block(self, node):
        for s in node.statements:
            self.stmt(s)

    def gen_If(self, node):
        cond = self.expr(node.cond)
        l_else = self.new_label()
        self.emit("ifFalse", cond, result=l_else)
        self.gen_Block(node.then_block)
        if node.else_block:
            l_end = self.new_label()
            self.emit("goto", result=l_end)
            self.label(l_else)
            self.gen_Block(node.else_block)
            self.label(l_end)
        else:
            self.label(l_else)

    def gen_While(self, node):
        l_start, l_end = self.new_label(), self.new_label()
        self.label(l_start)
        cond = self.expr(node.cond)
        self.emit("ifFalse", cond, result=l_end)
        self.break_targets.append(l_end)
        self.gen_Block(node.body)
        self.break_targets.pop()
        self.emit("goto", result=l_start)
        self.label(l_end)

    def gen_For(self, node):
        self.stmt(node.init)
        l_start, l_end = self.new_label(), self.new_label()
        self.label(l_start)
        cond = self.expr(node.cond)
        self.emit("ifFalse", cond, result=l_end)
        self.break_targets.append(l_end)
        self.gen_Block(node.body)
        self.break_targets.pop()
        self.stmt(node.update)
        self.emit("goto", result=l_start)
        self.label(l_end)

    # ------------------------------------------------------------- expressions
    def expr(self, node):
        """Generate code for an expression and return the operand holding its value."""
        return getattr(self, "ex_" + type(node).__name__)(node)

    def ex_IntLiteral(self, node):
        return str(node.value)

    def ex_StringLiteral(self, node):
        return f'"{node.value}"'

    def ex_BoolLiteral(self, node):
        return "yes" if node.value else "no"

    def ex_Identifier(self, node):
        return node.name

    def ex_BinaryOp(self, node):
        left = self.expr(node.left)
        right = self.expr(node.right)
        temp = self.new_temp(node.type)
        self.emit(node.op, left, right, temp)
        return temp


def format_listing(code):
    """Numbered TAC text.  Labels are shown on their own line without a number."""
    lines, n = [], 0
    for ins in code:
        if ins.is_label:
            lines.append(f"{ins.text()}")
        else:
            n += 1
            lines.append(f"{n:>4}:   {ins.text()}")
    return "\n".join(lines)
