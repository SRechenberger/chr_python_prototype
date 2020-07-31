:- use_module(library(chr)).

:- chr_constraint test/1, passed/1.

test(_1) ==> _1 = (X, Y, Z) | passed(X), passed((Y, Z)).
