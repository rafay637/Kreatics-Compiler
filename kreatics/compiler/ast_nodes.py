"""
ast_nodes.py - Abstract Syntax Tree used by phases 2, 3 and 4.

The parser builds it, the semantic analyzer annotates expression nodes with a
`type`, and the intermediate code generator walks the very same tree.
"""


class Node:
    kind = "Node"

    def __init__(self, line=0, column=0):
        self.line = line
        self.column = column
        self.type = None        # filled in by the semantic analyzer (expressions)

    def children(self):
        """List of (edge_label, child_node) pairs, used to print the tree."""
        return []

    def describe(self):
        return self.kind

    def _typed(self, text):
        return f"{text}  : {self.type}" if self.type else text


# ---------------------------------------------------------------- statements
class Program(Node):
    kind = "Program"

    def __init__(self, statements, line=1, column=1):
        super().__init__(line, column)
        self.statements = statements

    def children(self):
        return [("", s) for s in self.statements]


class Block(Node):
    kind = "Block"

    def __init__(self, statements, line, column):
        super().__init__(line, column)
        self.statements = statements

    def children(self):
        return [("", s) for s in self.statements]


class VarDecl(Node):
    kind = "VarDecl"

    def __init__(self, dtype, name, init, line, column):
        super().__init__(line, column)
        self.dtype, self.name, self.init = dtype, name, init

    def children(self):
        return [("init", self.init)] if self.init else []

    def describe(self):
        return f"VarDecl  hold {self.dtype} {self.name}"


class Assign(Node):
    kind = "Assign"

    def __init__(self, name, value, line, column):
        super().__init__(line, column)
        self.name, self.value = name, value

    def children(self):
        return [("value", self.value)]

    def describe(self):
        return f"Assign  {self.name} =>"


class If(Node):
    kind = "If"

    def __init__(self, cond, then_block, else_block, line, column):
        super().__init__(line, column)
        self.cond, self.then_block, self.else_block = cond, then_block, else_block

    def children(self):
        kids = [("condition", self.cond), ("then", self.then_block)]
        if self.else_block:
            kids.append(("otherwise", self.else_block))
        return kids

    def describe(self):
        return "If  (maybe)"


class While(Node):
    kind = "While"

    def __init__(self, cond, body, line, column):
        super().__init__(line, column)
        self.cond, self.body = cond, body

    def children(self):
        return [("condition", self.cond), ("body", self.body)]

    def describe(self):
        return "While  (wheel)"


class For(Node):
    kind = "For"

    def __init__(self, init, cond, update, body, line, column):
        super().__init__(line, column)
        self.init, self.cond, self.update, self.body = init, cond, update, body

    def children(self):
        return [("init", self.init), ("condition", self.cond),
                ("update", self.update), ("body", self.body)]

    def describe(self):
        return "For  (spin)"


class Show(Node):
    kind = "Show"

    def __init__(self, value, line, column):
        super().__init__(line, column)
        self.value = value

    def children(self):
        return [("value", self.value)]

    def describe(self):
        return "Show  (shout)"


class Break(Node):
    kind = "Break"

    def describe(self):
        return "Break  (stop)"


# --------------------------------------------------------------- expressions
class BinaryOp(Node):
    kind = "BinaryOp"

    def __init__(self, op, left, right, line, column):
        super().__init__(line, column)       # position of the operator
        self.op, self.left, self.right = op, left, right

    def children(self):
        return [("left", self.left), ("right", self.right)]

    def describe(self):
        return self._typed(f"BinaryOp  {self.op}")


class IntLiteral(Node):
    kind = "IntLiteral"

    def __init__(self, value, line, column):
        super().__init__(line, column)
        self.value = value

    def describe(self):
        return self._typed(f"Integer  {self.value}")


class StringLiteral(Node):
    kind = "StringLiteral"

    def __init__(self, value, line, column):
        super().__init__(line, column)
        self.value = value

    def describe(self):
        return self._typed(f'String  "{self.value}"')


class BoolLiteral(Node):
    kind = "BoolLiteral"

    def __init__(self, value, line, column):
        super().__init__(line, column)
        self.value = value

    def describe(self):
        return self._typed(f"Boolean  {'yes' if self.value else 'no'}")


class Identifier(Node):
    kind = "Identifier"

    def __init__(self, name, line, column):
        super().__init__(line, column)
        self.name = name

    def describe(self):
        return self._typed(f"Identifier  {self.name}")


def format_tree(root):
    """Return the AST as a readable text tree (├── / └── style)."""
    lines = [root.describe()]

    def walk(node, prefix):
        kids = node.children()
        for i, (label, child) in enumerate(kids):
            last = i == len(kids) - 1
            branch = "└── " if last else "├── "
            text = (label + ": " if label else "") + child.describe()
            lines.append(prefix + branch + text)
            walk(child, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)
