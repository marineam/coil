"""Tests for coil.struct."""

from twisted.trial import unittest
from coil import struct


class InitialStructTestCase(unittest.TestCase):

    def setUp(self):
        server = struct.Struct(None, [('host', "localhost"),
                                      ('port', 0)])
        imapClient = struct.Struct(None,
                                   [('server', server),
                                    ('username', ""),
                                    ('password', "")])
        keychainImap = struct.Struct(None,
                              [('password', ""),
                               ('description', "a keychain"),
                               ('imap', struct.Struct(imapClient, [('password',  struct.Link(struct.CONTAINER, "password"))]))])
        self.joeKeychain = struct.Struct(keychainImap,
                                         [('password', "mypassword"),
                                          ('imap.username', "joe")])
        self.joenode = struct.StructNode(self.joeKeychain)
        self.nodesc = struct.Struct(self.joeKeychain, deletedAttrs=("description",))
        self.nodescNode = struct.StructNode(self.nodesc)

    def testAttribute(self):
        self.assertEquals(self.joenode.description, "a keychain")
        self.assertEquals(self.joenode.imap.server.host, "localhost")

    def testLink(self):
        self.assertEquals(self.joenode.imap.password, "mypassword")

    def testOverride(self):
        self.assertEquals(self.joenode.imap.username, "joe")

    def testDeletion(self):
        self.assert_(not hasattr(self.nodescNode, "description"))
        self.assertEquals(list(self.joeKeychain.attributes()), ["password", "description", "imap"])
        self.assertEquals(list(self.nodesc.attributes()), ["password", "imap"])


class StructTestCase(unittest.TestCase):
    """Tests for Struct class."""

    def testIterItems(self):
        """Test functionality of iteritems."""
        s = struct.Struct(None, [("value", 0), ("value2", [])])
        self.assertEquals(list(s.iteritems()),
                          [("value", 0), ("value2", [])])
    
    def testAttributePath(self):
        """Attributes can be looked up using __getattr__."""
        s = struct.Struct(None, [("value", 0)])
        pair = struct.Struct(None,
                             [("a1", s), ("a2", s), ("a1.value", 2)])
        n = struct.StructNode(pair)
        self.assertEquals(n.a1.value, 2)
        self.assertEquals(n.a2.value, 0)

    def testStructRendering(self):
        """Structs can be rendered to strings using coil.text format."""
        s = struct.Struct(None, [("float", 12.5),
                                 ("integer", 123),
                                 ("string", u'a\t\r"\nx!\u3456'),
                                 ("list", [12, "hello", []]),
                                 ("struct", struct.Struct(None, [("key", 12)]))])
        rep = repr(s)
        expected = u'''\
float: 12.5
integer: 123
string: "a\\t\\r\\"\\nx!\u3456"
list: [12 "hello" []]
struct: {
    key: 12
}
'''.encode("utf-8")
        self.assertEquals(rep, expected)

        # now try round-trip parse/render
        from coil import text
        self.assertEquals(repr(text.fromString(rep)), rep)
        

class NodeTestCase(unittest.TestCase):

    def testNodeMethods(self):
        s = struct.Struct(None, [("value", 0)])
        n = struct.StructNode(s)
        sub = struct.Struct(s)
        subn = struct.StructNode(sub)
        for o in (s, n, sub, subn):
            self.assertEquals(list(o.attributes()), ["value"])
            self.assertEquals(o.get("value"), 0)
            self.assertRaises(struct.StructAttributeError, o.get, "foo")
            self.assertEquals(o.get("foo", 2), 2)
            self.assertEquals(o.get("foo", None), None)
            self.assertEquals(o.has_key("value"), True)
            self.assertEquals(o.has_key("foo"), False)
