import ast
from typing import List, Dict, Any, Tuple, Set, Union, Callable

from ast_decompiler import decompile

from chr.ast import *
from chr.parser import chr_parse

Statement = Union[
    ast.FunctionDef,
    ast.Return,
    ast.Assign,
    ast.For,
    ast.If,
    ast.Raise,
    ast.Expr,
    ast.Try,
    ast.Pass
]

Expression = Union[
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Lambda,
    ast.IfExp,
    ast.Dict,
    ast.Set,
    ast.List,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Compare,
    ast.Call,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.Starred,
    ast.Name,
    ast.List,
    ast.Tuple
]

Operator = Union[
    ast.Add, ast.Sub, ast.Mult, ast.MatMult, ast.Div, ast.Mod, ast.Pow,
    ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd, ast.FloorDiv
]

BoolOp = Union[ast.And, ast.Or]

UnaryOp = Union[ast.Invert, ast.Not, ast.UAdd, ast.USub]

CmpOp = Union[
    ast.Eq, ast.NotEq,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn
]

BUILTIN_TYPES = {
    "int",
    "str",
    "bool",
    "dict",
    "set",
    "list",
    "tuple",
    "range",
    "float",
    "complex",
    "frozenset",
    "bytes",
    "bytearray",
    "memoryview"
}


class CHRCompilationError(RuntimeError):
    def __init__(self, message):
        self.message = message


class NameGenerator:
    """Capsules generation of fresh variable names for code generation"""

    def __init__(self):
        self.known_prefixes = {}
        self.names = set()

    def new_name(self, prefix: str = "G") -> str:
        """Generate a new string with the format
            `_PREFIX_I`
        where PREFIX is the given prefix, and I is the number of uses of the prefix.
        """
        if prefix not in self.known_prefixes:
            self.known_prefixes[prefix] = 0

        index = self.known_prefixes[prefix]
        self.known_prefixes[prefix] += 1

        new_name = f'_{prefix}{index}'
        self.names.add(new_name)
        return new_name


def gen_call(
        func: Union[str, Expression],
        *args: Expression,
        **kwargs: Expression
) -> ast.Call:
    """Returns a Call-statement ast, with given function ast"""
    return ast.Call(
        func=gen_name(func) if type(func) is str else func,
        args=list(args),
        keywords=[ast.keyword(arg=key, value=val) for key, val in kwargs.items()]
    )


def gen_attribute(value: Expression, *attrs: str) -> ast.Attribute:
    """Generates an Attribute-node, with
        `gen_attribute(x, a1, a2, ..., an) == ast_of(x.a1.a2.....an)`
    """
    to_return = value
    for attr in attrs:
        to_return = ast.Attribute(
            value=to_return,
            attr=attr,
            context=ast.Load()
        )
    return to_return


def gen_not(expr: Expression) -> ast.UnaryOp:
    return ast.UnaryOp(
        op=ast.Not(),
        operand=expr
    )


def gen_raise_on_false(
        exception_ast: Expression,
        *condition_asts: Expression
) -> Statement:
    """Generates statement of the form
        `if not C: raise E`
    """
    return ast.If(
        test=ast.UnaryOp(
            op=ast.Not(),
            operand=ast.BoolOp(op=ast.And(), values=condition_asts) if len(condition_asts) > 1 else condition_asts[0]
        ),
        orelse=[],
        body=[ast.Raise(
            exc=exception_ast,
            cause=None
        )]
    )


def gen_raise(exception_ast: Expression) -> Statement:
    """Generates raise statement"""

    return ast.Raise(exc=exception_ast, cause=None)


def gen_assign(
        targets: List[Expression],
        value: Expression
) -> ast.Assign:
    """Generates an Assignment-node"""
    return ast.Assign(
        targets=targets if len(targets) > 1 else [targets[0]],
        value=value
    )


def gen_new_call(var_name: str) -> ast.Assign:
    return gen_assign(
        [gen_name(var_name)],
        gen_call(gen_attribute(gen_self(), "chr", "new"))
    )


def gen_insert_call(index_var: str, constraint_var: str) -> Statement:
    return gen_expr(gen_call(
        gen_attribute(gen_self(), "chr", "insert"),
        gen_name(index_var),
        gen_name(constraint_var)
    ))


def gen_activate_call(index_var: str, symbol: str, arity: int, *args: Expression) -> Statement:
    return gen_expr(gen_call(
        gen_attribute(gen_self(), f'__activate_{symbol}_{arity}'),
        gen_name(index_var),
        *args
    ))


def gen_self() -> ast.Name:
    """Generates a Name-node, with id=self"""
    return ast.Name(id="self", context=ast.Load())


def gen_name(name: str) -> ast.Name:
    """Generates a Name-node"""
    return ast.Name(id=name, context=ast.Load())


def gen_bool_op(op: BoolOp, *values: Expression) -> Expression:
    if len(values) > 1:
        return ast.BoolOp(op=op, values=list(values))

    return values[0]


def gen_or(*values: Expression) -> Expression:
    return gen_bool_op(ast.Or(), *values)


def gen_and(*values: Expression) -> Expression:
    return gen_bool_op(ast.And(), *values)


def gen_is(lhs: Expression, rhs: Expression) -> Expression:
    return ast.Compare(ops=[ast.Is()], left=lhs, comparators=[rhs])


def gen_bin_op(op: str, lhs: Expression, rhs: Expression) -> Expression:
    return ast.BinOp(left=lhs, op=BUILTIN_ARITH_OPERATOR_TRANSLATION[op](), right=rhs)


def gen_list(*elts: Expression) -> Expression:
    return ast.List(elts=list(elts))


def gen_tuple(*elts: Expression) -> Expression:
    return ast.Tuple(elts=list(elts))


def gen_dict(pairs: Dict[Expression, Expression]) -> Expression:
    keys = list(pairs.keys())
    values = list(pairs.values())
    return ast.Dict(keys=list(keys), values=list(values))


def gen_constant(constant: Any) -> Expression:
    return ast.Constant(value=constant, kind=None)


def gen_if(
        test_ast: Expression,
        *body: Statement,
        orelse: List[Statement] = None
) -> Statement:
    if orelse is None:
        orelse = []
    return ast.If(
        test=test_ast,
        body=list(body),
        orelse=orelse
    )


def gen_return(value_ast: Expression) -> Statement:
    return ast.Return(
        value=value_ast
    )


def gen_alive_call(id_var: str) -> Expression:
    return gen_call(
        gen_attribute(gen_self(), "chr", "alive"),
        gen_name(id_var)
    )


def gen_subscript_index(value_ast: Expression, index_ast: Expression) -> Expression:
    return ast.Subscript(
        value=value_ast,
        slice=ast.Index(index_ast)
    )


BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS: Dict[str, Callable[[], CmpOp]] = {
    "==": ast.Eq,
    "!=": ast.NotEq,
    "<": ast.Lt,
    "<=": ast.LtE,
    ">": ast.Gt,
    ">=": ast.GtE,
    "is": ast.Is,
    "in": ast.In
}

BUILTIN_ARITH_OPERATOR_TRANSLATION: Dict[str, Callable[[], Operator]] = {
    "+": ast.Add,
    "-": ast.Sub,
    "*": ast.Mult,
    "/": ast.Div,
    "%": ast.Mod,
}


def gen_comparison(op: str, lhs_ast: Expression, rhs_ast: Expression) -> Expression:
    if op not in BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS:
        raise CHRCompilationError(f"unknown operator: {op}")

    return ast.Compare(
        left=lhs_ast,
        ops=[BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS[op]()],
        comparators=[rhs_ast]
    )


def gen_kill_call(index_name: str) -> Statement:
    return gen_expr(
        gen_call(
            gen_attribute(gen_self(), "chr", "delete"),
            gen_name(index_name)
        )
    )


def gen_len_check(value_ast: Expression, pattern: Union[List, Tuple, Dict]) -> Expression:
    return gen_comparison(
        "==",
        gen_call("len", value_ast),
        gen_constant(len(pattern))
    )


def gen_type_check(value_ast: Expression, pattern: Any) -> Expression:
    return gen_comparison(
        "is",
        gen_call("type", value_ast),
        gen_name(type(pattern).__name__)
    )


def gen_generator(expr: Expression, target: Expression, iterator: Expression) -> Expression:
    return ast.GeneratorExp(
        elt=expr,
        generators=[ast.comprehension(target=target, iter=iterator)]
    )


def gen_for_loop(
        target: Expression,
        iterator: Expression,
        *body: Statement,
        orelse: List[Statement] = None
) -> Statement:
    if orelse is None:
        orelse = []

    return ast.For(
        target=target,
        iter=iterator,
        body=list(body),
        orelse=orelse
    )


def gen_pass() -> Statement:
    return ast.Pass()


def gen_expr(expr_ast: Expression) -> Statement:
    return ast.Expr(value=expr_ast)


def gen_commit() -> Statement:
    return gen_expr(gen_call(gen_attribute(gen_self(), "builtin", "commit_recent_bindings")))


def gen_backtrack() -> Statement:
    return gen_expr(gen_call(gen_attribute(gen_self(), "builtin", "reset_recent_bindings")))


def gen_guard_try_catch(*body: Statement) -> Statement:
    return ast.Try(
        body=list(body),
        handlers=[ast.ExceptHandler(type=gen_name("CHRGuardFail"), name=None, body=[
            gen_backtrack()
        ])],
        orelse=[],
        finalbody=[]
    )


def gen_func_def(
        name: str,
        arguments: ast.arguments,
        *body: Statement,
        decorator_list: List[Expression] = None
) -> Statement:
    if decorator_list is None:
        decorator_list = []
    return ast.FunctionDef(
        name=name,
        args=arguments,
        body=list(body),
        decorator_list=decorator_list,
        defaults=[]
    )


def gen_starred(value_ast: Expression) -> Expression:
    return ast.Starred(value=value_ast, ctx=ast.Load())


def gen_lambda(
        body: Expression,
        posonlyargs: List[ast.arg] = [],
        args: List[ast.arg] = [],
        vararg: Union[None, ast.arg] = None,
        kwonlyargs: List[ast.arg] = [],
        kw_defaults: List[Expression] = [],
        kwarg: Union[ast.arg, None] = None,
        defaults: List[Expression] = []
) -> Expression:
    return ast.Lambda(
        args=ast.arguments(
            posonlyargs=posonlyargs,
            args=args,
            vararg=vararg,
            kwonlyargs=kwonlyargs,
            kw_defaults=kw_defaults,
            kwarg=kwarg,
            defaults=defaults
        ),
        body=body
    )


def compile_term(
        term: Term,
        known_variables: Dict[str, Expression],
) -> Expression:
    """Compiles a builtin term"""

    if isinstance(term, Var):
        if term.name not in known_variables:
            raise CHRCompilationError(f"variable {term.name} now known")

        return gen_call("get_value", known_variables[term.name])

    if isinstance(term, dict):
        return gen_dict({
            compile_term(key, known_variables): compile_term(sub_term, known_variables)
            for key, sub_term in term.items()
        })

    if isinstance(term, (tuple, list)):
        return (gen_tuple if isinstance(term, tuple) else gen_list)(*(
            compile_term(sub_term, known_variables)
            for sub_term in term
        ))

    if isinstance(term, Term):
        if term.symbol in BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS:
            return gen_comparison(
                term.symbol,
                compile_term(term.params[0], known_variables),
                compile_term(term.params[1], known_variables)
            )

        if term.symbol in BUILTIN_ARITH_OPERATOR_TRANSLATION:
            return gen_bin_op(
                term.symbol,
                compile_term(term.params[0], known_variables),
                compile_term(term.params[1], known_variables)
            )

        if term.symbol in BUILTIN_TYPES and not term.params:
            return gen_name(term.symbol)

        return gen_call(
            gen_attribute(*term.symbol.split(".")),
            *(
                compile_term(sub_term, known_variables)
                for sub_term in term.params
            )
        )

    return gen_constant(term)


def compile_fresh_constraint(
        name_gen: NameGenerator,
        variable_name: str,
        known_variables: Dict[str, Expression],
        value_ast: Union[Expression, None] = None
) -> Statement:
    """Compiles the 'fresh' builtin constraint, which generates a fresh logical variable"""
    if variable_name in known_variables:
        raise CHRCompilationError(f"Variable {variable_name} already known as {known_variables[variable_name]}")

    new_name = name_gen.new_name(prefix="local")
    known_variables[variable_name] = gen_name(new_name)

    return gen_assign(
        [gen_name(new_name)],
        gen_call(
            gen_attribute(gen_self(), "builtin", "fresh"),
            value=value_ast
        ) if value_ast else gen_call(gen_attribute(gen_self(), "builtin", "fresh"))
    )


def compile_unify(
        lhs: Term,
        rhs: Term,
        known_variables: Dict[str, Expression],
        in_guard: bool = False
) -> Statement:
    """Compiles the '=' builtin constraint"""
    var_names = vars(lhs).union(vars(rhs))
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    lhs_ast = compile_term(lhs, known_variables)
    rhs_ast = compile_term(rhs, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_call("unify", lhs_ast, rhs_ast)
    )


def compile_is(
        lhs: Term,
        rhs: Term,
        known_variables: Dict[str, Expression],
        in_guard: bool = False
) -> Statement:
    """Compiles the 'is' builtin constraint where

        X is Y

    compiles to

        if not (is_bound(X) and is_bound(Y) and get_value(X) is get_value(Y) or X is Y):
            raise ...
    """

    var_names = vars(lhs).union(vars(rhs))
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    lhs_ast = compile_term(lhs, known_variables)
    rhs_ast = compile_term(rhs, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_or(
            gen_and(
                gen_call("is_bound", lhs_ast),
                gen_call("is_bound", rhs_ast),
                gen_is(lhs_ast, rhs_ast)
            ),
            gen_is(lhs_ast, rhs_ast)
        )
    )


def compile_comparisons(
        op: str,
        lhs: Term,
        rhs: Term,
        known_variables: Dict[str, Expression],
        in_guard=False
) -> Statement:
    """Compiles a comparison constraint, i.e. one in {'==', '!=', '<', '<=', '>', '>='}"""
    var_names = vars(lhs).union(vars(rhs))
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    lhs_ast = compile_term(lhs, known_variables)
    rhs_ast = compile_term(rhs, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_and(
            gen_call("is_bound", lhs_ast),
            gen_call("is_bound", rhs_ast),
            gen_comparison(op, gen_call("get_value", lhs_ast), gen_call("get_value", rhs_ast))
        )
    )


def compile_is_bound(
        term: Term,
        known_variables: Dict[str, Expression],
        in_guard: bool = False
) -> Statement:
    """Compiles the 'is_bound' builtin constraint"""
    var_names = vars(term)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    term_ast = compile_term(term, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_call("is_bound", term_ast)
    )


def compile_not(
        term: Term,
        known_variables: Dict[str, Expression],
        in_guard: bool = False
) -> Statement:
    """Compile the 'not' builtin constraint/operator"""
    var_names = vars(term)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    term_ast = compile_term(term, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_not(term_ast)
    )


def compile_misc_builtin(
        term: Term,
        known_variables: Dict[str, Expression],
        in_guard: bool = False
) -> Statement:
    """Compiles any other function call as a constraint"""
    var_names = vars(term)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    if isinstance(term, Term):
        symbol = term.symbol
        arg_asts = [compile_term(sub_term, known_variables) for sub_term in term.params]
        term_ast = gen_call(gen_attribute(*symbol.split("."), *arg_asts))
    else:
        term_ast = compile_term(term, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        term_ast
    )


def compile_chr_constraint(
        name_gen: NameGenerator,
        term: Term,
        known_variables: Dict[str, Expression]
) -> List[Statement]:
    """Compiles a CHR-Constraint in the body, where

        c(t1, t2, ..., tn)

    is translated to

        _id_j = self.chr.new()
        _c_i = ("c/n", t1', t2', ..., tn')
        self.chr.insert(_c_i, _id_j)
        self.__activate_c_n(id_j, t1', t2', ..., t3')

    where ti' = compile_term(ti)
    """
    var_names = vars(term)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {var_names - set(known_variables.keys())} not known.")

    id_var = name_gen.new_name(prefix="id")
    c_var = name_gen.new_name(prefix="c")

    id_var_ast = gen_name(id_var)
    c_var_ast = gen_name(c_var)

    known_variables[id_var] = id_var_ast
    known_variables[c_var] = c_var_ast

    arg_asts = [compile_term(sub_term, known_variables) for sub_term in term.params]

    return [
        gen_new_call(id_var),
        gen_assign(
            [c_var_ast],
            gen_tuple(
                gen_constant(f'{term.symbol}/{term.arity}'),
                *arg_asts
            )
        ),
        gen_insert_call(c_var, id_var),
        gen_activate_call(id_var, term.symbol, term.arity, *arg_asts)  # TODO optimize
    ]


def compile_rule_body(
        name_gen: NameGenerator,
        killed_constraints: Set[str],
        known_chr_constraints: Set[str],
        known_variables: Dict[str, Expression],
        body_constraints: List[Term]
) -> List[Statement]:
    kills = [gen_kill_call(index) for index in killed_constraints]
    constraints = []

    for body_constraint in body_constraints:
        if isinstance(body_constraint, Term):
            if f"{body_constraint.symbol}/{body_constraint.arity}" in known_chr_constraints:
                constraints += compile_chr_constraint(name_gen, body_constraint, known_variables)
            elif body_constraint.symbol == "=":
                constraints.append(compile_unify(body_constraint.params[0], body_constraint.params[1], known_variables))
                constraints.append(gen_commit())
            elif body_constraint.symbol == "is":
                constraints.append(
                    compile_is(body_constraint.params[0], body_constraint.params[1], known_variables)
                )
            elif body_constraint.symbol == "is_bound":
                constraints.append(
                    compile_is_bound(body_constraint.params[0], known_variables)
                )
            elif body_constraint.symbol in BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS:
                constraints.append(
                    compile_comparisons(
                        body_constraint.symbol,
                        body_constraint.params[0],
                        body_constraint.params[1],
                        known_variables
                    )
                )
            elif body_constraint.symbol == "fresh":
                constraints.append(compile_fresh_constraint(
                    name_gen,
                    body_constraint.params[0].name,
                    known_variables
                ))

            elif body_constraint.symbol == "not":
                constraints.append(
                    compile_not(body_constraint.params[0], known_variables)
                )
            else:
                constraints.append(
                    compile_misc_builtin(body_constraint, known_variables)
                )
        else:
            constraints.append(
                compile_misc_builtin(body_constraint, known_variables)
            )

    finalize = gen_return(gen_constant(True))

    if "id_0" not in killed_constraints:
        finalize = gen_if(
            gen_not(gen_alive_call("id_0")),
            finalize
        )

    return [
        *kills,
        *constraints,
        finalize
    ]


def compile_match(
        value_ast: Expression,
        pattern: Any,
        known_vars: Dict[str, Expression]
) -> List[Expression]:
    conditions = []

    if not isinstance(pattern, Var):
        conditions.append(gen_type_check(value_ast, pattern))

    if isinstance(pattern, (dict, tuple, list)):
        conditions.append(
            gen_len_check(value_ast, pattern)
        )

        if isinstance(pattern, dict):
            for key in pattern.keys():
                conditions.append(
                    gen_comparison("in", gen_constant(key), value_ast)
                )

        for index, sub_term in enumerate(pattern) if isinstance(pattern, (tuple, list)) else pattern.items():
            conditions += compile_match(
                gen_subscript_index(value_ast, gen_constant(index)),
                pattern[index],
                known_vars
            )

    elif isinstance(pattern, Var):
        if pattern.name in known_vars:
            conditions.append(
                gen_comparison("==", value_ast, known_vars[pattern.name])
            )
        else:
            known_vars[pattern.name] = value_ast

    else:
        conditions.append(
            gen_comparison("==", value_ast, gen_constant(pattern))
        )

    return conditions


def compile_guard_constraint(
        name_gen: NameGenerator,
        constraint: Term,
        known_variables: Dict[str, Expression]
) -> Statement:
    symbol = constraint.symbol
    params = constraint.params
    if symbol == "fresh":
        var = params[0]
        if not isinstance(var, Var):
            raise CHRCompilationError(f"{var} is not an instance of {Var}")

        return compile_fresh_constraint(name_gen, var.name, known_variables)

    if symbol == "=":
        return compile_unify(params[0], params[1], known_variables, in_guard=True)

    if symbol == "is":
        return compile_is(params[0], params[1], known_variables, in_guard=True)

    if symbol == "is_bound":
        return compile_is_bound(params[0], known_variables, in_guard=True)

    if symbol == "not":
        return compile_not(params[0], known_variables, in_guard=True)

    if symbol in BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS:
        return compile_comparisons(symbol, params[0], params[1], known_variables, in_guard=True)

    if symbol in BUILTIN_ARITH_OPERATOR_TRANSLATION:
        return gen_raise_on_false(
            gen_call("CHRGuardFail"),
            compile_term(constraint, known_variables)
        )

    return compile_misc_builtin(constraint, known_variables, in_guard=True)


def compile_guarded_body(
        name_gen: NameGenerator,
        killed_constraints: Set[str],
        known_chr_constraints: Set[str],
        known_variables: Dict[str, Expression],
        guard_constraints: List[Term],
        body_constraints: List[Term],
        history_entry: Tuple[Expression, ...]
) -> Statement:
    guard_statements = [
        compile_guard_constraint(name_gen, gc, known_variables)
        for gc in guard_constraints
    ]

    return gen_guard_try_catch(
        *guard_statements,
        gen_if(
            gen_not(gen_call(gen_attribute(gen_self(), "chr", "in_history"), *history_entry)),
            gen_expr(gen_call(gen_attribute(gen_self(), "chr", "add_to_history"), *history_entry)),
            gen_commit(),
            *compile_rule_body(
                name_gen,
                killed_constraints,
                known_chr_constraints,
                known_variables,
                body_constraints
            ),
        )
    )


def compile_alive_checks(
        rule_name: str,
        name_gen: NameGenerator,
        total_head_constraints: int,
        killed_constraints: Set[str],
        known_chr_constraints: Set[str],
        known_variables: Dict[str, Expression],
        guard_constraints: List[Term],
        body_constraints: List[Term]
) -> Statement:
    return gen_if(
        gen_and(*(gen_alive_call(f"id_{i}") for i in range(0, total_head_constraints))),
        compile_guarded_body(
            name_gen,
            killed_constraints,
            known_chr_constraints,
            known_variables,
            guard_constraints,
            body_constraints,
            (
                gen_constant(rule_name),
                *(known_variables[f"id_{i}"] for i in range(0, total_head_constraints))
            )
        )
    )


def compile_match_loops(
        rule_name: str,
        name_gen: NameGenerator,
        current_head_constraint: int,
        killed_constraints: Set[str],
        known_chr_constraints: Set[str],
        known_variables: Dict[str, Expression],
        matched_symbols: Dict[str, List[str]],
        head_constraints: List[HeadConstraint],
        matchings: List[Term],
        guard_constraints: List[Term],
        body_constraints: List[Term]
) -> Statement:
    if not head_constraints:
        if matchings:
            raise CHRCompilationError(f"There are uncompiled matchings: {matchings}")

        return compile_alive_checks(
            rule_name,
            name_gen,
            current_head_constraint,
            killed_constraints,
            known_chr_constraints,
            known_variables,
            guard_constraints,
            body_constraints
        )

    c_var_name = f"c_{current_head_constraint}"
    index_var_name = f"id_{current_head_constraint}"

    c_var_ast = gen_name(c_var_name)
    index_var_ast = gen_name(index_var_name)

    known_variables[c_var_name] = c_var_ast
    known_variables[index_var_name] = index_var_ast

    current, *next_constraints = head_constraints

    for i, param in enumerate(current.params):
        known_variables[param] = gen_subscript_index(c_var_ast, gen_constant(i + 1))

    viable_matchings = []
    future_matchings = []

    next_vars = set().union(*(vars(c) for c in next_constraints))

    for matching in matchings:
        if (
                vars(matching.params[0]).issubset(set(known_variables.keys())) and
                not vars(matching.params[1]).intersection(next_vars)
        ):
            viable_matchings.append(matching)
        else:
            future_matchings.append(matching)

    matching_condition = []

    for m in viable_matchings:
        matching_condition += compile_match(
            compile_term(m.params[0], known_variables),
            m.params[1],
            known_variables
        )

    symbol = f'{current.symbol}/{current.arity}'
    different_symbols = []
    if symbol in matched_symbols:
        different_symbols = matched_symbols[symbol]
    checks = [
        gen_comparison("!=", index_var_ast, gen_name(other))
        for other in different_symbols
    ]
    if symbol in matched_symbols:
        matched_symbols[symbol].append(index_var_name)
    else:
        matched_symbols[symbol] = [index_var_name]

    if not current.kept:
        killed_constraints.add(index_var_name)

    return gen_for_loop(
        gen_tuple(index_var_ast, c_var_ast),
        gen_call(
            gen_attribute(gen_self(), "chr", "get_iterator"),
            fix=gen_constant(True),
            symbol=gen_constant(symbol)
        ),
        gen_if(
            gen_and(*checks, *matching_condition) if matching_condition or checks else gen_constant(True),
            compile_match_loops(
                rule_name,
                name_gen,
                current_head_constraint + 1,
                killed_constraints,
                known_chr_constraints,
                known_variables,
                matched_symbols,
                next_constraints,
                future_matchings,
                guard_constraints,
                body_constraints
            )
        )
    )


def compile_occurrence(
        occurrence_scheme: OccurrenceScheme,
        known_chr_constraints: Set[str]
) -> Tuple[str, int, Statement]:
    _, head = occurrence_scheme.occurring_constraint
    known_variables = {
        v: gen_name(v) for v in head.params
    }

    known_variables["id_0"] = gen_name("id_0")

    killed_constraints = set() if head.kept else {"id_0"}

    matched_symbols = {f"{head.symbol}/{head.arity}": ["id_0"]}

    proc_name = f"__{head.symbol}_{head.arity}_{head.occurrence_idx}"

    viable_matchings = []
    future_matchings = []

    next_vars = set().union(*(vars(c) for c in occurrence_scheme.other_constraints))

    for matching in occurrence_scheme.matching:
        if (
                vars(matching.params[0]).issubset(set(known_variables.keys())) and
                not vars(matching.params[1]).intersection(next_vars)
        ):
            viable_matchings.append(matching)
        else:
            future_matchings.append(matching)

    matching_condition = []
    for m in viable_matchings:
        matching_condition += compile_match(
            compile_term(m.params[0], known_variables),
            m.params[1],
            known_variables
        )

    return head.symbol, head.arity, gen_func_def(
        proc_name,
        ast.arguments(
            args=[
                ast.arg(arg="self", annotation=None),
                ast.arg(arg="id_0", annotation=None),
                *(ast.arg(arg=v, annotation=None) for v in head.params)
            ],
            defaults=[],
            vararg=None,
            kwarg=None
        ),
        gen_if(
            gen_not(gen_and(*matching_condition)),
            gen_return(gen_constant(False))
        ) if matching_condition else gen_pass(),
        compile_match_loops(
            occurrence_scheme.rule_name,
            NameGenerator(),
            1,
            killed_constraints,
            known_chr_constraints,
            known_variables,
            matched_symbols,
            list(c for _, c in occurrence_scheme.other_constraints),
            future_matchings,
            occurrence_scheme.guard,
            occurrence_scheme.body
        ),
        gen_return(gen_constant(False))
    )


def compile_activate_procedure(symbol: str, arity: int, occurrences: List[ast.FunctionDef]) -> Statement:
    proc_name: str = f"__activate_{symbol}_{arity}"

    occurrence_calls: List[Expression] = [
        gen_call(
            gen_attribute(gen_self(), proc.name),
            gen_name("index"),
            gen_starred(gen_name("args"))
        )
        for proc in occurrences
    ]

    occurrence_tries: List[Statement] = [
        gen_if(proc_call, gen_return(gen_constant(True)))
        for proc_call in occurrence_calls
    ]

    args_ast = gen_name("args")

    delay_checks = [gen_not(gen_name("delayed"))]
    if arity > 0:
        delay_checks.append(gen_or(*(
            gen_and(
                gen_call(
                    "isinstance",
                    gen_subscript_index(args_ast, gen_constant(i)),
                    gen_name("LogicVariable")
                ),
                gen_not(gen_call(
                    "is_bound",
                    gen_subscript_index(args_ast, gen_constant(i))
                ))
            )
            for i in range(0, arity)
        )))

    delay_call: Statement = gen_if(
        gen_and(*delay_checks),
        gen_expr(gen_call(
            gen_attribute(gen_self(), "builtin", "delay"),
            gen_lambda(gen_call(
                gen_attribute(gen_self(), proc_name),
                gen_name("index"),
                gen_starred(args_ast),
                delayed=gen_constant(True)
            )),
            gen_starred(args_ast),
        ))
    )

    return gen_func_def(
        proc_name,
        ast.arguments(
            args=[
                ast.arg(arg="self", annotation=None),
                ast.arg(arg="index", annotation=None)
            ],
            vararg=ast.arg(arg="args", annotation=None),
            kwonlyargs=[ast.arg(arg="delayed", annotation=None)],
            kw_defaults=[gen_constant(False)],
            defaults=[],
            kwarg=None
        ),
        *occurrence_tries,
        delay_call,
        gen_return(gen_constant(False))
    )


def compile_public_procedure(symbol: str, arities: List[int]) -> Statement:
    arity_checks: List[Statement] = [gen_pass()]
    if not arities:
        raise CHRCompilationError(f"symbol {symbol} hast no valid arities")

    arity_checks = [
        gen_if(
            gen_comparison(
                "==",
                gen_call("len", gen_name("args")),
                gen_constant(arity)
            ),
            gen_assign(
                [gen_name("new_id")],
                gen_call(gen_attribute(gen_self(), "chr", "new"))
            ),
            gen_assign(
                [gen_name("new_constraint")],
                gen_tuple(gen_constant(f"{symbol}/{arity}"), gen_starred(gen_name("args")))
            ),
            gen_insert_call("new_constraint", "new_id"),
            gen_return(
                gen_call(
                    gen_attribute(gen_self(), f"__activate_{symbol}_{arity}"),
                    gen_name("new_id"),
                    gen_starred(gen_name("args"))
                )
            )
        )
        for arity in arities
    ]

    wrong_arity_default = gen_raise(
        gen_call(
            "UndefinedConstraintError",
            gen_constant(f"Unknown symbol: {symbol}/"),
            gen_call("len", gen_name("args"))
        )
    )

    return gen_func_def(
        symbol,
        ast.arguments(
            args=[ast.arg(arg="self", annotation=None)],
            vararg=ast.arg(arg="args", annotation=None),
            defaults=[],
            kwarg=None,
        ),
        *arity_checks,
        wrong_arity_default
    )


def compile_omega_r_program(solver_class_name: str, program: Program) -> ast.Module:
    known_chr_constraints = set(program.user_constraints)

    occurrences: Dict[Tuple[str, int], List[ast.FunctionDef]] = {
        (symbol, int(arity)): []
        for symbol, arity in map(lambda x: x.split('/'), known_chr_constraints)
    }

    constraints = {
        symbol: {int(arity)}
        for symbol, arity in map(lambda x: x.split('/'), known_chr_constraints)
    }

    for rule in program.rules:
        definitions: List[Tuple[str, int, ast.FunctionDef]] = [
            compile_occurrence(occurrence_scheme, known_chr_constraints)
            for occurrence_scheme in rule.get_occurrence_schemes()
        ]

        for symbol, arity, func_ast in definitions:
            if (symbol, arity) in occurrences:
                occurrences[symbol, arity].append(func_ast)
            else:
                occurrences[symbol, arity] = [func_ast]

            if symbol in constraints:
                constraints[symbol].add(arity)
            else:
                constraints[symbol] = {arity}

    activation_procedures = [
        compile_activate_procedure(symbol, arity, occurrences[symbol, arity])
        for (symbol, arity), procedures in occurrences.items()
    ]

    constraint_procedures = [
        proc
        for procs in occurrences.values()
        for proc in procs
    ]

    public_procedures = [
        compile_public_procedure(symbol, arities)
        for symbol, arities in constraints.items()
    ]

    return ast.Module(body=[
        ast.ImportFrom(
            module="chr.runtime",
            names=[
                ast.alias(name="LogicVariable", asname=None),
                ast.alias(name="CHRSolver", asname=None),
                ast.alias(name="CHRFalse", asname=None),
                ast.alias(name="UndefinedConstraintError", asname=None),
                ast.alias(name="CHRGuardFail", asname=None),
                ast.alias(name="get_value", asname=None),
                ast.alias(name="is_bound", asname=None),
                ast.alias(name="unify", asname=None)
            ],
            level=0
        ),
        ast.ClassDef(
            name=solver_class_name,
            body=[
                *constraint_procedures,
                *activation_procedures,
                *public_procedures
            ],
            bases=[ast.Name("CHRSolver")],
            decorator_list=[],
            keywords=[]
        )
    ])


def chr_compile_source(source: str, verbose: bool = False) -> str:
    """
    Compiles CHR source code into python source code
    :param source: CHR program as a string
    :param verbose: Gives some extra output if set to True.
    :return: Generated Python code
    """
    if verbose:
        print("Parsing and transforming...", end=" ")
    chr_ast = chr_parse(source).get_normal_form().omega_r()
    if verbose:
        print("done.")
        print("Compiling to python ast...", end=" ")
    python_ast = compile_omega_r_program(chr_ast.class_name, chr_ast)
    # pprintast(python_ast)
    if verbose:
        print("done.")
        print("Generating python code...", end=" ")
    python_code = decompile(python_ast)
    if verbose:
        print("done.")

    return python_code
