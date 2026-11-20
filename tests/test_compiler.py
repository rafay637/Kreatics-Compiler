"""Automated tests: run with   python -m unittest discover -s tests -v   (from the project folder)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kreatics.compiler.examples import EXAMPLES
from kreatics.compiler.lexer import Lexer
from kreatics.compiler.pipeline import CompilerPipeline
from tac_interpreter import run_tac


def compile_all(src):
    p = CompilerPipeline()
    return p, p.run_all(src)


class ExampleProgramTests(unittest.TestCase):
    """Every demo program must fail exactly where it is supposed to."""

    def test_examples(self):
        for title, src, fails_at, expected in EXAMPLES:
            with self.subTest(title):
                _, res = compile_all(src)
                statuses = [r.status for r in res]
                if fails_at is None:
                    self.assertEqual(statuses, ["ok"] * 4)
                    self.assertEqual(run_tac(res[3].data["code"]), expected)
                else:
                    k = fails_at - 1
                    self.assertEqual(statuses[:k], ["ok"] * k)
                    self.assertEqual(statuses[k], "fail")
                    self.assertTrue(all(s == "blocked" for s in statuses[k + 1:]))
                    self.assertTrue(res[k].errors)


class LexerTests(unittest.TestCase):
    def kinds(self, src):
        toks, errs = Lexer(src).tokenize()
        return [(t.type, t.lexeme) for t in toks], errs

    def test_double_equals_before_single(self):
        toks, errs = self.kinds("a == b")
        self.assertEqual(toks[1], ("OPERATOR", "=="))
        self.assertFalse(errs)

    def test_arrow_assignment_and_relational(self):
        toks, errs = self.kinds("x => y >? 1 <? 2")
        self.assertEqual([t[1] for t in toks[:-1]], ["x", "=>", "y", ">?", "1", "<?", "2"])

    def test_lone_equals_is_error(self):
        _, errs = self.kinds("a = 1")
        self.assertEqual((errs[0].line, errs[0].column), (1, 3))

    def test_positions_and_eof(self):
        toks, _ = Lexer("hold\n  numb").tokenize()
        self.assertEqual((toks[1].line, toks[1].column), (2, 3))
        self.assertEqual(toks[-1].type, "EOF")

    def test_literals(self):
        toks, _ = self.kinds('yes no 42 "hi"')
        self.assertEqual([t[0] for t in toks],
                         ["BOOLEAN_LITERAL", "BOOLEAN_LITERAL", "INTEGER_LITERAL", "STRING_LITERAL", "EOF"])

    def test_multiple_errors(self):
        _, errs = self.kinds("a @ b # c")
        self.assertEqual(len(errs), 2)

    def test_dot_arithmetic_operators(self):
        toks, errs = self.kinds("a +. b -. c *. d /. e")
        self.assertEqual([t[1] for t in toks if t[0] == "OPERATOR"], ["+.", "-.", "*.", "/."])
        self.assertFalse(errs)

    def test_plain_arithmetic_symbols_are_invalid(self):
        _, errs = self.kinds("a + b")
        self.assertEqual(len(errs), 1)
        self.assertIn("+.", errs[0].hint)

    def test_digit_start_name(self):
        _, errs = self.kinds("12abc")
        self.assertEqual(len(errs), 1)


class ErrorPositionTests(unittest.TestCase):
    def first_error(self, src, phase):
        _, res = compile_all(src)
        return res[phase].errors

    def test_missing_semicolon_position(self):
        errs = self.first_error("hold numb a => 5\nshout a;", 1)
        self.assertEqual((errs[0].line, errs[0].column), (1, 17))   # right after '5'
        self.assertIn("Missing ';'", errs[0].message)

    def test_missing_brace_mentions_open_line(self):
        errs = self.first_error("maybe (yes) {\n shout 1;\n", 1)
        self.assertIn("line 1", errs[0].message)

    def test_stray_closing_brace(self):
        errs = self.first_error("shout 1; }", 1)
        self.assertIn("Unexpected '}'", errs[0].message)

    def test_two_missing_semicolons_both_reported(self):
        errs = self.first_error("hold numb a => 1\nhold numb b => 2\nshout a;", 1)
        self.assertEqual(len(errs), 2)

    def test_duplicate_declaration(self):
        errs = self.first_error("hold numb a => 1;\nhold numb a => 2;", 2)
        self.assertEqual(errs[0].line, 2)
        self.assertIn("Duplicate", errs[0].message)

    def test_undeclared_reports_each_use(self):
        errs = self.first_error("shout a;\nb => 1;", 2)
        self.assertEqual([e.line for e in errs], [1, 2])

    def test_type_mismatch_text(self):
        errs = self.first_error('hold numb a => 1;\na => "x";', 2)
        self.assertIn("characters", errs[0].message)
        self.assertIn("numb", errs[0].message)

    def test_division_by_zero(self):
        errs = self.first_error("hold numb a => 4 /. 0;", 2)
        self.assertIn("Division by zero", errs[0].message)

    def test_scope_rules(self):
        # sibling blocks may reuse a name; a name visible from outside may not be re-declared
        ok = "maybe (yes) { hold numb t => 1; } otherwise { hold numb t => 2; }"
        self.assertEqual(compile_all(ok)[1][2].status, "ok")
        bad = "hold numb t => 1; maybe (yes) { hold numb t => 2; }"
        self.assertEqual(compile_all(bad)[1][2].status, "fail")
        out = "maybe (yes) { hold numb t => 1; } shout t;"
        self.assertEqual(compile_all(out)[1][2].status, "fail")


class PipelineRuleTests(unittest.TestCase):
    def test_blocked_when_prerequisite_fails(self):
        p = CompilerPipeline()
        r = p.run_phase(3, "hold numb a = 1;")        # lexical error
        self.assertEqual(r.status, "blocked")
        self.assertEqual(r.blocked_by, 0)
        self.assertEqual(p.results[0].status, "fail")

    def test_phases_run_independently(self):
        p = CompilerPipeline()
        p.run_phase(0, "hold numb a => 1;")
        self.assertIsNone(p.results[1])
        p.run_phase(2, "hold numb a => 1;")           # auto-runs syntax first
        self.assertEqual(p.results[1].status, "ok")

    def test_source_change_invalidates(self):
        p = CompilerPipeline()
        p.run_all("shout 1;")
        p.run_phase(0, "shout 2;")
        self.assertIsNone(p.results[1])

    def test_empty_program(self):
        _, res = compile_all("")
        self.assertEqual([r.status for r in res], ["ok"] * 4)


class RunProgramTests(unittest.TestCase):
    def test_output_without_opening_phases(self):
        r = CompilerPipeline().run_program('hold numb a => 6;\nshout a *. 7;\nshout "done";')
        self.assertEqual((r.status, r.output), ("ok", ["42", "done"]))

    def test_compile_error_reported(self):
        r = CompilerPipeline().run_program("shout x;")
        self.assertEqual((r.status, r.failed_phase), ("compile_error", 2))

    def test_runtime_division_by_zero(self):
        r = CompilerPipeline().run_program("hold numb z => 0;\nshout 1;\nshout 5 /. z;")
        self.assertEqual(r.status, "runtime_error")
        self.assertEqual(r.output, ["1"])

    def test_endless_loop_is_stopped(self):
        r = CompilerPipeline().run_program("wheel (yes) { }")
        self.assertEqual(r.status, "runtime_error")

    def test_negative_division_truncates(self):
        r = CompilerPipeline().run_program("shout (0 -. 7) /. 2;")
        self.assertEqual(r.output, ["-3"])


class IntermediateCodeTests(unittest.TestCase):
    def test_not_just_source(self):
        _, res = compile_all("hold numb a => 1 +. 2 *. 3;")
        lines = [i.text() for i in res[3].data["code"]]
        self.assertEqual(lines, ["t1 = 2 *. 3", "t2 = 1 +. t1", "a = t2"])

    def test_if_else_jumps(self):
        _, res = compile_all('maybe (1 <? 2) { shout 1; } otherwise { shout 2; }')
        lines = [i.text() for i in res[3].data["code"]]
        self.assertEqual(lines, ["t1 = 1 <? 2", "ifFalse t1 goto L1", "print 1",
                                 "goto L2", "L1:", "print 2", "L2:"])

    def test_loop_labels(self):
        _, res = compile_all("hold numb i => 0; wheel (i <? 3) { i => i +. 1; }")
        lines = [i.text() for i in res[3].data["code"]]
        self.assertIn("L1:", lines)
        self.assertIn("goto L1", lines)
        self.assertIn("ifFalse t1 goto L2", lines)

    def test_nested_break_targets_inner_loop(self):
        src = """hold numb i => 0;
        wheel (i <? 2) {
            wheel (yes) { stop; }
            shout i;
            i => i +. 1;
        }"""
        _, res = compile_all(src)
        self.assertEqual(run_tac(res[3].data["code"]), ["0", "1"])

    def test_division_truncates(self):
        _, res = compile_all("shout 7 /. 2;")
        self.assertEqual(run_tac(res[3].data["code"]), ["3"])


if __name__ == "__main__":
    unittest.main()
