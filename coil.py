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


class Struct:
    """A configuration structure.

    __extends__: another Struct that acts as a prototype for this one.
    """

    def __init__(self, __extends__=None, **attrs):
        self.__extends__ = __extends__
        self._attrs = attrs

    def get(self, attr):
        """Get an attribute, checking prototypes as necessary."""
        if self._attrs.has_key(attr):
            return self._attrs[attr]
        elif self.__extends__ is not None:
            return self.__extends__.get(attr)
        else:
            raise AttributeError, attr

        
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
    imapClient = Struct(server=Struct(host="localhost", port=0),
                        username="",
                        password="")
    keychainImap = Struct(password="",
                          imap=Struct(imapClient, password=Link(CONTAINER, "password")))

    # XXX smartfrog would let us say, imap:username = 'joe',
    # imap:server:host = 'example.com'. perhaps niceties like that can
    # be done behind the scenes in the non-code config language,
    # or perhaps straight python should do them too
    joeKeychain = StructNode(Struct(keychainImap, password="mypassword",
                                    imap=Struct(keychainImap.get("imap"), username="joe")))
    assert joeKeychain.imap.password == "mypassword"
    assert joeKeychain.imap.username == "joe"
    assert joeKeychain.imap.server.host == "localhost"
    print "OK!"


if __name__ == '__main__':
    test()
