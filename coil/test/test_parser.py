"""Tests for coil.tokenizer."""

import unittest
from coil import parser, tokenizer, struct

class ParserTestCase(unittest.TestCase):

    def testEmpty(self):
        root = parser.Parser([""]).root()
        self.assert_(isinstance(root, struct.Struct))
        self.assertEquals(len(root), 0)

    def testSingle(self):
        root = parser.Parser(["this: 'that'"]).root()
        self.assertEquals(len(root), 1)
        self.assertEquals(root['this'], "that")

    def testMany(self):
        root = parser.Parser(["this: 'that' int: 1 float: 2.0"]).root()
        self.assertEquals(len(root), 3)
        self.assertEquals(root['this'], "that")
        self.assert_(isinstance(root['int'], int))
        self.assertEquals(root['int'], 1)
        self.assert_(isinstance(root['float'], float))
        self.assertEquals(root['float'], 2.0)

    def testStruct(self):
        root = parser.Parser(["foo: { bar: 'baz' }"]).root()
        self.assert_(isinstance(root['foo'], struct.Struct))
        self.assertEquals(root['foo']['bar'], "baz")
