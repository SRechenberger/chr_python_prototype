import pytest
from chr.compiler import Emitter

def test_code_gen():
    cg = Emitter(indent_padding='-', indent_factor=1)
    cg.emit("1")
    cg.emit("2")
    cg.enter_block()
    cg.emit("3")
    cg.emit("4")
    cg.leave_block()
    cg.emit("5")
    assert cg.render() == '''1
2
-3
-4
5'''

def test_code_gen_2():
    cg = Emitter(indent_padding='.', indent_factor=2)
    cg.emit("1")
    cg.enter_block()
    cg.emit("2")
    cg.enter_block()
    cg.emit("3")
    cg.leave_block()
    cg.leave_block()
    assert cg.render() == '''1
..2
....3'''
