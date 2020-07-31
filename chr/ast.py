class Term:
    def __init__(self, symbol, params=[]):
        self.symbol = symbol
        self.params = params
        self.arity = len(params)
        self.signature = f'{self.symbol}/{self.arity}'

    def __str__(self):
        if self.arity > 0:
            return f'{self.symbol}({", ".join(map(str, self.params))})'
        else:
            return self.symbol

    def __eq__(self, other):
        return self.symbol == other.symbol \
            and self.params == other.params

    def __repr__(self):
        return str(self)

    def vars(self):
        if self.arity > 0:
            vs, *vss = map(
                lambda p: set([p]) if type(p) is str else p.vars(),
                self.params
            )
            return vs.union(*vss)
        return set()


class Var:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f'Var({str(self.name)})'

    def __repr__(self):
        return f'Var({repr(self.name)})'

    def __eq__(self, other):
        return type(self) == type(other) \
            and self.name == other.name


def is_ground(term):
    if isinstance(term, Var):
        return False
    if isinstance(term, dict):
        return all(is_ground(v) for v in term.values())
    if isinstance(term, (tuple, list)):
        return all(is_ground(v) for v in term)
    return True



def vars(term):
    if isinstance(term, Var):
        return set([term.name])
    if isinstance(term, dict):
        return set().union(*(vars(v) for v in term.items()))
    if isinstance(term, (list, tuple)):
        return set().union(*(vars(v) for v in term))
    if isinstance(term, HeadConstraint):
        return set(term.params)
    if isinstance(term, Term):
        return set().union(*(vars(a) for a in term.params))
    return set()


class Constraint(Term):
    pass


class HeadConstraint(Constraint):
    def __init__(self, symbol, occurrence_idx, params, kept):
        self.symbol = symbol
        self.occurrence_idx = occurrence_idx
        self.params = params
        self.kept = kept
        self.arity = len(params)

    def __str__(self):
        return ('+' if self.kept else '-') \
            + f'{self.symbol}_{self.occurrence_idx}' \
            + (f'({", ".join(map(str, self.params))})' if self.arity > 0 else "")

    def __eq__(self, other):
        return self.symbol == other.symbol \
            and self.occurrence_idx == other.occurrence_idx \
            and self.params == other.params \
            and self.kept == other.kept

    def __repr__(self):
        return str(self)


class Rule:
    def __init__(self, name, kept_head, removed_head, guard, body):
        self.name = name
        self.kept_head = kept_head
        self.removed_head = removed_head
        self.guard = guard
        self.body = body

    def __eq__(self, other):
        return self.name == other.name \
            and self.kept_head == other.kept_head \
            and self.removed_head == other.removed_head \
            and self.guard == other.guard \
            and self.body == other.body

    def __str__(self):
        ks = ', '.join(map(str, self.kept_head)) if self.kept_head else None
        rs = ', '.join(map(str, self.removed_head)) if self.removed_head else None
        gs = ', '.join(map(str, self.guard)) if self.guard else None
        bs = ', '.join(map(str, self.body)) if self.body else "true"

        rule = f'{self.name} @ '
        if ks and rs:
            rule += f'{ks} \\ {rs} <=> '
        elif ks:
            rule += f'{ks} ==> '
        elif rs:
            rule += f'{rs} <=> '
        else:
            raise Exception(f'rule with empty head: {self}')

        if gs:
            rule += f'{gs} | '

        rule += bs

        return rule

    def __repr__(self):
        return str(self)

    def get_normal_form(self):
        normal_kept = []
        normal_removed = []
        matching = []
        next_var_id = 0
        known_vars = set()

        def mk_new_var():
            nonlocal next_var_id
            new_var = None
            while not new_var or new_var in known_vars:
                new_var = f'_{next_var_id}'
                next_var_id += 1
            return new_var

        for head, normal_head in [(self.kept_head, normal_kept), (self.removed_head, normal_removed)]:
            for k in head:
                normal_params = []
                for p in k.params:
                    if isinstance(p, Var):
                        print("known vars:", known_vars)
                        if p.name in known_vars:
                            new_var = mk_new_var()
                            known_vars.add(new_var)
                            matching.append(Constraint("ask_match", params=[
                                Var(new_var), p
                            ]))
                            normal_params.append(new_var)
                        else:
                            known_vars.add(p.name)
                            normal_params.append(p.name)


                    else:
                        new_var = mk_new_var()
                        matching.append(Constraint("ask_match", params=[
                            Var(new_var), p
                        ]))
                        normal_params.append(new_var)

                normal_head.append(Constraint(k.symbol, normal_params))

        return NormalizedRule(
            self.name,
            normal_kept,
            normal_removed,
            matching,
            self.guard,
            [c for c in self.body if c.symbol != "true"]
        )

class NormalizedRule(Rule):
    def __init__(self, name, kept, removed, matching, guard, body):
        self.name = name
        self.kept_head = kept
        self.removed_head = removed
        self.matching = matching
        self.guard = guard
        self.body = body

class OccurrenceScheme:
    def __init__(self, rule_name, occurring_constraint, other_constraints, matching, guard, body):
        self.rule_name = rule_name
        self.occurring_constraint = occurring_constraint
        self.other_constraints = other_constraints
        self.matching = matching
        self.guard = guard
        self.body = body

    def __eq__(self, other):
        return self.occurring_constraint == other.occurring_constraint \
            and self.other_constraints == other.other_constraints \
            and self.guard == other.guard \
            and self.body == other.body

    def __str__(self):
        occ = f'*{self.occurring_constraint}*'
        others = ', '.join(map(str, self.other_constraints))
        rule = occ
        if others:
            rule += ', ' + others + " <=> "

        if self.guard:
            rule += f" {', '.join(map(str, self.guard))} | "

        rule += ' ' + ', '.join(map(str, self.body))

        return rule

    def __repr__(self):
        return str(self)

    def free_vars(self):
        oc_vars = vars(self.occurring_constraint[1])
        print("oc_vars", oc_vars)
        head_vars = oc_vars.union(*(vars(c[1]) for c in self.other_constraints))
        print("head_vars", head_vars)
        return set().union(*(vars(c) for c in self.matching + self.guard + self.body)) \
             - head_vars



class ProcessedRule:
    def __init__(self, name, head, matching, guard, body):
        self.name = name
        self.head = head
        self.matching = matching
        self.body = body
        self.guard = guard

    def get_occurrence_scheme(self, idx):
        indexed = list(enumerate(self.head))
        constraint = indexed.pop(idx)
        return OccurrenceScheme(self.name, constraint, indexed, self.matching, self.guard, self.body)

    def get_occurrence_schemes(self):
        for idx, _ in enumerate(self.head):
            yield self.get_occurrence_scheme(idx)

    def __eq__(self, other):
        return self.name == other.name \
            and self.head == other.head \
            and self.body == other.body \
            and self.guard == other.guard

    def __str__(self):
        rule = f"{self.name} @ "
        rule += ', '.join(map(str, self.head)) + ' <=> '
        if self.guard:
            rule += ', '.join(map(str, self.guard)) + ' | '

        if self.body:
            rule += ', '.join(map(str, self.body))
        else:
            rule += "true"

        return rule

    def __repr__(self):
        return str(self)


class Program:
    def __init__(self, user_constraints, rules):
        self.user_constraints = user_constraints
        self.rules = rules

    def __eq__(self, other):
        return self.user_constraints == other.user_constraints \
            and self.rules == other.rules

    def __str__(self):
        return '\n'.join(map(str, self.rules))

    def __repr__(self):
        return str(self)

    def get_normal_form(self):
        return Program(
            self.user_constraints,
            [rule.get_normal_form() for rule in self.rules]
        )

    def omega_r(self):
        symbols = {}

        rules = []
        for rule in (rule for rule in self.rules):
            head = []
            for constr in rule.removed_head:
                if constr.symbol in symbols:
                    occ = symbols[constr.symbol]
                    symbols[constr.symbol] += 1
                else:
                    occ = 0
                    symbols[constr.symbol] = 1
                head.append(HeadConstraint(
                    symbol=constr.symbol,
                    occurrence_idx=occ,
                    params=constr.params,
                    kept=False
                ))

            for constr in rule.kept_head:
                if constr.symbol in symbols:
                    occ = symbols[constr.symbol]
                    symbols[constr.symbol] += 1
                else:
                    occ = 0
                    symbols[constr.symbol] = 1
                head.append(HeadConstraint(
                    symbol=constr.symbol,
                    occurrence_idx=occ,
                    params=constr.params,
                    kept=True
                ))

            rules.append(ProcessedRule(
                name=rule.name,
                head=head,
                matching=rule.matching,
                guard=rule.guard,
                body=rule.body
            ))


        return Program(self.user_constraints, rules), symbols
