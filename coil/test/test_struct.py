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

    def testAttributePath(self):
        s = struct.Struct(None, [("value", 0)])
        pair = struct.Struct(None,
                             [("a1", s), ("a2", s), ("a1.value", 2)])
        n = struct.StructNode(pair)
        self.assertEquals(n.a1.value, 2)
        self.assertEquals(n.a2.value, 0)
