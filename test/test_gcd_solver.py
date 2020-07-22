import pytest
import chr.runtime as rt

class RecursiveSolver:

    def __init__(self):
        self.builtin = rt.BuiltInStore()
        self.chr = rt.CHRStore()

    def gcd(self,x):
        c = ('gcd', x)
        id = self.chr.new()
        self.chr.insert(c, id)
        self.builtin.delay(lambda: gcd_1(id, x), x)
        self.gcd_1(id, x)


    def gcd_1(self, id, x):
        self.gcd_1_call_body(id, x)
        if self.chr.alive(id):
            self.gcd_2(id, x)


    def gcd_1_call_body(self, id, x):
        if self.builtin.ask_eq(x, 0):
            self.chr.delete(id)


    def gcd_2(self, id, x):
        ls = self.chr.get_iterator(fix=True)
        self.gcd_2_join_loop(ls, id, x)
        if self.chr.alive(id):
            self.gcd_3(id, x)


    def gcd_2_join_loop(self, ls, i, n):
        for j, c in ls:
            if c[0] == "gcd" and self.chr.alive(j) and j != i:
                self.gcd_2_call_body(i, n, c[1])
            if not self.chr.alive(i):
                break


    def gcd_2_call_body(self, i, n, m):
        if m.get_value() <= n.get_value():
            self.chr.delete(i)
            z = self.builtin.fresh(value=n.get_value() - m.get_value())
            self.gcd(z)


    def gcd_3(self, i, m):
        ls = self.chr.get_iterator(fix=True)
        self.gcd_3_join_loop(ls, i, m)


    def gcd_3_join_loop(self, ls, i, m):
        for j, c in ls:
            if c[0] == "gcd" and self.chr.alive(j) and j != i:
                self.gcd_3_call_body(j, c[1], m)
            if not self.chr.alive(i):
                break


    def gcd_3_call_body(self, j, n, m):
        if m.get_value() <= n.get_value():
            self.chr.delete(j)
            z = self.builtin.fresh(value=n.get_value() - m.get_value())
            self.gcd(z)

    def fresh(self, name=None):
        return self.builtin.fresh(name=name)



GCD_SYMBOL = "gcd"
GCD_1_SYMBOL = f"{GCD_SYMBOL}/1"

class IterativeSolver:


    def __init__(self):
        self.builtin = rt.BuiltInStore()
        self.chr = rt.CHRStore()


    def fresh(self, name=None):
        return self.builtin.fresh(name=name)


    def gcd(self, *args):
        if len(args) == 1:
            vars = [
                arg if isinstance(arg, rt.LogicVariable) else self.builtin.fresh(value=args[0])
                for arg in args
            ]
            new_constraint = (GCD_1_SYMBOL, *vars)
            new_id = self.chr.new()
            self.chr.insert(new_constraint, new_id)
            self.__activate_gcd(new_id, *vars)

        else:
            raise Exception(f"constraint {GCD_SYMBOL}/{len(args)} not defined")


    def __activate_gcd(self, id, x):
        if self.__gcd_1(id, x):
            return
        if self.__gcd_2(id, x):
            return
        if self.__gcd_3(id, x):
            return

        if not x.is_bound():
            self.builtin.delay(lambda: self.__activate_gcd(id, x), x)


    def __gcd_1(self, id, x):
        if self.chr.alive(id):
            if x.get_value() == 0 and not self.chr.in_history("r0", id):
                self.chr.add_to_history("r0", id)
                self.chr.delete(id)
                return True
        return False


    def __gcd_2(self, id, x):
        for j, c in self.chr.get_iterator(symbol=GCD_1_SYMBOL, fix=True):
            if j != id:
                if self.chr.alive(id) and self.chr.alive(j):
                    if c[1].is_bound() and x.is_bound():
                        m = c[1].get_value()
                        n = x.get_value()
                        if m <= n and not self.chr.in_history("r1", id, j):
                            self.chr.add_to_history("r1", id, j)
                            self.chr.delete(id)
                            new_id = self.chr.new()
                            new_var = self.builtin.fresh(value=n-m)
                            new_constraint = (GCD_1_SYMBOL, new_var)
                            self.chr.insert(new_constraint, new_id)
                            self.__activate_gcd(new_id, new_var)
                            return True
        return False


    def __gcd_3(self, id, x):
        print("gcd/1_3", id, x)
        for j, c in self.chr.get_iterator(symbol=GCD_1_SYMBOL, fix=True):
            if j != id:
                if self.chr.alive(id) and self.chr.alive(j):
                    if x.is_bound() and c[1].is_bound():
                        m = x.get_value()
                        n = c[1].get_value()
                        if m <= n and not self.chr.in_history("r1", id, j):
                            self.chr.add_to_history("r1", id, j)
                            self.chr.delete(j)
                            new_id = self.chr.new()
                            new_var = self.builtin.fresh(value=n-m)
                            new_constraint = (GCD_1_SYMBOL, new_var)
                            self.chr.insert(new_constraint, new_id)
                            self.__activate_gcd(new_id, new_var)
                            if not self.chr.alive(id):
                                return True
        return False


def test_gcd_iterative_solver():
    solver = IterativeSolver()

    solver.gcd(100)
    solver.gcd(89)

    assert ('gcd/1', 1) in list(zip(*solver.chr.get_iterator()))[1]


def test_delay():
    for solver in IterativeSolver(),:
        m = solver.builtin.fresh()
        n = solver.builtin.fresh()
        p = solver.builtin.fresh()
        solver.gcd(n)
        solver.gcd(m)
        assert ('gcd/1', m) in list(zip(*solver.chr.get_iterator()))[1]
        assert ('gcd/1', n) in list(zip(*solver.chr.get_iterator()))[1]
        solver.gcd(p)
        solver.builtin.tell_eq(m, 2*3*3*5)
        solver.builtin.tell_eq(n, 3*5*7)
        assert ('gcd/1', 3*5) in list(zip(*solver.chr.get_iterator()))[1]
        solver.builtin.tell_eq(p, 3*3)
        assert ('gcd/1', 3) in list(zip(*solver.chr.get_iterator()))[1]

def test_gcd_rec_solver():
    solver = RecursiveSolver()


    x = solver.fresh()
    y = solver.fresh()

    solver.builtin.tell_eq(x, 100)
    solver.builtin.tell_eq(y, 89)

    solver.gcd(x)
    solver.gcd(y)

    assert ('gcd', 1) in list(zip(*solver.chr.get_iterator()))[1]
