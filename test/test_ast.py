from chr.ast import *
import pytest

def test_program_processing():
    program = Program(user_constraints=["gcd/1"], rules=[
        Rule(
            name="r1",
            kept_head=[],
            removed_head=[Constraint("gcd", params=["N"])],
            guard=[Constraint("ask_eq", params=["N", "0"])],
            body=[]
        ),
        Rule(
            name="r2",
            kept_head=[Constraint("gcd", params=["M"])],
            removed_head=[Constraint("gcd", params=["N"])],
            guard=[Constraint("ask_leq", params=["M", "N"])],
            body=[
                Constraint("tell_eq", params=["K", Term("-", ["M", "N"])]),
                Constraint("gcd", params=["K"])
            ]
        )
    ])

    processed = Program(user_constraints=["gcd/1"], rules=[
        ProcessedRule(
            name="r1",
            head=[HeadConstraint("gcd", 0, ["N"], False)],
            guard=[Constraint("ask_eq", params=["N", "0"])],
            body=[]
        ),
        ProcessedRule(
            name="r2",
            head=[
                HeadConstraint("gcd", 1, ["N"], False),
                HeadConstraint("gcd", 2, ["M"], True)
            ],
            guard=[Constraint("ask_leq", params=["M", "N"])],
            body=[
                Constraint("tell_eq", params=["K", Term("-", ["M", "N"])]),
                Constraint("gcd", params=["K"])
            ]
        )
    ])

    result, _ = program.omega_r()

    print(result)

    for rule_result, rule_expected in zip(result.rules, processed.rules):
        assert rule_result == rule_expected
