class Term:
    def __init__(self, symbol, params):
        self.symbol = symbol
        self.params = params

    def __str__(self):
        return f'{self.symbol}({", ".join(map(str, self.params))})'

    def __eq__(self, other):
        return self.symbol == other.symbol \
            and self.params == other.params

    def __repr__(self):
        return str(self)


class Constraint:
    def __init__(self, symbol, params):
        self.symbol = symbol
        self.params = params

    def __str__(self):
        return f'{self.symbol}({", ".join(map(str, self.params))})'

    def __eq__(self, other):
        return self.symbol == other.symbol \
            and self.params == other.params

    def __repr__(self):
        return str(self)


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
            + f'({", ".join(map(str, self.params))})'

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


class OccurrenceScheme:
    def __init__(self, occurring_constraint, other_constraints, guard, body):
        self.occurring_constraint = occurring_constraint
        self.other_constraints = other_constraints
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


class ProcessedRule:
    def __init__(self, name, head, guard, body):
        self.name = name
        self.head = head
        self.body = body
        self.guard = guard

    def get_occurrence_scheme(self, idx):
        indexed = list(enumerate(self.head))
        constraint = indexed.pop(idx)
        return OccurrenceScheme(constraint, indexed, self.guard, self.body)

    def get_occurrence_schemes(self):
        for idx, _ in enumerate(self.head):
            yield self.get_occurrence_scheme(idx)

    def __eq__(self, other):
        return self.name == other.name \
            and self.head == other.head \
            and self.body == other.body \
            and self.guard == other.guard

    def __str__(self):
        rule = ', '.join(map(str, self.head)) + ' <=> '
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
    def __init__(self, rules):
        self.rules = rules

    def __eq__(self, other):
        return self.rules == other.rules

    def __str__(self):
        return '\n'.join(map(str, self.rules))

    def __repr__(self):
        return str(self)

    def omega_r(self):
        symbols = {}

        rules = []
        for rule in self.rules:
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
                guard=rule.guard,
                body=rule.body
            ))


        return Program(rules), symbols
