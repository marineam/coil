"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

__metaclass__ = type

CONTAINER = object()
ROOT = object()

class Link:
    """A lazy link to a configuration atom.

    Resolution will be done only when follow() is called.
    """

    def __init__(self, *path):
        self.path = path

class StructAttributeError(AttributeError):
    pass


class Struct:
    """A configuration structure.

    @param prototype: another Struct that acts as a prototype for
    this one.
    @param attrs: a list of (name, value) tuples. If name contains ':'
    this will be taken to indicate a path.
    """

    def __init__(self, prototype, attrs=()):
        assert prototype is None or isinstance(prototype, Struct)
        self.prototype = prototype
        self._attrsOrder = []
        self._attrsDict = {}
        for key, value in attrs:
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
                    pass
                else:
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
        elif self.prototype is not None:
            return self.prototype.get(attr)
        else:
            raise StructAttributeError, attr

    def _strBody(self):
        if self.prototype is not None:
            s = self.prototype._strBody()
        else:
            s = ""
        return s + "".join([("%s: %s\n" % (key, self._attrsDict[key])) for key in self._attrsOrder])
    
    def __str__(self):
        return "<Struct: \n%s\n>" % (self._strBody(),)


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
    joeKeychain = StructNode(Struct(keychainImap,
                                    [('password', "mypassword"),
                                     ('imap:username', "joe")]))
    assert joeKeychain.description == "a keychain"
    assert joeKeychain.imap.password == "mypassword"
    assert joeKeychain.imap.username == "joe"
    assert joeKeychain.imap.server.host == "localhost"
    print joeKeychain._struct
    print "OK!"


if __name__ == '__main__':
    test()
