from typing import Any, Optional, Callable


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
        self.history = set()

    def new(self):
        id = self.next_id
        self.next_id += 1
        self.alive_set[id] = True
        return id

    def add_to_history(self, rule_name, *ids):
        self.history.add((rule_name, ids))

    def in_history(self, rule_name, *ids):
        return (rule_name, ids) in self.history

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


def unify(left, right) -> bool:
    """
    unifies two values:
        - if either value is a logic variable, the variable is bound to the other value
        - if both values are dict/list/tuple, they are unified elementwise
        - otherwise equality is checked
    :param left: one value
    :param right: other value
    :return: True, if the values are unifiable; False otherwise
    """

    if isinstance(left, LogicVariable):
        if left.is_bound():
            return unify(left.get_value(), right)
        return left.set_value(right)
    if isinstance(right, LogicVariable):
        if right.is_bound():
            return unify(left, right.get_value())
        return right.set_value(left)

    if type(left) is not type(right):
        return False

    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return False
        for vl, vr in zip(left.values(), right.values()):
            if not unify(vl, vr):
                return False
        return True

    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        for vl, vr in zip(left, right):
            if not unify(vl, vr):
                return False
        return True

    return left == right


def get_value(v):
    if isinstance(v, LogicVariable) and v.is_bound():
        return v.get_value()
    return v


def is_bound(v):
    if isinstance(v, LogicVariable):
        return v.is_bound()

    return True


class UnknownVariableError(KeyError):
    """
    Raised, if the given variable index is unknown to the builtin store
    """

    def __init__(self, index):
        self.index = index


class UnboundVariableError(KeyError):
    """
    Raised, if the variable with the given index is not bound to a value
    """

    def __init__(self, index):
        self.index = index


class BoundVariableError(KeyError):
    """
    Raised, if the variable with the given index is already bound to a value
    """

    def __init__(self, index):
        self.index = index


class BuiltInStore:

    def __init__(self):
        self.union_find = {}
        self.value_bindings = {}
        self.next_variable_index = 0
        self.known_names = {}
        self.next_save_point = 0
        self.recent_bindings = []
        self.delayed_calls = {}
        self.next_delay_id = 0
        self.called_delayed_closures = set()

    def commit_recent_bindings(self):
        """
        Commits recent bindings, i.e. deletes the list of bindings.
        :return: None
        """

        recent_bindings = self.recent_bindings
        self.recent_bindings = []
        for _, index in recent_bindings:
            self.call_delayed_closures(index)

    def reset_recent_bindings(self):
        """
        Resets all the recent uncommitted variable bindings.
        :return: None
        """
        while self.recent_bindings:
            t, v = self.recent_bindings.pop()
            assert t in {"union", "value", "closure"}
            if t == "union":
                self.union_find[v] = v
            if t == "value":
                del self.value_bindings[v]

    def fresh(self, name: Optional[str] = None, value: Optional[Any] = None) -> 'LogicVariable':
        """
        Generate a fresh logic variable
        :param name: name of the variable (only for usability/cosmetics)
        :param value: initial value of the variable
        :return: LogicVariable object, representing the variable
        """
        assert len(self.union_find) == self.next_variable_index

        variable_index = self.next_variable_index
        self.next_variable_index += 1
        variable_name = name

        if not variable_name:
            variable_name = f"_V{variable_index}"
        else:
            if variable_name in self.known_names:
                variable_name = f"{variable_name}_{self.known_names[variable_name]}"
                self.known_names[variable_name] += 1
            else:
                self.known_names[variable_name] = 0

        self.union_find[variable_index] = variable_index

        if value:
            self.value_bindings[variable_index] = value

        return LogicVariable(variable_index, variable_name, self)

    def find(self, index: int) -> int:
        """
        Find the representative if the given index in the union-find structure
        :param index: index to find the representative of
        :return: representative index of the given index
        """
        assert index in self.union_find

        idx = index
        r = self.union_find[idx]
        while idx != r:
            idx, r = r, self.union_find[r]

        return r

    def union(self, a: int, b: int) -> bool:
        """
        Union two variable indices, with respect to value binding
        :param a: first variable index
        :param b: second variable index
        :return: True, if the variables were unioned successfully; False otherwise.
        """
        assert a in self.union_find
        assert b in self.union_find

        # Find representative of both variables
        r_a = self.find(a)
        r_b = self.find(b)

        # If both representatives are different i.e.:
        #   - the variables are not equal to begin with
        #   - and not already bound to one another
        if r_a != r_b:
            # If both variables are already bound to a value, the values must be unifiable
            if r_a in self.value_bindings and r_b in self.value_bindings:
                u = unify(self.value_bindings[r_a], self.value_bindings[r_b])
                # if the values are unifiable, union them
                # and return True
                if u:
                    self.union_find[r_a] = r_b
                    self.recent_bindings.append(("union", r_a))
                    return True
                # return false otherwise
                return False
            # if only one of the variables is bound, set the
            # bound one as representative of the unbound one
            if r_a in self.value_bindings:
                self.union_find[r_b] = r_a
                self.recent_bindings.append(("union", r_b))
                self.value_bindings[r_b] = self.value_bindings[r_a]
                self.recent_bindings.append(("value", r_b))
                return True
            if r_b in self.value_bindings:
                self.union_find[r_a] = r_b
                self.recent_bindings.append(("union", r_a))
                self.value_bindings[r_a] = self.value_bindings[r_b]
                self.recent_bindings.append(("value", r_a))
                return True
            # If neither variable is bound, union them
            self.union_find[r_a] = r_b
            self.recent_bindings.append(("union", r_a))
        # If the variables are already in a union, return True
        return True

    def get_value(self, index: int) -> Optional[Any]:
        """
        Retrieve the value of a variable, if it is bound.
        :param index: index of the variable
        :return: the value of the variable, if it is bound; None otherwise
        """

        r = self.find(index)
        if r in self.value_bindings:
            return self.value_bindings[r]
        return None

    def set_value(self, index: int, value: Any) -> None:
        """
        Set the value of a variable.
        :param index: index of the variable
        :param value: value to bind it to
        :return: None
        :raises BoundVariableException: variable is already bound
        """
        if index in self.value_bindings:
            if self.get_value(index) == value:
                return
            raise BoundVariableError(index)
        r = self.find(index)
        self.value_bindings[r] = value
        self.recent_bindings.append(("value", r))

    def is_bound(self, index: int) -> bool:
        """
        Check if the variable with the given index is bound to a value
        :param index: index of the variable to check
        :return: True, if the variable is bound; false otherwise
        """
        if index not in self.union_find:
            raise UnknownVariableError(index)

        return index in self.value_bindings

    def delay(self, closure: Callable, *args: Any):
        """
        delayes the call of a closure until an unbound variable in its arguments is set
        :param closure: closure to delay
        :param args: arguments of the closure
        """
        for arg in args:
            i = self.next_delay_id
            if isinstance(arg, LogicVariable) and not arg.is_bound():
                if arg.index in self.delayed_calls:
                    self.delayed_calls[arg.index].append((i, closure))
                else:
                    self.delayed_calls[arg.index] = [(i, closure)]

    def call_delayed_closures(self, index: int):
        """
        Tries to call all delayed closures associated with the given variable index
        :param index: variable index
        """
        if index in self.delayed_calls:
            for i, closure in self.delayed_calls[index]:
                if i not in self.called_delayed_closures:
                    if closure():
                        self.called_delayed_closures.add(i)


class LogicVariable:
    """
    An interface to a specific logic variable, managed by the builtin store.
    """

    def __init__(self, index: int, name: str, store: BuiltInStore):
        """
        Create a logic variable with the given index and name, and a back reference to the
        BuiltInStore instance, which created it.
        :param index: index of the variable in the store
        :param name: name of the variable (for usability/cosmetic purposes)
        :param store: back reference to the BuiltInStore instance, that created this variable
        """
        self.index = index
        self.name = name
        self.store = store

    def __str__(self):
        return f"{self.name}{f'={self.get_value()}' if self.is_bound() else ''}@{self.index}"

    def __repr__(self):
        return str(self)

    def get_value(self) -> Optional[Any]:
        """
        Retrieve the value of this variable, if it is bound.
        :return: the value of this variable, if it is bound; None otherwise.
        """
        return self.store.get_value(self.index)

    def is_bound(self) -> bool:
        """
        Check, if the variable is bound to a value.
        :return: True, if the variable is bound; False otherwise
        """
        return self.store.is_bound(self.index)

    def __get_representative(self) -> int:
        return self.store.find(self.index)

    def __eq__(self, other: Any) -> bool:
        """
        Checks, whether the variable is equal to the given object, i.e.:
            - if the other object is a variable:
                - they are the same variable (i.e. same index)
                - they are bound to the same value (referentially)
            - the other object is the value, which this object is bound to (referentially)
        :param other: other object
        :return: True, if the object is equal (see above) to the variable; False otherwise
        :raises RuntimeError: the other value is a logic variable of another BuiltInStore instance.
        """

        if isinstance(other, LogicVariable):
            if self.store is not other.store:
                raise RuntimeError("cannot call __eq__ for variables of different BuiltInStore instances")

            if self is other:
                return True

            if self.__get_representative() == other.__get_representative():
                return True

            if self.is_bound() and other.is_bound():
                if type(self.get_value()) is not type(other.get_value()):
                    return False
                if isinstance(self.get_value(), dict):
                    if self.get_value().keys() != other.get_value().keys():
                        return False
                    return all(
                        l == r
                        for l, r
                        in zip(self.get_value().values(), other.get_value().values())
                    )
                if isinstance(self.get_value(), (list, tuple)):
                    return all(
                        l == r
                        for l, r
                        in zip(self.get_value(), other.get_value())
                    )
                return self.get_value() == other.get_value()

            return False

        return self.get_value() == other

    def set_value(self, value: Any) -> bool:
        """
        Binds the value of the logic variable to the given value.
        If value is a logic variable, they are unioned.
        :param value: value to bind this variable to
        :return: True if the value was set successfully; False otherwise
        :raises RuntimeError: the value is a logic variable of another BuiltInStore instance.
        """

        if isinstance(value, LogicVariable):
            if self.store is not value.store:
                raise RuntimeError("cannot call set_value for variables of different BuiltInStore instances")
            return self.store.union(self.index, value.index)
        self.store.set_value(self.index, value)
        return True

    def occurs_check(self, term) -> bool:
        if self is term:
            return True
        if isinstance(term, (tuple, list)):
            return any(self.occurs_check(sub_term) for sub_term in term)
        if isinstance(term, dict):
            return any(self.occurs_check(sub_term) for sub_term in term.values())
        return False


class CHRSolver:

    def __init__(self):
        self.builtin, self.chr = BuiltInStore(), CHRStore()

    def fresh_var(self, name: Optional[str] = None, value: Optional[Any] = None) -> LogicVariable:
        return self.builtin.fresh(name=name, value=value)

    def dump_chr_store(self):
        return self.chr.dump()
