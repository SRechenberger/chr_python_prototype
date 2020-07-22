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

class Emitter:

    def __init__(self, indent_padding=' ', indent_factor=4):
        self.lines = []
        self.level = 0
        self.indent_padding = indent_padding
        self.indent_factor = indent_factor
        self.var_idents = {}

    def leave_block(self, n=1):
        self.level -= n
        if self.level < 0:
            raise Exception("Negative indentation level")

    def enter_block(self, n=1):
        self.level += n

    def emit(self, line):
        self.lines.append((self.level, line))

    def render(self):
        return "\n".join([
            self.indent_padding * (level * self.indent_factor) + line
            for level, line in self.lines
        ])

    def emit_matching(self, rule, heads, i, j):
        if heads:
            (sym, *vars), *hs = heads
            if j == i:
                self.emit_heads(rule, hs, i, j+1)
            else:
                self.emit("for id_{j}, c_{j} in self.chr.get_enumerator(symbol={sym}, fix=True):")
                self.enter_block()
                self.emit_matching(rule, hs, i, j+1)
                self.leave_block()
        else:
            self.emit_body(rule, range(1,j))



    def emit_occurrence(self, rule, symbol, occurrence_id, i):
        self.emit(f"def {symbol}_{occurrence_id}(id_{i}, vars_{i}):")
        self.enter_block()
        self.emit_matching(
            rule,
            rule["kept"] + rule["removed"],
            i,
            1
        )
        self.leave_block()
