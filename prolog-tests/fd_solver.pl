:- use_module(library(chr)).

:- chr_constraint
    element_of/2,
    element_of/3,
    set_fragments/2,
    range/3,
    set/2,
    lt/2,
    leq/2,
    eq/2,
    neq/2,
    geq/2,
    gt/2.


element_of(X, Ss) <=> is_list(Ss) | var(SetId), element_of(X, SetId, Ss), length(Ss, L), set_fragments(SetId, L).
element_of(X, SetId, []) <=> element_of(X, SetId).
element_of(X, SetId, [range(From, To) | Ss]) <=> range(SetId, From, To), element_of(X, SetId, Ss).
element_of(X, SetId, [set(Xs) | Ss]) <=> set(SetId, Xs), element_of(X, SetId, Ss).

lt(X, Y) <=> nonvar(X), integer(Y) | geq(Y, X).
gt(X, Y) <=> nonvar(X), integer(Y) | leq(Y, X).
geq(X, Y) <=> nonvar(X), integer(Y) | lt(Y, X).
gt(X, Y) <=> nonvar(X), integer(Y) | leq(Y, X).
neq(X, Y) <=> nonvar(X), integer(Y) | neq(Y, X).
eq(X, Y) <=> nonvar(X), integer(Y) | eq(Y, X).

element_of(X, SetId),
range(SetId, From, To),
eq(X, Y) <=>
    integer(Y), integer(From), integer(To) |
    From =< Y,
    Y =< To,
    X = Y.

element_of(X, Set1),
element_of(Y, Set2),
eq(X, Y) \
range(Set1, FromX, ToX),
range(Set2, FromY, ToY) <=>
        (FromX =\= FromY ; ToX =\= ToY) |
    From is max(FromX, FromY),
    To is min(ToX, ToY),
    range(Set1, From, To),
    range(Set2, From, To).


element_of(X, SetId) \
set_fragments(SetId, N),
range(SetId, From, To),
neq(X, Y) <=>
        integer(Y),
        From =< Y,
        Y =< To |
    To1 is Y - 1,
    To2 is Y + 1,
    N1 is N + 1,
    set_fragments(SetId, N1),
    range(SetId, From, To1),
    range(SetId, To2, To).

element_of(X, SetId) \
range(SetId, From, To),
geq(X, Y) <=>
        integer(Y),
        From =< Y,
        Y =< To |
    range(SetId, Y, To).

element_of(X, SetId) \
range(SetId, From, To),
leq(X, Y) <=>
        integer(Y),
        From =< Y,
        Y =< To |
    range(SetId, From, Y).

element_of(X, SetId) \
range(SetId, From, To),
gt(X, Y) <=>
        integer(Y),
        From =< Y,
        Y =< To |
    To1 is Y + 1,
    range(SetId, From, To1).

element_of(X, SetId) \
range(SetId, From, To),
lt(X, Y) <=>
        integer(Y),
        From =< Y,
        Y =< To |
    To1 is Y - 1,
    range(SetId, From, To1).

cleanup_set @ set(SetId, []), set_fragments(SetId, N) <=> N1 is N - 1, set_fragments(SetId, N1).

range(SetId, X, X) <=>
    set(SetId, [X]).

range(SetId, From, To) <=>
        From > To |
    set(SetId, []).

set(SetId, Xs),
set(SetId, Ys),
set_fragments(SetId, N) <=>
    N1 is N - 1,
    union(Xs, Ys, Zs),
    set(SetId, Zs),
    set_fragments(SetId, N1).

range(SetId, From, To) \
set(SetId, Ss) <=>
        From =< To,
        member(S, Ss), (S < From; To < S) |
    select(S, Ss, Ss1),
    set(SetId, Ss1).

range(SetId, From1, To1),
range(SetId, From2, To2) <=>
        From1 < From2, From2 < To1 |
    range(SetId, From2, To1),
    range(SetId, From2, To2).

range(SetId, From1, To1),
range(SetId, From2, To2) <=>
        From2 < To1, To1 < To2 |
    range(SetId, From1, To1),
    range(SetId, From2, To1).

range(SetId, From, To) \
range(SetId, From, To),
set_fragments(SetId, N) <=>
    N1 is N - 1,
    set_fragments(SetId, N1).

element_of(X, SetId),
set_fragments(SetId, 1),
set(SetId, [Y]) <=>
    X = Y.