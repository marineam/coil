"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

__metaclass__ = type

import sets

class _Constant:

    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return self.s


CONTAINER = _Constant("CONTAINER")
ROOT = _Constant("ROOT")

class Link:
    """A lazy link to a configuration atom.

    Resolution will be done only when follow() is called.
    """

    def __init__(self, *path):
        self.path = path

    def __repr__(self):
        return "--> %s" % (":".join([repr(i) for i in self.path]),)


class StructAttributeError(AttributeError):
    pass


class Struct:
    """A configuration structure.

    @param prototype: another Struct that acts as a prototype for
    this one.
    @param attrs: a list of (name, value) tuples. If name contains ':'
    this will be taken to indicate a path.
    @param deletedAttrs: a list of attribute names that, though
    present in the prototype, should not be present in this instance.
    """

    def __init__(self, prototype, attrs=(), deletedAttrs=()):
        assert prototype is None or isinstance(prototype, Struct)
        self.prototype = prototype
        self._deletedAttrs = sets.Set(deletedAttrs)
        self._attrsOrder = []
        self._attrsDict = {}
        for key, value in attrs:
            assert key not in self._deletedAttrs
            if ":" in key:
                self._add(key.split(":"), value)
            else:
                self._add([key], value)

    def _add(self, path, value):
        key = path.pop(0)
        if not path:
            if self.prototype is None:
                self._attrsOrder.append(key)
            else:
                try:
                    self.prototype.get(key)
                except StructAttributeError:
                    self._attrsOrder.append(key)
            self._attrsDict[key] = value
        else:
            if not self._attrsDict.has_key(key):
                self._attrsDict[key] = Struct(self.prototype.get(key))
            self._attrsDict[key]._add(path, value)

    def get(self, attr):
        """Get an attribute, checking prototypes as necessary."""
        if self._attrsDict.has_key(attr):
            return self._attrsDict[attr]
        elif self.prototype is not None and attr not in self._deletedAttrs:
            return self.prototype.get(attr)
        else:
            raise StructAttributeError, attr

    def attributes(self):
        """Return list of all attributes."""
        if self.prototype is not None:
            for i in self.prototype.attributes():
                if i not in self._deletedAttrs:
                    yield i
        for i in self._attrsOrder:
            yield i
    
    def _strBody(self, indent):
        l = []
        for key in self.attributes():
            prefix = "%s%s: " % (indent * " ", key)
            val = self.get(key)
            if isinstance(val, Struct):
                val = "\n" + val._strBody(len(prefix))
            else:
                val = repr(val)
            l.extend([prefix, val, "\n"])
        return "".join(l)
    
    def __str__(self):
        return "<Struct %x:\n%s>" % (id(self), self._strBody(2))


class StructNode:
    """A wrapper for Structs that knows about containment."""

    def __init__(self, struct, container=None):
        self._struct = struct
        self._container = container

    def _followLink(self, link):
        node = self
        for p in link.path:
            if p is CONTAINER:
                node = node._container
            elif p is ROOT:
                while node._container != None:
                    node = node._container
            else:
                node = getattr(node, p)
        return node
    
    def __getattr__(self, attr):
        val = self._struct.get(attr)
        if isinstance(val, Struct):
            val = StructNode(val, self)
        elif isinstance(val, Link):
            val = self._followLink(val)
        return val


def test():
    server = Struct(None, [('host', "localhost"),
                           ('port', 0)])
    imapClient = Struct(None,
                        [('server', server),
                         ('username', ""),
                         ('password', "")])
    keychainImap = Struct(None,
                          [('password', ""),
                           ('description', "a keychain"),
                           ('imap', Struct(imapClient, [('password',  Link(CONTAINER, "password"))]))])
    joeKeychain = Struct(keychainImap,
                         [('password', "mypassword"),
                          ('imap:username', "joe")])
    joenode = StructNode(joeKeychain)
    nodesc = Struct(joeKeychain, deletedAttrs=("description",))
    nodescNode = StructNode(nodesc) 
    assert joenode.description == "a keychain"
    assert joenode.imap.password == "mypassword"
    assert joenode.imap.username == "joe"
    assert joenode.imap.server.host == "localhost"
    print joeKeychain
    assert not hasattr(nodescNode, "description")
    assert list(joeKeychain.attributes()) == ["password", "description", "imap"]
    assert list(nodesc.attributes()) == ["password", "imap"]
    print nodesc
    print "OK!"


if __name__ == '__main__':
    test()
