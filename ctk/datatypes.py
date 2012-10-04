FORMAT_HEX_SPACE=0
FORMAT_INTEGER=1
FORMAT_BINARY=2

class _operations():
    def __add__(self, other):
        return Concat(self, other)
    
    def __invert__(self):
        return Optional(self)
    
    def __mul__(self, other):
        try:
            return Repeat(self, min=other[0], max=other[1])
        except:
            return Repeat(self, min=int(other), max=int(other))

class Permute(object, _operations):
    """Investigates a subset of all possible permutations of the input data items, possibly
    restricted by minimum and maximum of data items that must be used.
    
    Permute(Data("1"), Data("2"), Data("3")) will yield
    (1,2,3), (1,3,2), (2,1,3), (2,3,1), (3,1,2), (3,2,1).
    
    Permute(Data("1"), Data("2"), Data("3"), max=2) will yield
    (1,2), (1,3), (2,1), (2,3), (3,1), (3,2)."""
    
    def __init__(self, *values, **kw):
        """Takes a list of expressions and two optional keyword parameters:
        min: minimum number of arguments that must be used in the result (inclusive)
        max: maximum number of arguments that must be used in the result (inclusive),
        both default to the number of non-keyword arguments. min is bounded to max. """
        self.values = tuple(values)
        
        self.min = kw.get("min", len(self.values))
        self.max = kw.get("max", len(self.values))
        
        if self.min > self.max:
            self.min = self.max
    
    def __repr__(self):
        return "Permute(%s,min=%i,max=%i)" % (", ".join(map(repr, self.values)), self.min, self.max)
    
    def expand(self):
        import itertools
        
        def recursive_unroll(head, tail):
            if len(tail) == 0:
                for a in head.expand():
                    yield a
            else:
                for a in head.expand():
                    for b in recursive_unroll(tail[0], tail[1:]):
                        yield a + b
        
        for r in range(self.min, self.max+1):
            for order in itertools.permutations(self.values, r):
                for result in recursive_unroll(order[0], order[1:]):
                    yield result
    
    def _get_crc(self):
        for v in self.values:
            r = v._get_crc()
            if r is not None:
                return r
    
    def get_data_width(self):
        return self.values[0].get_data_width()

class Combine(Permute):
    """Investigates a subset of all possible combinations of the input data items, possibly
    restricted by minimum and maximum of data items that must be used.
    
    Combine(Data("1"), Data("2"), Data("3")) will yield
    (1,2,3).
    
    Comine(Data("1"), Data("2"), Data("3"), max=2) will yield
    (1,2), (1,3), (2,3)."""
    
    def __repr__(self):
        return "Combine(%s,min=%i,max=%i)" % (", ".join(map(repr, self.values)), self.min, self.max)
    
    def expand(self):
        import itertools
        
        def recursive_unroll(head, tail):
            if len(tail) == 0:
                for a in head.expand():
                    yield a
            else:
                for a in head.expand():
                    for b in recursive_unroll(tail[0], tail[1:]):
                        yield a + b
        
        for r in range(self.min, self.max+1):
            for order in itertools.combinations(self.values, r):
                for result in recursive_unroll(order[0], order[1:]):
                    yield result
    
class Concat(object, _operations):
    """Concatenates expressions.
    
    Concat(Data("1"), Data("2")) will yield
    (1,2)."""
    
    def __init__(self, *values):
        self.a = values[0]
        b = values[1:]
        
        if len(b) > 1:
            self.b = Concat(*b)
        else:
            self.b = b[0]
    
    def __repr__(self):
        return "%r + %r" % (self.a, self.b)

    def expand(self):
        for a in self.a.expand():
            for b in self.b.expand():
                yield a + b
    
    def _get_crc(self):
        return self.a._get_crc() or self.b._get_crc()
    
    def get_data_width(self):
        return self.a.get_data_width()


class Optional(object, _operations):
    """Makes an expression optional.
    
    Optional(Data("1")) will yield
    (), (1)."""
    
    def __init__(self, a):
        self.a = a
    
    def __repr__(self):
        return "Optional(%r)" % self.a
    
    def expand(self):
        yield tuple()
        for a in self.a.expand():
            yield a
    
    def _get_crc(self):
        return self.a._get_crc()
    
    def get_data_width(self):
        return self.a.get_data_width()

class Repeat(object, _operations):
    """Repeats an expression, a fixed number of times or over a range of repetitions.
    
    Repeat(Data("1"), min=3) will yield
    (1,1,1).
    
    Repeat(Data("1", min=1, max=3)) will yield
    (1), (1,1), (1,1,1)."""
    
    def __init__(self, a, min, max=1):
        self.a = a
        self.min = min
        self.max = max
        
        if self.max < self.min:
            self.max = self.min
    
    def __repr__(self):
        return "Repeat(%r, min=%i, max=%i)" % (self.a, self.min, self.max)
    
    def expand(self):
        def recursive_unroll(remainder):
            for a in self.a.expand():
                if remainder > 1:
                    for b in recursive_unroll(remainder - 1):
                        yield a + b
                else:
                    yield a
        
        for i in range(self.min, self.max+1):
            for result in recursive_unroll(i):
                yield result
    
    def _get_crc(self):
        return self.a._get_crc()
    
    def get_data_width(self):
        return self.a.get_data_width()

class Data(object, _operations):
    """A basic data item, a sequence of words of a fixed word length.
    
    These can be combined with one of the expression combinators in this
    module. For convenience, operator overloading is defined with the
    following operators:
    
    Data(a) + Data(b)   is  Concat(Data(a), Data(b))
    Data(a) * b         is  Repeat(Data(a), min=b, max=b)
    Data(a) * (b,c)     is  Repeat(Data(a), min=b, max=c)
    ~Data(a)            is  Optional(Data(a)).
    
    Combinations are valid and will be solved by Pythons normal operator
    precedence rules:
    Data(a) + ~Data(b) * c is  Concat(Data(a), Repeat(Optional(Data(b)), min=c, max=c).
    
    Note that this example is inefficient: 
    Repeat(Optional(Data(b)), min=c, max=c) will yield the same set of combinations as
    Repeat(Data(b), min=0, max=c), but will repeat many of the same outputs."""
    
    def __init__(self, value, format=FORMAT_HEX_SPACE, data_width=8):
        r"""Initializes a new Data item. The value can be given in multiple formats
        and will internally be converted to a list of words (as integers).
        
        FORMAT_HEX_SPACE: "3 14 0A" ->   (3, 20, 10)
        FORMAT_INTEGER:   (1, 2, 3) ->   (1, 2, 3)
        FORMAT_BINARY:    "3\x3 "  ->    (51, 3, 32)."""
        
        self.data_width = data_width
        
        if format == FORMAT_HEX_SPACE:
            self.value = tuple([int(e, 16) for e in value.split()])
        elif format == FORMAT_INTEGER:
            self.value = tuple(value)
        else:
            self.value = tuple(map(ord, value))
    
    def __repr__(self):
        return "%s(value='%s')" % (self.__class__.__name__, " ".join(["%02X" % e for e in self.value]))
    
    def expand(self):
        yield self.value
    
    def _get_crc(self):
        return None
    
    def get_data_width(self):
        # FIXME Is not properly implemented for mixed values
        return self.data_width

class TargetCRC(Data):
    """The target CRC that this expression should evaluate to.
    For convenience it is handled just as Data objects, though you should not
    add more than one (concatenation etc. will not work).
    
    Data("3A") + TargetCRC("F0")  specifies the single byte 0x3A as data that
    should result in the CRC 0xF0.
    Note: TargetCRC.data_width should be equal to CRC.order, which may be
    distinct from Data.data_width (e.g. 16-bit CRC over 8-bit 'words', that is,
    bytes)."""
    
    def expand(self):
        yield tuple()
    
    def _get_crc(self):
        return self.value[0]
