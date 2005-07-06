"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

from __future__ import generators
__metaclass__ = type

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
    """A configuration structure."""

    def __init__(self, prototype, attrs=(), deletedAttrs=()):
        """
        @param prototype: another Struct that acts as a prototype for
        this one.
        @param attrs: a list of (name, value) tuples. If name contains
        ':' this will be taken to indicate a path.
        @param deletedAttrs: a list of attribute names that, though
        present in the prototype, should not be present in this
        instance.
        """
        assert prototype is None or isinstance(prototype, Struct)
        self.prototype = prototype
        self._deletedAttrs = {}
        self._attrsOrder = []
        self._attrsDict = {}
        for key, value in attrs:
            self._add(key.split("."), value)
        for key in deletedAttrs:
            self._addDelete(key.split("."))

    def _addDelete(self, path):
        key = path.pop(0)
        assert key
        if not path:
            self._deletedAttrs[key] = True
        else:
            # XXX use contructor, maybe?, plus this is inefficient as hell
            self._attrsDict[key] = Struct(self.get(key))
            self._attrsDict[key]._addDelete(path)
    
    def _add(self, path, value):
        key = path.pop(0)
        assert key
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
            # XXX same as in _addDelete
            self._attrsDict[key] = Struct(self.get(key))
            self._attrsDict[key]._add(path, value)

    def get(self, attr):
        """Get an attribute, checking prototypes as necessary."""
        if attr in self._deletedAttrs:
            raise StructAttributeError, attr
        if attr in self._attrsDict:
            return self._attrsDict[attr]
        elif self.prototype is not None:
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
            if i not in self._deletedAttrs:
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

    def get(self, attr):
        val = self._struct.get(attr)
        if isinstance(val, Struct):
            val = self._wrap(attr, val)
        elif isinstance(val, Link):
            val = self._followLink(val)
        return val

    def iterkeys(self):
        return self._struct.attributes()
    
    def iteritems(self):
        for i in self.iterkeys():
            yield (i, self.get(i))
    
    def _followLink(self, link):
        node = self
        for p in link.path:
            if p is CONTAINER:
                node = node._container
            elif p is ROOT:
                while node._container != None:
                    node = node._container
            else:
                # XXX use get() if is Struct
                node = getattr(node, p)
        return node

    def _wrap(self, attr, struct):
        return self.__class__(struct, self)
    
    def __getattr__(self, attr):
        return self.get(attr)
