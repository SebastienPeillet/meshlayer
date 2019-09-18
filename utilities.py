# -*- coding: UTF-8 -*-

import time
import os
from math import log, exp as exp_
from collections import defaultdict

def complete_filename(name):
    return os.path.join(os.path.dirname(__file__), name)

def format_(min_, max_):
    format_ = "%.2e"
    if max_ < 10000 and abs(min_) >= 0.1:
        format_ = "%.2f"
    return format_

def multiplier(value):
    """return a couple of multiplier and text representing it that are appropiate for
    the specified range"""

    multiplyers = {1e-9:u" x 10⁻⁹", 1e-6:u" x 10⁻⁶", 1e-3:u" x 10⁻³", 1.0:u"", 1e3:u" x 10³", 1e6:u" x 10⁶", 1e9:u" x 10⁹"}
    mult = 1e-9
    for x in sorted(multiplyers.keys()):
        if x <= abs(value):
            mult = x
    return mult, multiplyers[mult]

def linemerge(lines):
    """Returns a (set of) LineString(s) formed by sewing together a multilinestring."""
    graph = defaultdict(set)
    # first build a bidirectional graph
    for line in lines:
        b = tuple(line[0])
        e = tuple(line[-1])
        graph[b].add(e)
        graph[e].add(b)
    for k, v in graph.iteritems():
        assert(len(v) in (1,2))

    # now consume the graph
    if not len(graph):
        return []

    def depth_first_append(graph, node):
        connected=[node]
        direction = "first"
        neigbors = graph[node]
        del graph[node]
        for n in neigbors:
            if n in graph:
                if direction == "first":
                    connected += depth_first_append(graph, n)
                #else:
                #    connected = list(reversed(depth_first_append(graph, n))) + connected
            direction = "second"
        return connected

    out = []
    while len(graph):
        nxt = graph.iterkeys().next()
        out.append(depth_first_append(graph, nxt))
    return out

# run as script for testing
if __name__ == "__main__":
    #@todo: unit test multiplier
    #@todo: unit test linemerge
    pass

class Timer(object):
    def __init__(self):
        self.start = time.time()
    def reset(self, text=""):
        s = self.start
        self.start = time.time()
        return "%30s % 8.4f sec"%(text, (self.start - s))



