"""errors.py - one error type shared by every compiler phase."""


class CompilerError:
    """A single problem found by a phase, with an exact source position."""

    def __init__(self, phase, line, column, message, hint=""):
        self.phase = phase      # "Lexical", "Syntax" or "Semantic"
        self.line = line        # 1-based
        self.column = column    # 1-based
        self.message = message
        self.hint = hint        # optional "how to fix it" text

    def __str__(self):
        text = f"{self.phase} error at line {self.line}, column {self.column}: {self.message}"
        if self.hint:
            text += f"  (Hint: {self.hint})"
        return text
