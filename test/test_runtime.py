import pytest
import chr.runtime as rt

def test_add_constraint():
    store = rt.CHRStore()

    a = store.new()
    b = store.new()
    c = store.new()

    store.insert('a', a)
    store.insert('b', b)
    store.insert('c', c)

    for i,x in [(a,'a') ,(b, 'b') ,(c, 'c')]:
        assert store.alive(i)
        assert (i,x) in store.get_iterator()

def test_delete_constraint():
    store = rt.CHRStore()

    a = store.new()
    b = store.new()
    c = store.new()

    store.insert('a', a)
    store.insert('b', b)
    store.insert('c', c)

    store.delete(a)
    assert not store.alive(a)
    cs = list(store.get_iterator())
    assert (a, 'a') not in cs
    assert (b, 'b') in cs
    assert (c, 'c') in cs

    store.delete(b)
    assert not store.alive(b)
    cs = list(store.get_iterator())
    assert (b, 'b') not in cs
    assert (c, 'c') in cs

    store.delete(c)
    assert not store.alive(c)
    assert (c, 'c') not in store.get_iterator()


def test_unification():
    store = rt.BuiltInStore()
    a = store.fresh()
    b = store.fresh()
    c = store.fresh()
    terms = [
        (a, 2),
        (b, c),
        (c, 1),
        (1,1),
        ([a, 1], [2, b]),
        ((a, 1), (2, b)),
        ({1: a, 2: 1}, {1: 2, 2: b})
    ]

    for term1, term2 in terms:
        rt.unify(term1, term2)

        assert term1 == term2


def test_unify_cycle():
    store = rt.BuiltInStore()
    a = store.fresh()
    b = store.fresh()

    rt.unify(a, b)
    rt.unify(b, a)

    assert a.value == b and b.value != a


def test_ask_eq():
    store = rt.BuiltInStore()

    x = store.fresh()
    y = store.fresh()
    z = store.fresh()

    assert rt.unify(x, (1, 2))
    assert rt.unify(y, (1, 3))
    assert rt.unify((1, z), x)

    assert z == 2


def test_tell_eq():
    store = rt.BuiltInStore()
    x = store.fresh()
    y = store.fresh()
    z = store.fresh()

    assert store.tell_eq(y, 1)
    assert store.tell_eq(z, 2)

    assert store.tell_eq(x, (y, z))

    assert x == (1, 2)


def test_logic_variable():
    trail = []
    x = rt.LogicVariable('x', trail)
    y = rt.LogicVariable('y', trail)
    assert rt.unify(x, 1)
    assert x.is_bound()
    assert rt.unify(x, y)
    assert y.get_value() == 1
    z = rt.LogicVariable('z', trail)
    assert rt.unify(z, (x,y))
    assert z.get_value() == (1,1)
    assert rt.unify(z, (1,1))


def test_occurs_check():
    trail = []
    x = rt.LogicVariable('x', trail)
    assert not x.occurs_check(x)
    assert x.occurs_check((x,))
