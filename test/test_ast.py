from chr.ast import *


def test_program_processing():
    program = Program(user_constraints=["gcd/1"], rules=[
        Rule(
            name="r1",
            kept_head=[],
            removed_head=[Constraint("gcd", params=[Var("N")])],
            guard=[Constraint("ask_eq", params=[Var("N"), "0"])],
            body=[]
        ),
        Rule(
            name="r2",
            kept_head=[Constraint("gcd", params=[Var("M")])],
            removed_head=[Constraint("gcd", params=[Var("N")])],
            guard=[Constraint("ask_leq", params=[Var("M"), Var("N")])],
            body=[
                Constraint("tell_eq", params=[Var("K"), Term("-", [Var("M"), Var("N")])]),
                Constraint("gcd", params=[Var("K")])
            ]
        )
    ])

    processed = Program(user_constraints=["gcd/1"], rules=[
        ProcessedRule(
            name="r1",
            head=[HeadConstraint("gcd", 0, ["N"], False)],
            matching=[],
            guard=[Constraint("ask_eq", params=[Var("N"), "0"])],
            body=[]
        ),
        ProcessedRule(
            name="r2",
            head=[
                HeadConstraint("gcd", 1, ["N"], False),
                HeadConstraint("gcd", 2, ["M"], True)
            ],
            matching=[],
            guard=[Constraint("ask_leq", params=[Var("M"), Var("N")])],
            body=[
                Constraint("tell_eq", params=[Var("K"), Term("-", [Var("M"), Var("N")])]),
                Constraint("gcd", params=[Var("K")])
            ]
        )
    ])

    result, _ = program.get_normal_form().omega_r()

    print(result)

    for rule_result, rule_expected in zip(result.rules, processed.rules):
        assert rule_result == rule_expected
