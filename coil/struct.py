# Copyright (c) 2005-2006 Itamar Shtull-Trauring.
# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Struct is the core object in Coil.

Struct objects are similar to dicts except they are intended to be used
as a tree and can handle relative references between them.
"""

from __future__ import generators

import re
from UserDict import DictMixin

from coil import tokenizer, errors

class Path(tuple):

    KEY = re.compile(r'^%s$' % tokenizer.Tokenizer.KEY_REGEX)
    PATH = re.compile(r'^%s$' % tokenizer.Tokenizer.PATH_REGEX)

    def __new__(cls, path):
        if isinstance(path, Path):
            return path
        elif isinstance(path, basestring):
            path = cls._parse(path)
        else:
            raise errors.KeyTypeError(self, path)

        return super(Path, cls).__new__(cls, path)

    def __str__(self):
        # Insert the self reference . if needed
        if not self[0]:
            pretty = [""] + list(self)
        else:
            pretty = self

        return ".".join(pretty)

    @classmethod
    def _parse(cls, path):
        new = path.split(path, ".")

        # Remove the self reference . if it is there
        if not new[0]:
            new.pop(0)

        for i in xrange(new):
            if new[i]:
                break

        for i in xrange(i, new):
            if not new[i]:
                raise errors.KeyValueError(self, path)
            if not cls.KEY.match(new[i])
                raise errors.KeyValueError(self, path)

        return new

    @classmethod
    def validate_key(cls, key):
        """Check if the given key is valid.

        :rtype: bool
        """
        return bool(cls.KEY.match(key))

    @classmethod
    def validate_path(cls, path):
        """Check if the given path is valid.

        :rtype: bool
        """
        return bool(cls.PATH.match(path))

class Element(tokenizer.Location):

    #: Signal :meth:`get` to raise an error if key is not found
    _raise = object()

    def __init__(self, container=None, name=None, location=None):
        super(Element, self).__init__(location)
        self.container = container
        self.name = name
        self.done = False

    def get(self, path, default=Element._raise):
        raise Exception("unimplemented")

    def expand(self):
        self.done = True

    def _get_path(self, path, default):
        if not isinstnace(path, Path):
            path = Path(path)

        current = self
        for key in path:
            if not key:
                current = current.container
                if not current:
                    raise errors.StructError(self, "Reference past root: %s" % path)
            elif key == "@root":
                while current.container:
                    current = current.container
            else:
                current = current.get(key, default)

        return current


class Link(Element):

    def __init__(self, taget, container=None, name=None, location=None):
        super(Link, self).__init__(container, name, location)
        self.target = target
        self.value = None

    def __str__(self):
        return "<Link %s: %s>" % (self.path(), self.target)

    def get(self, path, default=Element._raise):
        if self.done:
            value = self.value
        else:
            value = self.container.get(path, default)

        if path:
            value = value.get(path, default)

        return value

    def expand(self):
        if not self.done:
            self.value = self.container.get(self.target)
            super(Link, self).expand()

class Value(Element):

    _EXPAND = re.compile(r'\$\{(%s)\}' % tokenizer.Tokenizer.PATH_REGEX)

    def __init__(self, value, container=None, name=None, location=None):
        super(Value, self).__init__(container, name, location)

        if not isinstance(value, (basestring, int, float, None.__class__)):
            raise Exception("TODO")

        self.value = value

    def __str__(self):
        return "<Value %s: %r>" % (self.path(), self.value)

    def get(self, path, default=Element._raise):
        assert not path
        value = self.value

    def expand(self):
        def expand_substr(match):
            subkey = match.group(1)
            try:
                subval = self.container.get(subkey)
                        defaults, ignore_missing, _block)
            except errors.KeyMissingError, ex:
                if ignore_missing is True or ex.key in ignore_missing:
                    return match.group(0)
                else:
                    raise

            if not isinstance(subval, basestring):
                subval = str(subval)

            return subval

        if not self.done:
            if isinstance(self.value, basestring):
                self.value = self._EXPAND.sub(expand_substr, self.value)
            super(Value, self).expand()

class Delete(Element):

    def get(self, path, default=Element._raise):
        assert not path
        if default is self._raise:
            raise errors.KeyMissingError(self, key)
        else:
            return default

    def expand(self):
        if not self.done:
            self.container.get(self.target)
            super(Link, self).expand()

class List(Element):

    def __init__(self, container, name, seq=(), location=None):
        super(List, self).__init__(container, name, location)
        raise Exception("TODO")

class Struct(Element, DictMixin):
    """A dict-like object for use in trees."""

    def __init__(self, base=(), container=None, name=None, location=None):
        """
        :param base: A *dict*, *Struct*, or a sequence of (key, value)
            tuples to initialize with. Any child *dict* or *Struct*
            will be recursively copied as a new child *Struct*.
        :param container: the parent *Struct* if there is one.
        :param name: The name of this *Struct* in *container*.
        :param location: The where this *Struct* is defined.
            This is normally only used by the :class:`Parser
            <coil.parser.Parser>`.
        """

        super(Struct, self).__init__(container, name, location)
        self._values = {}
        self._order = []

        if hasattr(base, 'iteritems'):
            base_iter = base.iteritems()
        else:
            base_iter = iter(base)

        for key, value in base_iter:
            if isinstance(value, (Struct, dict)):
                value = self.__class__(value)
            elif isinstance(value, list):
                value = list(value)
            self[key] = value

    def __contains__(self, key):
        return key in self._values

    def __iter__(self):
        """Iterate over the ordered list of keys."""
        iter(self._order)

    def __len__(self):
        return len(self._values)

    def get(self, path, default=_raise):
        """Get a value from any :class:`Struct` in the tree.

        :param path: key or arbitrary path to fetch.
        :param default: return this value if item is missing.
            Note that the behavior here differs from a *dict*.
            If *default* is unspecified and missing a
            :exc:`~errors.KeyMissingError` will be raised as
            __getitem__ does, not return *None*.

        :return: The fetched item or the value of *default*.
        """

        if not isinstance(path, Path):
            path = Path

        if not path:
            return self
        elif len(path) == 1:
            try:
                return self._values[path[0]]
            except KeyError:
                if default is self._raise:
                    raise errors.KeyMissingError(self, key)
                else:
                    return default
        else:
            return self._get_path(path, default)

    __getitem__ = get

    def set(self, path, value, location=None):
        """Set a value in any :class:`Struct` in the tree.

        :param path: key or arbitrary path to set.
        :param value: value to save.
        :param location: defines where this value was defined.
            Set to :data:`Struct.keep` to not modify the location if it
            is already set, this is used by :meth:`expanditem`.
        """

        if not isinstance(path, Path):
            path = Path

        if not path:
            assert 0
        elif len(path) == 1:
            if not isinstance(value, Element):
                value = Value(value, self, path[0], location)
            elif not value.container:
                value.container = self
                value.name = path[0]

            self._values[key] = value
            if key not in self._order:
                self._order.append(key)

            self.done = False
        else:
            parent = self._get_path(path[:-1])
            parent.set(path[-1], value, location)

    __setitem__ = set

    def __delitem__(self, path):
        self.set(path, Delete())

    def keys(self):
        """Get an ordered list of keys."""
        return list(self)

    def attributes(self):
        """Alias for :meth:`keys`.

        Only for compatibility with Coil <= 0.2.2.
        """
        return self.keys()

    def has_key(self, key):
        """True if key is in this :class:`Struct`"""
        return key in self

    def iteritems(self):
        """Iterate over the ordered list of (key, value) pairs."""
        for key in self:
            yield key, self[key]

    def expand(self, defaults=(), ignore_missing=(), recursive=True, _block=()):
        """Expand all :class:`Link` and sub-string variables in this
        and, if recursion is enabled, all child :class:`Struct`
        objects. This is normally called during parsing but may be
        useful if more control is required.

        This method modifies the tree!

        :param defaults: See :meth:`expandvalue`
        :param ignore_missing: :meth:`expandvalue`
        :param recursive: recursively expand sub-structs
        :type recursive: *bool*
        :param _block: See :meth:`expandvalue`
        """

        for key, value in self._values.iteritems():
            value.expand()

        abspath = self.path()
        if abspath in _block:
            raise errors.StructError(self, "Circular reference to %s" % abspath)

        _block = list(_block)
        _block.append(abspath)

        for key in self:
            value = self.expanditem(key, defaults, ignore_missing, _block)
            self.set(key, value, self.keep)
            if recursive and isinstance(value, Struct):
                value.expand(defaults, ignore_missing, True, _block)

    def expanditem(self, path, defaults=(), ignore_missing=(), _block=()):
        """Fetch and expand an item at the given path. All :class:`Link`
        and sub-string variables will be followed in the process. This
        method is a no-op if value is a :class:`Struct`, use the
        :meth:`Struct.expand` method instead.

        This method does not make any changes to the tree.

        :param path: A key or arbitrary path to get.
        :param defaults: See :meth:`expandvalue`
        :param ignore_missing: See :meth:`expandvalue`
        :param _block: See :meth:`expandvalue`
        """

        parent, key = self._get_next_parent(path)

        if parent is self:
            abspath = self.path(key)
            if abspath in _block:
                raise errors.StructError(self,
                        "Circular reference to %s" % abspath)

            _block = list(_block)
            _block.append(abspath)

            try:
                value = self[key]
            except errors.KeyMissingError:
                if key in defaults:
                    return defaults[key]
                else:
                    raise

            return self.expandvalue(value, defaults, ignore_missing, _block)
        else:
            return parent.expanditem(key, defaults, ignore_missing, _block)

    def expandvalue(self, value, defaults=(), ignore_missing=(), _block=()):
        """Use this :class:`Struct` to expand the given value. All
        :class:`Link` and sub-string variables will be followed in
        the process. This method is a no-op if value is a
        :class:`Struct`, use the :meth:`expand` method instead.

        This method does not make any changes to the tree.

        :param value: Any value to expand, typically a
            :class:`Link` or string.
        :param defaults: default values to use if undefined.
        :type defaults: *dict*
        :param ignore_missing: a set of keys that are ignored if
            undefined and not in defaults. If simply set to True
            then all are ignored. Otherwise raise
            :exc:`~errors.KeyMissingError`.
        :type ignore_missing: *True* or any container
        :param _block: a set of absolute paths that cannot be expanded.
            This is only for use internally to avoid circular references.
        :type block: any container
        """

        def expand_substr(match):
            subkey = match.group(1)
            try:
                subval = self.expanditem(subkey,
                        defaults, ignore_missing, _block)
            except errors.KeyMissingError, ex:
                if ignore_missing is True or ex.key in ignore_missing:
                    return match.group(0)
                else:
                    raise

            return str(subval)

        def expand_link(link):
            try:
                subval = self.expanditem(link.path,
                        defaults, ignore_missing, _block)
            except errors.KeyMissingError, ex:
                if ignore_missing is True or ex.key in ignore_missing:
                    return link
                else:
                    raise

            # Structs and lists must be copied
            if isinstance(subval, Struct):
                subval = subval.copy()
            if isinstance(subval, list):
                subval = list(subval)

            return subval

        def expand_list(list_):
            for i in xrange(len(list_)):
                if isinstance(list_[i], basestring):
                    list_[i] = self.EXPAND.sub(expand_substr, list_[i])
                elif isinstance(list_[i], list):
                    expand_list(list_[i])

        # defaults should only contain simple keys, not paths.
        for key in defaults:
            assert "." not in key

        if isinstance(value, Struct):
            pass
        elif isinstance(value, basestring):
            value = self.EXPAND.sub(expand_substr, value)
        elif isinstance(value, Link):
            value = expand_link(value)
        elif isinstance(value, list):
            expand_list(value)

        return value

    def unexpanded(self, absolute=False, recursive=True):
        """Find a set of all keys that have not been expanded.
        This is generally only useful if :meth:`expand` was
        run with the ignore_missing parameter was set to see got
        missed.

        Normally only the short key name is given as it would be
        provided in defaults or ignore_missing parameters for the
        various expansion methods. Set absolute=True to return the
        full path for each key instead.

        :param absolute: Enables absolute paths.
        :type absolute: *bool*
        :param recursive: recursively search sub-structs
        :type recursive: *bool*

        :return: unexpanded keys
        :rtype: set
        """

        def normalize_key(key):
            if absolute:
                return self.path(key)
            else:
                return key.rsplit('.', 1).pop()

        def unexpanded_list(list_):
            keys = set()

            for item in list_:
                if isinstance(item, basestring):
                    for match in self.EXPAND.finditer(item):
                        keys.add(normalize_key(match.group(1)))
                elif isinstance(item, Link):
                    keys.add(normalize_key(item.path))
                elif isinstance(item, (list, tuple)):
                    keys += unexpanded_list(item)
                elif recursive and isinstance(item, Struct):
                    keys += item.unexpanded(absolute)

            return keys

        return unexpanded_list(self.values())

    def copy(self):
        """Recursively copy this :class:`Struct`"""

        return self.__class__(self)

    def dict(self):
        """Recursively copy this :class:`Struct` into normal *dict* objects"""

        new = {}
        for key, value in self.iteritems():
            if isinstance(value, Struct):
                value = value.dict()
            elif isinstance(value, dict):
                value = value.copy()
            elif isinstance(value, list):
                value = list(value)
            new[key] = value

        return new

    def path(self, path=None):
        """Get the absolute path of this :class:`Struct` if path is
        *None*, otherwise the relative path from this :class:`Struct`
        to the given path."""

        if path:
            parent, key = self._get_next_parent(path)

            if parent is self:
                return "%s.%s" % (self.path(), key)
            else:
                return parent.path(path)
        else:
            if not self.container:
                return "@root"
            else:
                return "%s.%s" % (self.container.path(), self.name)

    def string(self, strict=True, prefix=''):
        """Convert this :class:`Struct` tree to the coil text format.

        Note that if any value is a unicode string then this
        will return a unicode object rather than a str.

        :param strict: If True then fail if the tree contains any
            values that cannot be represented in the coil text format.
        :type strict: *bool*
        :param prefix: Start each line with the given prefix.
            Used internally to properly intend sub-structs.
        :type prefix: string
        """

        def stritem(item):
            # FIXME: unicode breaks this, we need to handle encodings
            # explicitly in Structs rather than just in Parser
            if isinstance(item, basestring):
                # Should we use """ for multi-line strings?
                item = item.replace('\\', '\\\\')
                item = item.replace('\n', '\\n')
                item = item.replace('"', '\\"')
                return '"%s"' % item
            elif isinstance(item, (list, tuple)):
                return "[%s]" % " ".join([stritem(x) for x in item])
            elif (isinstance(item, (int, long, float)) or
                    item in (True, False, None)):
                return str(item)
            else:
                raise errors.StructError(self,
                    "%s cannot be represented in the coil text format" % item)

        result = ""
        next_prefix = "%s    " % prefix

        for key, val in self.iteritems():
            # This should never happen, but might as well be safe
            assert self.KEY.match(key)

            result = "%s%s%s: " % (result, prefix, key)

            if isinstance(val, Struct):
                child = val.string(strict, "%s    " % prefix)
                if child:
                    result = "%s{\n%s\n%s}\n" % (result, child, prefix)
                else:
                    result += "{}\n"
            else:
                result = "%s%s\n" % (result, stritem(val))

        return result.rstrip()

    def __str__(self):
        return self.string()

    def __repr__(self):
        attrs = ["%s: %s" % (repr(key), repr(val))
                 for key, val in self.iteritems()]
        return "%s({%s})" % (self.__class__.__name__, ", ".join(attrs))

    @classmethod
    def validate_key(cls, key):
        """Check if the given key is valid.

        @rtype: bool
        """
        return bool(cls.KEY.match(key))

    @classmethod
    def validate_path(cls, path):
        """Check if the given path is valid.

        @rtype: bool
        """
        return bool(cls.PATH.match(path))

    def _get_next_parent(self, path, add_parents=False):
        """Returns the next Struct in a path and the remaining path.

        If the path is a single key just return self and the key.
        If add_parents is true then create parent Structs as needed.
        """

        if not isinstance(path, basestring):
            raise errors.KeyTypeError(self, path)

        if path.startswith("@root"):
            if self.container:
                parent = self.container
            else:
                parent = self
                path = path[5:]
        elif "." not in path:
            # Quick exit for the simple case...
            return self, path
        elif path.startswith(".."):
            if self.container:
                parent = self.container
            else:
                raise errors.StructError(self, "Reference past root")
            path = path[1:]
        elif path.startswith("."):
            parent = self
            path = path[1:]
        else:
            # check for mid-path parent references
            if ".." in path:
                raise errors.KeyValueError(self, path)

            split = path.split(".", 1)
            key = split.pop(0)
            if split:
                path = split[0]
            else:
                path = ""

            try:
                parent = self.get(key)
            except errors.KeyMissingError:
                if add_parents:
                    parent = self.__class__()
                    self.set(key, parent)
                else:
                    raise

            if not isinstance(parent, Struct):
                raise errors.ValueTypeError(self, key, type(parent), Struct)

        if parent is self and "." in path:
            # Great, we went nowhere but there is still somewhere to go
            parent, path = self._get_next_parent(path, add_parents)

        return parent, path


#: For compatibility with Coil <= 0.2.2, use KeyError or KeyMissingError
StructAttributeError = errors.KeyMissingError

class StructNode(object):
    """For compatibility with Coil <= 0.2.2, use :class:`Struct` instead."""

    def __init__(self, struct, container=None):
        # The container argument is now bogus,
        # just make sure it matches the struct.
        assert isinstance(struct, Struct)
        assert container is None or container == struct.container
        self._struct = struct
        self._container = struct.container

    def has_key(self, attr):
        return self._struct.has_key(attr)

    def get(self, attr, default=Struct._raise):
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
