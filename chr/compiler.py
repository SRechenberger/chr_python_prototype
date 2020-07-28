import ast
import chr.ast as chrast
from chr.parser import chr_parse
from functools import partial
from ast_decompiler import decompile

def comparison(op, args):
    return ast.Compare(
        left = args[0],
        ops=[op],
        comparators=[args[1]]
    )


def compile_self_arg():
    return ast.arg(arg="self", annotation=None)

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

def compile_is_bound(varname):
    print("varname", varname)
    return ast.Call(
        func=ast.Attribute(
            value=varname[0],
            attr="is_bound"
        ),
        args=[],
        keywords=[]
    )


def compile_activate(id, args, symbol):
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="self", ctx=ast.Load()),
            attr=f"__activate_{symbol}"
        ),
        args=[
            ast.Name(id=id, context=ast.Load()),
            *(ast.Name(id=arg, context=ast.Load()) for arg in args)
        ],
        keywords=[]
    ))

ASK_OPS = {
    ("eq", 2): partial(comparison, ast.Eq()),
    ("lt", 2): partial(comparison, ast.Lt()),
    ("leq", 2): partial(comparison, ast.LtE()),
    ("gt", 2): partial(comparison, ast.Gt()),
    ("geq", 2): partial(comparison, ast.GtE()),
    ("neq", 2): partial(comparison, ast.NotEq()),
    ("bound", 1): compile_is_bound
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
    '+': ast.Add(),
    '-': ast.Sub(),
    '*': ast.Mult(),
    '/': ast.Div(),
    '%': ast.Mod()
}

class Emitter:

    def __init__(self, existentials=set()):
        self.next_gen_var = 0
        self.known_vars = set()
        self.matchings = {}
        self.indexes = {}
        self.chr_constraints = None
        self.existential_variables = existentials


    def add_var(self, var):
        self.known_vars.add(var)


    def gensym(self, prefix="E"):
        sym = f'_{prefix}_{self.next_gen_var}'
        self.next_gen_var += 1
        return sym


    def compile_program(self, solver_class_name, program):
        if not isinstance(program, chrast.Program):
            raise TypeError(f'{program} is not an instance of {chrast.Program}')

        self.chr_constraints = set(program.user_constraints)

        processed, _ = program.omega_r()

        print("\n".join(map(str, processed.rules)))

        occs = {
            (symbol, int(arity)): []
            for symbol, arity in map(lambda x:x.split('/'), self.chr_constraints)
        }
        constraints = {
            symbol: set([int(arity)])
            for symbol, arity in map(lambda x:x.split('/'), self.chr_constraints)
        }

        print(constraints)

        for rule in processed.rules:
            defn = [
                self.compile_occurrence(occurrence_scheme)
                for occurrence_scheme in rule.get_occurrence_schemes()
            ]
            print(defn)
            for proc, symb, ar in defn:
                if (symb, ar) in occs:
                    occs[symb,ar].append(proc)
                else:
                    occs[symb,ar] = [proc]

                if symb in constraints:
                    constraints[symb].add(ar)
                else:
                    constraints[symb] = set([ar])

        activations = [
            self.compile_activate_proc(symbol, arity, len(occurrences))
            for (symbol, arity), occurrences in occs.items()
        ]

        occurrences = []

        for occ in occs.values():
            occurrences += occ

        constraint_functions = [
            self.compile_constraint_function(symbol, arities)
            for symbol, arities in constraints.items()
        ]

        return ast.Module(body=[
            ast.ImportFrom(
                module="chr.runtime",
                names=[
                    ast.alias(name="UndefinedConstraintError",asname=None),
                    ast.alias(name="InconsistentBuiltinStoreError", asname=None),
                    ast.alias(name="all_different", asname=None),
                    ast.alias(name="LogicVariable", asname=None),
                    ast.alias(name="CHRFalse", asname=None),
                    ast.alias(name="CHRSolver", asname=None)
                ],
                level=0
            ),
            ast.ClassDef(
                name=solver_class_name,
                body=[
                    *constraint_functions,
                    *activations,
                    *occurrences
                ],
                bases=[ast.Name("CHRSolver")],
                decorator_list=[],
                keywords=[]
            )
        ])


    def compile_constraint_function(self, symbol, valid_arities):
        checks = [
            ast.If(
                test=ast.Compare(
                    left=ast.Call(
                        func=ast.Name(id="len"),
                        args=[ast.Name(id="args")],
                        keywords=[]
                    ),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=valid_arity, kind=None)]
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Name(id="vars")],
                        value=ast.ListComp(
                            elt=ast.IfExp(
                                test=ast.Call(
                                    func=ast.Name(id="isinstance"),
                                    args=[
                                        ast.Name(id="arg"),
                                        ast.Name(id="LogicVariable")
                                    ],
                                    keywords=[]
                                ),
                                body=ast.Name(id="arg"),
                                orelse=compile_builtin_call("fresh",
                                    [],
                                    kwargs=[
                                        ast.keyword(arg="value", value=ast.Name("arg"))
                                    ]
                                )
                            ),
                            generators=[ast.comprehension(
                                target=ast.Name(id="arg"),
                                iter=ast.Name(id="args"),
                                ifs=[],
                                is_async=0
                            )]
                        )
                    ),
                    ast.Assign(
                        targets=[ast.Name(id="new_constraint")],
                        value=ast.Tuple(elts=[
                            ast.Constant(value=f'{symbol}/{valid_arity}', kind=None),
                            ast.Starred(value=ast.Name("vars"))
                        ])
                    ),
                    ast.Assign(
                        targets=[ast.Name(id="new_id")],
                        value=compile_chr_call("new", [])
                    ),
                    ast.Expr(
                        value=compile_chr_call("insert", [
                            ast.Name("new_constraint"),
                            ast.Name("new_id")
                        ])
                    ),
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="self"),
                                attr=f'__activate_{symbol}_{valid_arity}'
                            ),
                            args=[
                                ast.Name(id="new_id"),
                                ast.Starred(value=ast.Name("vars"))
                            ],
                            keywords=[]
                        )
                    ),
                    ast.Return(value=None)
                ],
                orelse=[]
            )
            for valid_arity in valid_arities
        ]

        finish = ast.Raise(
            exc=ast.Call(
                func=ast.Name("UndefinedConstraintError"),
                args=[
                    ast.Constant(value=symbol, kind=None),
                    ast.Call(
                        func=ast.Name(id="len"),
                        args=[ast.Name(id="args")],
                        keywords=[]
                    )
                ],
                keywords=[]
            ),
            cause=None
        )

        return ast.FunctionDef(
            name=symbol,
            args=ast.arguments(
                args=[ast.arg(arg="self", annotation=None)],
                vararg=ast.arg(arg="args", annotation=None),
                kwarg=None,
                defaults=[]
            ),
            body=[
                *checks,
                finish
            ],
            decorator_list=[]
        )

    def compile_activate_proc(self, symbol, arity, occurrences):
        pname = f"__activate_{symbol}_{arity}"
        params = [ 'id', *(f'_{i}' for i in range(0, arity)) ]
        procnames = [
            f'__{symbol}_{arity}_{i}'
            for i in range(0, occurrences)
        ]

        calls = [
            ast.If(
                test=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="self"),
                        attr=procname
                    ),
                    args=[
                        ast.Name(id=param, ctx=ast.Load())
                        for param in params
                    ],
                    keywords=[]
                ),
                body=[ast.Return(value=None)],
                orelse=[]
            )
            for procname in procnames
        ]

        delay = ast.Pass()

        if len(params) > 1:
            delay = ast.If(
                test=ast.BoolOp(op=ast.Or(),
                    values=[
                        ast.UnaryOp(
                            op=ast.Not(),
                            operand=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=param, ctx=ast.Load()),
                                    attr="is_bound"
                                ),
                                args=[],
                                keywords=[]
                            )
                        )
                        for param in params[1:]
                    ]
                ),
                body=[ast.Expr(
                    value=compile_builtin_call("delay", args=[
                        ast.Lambda(
                            args=ast.arguments(args=[], defaults=[], vararg=None, kwarg=None),
                            body=ast.Call(
                                func=ast.Name(id=pname, ctx=ast.Load()),
                                args=[
                                    ast.Name(id=param, ctx=ast.Load())
                                    for param in params
                                ],
                                keywords=[]
                            )
                        ),
                        *(ast.Name(id=param, ctx=ast.Load()) for param in params[1:])
                    ])
                )],
                orelse=[]
            )

        return ast.FunctionDef(
            name=pname,
            args=ast.arguments(
                args=[
                    ast.arg(arg="self", annotation=None),
                    *(ast.arg(arg=param, annotation=None) for param in params)
                ],
                defaults=[],
                vararg=None,
                kwarg=None
            ),
            body=[
                *calls,
                delay
            ],
            decorator_list=[]
        )


    def check_for_ask_constraint(self, param, get_value=False):
        if isinstance(param, chrast.Var) and param.name in self.known_vars:
            if get_value:
                return compile_get_value(param.name)
            return ast.Name(id=param.name, ctx=ast.Load())
        else:
            return ast.Constant(value=param, kind=None)


    def check_for_tell_constraint(self, param, get_value=False):
        if isinstance(param, chrast.Var):
            if param.name not in self.known_vars:
                self.add_var(param.name)
            if get_value:
                return compile_get_value(param.name)
            return ast.Name(id=param.name, ctx=ast.Load())
        else:
            return ast.Constant(value=param, kind=None)


    def compile_term(self, term):
        if isinstance(term, chrast.Term):
            symbol = term.symbol
            arity = len(term.params)
            subterms = []

            for subterm in term.params:
                subterm_eval = self.compile_term(subterm)
                subterms += [subterm_eval]

            if symbol == '-' and arity == 1:
                return ast.UnaryOp(
                    ast.Invert(),
                    operand=subterms[0]
                )
            elif symbol in TERM_OPS and arity == 2:
                return ast.BinOp(
                    left=subterms[0],
                    op=TERM_OPS[symbol],
                    right=subterms[1]
                )
            else:
                raise Exception(f"unknown operator: {symbol}/{arity}")

        elif isinstance(term, chrast.Var):
            return compile_get_value(term.name)

        else:
            return ast.Constant(value=term, kind=None)


    def compile_fresh(self, varname=None, value_ast=None):
        if not varname:
            varname = self.gensym(prefix="local")
        stmt = ast.Assign(
            targets=[ast.Name(id=varname, ctx=ast.Load())],
            value=compile_builtin_call(
                "fresh",
                [],
                kwargs=[ast.keyword(
                    arg='value',
                    value=value_ast
                )] if value_ast else []
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

        return TELL_OPS[symbol, arity](prepared_params)


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


    def compile_body_constraint(self, c):
        symbol = c.symbol
        params = c.params

        inits = []
        vars = []


        for param in params:
            if isinstance(param, chrast.Var):
                vars.append(param.name)
            else:
                value_ast = self.compile_term(param)
                var, init = self.compile_fresh(value_ast=value_ast)

                inits += [init]
                vars.append(var)
                self.known_vars.add(var)

        if symbol == "false":
            false_stmt = ast.Raise(
                exc=ast.Call(
                    func=ast.Name(id="CHRFalse"),
                    args=[compile_get_value(var) for var in vars],
                    keywords=[]
                ),
                cause=None
            )

            return [*inits, false_stmt], None, None

        if c.signature in self.chr_constraints:
            new_id = self.gensym(prefix="fresh_id")
            new_id_stmt = ast.Assign(
                targets=[ast.Name(id=new_id, ctx=ast.Load())],
                value=compile_chr_call("new", [])
            )
            new_constr = self.gensym(prefix="fresh_constr")
            new_constr_stmt = ast.Assign(
                targets=[ast.Name(id=new_constr, ctx=ast.Load())],
                value=ast.Tuple(elts=[
                    ast.Constant(value=c.signature, kind=None),
                    *[ast.Name(id=var) for var in vars]
                ])
            )

            insert_stmt = ast.Expr(
                value=compile_chr_call(
                    "insert",
                    [ast.Name(id=new_constr),ast.Name(id=new_id)]
                )
            )

            return [*inits, new_id_stmt, new_constr_stmt, insert_stmt], new_id, [ast.Name(id=var) for var in vars]

        new_builtin_constraint = chrast.Constraint(symbol, list(map(chrast.Var, vars)))

        builtin_stmt = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=self.compile_guard_constraint(new_builtin_constraint)
            ),
            body=[
                ast.Expr(value=compile_builtin_call("set_inconsistent", args=[])),
                ast.Raise(
                    exc=ast.Call(
                        func=ast.Name("CHRFalse", ctx=ast.Load()),
                        args=[
                            ast.Constant(value=c.signature, kind=None),
                            *(
                                ast.Call(
                                    func=ast.Name(id="str"),
                                    args=[ast.Name(id=vname)],
                                    keywords=[]
                                )
                                for vname in vars
                            )
                        ],
                        keywords=[]
                    ),
                    cause=None
                ),
            ],
            orelse=[]
        )

        return [*inits, builtin_stmt], None, None


    def compile_guard_constraint(self, c):
        cat, symbol = c.symbol.split('_')

        if cat == 'ask':
            return self.compile_ask_constraint(symbol, c.params)
        elif cat == 'tell':
            return self.compile_tell_constraint(symbol, c.params)


    def compile_body(self, i, occurrence_scheme):

        idxs = list(self.indexes.keys())

        body = []

        body_constraints = (
            c for c in occurrence_scheme.body
        )

        activates = []

        for constr in body_constraints:
            compiled_constr, new_id, constr_args = self.compile_body_constraint(constr)
            body += compiled_constr
            if constr.signature in self.chr_constraints:
                activates += [compile_activate(
                    new_id,
                    constr_args,
                    f'{constr.symbol}_{constr.arity}'
                )]


        history_entry = (
            occurrence_scheme.rule_name,
            [f'id_{ix}' for ix in idxs]
        )

        kills = [
            ast.Expr(value=compile_delete(f'id_{id}'))
            for id, kept in self.indexes.items()
            if not kept
        ]

        terminate = ast.Return(
            value=ast.Constant(value=True, kind=None)
        )

        if occurrence_scheme.occurring_constraint[1].kept:
            terminate = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=compile_alive(f"id_{i}")
                ),
                body=[terminate],
                orelse=[]
            )

        history_check = ast.UnaryOp(
            op=ast.Not(),
            operand=compile_in_history(*history_entry)
        )


        guard_check = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[
                    *(
                        self.compile_guard_constraint(guard_constraint)
                        for guard_constraint in occurrence_scheme.guard
                    ),
                    history_check
                ]
            ),
            body=[
                ast.Expr(value=compile_builtin_call("commit", args=[])),
                ast.Expr(value=compile_add_to_history(*history_entry)),
                *kills,
                *body,
                *activates,
                terminate
            ],
            orelse=[
                ast.Expr(value=compile_builtin_call("backtrack", args=[]))
            ]
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

        print("FREE VARS", occurrence_scheme.free_vars())

        init_local_vars = [
            self.compile_fresh(varname=var)[1]
            for var in occurrence_scheme.free_vars()
        ]

        body = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[
                    compile_alive(f'id_{k}')
                    for k in idxs
                ] + ([compile_all_different(idxs)] if len(idxs) > 1 else [])
            ),
            body=matching + init_local_vars + [guard_check],
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
                        arg='fix',
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
        self.next_gen_var = 0
        self.indexes = {}

        i, c = occurrence_scheme.occurring_constraint

        for var in c.params:
            self.add_var(var)

        self.indexes[i] = c.kept

        args = [ast.arg(arg=f'id_{i}', annotation=None)]
        args += [ast.arg(arg=param, annotation=None) for param in c.params]

        procname = f'__{c.symbol}_{c.arity}_{c.occurrence_idx}'

        proc = ast.FunctionDef(
            name=procname,
            args=ast.arguments(
                args=[ast.arg(arg="self", annotation=None), *args],
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

        return proc, c.symbol, c.arity


def chr_compile(solver_class_name, source, target_file=None):
    chr_ast = chr_parse(source).get_normal_form()
    e = Emitter()
    python_ast = e.compile_program(solver_class_name, chr_ast)
    python_code = decompile(python_ast)
    if not target_file:
        return python_code

    with open(target_file, 'w') as f:
        f.write(python_code)
