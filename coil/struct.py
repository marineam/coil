"""Configuration is a tree of structs.

Structs can extend other structs (i.e. use another as a prototype).
"""

from __future__ import generators
__metaclass__ = type

class _Constant:

    def __init__(self, s):
        self.s = s

    def __deepcopy__(self, d):
        return self
    
    def __str__(self, other):
        return "<%s>" % self.s


ROOT = _Constant("ROOT")
CONTAINER = _Constant("CONTAINER")

class Link:
    """A lazy link to a configuration atom.

    Resolution will be done only when follow() is called.
    """

    def __init__(self, *path):
        if not path:
            raise ValueError, "must have at least one segment"
        self.path = list(path)

    def _relativize(self, depth):
        """Turn absolute path into relative path."""
        if self.path[0] == ROOT:
            self.path[:1] = [CONTAINER] * depth

    def __unicode__(self):
        return repr(self).decode("ascii")

    def __repr__(self):
        result = ["="]
        for p in self.path:
            if p is CONTAINER:
                result.append(".")
            elif p is ROOT:
                result.append("@root")
            else:
                result.append("." + p)
        return "".join(result)


class StructAttributeError(AttributeError):
    pass


_raise = object()

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

    def copy(self):
        """Return a self-contained copy."""
        copy = Struct()
        for name in self.attributes():
            copy._attrsOrder.append(name)
            value = self.get(name)
            if isinstance(value, Struct):
                value = value.copy()
            copy._attrsDict[name] = value
        return copy
    
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

    def get(self, attr, default=_raise):
        """Get an attribute, checking prototypes as necessary."""
        if attr in self._deletedAttrs:
            raise StructAttributeError, attr
        if attr in self._attrsDict:
            return self._attrsDict[attr]
        elif self.prototype is not None:
            return self.prototype.get(attr)
        else:
            if default is _raise:
                raise StructAttributeError, attr
            else:
                return default

    def has_key(self, attr):
        """Return if struct has this attribute."""
        if attr in self._deletedAttrs:
            return False
        if attr in self._attrsDict:
            return True
        if self.prototype is not None:
            return self.prototype.has_key(attr)
        return False
    
    def attributes(self):
        """Return list of all attributes."""
        if self.prototype is not None:
            for i in self.prototype.attributes():
                if i not in self._deletedAttrs:
                    yield i
        for i in self._attrsOrder:
            if i not in self._deletedAttrs:
                yield i

    def _quote(self, o):
        if isinstance(o, unicode):
            return u'"' + o + u'"'
        elif isinstance(o, list):
            return u"[" + u" ".join([self._quote(i) for i in o]) + u"]"
        else:
            return unicode(o)
    
    def _strBody(self, indent):
        l = []
        for key in self.attributes():
            prefix = "%s%s: " % (indent * " ", key)
            val = self.get(key)
            if isinstance(val, Struct):
                l.extend([prefix, "{\n", val._strBody(indent + 4),  (" " * indent), "}\n"])
            else:
                l.extend([prefix, self._quote(val), "\n"])
        return u"".join(l).encode("utf-8")
    
    def __str__(self):
        return "<Struct %x:\n%s>" % (id(self), self._strBody(2))
    
    def __repr__(self):
        return self._strBody(0)


class StructNode:
    """A wrapper for Structs that knows about containment."""

    def __init__(self, struct, container=None):
        self._struct = struct
        self._container = container

    def has_key(self, attr):
        return self._struct.has_key(attr)
    
    def get(self, attr, default=_raise):
        val = self._struct.get(attr, default)
        if isinstance(val, Struct):
            val = self._wrap(attr, val)
        elif isinstance(val, Link):
            val = self._followLink(val)
        return val

    def attributes(self):
        return self._struct.attributes()

    def iteritems(self):
        for i in self.attributes():
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


__all__ = ["Struct", "StructNode", "Link", "StructAttributeError"]
