"""symbol_table.py - scoped symbol table used by the semantic analyzer."""


class Symbol:
    def __init__(self, name, dtype, line, column, scope, has_init):
        self.name = name
        self.dtype = dtype
        self.line = line
        self.column = column
        self.scope = scope          # readable scope label, e.g. "global" or "maybe#1"
        self.has_init = has_init    # declared with an initial value?


class SymbolTable:
    """Stack of scopes.  `all_symbols` keeps every declaration for display."""

    def __init__(self):
        self.scopes = [("global", {})]
        self.all_symbols = []
        self._counters = {}

    def enter_scope(self, kind):
        self._counters[kind] = self._counters.get(kind, 0) + 1
        self.scopes.append((f"{kind}#{self._counters[kind]}", {}))

    def exit_scope(self):
        self.scopes.pop()

    @property
    def current_scope_name(self):
        return self.scopes[-1][0]

    def lookup(self, name):
        """Find a visible symbol (innermost scope first) or None."""
        for _, table in reversed(self.scopes):
            if name in table:
                return table[name]
        return None

    def declare(self, name, dtype, line, column, has_init):
        sym = Symbol(name, dtype, line, column, self.current_scope_name, has_init)
        self.scopes[-1][1][name] = sym
        self.all_symbols.append(sym)
        return sym
