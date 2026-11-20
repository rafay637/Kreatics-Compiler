"""
pipeline.py - connects the four phases and enforces the execution rules.

  Source -> Lexical -> Syntax -> Semantic -> Intermediate Code

* Each phase can be run on its own; missing earlier phases are run first.
* A phase is never executed if a prerequisite phase failed (status "blocked").
* Changing the source invalidates every earlier result.
No GUI code here - the GUI only displays what this class produces.
"""
from .ast_nodes import format_tree
from .icg import IntermediateCodeGenerator, format_listing
from .interpreter import run_tac
from .lexer import Lexer
from .parser import parse
from .semantic import SemanticAnalyzer

PHASE_NAMES = ["Lexical Analysis", "Syntax Analysis", "Semantic Analysis",
               "Intermediate Code Generation"]
PHASE_SHORT = ["Lexical", "Syntax", "Semantic", "Intermediate Code"]


class PhaseResult:
    def __init__(self, index, status, errors=None, data=None, blocked_by=None, summary=""):
        self.index = index
        self.status = status            # "ok" | "fail" | "blocked"
        self.errors = errors or []
        self.data = data or {}
        self.blocked_by = blocked_by    # index of the failed prerequisite phase
        self.summary = summary


class ProgramResult:
    """Result of 'Run Program': what the program printed (or why it could not run)."""

    def __init__(self, status, output=None, errors=None, failed_phase=None, message=""):
        self.status = status            # "ok" | "compile_error" | "runtime_error"
        self.output = output or []      # lines printed by shout
        self.errors = errors or []      # compile errors (when status == "compile_error")
        self.failed_phase = failed_phase
        self.message = message


class CompilerPipeline:
    def __init__(self):
        self.reset()

    def reset(self):
        self.source = None
        self.results = [None] * 4

    def invalidate(self):
        self.results = [None] * 4

    # ------------------------------------------------------------ running
    def _set_source(self, source):
        if source != self.source:
            self.source = source
            self.invalidate()

    def run_phase(self, index, source):
        """Run one phase (running un-run prerequisites first)."""
        self._set_source(source)
        for k in range(index):
            if self.results[k] is None:
                self.results[k] = self._execute(k)
            if self.results[k].status != "ok":
                self.results[index] = PhaseResult(
                    index, "blocked", blocked_by=k,
                    summary=f"Not executed: {PHASE_NAMES[k]} failed.")
                for j in range(index + 1, 4):
                    self.results[j] = None
                return self.results[index]
        self.results[index] = self._execute(index)
        for j in range(index + 1, 4):            # later results are now outdated
            self.results[j] = None
        return self.results[index]

    def run_all(self, source):
        """Run the four phases in order, stopping at the first failure."""
        self._set_source(source)
        self.invalidate()
        for k in range(4):
            self.results[k] = self._execute(k)
            if self.results[k].status != "ok":
                for j in range(k + 1, 4):
                    self.results[j] = PhaseResult(
                        j, "blocked", blocked_by=k,
                        summary=f"Not executed: {PHASE_NAMES[k]} failed.")
                break
        return self.results

    def run_program(self, source):
        """Compile through all four phases, then execute the TAC and return the output."""
        results = self.run_all(source)
        for r in results:
            if r.status == "fail":
                return ProgramResult("compile_error", errors=r.errors, failed_phase=r.index,
                                     message=f"{PHASE_NAMES[r.index]} failed, so the program was not run.")
        out, err = run_tac(results[3].data["code"])
        if err:
            return ProgramResult("runtime_error", output=out, message=err)
        return ProgramResult("ok", output=out)

    # ------------------------------------------------------------ the phases
    def _execute(self, k):
        return [self._lexical, self._syntax, self._semantic, self._icg][k]()

    def _lexical(self):
        tokens, errors = Lexer(self.source).tokenize()
        if errors:
            return PhaseResult(0, "fail", errors, {"tokens": tokens},
                               summary=f"{len(errors)} lexical error(s) found.")
        return PhaseResult(0, "ok", [], {"tokens": tokens},
                           summary=f"{len(tokens)} tokens generated (including EOF).")

    def _syntax(self):
        tokens = self.results[0].data["tokens"]
        ast, errors = parse(tokens)
        if errors:
            return PhaseResult(1, "fail", errors, {},
                               summary=f"{len(errors)} syntax error(s) found.")
        return PhaseResult(1, "ok", [], {"ast": ast, "ast_text": format_tree(ast)},
                           summary="Syntax is valid: the program follows the Kreatics grammar.")

    def _semantic(self):
        ast = self.results[1].data["ast"]
        table, errors = SemanticAnalyzer().analyze(ast)
        data = {"symbols": table.all_symbols}
        if errors:
            return PhaseResult(2, "fail", errors, data,
                               summary=f"{len(errors)} semantic error(s) found.")
        return PhaseResult(2, "ok", [], data,
                           summary=f"Semantically valid: {len(table.all_symbols)} symbol(s) declared, all types consistent.")

    def _icg(self):
        ast = self.results[1].data["ast"]          # same AST, annotated by phase 3
        code, temps, labels = IntermediateCodeGenerator().generate(ast)
        real = sum(1 for i in code if not i.is_label)
        data = {"code": code, "temps": temps, "labels": labels, "listing": format_listing(code)}
        return PhaseResult(3, "ok", [], data,
                           summary=f"{real} instruction(s), {len(temps)} temporary variable(s), {len(labels)} label(s).")
