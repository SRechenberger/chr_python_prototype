import pytest
import ast
from ast_decompiler import decompile
from chr.compiler import Emitter
from chr.ast import *

from pprintast import pprintast as ppast

TEST_PROGRAM = '''
from chr.runtime import \\
    UndefinedConstraintError, \\
    InconsistentBuiltinStoreError, \\
    all_different, \\
    CHRStore, \\
    BuiltInStore


class GCDSolver:

    def __init__(self):
        self.builtin, self.chr = BuiltInStore(), CHRStore()

    def gcd(self, *args):
        if len(args) == 1:
            vars = [
                arg if isinstance(arg, LogicVariable) else self.builtin.fresh(value=arg)
                for arg in args
            ]
            new_constraint = 'gcd/1', *vars
            new_id = self.chr.new()
            self.chr.insert(new_constraint, new_id)
            self.__activate_gcd_1(new_id, *vars)
            return
        raise UndefinedConstraintError('gcd', len(args))

    def __activate_gcd_1(self, id, _0):
        if self.__gcd_1_1(id, _0):
            return
        if self.__gcd_1_2(id, _0):
            return
        if self.__gcd_1_3(id, _0):
            return
        if not _0.is_bound():
            self.builtin.delay(lambda: __activate_gcd_1(id, _0), _0)

    def __gcd_1_0(self, id_0, _0):
        if self.chr.alive(id_0):
            if self.builtin.is_bound(_0) and _0.get_value() == 0:
                if not self.chr.in_history('r1', id_0):
                    self.chr.add_to_history('r1', id_0)
                    self.chr.delete(id_0)
                    return True
        return False

    def __gcd_1_1(self, id_0, _1):
        for id_1, c_1 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
            if self.chr.alive(id_0) and self.chr.alive(id_1) and all_different(id_0, id_1):
                _0 = c_1[1]
                _2 = self.builtin.fresh()
                if (
                    self.builtin.is_bound(_0) and
                    self.builtin.is_bound(_1) and
                    _0.get_value() <= _1.get_value()
                ):
                    if not self.chr.in_history('r2', id_0, id_1):
                        self.chr.add_to_history('r2', id_0, id_1)
                        self.chr.delete(id_0)
                        _local_0 = self.builtin.fresh(value=_0.get_value() - _1.get_value())
                        if not self.builtin.tell_eq(_2, _local_0):
                            self.builtin.set_inconsistent()
                            raise InconsistentBuiltinStoreError()
                        _fresh_id_1 = self.chr.new()
                        _fresh_constr_2 = 'gcd/1', _2
                        self.chr.insert(_fresh_constr_2, _fresh_id_1)
                        self.__activate_gcd_1(_fresh_id_1, _fresh_constr_2)
                        return True
        return False

    def __gcd_1_2(self, id_1, _0):
        for id_0, c_0 in self.chr.get_iterator(symbol='gcd/1', fixed=True):
            if self.chr.alive(id_0) and self.chr.alive(id_1) and all_different(id_0, id_1):
                _1 = c_0[1]
                _2 = self.builtin.fresh()
                if (
                    self.builtin.is_bound(_0) and
                    self.builtin.is_bound(_1) and
                    _0.get_value() <= _1.get_value()
                ):
                    if not self.chr.in_history('r2', id_0, id_1):
                        self.chr.add_to_history('r2', id_0, id_1)
                        self.chr.delete(id_0)
                        _local_0 = self.builtin.fresh(value=_0.get_value() - _1.get_value())
                        if not self.builtin.tell_eq(_2, _local_0):
                            self.builtin.set_inconsistent()
                            raise InconsistentBuiltinStoreError()
                        _fresh_id_1 = self.chr.new()
                        _fresh_constr_2 = 'gcd/1', _2
                        self.chr.insert(_fresh_constr_2, _fresh_id_1)
                        self.__activate_gcd_1(_fresh_id_1, _fresh_constr_2)
                        if not self.chr.alive(id_1):
                            return True
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
    e = Emitter(set(["gcd/1"]))
    result = e.compile_program("GCDSolver", program, ["gcd/1"])
    expected = ast.parse(TEST_PROGRAM)
    print("result:")
    ppast(result)
    print("expected:")
    ppast(expected)
    assert decompile(result) == decompile(expected)
