"""Tests for coil.struct.Node"""

import unittest
from coil import errors
from coil.struct import Node

class BasicTestCase(unittest.TestCase):

    def testInit(self):
        r = Node()
        a = Node(r, "a")
        b = Node(a, "b")
        self.assertEquals(b.node_name, "b")
        self.assertEquals(b.node_path, "@root.a.b")
        self.assert_(b.container is a)
        self.assert_(b.tree_root is r)

class PathTestCase(unittest.TestCase):

    def setUp(self):
        self.r = Node()
        self.a = Node(self.r, "a")
        self.b = Node(self.a, "b")

    def testRelative(self):
        self.assertEquals(self.r.relative_path("@root"), ".")
        self.assertEquals(self.r.relative_path("@root.a"), "a")
        self.assertEquals(self.r.relative_path("@root.a.b"), "a.b")
        self.assertEquals(self.r.relative_path("@root.a.b.c"), "a.b.c")
        self.assertEquals(self.a.relative_path("@root"), "..")
        self.assertEquals(self.a.relative_path("@root.a"), ".")
        self.assertEquals(self.a.relative_path("@root.a.b"), "b")
        self.assertEquals(self.a.relative_path("@root.a.b.c"), "b.c")
        self.assertEquals(self.b.relative_path("@root"), "...")
        self.assertEquals(self.b.relative_path("@root.a"), "..")
        self.assertEquals(self.b.relative_path("@root.a.b"), ".")
        self.assertEquals(self.b.relative_path("@root.a.b.c"), "c")
        self.assertEquals(self.b.relative_path("@root.x.y.z"), "...x.y.z")
        self.assertEquals(self.b.relative_path("@root.a.x.y"), "..x.y")

    def testAbsolute(self):
        self.assertEquals(self.r.absolute_path("."), "@root")
        self.assertEquals(self.r.absolute_path("a"), "@root.a")
        self.assertEquals(self.r.absolute_path(".a"), "@root.a")
        self.assertEquals(self.r.absolute_path("a.b"), "@root.a.b")
        self.assertEquals(self.b.absolute_path("."), "@root.a.b")
        self.assertEquals(self.b.absolute_path(".."), "@root.a")
        self.assertEquals(self.b.absolute_path("..."), "@root")
        self.assertEquals(self.b.absolute_path("x"), "@root.a.b.x")
        self.assertEquals(self.b.absolute_path(".x"), "@root.a.b.x")
        self.assertEquals(self.b.absolute_path("..x"), "@root.a.x")
        self.assertEquals(self.b.absolute_path("...x"), "@root.x")
        self.assertRaises(errors.CoilError,
                self.r.absolute_path, "..")
        self.assertRaises(errors.CoilError,
                self.a.absolute_path, "...")
        self.assertRaises(errors.CoilError,
                self.b.absolute_path, "....")
