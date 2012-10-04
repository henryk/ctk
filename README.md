# ctk

CRC Tool Kit - Python tools for working with CRCs.

The main functionality is a brute-force search (the search space is pruned
as soon as possible), that, when given a specification of data sequences
and the CRC values they should evaluate to, will try to find the CRC
parameters.

## CRC Solver

For the case when it is not exactly known over which sequences the CRC
is calculated it is possible to symbolically specify multiple alternate
possibilities using an embedded domain specific language based on Python
operator overloading.

Usage example:

    from ctk import *
    
    s = Solver()
    s += Data("41 8B 35 10") + TargetCRC("9e")
    s.solve()

In general one example will not be enough to uniquely restrict the
parameter space. Two examples will usually fix the polynom and inverse
parameters. If both are of the same length, the initial value and post
XOR value will still be free, since it's possible to give one for an
arbitrary value of the other. To circumvent that you may limit the
search space if you know or suspect a parameter (e.g. fix post XOR to 0):

    s = Solver()
    s += Data("41 8B 35 10") + TargetCRC("9e")
    s += Data("57 81 82 da") + TargetCRC("6d")
    s.search_post = [0]
    s.solve()

## Data variations

To specify potential variations a set of combining operators is provided
that allow examples to be built up from expressions and combinations of
expressions (`Data()` itself is an expression):
 * `Concat()`         (Operator `+` )
 * `Optional()`       (Operator `~` )
 * `Repeat()`         (Operator `* integer`  or  `* (integer, integer)` )
 * `Permute()`
 * `Combine()`


### Concat(a, b, …)
 simply concatenates the source expressions

### Optional(a)
 will either include `a` or not (yielding two variations)

### Repeat(a, min, max=1)
 repeats `a` for a fixed or variable number of repetitions.
 `Repeat(a, 2)` is equivalent to `Concat(a, a)`.
 Note that if a yields multiple variations the Cartesian product is
      generated (same as with `Concat()`).

### Permute(a, b, …, min=?, max=?)
 generates all permutations of the given elements. If `min` and/or
 `max` are specified it can additionally generate permutation that
 include only the given number of elements.

### Combine(a, b, …, min=?, max=?)
 generates combinations, similar to `Permute()` but only with
 elements in the given order. `Combine(a, b, c)` is equivalent to
 `Concat(a, b, c)`.


Example:

    s = Solver()
    s += Data("41 8B 35 10") + TargetCRC("9e")
    s += Data("57 81 82 da") + TargetCRC("6d")
    s += ~Data("57 81 82 da") + Data("20 40 00 00") + TargetCRC("7a")
    s.solve()
