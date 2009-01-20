"""Coil Parser"""

import os
import sys

from coil.tokenizer import Tokenizer, CoilSyntaxError
from coil.struct import Struct, StructError

class CoilDataError(CoilSyntaxError):
    pass

class Parser(object):
    """The standard coil parser"""

    def __init__(self, input_, path=None, encoding=None):
        if path:
            self._path = os.path.abspath(path)
        else:
            self._path = None

        self._encoding = encoding
        self._tokenizer = Tokenizer(input_, self._path, encoding)

        # Create the root Struct and parse!
        self._root = Struct()
        self._parse_struct_attributes(self._root)

    def root(self):
        """Get the root Struct"""
        return self._root

    def _expect(self, token, types):
        if token.type is None:
            raise CoilSyntaxError(token, "Unexpected end of input, "
                    "looking for: %s" % " ".join(types))

        if token.type not in types:
            if token.type == token.value:
                unexpected = repr(token.type)
            else:
                unexpected = "%s: %s" % (token.type, repr(token.value))

            raise CoilSyntaxError(token, "Unexpected %s, looking for %s" %
                    (unexpected, " ".join(types)))

    def _next(self, *types):
        token = self._tokenizer.next()
        if types:
            self._expect(token, types)
        return token

    def _peek(self, *types):
        token = self._tokenizer.peek()
        if types:
            self._expect(token, types)
        return token

    def _parse_struct(self, container=None, name=None):
        """{ ... }"""

        self._next('{')

        new = Struct(container=container, name=name)
        self._parse_struct_attributes(new)

        self._next('}')

        return new

    def _parse_struct_attributes(self, new_struct):
        """attribute..."""

        # Check for attempts to set and/or delete the same thing twice
        added = set()
        deleted = set()

        while self._peek().type not in (None, '}'):
            self._parse_attribute(new_struct, added, deleted)

    def _parse_attribute(self, container, added, deleted):
        """name: value"""

        token = self._peek('@', '~', 'ATOM')

        if token.type == '@':
            self._next()
            name = self._next('ATOM').value
            self._next(':')

            special = getattr(self, "_special_%s" % name, None)
            if special is None:
                raise CoilSyntaxError(token,
                        "Unknown special attribute: @%s" % name)
            else:
                special(container, added, deleted)

        elif token.type == '~':
            self._next()
            name = self._parse_name()

            if name in added:
                raise CoilDataError(token, "Attribute added and "
                        "deleted in the same structure: %s" % name)
            elif name in deleted:
                raise CoilDataError(token, "Attribute deleted twice "
                        "in the same structure: %s" % name)
            try:
                container.delete(name)
            except StructError, ex:
                raise CoilDataError(token, ex.message)

        else:
            name = self._parse_name()
            self._next(':')

            if name in added:
                raise CoilDataError(token, "Attribute added twice "
                        "in the same structure: %s" % name)
            elif name in deleted:
                raise CoilDataError(token, "Attribute added and "
                        "deleted in the same structure %s" % name)

            value = self._parse_value(container, name)
            try:
                container.set(name, value)
            except StructError, ex:
                raise CoilDataError(token, ex.message)

    def _parse_name(self):
        """ATOM[.ATOM]*"""

        name = self._next('ATOM').value

        while self._peek().type == '.':
            self._next()
            name = "%s.%s" % (name, self._next('ATOM').value)

        return name

    def _parse_value(self, container, name):
        """path, number, or string"""
        token = self._peek('{', '[', '@', '.', 'ATOM',
                'INTEGER', 'FLOAT', 'STRING')

        if token.type == '{':
            return self._parse_struct(container, name)
        elif token.type == '[':
            return self._parse_list()
        elif token.type in ('@', '.', 'ATOM'):
            return self._parse_and_follow_path(container)
        elif token.type in ('INTEGER', 'FLOAT', 'STRING'):
            self._next('INTEGER', 'FLOAT', 'STRING')
            return token.value

    def _parse_list(self):
        """[ number or string ... ]"""

        self._next('[')
        new = []

        while True:
            token = self._next(']', 'INTEGER', 'FLOAT', 'STRING')
            if token.type == ']':
                return new
            else:
                new.append(token.value)

    def _parse_and_follow_path(self, container):
        """(...*|@root)?ATOM(.ATOM)*"""

        token = self._next('.', '@', 'ATOM')
        path = token.value

        if token.type == '.':
            # There must be at least one more .
            self._next('.')
            path += '.'

            # Loop until we get an ATOM
            next = self._next('.', 'ATOM')
            path += next.value
            while next.type == '.':
                next = self._next('.', 'ATOM')
                path += next.value

        elif token.type == '@':
            # Handle @root, etc
            next = self._next('ATOM')
            if next.value == "root":
                path = "@root"
            else:
                raise CoilSyntaxError(token, "Unknown @%s, expected @root" %
                        next.value)

        while self._peek().type == '.':
            self._next()
            path = "%s.%s" % (path, self._next('ATOM').value)

        try:
            return container.get(path)
        except StructError, ex:
            raise CoilDataError(token, ex.message)

    def _extend_with_struct(self, container, added, deleted, parent, token):
        if isinstance(parent, Struct):
            for key, val in parent.iteritems():
                # Don't blindly set if if missing, it may have been
                # deleted (@extends can appear anywhere in the Struct)
                if key not in added and key not in deleted:
                    if isinstance(val, Struct):
                        val = val.copy()
                    container[key] = val
        else:
            raise CoilSyntaxError(token, "Reference must be a Struct")

    def _extend_with_file(self, container, added, deleted,
            file_path, struct_path, token):

        try:
            coil_file = open(file_path)
        except IOError, ex:
            raise CoilDataError(token, "Failed to open %s: %s" % (file_path,ex))

        struct = self.__class__(coil_file, file_path, self.encoding).root()

        if struct_path:
            try:
                struct = struct.get(struct_path)
            except KeyError, ex:
                raise CoilDataError(token, "Failed to find %s in %s" %
                        (struct_path, file_path))

        self._extend_with_struct(container, added, deleted, struct, token)

    def _special_extends(self, container, added, deleted):
        token = self._peek()
        parent = self._parse_and_follow_path(container)
        self._extend_with_struct(container, added, deleted, parent, token)

    def _special_file(self, value):
        token = self._next('[', 'STRING')

        if token.type == '[':
            file_path = self._next('STRING').value
            struct_path = self._next('STRING').value
            self._next(']')
        else:
            file_path = token.value
            struct_path = ""

        if self.path and not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(self.path), file_path)

        if not os.path.isabs(file_path):
            raise CoilDataError("Unable to find absolute path: %s" % file_path)

        self._extend_with_file(container, added, deleted,
                file_path, struct_path, token)

    def _special_package(self, container, added, deleted):
        token = self._next('STRING')
        try:
            package, path = token.value.split(":", 1)
        except ValueError:
            CoilSyntaxError(token, '@package value must be "package:path"')

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
            raise CoilDataError(token, "Unable to find package: %s" % package)

        self._extend_with_file(container, added, deleted, fullpath, "", token)
