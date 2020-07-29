from chr.compiler import chr_compile
from chr.runtime import CHRFalse

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
    solver.triple({1:"A", 2:"B", 3:"C"})

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
    a = solver.fresh_var()
    b = solver.fresh_var()
    c = solver.fresh_var()

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
