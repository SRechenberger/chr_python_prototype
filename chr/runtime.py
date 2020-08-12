from typing import Any, Union


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


class CHRGuardFail(Exception):
    def __init__(self, *messages):
        self.messages = messages


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
        print("FIRE:", rule_name, *ids)
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
    if isinstance(v, LogicVariable) and v.is_bound():
        return v.get_value()
    return v


def is_bound(v):
    if isinstance(v, LogicVariable):
        return v.is_bound()

    return True


class BuiltInStore:
    def __init__(self):
        self.union_find = []
        self.value_bindings = {}
        self.next_variable_index = 0

    def fresh(self, name: Union[None, str] = None, value: Union[None, Any] = None) -> LogicVariable:
        assert len(self.union_find) == self.next_variable_index

        variable_index = self.next_variable_index
        self.next_variable_index += 1
        variable_name = name
        if not variable_name:
            variable_name = f"_V{variable_index}"

        self.union_find.append(variable_index)

        if value:
            self.value_bindings[variable_index] = value

        return LogicVariable(variable_index, variable_name, self)

    def find(self, index: int) -> int:
        r = index
        while r != self.union_find[r]:
            r = self.union_find[r]

        return r

    def union(self, a: int, b: int):
        r_a = self.find(a)
        r_b = self.find(b)

        if r_a != r_b:
            self.union_find[r_a] = r_b



class LogicVariable:
    def __init__(self, index: int, name: str, store: BuiltInStore):


class CHRSolver:

    def __init__(self):
        self.builtin, self.chr = BuiltInStore(), CHRStore()

    def fresh_var(self, name=None, value=None):
        return self.builtin.fresh(name=name, value=value)

    def dump_chr_store(self):
        return self.chr.dump()
