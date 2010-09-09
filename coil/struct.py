# Copyright (c) 2005-2006 Itamar Shtull-Trauring.
# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Struct is the core object in Coil.

Struct objects are similar to dicts except they are intended to be used
as a tree and can handle relative references between them.
"""

from __future__ import generators

import re
try:
    from collections import OrderedDict
except ImportError:
    from coil.ordereddict import OrderedDict

from coil import tokenizer, errors


# Used by _expand_str()
_EXPAND_BRACES = re.compile("^(.*){([^}]+)}(.*)$")
_EXPAND_RANGE = re.compile("^(0*(\d+))\.\.(\d+)$")

def _expand_str(string):
    """Helper function for _expand_list to operate on individual strings"""

    if not isinstance(string, basestring):
        return [string]

    match = _EXPAND_BRACES.search(string)
    if not match:
        return [string]
    else:
        new = []
        prefix = match.group(1)
        postfix = match.group(3)

        for item in match.group(2).split(','):
            range = _EXPAND_RANGE.match(item)
            if range:
                fmt = "%%s%%0%dd%%s" % len(range.group(1))
                for i in xrange(int(range.group(2)), int(range.group(3))+1):
                    new.extend(_expand_str(fmt % (prefix, i, postfix)))
            else:
                new.extend(_expand_str("%s%s%s" % (prefix, item, postfix)))

        return new

def _expand_list(seq):
    """Expand {1..2} and {1,2} constructs in a list of strings.
    Although this would be a useful public function it is private for
    now since in the future I think I will provide a list subclass.
    """

    new = []
    for item in seq:
        new.extend(_expand_str(item))

    return new

def _copy_list_contents(seq, cls=list):
    """Recursively copy a list of lists"""
    for item in seq:
        if isinstance(item, list):
            yield cls(_copy_list_contents(item))
        else:
            yield item

def _copy_list(seq, cls=list):
    return cls(_copy_list_contents(seq, cls))


class Node(tokenizer.Location):
    """The base class for elements in a coil tree"""

    KEY = re.compile(r'^%s$' % tokenizer.Tokenizer.KEY_REGEX)
    PATH = re.compile(r'^%s$' % tokenizer.Tokenizer.PATH_REGEX)

    #: The parent node in the coil tree
    container = None
    #: The name of this node inside container
    node_name = None
    #: The absolute path of this node in the coil tree
    node_path = None
    #: The root node of the coil tree
    tree_root = None

    def __init__(self, container=None, name=None, location=None):
        """
        :param container: the parent *Struct* of this *Node*.
        :type container: :class:`Struct`
        :param name: The name of this *Node* in *container*.
        :type name: str
        :param location: original file location from the tokenizer
        :type location: :class:`Location <coil.tokenizer.Location>`
        """
        super(Node, self).__init__(location)
        self._set_container(container, name)

    def _set_container(self, container, name):
        if self.container is not None and self.container is container:
            pass
        elif container is not None and name:
            self.container = container
            self.node_name = name
            self.node_path = "%s.%s" % (container.node_path, name)
            self.tree_root = container.tree_root
        elif container is None:
            assert name is None or name == "@root"
            self.container = None
            self.node_name = "@root"
            self.node_path = "@root"
            self.tree_root = self
        else:
            assert 0

    @classmethod
    def validate_key(cls, key):
        """Check if the given key is valid.

        :param path: path to test
        :typo path: str
        :rtype: bool
        """
        return bool(cls.KEY.match(key))

    @classmethod
    def validate_path(cls, path):
        """Check if the given path is valid.

        :param path: path to test
        :typo path: str
        :rtype: bool
        """
        return bool(cls.PATH.match(path))

    def relative_path(self, path, ref=None):
        """Convert an absolute path into a relative path.
        The new path will be relative to this *Node*. If the given path
        is not absolute this function is a no-op. The ref parameter
        defaults to :attr:`node_path`.

        :param path: absolute path to translate
        :type path: str
        :param ref: reference path the translation is relative to
        :type ref: str
        :rtype: str
        """

        if not path.startswith("@root"):
            return path
        if ref is None:
            ref = self.node_path

        split_path = path.split('.')
        split_self = ref.split('.')

        common = 0
        len_self = len(split_self)
        for i in xrange(min(len_self, len(split_path))):
            if split_self[i] == split_path[i]:
                common = i
            else:
                break

        dots = len_self - common
        names = ".".join(split_path[common+1:])

        # Don't bother with leading . if possible
        if dots == 1 and names:
            return names
        else:
            return "."*dots + names

    def absolute_path(self, path, ref=None):
        """Convert a relative path into an absolute path.
        If the given path is not relative this function is a no-op.
        The ref parameter defaults to :attr:`path`.

        :param path: relative path to translate
        :type path: str
        :param ref: reference path the translation is relative to
        :type ref: str
        :rtype: str
        """

        if path.startswith("@root"):
            return path
        if ref is None:
            ref = self.node_path

        names = path.lstrip('.')
        dots = len(path) - len(names)
        split = ref.split('.')

        if dots > len(split):
            # What exception should this be?
            raise errors.CoilError(self, "Relative reference past root.")
        if dots > 1:
            split = split[:-dots+1]
        if names:
            split.append(names)
        return ".".join(split)

    def copy(self, container=None, name=None):
        """Return a self-contained copy of this Node,
        recursively copying any mutable child nodes.

        container and named are passed to the constructor.
        """
        if self.__class__ is Node:
            return Node(container, name, self)
        else:
            return self.__class__(self, container, name, self)


class Link(Node):
    """A temporary symbolic link to another item."""

    def __init__(self, path, container=None, name=None, location=None):
        """
        :param path: An absolute or relative path to point at.
        :type path: str
        :param container: the parent *Struct* of this *Node*.
        :type container: :class:`Struct`
        :param name: The name of this *Node* in *container*.
        :type name: str
        :param location: original file location from the tokenizer
        :type location: :class:`Location <coil.tokenizer.Location>`
        """
        super(Link, self).__init__(container, name, location)
        if isinstance(path, Link):
            path = path.path
        #self.link_path = self.absolute_path(path)
        self.path = path

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.path))

class List(Node, list):
    """A list that can copy itself recursively"""

    def __init__(self, sequence=(), container=None, name=None, location=None):
        list.__init__(self, _copy_list_contents(sequence, self.__class__))
        Node.__init__(self, container, name, location)

class Struct(Node, OrderedDict):
    """A dict-like object for use in trees."""

    EXPAND = re.compile(r'\$\{(%s)\}' % tokenizer.Tokenizer.PATH_REGEX)

    #: Signal :meth:`get` to raise an error if key is not found
    _raise = object()
    #: Signal :meth:`set` to preserve location data for key
    keep = object()

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
        OrderedDict.__init__(self)
        Node.__init__(self, container, name, location)

        # the list of child structs if this is a map, this map
        # copy kludge probably can go away when StructPrototype does.
        self._map = getattr(base, '_map', None)

        # load base and recursively copy any mutable types
        for key, value in getattr(base, 'iteritems', base.__iter__)():
            if isinstance(value, Struct):
                # This can be covered by Node once StructPrototype is gone
                self._set(key, self.__class__(value, self, key))
            elif isinstance(value, Node):
                self._set(key, value.copy(self, key))
            elif isinstance(value, dict):
                self._set(key, self.__class__(value, self, key))
            elif isinstance(value, list):
                self._set(key, List(value))
            else:
                self._set(key, value)

    # Raw get/set/del functions
    _get = OrderedDict.__getitem__
    _set = OrderedDict.__setitem__
    _del = OrderedDict.__delitem__

    # 3.x compat
    @property
    def name(self):
        return self.node_name

    @property
    def _path(self):
        return self.node_path

    def _set_container(self, container, name):
        super(Struct, self)._set_container(container, name)
        if container is not None:
            self._update_path()

    def _update_path(self):
        assert self.container is not None
        self.node_path = "%s.%s" % (self.container.node_path, self.node_name)
        for node in self.itervalues():
            if isinstance(node, Struct):
                node._update_path()

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

        try:
            parent, key = self._get_next_parent(path)
        except KeyError:
            if default is self._raise:
                raise
            else:
                return default

        if parent is self:
            if not key:
                value = self
            else:
                try:
                    value = self._get(key)
                except KeyError:
                    if default is self._raise:
                        raise errors.KeyMissingError(self, key)
                    else:
                        value = default
        else:
            value = parent.get(key, default)

        return value

    __getitem__ = get

    def set(self, path, value, location=None):
        """Set a value in any :class:`Struct` in the tree.

        :param path: key or arbitrary path to set.
        :param value: value to save.
        :param location: defines where this value was defined.
            Set to :data:`Struct.keep` to not modify the location if it
            is already set, this is used by :meth:`expanditem`.
        """

        parent, key = self._get_next_parent(path, True)

        if parent is self:
            if not key or not self.KEY.match(key):
                raise errors.KeyValueError(self, key)

            if isinstance(value, Struct):
                value._set_container(self, key)

            self._set(key, value)
        else:
            parent.set(key, value, location)

    __setitem__ = set

    def __delitem__(self, path):
        parent, key = self._get_next_parent(path)

        if parent is self:
            if not key:
                raise errors.KeyValueError(path)

            try:
                self._del(path)
            except KeyError:
                raise errors.KeyMissingError(self, key)
        else:
            del parent[key]

    def merge(self, other):
        """Recursively merge a coil :class:`Struct` tree.

        This is similar to :meth:`update` except that it will update
        the entire subtree rather than just this object.
        """

        for key, value in other.iteritems():
            if isinstance(value, Struct):
                dest = self.get(key, None)
                if not isinstance(dest, Struct):
                    dest = Struct(container=self, name=key)
                dest.merge(value)
                self._set(key, dest)
            else:
                self._set(key, value)

    def attributes(self):
        """Alias for :meth:`keys`.

        Only for compatibility with Coil <= 0.2.2.
        """
        return self.keys()

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

        abspath = self.path()
        if abspath in _block:
            raise errors.StructError(self, "Circular reference to %s" % abspath)

        _block = list(_block)
        _block.append(abspath)

        if self._map is not None:
            map = _expand_list(self._map)
            self._map = None
            structs = []
            lists = []

            # We don't use iter because this loop delete stuff
            for key in self.keys():
                value = self.expanditem(key, defaults, ignore_missing, _block)
                if isinstance(value, Struct):
                    structs.append((key, value))
                    del self[key]
                elif isinstance(value, list):
                    value = _expand_list(value)
                    if len(value) != len(map):
                        raise errors.StructError(self, "Invalid @map list: "
                                "expected length is %s, %s has length of %s" %
                                (len(map), key, len(value)))
                    lists.append((key, value))
                    del self[key]
                else:
                    self.set(key, value, self.keep)

            for key, orig in structs:
                for i, suffix in enumerate(map):
                    name = "%s%s" % (key, suffix)
                    if not self.validate_key(name):
                        raise errors.StructError(self, "Invalid @map list: "
                                "key contains invalid characters: %r" % suffix)
                    new = orig.copy(name=name, container=self)
                    self[name] = new

                    for item_key, item_values in lists:
                        new[item_key] = item_values[i]

                    if recursive:
                        new.expand(defaults, ignore_missing, True, _block)

        else:
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
                subval = List(subval)

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

        # allow ignore_missing=False
        if ignore_missing is False:
            ignore_missing = ()

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
                    keys.update(unexpanded_list(item))
                elif recursive and isinstance(item, Struct):
                    keys.update(item.unexpanded(absolute))

            return keys

        return unexpanded_list(self.values())

    def dict(self):
        """Recursively copy this :class:`Struct` into normal *dict* objects"""

        new = {}
        for key, value in self.iteritems():
            if isinstance(value, Struct):
                value = value.dict()
            elif isinstance(value, dict):
                value = value.copy()
            elif isinstance(value, list):
                value = _copy_list(value)
            new[key] = value

        return new

    def path(self, path=None):
        """Get the absolute path of this :class:`Struct` if path is
        *None*, otherwise the relative path from this :class:`Struct`
        to the given path."""

        if path:
            return self.absolute_path(path)
        else:
            return self._path

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
                item = item.replace('\r', '\\r')
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

    def __eq__(self, other):
        if isinstance(other, Struct):
            return self.items() == other.items()
        else:
            return self.dict() == dict(other)

    def __ne__(self, other):
        return not self == other

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
                    parent = self.__class__(container=self, name=key)
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
