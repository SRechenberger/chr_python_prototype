import runtime

class EqSolver:

    def __init__(self):
        self.store = runtime.Store()

    def eq(self, x, y):
        constraint = ("eq", x, y)
        id = self.store.new()
        self.store.insert(constraint, id)
        
