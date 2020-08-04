from chr.parser import *


def test_term():
    test_cases = [
        ("$A", Var("A")),
        ("$_1", Var("_1")),
        ("123", 123),
        ("a", Term("a")),
        ("b(1,2)", Term("b", params=[1, 2])),
        ("c(\"blub\", $A)", Term("c", params=["blub", Var("A")])),
        ("a_longer_name", Term("a_longer_name")),
        ("c1", Term("c1")),
        ("'*'(1,2)", Term("*", params=[1, 2])),
        ("[]", []),
        ("[1,]", [1]),
        ("[1, \"blub\", $A]", [1, "blub", Var("A")]),
        ("{1 : 2}", dict([(1, 2)])),
        ("{3 : $A}", dict([(3, Var("A"))])),
        ("(1,2,3)", (1, 2, 3)),
        ("(1,2)", (1, 2)),
        ("(1,)", (1,)),
        ("(1,2,3, [1,2,3])", (1, 2, 3, [1, 2, 3])),
        ("1 + 2", Term("+", params=[1, 2])),
        ("1 + 2 == 3 * 4", Term("==",
                                params=[Term("+", params=[1, 2]), Term("*", params=[3, 4])])
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
        ("gcd($N)", Term("gcd", params=[Var("N")])),
        ("gcd(0)", Term("gcd", params=[0])),
        ("gcd(minus($M,$N))", Term(
            "gcd",
            params=[Term("minus", params=[Var("M"), Var("N")])]
        )),
        ("triple(($X,$Y,$Z))", Term("triple", params=[
            (Var("X"), Var("Y"), Var("Z"))
        ])),
        ("$X = 1", Term("=", params=[Var("X"), 1])),
        ("0 == 1", Term("==", params=[0, 1])),
        ("0 <= 1", Term("<=", params=[0, 1]))
    ]

    for input, expected_output in test_cases:
        assert parse_term.parse(input) == expected_output


def test_constraints():
    test_cases = [
        ("c1", [Term("c1")]),
        ("c1, c2, c3", [Term(f'c{i}') for i in range(1, 4)])
    ]
    for input, expected_output in test_cases:
        print("input", input, "expected", expected_output)
        result = parse_constraints.parse(input)
        print("result", result)
        assert result == expected_output


def test_simpagation():
    test_cases = [
        ("k \\ r <=> b", ([Term("k")], [Term("r")], None, [Term("b")]))
    ]
    for input_string, expected_output in test_cases:
        assert parse_simpagation.parse(input_string) == expected_output


def test_guard_body():
    test_cases = [
        ("g1, g2, g3 | c1", ([
                                 Term("g1"),
                                 Term("g2"),
                                 Term("g3")
                             ], [
                                 Term("c1")
                             ])),
        ("b1, b2", (None, [Term("b1"), Term("b2")]))
    ]

    for input_string, expected_output in test_cases:
        print("input", input_string, "expected", expected_output)
        assert parse_body.parse(input_string) == expected_output


program_code = '''constraints gcd/1.

error @ gcd($_0) <=> ask_bound($_0), $_0 < 0 | false("Number < Zero").
r1 @ gcd(0) <=> true.
r2 @ gcd($_0) \\ gcd($_1) <=>
        ask_bound($_0), ask_bound($_1), $_0 <= $_1 |
    $_2 = $_1 - $_0, gcd($_2).
'''

program = Program(user_constraints=["gcd/1"], rules=[
    # error @ gcd(_0) <=> _0 < 0 | false.
    Rule(
        name="error",
        kept_head=[],
        removed_head=[Term("gcd", params=[Var("_0")])],
        guard=[
            Term("ask_bound", params=[Var("_0")]),
            Term("<", params=[Var("_0"), 0])
        ],
        body=[
            Term("false", params=["Number < Zero"])
        ]
    ),
    # r1 @ gcd(_0) <=> _0 == 0 | true.
    Rule(
        name="r1",
        kept_head=[],
        removed_head=[Term("gcd", params=[0])],
        guard=[],
        body=[Term("true")]
    ),
    # r2 @ gcd(_0) \ gcd(_1) <=> _0 <= _1 | _2 = _1 - _0, gcd(_2).
    Rule(
        name="r2",
        kept_head=[Term("gcd", params=[Var("_0")])],
        removed_head=[Term("gcd", params=[Var("_1")])],
        guard=[
            Term("ask_bound", params=[Var("_0")]),
            Term("ask_bound", params=[Var("_1")]),
            Term("<=", params=[Var("_0"), Var("_1")])
        ],
        body=[
            Term("=", params=[Var("_2"), Term("-", [Var("_1"), Var("_0")])]),
            Term("gcd", params=[Var("_2")])
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
