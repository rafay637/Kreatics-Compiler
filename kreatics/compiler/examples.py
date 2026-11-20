"""
examples.py - demonstration programs for the teacher.

Each entry: (title, source, fails_at, expected_output)
  fails_at = None -> program is fully valid
           = 1/2/3 -> the phase (1 lexical, 2 syntax, 3 semantic) that must fail
  expected_output = what the program prints (used by the automated tests)
"""

EXAMPLES = [
    ("V1  Valid - variables, arithmetic, shout",
     '''hold numb a => 10;
hold numb b => 4;
hold numb sum => a +. b *. 2;
shout sum;
hold characters msg => "Hola, Amigo!";
shout msg;
''', None, ["18", "Hola, Amigo!"]),

    ("V2  Valid - conditional (maybe / otherwise)",
     '''hold numb marks => 72;
hold decision passed => marks >? 50;
maybe (passed) {
    shout "Pass";
} otherwise {
    shout "Fail";
}
''', None, ["Pass"]),

    ("V3  Valid - while loop (wheel) with stop",
     '''hold numb n => 1;
wheel (n <? 10) {
    maybe (n == 5) {
        stop;
    }
    shout n;
    n => n +. 1;
}
''', None, ["1", "2", "3", "4"]),

    ("V4  Valid - for loop (spin)",
     '''hold numb total => 0;
spin (hold numb i => 1; i <? 6; i => i +. 1) {
    total => total +. i;
}
shout total;
''', None, ["15"]),

    ("V5  Valid - nested expressions",
     '''hold numb x => 3;
hold numb y => 4;
hold numb r => ((x +. y) *. (x -. y)) /. 2 +. 10;
hold decision ok => (r >? 0) == (x <? y);
shout r;
shout ok;
''', None, ["7", "yes"]),

    ("V6  Valid - nested blocks and loops",
     '''hold numb limit => 3;
maybe (limit >? 0) {
    spin (hold numb i => 1; i <? limit +. 1; i => i +. 1) {
        hold numb sq => i *. i;
        shout sq;
    }
} otherwise {
    shout "nothing";
}
''', None, ["1", "4", "9"]),

    ("L1  Lexical error - invalid character",
     '''hold numb price => 10 @ 5;
shout price;
''', 1, None),

    ("L2  Lexical error - '=' instead of '=>'",
     '''hold numb a = 5;
shout a;
''', 1, None),

    ("L3  Lexical error - unterminated string",
     '''hold characters name => "Rafay;
shout name;
''', 1, None),

    ("L4  Lexical error - '+' written without the dot",
     '''hold numb a => 4;
hold numb b => a + 2;
shout b;
''', 1, None),

    ("S1  Syntax error - missing semicolon",
     '''hold numb a => 5
shout a;
''', 2, None),

    ("S2  Syntax error - missing closing brace",
     '''hold numb n => 3;
maybe (n >? 1) {
    shout n;
''', 2, None),

    ("S3  Syntax error - missing bracket in condition",
     '''hold numb n => 3;
maybe n >? 1) {
    shout n;
}
''', 2, None),

    ("M1  Semantic error - duplicate declaration",
     '''hold numb a => 1;
hold numb a => 2;
shout a;
''', 3, None),

    ("M2  Semantic error - undeclared variable",
     '''hold numb a => 1;
shout a +. total;
count => 5;
''', 3, None),

    ("M3  Semantic error - assignment type mismatch",
     '''hold numb age => 20;
age => "twenty";
hold characters name => 42;
''', 3, None),

    ("M4  Semantic error - invalid arithmetic",
     '''hold characters s => "abc";
hold numb x => s +. 1;
hold decision d => yes *. 2;
''', 3, None),

    ("M5  Semantic error - non-Boolean conditions",
     '''hold numb n => 5;
maybe (n) {
    shout "never";
}
wheel (n +. 1) {
    stop;
}
''', 3, None),

    ("M6  Semantic error - == with different types",
     '''hold numb n => 5;
hold decision same => n == "five";
''', 3, None),

    ("M7  Semantic error - stop outside a loop",
     '''hold numb n => 5;
stop;
''', 3, None),
]
