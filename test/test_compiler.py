import pytest

from chr.runtime import CHRFalse
from random import sample
from math import inf


def test_sum_solver():
    from test_files.sum_solver import SumSolver

    solver = SumSolver()
    solver.sum(0)
    assert len(solver.chr.dump()) == 0

    solver.sum(1)
    assert len(solver.chr.dump()) == 1

    solver.sum(1)
    assert len(solver.chr.dump()) == 1
    assert ("sum/1", 2) in solver.chr.dump()

    v = solver.builtin.fresh()
    solver.read(v)
    assert len(solver.chr.dump()) == 1
    assert ("read/1", 2) not in solver.chr.dump()
    assert v == 2


def test_triple_solver():
    from test_files.triple import TripleSolver

    solver = TripleSolver()
    solver.triple((1, 2, 3))

    assert len(solver.chr.dump()) == 4

    solver = TripleSolver()
    solver.triple({1: "A", 2: "B", "scheiss": "C"})

    assert len(solver.chr.dump()) == 3

    solver = TripleSolver()
    solver.triple([1, 2, 3])

    assert len(solver.chr.dump()) == 2
    assert ("single/1", 5) in solver.chr.dump()


def test_eq_solver():
    from test_files.eq_solver import EqSolver

    solver = EqSolver()
    a = solver.fresh_var("a")
    b = solver.fresh_var("b")
    c = solver.fresh_var("c")

    solver.eq(a, b)
    solver.eq(c, b)

    dump = solver.dump_chr_store()
    print(dump)
    assert len(dump) == 0

    solver.eq(a, 1)
    assert b == 1
    assert c == 1


def test_guard_tell():
    from test_files.guard_tell import GuardTellTest

    solver = GuardTellTest()

    a = solver.fresh_var()

    solver.test(a)

    assert not a.is_bound()


def test_error_message():
    from test_files.error_message import ErrorTest

    solver = ErrorTest()

    message = "this is an error message!"

    with pytest.raises(CHRFalse, match=message):
        solver.error(message)


def test_leq_solver():
    from test_files.leq_solver import LeqSolver

    solver = LeqSolver()

    assert len(solver.dump_chr_store()) == 0

    x = solver.fresh_var("X")
    y = solver.fresh_var("Y")
    z = solver.fresh_var("Z")

    # x <= y, z <= y, x <= z
    solver.leq(x, y)
    solver.leq(z, y)
    solver.leq(x, z)

    dump = solver.dump_chr_store()
    assert len(dump) == 3

    solver.leq(z, x)
    dump = solver.dump_chr_store()
    print(dump)
    assert len(dump) == 1
    assert ('leq/2', x, y) in dump
    assert ('leq/2', z, y) in dump


def test_fibonacci():
    from test_files.fibonacci import Fibonacci

    def fib(n, r1=1, r0=0):
        if n == 0:
            return r0
        if n == 1:
            return r1
        return fib(n - 1, r1 + r0, r1)

    solver = Fibonacci()

    for n in range(1, 15):
        solver.fib(n)
        r = solver.fresh_var()
        solver.read(r)
        assert r == fib(n)


def test_match():
    from test_files.match_solver import MatchTest

    solver = MatchTest()

    x, y = solver.fresh_var(), solver.fresh_var()
    solver.match(x)
    solver.match(y)

    assert x != y
    assert len(solver.dump_chr_store()) == 2


def test_gcd():
    from test_files.gcd_solver import GCDSolver


    solver = GCDSolver()

    x = solver.fresh_var()

    solver.gcd(0)
    assert len(solver.dump_chr_store()) == 0

    solver.gcd(100)
    solver.gcd(66)

    dump = solver.dump_chr_store()
    assert len(dump) == 1
    assert ("gcd/1", 2) in dump
    solver.gcd(x)
    dump = solver.dump_chr_store()
    assert len(dump) == 2
    solver.builtin.tell_eq(x, 3)
    solver.builtin.commit()
    dump = solver.dump_chr_store()
    print("DUMP:", dump)
    assert len(dump) == 1
    assert ("gcd/1", 1) in dump


def test_length():
    from test_files.length import LengthSolver

    solver = LengthSolver()

    l1 = solver.fresh_var()
    solver.length("Nil", l1)

    assert len(solver.dump_chr_store()) == 0
    assert l1 == 0

    l2 = solver.fresh_var()
    solver.length(l2, 0)

    assert len(solver.dump_chr_store()) == 0
    assert l2 == "Nil"

    l3 = solver.fresh_var()
    solver.length((1, (2, "Nil")), l3)
    assert len(solver.dump_chr_store()) == 0
    assert l3 == 2

    l4 = solver.fresh_var()
    solver.length(l4, 5)
    assert len(solver.dump_chr_store()) == 0
    assert l4.is_bound()


def test_minimum():
    from test_files.minimum import MinimumSolver

    solver = MinimumSolver()

    current_minimum = inf

    for x in sample(range(0, 1000), 200):
        current_minimum = current_minimum if current_minimum < x else x
        solver.min(x)
        dump = solver.dump_chr_store()
        assert len(dump) == 1
        assert ("min/1", current_minimum) in dump


def test_minimax():
    from test_files.minimax import Minimax

    solver = Minimax()

    minimum = 1000
    maximum = 0

    for x in sample(range(1, 100000), 3000):
        minimum = x if minimum >= x else minimum
        maximum = x if maximum <= x else maximum
        solver.a(x)

    assert ("minimax/2", minimum, maximum) in solver.dump_chr_store()