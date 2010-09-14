"""Tests for coil.struct.Link"""

import unittest
from coil import errors
from coil.struct import Struct, List, Leaf

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        self.r = Struct({'a': {'b': {}}})

    def testInit(self):
        x = Leaf("string", self.r, "x")
        self.assertEquals(x, "string")
        self.assertEquals(x.node_path, "@root.x")

class ExpansionTestCase(unittest.TestCase):

    config = {
            'a': {
                'b': {
                    'i': "i",
                    'j': "j",
                },
                'k': 3,
            },
        }

    def setUp(self):
        self.r = Struct(self.config)

    def testNoop1(self):
        x = Leaf("string", self.r, "x")
        self.assertEquals(x, "string")
        x.expand()
        self.assertEquals(x, "string")

        x = Leaf(1, self.r, "x")
        self.assertEquals(x, 1)
        x.expand()
        self.assertEquals(x, 1)

    def testRelative1(self):
        x = Leaf("string${a.b.i}", self.r, "x")
        self.assertEquals(x, "string${a.b.i}")
        x.expand()
        self.assertEquals(x, "stringi")

    def testRelative2(self):
        x = Leaf("string${j}", self.r['a.b'], "x")
        self.assertEquals(x, "string${j}")
        x.expand()
        self.assertEquals(x, "stringj")

    def testRelative3(self):
        x = Leaf("string${..k}", self.r['a.b'], "x")
        self.assertEquals(x, "string${..k}")
        x.expand()
        self.assertEquals(x, "string3")

    def testAbsolute(self):
        x = Leaf("string${@root.a.k}", self.r['a.b'], "x")
        self.assertEquals(x, "string${@root.a.k}")
        x.expand()
        self.assertEquals(x, "string3")
