# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Coil Parser"""

import os
import sys

from coil import tokenizer, struct, errors

_missing = object()

class StructPrototype(struct.Struct):
    """A temporary struct used for parsing only.

    This Struct tracks links and inheritance so they can be processed
    when parsing is all done. This is important because it allows us
    to do fancy things with inheritance and catch errors during
    parse-time rather than run-time.
    """

    def __init__(self, base=(), container=None, name=None):
        struct.Struct.__init__(self, base, container, name)

        # Secondary items are ones that are inherited via @extends or @file
        # They must be tracked separately so we can raise errors on
        # double adds and deletes in the primary values.
        self._secondary_values = {}
        self._secondary_order = []
        # _deleted is a list of items that exist in one of the parents
        # but have been removed from this Struct by ~foo tokens.
        self._deleted = []

    def __contains__(self, key):
        return key in self._values or key in self._secondary_values

    def _validate_doubleset(self, key):
        """Private: check that key has not been used (excluding parents)"""

        if key in self._deleted or key in self._values:
            raise errors.CoilStructError(self,
                    "Setting/deleting '%s' twice" % repr(key))

    def set(self, path, value, expand=None, silent=False):
        parent, key = self._get_path_parent(path)

        if parent is self:
            self._validate_doubleset(key)

            if path in self._secondary_values:
                del self._secondary_values[key]

            struct.Struct.set(self, key, value, expand, silent)
        else:
            parent.set(key, value, expand, silent)

    def delete(self, path):
        parent, key = self._get_path_parent(path)

        if parent is self:
            self._validate_doubleset(key)

            try:
                struct.Struct.delete(self, key)
            except KeyError:
                if path in self._secondary_values:
                    del self._secondary_values[key]
                    self._secondary_order.remove(key)
                else:
                    raise

            self._deleted.append(key)
        else:
            parent.delete(key)

    def get(self, path, default=_missing, expand=False, silent=False):
        parent, key = self._get_path_parent(path)

        if parent is self:
            try:
                return struct.Struct.get(self, key,
                        expand=expand, silent=silent)
            except KeyError:
                value = self._secondary_values.get(key, _missing)

                if value is not _missing:
                    return self._expand_item(key, value, expand, silent)
                elif default is not _missing:
                    return default
                else:
                    raise
        else:
            return parent.get(key, default, expand, silent)

    def __iter__(self):
        for key in self._secondary_order:
            yield key
        for key in self._order:
            yield key

    def extends(self, base, relative=False):
        """Add a struct as another parent.

        @param base: A Struct or dict to extend.
        @param relative: Convert @root links to relative links.
            Used when extending a Struct from another file.
        """

        for key, value in base.iteritems():
            if key in self or key in self._deleted:
                continue

            # Copy child Structs so that they can be edited independently
            if isinstance(value, struct.Struct):
                new = self.__class__(container=self, name=key)
                new.extends(value, relative)
                value = new

            # Convert absolute to relative links if required
            if (relative and isinstance(value, struct.Link) and
                    value.path.startswith("@root")):
                path = ""
                container = base
                while container.container:
                    container = container.container
                    path += "."
                path += value.path[5:]
                value.path = path

            self._secondary_values[key] = value
            self._secondary_order.append(key)


class Parser(object):
    """The standard coil parser"""

    def __init__(self, input_, path=None, encoding=None, silent=False):
        """
        @param input_: An iterator over lines of input.
            Typically a C{file} object or list of strings.
        @param path: Path to input file, used for errors and @file imports.
        @param encoding: Read strings using the given encoding. All
            string values will be C{unicode} objects rather than C{str}.
        @param silent: Ignore any errors while attempting to follow links.
        """

        if path:
            self._path = os.path.abspath(path)
        else:
            self._path = None

        self._encoding = encoding
        self._tokenizer = tokenizer.Tokenizer(input_, self._path, encoding)

        # Create the root Struct and parse!
        self._prototype = StructPrototype()

        while self._tokenizer.peek('~', 'PATH', 'EOF').type != 'EOF':
            self._parse_attribute(self._prototype)

        self._tokenizer.next('EOF')
        self._root = struct.Struct(self._prototype)
        self._root.expand(silent, True)

    def root(self):
        """Get the root Struct"""
        return self._root

    def prototype(self):
        """Get the raw unexpanded prototype, you probably don't want this."""
        return self._prototype

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self._root)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self._root)

    def _parse_attribute(self, container):
        """name: value"""

        token = self._tokenizer.next('~', 'PATH')

        if token.type == '~':
            token = self._tokenizer.next('PATH')

            try:
                container.delete(token.value)
            except errors.CoilStructError, ex:
                raise errors.CoilDataError(token, ex.message)
        else:
            self._tokenizer.next(':')

            if token.value[0] == '@':
                special = getattr(self, "_special_%s" % token.value[1:], None)
                if special is None:
                    raise errors.CoilSyntaxError(token,
                            "Unknown special attribute: %s" % token.value)
                else:
                    special(container)
            else:
                self._parse_value(container, token.value)

    def _parse_value(self, container, name):
        """path, number, or string"""

        token = self._tokenizer.peek('{', '[', '=',
                'PATH', 'INTEGER', 'FLOAT', 'STRING', 'BOOLEAN')

        if token.type == '{':
            # Got a struct, will be added inside _parse_struct
            self._parse_struct(container, name)
            value = None
        elif token.type == '[':
            # Got a list, will be added inside _parse_list
            self._parse_list(container, name)
            value = None
        elif token.type == '=':
            # Got a reference, chomp the =, save the link
            # I only support the = for backwards compatibility
            self._tokenizer.next('=')
            value = struct.Link(self._tokenizer.next('PATH'), container)
        elif token.type == 'PATH':
            # Got a reference, save the link
            value = struct.Link(self._tokenizer.next('PATH'), container)
        else:
            # Plain old boring values
            self._tokenizer.next('INTEGER', 'FLOAT', 'STRING', 'BOOLEAN')
            value = token.value

        if value is not None:
            try:
                container.set(name, value)
            except errors.CoilStructError, ex:
                raise errors.CoilDataError(token, ex.message)

    def _parse_struct(self, container, name):
        """{ attrbute... }"""

        token = self._tokenizer.next('{')

        try:
            new = StructPrototype()
            container.set(name, new)
        except errors.CoilStructError, ex:
            raise errors.CoilDataError(token, ex.message)

        while self._tokenizer.peek('~', 'PATH', '}').type != '}':
            self._parse_attribute(new)

        self._tokenizer.next('}')

    def _parse_list(self, container, name):
        """[ number or string ... ]"""

        valid = ('INTEGER', 'FLOAT', 'STRING', 'BOOLEAN')
        token = self._tokenizer.next('[')

        try:
            new = list()
            container.set(name, new)
        except errors.CoilStructError, ex:
            raise errors.CoilDataError(token, ex.message)

        while self._tokenizer.peek(']', *valid).type != ']':
            item = self._tokenizer.next(*valid)
            new.append(item.value)

        self._tokenizer.next(']')

    def _special_extends(self, container):
        """Handle @extends: some.struct"""

        token = self._tokenizer.next('PATH')

        try:
            parent = container.get(token.value)
        except errors.CoilStructError, ex:
            raise errors.CoilDataError(token, str(ex))

        container.extends(parent)

    def _extend_with_file(self, container, file_path, struct_path):
        """Parse another coil file and merge it into the tree"""

        coil_file = open(file_path)
        parent = self.__class__(coil_file, file_path,
                self._encoding).prototype()

        if struct_path:
            parent = parent.get(struct_path)

        container.extends(parent, True)

    def _special_file(self, container):
        """Handle @file"""

        token = self._tokenizer.next('[', 'STRING')

        if token.type == '[':
            # @file: [ "file_name" "substruct_name" ]
            file_path = self._tokenizer.next('STRING').value
            struct_path = self._tokenizer.next('STRING').value
            self._tokenizer.next(']')
        else:
            # @file: "file_name"
            file_path = token.value
            struct_path = ""

        if self._path and not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(self._path), file_path)

        if not os.path.isabs(file_path):
            raise errors.CoilDataError(token,
                    "Unable to find absolute path: %s" % file_path)

        try:
            self._extend_with_file(container, file_path, struct_path)
        except (IOError, errors.CoilStructError), ex:
            raise errors.CoilDataError(token, str(ex))

    def _special_package(self, container):
        """Handle @package"""

        token = self._tokenizer.next('STRING')
        try:
            package, path = token.value.split(":", 1)
        except ValueError:
            errors.CoilSyntaxError(token,
                    '@package value must be "package:path"')

        parts = package.split(".")
        parts.append("__init__.py")

        fullpath = None
        for directory in sys.path:
            if not isinstance(directory, basestring):
                continue
            if os.path.exists(os.path.join(directory, *parts)):
                fullpath = os.path.join(directory, *(parts[:-1] + [path]))
                break

        if not fullpath:
            raise errors.CoilDataError(token,
                    "Unable to find package: %s" % package)

        try:
            self._extend_with_file(container, fullpath, "")
        except (IOError, errors.CoilStructError), ex:
            raise errors.CoilDataError(token, str(ex))
