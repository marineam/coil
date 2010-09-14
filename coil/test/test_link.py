"""Tests for coil.struct.Link"""

import unittest
from coil import errors
from coil.struct import Node, Link

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        self.r = Node()
        self.a = Node(None, self.r, "a")
        self.b = Node(None, self.a, "b")

    def assertRelative(self, link, expect):
        relative = link.relative_path(link.link_path, '..')
        self.assertEquals(relative, expect)

    def assertAbsolute(self, link, expect):
        absolute = link.absolute_path(link.link_path, '..')
        self.assertEquals(absolute, expect)

    def testInit(self):
        w = Link("@root", self.r, "w")
        x = Link("i.j.k", self.r, "x")
        y = Link("..j.k", self.a, "y")
        z = Link("..k", self.b, "z")
        self.assertRelative(w, ".")
        self.assertAbsolute(w, "@root")
        self.assertRelative(x, "i.j.k")
        self.assertAbsolute(x, "@root.i.j.k")
        self.assertRelative(y, "..j.k")
        self.assertAbsolute(y, "@root.j.k")
        self.assertRelative(z, "..k")
        self.assertAbsolute(z, "@root.a.k")
        self.assertRaises(errors.CoilError, Link, "..z", self.r, "z")

    def testCopy1(self):
        x = Link("b", self.a, "x")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertRelative(x, "b")
        self.assertAbsolute(x, "@root.a.b")
        a2 = self.a.copy()
        x2 = x.copy(a2, "x")
        self.assertEquals(x2.node_path, "@root.x")
        self.assertRelative(x2, "b")
        self.assertAbsolute(x2, "@root.b")

    def testCopy2(self):
        x = Link("..i", self.a, "x")
        y = x.copy(self.b, "y")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertRelative(x, "..i")
        self.assertAbsolute(x, "@root.i")
        self.assertEquals(y.node_path, "@root.a.b.y")
        self.assertRelative(y, "..i")
        self.assertAbsolute(y, "@root.a.i")

    def testCopyTree1(self):
        x = Link("i", self.a, "x")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertEquals(x.link_path, "i")
        self.assertRelative(x, "i")
        self.assertAbsolute(x, "@root.a.i")
        y = x.copy(self.b, "y")
        self.assertEquals(y.node_path, "@root.a.b.y")
        self.assertEquals(y.link_path, "i")
        self.assertRelative(y, "i")
        self.assertAbsolute(y, "@root.a.b.i")

        r2 = self.r.copy()
        a2 = self.a.copy(r2, "a")
        b2 = self.b.copy(a2, "b")
        x2 = x.copy(a2, "x")
        y2 = y.copy(b2, "y")

        self.assertEquals(x2.node_path, "@root.a.x")
        self.assertEquals(x2.link_path, "i")
        self.assertRelative(x2, "i")
        self.assertAbsolute(x2, "@root.a.i")
        self.assertEquals(y2.node_path, "@root.a.b.y")
        self.assertEquals(y2.link_path, "i")
        self.assertRelative(y2, "i")
        self.assertAbsolute(y2, "@root.a.b.i")

    def testCopyTree2(self):
        x = Link("@root.a.i", self.a, "x")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertEquals(x.link_path, "@root.a.i")
        self.assertRelative(x, "i")
        self.assertAbsolute(x, "@root.a.i")
        y = x.copy(self.b, "y")
        self.assertEquals(y.node_path, "@root.a.b.y")
        self.assertEquals(y.link_path, "@root.a.i")
        self.assertRelative(y, "..i")
        self.assertAbsolute(y, "@root.a.i")

        r2 = self.r.copy()
        a2 = self.a.copy(r2, "a")
        b2 = self.b.copy(a2, "b")
        x2 = x.copy(a2, "x")
        y2 = y.copy(b2, "y")

        self.assertEquals(x2.node_path, "@root.a.x")
        self.assertEquals(x2.link_path, "@root.a.i")
        self.assertRelative(x2, "i")
        self.assertAbsolute(x2, "@root.a.i")
        self.assertEquals(y2.node_path, "@root.a.b.y")
        self.assertEquals(y2.link_path, "@root.a.i")
        self.assertRelative(y2, "..i")
        self.assertAbsolute(y2, "@root.a.i")

    def testCopySubTree1(self):
        x = Link("i", self.a, "x")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertEquals(x.link_path, "i")
        self.assertRelative(x, "i")
        self.assertAbsolute(x, "@root.a.i")
        y = x.copy(self.b, "y")
        self.assertEquals(y.node_path, "@root.a.b.y")
        self.assertEquals(y.link_path, "i")
        self.assertRelative(y, "i")
        self.assertAbsolute(y, "@root.a.b.i")

        a2 = self.a.copy()
        b2 = self.b.copy(a2, "b")
        x2 = x.copy(a2, "x")
        y2 = y.copy(b2, "y")

        self.assertEquals(x2.node_path, "@root.x")
        self.assertEquals(x2.link_path, "i")
        self.assertRelative(x2, "i")
        self.assertAbsolute(x2, "@root.i")
        self.assertEquals(y2.node_path, "@root.b.y")
        self.assertEquals(y2.link_path, "i")
        self.assertRelative(y2, "i")
        self.assertAbsolute(y2, "@root.b.i")

    def testCopySubTree2(self):
        x = Link("@root.a.i", self.a, "x")
        self.assertEquals(x.node_path, "@root.a.x")
        self.assertEquals(x.link_path, "@root.a.i")
        self.assertRelative(x, "i")
        self.assertAbsolute(x, "@root.a.i")
        y = x.copy(self.b, "y")
        self.assertEquals(y.node_path, "@root.a.b.y")
        self.assertEquals(y.link_path, "@root.a.i")
        self.assertRelative(y, "..i")
        self.assertAbsolute(y, "@root.a.i")

        a2 = self.a.copy()
        b2 = self.b.copy(a2, "b")
        x2 = x.copy(a2, "x")
        y2 = y.copy(b2, "y")

        self.assertEquals(x2.node_path, "@root.x")
        self.assertEquals(x2.link_path, "@root.i")
        self.assertRelative(x2, "i")
        self.assertAbsolute(x2, "@root.i")
        self.assertEquals(y2.node_path, "@root.b.y")
        self.assertEquals(y2.link_path, "@root.i")
        self.assertRelative(y2, "..i")
        self.assertAbsolute(y2, "@root.i")
