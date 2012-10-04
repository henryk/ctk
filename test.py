#!/usr/bin/env python

from ctk import *

if __name__ == "__main__":
    s = Solver()
    s += Data("41") + ~Data("a4 1f 10") + TargetCRC("0f")
    s += ~Data("41 a4 1f 10") + Permute( Data("20"), Data("40"), ~Data("00")) + Data("00") + TargetCRC("d1")
    s += ~Data("41 a4 1f 10") + Data("3b 40 00 00") + TargetCRC("a2")
    
    s.search_post = [0]
    s.solve()
