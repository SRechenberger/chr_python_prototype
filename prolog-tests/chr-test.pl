:- use_module(library(chr)).

:- chr_constraint minimax/2, a/1.

a(X) <=> minimax(X, X).
minimax(X, _) \ minimax(A, B) <=> X < A | minimax(X, B).
minimax(_, Y) \ minimax(A, B) <=> Y > B | minimax(A, Y).
minimax(X, Y) \ minimax(X, Y) <=> true.
