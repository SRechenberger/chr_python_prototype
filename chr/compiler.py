import ast
from functools import partial

from ast_decompiler import decompile

import chr.ast as chrast
from chr.parser import chr_parse


def comparison(op, args):
    return ast.Compare(
        left=args[0],
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


def compile_builtin_call(func_id, args, kwargs=None):
    if kwargs is None:
        kwargs = []
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


def compile_get_value(var_ast):
    return ast.Call(
        func=ast.Name(
            id="get_value"
        ),
        args=[var_ast],
        keywords=[]
    )


def compile_is_bound(varname):
    return ast.Call(
        func=ast.Attribute(
            value=varname[0],
            attr="is_bound"
        ),
        args=[],
        keywords=[]
    )


def compile_activate(index, args, symbol):
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="self", ctx=ast.Load()),
            attr=f"__activate_{symbol}"
        ),
        args=[
            ast.Name(id=index, context=ast.Load()),
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
    ("eq", 2): (False, False),
    ("lt", 2): (True, True),
    ("leq", 2): (True, True),
    ("gt", 2): (True, True),
    ("geq", 2): (True, True),
    ("neq", 2): (False, False),
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


def compile_activate_proc(symbol, arity, occurrences):
    pname = f"__activate_{symbol}_{arity}"
    params = ['id', *(f'_{i}' for i in range(0, arity))]
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
            body=[ast.Return(value=ast.Constant(value=True, kind=None))],
            orelse=[]
        )
        for procname in procnames
    ]

    delay = ast.Pass()

    if len(params) > 1:
        bound_checks = []
        for param in params[1:]:
            bound_checks.append(
                ast.BoolOp(op=ast.And(), values=[
                    ast.Call(
                        func=ast.Name(id="isinstance"),
                        args=[
                            ast.Name(id=param),
                            ast.Name(id="LogicVariable")
                        ],
                        keywords=[]
                    ),
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
                ])
            )

        delay = ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[
                    ast.UnaryOp(op=ast.Not(), operand=ast.Name(id="delayed")),
                    ast.BoolOp(op=ast.Or(),
                               values=bound_checks
                               )
                ]
            ),
            body=[ast.Expr(
                value=compile_builtin_call("delay", args=[
                    ast.Lambda(
                        args=ast.arguments(args=[], defaults=[], vararg=None, kwarg=None),
                        body=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr=pname
                            ),
                            args=[
                                ast.Name(id=param, ctx=ast.Load())
                                for param in params
                            ],
                            keywords=[
                                ast.keyword(
                                    arg="delayed",
                                    value=ast.Constant(value=True, kind=None)
                                )
                            ]
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
                *(ast.arg(arg=param, annotation=None) for param in params),
                ast.arg(arg="delayed", annotation=None)
            ],
            defaults=[ast.Constant(value=False, kind=None)],
            vararg=None,
            kwarg=None
        ),
        body=[
            *calls,
            delay,
            ast.Return(value=ast.Constant(value=False, kind=None))
        ],
        decorator_list=[]
    )


def compile_constraint_function(symbol, valid_arities):
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


def compile_term(term, known_vars):
    if isinstance(term, chrast.Term):
        symbol = term.symbol
        arity = len(term.params)
        subterms = []

        for subterm in term.params:
            subterm_eval = compile_term(subterm, known_vars)
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

    if isinstance(term, chrast.Var):
        if not known_vars[term.name]:
            known_vars[term.name] = ast.Name(id=term.name)
        return compile_get_value(known_vars[term.name])

    if isinstance(term, list):
        return ast.List(elts=[
            compile_term(subterm, known_vars)
            for subterm in term
        ])

    if isinstance(term, tuple):
        return ast.Tuple(elts=[
            compile_term(subterm, known_vars)
            for subterm in term
        ])

    if isinstance(term, dict):
        return ast.List(keys=[
            *term.keys()
        ], values=[
            compile_term(val, known_vars)
            for val in term.values()
        ])

    return ast.Constant(value=term, kind=None)


def check_for_ask_constraint(param, known_vars, get_value=False):
    if isinstance(param, chrast.Var):
        if get_value:
            return compile_get_value(known_vars[param.name])
        return known_vars[param.name]
    if isinstance(param, tuple):
        return ast.Tuple(elts=[
            check_for_ask_constraint(subterm, known_vars, get_value=get_value)
            for subterm in param
        ])
    if isinstance(param, list):
        return ast.List(elts=[
            check_for_ask_constraint(subterm, known_vars, get_value=get_value)
            for subterm in param
        ])
    if isinstance(param, dict):
        ks, vs = zip(*(
            (
                compile_term(key, known_vars),
                check_for_ask_constraint(val, known_vars, get_value=get_value)
            )
            for key, val in param.items()
        ))
        return ast.Dict(keys=ks, values=vs)

    return ast.Constant(value=param, kind=None)


def check_for_tell_constraint(param, known_vars, get_value=False):
    if isinstance(param, chrast.Var):
        if param.name not in known_vars:
            var_ast = ast.Name(id=param.name, ctx=ast.Load())
            known_vars[param.name] = var_ast
        else:
            var_ast = known_vars[param.name]
        if get_value:
            return compile_get_value(known_vars[param.name])
        return var_ast

    if isinstance(param, tuple):
        return ast.Tuple(elts=[
            check_for_tell_constraint(subterm, known_vars, get_value=get_value)
            for subterm in param
        ])
    if isinstance(param, list):
        return ast.List(elts=[
            check_for_tell_constraint(subterm, known_vars, get_value=get_value)
            for subterm in param
        ])
    if isinstance(param, dict):
        ks, vs = zip(*(
            (
                compile_term(key, known_vars),
                check_for_tell_constraint(val, known_vars, get_value=get_value)
            )
            for key, val in param.items()
        ))
        return ast.Dict(keys=ks, values=vs)

    return ast.Constant(value=param, kind=None)


def compile_tell_constraint(symbol, params, known_vars):
    arity = len(params)
    if (symbol, arity) not in TELL_OPS:
        raise Exception(f'unknown symbol: {symbol}/{arity}')

    prepared_params = [
        check_for_tell_constraint(param, known_vars, get_value=force_ground)
        for param, force_ground
        in zip(params, TELL_OPS_GROUNDNESS[symbol, arity])
    ]

    return TELL_OPS[symbol, arity](prepared_params)


def compile_ask_constraint(symbol, params, known_vars):
    arity = len(params)
    if (symbol, arity) not in ASK_OPS:
        raise Exception(f'unknown symbol: {symbol}/{arity}')

    prepared_params = [
        check_for_ask_constraint(param, known_vars, get_value=force_ground)
        for param, force_ground
        in zip(params, ASK_OPS_GROUNDNESS[symbol, arity])
    ]
    result = ASK_OPS[symbol, arity](prepared_params)
    return result


def compile_guard_constraint(c, known_vars):
    cat, symbol = c.symbol.split('_')

    if cat == 'ask':
        return compile_ask_constraint(symbol, c.params, known_vars)
    elif cat == 'tell':
        return compile_tell_constraint(symbol, c.params, known_vars)


def compile_destructuring(value_ast, pattern, known_vars):
    if isinstance(pattern, chrast.Var):
        if pattern.name in known_vars:
            if known_vars[pattern.name]:
                return [
                           ast.Compare(
                               left=known_vars[pattern.name],
                               ops=[ast.Eq()],
                               comparators=[value_ast]
                           )
                       ], []
            else:
                known_vars[pattern.name] = value_ast
                return [], []

        known_vars[pattern.name] = value_ast
        return [], [
            ast.Assign(
                targets=ast.Name(id=pattern.name),
                value=value_ast
            )
        ]

    val_bound = ast.Call(
        func=ast.Name(id="is_bound"),
        args=[value_ast],
        keywords=[]
    )

    if isinstance(pattern, (tuple, list, dict)):

        iter = enumerate(pattern) if isinstance(pattern, (tuple, list)) else pattern.items()

        checks, stmts = [], []

        if isinstance(pattern, (tuple, list)):
            checks.append(
                ast.Compare(
                    left=ast.Call(func=ast.Name(id="len"), args=[
                        compile_get_value(value_ast)
                    ], keywords=[]),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=len(pattern), kind=None)]
                )
            )

        else:
            checks += [
                ast.Compare(
                    left=ast.Constant(value=key, kind=None),
                    ops=[ast.In()],
                    comparators=[compile_get_value(value_ast)]
                )
                for key in pattern.keys()
            ]

        for key, subpattern in iter:
            check, stmt = compile_destructuring(
                ast.Subscript(
                    value=value_ast,
                    slice=ast.Index(value=ast.Constant(
                        value=key,
                        kind=None
                    ))
                ),
                subpattern,
                known_vars
            )

            checks += check
            stmts += stmt

        return [
                   val_bound,
                   ast.Call(
                       func=ast.Name(id="isinstance"),
                       args=[
                           compile_get_value(value_ast),
                           ast.Name(id=type(pattern).__name__),
                       ],
                       keywords=[]
                   ),
                   *checks
               ], stmts

    return [
               val_bound,
               ast.Compare(
                   left=value_ast,
                   ops=[ast.Eq()],
                   comparators=[ast.Constant(value=pattern, kind=None)]
               )
           ], []


class Emitter:

    def __init__(self, existentials=None):
        if existentials is None:
            existentials = set()
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

        processed = program

        occs = {
            (symbol, int(arity)): []
            for symbol, arity in map(lambda x: x.split('/'), self.chr_constraints)
        }
        constraints = {
            symbol: {int(arity)}
            for symbol, arity in map(lambda x: x.split('/'), self.chr_constraints)
        }

        for rule in processed.rules:
            defn = [
                self.compile_occurrence(occurrence_scheme)
                for occurrence_scheme in rule.get_occurrence_schemes()
            ]
            for proc, symb, ar in defn:
                if (symb, ar) in occs:
                    occs[symb, ar].append(proc)
                else:
                    occs[symb, ar] = [proc]

                if symb in constraints:
                    constraints[symb].add(ar)
                else:
                    constraints[symb] = {ar}

        activations = [
            compile_activate_proc(symbol, arity, len(occurrences))
            for (symbol, arity), occurrences in occs.items()
        ]

        occurrences = []

        for occ in occs.values():
            occurrences += occ

        constraint_functions = [
            compile_constraint_function(symbol, arities)
            for symbol, arities in constraints.items()
        ]

        return ast.Module(body=[
            ast.ImportFrom(
                module="chr.runtime",
                names=[
                    ast.alias(name="UndefinedConstraintError", asname=None),
                    ast.alias(name="InconsistentBuiltinStoreError", asname=None),
                    ast.alias(name="all_different", asname=None),
                    ast.alias(name="LogicVariable", asname=None),
                    ast.alias(name="CHRFalse", asname=None),
                    ast.alias(name="CHRSolver", asname=None),
                    ast.alias(name="get_value", asname=None),
                    ast.alias(name="is_bound", asname=None),
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

    def compile_body_constraint(self, c, known_vars):
        symbol = c.symbol
        params = c.params

        inits = []
        variables = []

        for param in params:
            if isinstance(param, chrast.Var):
                variables.append(param.name)
                if param.name not in known_vars or not known_vars[param.name]:
                    known_vars[param.name] = ast.Name(id=param.name)
                    inits.append(self.compile_fresh(varname=param.name)[1])
            else:
                value_ast = compile_term(param, known_vars)
                var, init = self.compile_fresh(value_ast=value_ast)

                inits += [init]
                variables.append(var)
                known_vars[var] = ast.Name(id=var)

        if symbol == "false":
            false_stmt = ast.Raise(
                exc=ast.Call(
                    func=ast.Name(id="CHRFalse"),
                    args=[compile_get_value(known_vars[var]) for var in variables],
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
                    *[known_vars[var] for var in variables]
                ])
            )

            insert_stmt = ast.Expr(
                value=compile_chr_call(
                    "insert",
                    [ast.Name(id=new_constr), ast.Name(id=new_id)]
                )
            )

            return [*inits, new_id_stmt, new_constr_stmt, insert_stmt], new_id, [known_vars[var] for var in variables]

        new_builtin_constraint = chrast.Constraint(symbol, list(map(chrast.Var, variables)))

        builtin_stmt = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=compile_guard_constraint(new_builtin_constraint, known_vars)
            ),
            body=[
                ast.Raise(
                    exc=ast.Call(
                        func=ast.Name("CHRFalse", ctx=ast.Load()),
                        args=[
                            ast.Constant(value=c.signature, kind=None),
                            *(
                                ast.Call(
                                    func=ast.Name(id="str"),
                                    args=[known_vars[vname]],
                                    keywords=[]
                                )
                                for vname in variables
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

    def compile_body(self, total_heads, known_vars, removed_ids, occurrence_scheme):

        ids = [f'id_{i}' for i in range(0, total_heads)]

        to_return = ast.If(
            test=ast.BoolOp(op=ast.And(), values=[
                compile_alive(id)
                for id in ids
            ]),
            orelse=[]
        )

        guarded_body = ast.If(
            test=ast.BoolOp(op=ast.And(), values=[
                compile_guard_constraint(c, known_vars)
                for c in occurrence_scheme.guard
            ]),
            orelse=[ast.Expr(value=compile_builtin_call("backtrack", []))]
        )

        to_return.body = [guarded_body]

        kills = [ast.Expr(value=compile_delete(id)) for id in removed_ids]

        body_constraints = []

        for c in occurrence_scheme.body:
            stmts, new_id, args = self.compile_body_constraint(c, known_vars)
            body_constraints += stmts
            body_constraints.append(ast.Expr(value=compile_builtin_call("commit", [])))
            if new_id and args:
                body_constraints.append(compile_activate(new_id, args, f'{c.symbol}_{c.arity}'))

        finalize = ast.Return(value=ast.Constant(value=True, kind=None))

        if occurrence_scheme.occurring_constraint[1].kept:
            finalize = ast.If(
                test=ast.UnaryOp(op=ast.Not(), operand=compile_alive("id_0")),
                orelse=[],
                body=[finalize]
            )

        history_checked_body = ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=compile_in_history(occurrence_scheme.rule_name, ids)),
            orelse=[],
            body=[
                ast.Expr(value=compile_add_to_history(occurrence_scheme.rule_name, ids)),
                *kills,
                *body_constraints,
                ast.Expr(value=compile_builtin_call("commit", [])),
                finalize
            ]
        )

        if occurrence_scheme.guard:
            guarded_body.body = [history_checked_body]

        else:
            to_return.body = [history_checked_body]

        return to_return

    def compile_matching_loops(self, i, head_constraints, matchings, known_vars, removed_ids, occurrence_scheme):
        if not head_constraints:
            if matchings:
                raise Exception(f"there are still unchecked matchings: {matchings}")
            return self.compile_body(i, known_vars, removed_ids, occurrence_scheme)

        current = head_constraints[0][1]

        symbol = current.symbol
        arg_vars = current.params
        arity = current.arity

        id_string = f'id_{i}'
        c_string = f'c_{i}'

        if not current.kept:
            removed_ids.add(id_string)

        known_vars.update(
            dict(zip(arg_vars, [
                ast.Subscript(
                    value=ast.Name(id=c_string),
                    slice=ast.Index(value=ast.Constant(value=j + 1, kind=None))
                )
                for j in range(0, arity)
            ]))
        )

        checks = [compile_all_different(range(0, i + 1))]
        destructs = []
        uncheckable_matchings = []

        for matching in matchings:
            if all(v in known_vars for v in chrast.vars(matching)):
                check, destruct = compile_destructuring(
                    known_vars[matching.params[0].name],
                    matching.params[1],
                    known_vars
                )
                checks += check
                destructs += destruct
            else:
                uncheckable_matchings.append(matching)

        check_and_destr = self.compile_matching_loops(
            i + 1,
            head_constraints[1:],
            uncheckable_matchings,
            known_vars,
            removed_ids,
            occurrence_scheme
        )
        if checks:
            check_and_destr = ast.If(
                test=ast.BoolOp(op=ast.And(), values=checks),
                orelse=[ast.Expr(value=compile_builtin_call("backtrack", []))],
                body=[
                    *destructs,
                    check_and_destr
                ]
            )

        matching_loop = ast.For(
            target=ast.Tuple(elts=[
                ast.Name(id=id_string),
                ast.Name(id=c_string)
            ]),
            iter=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="self"),
                        attr="chr"
                    ),
                    attr="get_iterator"
                ),
                args=[],
                keywords=[
                    ast.keyword(arg="symbol", value=ast.Constant(
                        value=f'{symbol}/{arity}',
                        kind=None
                    )),
                    ast.keyword(arg="fix", value=ast.Constant(value=True, kind=None))
                ]
            ),
            body=[check_and_destr],
            orelse=[]
        )

        return matching_loop

    def compile_occurrence(self, occurrence_scheme):
        _, current = occurrence_scheme.occurring_constraint
        heads = occurrence_scheme.other_constraints
        matchings = occurrence_scheme.matching

        symbol = current.symbol
        arity = current.arity
        variables = current.params
        idx = current.occurrence_idx
        current_index = 'id_0'

        removed_ids = set()

        if not current.kept:
            removed_ids.add(current_index)

        known_vars = {
            **{var: ast.Name(id=var) for var in variables},
            **{var: None for var in occurrence_scheme.free_vars()}
        }

        checks, destructs = [], []
        uncheckable_matchings = []

        for matching in matchings:
            if all(v in known_vars for v in chrast.vars(matching)):
                check, destruct = compile_destructuring(
                    known_vars[matching.params[0].name],
                    matching.params[1],
                    known_vars
                )
                checks += check
                destructs += destruct
            else:
                uncheckable_matchings.append(matching)

        check_and_destr = [
            *destructs,
            self.compile_matching_loops(
                1,
                heads,
                uncheckable_matchings,
                known_vars,
                removed_ids,
                occurrence_scheme
            )
        ]

        if checks:
            check_and_destr = [ast.If(
                test=ast.BoolOp(op=ast.And(), values=checks),
                orelse=[ast.Expr(value=compile_builtin_call("backtrack", []))],
                body=check_and_destr
            )]

        args = [ast.arg(arg=current_index, annotation=None)]
        args += [ast.arg(arg=param, annotation=None) for param in current.params]

        procname = f'__{symbol}_{arity}_{idx}'
        proc = ast.FunctionDef(
            name=procname,
            args=ast.arguments(
                args=[ast.arg(arg="self", annotation=None), *args],
                defaults=[],
                vararg=None,
                kwarg=None
            ),
            body=[
                *check_and_destr,
                ast.Return(ast.Constant(value=False, kind=None))
            ],
            decorator_list=[]
        )

        return proc, symbol, arity


def chr_compile(solver_class_name, source, target_file=None):
    chr_ast, _ = chr_parse(source).get_normal_form().omega_r()
    e = Emitter()
    python_ast = e.compile_program(solver_class_name, chr_ast)
    python_code = decompile(python_ast)
    if not target_file:
        return python_code

    with open(target_file, 'w') as f:
        f.write(python_code)
