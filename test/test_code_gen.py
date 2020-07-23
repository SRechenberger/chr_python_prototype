import pytest
import ast
from ast_decompiler import decompile
from chr.compiler import Emitter
from chr.ast import *

TEST_PROGRAM = '''
def __gcd_1_0(id_0, N):
    pass
    return False
def __gcd_1_1(id_0, N):
    for id_1, c_1 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
        pass
    return False
def __gcd_1_2(id_1, M):
    for id_0, c_0 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
        pass
    return False
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
    print("result:", ast.dump(result))
    print("expected:", ast.dump(expected))
    assert decompile(result) == decompile(expected)
