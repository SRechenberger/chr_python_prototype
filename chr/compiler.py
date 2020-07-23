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

class Emitter:

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

    def compile_occurrence(self, occurrence_scheme):
        if not isinstance(occurrence_scheme, chrast.OccurrenceScheme):
            raise TypeError(f'{occurrence_scheme} is not an instance of {chrast.OccurrenceScheme}')

        i, c = occurrence_scheme.occurring_constraint

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
            body=[ast.Pass()],
            decorator_list=[]
        )

        return proc

    def emit_occurrence(self, rule, i, symbol, occurrence_id, *variables):
        args = [ast.arg(arg=f'id_{i}', annotation=None)] + \
            [ast.arg(arg=var, annotation=None) for var in variables]
        name = f'{symbol}_{occurrence_id}'
        body = [
            ast.Pass()
        ]
        proc = ast.FunctionDef(
            name=name,
            args=ast.arguments(
                args=args,
                defaults=[],
                vararg=None,
                kwarg=None
            ),
            body=[ast.Pass()],
            decorator_list=[]
        )
        return proc
