"""
lexer.py - Phase 1: Lexical Analysis.

Reads the source one character at a time and produces tokens.  Lexical errors
(unknown characters, unterminated strings, bad numbers) are collected with exact
line / column positions and scanning continues so several errors can be shown.
"""
from .errors import CompilerError
from .language import (KEYWORDS, BOOLEAN_LITERALS, TWO_CHAR_OPERATORS, OPERATORS,
                       DELIMITERS)

# Token type names (match the categories in the project brief)
KEYWORD = "KEYWORD"
IDENTIFIER = "IDENTIFIER"
INTEGER_LITERAL = "INTEGER_LITERAL"
STRING_LITERAL = "STRING_LITERAL"
BOOLEAN_LITERAL = "BOOLEAN_LITERAL"
OPERATOR = "OPERATOR"
DELIMITER = "DELIMITER"
EOF = "EOF"


class Token:
    """One lexeme with its type and position (1-based line and column)."""

    def __init__(self, type_, lexeme, line, column, value=None):
        self.type = type_
        self.lexeme = lexeme
        self.line = line
        self.column = column
        self.value = value      # python value for literals (int / str / bool)

    def __repr__(self):
        return f"Token({self.type}, {self.lexeme!r}, {self.line}:{self.column})"


def _is_letter(ch):
    return ch != "" and ch.isascii() and (ch.isalpha() or ch == "_")


def _is_digit(ch):
    return ch != "" and ch.isascii() and ch.isdigit()


class Lexer:
    def __init__(self, source):
        self.src = source
        self.n = len(source)
        self.i = 0              # index into source
        self.line = 1
        self.col = 1
        self.tokens = []
        self.errors = []

    # -- character helpers --------------------------------------------------
    def _peek(self, k=0):
        j = self.i + k
        return self.src[j] if j < self.n else ""

    def _advance(self):
        ch = self.src[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, line, col, message, hint=""):
        self.errors.append(CompilerError("Lexical", line, col, message, hint))

    # -- main loop ----------------------------------------------------------
    def tokenize(self):
        """Return (tokens, errors).  The token list always ends with EOF."""
        while self.i < self.n:
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
                continue
            line, col = self.line, self.col
            if _is_letter(ch):
                self._word(line, col)
            elif _is_digit(ch):
                self._number(line, col)
            elif ch == '"':
                self._string(line, col)
            else:
                self._symbol(line, col)
        self.tokens.append(Token(EOF, "<EOF>", self.line, self.col))
        return self.tokens, self.errors

    # -- token readers --------------------------------------------------------
    def _word(self, line, col):
        """Keyword, boolean literal or identifier."""
        start = self.i
        while _is_letter(self._peek()) or _is_digit(self._peek()):
            self._advance()
        text = self.src[start:self.i]
        if text in KEYWORDS:
            self.tokens.append(Token(KEYWORD, text, line, col))
        elif text in BOOLEAN_LITERALS:
            self.tokens.append(Token(BOOLEAN_LITERAL, text, line, col, BOOLEAN_LITERALS[text]))
        else:
            self.tokens.append(Token(IDENTIFIER, text, line, col))

    def _number(self, line, col):
        start = self.i
        while _is_digit(self._peek()):
            self._advance()
        if _is_letter(self._peek()):                 # something like 12abc
            while _is_letter(self._peek()) or _is_digit(self._peek()):
                self._advance()
            bad = self.src[start:self.i]
            self._error(line, col, f"Invalid token '{bad}': a name cannot start with a digit.",
                        "Names must start with a letter or _ ; numbers contain digits only.")
            return
        text = self.src[start:self.i]
        self.tokens.append(Token(INTEGER_LITERAL, text, line, col, int(text)))

    def _string(self, line, col):
        start = self.i
        self._advance()                               # opening quote
        while self.i < self.n and self._peek() not in ('"', "\n"):
            self._advance()
        if self._peek() == '"':
            self._advance()                           # closing quote
            text = self.src[start:self.i]
            self.tokens.append(Token(STRING_LITERAL, text, line, col, text[1:-1]))
        else:
            self._error(line, col, "Unterminated string literal: the closing \" is missing.",
                        "Close the string with a double quote on the same line.")

    def _symbol(self, line, col):
        ch = self._peek()
        two = ch + self._peek(1)
        # Two-character operators first => '==' is never split into '=' '='.
        if two in TWO_CHAR_OPERATORS:
            self._advance(); self._advance()
            self.tokens.append(Token(OPERATOR, two, line, col))
        elif ch in DELIMITERS:
            self._advance()
            self.tokens.append(Token(DELIMITER, ch, line, col))
        else:
            self._advance()
            self._invalid_char(ch, line, col)

    def _invalid_char(self, ch, line, col):
        hints = {
            "=": "A single '=' is not a Kreatics operator. Use '=>' for assignment or '==' for comparison.",
            "<": "Kreatics uses '<?' for 'less than'.",
            ">": "Kreatics uses '>?' for 'greater than'.",
            "!": "Kreatics has no '!' or '!=' operator.",
            "?": "'?' is only valid as part of '>?' or '<?'.",
            "+": "Kreatics addition is '+.' (with a dot).",
            "-": "Kreatics subtraction is '-.' (with a dot).",
            "*": "Kreatics multiplication is '*.' (with a dot).",
            "/": "Kreatics division is '/.' (with a dot).",
            ".": "A dot is only valid as part of '+.' '-.' '*.' '/.'.",
        }
        shown = ch if ch.isprintable() else f"U+{ord(ch):04X}"
        self._error(line, col, f"Invalid character '{shown}': it is not part of the Kreatics language.",
                    hints.get(ch, "Remove or replace this character."))
