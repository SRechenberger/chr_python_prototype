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


class BuiltInStore:

    def __init__(self):
        self.vars = {}
        self.next_var = 0

    def fresh(self, name=None):
        if name.startswith("_"):
            raise Exception("user variables must not begin with '_'")

        if name:
            if name in self.vars:
                var_name = f'_{name}{self.next_var}'
                self.next_var += 1
            else:
                var_name = name

        else:
            var_name = f'_VAR{self.next_var}'
            self.next_var += 1

        self.vars[var_name] = None
        return var_name

    def get_value(self, v):
        if v in self.vars:
            get_value(self.vars[v])

        else:
            return v

    def set_value(self, v):
        if v in self.vars:
            

    def ask_eq(self, a, b):
        if type(a) != type(b):
            return False

        elif a in exist_vars:
            if self.is_exist_var(a):
                exist_vars[a] = b
                return True
            else:
                return exist_vars[a] == b

        elif b in exist_vars:
            if self.is_exist_var(b):
                exist_vars[b] = a
                return True
            else:
                return exist_vars[b] == a



        if type(a) in [tuple, list] and type(b) in [tuple, list]:
            for x, y in zip(a, b)
