"""Tests for coil.struct."""

import unittest
from coil import struct, errors

class BasicTestCase(unittest.TestCase):

    def setUp(self):
        # Use a tuple to preserve order
        self.data = (('first', {
                        'string': "something",
                        'float': 2.5,
                        'int': 1 }),
                    ('second', "something else"),
                    ('last', [ "list", "of", "strings" ]))
        self.struct = struct.Struct(self.data)

    def testFirstLevelContains(self):
        for key in ('first', 'second', 'last'):
            self.assert_(key in self.struct)

    def testSecondLevelContains(self):
        for key in ('string', 'float', 'int'):
            self.assert_(key in self.struct['first'])

    def testKeyOrder(self):
        self.assertEquals(self.struct.keys(), ['first', 'second', 'last'])

    def testGetItem(self):
        self.assertEquals(self.struct['second'], "something else")

    def testGetSimple(self):
        self.assertEquals(self.struct.get('second'), "something else")

    def testGetDefault(self):
        self.assertEquals(self.struct.get('bogus', "awesome"), "awesome")

    def testGetPath(self):
        self.assertEquals(self.struct.get('first.int'), 1)

    def testGetParent(self):
        child = self.struct['first']
        self.assertEquals(child.get('..second'), "something else")

    def testGetRoot(self):
        child = self.struct['first']
        self.assertEquals(child.get('@root.second'), "something else")

    def testIterItems(self):
        itemlist = [("one", 1), ("two", 2), ("three", 3)]
        self.assertEquals(list(struct.Struct(itemlist).iteritems()), itemlist)

    def testKeyMissing(self):
        self.assertRaises(struct.errors.KeyMissingError,
                lambda: self.struct['bogus'])
        self.assertRaises(struct.errors.KeyMissingError,
                lambda: self.struct.get('bad'))

    def testKeyType(self):
        self.assertRaises(struct.errors.KeyTypeError,
                lambda: self.struct[None])
        self.assertRaises(struct.errors.KeyTypeError,
                lambda: self.struct.get(None))

    def testKeyValue(self):
        self.assertRaises(struct.errors.KeyValueError,
                lambda: self.struct['first#'])
        self.assertRaises(struct.errors.KeyValueError,
                lambda: self.struct.get('first..second'))

    def testDict(self):
        self.assertEquals(self.struct['first'].dict(), dict(self.data[0][1]))

class ExpansionTestCase(unittest.TestCase):

    def testExpandGet(self):
        root = struct.Struct()
        root["foo"] = "bbq"
        root["bar"] = "omgwtf${foo}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}")
        self.assertEquals(root.get('bar', expand=True), "omgwtfbbq")

    def testExpandError(self):
        root = struct.Struct()
        root["bar"] = "omgwtf${foo}"
        self.assertEquals(root.get('bar'), "omgwtf${foo}")
        self.assertRaises(KeyError, root.get, 'bar', expand=True)

    def testExpandSilent(self):
        root = struct.Struct()
        root["bar"] = "omgwtf${foo}"
        self.assertEquals(root.get('bar', None, True, True), "omgwtf${foo}")
