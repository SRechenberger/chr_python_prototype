from chr.compiler import chr_compile
from chr.runtime import CHRFalse, unify

import pytest

def test_sum_solver():
    with open("test_files/sum_solver.chr", "r") as f:
        chr_compile("SumSolver", f.read(), target_file="generated/sum_solver.py")
    from generated.sum_solver import SumSolver

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
    with open("test_files/triple.chr", "r") as f:
        chr_compile("TripleSolver", f.read(), target_file="generated/triple.py")

    from generated.triple import TripleSolver

    solver = TripleSolver()
    solver.triple((1,2,3))

    assert len(solver.chr.dump()) == 4

    solver = TripleSolver()
    solver.triple({1:"A", 2:"B", "scheiss":"C"})

    assert len(solver.chr.dump()) == 3

    solver = TripleSolver()
    solver.triple([1, 2, 3])

    assert len(solver.chr.dump()) == 2
    assert ("single/1", 5) in solver.chr.dump()


def test_eq_solver():
    with open("test_files/eq_solver.chr", "r") as f:
        chr_compile("EqSolver", f.read(), target_file="generated/eq_solver.py")

    from generated.eq_solver import EqSolver

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
    with open("test_files/guard_tell.chr", "r") as f:
        chr_compile("GuardTell", f.read(), target_file="generated/guard_tell.py")

    from generated.guard_tell import GuardTell

    solver = GuardTell()

    a = solver.fresh_var()

    solver.test(a)

    assert not a.is_bound()

def test_error_message():
    with open("test_files/error_message.chr", "r") as f:
        chr_compile("ErrorSolver", f.read(), target_file="generated/error_message.py")

    from generated.error_message import ErrorSolver

    solver = ErrorSolver()

    message = "this is an error message!"

    with pytest.raises(CHRFalse, match=message):
        solver.error(message)

def test_leq_solver():
    with open("test_files/leq_solver.chr", "r") as f:
        chr_compile("LeqSolver", f.read(), target_file="generated/leq_solver.py")

    from generated.leq_solver import LeqSolver

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
    with open("test_files/fibonacci.chr", "r") as f:
        chr_compile("Fibonacci", f.read(), target_file="generated/fibonacci.py")

    from generated.fibonacci import Fibonacci

    def fib(n, r1=1, r0=0):
        if n == 0:
            return r0
        if n == 1:
            return r1
        return fib(n-1, r1 + r0, r1)

    solver = Fibonacci()

    for n in range(1, 15):
        solver.fib(n)
        r = solver.fresh_var()
        solver.read(r)
        assert r == fib(n)


def test_match():
    with open("test_files/match_solver.chr", "r") as f:
        chr_compile("MatchTest", f.read(), target_file="generated/match_test.py")

    from generated.match_test import MatchTest

    solver = MatchTest()

    x, y = solver.fresh_var(), solver.fresh_var()
    solver.match(x)
    solver.match(y)

    assert x != y
    assert len(solver.dump_chr_store()) == 2

def test_gcd():
    with open("test_files/gcd_solver.chr", "r") as f:
        chr_compile("GCDSolver", f.read(), target_file="generated/gcd_solver.py")

    from generated.gcd_solver import GCDSolver

    solver = GCDSolver()

    x = solver.fresh_var()

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
    assert len(dump) == 1
    assert ("gcd/1", 1) in dump


def test_length():
    with open("test_files/length.chr", "r") as f:
        chr_compile("LengthSolver", f.read(), target_file="generated/length.py")

    from generated.length import LengthSolver

    solver = LengthSolver()

    l1 = solver.fresh_var()
    solver.length("Nil", l1)

    assert len(solver.dump_chr_store()) == 0
    assert l1 == 0

    l2 = solver.fresh_var()
    solver.length(l2, 0)

    assert len(solver.dump_chr_store()) == 0
    assert l2 == "Nil"

    ## Will fail, because the recursion will in fact only happen,
    ## *after* the variable is required.
    ## Consider calling activate procedure directly after adding
    ## a constraint.
    l3 = solver.fresh_var()
    solver.length((1, (2, "Nil")), l3)
    assert len(solver.dump_chr_store()) == 0
    assert l3 == 2
