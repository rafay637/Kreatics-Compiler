"""Test helper: run TAC with the project's interpreter and return only the printed lines."""
from kreatics.compiler.interpreter import run_tac as _run


def run_tac(code, step_limit=10000):
    out, err = _run(code, step_limit)
    assert err is None, err
    return out
