from collections.abc import Hashable

class CHRStore:

    def __init__(self):
        self.next_id = 0
        self.alive_set = {}
        self.constraints = {}

    def new(self):
        id = self.next_id
        self.next_id += 1
        self.alive_set[id] = True
        return id

    def kill(self, id):
        if id in self.alive_set:
            self.alive_set[id] = False
        else:
            raise Exception(f'id {id} unknown')

    def alive(self, id):
        if id in self.alive_set:
            return self.alive_set[id]
        else:
            raise Exception(f'id {id} unknown')

    def insert(self, constraint, id):
        if id in self.constraints:
            raise Exception(
                f'constraint with id {id} already set to {self.constraints[id]}'
            )
        else:
            self.constraints[id] = constraint

    def delete(self, id):
        if id in self.constraints:
            del self.constraints[id]
            self.alive_set[id] = False
        else:
            raise Exception(f'constraint with id {id} unknown')

    def get_iterator(self):
        return self.constraints.items()


def unify(left, right):
    if isinstance(left, LogicVariable):
        if left.is_bound():
            return unify(left.get_value(), right)

        return left.set_value(right)

    if isinstance(right, LogicVariable):
        if right.is_bound():
            return unify(right.get_value(), left)

        return right.set_value(left)

    if type(left) != type(right):
        return False

    if type(left) in [list, tuple] and type(right) in [list, tuple]:
        for l, r in zip(left, right):
            if not unify(l, r):
                return False

    if type(left) is dict and type(right) is dict:
        for l, r in zip(left.items(), right.items()):
            if not unify(l, r):
                return False

    return left == right


class LogicVariable:
    def __init__(self, name, trail, value=None):
        self.value = value
        self.name = name
        self.trail = trail
        self.delayed = []

    def occurs_check(self, term):
        if term == self:
            return True

        if type(term) in [list, tuple]:
            for subterm in term:
                if self.occurs_check(subterm):
                    return True

        if type(term) is dict:
            for subterm in term.values():
                if self.occurs_check(subterm):
                    return True

        return False

    def unset(self):
        self.value = None

    def delay(self, callable):
        self.delayed.append(callable)

    def set_value(self, value):
        if self.occurs_check(value):
            raise Exception(f'{self} occurs in {value}')

        if self.is_bound():
            return False

        if self.value == None:
            self.value = value
            self.trail.append(self)
            for callable in self.delayed:
                callable()
            return True

        if isinstance(self.value, LogicVariable):
            return self.value.set_value(value)

        return False


    def get_value(self):
        if self.value == None:
            return None

        if isinstance(self.value, LogicVariable):
            return self.value.get_value()

        if type(self.value) is list:
            return [
                term.get_value() if isinstance(term, LogicVariable) else term
                for term in self.value
            ]

        if type(self.value) is tuple:
            return tuple(
                term.get_value() if isinstance(term, LogicVariable) else term
                for term in self.value
            )

        if type(self.value) is dict:
            return {
                key: term.get_value() if isinstance(term, LogicVariable) else term
                for key, term in self.value.items()
            }

        return self.value


    def is_bound(self):
        if self.value == None:
            return False

        if isinstance(self.value, LogicVariable):
            return self.value.bound()

        return True

    def __str__(self):
        if self.is_bound():
            return str(self.value)

        return self.name

    def __repr__(self):
        return str(self)


class BuiltInStore:

    def __init__(self):
        self.vars = {}
        self.next_fresh_var = 0
        self.trail = []


    def fresh(self, name=None):
        if name and name.startswith("_"):
            raise Exception("user variables must not begin with '_'")

        if name:
            if name in self.vars:
                var_name = f'_{name}{self.next_fresh_var}'
                self.next_fresh_var += 1
            else:
                var_name = name

        else:
            var_name = f'_VAR{self.next_fresh_var}'
            self.next_fresh_var += 1

        return LogicVariable(var_name, self.trail)


    def delay(self, callable, *vars):
        for var in vars:
            var.delay(callable)


    def ask_eq(self, x, y):
        return unify(x,y)


    def tell_eq(self, x, y):
        u = unify(x, y, self.varset)
        if u == None:
            return False

        subst = merge_substitution(self.subst, u, self.varset)
        if subst == None:
            return False

        for key, calls in self.delays:
            if self.subst[key] != subst[key]:
                for call in calls:
                    call()

        self.subst = subst
        return True
