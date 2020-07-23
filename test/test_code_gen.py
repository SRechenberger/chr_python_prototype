import pytest
import ast
from ast_decompiler import decompile
from chr.compiler import Emitter
from chr.ast import *

TEST_PROGRAM = '''
def __gcd_1_0(id_0, N): pass
def __gcd_1_1(id_0, N): pass
def __gcd_1_2(id_1, M): pass
'''

program = Program(rules=[
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

def test_code_gen():
    e = Emitter()
    result = e.compile_program(program, ["gcd/1"])
    expected = ast.parse(TEST_PROGRAM)
    print(ast.dump(result))
    print(ast.dump(expected))
    assert decompile(result) == decompile(expected)
