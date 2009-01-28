"""Coil Configuration Library

Coil Struct objects are similar to dicts except they are intended to be used
as a tree and can handle relative references between them.
"""

from __future__ import generators

import re
from UserDict import DictMixin

from coil import tokenizer, errors

_missing = object()

class Struct(object, DictMixin):
    """A configuration structure."""

    KEY = re.compile(r'^%s$' % tokenizer.Tokenizer.KEY_REGEX)
    PATH = re.compile(r'^%s$' % tokenizer.Tokenizer.PATH_REGEX)
    EXPAND = re.compile(r'\$\{(%s)\}' % tokenizer.Tokenizer.PATH_REGEX)

    def __init__(self, base=(), container=None, name=None, recursive=True):
        """
        @param base: A dict or Struct to initilize this one with.
        @param container: the parent Struct if there is one.
        @param name: The name of this Struct in container.
        @param recursive: Convert all mapping objects in base to Structs.
        """

        assert isinstance(container, Struct) or container is None
        assert isinstance(base, (list, tuple, dict, DictMixin))

        self.container = container
        self.name = name
        self._values = {}
        self._order = []

        if isinstance(base, (list, tuple)):
            base_iter = iter(base)
        else:
            base_iter = base.iteritems()

        for key, value in base_iter:
            if recursive and isinstance(value, (dict, DictMixin)):
                value = self.__class__(value, self, key)
            self[key] = value

    def copy(self):
        """Return a self-contained copy."""

        return self.__class__(self)

    def path(self):
        """Get the absolute path of a Struct in the tree"""

        if not self.container:
            return "@root"
        else:
            return "%s.%s" % (self.container.path(), self.name)

    def _validate_key(self, key):
        """Check that key doesn't contain invalid characters"""

        if not isinstance(key, basestring):
            raise errors.KeyTypeError(self, key)
        if not re.match(self.KEY, key):
            raise errors.KeyValueError(self, key)

    def __contains__(self, key):
        self._validate_key(key)
        return key in self._values

    def __setitem__(self, key, value):
        self._validate_key(key)

        if isinstance(value, Struct) and not value.container:
            value.container = self
            value.name = key

        if key not in self:
            self._order.append(key)

        self._values[key] = value

    def __delitem__(self, key):
        self._validate_key(key)

        try:
            self._order.remove(key)
        except ValueError:
            raise errors.KeyMissingError(self, key)

        try:
            del self._values[key]
        except KeyError:
            raise errors.KeyMissingError(self, key)

    def __getitem__(self, key):
        self._validate_key(key)

        try:
            return self._values[key]
        except KeyError:
            raise errors.KeyMissingError(self, key)

    def _get_path_parent(self, path):
        """Returns the second to last Struct and last key in the path."""

        if not isinstance(path, basestring):
            raise errors.KeyTypeError(self, path)
        if not re.match(self.PATH, path):
            raise errors.KeyValueError(self, path)

        split = path.split('.')

        # Relative path's start with .. which adds one extra blank string 
        if not split[0]:
            del split[0]

        # Walk the path if there is one
        struct = self
        for key in split[:-1]:
            if key == '@root':
                while struct.container:
                    struct = struct.container
                    assert isinstance(struct, Struct)
            elif not key:
                struct = struct.container
                if struct is None:
                    raise errors.CoilStructError(self,
                            "reference past tree root: %s" % path)
                assert isinstance(struct, Struct)
            else:
                try:
                    struct = struct[key]
                except KeyError:
                    raise errors.KeyMissingError(self, key, path)

                if not isinstance(struct, Struct):
                    raise errors.CoilStructError(self,
                            "key %s in path %s is not a Struct"
                            % (repr(key), repr(path)))

        return struct, split[-1]

    def _expand_vars(self, orig, expand, silent):
        def expand_one(match):
            name = match.group(1)
            value = None

            if hasattr(expand, "get"): # expand may simply be True
                value = expand.get(name, None)
            if value is None:
                value = self.get(name, None)

            if value is None and not silent:
                raise errors.KeyMissingError(self, name)
            elif value is None:
                return match.group(0)
            else:
                return value

        return self.EXPAND.sub(expand_one, orig)

    def get(self, path, default=_missing, expand=None, silent=False):
        """Get a value from any Struct in the tree"""

        parent, key = self._get_path_parent(path)

        try:
            value = parent[key]
        except KeyError:
            if default == _missing:
                raise errors.KeyMissingError(self, path)
            else:
                value = default

        if expand is not None:
            value = self._expand_vars(value, expand, silent)

        return value

    def set(self, path, value, expand=None, silent=False):
        """Set a value in any Struct in the tree"""

        parent, key = self._get_path_parent(path)

        if expand is not None:
            value = self._expand_vars(value, expand, silent)

        parent[key] = value

    def delete(self, path):
        """Delete a value from any Struct in the tree"""

        parent, key = self._get_path_parent(path)
        del parent[key]

    def keys(self):
        """Get a ordered list of keys"""
        return list(iter(self))

    def attributes(self):
        """For compatibility with Coil 0.2.2, use keys() instead!"""
        return self.keys()

    def __iter__(self):
        """Iterate over the list of keys"""
        for key in self._order:
            yield key

    def iteritems(self):
        """Iterate over the list of (key, value) pairs"""
        for key in self:
            yield key, self[key]

    def __str__(self):
        attrs = []
        for key, val in self.iteritems():
            if isinstance(val, Struct):
                attrs.append("%s: %s" % (repr(key), str(val)))
            else:
                attrs.append("%s: %s" % (repr(key), repr(val)))
        return "{%s}" % " ".join(attrs)

    def __repr__(self):
        attrs = ["%s: %s" % (repr(key), repr(val))
                 for key, val in self.iteritems()]
        return "%s({%s}" % (self.__class__.__name__, ", ".join(attrs))

# For compatibility with Coil 0.2.2, use KeyError instead!
StructAttributeError = errors.KeyMissingError

class StructNode(object):
    """For compatibility with Coil 0.2.2, use Struct instead!"""

    def __init__(self, struct, container=None):
        # The container argument is now bogus,
        # just make sure it matches the struct.
        assert isinstance(struct, Struct)
        assert container is None or container == struct.container
        self._struct = struct
        self._container = struct.container

    def has_key(self, attr):
        return self._struct.has_key(attr)

    def get(self, attr, default=_missing):
        val = self._struct.get(attr, default)
        if isinstance(val, Struct):
            val = self.__class__(val)
        return val

    def attributes(self):
        return self._struct.keys()

    def iteritems(self):
        for item in self._struct.iteritems():
            yield item

    def __getattr__(self, attr):
        return self.get(attr)
