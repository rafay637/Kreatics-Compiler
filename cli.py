"""Command-line runner (handy for quick checks):  python cli.py program.kr [phase 1-4]"""
import sys
from kreatics.compiler.pipeline import CompilerPipeline, PHASE_NAMES


def main():
    if len(sys.argv) < 2:
        print("usage: python cli.py <file> [phase 1-4]")
        return
    source = open(sys.argv[1], encoding="utf-8").read()
    phase = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 3
    p = CompilerPipeline()
    p.run_phase(phase, source)
    for r in p.results:
        if r is None:
            continue
        print(f"[{PHASE_NAMES[r.index]}] {r.status.upper()} - {r.summary}")
        for e in r.errors:
            print("   ", e)
    r = p.results[phase]
    if r and r.status == "ok":
        if phase == 0:
            for i, t in enumerate(r.data["tokens"], 1):
                print(f"{i:>3} {t.lexeme!r:<14} {t.type:<16} {t.line}:{t.column}")
        elif phase == 1:
            print(r.data["ast_text"])
        elif phase == 2:
            for s in r.data["symbols"]:
                print(s.name, s.dtype, s.scope, s.line)
        else:
            print(r.data["listing"])


if __name__ == "__main__":
    main()
