"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

__metaclass__ = type

PARENT = object()
ROOT = object()

class Link:
    """A link to a configuration atom."""

    def __init__(self, *path):
        self._path = path

    def follow(self, node):
        """Get item at end of path."""
        for p in self._path:
            if p is PARENT:
                node = node.__parent__
            elif p is ROOT:
                while node.__parent__ != None:
                    node = node.__parent__
            else:
                node = getattr(node, p)
        return node


class Struct:
    """A configuration structure.

    __extends__: another Struct that acts as a prototype for this one.
    __parent__: container.
    """

    def __init__(self, __extends__=None, **attrs):
        self.__extends__ = __extends__
        # XXX this is horrible, maybe __parent__ should be done using
        # another class that is tuple of (parent, struct) essentially
        self.__parent__ = None
        self._attrs = attrs
        for key, val in attrs.items():
            if isinstance(val, Struct):
                # create copy that has self as parent
                val = Struct(val)
                val.__parent__ = self
                self._attrs[key] = val

    def __get(self, attr, realNode):
        if self._attrs.has_key(attr):
            val = self._attrs[attr]
            if isinstance(val, Link):
                val = val.follow(realNode)
            return val
        elif self.__extends__ is not None:
            return self.__extends__.__get(attr, realNode)
        else:
            raise AttributeError, attr
    
    def __getattr__(self, attr):
        return self.__get(attr, self)


def test():
    imapClient = Struct(server=Struct(host="localhost", port=0),
                        username="",
                        password="")
    keychainImap = Struct(password="",
                          imap=Struct(imapClient, password=Link(PARENT, "password")))

    # XXX smartfrog would let us say, imap:username = 'joe',
    # imap:server:host = 'example.com'. perhaps niceties like that can
    # be done behind the scenes in the non-code config language,
    # or perhaps straight python should do them too
    joeKeychain = Struct(keychainImap, password="mypassword",
                         imap=Struct(keychainImap.imap, username="joe"))
    assert joeKeychain.imap.password == "mypassword"
    assert joeKeychain.imap.username == "joe"
    assert joeKeychain.imap.server.host == "localhost"
    print "OK!"


if __name__ == '__main__':
    test()
