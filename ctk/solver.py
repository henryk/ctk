from crc import CRC

def _solve_internal(self, poly, inv, same_length, output):
    c = self.crc(self.order, poly, inv, 0, 0)
    
    ## This part of the algorithm fixes poly and inv and searches for
    ## overall successful pairs of init_value and post_xor
    ## To be overall successful a pair must yield correct results for
    ## at least one alternative in each dataset.
    ## That means: a) If no init_value/post_xor pair is
    ##   successful for one entire dataset, there can not be
    ##   an overall successful pair for this poly/inv combination
    ##   and we can abort this search branch
    ## b) The set of overall successful pairs is a subset of
    ##   per dataset successful pairs. Therefore, on datasets
    ##   after the first, we only need to check pairs that were
    ##   successful on all previous datasets.
    ## Further optimization: post_xor need not be attempted, but can
    ## be looked up: crc.finish() ^ potential_post_xor == given_crc
    ## (for potential_post_xor in search_post_xor) is equivalent to
    ## crc.finish() ^ given_crc in search_post_xor. This is faster
    ## than a manual comparison if search_post_xor is xrange(), and
    ## should fall back otherwise.

    pairs = {}
    for init in self.search_init:
        c._init = init
        
        ## Step 1: Go through the first dataset and generate
        ## candidate init_value/post_xor pairs. Abort this poly
        ## if none are found
        
        
        dataset = self.data[0]
        data_width = dataset.get_data_width()
        given_crc = dataset._get_crc()
        for alternative in dataset.expand():
            c.clear()
            
            for word in alternative:
                c.update(word, data_width)
            
            post = c.finish()^given_crc
            
            if post in self.search_post:
                ## Hit! Record this combination
                
                if not pairs.has_key( (init, post) ):
                    pairs[ (init, post) ] = []
                
                pairs[ (init, post) ].append( alternative )
    
    if len(pairs) == 0:
        return
    
    ## Step 2: Go through the rest of the datasets, and
    ## thin out the list generated in step 1, skip to next
    ## init_value if it becomes empty.
    
    for dataset in self.data[1:]:
        data_width = dataset.get_data_width()
        given_crc = dataset._get_crc()
        
        for init, post in pairs.keys():
            c._init = init
            
            hitone = False
            
            for alternative in dataset.expand():
                c.clear()
                
                for word in alternative:
                    c.update(word, data_width)
                
                if c.finish() ^ post == given_crc:
                    hitone = True
                    ## Hit! Record this alternative as matching
                    
                    pairs[ (init, post) ].append(alternative)
            
            if not hitone:
                ## Miss for all alternatives! Discard this pair, and go to next pair
                del pairs[ (init, post) ]
    
    if len(pairs) == 0:
        return
    
    ## Emit all found combinations
    
    for (init, post), alternatives in pairs.items():
        skip_this = False
        
        if same_length:
            l = len(alternatives[0])
            for alternative in alternatives:
                if l != len(alternative):
                    skip_this = True
                    break
        
        if not skip_this:
            lines = []
            lines.append("poly=%02X, inv=%r, init=%02X, post=%02X, success on:" % (poly, inv, init, post))
            for alternative in alternatives:
                lines.append("%3i: %s" % (len(alternative), " ".join(["%02X" % e for e in alternative])))
            output.put("\n".join(lines))


class _cacher:
    """"Evaluate Data or one of the combination operators' attributes
    on object creation, store the results and then just return the 
    stored results"""
    
    __slots__ = ["_o", "_r", "_e", "_c", "_w"]
    
    def __init__(self, o):
        self._o = o
        self._r = self._o.__repr__()
        self._e = tuple(self._o.expand())
        self._c = self._o._get_crc()
        self._w = self._o.get_data_width()
    
    def __repr__(self):
        return self._r

    def expand(self):
        return self._e
    
    def _get_crc(self):
        return self._c
    
    def get_data_width(self):
        return self._w

class Solver(object):
    """An object that keeps a list of given data value/CRC value examples and can be 
    instructed to search for matching CRC parameters.
    
    Publically modifiable attributes of instances are:
    search_poly: a sequence of polynom values to search, defaults to xrange(1<<order)
    search_inv: a sequence of 'inverse' attributes to search, defaults to [True, False]
    search_init: a sequence of init_value values to search, defaults to xrange(1<<order)
    search_post: a sequence of post_xor values to search, defaults to xrange(1<<order).
    
    When an object has been instantiated, data is added to it with the += operator:
    s = Solver()
    s += Data("3A") + TargetCRC("F0").
    s.solve(). """
    
    def __init__(self, crc=CRC, order=8):
        """Initialize a new Solver object.
        crc must be a Callable that returns a CRC or compatible object.
        order is the width of the CRC state register, e.g. 8 for 8-bit CRC."""
        self.crc = crc
        self.data = []
        self.order = order
        
        self.set_full_search()
    
    def set_full_search(self):
        """Reset attributes to do a full parameter space search:
        search_poly = xrange(1<<order)
        search_inv = [True, False]
        search_init = xrange(1<<order)
        search_post = xrange(1<<order)"""
        
        self.max_value = 1<<self.order
        self.search_poly = xrange(self.max_value)
        self.search_inv = [True, False]
        self.search_init = xrange(self.max_value)
        self.search_post = xrange(self.max_value)

    
    def __iadd__(self, data):
        "Operator to allow Data to be added with convenient syntax."
        
        self.data.append( _cacher(data) )
        return self
    
    
    def solve(self, same_length=False):
        """Try to find CRC parameter sets that work for all the given samples.
        Uses multiprocessing to spawn a worker pool equivalent in size to the number of CPUs."""
        print "Will solve:"
        for i in self.data:
            print i, "should result in CRC %02X" % i._get_crc()
            
            for d in i.expand():
                print d
        
            print
        
        print
        
        import multiprocessing
        manager = multiprocessing.Manager()
        pool = multiprocessing.Pool()
        output = manager.Queue()
        

        for poly in self.search_poly:
            for inv in self.search_inv:
                pool.apply_async(_solve_internal, (self, poly, inv, same_length, output))
                #_solve_internal(self, poly, inv, same_length, output)  ## For single processed testing purposes
        
        def printit(output):
            lines = output.get()
            while lines != "STOP":
                print lines
                lines = output.get()
        
        printer = multiprocessing.Process(target=printit, args=(output, ))
        printer.start()
        
        pool.close()
        pool.join()
        output.put("STOP")
        printer.join()
