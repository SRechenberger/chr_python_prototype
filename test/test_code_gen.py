import pytest
import ast
from ast_decompiler import decompile
from chr.compiler import Emitter
from chr.ast import *

TEST_PROGRAM = '''
def __gcd_1_0(id_0, _0):
    if self.chr.alive(id_0):
        if self.builtin.is_bound(_0) and _0.get_value() == 0:
            pass
    return False

def __gcd_1_1(id_0, _1):
    for id_1, c_1 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
        if self.chr.alive(id_0) and self.chr.alive(id_1) and all_different(id_0, id_1):
            _0 = c_1[1]
            if (
                self.builtin.is_bound(_0) and
                self.builtin.is_bound(_1) and
                _0.get_value() <= _1.get_value()
            ):
                pass
    return False

def __gcd_1_2(id_1, _0):
    for id_0, c_0 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
        if self.chr.alive(id_0) and self.chr.alive(id_1) and all_different(id_0, id_1):
            _1 = c_0[1]
            if (
                self.builtin.is_bound(_0) and
                self.builtin.is_bound(_1) and
                _0.get_value() <= _1.get_value()
            ):
                pass
    return False
'''

program = Program(rules=[
    Rule(
        name="r1",
        kept_head=[],
        removed_head=[Constraint("gcd", params=["_0"])],
        guard=[
            Constraint("ask_bound", params=[Var("_0")]),
            Constraint("ask_eq", params=[Var("_0"), Const(0)])
        ],
        body=[]
    ),
    Rule(
        name="r2",
        kept_head=[Constraint("gcd", params=["_0"])],
        removed_head=[Constraint("gcd", params=["_1"])],
        guard=[
            Constraint("ask_bound", params=[Var("_0")]),
            Constraint("ask_bound", params=[Var("_1")]),
            Constraint("ask_leq", params=[Var("_0"), Var("_1")])
        ],
        body=[
            Constraint("tell_eq", params=[Var("_2"), Term("-", [Var("_0"), Var("_1")])]),
            Constraint("gcd", params=[Var("_2")])
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
