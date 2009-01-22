"""Coil Parser"""

import os
import sys

from coil.tokenizer import Token, Tokenizer, CoilSyntaxError
from coil.struct import Struct, StructError, KeyMissingError

class CoilDataError(CoilSyntaxError):
    pass

class StructPrototype(Struct):
    """A temporary struct used for parsing only.

    This Struct tracks links and inheritance so they can be processed
    when parsing is all done. This is important because it allows us
    to do fancy things with inheritance and catch errors during
    parse-time rather than run-time.
    """

    def __init__(self):
        Struct.__init__(self)
        # _extends is a list of parents (set by @extends or @file)
        # If any item is not found in this Struct then the parent
        # list is searched in order.
        self._extends = []
        # _deleted is a list of items that exist in one of the parents
        # but have been removed from this Struct by ~foo tokens.
        self._deleted = []

    def __contains__(self, key):
        self._validate_key(key)
        if key in self._values:
            return True
        elif key in self._deleted:
            return False
        else:
            for parent in self._extends:
                if key in parent:
                    return True
            return False

    def __getitem__(self, key):
        self._validate_key(key)
        if key in self._values:
            return self._values[key]
        elif key in self._deleted:
            raise KeyMissingError(self, key)
        else:
            for parent in self._extends:
                if key in parent:
                    return parent[key]
            raise KeyMissingError(self, key)

    def __setitem__(self, key, value):
        if key in self._deleted or key in self._values:
            raise StructError(self, "Setting/deleting '%s' twice" % repr(key))
        Struct.__setitem__(self, key, value)

    def __delitem__(self, key):
        if key in self._deleted or key in self._values:
            raise StructError(self, "Setting/deleting '%s' twice" % repr(key))

        for parent in self._extends:
            if key in parent:
                self._deleted.append(key)
                return

        raise StructError(self, "Deleting unknown key '%s'" % repr(key))

    def __iter__(self):
        keys = []
        for parent in self._extends:
            for key in parent:
                if key not in keys and key not in self._deleted:
                    keys.append(key)
        for key in self._order:
            if key not in keys:
                keys.append(key)
        return iter(keys)

    def extends(self, struct):
        """Add a struct as another parent"""
        assert isinstance(struct, StructPrototype)
        self._extends.append(struct)

    def copy(self):
        """Convert this prototype into a normal Struct.
        
        All links and inheritance rules are resolved and any errors
        are raised. This should be performed once parsing is complete.
        """

        struct = Struct()
        for key, value in self.iteritems():
            # Recursively handle any child prototypes
            if isinstance(value, Struct):
                value = value.copy()

            # Resolve any links
            if isinstance(value, Token):
                assert value.type == 'PATH'
                try:
                    value = self.get(value.value)
                except StructError, ex:
                    raise CoilDataError(value, str(ex))

            struct[key] = value

        return struct

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
        self._prototype = StructPrototype()

        while self._tokenizer.peek('~', 'PATH', 'EOF').type != 'EOF':
            self._parse_attribute(self._prototype)

        self._tokenizer.next('EOF')
        self._root = self._prototype.copy()

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
            except StructError, ex:
                raise CoilDataError(token, ex.message)
        else:
            self._tokenizer.next(':')

            if token.value[0] == '@':
                special = getattr(self, "_special_%s" % token.value[1:], None)
                if special is None:
                    raise CoilSyntaxError(token,
                            "Unknown special attribute: %s" % token.value)
                else:
                    special(container)
            else:
                self._parse_value(container, token.value)

    def _parse_value(self, container, name):
        """path, number, or string"""

        token = self._tokenizer.peek('{', '[', '=',
                'PATH', 'INTEGER', 'FLOAT', 'STRING')

        if token.type == '{':
            # Got a struct, will be added inside _parse_struct
            self._parse_struct(container, name)
            value = None
        elif token.type == '[':
            # Got a list, will be added inside _parse_list
            self._parse_list(container, name)
            value = None
        elif token.type == '=':
            # Got a reference, just chomp the =
            # I only support the = for backwards compatibility
            self._tokenizer.next('=')
            value = self._tokenizer.next('PATH')
        elif token.type == 'PATH':
            # Got a reference, save the token itself.
            # We don't resolve the path until parsing is done.
            value = self._tokenizer.next('PATH')
        else:
            # Plain old boring values
            self._tokenizer.next('INTEGER', 'FLOAT', 'STRING')
            value = token.value

        if value is not None:
            try:
                container.set(name, value)
            except StructError, ex:
                raise CoilDataError(token, ex.message)

    def _parse_struct(self, container, name):
        """{ attrbute... }"""

        self._tokenizer.next('{')

        try:
            new = StructPrototype()
            container.set(name, new)
        except StructError, ex:
            raise CoilDataError(token, ex.message)

        while self._tokenizer.peek('~', 'PATH', '}').type != '}':
            self._parse_attribute(new)

        self._tokenizer.next('}')

    def _parse_list(self, container, name):
        """[ number or string ... ]"""

        self._tokenizer.next('[')

        try:
            new = list()
            container.set(name, new)
        except StructError, ex:
            raise CoilDataError(token, ex.message)

        while self._tokenizer.peek('INTEGER','FLOAT','STRING',']').type != ']':
            item = self._tokenizer.next('INTEGER', 'FLOAT', 'STRING')
            new.append(item.value)

        self._tokenizer.next(']')

    def _special_extends(self, container):
        """Handle @extends: some.struct"""

        token = self._tokenizer.next('PATH')

        try:
            parent = container.get(token.value)
        except StructError, ex:
            raise CoilDataError(token, str(ex))

        container.extends(parent)

    def _extend_with_file(self, container, file_path, struct_path):
        """Parse another coil file and merge it into the tree"""

        coil_file = open(file_path)
        parent = self.__class__(coil_file, file_path,
                self._encoding).prototype()

        if struct_path:
            parent = parent.get(struct_path)

        container.extends(parent)

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
            raise CoilDataError(token,
                    "Unable to find absolute path: %s" % file_path)

        try:
            self._extend_with_file(container, file_path, struct_path)
        except (IOError, StructError), ex:
            raise CoilDataError(token, str(ex))

    def _special_package(self, container):
        token = self._tokenizer.next('STRING')
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

        try:
            self._extend_with_file(container, fullpath, "")
        except (IOError, StructError), ex:
            raise CoilDataError(token, str(ex))
