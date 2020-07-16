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


def apply_substitution(subst, term):
    if isinstance(term, Hashable) and term in subst:
        return apply_substitution(subst, subst[term])

    if type(term) is list:
        return [
            apply_substitution(subst, subterm)
            for subterm in term
        ]

    if type(term) is tuple:
        return tuple(
            apply_substitution(subst, subterm)
            for subterm in term
        )

    if type(term) is dict:
        return {
            key: apply_substitution(subst, value)
            for key, value in term.items()
        }

    return term


def merge_substitution(subst1, subst2, variables):
    result = subst1
    for key, val in subst2.items():
        if key in result:
            unifier = unify(val, result[key], variables)
            if unifier == None:
                return None
            result[key] = apply_substitution(unifier, val)
            result.update(unifier)
        else:
            result[key] = val
    return result


def unify(x, y, vars):

    if isinstance(x, Hashable) and x in vars:
        return {x: y}

    if isinstance(y, Hashable) and y in vars:
        return {y: x}

    if type(x) != type(y):
        return None

    if type(x) in [list, tuple] and type(y) in [list, tuple]:
        if len(x) != len(y):
            return None

        subst = {}
        for a, b in zip(x,y):
            u = unify(a, b, vars)
            if u == None:
                return None
            subst = merge_substitution(subst, u, vars)

        return subst

    if type(x) is dict and type(y) is dict:
        if x.keys() != y.keys():
            return None

        subst = {}
        for ka, a in x.items():
            u = unify(a, y[ka], vars)
            if u == None:
                return None
            subst = merge_substitution(subst, u, vars)

        return subst

    if x == y:
        return {}


class BuiltInStore:

    def __init__(self):
        self.subst = {}
        self.varset = set()
        self.next_fresh_var = 0
        self.delays = {}


    def fresh(self, name=None, existential=False):
        if name and name.startswith("_"):
            raise Exception("user variables must not begin with '_'")

        if name:
            if name in self.varset:
                var_name = f'_{name}{self.next_fresh_var}'
                self.next_fresh_var += 1
            else:
                var_name = name

        else:
            var_name = f'_VAR{self.next_fresh_var}'
            self.next_fresh_var += 1

        # self.subst[var_name] = None
        if not existential:
            self.varset.add(var_name)
        return var_name


    def delay(self, to_call, *vars):
        for var in vars:
            if var in self.delays and self.delays[var]:
                self.delays[var].append(to_call)
            else:
                self.delays[var] = [to_call]


    def ask_eq(self, x, y, subst={}, e_vars=set()):
        vars = e_vars.union(self.varset)
        u = unify(x, y, vars)
        if u == None:
            return None

        merged = merge_substitution(subst if subst else self.subst, u, vars)
        return merged


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
