import ast
from chr.ast import *


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


def gen_call(func, *args, **kwargs) -> ast.Call:
    """Returns a Call-statement ast, with given function ast"""
    return ast.Call(
        func=gen_name(func) if type(func) is str else func,
        args=args,
        keywords=[ast.keyword(arg=key, value=val) for key, val in kwargs]
    )


def gen_attribute(value, *attrs) -> ast.Attribute:
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


def gen_not(expr):
    return ast.UnaryOp(
        op=ast.Not(),
        operand=expr
    )


def gen_raise_on_false(exception_ast, *condition_asts):
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
            exc=exception_ast
        )]
    )


def gen_assign(targets, value) -> ast.Assign:
    """Generates an Assignment-node"""
    return ast.Assign(targets=targets, value=value)


def gen_self() -> ast.Name:
    """Generates a Name-node, with id=self"""
    return ast.Name(id="self", context=ast.Load())


def gen_name(name: str) -> ast.Name:
    """Generates a Name-node"""
    return ast.Name(name=name, context=ast.Load())


def gen_bool_op(op, *values):
    if len(values) > 1:
        return ast.BoolOp(op=op, values=values)

    return values[0]


def gen_or(*values):
    return gen_bool_op(ast.Or(), *values)


def gen_and(*values):
    return gen_bool_op(ast.And(), *values)


def gen_is(lhs, rhs):
    return ast.Compare(ops=[ast.Is()], left=lhs, comparators=[rhs])


def gen_bin_op(op, lhs, rhs):
    return ast.BinOp(left=lhs, op=BUILTIN_ARITH_OPERATOR_TRANSLATION[op], right=rhs)


BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS = {
    "==": ast.Eq,
    "!=": ast.NotEq,
    "<": ast.Lt,
    "<=": ast.LtE,
    ">": ast.Gt,
    ">=": ast.GtE,
    "is": ast.Is
}


BUILTIN_ARITH_OPERATOR_TRANSLATION = {
    "+": ast.Add,
    "-": ast.Sub,
    "*": ast.Mult,
    "/": ast.Div,
    "%": ast.Mod,
}


def gen_comparison(op: str, lhs_ast, rhs_ast):
    if op not in BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS:
        raise CHRCompilationError(f"unknown operator: {op}")

    return ast.Compare(
        left=lhs_ast,
        ops=[BUILTIN_COMPARISON_OPERATOR_TRANSLATIONS[op]],
        comparators=[rhs_ast]
    )


def compile_term(term, known_variables):
    """Compiles a builtin term"""

    if isinstance(term, Var):
        if term.name not in known_variables:
            raise CHRCompilationError(f"variable {term.name} now known")

        return known_variables[term.name]

    if isinstance(term, dict):
        return {
            key: compile_term(sub_term, known_variables)
            for key, sub_term in term.items()
        }

    if isinstance(term, (tuple, list)):
        return type(term)(
            compile_term(sub_term, known_variables)
            for sub_term in term
        )

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

        return gen_call(
            gen_attribute(*term.symbol.split(".")),
            *(
                compile_term(sub_term, known_variables)
                for sub_term in term.params
            )
        )

    return term


def compile_fresh_constraint(name_gen: NameGenerator, variable_name, known_variables, value_ast=None) -> ast.Assign:
    """Compiles the 'fresh' builtin constraint, which generates a fresh logical variable"""
    if variable_name in known_variables:
        raise CHRCompilationError(f"Variable {variable_name} already known as {known_variables[variable_name]}")

    new_name = name_gen.new_name(prefix="local")

    return gen_assign(
        gen_name(new_name),
        gen_call(
            gen_attribute(gen_self(), "builtin", "fresh"),
            value=value_ast
        )
    )


def compile_unify(lhs: Term, rhs: Term, known_variables, in_guard=False):
    """Compiles the '=' builtin constraint"""
    var_names = vars(lhs) + vars(rhs)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {set(known_variables.keys()) - var_names} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    lhs_ast = compile_term(lhs, known_variables)
    rhs_ast = compile_term(rhs, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_call(gen_attribute(gen_self(), "builtin", "unify"), lhs_ast, rhs_ast)
    )


def compile_is(lhs: Term, rhs: Term, known_variables, in_guard=False):
    """Compiles the 'is' builtin constraint where

        X is Y

    compiles to

        if not (is_bound(X) and is_bound(Y) and get_value(X) is get_value(Y) or X is Y):
            raise ...
    """

    var_names = vars(lhs) + vars(rhs)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {set(known_variables.keys()) - var_names} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    lhs_ast = compile_term(lhs, known_variables)
    rhs_ast = compile_term(rhs, known_variables)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_or(
            gen_and(
                gen_call("is_bound", lhs_ast),
                gen_call("is_bound", rhs_ast),
                gen_is(lhs, rhs)
            ),
            gen_is(lhs, rhs)
        )
    )


def compile_comparisons(op: str, lhs: Term, rhs: Term, known_variables, in_guard=False):
    """Compiles a comparison constraint, i.e. one in {'==', '!=', '<', '<=', '>', '>='}"""
    var_names = vars(lhs) + vars(rhs)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {set(known_variables.keys()) - var_names} not known.")

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


def compile_is_bound(term: Term, known_variables, in_guard=False):
    """Compiles the 'is_bound' builtin constraint"""
    var_names = vars(term)
    if not all(v in known_variables for v in var_names):
        raise CHRCompilationError(f"Variables {set(known_variables.keys()) - var_names} not known.")

    exception_name = "CHRGuardFail" if in_guard else "CHRFalse"

    term_ast = compile_term(term)

    return gen_raise_on_false(
        gen_call(exception_name),
        gen_call("is_bound", term_ast)
    )

