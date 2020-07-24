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


def comparison(op, args):
    return ast.Compare(
        left = args[0],
        ops=[op],
        comparators=[args[1]]
    )




def compile_all_different(ids):
    return ast.Call(
        func=ast.Name(id="all_different"),
        args=[ast.Name(id=f'id_{id}', context=ast.Load()) for id in ids],
        keywords=[]
    )


def compile_chr_call(func_id, args):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Attribute(
                value=ast.Name(id="self"),
                attr="chr"
            ),
            attr=func_id
        ),
        args=list(args),
        keywords=[]
    )

def compile_alive(id):
    return compile_chr_call(
        "alive",
        [ast.Name(id=id, context=ast.Load())]
    )

def compile_builtin_call(func_id, args, kwargs=[]):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Attribute(
                value=ast.Name(id="self"),
                attr="builtin"
            ),
            attr=func_id
        ),
        args=list(args),
        keywords=kwargs
    )

def compile_in_history(rule_id, ids):
    return compile_chr_call(
        "in_history",
        [ast.Constant(value=rule_id, kind=None)] + \
        [ast.Name(id=id, context=ast.Load()) for id in ids]
    )

def compile_add_to_history(rule_id, ids):
    return compile_chr_call(
        "add_to_history",
        [ast.Constant(value=rule_id, kind=None)] + \
        [ast.Name(id=id, context=ast.Load()) for id in ids]
    )

def compile_delete(id):
    return compile_chr_call(
        "delete",
        [ast.Name(id=id, context=ast.Load())]
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


ASK_OPS = {
    ("eq", 2): partial(comparison, ast.Eq()),
    ("lt", 2): partial(comparison, ast.Lt()),
    ("leq", 2): partial(comparison, ast.LtE()),
    ("gt", 2): partial(comparison, ast.Gt()),
    ("geq", 2): partial(comparison, ast.GtE()),
    ("neq", 2): partial(comparison, ast.NotEq()),
    ("bound", 1): partial(compile_builtin_call, "is_bound")
}

ASK_OPS_GROUNDNESS = {
    ("eq", 2): (True, True),
    ("lt", 2): (True, True),
    ("leq", 2): (True, True),
    ("gt", 2): (True, True),
    ("geq", 2): (True, True),
    ("neq", 2): (True, True),
    ("bound", 1): (False,)
}

TELL_OPS = {
    ("eq", 2): partial(compile_builtin_call, "tell_eq")
}

TELL_OPS_GROUNDNESS = {
    ("eq", 2): (False, False)
}

TERM_OPS = {
    '+': ast.Add,
    '-': ast.Sub,
    '*': ast.Mult,
    '/': ast.Div,
    '%': ast.Mod
}

class Emitter:

    def __init__(self):
        self.next_gen_var = 0
        self.known_vars = set()
        self.matchings = {}
        self.indexes = {}


    def add_var(self, var):
        self.known_vars.add(var)


    def gensym(self, prefix="E"):
        sym = f'_{prefix}_{self.next_gen_var}'
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


    def check_for_ask_constraint(self, param, get_value=False):
        if isinstance(param, chrast.Var) and param.name in self.known_vars:
            if get_value:
                return compile_get_value(param.name)
            return ast.Name(id=param.name, ctx=ast.Load())
        elif isinstance(param, chrast.Const):
            return ast.Constant(value=param.val, kind=None)
        else:
            raise Exception(f'invalid argument for ask_eq: {param}')


    def check_for_tell_constraint(self, param, get_value=False):
        if isinstance(param, chrast.Var):
            if param.name not in self.known_vars:
                self.add_var(param.name)
            if get_value:
                return compile_get_value(param.name)
            return ast.Name(id=param.name, ctx=ast.Load())
        elif isinstance(param, chrast.Const):
            return ast.Constant(value=c.val, kind=None)
        else:
            raise Exception(f'invalid argument for ask_eq: {param}')


    def compile_term(self, term):
        if isinstance(term, chrast.Term):
            symbol = term.symbol
            arity = len(term.params)
            subterms = []

            for subterm in term.params:
                subterm = self.compile_term(subterm)
                subterms += subterm_eval

            if symbol == '-' and arity == 1:
                return ast.UnaryOp(
                    ast.Invert(),
                    operand=ast.Name(id=subterm_vars[0], ctx=ast.Load())
                )
            elif symbol in TERM_OPS and arity == 2:
                return ast.BinOp(
                    left=ast.Name(id=subterm_vars[0], ctx=ast.Load()),
                    op=TERM_OPS[symbol],
                    right=ast.Name(id=subterm_vars[1], ctx=ast.Load())
                )
            else:
                raise Exception(f"unknown operator: {symbol}/{arity}")

        elif isinstance(term, chrast.Var):
            return compile_get_value(term.name)

        elif isinstance(term, chrast.Const):
            return ast.Constant(value=term.val, kind=None)


        raise TypeError(f'not a valid term: {term}')


    def compile_fresh(self, value_ast=None):
        varname = self.gensym(prefix="local")
        stmt = ast.Assign(
            targets=[ast.Name(id=varname, ctx=ast.Load())],
            value=compile_builtin_call(
                "fresh",
                [],
                kwargs={"value": value_ast} if value else []
            )
        )
        return varname, stmt


    def compile_tell_constraint(self, symbol, params):
        arity = len(params)
        if (symbol, arity) not in TELL_OPS:
            raise Exception(f'unknown symbol: {symbol}/{arity}')

        prepared_params = [
            self.check_for_tell_constraint(param, get_value=force_ground)
            for param, force_ground
            in zip(params, TELL_OPS_GROUNDNESS[symbol, arity])
        ]

        return TELL_OPS[symbol, params](prepared_params)


    def compile_ask_constraint(self, symbol, params):
        arity = len(params)
        if (symbol, arity) not in ASK_OPS:
            raise Exception(f'unknown symbol: {symbol}/{arity}')

        prepared_params = [
            self.check_for_ask_constraint(param, get_value=force_ground)
            for param, force_ground
            in zip(params, ASK_OPS_GROUNDNESS[symbol, arity])
        ]
        result = ASK_OPS[symbol, arity](prepared_params)
        return result


    def compile_body_chr_constraint(self, c):
        symbol = c.symbol
        params = c.params

        inits = []
        vars = []

        for param in params:
            value_ast = self.compile_term(param)
            var, init = self.compile_fresh(value_ast=value_ast)

            inits += init
            vars.append(var)

        id = self.gensym(prefix="fresh_id")
        new_id_stmt = ast.Assign(
            target=ast.Name(id=id, ctx=ast.Load()),
            value=compile_chr_call("new", [])
        )
        constr = self.gensym(prefix="fresh_constr")
        new_constr_stmt = ast.Assign(
            target=ast.Name(id=new_constr, ctx=ast.Load()),
            value=ast.Tuple(elts=[
                ast.Constant(value=symbol),
                *[ast.Name(id=var) for var in vars]
            ])
        )

        insert_stmt = ast.Expr(
            value=compile_chr_call(
                "insert",
                [ast.Name(id=constr), ast.Name(id=id)]
            )
        )

        return [*inits, new_id_stmt, new_constr_stmt, insert_stmt]






    def compile_guard_constraint(self, c):
        cat, symbol = c.symbol.split('_')

        if cat == 'ask':
            return self.compile_ask_constraint(symbol, c.params)
        elif cat == 'tell':
            return self.compile_tell_constraint(symbol, c.params)


    def compile_body(self, i, occurrence_scheme):

        idxs = list(self.indexes.keys())

        history_entry = (
            occurrence_scheme.rule_name,
            [f'id_{ix}' for ix in idxs]
        )

        kills = [
            ast.Expr(value=compile_delete(f'id_{id}'))
            for id, kept in self.indexes.items()
            if not kept
        ]

        history_check = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=compile_in_history(*history_entry)
            ),
            body=[
                ast.Expr(value=compile_add_to_history(*history_entry)),
                *kills
            ],
            orelse=[]
        )

        guard_check = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=list(map(
                    self.compile_guard_constraint,
                    occurrence_scheme.guard
                ))
            ),
            body=[history_check],
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
