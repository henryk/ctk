class CRC(object):
    "A generic CRC generator"
    
    def __init__(self, order, polynom, inverse = False, init_value = 0, post_xor = 0):
        """Initialize a new CRC generator object.
        order is an integer specifying the width of the CRC register in bits, e.g. 8 for an 8-bit CRC.
        polynom is the CRC polynom as an integer.
        If inverse is true the shift direction on state update is reversed (shift left instead of shift right).
        init_value is the value the state register is set to at clear() time.
        post_xor is XORed onto the result before being returned by finish()."""
        self._order = order
        self._mask = (1<<order)-1
        self._poly = polynom
        self._inverse = inverse
        self._tap = [1, (1<<(order-1))][inverse]
        self._init = init_value
        self._post = post_xor
        self.clear()
    
    def clear(self):
        self._state = self._init
    
    def update(self, data, length):
        for i in range(length):
            b = bool(self._state & self._tap)
            d = bool((data>>i) & 1)
            if self._inverse:
                self._state = (self._state << 1) & self._mask
            else:
                self._state = (self._state >> 1) & self._mask
            if b ^ d:
                self._state = self._state ^ self._poly
    
    def finish(self):
        return self._state ^ self._post

    def map(self, expression):
        data_width = expression.get_data_width()
        
        for data in expression.expand():
            self.clear()
            for word in data:
                self.update(word, data_width)
            yield self.finish()
    
    def calculate(self, data):
        for result in self.map(data):
            return result # Only return the first result from the iterator
