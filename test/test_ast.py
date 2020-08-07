from chr.ast import *


def test_program_processing():
    program = Program(class_name="GCDSolver", user_constraints=["gcd/1"], rules=[
        Rule(
            name="r1",
            kept_head=[],
            removed_head=[Term("gcd", params=[Var("N")])],
            guard=[Term("ask_eq", params=[Var("N"), "0"])],
            body=[]
        ),
        Rule(
            name="r2",
            kept_head=[Term("gcd", params=[Var("M")])],
            removed_head=[Term("gcd", params=[Var("N")])],
            guard=[Term("ask_leq", params=[Var("M"), Var("N")])],
            body=[
                Term("tell_eq", params=[Var("K"), Term("-", [Var("M"), Var("N")])]),
                Term("gcd", params=[Var("K")])
            ]
        )
    ])

    processed = Program(class_name="GCDSolver", user_constraints=["gcd/1"], rules=[
        ProcessedRule(
            name="r1",
            head=[HeadConstraint("gcd", 0, ["N"], False)],
            matching=[],
            guard=[Term("ask_eq", params=[Var("N"), "0"])],
            body=[]
        ),
        ProcessedRule(
            name="r2",
            head=[
                HeadConstraint("gcd", 1, ["N"], False),
                HeadConstraint("gcd", 2, ["M"], True)
            ],
            matching=[],
            guard=[Term("ask_leq", params=[Var("M"), Var("N")])],
            body=[
                Term("tell_eq", params=[Var("K"), Term("-", [Var("M"), Var("N")])]),
                Term("gcd", params=[Var("K")])
            ]
        )
    ])

    result = program.get_normal_form().omega_r()

    print(result)

    for rule_result, rule_expected in zip(result.rules, processed.rules):
        assert rule_result == rule_expected
