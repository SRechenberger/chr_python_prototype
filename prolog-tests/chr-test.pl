:- use_module(library(chr)).

:- chr_constraint test/1, passed/1.

test(X) \ test(Z) <=> X == Z.
