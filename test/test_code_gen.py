import pytest
import ast
from ast_decompiler import decompile
from chr.compiler import Emitter
from chr.ast import *
import chr.runtime as rt

from pprintast import pprintast as ppast

import os

TEST_PROGRAM = '''
from chr.runtime import \\
    UndefinedConstraintError, \\
    InconsistentBuiltinStoreError, \\
    all_different, \\
    LogicVariable, \\
    CHRFalse, \\
    CHRSolver


class GCDSolver(CHRSolver):

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
        if self.__gcd_1_0(id, _0):
            return
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
            if _0.is_bound() and _0.get_value() < 0 and not self.chr.in_history('error', id_0):
                self.builtin.commit()
                self.chr.add_to_history('error', id_0)
                self.chr.delete(id_0)
                _local_0 = self.builtin.fresh(value='Number < Zero')
                raise CHRFalse(_local_0.get_value())
                return True
            else:
                self.builtin.backtrack()
        return False

    def __gcd_1_1(self, id_0, _0):
        if self.chr.alive(id_0):
            if _0.is_bound() and _0.get_value() == 0 and not self.chr.in_history('r1', id_0):
                self.builtin.commit()
                self.chr.add_to_history('r1', id_0)
                self.chr.delete(id_0)
                return True
            else:
                self.builtin.backtrack()
        return False

    def __gcd_1_2(self, id_0, _1):
        for id_1, c_1 in self.chr.get_iterator(symbol='gcd/1', fix=True):
            if self.chr.alive(id_0) and self.chr.alive(id_1) and all_different(id_0, id_1):
                _0 = c_1[1]
                _2 = self.builtin.fresh()
                if (
                    _0.is_bound() and
                    _1.is_bound() and
                    _0.get_value() <= _1.get_value() and
                    not self.chr.in_history('r2', id_0, id_1)
                ):
                    self.builtin.commit()
                    self.chr.add_to_history('r2', id_0, id_1)
                    self.chr.delete(id_0)
                    _local_0 = self.builtin.fresh(value=_1.get_value() - _0.get_value())
                    if not self.builtin.tell_eq(_2, _local_0):
                        self.builtin.set_inconsistent()
                        raise CHRFalse('tell_eq/2', str(_2), str(_local_0))
                    _fresh_id_1 = self.chr.new()
                    _fresh_constr_2 = 'gcd/1', _2
                    self.chr.insert(_fresh_constr_2, _fresh_id_1)
                    self.__activate_gcd_1(_fresh_id_1, _2)
                    return True
                else:
                    self.builtin.backtrack()
        return False

    def __gcd_1_3(self, id_1, _0):
        for id_0, c_0 in self.chr.get_iterator(symbol='gcd/1', fix=True):
            if self.chr.alive(id_1) and self.chr.alive(id_0) and all_different(id_1, id_0):
                _1 = c_0[1]
                _2 = self.builtin.fresh()
                if (
                    _0.is_bound() and
                    _1.is_bound() and
                    _0.get_value() <= _1.get_value() and
                    not self.chr.in_history('r2', id_1, id_0)
                ):
                    self.builtin.commit()
                    self.chr.add_to_history('r2', id_1, id_0)
                    self.chr.delete(id_0)
                    _local_0 = self.builtin.fresh(value=_1.get_value() - _0.get_value())
                    if not self.builtin.tell_eq(_2, _local_0):
                        self.builtin.set_inconsistent()
                        raise CHRFalse('tell_eq/2', str(_2), str(_local_0))
                    _fresh_id_1 = self.chr.new()
                    _fresh_constr_2 = 'gcd/1', _2
                    self.chr.insert(_fresh_constr_2, _fresh_id_1)
                    self.__activate_gcd_1(_fresh_id_1, _2)
                    if not self.chr.alive(id_1):
                        return True
                else:
                    self.builtin.backtrack()
        return False
'''

program_code = '''
constraints gcd/1.

error @ gcd(_0) <=> ask_lt(_0, 0) | false("Number < Zero").
r1 @ gcd(_0) <=> ask_eq(_0, 0) | true.
r2 @ gcd(_0) \\ gcd(_1) <=>
        ask_bound(_0), ask_bound(_1), ask_leq(_0, _1) |
    tell_eq(_2, '-'(_1, _0)), gcd(_2).
'''

program = Program(user_constraints=["gcd/1"], rules=[
    # error @ gcd(_0) <=> _0 < 0 | false.
    Rule(
        name="error",
        kept_head=[],
        removed_head=[Constraint("gcd", params=["_0"])],
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
        removed_head=[Constraint("gcd", params=["_0"])],
        guard=[
            Constraint("ask_bound", params=[Var("_0")]),
            Constraint("ask_eq", params=[Var("_0"), 0])
        ],
        body=[]
    ),
    # r2 @ gcd(_0) \ gcd(_1) <=> _0 <= _1 | _2 = _1 - _0, gcd(_2).
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
            Constraint("tell_eq", params=[Var("_2"), Term("-", [Var("_1"), Var("_0")])]),
            Constraint("gcd", params=[Var("_2")])
        ]
    )
])

program2 = Program(user_constraints=["a/0", "b/0"], rules=[
    # test @ a ==> b.
    Rule(
        name="test",
        kept_head=[Constraint("a")],
        removed_head=[],
        guard=[],
        body=[Constraint("b")]
    )
])

def test_code_gen():
    e = Emitter()
    result = e.compile_program("GCDSolver", program)
    expected = ast.parse(TEST_PROGRAM)
    print("result:")
    ppast(result)
    print("expected:")
    ppast(expected)
    assert decompile(result) == decompile(expected)


    if not os.path.exists('generated'):
        os.mkdir('generated')
    with open('generated/gcd_solver.py', 'w') as f:
        f.write(decompile(result))

    import generated.gcd_solver as s
    solver = s.GCDSolver()
    solver.gcd(200)
    solver.gcd(1239)
    assert ('gcd/1', 1) in solver.chr.constraints.values()

    with pytest.raises(rt.CHRFalse, match="Number < Zero"):
        solver.gcd(-1)


def test_propagation():
    e = Emitter(set(['a/0', 'b/0']))
    result = e.compile_program("PropagationTest", program2)

    if not os.path.exists('generated'):
        os.mkdir('generated')

    with open('generated/propagation_test.py', 'w') as f:
        f.write(decompile(result))

    import generated.propagation_test as p
    solver = p.PropagationTest()
    solver.a()

    assert ('b/0', ) in solver.chr.constraints.values()

    solver = p.PropagationTest()
    solver.b()
    solver.b()

    assert [('b/0', ), ('b/0', )] == list(solver.chr.constraints.values())
