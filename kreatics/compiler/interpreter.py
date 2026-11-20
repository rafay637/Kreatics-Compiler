"""
interpreter.py - runs the generated three-address code and collects what `shout` prints.

This is what makes "Run Program" possible: the program is first compiled through
all four phases, then the TAC is executed instruction by instruction.
"""

STEP_LIMIT = 200000          # protects the app from endless loops (e.g. wheel (yes) { })


def _truncating_div(a, b):
    """Integer division that rounds toward zero (same rule used everywhere in Kreatics)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def run_tac(code, step_limit=STEP_LIMIT):
    """Execute TAC. Returns (output_lines, error_message_or_None)."""
    labels = {ins.result: i for i, ins in enumerate(code) if ins.is_label}
    env, out, pc, steps = {}, [], 0, 0

    def val(a):
        if a in ("yes", "no"):
            return a == "yes"
        if a.startswith('"'):
            return a[1:-1]
        if a.lstrip("-").isdigit():
            return int(a)
        return env[a]

    def show(v):
        return ("yes" if v else "no") if isinstance(v, bool) else str(v)

    ops = {
        "+.": lambda a, b: a + b, "-.": lambda a, b: a - b, "*.": lambda a, b: a * b,
        ">?": lambda a, b: a > b, "<?": lambda a, b: a < b, "==": lambda a, b: a == b,
    }
    while pc < len(code):
        steps += 1
        if steps > step_limit:
            return out, (f"Program stopped: it ran more than {step_limit} instructions. "
                         "It may contain an endless loop (for example wheel (yes) { }).")
        ins = code[pc]
        pc += 1
        if ins.op == "label":
            continue
        if ins.op == "assign":
            env[ins.result] = val(ins.arg1)
        elif ins.op == "print":
            out.append(show(val(ins.arg1)))
        elif ins.op == "goto":
            pc = labels[ins.result]
        elif ins.op == "ifFalse":
            if not val(ins.arg1):
                pc = labels[ins.result]
        elif ins.op == "/.":
            a, b = val(ins.arg1), val(ins.arg2)
            if b == 0:
                return out, "Runtime error: division by zero."
            env[ins.result] = _truncating_div(a, b)
        else:
            env[ins.result] = ops[ins.op](val(ins.arg1), val(ins.arg2))
    return out, None
