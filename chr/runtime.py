from collections.abc import Hashable

class UndefinedConstraintError(Exception):
    def __init__(self, symbol, arity):
        self.signature = f'{symbol}/{arity}'

    def __str__(self):
        return f'undefined constraint: {self.signature}'

    def __repr__(self):
        return str(self)


class InconsistentBuiltinStoreError(Exception):
    pass

class CHRFalse(Exception):
    def __init__(self, *messages):
        self.messages = messages

def all_different(*vals):
    s = set()
    for val in vals:
        if val in s:
            return False
        s.add(val)

    return True

class CHRStore:

    def __init__(self):
        self.next_id = 0
        self.alive_set = {}
        self.constraints = {}
        self.history = {}
        self.recently_killed = set()

    def new(self):
        id = self.next_id
        self.next_id += 1
        self.alive_set[id] = True
        return id

    def add_to_history(self, rule_name, *ids):
        ids_set = set(ids)
        if rule_name in self.history:
            self.history[rule_name].append(ids_set)
        else:
            self.history[rule_name] = [ids_set]


    def in_history(self, rule_name, *ids):
        ids_set = set(ids)
        if rule_name not in self.history:
            return False

        delete_ixs = []
        deleted_set = set()
        to_return = False
        for ix, jds_set in enumerate(self.history[rule_name]):
            killed = jds_set.intersection(self.recently_killed)
            if len(killed) > 0:
                deleted_set = deleted_set.union(killed)
                delete_ixs.append(ix)
            elif ids_set == jds_set:
                to_return = True
                break

        for ix in delete_ixs:
            del self.history[rule_name][ix]

        self.recently_killed -= deleted_set

        return to_return


    def kill(self, id):
        if id in self.alive_set:
            self.alive_set[id] = False
            self.recently_killed.add(id)
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

    def get_iterator(self, symbol=None, fix=False):
        it = self.constraints.items()
        if symbol:
            it = filter(lambda c: c[1][0] == symbol, it)
        if fix:
            it = list(it)
        return it

    def dump(self):
        return list(self.constraints.values())


def unify(left, right):
    if left is right:
        return True

    if (
        isinstance(left, LogicVariable) and
        isinstance(right, LogicVariable) and
        (left.find_repr() is not left or right.find_repr() is not right)
    ):
        left_repr = left.find_repr()
        right_repr = right.find_repr()
        if left_repr.name < right_repr.name:
            return unify(left_repr, right_repr)
        return unify(right_repr, left_repr)


    if isinstance(left, LogicVariable):
        if left.is_bound():
            return unify(left.get_value(), right)

        return left.set_value(right)

    if isinstance(right, LogicVariable):
        if right.is_bound():
            return unify(left, right.get_value())

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

def get_value(v):
    if isinstance(v, LogicVariable):
        if v.is_bound():
            return v.get_value()
        else:
            raise Exception(f"variable {v} not bound")
    return v

def is_bound(v):
    if isinstance(v, LogicVariable):
        return v.is_bound()

    return True

class LogicVariable:
    def __init__(self, name, store, value=None):
        self.value = value
        self.name = name
        self.store = store

    def occurs_check(self, term):
        if self is term:
            return False

        if type(term) in [list, tuple]:
            return self in term \
                or any(self.occurs_check(subterm) for subterm in term)

        if type(term) is dict:
            return self in term.values() \
                or any(self.occurs_check(subterm) for subterm in term.values())

        return False

    def unset(self):
        self.value = None

    def __getitem__(self, key):
        return self.get_value()[key]

    def set_value(self, value):
        if self.occurs_check(value):
            raise Exception(f'{self} occurs in {value}')

        if self.is_bound():
            return False

        if self.value == None:
            self.value = value
            self.store.trail.append(self)
            return True

        if isinstance(self.value, LogicVariable):
            return self.value.set_value(value)

        return False


    def get_value(self):

        if isinstance(self.value, LogicVariable):
            return self.value.get_value()

        if self.value == None:
            return None

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

    def find_repr(self):
        if isinstance(self.value, LogicVariable):
            return self.value.find_repr()

        return self


    def is_bound(self):

        if isinstance(self.value, LogicVariable):
            return self.value.is_bound()

        if self.value == None:
            return False

        return True

    def __str__(self):
        if self.is_bound():
            return str(self.value)

        return self.name

    def __repr__(self):
        return str(self)


    def __eq__(self, other):
        if self is other:
            return True

        if isinstance(other, LogicVariable):
            return self.find_repr() is other.find_repr()

        if self.is_bound():
            return self.get_value() == other

        return False

class BuiltInStore:

    def __init__(self):
        self.vars = {}
        self.next_fresh_var = 0
        self.trail = []
        self.next_delay_id = 0
        self.delays = {}
        self.successfully_called_delays = set()


    def fresh(self, name=None, value=None):
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

        return LogicVariable(var_name, self, value=value)


    def delay(self, callable, *vars):
        id = self.next_delay_id
        for var in vars:
            if var.name in self.delays:
                self.delays[var.name].append((id, callable))
            else:
                self.delays[var.name] = [(id, callable)]


        self.next_delay_id += 1


    def ask_eq(self, x, y):
        return x == y

    def tell_eq(self, x, y):
        return unify(x, y)

    def is_consistent(self):
        return self.consistent

    def commit(self):
        trail = self.trail
        self.trail = []
        for var in trail:
            if var.name in self.delays:
                for id, f in self.delays[var.name]:
                    if id not in self.successfully_called_delays:
                        if f():
                            self.successfully_called_delays.add(id)

        # Cleanup
        for id in self.successfully_called_delays:
            for v, ds in self.delays.items():
                self.delays[v] = [
                    (id1, f)
                    for (id1, f) in ds
                    if id1 != id
                ]

    def backtrack(self):
        for var in self.trail:
            var.unset()

        self.trail = []


class CHRSolver:

    def __init__(self):
        self.builtin, self.chr = BuiltInStore(), CHRStore()

    def fresh_var(self, name=None, value=None):
        return self.builtin.fresh(name=name, value=value)

    def dump_chr_store(self):
        return self.chr.dump()
