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

    def leave_block(self):
        self.level -= 1
        if self.level < 0:
            raise Exception("Negative indentation level")

    def enter_block(self):
        self.level += 1

    def emit(self, line):
        self.lines.append((self.level, line))

    def render(self):
        return "\n".join([
            self.indent_padding * (level * self.indent_factor) + line
            for level, line in self.lines
        ])

    def emit_occurrence(symbol, occurrence_id, i):
        pass
