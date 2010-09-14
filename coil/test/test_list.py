"""Tests for coil.struct.Link"""

import unittest
from coil import errors
from coil.struct import Node, Leaf, List

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        self.r = Node()
        self.a = Node(None, self.r, "a")
        self.b = Node(None, self.a, "b")

    def testInit(self):
        x = List(["string"], self.r, "x")
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testSet(self):
        x = List([None], self.r, "x")
        x[0] = "string"
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testAppend(self):
        x = List([], self.r, "x")
        x.append("string")
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testExtend(self):
        x = List([], self.r, "x")
        x.extend(["string"])
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testInsert(self):
        x = List([], self.r, "x")
        x.insert(0, "string")
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testPop(self):
        x = List(["string"], self.r, "x")
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x.pop(0), str))

    def testIter(self):
        x = List(["string"], self.r, "x")
        for item in x:
            self.assert_(isinstance(item, str))

    def testGetSlice(self):
        x = List(["a", "b"], self.r, "x")
        y = x[1:]
        # Doubt returning list instead of List for __getslice__
        # really matters as long as __getitem__ is used for values.
        #self.assert_(isinstance(y, List))
        self.assertEquals(y, ["b"])
        self.assert_(isinstance(x._get(0), Leaf))
        self.assert_(isinstance(x[0], str))

    def testList(self):
        x = List(["a", "b"], self.r, "x")
        y = x.list()
        self.assertEquals(y, ["a", "b"])
        self.assert_(y.__class__ is list)
        self.assert_(isinstance(y[0], str))

