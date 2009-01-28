"""Coil Parser"""

import os
import sys

from coil import tokenizer, struct, errors

class Link(tokenizer.Token):
    """A temporary symbolic link to another item"""

    def __init__(self, token):
        assert isinstance(token, tokenizer.Token)
        tokenizer.Token.__init__(self, token, token.type, token.value)

class StructPrototype(struct.Struct):
    """A temporary struct used for parsing only.

    This Struct tracks links and inheritance so they can be processed
    when parsing is all done. This is important because it allows us
    to do fancy things with inheritance and catch errors during
    parse-time rather than run-time.
    """

    def __init__(self, base=None, container=None, name=None):
        struct.Struct.__init__(self, container=container, name=name)

        # Secondary items are ones that are inherited via @extends or @file
        # They must be tracked separately so we can raise errors on
        # double adds and deletes in the primary values.
        self._secondary_values = {}
        self._secondary_order = []
        # _deleted is a list of items that exist in one of the parents
        # but have been removed from this Struct by ~foo tokens.
        self._deleted = []

        if base:
            self.extends(base)

    def __contains__(self, key):
        self._validate_key(key)
        return key in self._values or key in self._secondary_values

    def _validate_doubleset(self, key):
        """Private: validate key and check that is is unused"""
        self._validate_key(key)

        if key in self._deleted or key in self._values:
            raise errors.CoilStructError(self,
                    "Setting/deleting '%s' twice" % repr(key))

    def __setitem__(self, key, value):
        self._validate_doubleset(key)

        if key in self._secondary_values:
            del self._secondary_values[key]

        struct.Struct.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._validate_doubleset(key)

        if key in self._values:
            del self._values[key]

            if key in self._secondary_order:
                self._secondary_order.remove(key)
            else:
                self._order.remove(key)
        elif key in self._secondary_values:
            del self._secondary_values[key]
            self._secondary_order.remove(key)
        else:
            raise errors.CoilStructError(self,
                    "Deleting unknown key '%s'" % repr(key))

        self._deleted.append(key)

    def __getitem__(self, key):
        self._validate_key(key)
        if key in self._values:
            return self._values[key]
        elif key in self._secondary_values:
            return self._secondary_values[key]
        else:
            raise errors.KeyMissingError(self, key)

    def __iter__(self):
        for key in self._secondary_order:
            yield key
        for key in self._order:
            yield key

    def extends(self, base):
        """Add a struct as another parent"""

        for key, value in base.iteritems():
            if key in self or key in self._deleted:
                continue

            # Copy child Structs so that they can be edited independently
            if isinstance(value, struct.Struct):
                value = self.__class__(value, self, key)

            self._secondary_values[key] = value
            self._secondary_order.append(key)

    def copy(self):
        """Convert this prototype into a normal Struct.
        
        All links and inheritance rules are resolved and any errors
        are raised. This should be performed once parsing is complete.
        """

        new = struct.Struct()
        for key, value in self.iteritems():
            # Recursively handle any child prototypes
            if isinstance(value, struct.Struct):
                value = value.copy()

            # Resolve any links
            if isinstance(value, Link):
                assert value.type == 'PATH'
                try:
                    value = self.get(value.value)
                except errors.CoilStructError, ex:
                    raise errors.CoilDataError(value, str(ex))

            new[key] = value

        return new

class Parser(object):
    """The standard coil parser"""

    def __init__(self, input_, path=None, encoding=None):
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
            # Got a reference, chomp the =, save the link
            # I only support the = for backwards compatibility
            self._tokenizer.next('=')
            value = Link(self._tokenizer.next('PATH'))
        elif token.type == 'PATH':
            # Got a reference, save the link
            value = Link(self._tokenizer.next('PATH'))
        else:
            # Plain old boring values
            self._tokenizer.next('INTEGER', 'FLOAT', 'STRING')
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

        valid = ('INTEGER', 'FLOAT', 'STRING')
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
