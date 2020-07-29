import pytest
from chr.parser import *

from pprintast import pprintast as ppast

def test_term():
    test_cases = [
        ("$A", Var("A")),
        ("$_1", Var("_1")),
        ("123", 123),
        ("a", Term("a")),
        ("b(1,2)", Term("b", params=[1,2])),
        ("c(\"blub\", $A)", Term("c", params=["blub", Var("A")])),
        ("a_longer_name", Term("a_longer_name")),
        ("c1", Term("c1")),
        ("'*'(1,2)", Term("*", params=[1, 2])),
        ("[]", []),
        ("[1,]", [1]),
        ("[1, \"blub\", $A]", [1, "blub", Var("A")]),
        ("{1 : 2}", dict([(1, 2)])),
        ("{3 : $A}", dict([(3, Var("A"))])),
        ("(1,2,3)", (1,2,3)),
        ("(1,2)", (1,2)),
        ("(1,)", (1,)),
        ("(1,2,3, [1,2,3])", (1,2,3, [1,2,3])),
        ("1 + 2", Term("+", params=[1,2])),
        ("1 + 2 == 3 * 4", Term("==",
            params=[Term("+", params=[1,2]), Term("*", params=[3,4])])
        ),
        ("1 == 3 + 4 and False", Term("and",
            params=[Term("==", params=[
                1,
                Term("+", params=[3, 4])
            ]), False]
        ))
    ]

    for input, expected_output in test_cases:
        print("input", input, "expected", expected_output)
        result = parse_term.parse(input)
        print("result", result)
        assert result == expected_output

def test_constraint():
    test_cases = [
        ("gcd($N)", Constraint("gcd", params=[Var("N")])),
        ("gcd(0)", Constraint("gcd", params=[0])),
        ("gcd(minus($M,$N))", Constraint(
            "gcd",
            params=[Term("minus", params=[Var("M"), Var("N")])]
        )),
        ("triple(($X,$Y,$Z))", Constraint("triple", params=[
            (Var("X"), Var("Y"), Var("Z"))
        ])),
        ("$X =! 1", Constraint("tell_eq", params=[Var("X"), 1])),
        ("0 =? 1", Constraint("ask_eq", params=[0, 1])),
        ("0 <=? 1", Constraint("ask_leq", params=[0, 1]))
    ]

    for input, expected_output in test_cases:
        assert parse_constraint.parse(input) == expected_output

def test_constraints():
    test_cases = [
        ("c1", [Constraint("c1")]),
        ("c1, c2, c3", [Constraint(f'c{i}') for i in range(1,4)])
    ]
    for input, expected_output in test_cases:
        print("input", input, "expected", expected_output)
        result = parse_constraints.parse(input)
        print("result", result)
        assert result == expected_output

def test_simpagation():
    test_cases = [
        ("k \\ r <=> b", ([Constraint("k")], [Constraint("r")], None, [Constraint("b")]))
    ]
    for input, expected_output in test_cases:
        assert parse_simpagation.parse(input) == expected_output

def test_guard_body():
    test_cases = [
        ("g1, g2, g3 | c1", ([
            Constraint("g1"),
            Constraint("g2"),
            Constraint("g3")
        ], [
            Constraint("c1")
        ])),
        ("b1, b2", (None, [Constraint("b1"), Constraint("b2")]))
    ]

    for input, expected_output in test_cases:
        print("input", input, "expected", expected_output)
        assert parse_body.parse(input) == expected_output


program_code = '''constraints gcd/1.

error @ gcd($_0) <=> ask_bound($_0), ask_lt($_0, 0) | false("Number < Zero").
r1 @ gcd(0) <=> true.
r2 @ gcd($_0) \\ gcd($_1) <=>
        ask_bound($_0), ask_bound($_1), $_0 <=? $_1 |
    $_2 =! $_1 - $_0, gcd($_2).
'''

program = Program(user_constraints=["gcd/1"], rules=[
    # error @ gcd(_0) <=> _0 < 0 | false.
    Rule(
        name="error",
        kept_head=[],
        removed_head=[Constraint("gcd", params=[Var("_0")])],
        guard=[
            Constraint("ask_bound", params=[Var("_0")]),
            Constraint("ask_lt", params=[Var("_0"), 0])
        ],
        body=[
            Constraint("false", params=["Number < Zero"])
        ]
    ),
    # r1 @ gcd(_0) <=> _0 == 0 | true.
    Rule(
        name="r1",
        kept_head=[],
        removed_head=[Constraint("gcd", params=[0])],
        guard=[],
        body=[Constraint("true")]
    ),
    # r2 @ gcd(_0) \ gcd(_1) <=> _0 <= _1 | _2 = _1 - _0, gcd(_2).
    Rule(
        name="r2",
        kept_head=[Constraint("gcd", params=[Var("_0")])],
        removed_head=[Constraint("gcd", params=[Var("_1")])],
        guard=[
            Constraint("ask_bound", params=[Var("_0")]),
            Constraint("ask_bound", params=[Var("_1")]),
            Constraint("ask_leq", params=[Var("_0"), Var("_1")])
        ],
        body=[
            Constraint("tell_eq", params=[Var("_2"), Term("-", [Var("_1"), Var("_0")])]),
            Constraint("gcd", params=[Var("_2")])
        ]
    )
])

def test_parse_program():
    result = parse_program().parse(program_code)
    print("result:\n", result)
    print("expected:\n", program)
    assert result == program
    print("result:\n", result.get_normal_form())
    print("expected:\n", result.get_normal_form())
    assert result.get_normal_form() == program.get_normal_form()
