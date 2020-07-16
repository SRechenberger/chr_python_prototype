import pytest
import chr.runtime as rt

class TestCHRStore:
    def test_add_constraint(self):
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

    def test_delete_constraint(self):
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


    def test_apply_substitution(self):
        subst = {'$a': 1, '$b': '$c', '$c': 3}

        tests = [
            ('$a', 1),
            ('$b', 3),
            (('$a', '$b', '$c'), (1, 3, 3)),
            (['$a', '$c', '$b'], [1, 3, 3]),
            ({1: '$a', 2: '$b', 3: '$c'}, {1:1, 2:3, 3:3}),
            (subst, {'$a': 1, '$b': 3, '$c': 3})
        ]

        for i, o in tests:
            assert rt.apply_substitution(subst, i) == o

    def test_unification(self):
        vars = set(['$a', '$b'])
        terms = [
            ('$a', 1),
            ('$b', '$c'),
            (1,1),
            (['$a', 1], [2, '$b']),
            (('$a', 1), (2, '$b')),
            ({1: '$a', 2: 1}, {1: 2, 2: '$b'})
        ]

        for term1, term2 in terms:
            u = rt.unify(term1, term2, vars)
            assert u != None

            t1 = rt.apply_substitution(u, term1)
            t2 = rt.apply_substitution(u, term2)
            assert t1
            assert t2
            assert t1 == t2
