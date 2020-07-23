# program looks like this:
# [
#   {
#       "kept": [],
#       "removed": [("gcd_1", 0, "_1")],
#       "guard": [("ask=", "_1", 0)]),
#       "body": []
#   },
#   {
#       "kept": [("gcd_1", 2, "_2")],
#       "removed": [("gcd_1", 1, "_1")],
#       "guard": [("bound", "_1"), ("bound", "_2"), ("ask<=", "_1", "_2")],
#       "body": [
#           ("fresh", "_3"),
#           ("tell=", "_3", ("-", "_2", "_1")),
#           ("gcd/1", "_3")
#       ]
#   }
# ]

TEMPLATES = {
    "var": "vars[{ var_id }]",
    "fresh": "{ varname } = self.builtin.fresh()",
    "tell=": "self.builtin.tell_eq({ var1 }, { var2 })",
    "ask=" : "{ var1 } == { var2 }",
    "bound": "{ var1 }.is_bound()",
    "ask<=": "{ var1 }.get_value() <= { var2 }.get_value()",
    "ask>=": "{ var1 }.get_value() >= { var2 }.get_value()",
    "occurrence_head": 'def __{ symbol }_{ occurrence_id }(id, *vars):',
    "matching_loop_head": 'for i_{ id_idx }, c_{ id_idx } in self.chr.get_iterator(symbol={ constraint_symbol }, fix=True):',
    "alive": 'self.chr.alive({ id })'
}

import ast
import chr.ast as chrast
from functools import partial

def compile_alive(id):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Attribute(
                value=ast.Name(id="self"),
                attr="chr"
            ),
            attr="alive"
        ),
        args=[ast.Name(id=id, context=ast.Load())],
        keywords=[]
    )

def compile_all_different(ids):
    return ast.Call(
        func=ast.Name(id="all_different"),
        args=[ast.Name(id=f'id_{id}', context=ast.Load()) for id in ids],
        keywords=[]
    )

def compile_builtin_call(func_id, args):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Attribute(
                value=ast.Name(id="self"),
                attr=builtin
            ),
            attr=func_id
        ),
        args=list(args),
        keywords=[]
    )

def compile_get_value(varname):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=varname, ctx=ast.Load()),
            attr="get_value"
        ),
        args=[],
        keywords=[]
    )

class Emitter:

    def __init__(self):
        self.next_gen_var = 0
        self.known_vars = set()
        self.matchings = {}
        self.indexes = {}


    def add_var(self, var):
        self.known_vars.add(var)


    def gensym(self):
        sym = f'_E{self.next_gen_var}'
        self.next_gen_var += 1
        return sym


    def compile_program(self, program, user_constraints):
        if not isinstance(program, chrast.Program):
            raise TypeError(f'{program} is not an instance of {chrast.Program}')

        processed, _ = program.omega_r()

        print(program.rules)

        defs = [
            self.compile_occurrence(occurrence_scheme)
            for rule in processed.rules
            for occurrence_scheme in rule.get_occurrence_schemes()
        ]

        return ast.Module(body=defs)

    def check_for_ask_constraint(self, param):
        if isinstance(param, chrast.Var) and param.name in self.known_vars:
            return compile_get_value(param.name)
        elif isinstance(param, chrast.Const):
            return ast.Constant(value=param.val, kind=None)
        else:
            raise Exception(f'invalid argument for ask_eq: {param}')


    def check_for_tell_constraint(self, param):
        if isinstance(param, chrast.Var):
            if param.name not in self.known_vars:
                self.add_var(param.name)
            return compile_get_value(param.name)
        elif isinstance(param, chrast.Const):
            return ast.Constant(value=c.paramval, kind=None)
        else:
            raise Exception(f'invalid argument for ask_eq: {param}')


    def compile_guard_constraint(self, c):
        if c.symbol == "ask_eq" and c.arity == 2:
            l = self.check_for_ask_constraint(c.params[0])
            r = self.check_for_ask_constraint(c.params[1])

            return ast.Compare(
                left=l,
                ops=[ast.Eq()],
                comparators=[r]
            )

        elif c.symbol == "tell_eq" and c.arity == 2:
            l = self.check_for_tell_constraint(c.params[0])
            r = self.check_for_tell_constraint(c.params[1])

            return compile_builtin_call(
                "tell_eq",
                [l, r]
            )

        elif c.symbol == "ask_leq" and c.arity == 2:
            l = self.check_for_ask_constraint(c.params[0])
            r = self.check_for_ask_constraint(c.params[1])

            return ast.Compare(
                left=l,
                ops=[ast.LtE()],
                comparators=[r]
            )

        else:
            raise Exception(f'unknown builtin constraint: {c.symbol}/{c.arity}')


    def compile_body(self, i, occurrence_scheme):

        idxs = list(self.indexes.keys())

        guard_check = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=list(map(
                    self.compile_guard_constraint,
                    occurrence_scheme.guard
                ))
            ),
            body=[ast.Pass()],
            orelse=[]
        )

        matching = [
            ast.Assign(
                targets=[ast.Name(id=varname, context=ast.Load())],
                value=ast.Subscript(
                    value=ast.Name(id=f'c_{i}'),
                    slice=ast.Index(value=ast.Constant(value=ix+1, kind=None)),
                    ctx=ast.Load()
                )
            )
            for varname, (i, ix) in self.matchings.items()
        ]

        body = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[
                    compile_alive(f'id_{k}')
                    for k in idxs
                ] + ([compile_all_different(idxs)] if len(idxs) > 1 else [])
            ),
            body=matching + [guard_check],
            orelse=[]
        )

        return body


    def compile_matching(self, i, others, occurrence_scheme):
        if not others:
            return self.compile_body(i, occurrence_scheme)

        (j, c), *cs = others

        self.indexes[j] = c.kept

        for ix, var in enumerate(c.params):
            self.add_var(var)
            self.matchings[var] = (j, ix)

        loop = ast.For(
            target=ast.Tuple(elts=[
                ast.Name(id=f'id_{j}'),
                ast.Name(id=f'c_{j}')
            ]),
            iter=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr="chr"
                    ),
                    attr="get_iterator"
                ),
                args=[],
                keywords=[
                    ast.keyword(
                        arg='symbol',
                        value=ast.Constant(value=f'{c.symbol}/{c.arity}', kind=None)
                    ),
                    ast.keyword(
                        arg='fixed',
                        value=ast.Constant(value=True, kind=None)
                    )
                ]
            ),
            body=[self.compile_matching(i, cs, occurrence_scheme)],
            orelse=[]
        )

        return loop


    def compile_occurrence(self, occurrence_scheme):
        if not isinstance(occurrence_scheme, chrast.OccurrenceScheme):
            raise TypeError(f'{occurrence_scheme} is not an instance of {chrast.OccurrenceScheme}')

        self.known_vars = set()
        self.matchings = {}

        i, c = occurrence_scheme.occurring_constraint

        for var in c.params:
            self.add_var(var)

        self.indexes[i] = c.kept

        args = [ast.arg(arg=f'id_{i}', annotation=None)]
        args += [ast.arg(arg=param, annotation=None) for param in c.params]

        proc = ast.FunctionDef(
            name=f'__{c.symbol}_{c.arity}_{c.occurrence_idx}',
            args=ast.arguments(
                args=args,
                defaults=[],
                vararg=None,
                kwarg=None
            ),
            body=[
                self.compile_matching(
                    i,
                    occurrence_scheme.other_constraints,
                    occurrence_scheme
                ),
                ast.Return(ast.Constant(value=False, kind=None))
            ],
            decorator_list=[]
        )

        return proc
