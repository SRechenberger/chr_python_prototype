from functools import reduce

from parsy import string, regex, generate, fail

from chr.ast import *

'''
integer  ::= [0-9]+
string   ::= '"' .* '"'
key_value ::= term ':' term
dict     ::= '{' key_value { ',' key_value }* '}'
list     ::= '[' term { ',' term }* ']'
symbol   ::= [a-z][a-zA-Z0-9_-]*
variable ::= [A-Z_][a-zA-Z0-9_-]*
functor  ::= symbol { '(' term { ',' term }* ')' }
operator ::= [+*/%-]
term     ::= variable | functor | integer | string | list | dict

rule     ::= { symbol @ } ( simplification | propagation | simpagation )

constraints ::= functor { ',' functor }*
guard ::= constraints '|'

simplification ::= constraints '<=>' { guard } constraints '.'
propagation ::= constraints '==>' { guard } constraints '.'
simpagation ::= constraints '\' constraints '<=>' { guard } constraints '.'

signature ::= symbol '/' [0-9]+
decl ::= 'constraints' signature { ',' signature }* '.'
'''

lit_symbol = regex(r'[a-z][a-zA-Z0-9_]*')
lit_operator = regex(r'\'[^\t\n\r ]+\'')
lit_variable = regex(r'[a-zA-Z_][a-zA-Z0-9_]*')
lit_number = regex(r'[0-9]+')
lit_string = regex(r'\".*\"')
lit_white = regex(r'[\n\t ]*')
lit_signature = regex(r'[a-z][a-zA-Z0-9_-]*/[0-9]+')
lit_class_name = regex(r'[A-Za-z_][A-Za-z_0-9]*')


def token(s):
    if type(s) is not str:
        raise TypeError(f'{s}: {str} expected; got {type(s)}')

    @generate
    def fun():
        nonlocal s
        t = yield lit_white >> string(s) << lit_white
        return t

    return fun


comma = token(',')

infix_term_ops = [
    [("-", 1)],
    [("*", 2), ("/", 2), ("%", 2)],
    [("+", 2), ("-", 2)],
    [("not", 1)],
    [("==", 2), ("!=", 2), ("<=", 2), ("<", 2), (">=", 2), (">", 2)],
    [("and", 2), ("or", 2)],
    [("=", 2)]
]


def mk_infix_term_parser(term_parser, operators):
    un_ops = [token(op) for op, ar in operators if ar == 1]
    bin_ops = [token(op) for op, ar in operators if ar == 2]
    un_op = reduce(lambda l, r: l | r, un_ops) if un_ops else None
    bin_op = reduce(lambda l, r: l | r, bin_ops) if bin_ops else None

    @generate
    def fun():
        u = None
        if un_op:
            u = yield un_op.optional()
        left = yield term_parser
        if u:
            left = Term(u, params=[left])
        chained = []
        if bin_op:
            while True:
                op = yield bin_op.optional()
                if not op:
                    break
                v = None
                if un_op:
                    v = yield un_op.optional()
                right = yield term_parser
                if v:
                    right = Term(v, params=[right])
                chained.append((op, right))

        return reduce(lambda l, r: Term(r[0], params=[l, r[1]]), chained, left)

    return fun


@generate
def parse_prefix_term():
    symbol = yield lit_symbol | (token("'") >> regex("[^\n\t ']+") << token("'"))
    args = []
    br_open = yield string('(').optional()
    if br_open:
        t = yield lit_white >> parse_term
        args.append(t)
        while True:
            c = yield lit_white >> string(',').optional()
            if not c:
                break
            t = yield lit_white >> parse_term
            args.append(t)
        yield lit_white >> string(')')

    return Term(symbol, args)


@generate
def parse_variable():
    varname = yield lit_white >> string('$') >> lit_variable
    return Var(varname)


@generate
def parse_integer():
    number = yield lit_white >> lit_number
    return int(number)


@generate
def parse_string():
    s = yield lit_white >> lit_string
    return s[1:-1]


@generate
def parse_bool():
    s = yield lit_white >> (string('False') | string('True'))
    return s == "True"


@generate
def parse_empty_list():
    yield token('[') + lit_white + token(']')
    return []


@generate
def parse_non_empty_list():
    yield token('[')
    ts = yield (lit_white >> parse_term << comma).many()
    t = yield parse_term.optional()
    yield token(']')
    return ts + ([t] if t else [])


@generate
def parse_list():
    ts = yield parse_empty_list | parse_non_empty_list
    return ts


@generate
def parse_key_value():
    k = yield parse_term
    if not is_ground(k):
        fail(f'{k} not ground')
    yield token(':')
    v = yield parse_term
    return k, v


@generate
def parse_dict():
    yield token('{')
    items = yield (parse_key_value << comma).many()
    last = yield parse_key_value.optional()
    yield token('}')

    return dict(items + ([last] if last else []))


@generate
def parse_tuple():
    yield token('(')
    es = yield (lit_white >> parse_term << comma).at_least(1)
    last = yield parse_term.optional()
    yield token(')')

    return tuple(es + ([last] if last else []))


@generate
def parse_atom():
    result = yield lit_white >> (
            parse_integer |
            parse_bool |
            parse_string |
            parse_variable |
            parse_list |
            parse_tuple |
            parse_dict |
            parse_prefix_term |
            token('(') >> parse_term << token(')')
    )
    return result


@generate
def parse_term():
    result = yield lit_white >> (
            parse_infix_term(infix_term_ops) |
            parse_atom
    )
    return result


def parse_infix_term(op_table, acc=parse_atom):
    if not op_table:
        return acc

    return parse_infix_term(
        op_table[1:],
        acc=mk_infix_term_parser(acc, op_table[0])
    )


@generate
def parse_constraints():
    c = yield lit_white >> parse_term
    args = [c]
    while True:
        sep = yield lit_white >> string(',').optional()
        if not sep:
            break

        c1 = yield lit_white >> parse_term
        args.append(c1)

    return args


@generate
def parse_guard():
    cs = yield lit_white >> parse_constraints
    yield lit_white >> string('|')
    return cs


@generate
def parse_body():
    gs = yield lit_white >> parse_guard.optional()
    cs = yield lit_white >> parse_constraints
    return gs, cs


@generate
def parse_rule_name():
    name = yield lit_white >> lit_symbol
    yield lit_white >> string('@')
    return name


def parse_rule(rule_name_generator):
    @generate
    def fun():
        name = yield lit_white >> parse_rule_name.optional()
        if not name:
            name = rule_name_generator()
        kept, removed, guard, body = yield \
            parse_simplification \
            | parse_propagation \
            | parse_simpagation

        yield lit_white >> string('.')
        return Rule(name, kept, removed, guard if guard else [], body)

    return fun


@generate
def parse_simplification():
    hs = yield lit_white >> parse_constraints
    yield lit_white >> string('<=>')
    gs, bs = yield lit_white >> parse_body
    return [], hs, gs, bs


@generate
def parse_propagation():
    hs = yield lit_white >> parse_constraints
    yield lit_white >> string('==>')
    gs, bs = yield lit_white >> parse_body
    return hs, [], gs, bs


@generate
def parse_simpagation():
    ks = yield lit_white >> parse_constraints
    yield lit_white >> string('\\')
    rs = yield lit_white >> parse_constraints
    yield lit_white >> string('<=>')
    gs, bs = yield lit_white >> parse_body
    return ks, rs, gs, bs


def parse_rules(rule_name_generator):
    @generate
    def fun():
        rules = []
        while True:
            rule = yield lit_white >> parse_rule(rule_name_generator).optional()
            if not rule:
                break
            rules.append(rule)

        return rules

    return fun


@generate
def parse_signature():
    signature = yield lit_white >> lit_signature
    return signature


@generate
def parse_declaration():
    yield lit_white >> string("constraints")
    c = yield lit_white >> parse_signature
    cs = [c]
    while True:
        comma = yield lit_white >> (string(',') | string('.'))
        if comma == '.':
            break

        c1 = yield lit_white >> parse_signature
        cs.append(c1)

    return cs


@generate
def parse_class_name():
    yield lit_white >> string("class")
    c = yield lit_white >> lit_class_name
    yield token(".")
    return c


def parse_program():
    next_rule_id = 0

    def rule_name_gen():
        nonlocal next_rule_id
        next_rule_id += 1
        return f'rule_{next_rule_id - 1}'

    @generate
    def fun():
        class_name = yield parse_class_name
        decls = yield parse_declaration
        rules = yield parse_rules(rule_name_gen)
        return Program(class_name, decls, rules)

    return fun


def chr_parse(source):
    return parse_program().parse(source)
