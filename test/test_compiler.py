from chr.compiler import chr_compile

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
    solver.triple(1,2,3)

    assert len(solver.chr.dump()) == 4


def test_eq_solver():
    with open("test_files/eq_solver.chr", "r") as f:
        chr_compile("EqSolver", f.read(), target_file="generated/eq_solver.py")

    from generated.eq_solver import EqSolver

    solver = EqSolver()
    a = solver.builtin.fresh()
    b = solver.builtin.fresh()
    c = solver.builtin.fresh()

    solver.eq(a, b)
    solver.eq(c, b)

    dump = solver.chr.dump()
    print(dump)
    assert len(dump) == 0

    solver.eq(a, 1)
    assert b == 1
    assert c == 1
