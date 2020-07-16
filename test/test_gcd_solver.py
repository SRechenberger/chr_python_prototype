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
    if m <= n:
        chr.delete(i)
        gcd(m-n)

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
    if n <= m:
        chr.delete(j)
        gcd(m-n)


def test_gcd_solver():
    x = builtin.fresh()
    y = builtin.fresh()
    
    gcd(x)
    gcd(y)

    print(list(chr.get_iterator()))
    assert False
