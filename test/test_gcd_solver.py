import pytest
import chr.runtime as rt

builtin = rt.BuiltInStore()
chr = rt.CHRStore()

def gcd(x):
    c = ('gcd', x)
    id = chr.new()
    chr.insert(c, id)
    builtin.delay(lambda: gcd_1(id, x), x)
    gcd_1(id, x)


def gcd_1(id, x):
    gcd_1_call_body(id, x)
    if chr.alive(id):
        gcd_2(id, x)


def gcd_1_call_body(id, x):
    if builtin.ask_eq(x, 0):
        chr.delete(id)


def gcd_2(id, x):
    ls = chr.get_iterator()
    gcd_2_join_loop(ls, id, x)
    if chr.alive(id):
        gcd_3(id, x)


def gcd_2_join_loop(ls, i, n):
    for j, c in ls:
        if c[0] == "gcd" and chr.alive(j) and j != i:
            gcd_2_call_body(i, n, c[1])
        if not chr.alive(i):
            break


def gcd_2_call_body(i, n, m):
    if m.get_value() <= n.get_value():
        chr.delete(i)
        z = builtin.fresh(value=n.get_value() - m.get_value())
        gcd(z)


def gcd_3(i, m):
    ls = chr.get_iterator()
    gcd_3_join_loop(ls, i, m)


def gcd_3_join_loop(ls, i, m):
    for j, c in ls:
        if c[0] == "gcd" and chr.alive(j) and j != i:
            gcd_3_call_body(j, c[1], m)
        if not chr.alive(i):
            break


def gcd_3_call_body(j, n, m):
    if m.get_value() <= n.get_value():
        chr.delete(j)
        z = builtin.fresh(value=n.get_value() - m.get_value())
        gcd(z)


def test_gcd_solver():
    x = builtin.fresh()
    y = builtin.fresh()

    builtin.tell_eq(x, 100)
    builtin.tell_eq(y, 89)

    gcd(x)
    gcd(y)

    assert ('gcd', 1) in list(zip(*chr.get_iterator()))[1]
