# CHR(Python)
A _Constraint Handling Rules_ (CHR) implementation for _Python_.


# Example
Given the following _CHR(Python)_ program, saved in `fibonacci.chr`:

```
class Fibonacci.

constraints fib/1, result/1, read/1.

fib($N) <=> $N > 1 | fib($N-1), fib($N-2).
fib($N) <=> $N <= 1 | result($N).
result($N), result($M) <=> result($N+$M).
read($N), result($M) <=> $M = $N.
```

After compilation into `fibonacci.py`, this file contains a class `Fibonacci`,
which has the public methods `fib`, `result` and `read`.

It can be used as such:

```python
from fibonacci import Fibonacci

# Generates an isolated solver instance
solver = Fibonacci()

# Add fib(6) to the constraint store,
# and immediately starts computation.
solver.fib(6)
# At this point, the constraint store
# contains the constraint result(8),
# so this assertion should hold
assert ("result/1", 8) in solver.dump_chr_store()

# Generate a fresh and unbound logical variable
result = solver.fresh_var()

# read the result from the store
# this will add the constraint read(result)
# to the store, and start computation, which
# will then (due to the last rule) bind result
# to the value in the result constraint.
# (in this case 8)
solver.read(result)

# At this point, this assertion holds:
assert result == 8

# To actually extract the value from result,
# use chr.runtime.get_value:

from chr.runtime import get_value

assert not isinstance(result, int)
assert isinstance(get_value(result), int)
```


# Usage

## Command line tool
_TODO_

## Automatic compilation

Add the following lines to a `__init__.py` file of a package to automatically
compile all `*.chr` files in this folder.

```python
import os
from chr.core import chr_compile_module

chr_compile_module(os.path.dirname(__file__), verbose=True)
```
