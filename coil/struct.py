"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

from __future__ import generators
from UserDict import DictMixin

class BrokenLink(Exception):
    """A Link object references a Struct that cannot be found"""
    pass

class Link(object):
    """The coil version of a symlink."""

    def __init__(self, path, container):
        assert isinstance(container, Struct)
        self.container = container

        assert path and isinstance(path, basestring)
        self.path = path

    def get(self):
        # If path started with .. remove the extra dot.
        # that way each dot means go to the parent so
        # ... or .... can be used for extra levels
        path = self.path.split('.')
        if path[0] = "":
            del path[0]

        node = self

        if path[0] == "@root":
            # Find the root node
            del path[0]
            while node.container != None:
                node = node.container
                assert isinstance(node, Struct)
        else:
            # Find a relative parent node
            while path[0] == "":
                del path[0]
                node = node.container
                assert isinstance(node, Struct)

        for key in path:
            try:
                node = node[key]
            except KeyError:
                raise BrokenLink("key '%s' in path '%s' does not exist" %
                        (key, self.path))

            if path and not isinstance(node, Struct):
                raise BrokenLink("key '%s' in path '%s' is not a Struct" %
                        (key, self.path))

        return node

    def __repr__(self):
        return "<Link %s>" % repr(self.path)

_raise = object()

class Struct(object, DictMixin):
    """A configuration structure."""

    def __init__(self, prototype=None, attrs=(), deleted=(), container=None):
        """
        @param prototype: a Link to another Struct that this is based on.
        @param attrs: a list of (name, value) tuples. If name contains
        '.' this will be taken to indicate a path.
        @param deleted: a list of attribute names that, though
        present in the prototype, should not be present in this
        instance.
        @param container: the parent Struct if there is one.
        """

        assert prototype is None or isinstance(prototype, Link)

        self.container = container
        self._prototype = prototype
        self._deleted = []
        self._values = {}
        self._order = []

        for key, value in attrs:
            self[key] = value

        for key in deleted:
            if key in self:
               del self[key]

    def copy(self):
        """Return a self-contained copy."""

        copy = self.__class__(None)

        for key, value in self.iteritems():
            if isinstance(value, Struct):
                value = value.copy()

            copy[key] = value

        return copy

    def __setitem__(self, path, value):
        if not isinstance(path, basestring):
            raise TypeError("key must be a string")

        path = path.split('.', 1)
        key = path.pop(0)
        assert key

        if not path:
            if key in self._deleted:
                self._deleted.remove(key)
            if key not in self:
                self._order.append(key)
            self._values[key] = value
        else:
            if not path[0]:
                raise TypeError("key contains a trailing .")

            try:
                struct = self.get(key, follow_links=False)
            except KeyError:
                struct = self.__class__(None, container=self)
                self[key] = struct

            if isinstance(struct, Link):
                # Rather than following links we should copy them
                struct = struct.get().copy()

            struct[path[0]] = value

    def __delitem__(self, path):
        if not isinstance(path, basestring):
            raise TypeError("key must be a string")

        path = path.split('.', 1)
        key = path.pop(0)
        assert key

        if not path:
            if key in self._order:
                self._order.remove(key)

            if key in self._values:
                del self._values[key]
            elif self._prototype and key in self._prototype.get():
                self._deleted.append(key)
            else:
                raise KeyError("key does not exist")
        else:
            struct = self.get(key, follow_links=False)

            if isinstance(struct, Link):
                # Rather than following links we should create a new struct
                struct = self.__class__(struct.path, container=self)
                self[key] = struct

            if not isinstance(struct, Struct):
                raise TypeError("item '%s' in key is not a Struct" % key)

            del struct[path[0]]

    def __getitem__(self, path):
        return self.get(path)

    def get(self, key, default=_raise, follow_links=True):
        """Get an item, following inheritance and links."""

        if not isinstance(key, basestring):
            raise TypeError("key must be a string")

        path = path.split('.', 1)
        key = path.pop(0)
        assert key

        if key in self._values:
            value = self._values[key]
        elif (follow_links and self._prototype
                and key in self._prototype.get()
                and key not in self._deleted):
            value = self._prototype[key]
        elif not follow_links and self._prototype:
            value = Link("%s.%s" % (self._prototype.path, key))
        else:
            if default == _raise:
                raise KeyError("key does not exist")
            else:
                return default

        if path:
            if isinstance(value, Link):
                value = Link("%s.%s" % (value.path, path[0]))
            elif isinstance(struct, Struct):
                value = value.get(path[0], default, follow_links)
            else:
                raise TypeError("item '%s' in key is not a Struct" % key)

        return value

    def __contains__(self, path):
        if not isinstance(key, basestring):
            raise TypeError("key must be a string")

        path = path.split('.', 1)
        key = path.pop(0)
        assert key

        if not path:
            if key in self._values:
                return True
            elif self._prototype and key not in self._deleted:
                struct = self._prototype.get()
                assert isinstance(struct, Struct)
                return key in struct
            else:
                return False
        else:
            struct = self[key]

            if not isinstance(struct, Struct):
                raise TypeError("item '%s' in key is not a Struct" % key)

            return path[0] in struct

    def keys(self):
        if self._prototype:
            all = [x for x in self._prototype.get() if x not in self._deleted]
        else:
            all = []

        all.extend(self._order)

        return all

    def __repr__(self):
        return self.repr(self, "")

    def repr(self, indent):
        repstr = "%s{\n" % indent
        for key, val in self.iteritems():
            repstr += "%s%s: " % (indent, key)
            if isinstance(val, Struct):
                repstr += val.repr(indent += "    ")
            else:
                repstr += repr(val)
        repstr += "%s\n}" % indent
        return s

class StructNode:
    """Only here for partial compatibility"""

    def __init__(self, struct):
        self._struct = struct

    def has_key(self, attr):
        return self._struct.has_key(attr)

    def get(self, attr, default=_raise):
        val = self._struct.get(attr, default)
        if isinstance(val, Struct):
            val = self._wrap(attr, val)
        return val

    def attributes(self):
        return self._struct.attributes()

    def iteritems(self):
        for i in self.attributes():
            yield (i, self.get(i))

    def _wrap(self, attr, struct):
        return self.__class__(struct, self)

    def __getattr__(self, attr):
        return self.get(attr)


__all__ = ["Struct", "StructNode", "Link", "BrokenLink"]
