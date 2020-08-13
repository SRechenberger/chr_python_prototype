:- use_module(library(chr)).

:- chr_constraint eq/2.

:- op(700, xfx, eq).

cleanup      @ X eq Y \ X eq Y <=> true.
transitivity @ X eq Y, Y eq Z ==> X eq Z.
symmetry     @ X eq Y ==> Y eq X.
reflexivity  @ X eq Y <=> X = Y.