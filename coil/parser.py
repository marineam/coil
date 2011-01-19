# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Coil Parser"""

import os
import sys

from coil import tokenizer, struct, errors

class StructPrototype(struct.Struct):
    """A temporary struct used for parsing only.

    This Struct tracks links and inheritance so they can be processed
    when parsing is all done. This is important because it allows us
    to do fancy things with inheritance and catch errors during
    parse-time rather than run-time.
    """

    def __init__(self, base=(), container=None, name=None, location=None,
            permissive=False):
        struct.Struct.__init__(self, base, container, name, location)

        # Secondary items are ones that are inherited via @extends or @file
        # They must be tracked separately so we can raise errors on
        # double adds and deletes in the primary values.
        self._secondary_values = {}
        self._secondary_order = []
        # _deleted is a list of items that exist in one of the parents
        # but have been removed from this Struct by ~foo tokens.
        self._deleted = []
        self._permissive = permissive

    def _get(self, key):
        try:
            return self._values[key]
        except KeyError:
            return self._secondary_values[key]

    def _set(self, key, value):
        self._validate_doubleset(key)

        self._values[key] = value

        if key in self._secondary_values:
            del self._secondary_values[key]
        elif key not in self._order:
            self._order.append(key)

    def _del(self, key):
        self._validate_doubleset(key)

        if key in self._values:
            del self._values[key]
            if key in self._order:
                self._order.remove(key)
            else:
                self._secondary_order.remove(key)
        elif key in self._secondary_values:
            del self._secondary_values[key]
            self._secondary_order.remove(key)
        else:
            raise KeyError

    def __contains__(self, key):
        return key in self._values or key in self._secondary_values

    def __iter__(self):
        for key in self._secondary_order:
            yield key
        for key in self._order:
            yield key

    def __len__(self):
        return len(self._values) + len(self._secondary_values)

    def extends(self, base, relative=False):
        """Add a struct as another parent.

        :param base: A Struct or dict to extend.
        :param relative: Convert @root links to relative links.
            Used when extending a Struct from another file.
        """

        def relativeize(path):
            if not path.startswith("@root"):
                return path
            else:
                new = ""
                container = base
                while container.container:
                    container = container.container
                    new += "."
                new += path[5:]
                return new

        def relativestr(match):
            return "${%s}" % relativeize(match.group(1))

        def relativelist(old):
            new = []
            for item in old:
                if isinstance(item, basestring):
                    item = struct.Struct.EXPAND.sub(relativestr, item)
                new.append(item)
            return new

        if base is self:
            raise errors.StructError(self,
                "Struct cannot extend itself.")

        if not isinstance(base, struct.Struct):
            raise errors.StructError(self,
                "attempting to extend a value which is NOT a struct.")

        if base._map is not None and self._map is None:
            self._map = list(base._map)

        for key, value in base.iteritems():
            if key in self or key in self._deleted:
                continue

            # Copy child Structs so that they can be edited independently
            if isinstance(value, struct.Struct):
                new = self.__class__(container=self, name=key)
                new.extends(value, relative)
                value = new

            # Convert absolute to relative links if required
            if relative:
                if isinstance(value, struct.Link):
                    value.path = relativeize(value.path)
                elif isinstance(value, basestring):
                    value = struct.Struct.EXPAND.sub(relativestr, value)
                elif isinstance(value, list):
                    value = relativelist(value)

            self._secondary_values[key] = value
            self._secondary_order.append(key)

    def _validate_doubleset(self, key):
        """Private: check that key has not been used (excluding parents)"""

        if self._permissive:
            return
        elif key in self._deleted or key in self._values:
            raise errors.StructError(self, "Setting/deleting %r twice" % key)


class Parser(object):
    """The standard coil parser.

    :param input_: An iterator over lines of input.
        Typically a :class:`file` object or list of strings.
    :param path: Path to input file, used for errors and @file imports.
    :param encoding: Read strings using the given encoding.
        All string values will be :class:`unicode` objects rather than
        :class:`str`.
    :param expand: Enables/disables expansion of the parsed tree.
    :param defaults: See :meth:`Struct.expanditem <coil.struct.Struct.expanditem>`
    :param ignore_missing: See :meth:`Struct.expanditem <coil.struct.Struct.expanditem>`
    :param ignore_types: See :meth:`Struct.expanditem <coil.struct.Struct.expanditem>`
    :param permissive: Disable some validation checks. Currently this
        just includes checking for double-setting atrributes.
    """

    def __init__(self, input_, path=None, encoding=None, expand=True,
            defaults=(), ignore_missing=(), ignore_types=(), permissive=False):
        if path:
            self._path = os.path.abspath(path)
        else:
            self._path = None

        self._encoding = encoding
        self._permissive = permissive
        self._tokenizer = tokenizer.Tokenizer(input_, self._path, encoding)

        # Create the root Struct and parse!
        self._prototype = StructPrototype(permissive=permissive)

        while self._tokenizer.peek('~', 'PATH', 'EOF').type != 'EOF':
            self._parse_attribute(self._prototype)

        self._tokenizer.next('EOF')
        self._root = struct.Struct(self._prototype)
        if expand:
            self._root.expand(defaults=defaults,
                              ignore_missing=ignore_missing,
                              ignore_types=ignore_types)

    def root(self):
        """Get the root Struct.

        :rtype: :class:`~coil.struct.Struct`
        """
        return self._root

    def prototype(self):
        """Get the raw unexpanded prototype, you probably don't want this.

        :rtype: :class:`~coil.parser.StructPrototype`
        """
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
                del container[token.value]
            except errors.StructError, ex:
                ex.location(token)
                raise ex
        else:
            self._tokenizer.next(':')

            if token.value[0] == '@':
                special = getattr(self, "_special_%s" % token.value[1:], None)
                if special is None:
                    raise errors.CoilParseError(token,
                            "Unknown special attribute: %s" % token.value)
                else:
                    special(container, token)
            elif '.' in token.value:
                # ensure parents are created for flattened paths
                parts = token.value.split('.')
                for key in parts[:-1]:
                    if not container.get(key, False):
                        new = StructPrototype(container=container, name=key,
                                              permissive=self._permissive)
                        container[key] = new
                    container = container[key]
                token.value = parts[-1]
                self._parse_value(container, token.value)
            else:
                self._parse_value(container, token.value)

    def _parse_value(self, container, name):
        """path, number, or string"""

        token = self._tokenizer.peek('{', '[', '=', 'PATH', 'VALUE')

        if token.type == '{':
            # Got a struct, will be added inside _parse_struct
            self._parse_struct(container, name)
        elif token.type == '[':
            # Got a list, will be added inside _parse_list
            self._parse_list(container, name)
        elif token.type == '=':
            # Got a reference, chomp the =, save the link
            self._tokenizer.next('=')
            self._parse_link(container, name)
        elif token.type == 'PATH':
            # Got a reference, save the link
            self._parse_link(container, name)
        else:
            # Plain old boring values
            self._parse_plain(container, name)

    def _parse_struct(self, container, name):
        """{ attrbute... }"""

        token = self._tokenizer.next('{')

        try:
            new = StructPrototype(container=container, name=name,
                                  permissive=self._permissive)
            container[name] = new
        except errors.StructError, ex:
            ex.location(token)
            raise ex

        while self._tokenizer.peek('~', 'PATH', '}').type != '}':
            self._parse_attribute(new)

        self._tokenizer.next('}')

    def _parse_list(self, container, name):
        """[ number or string or list ... ]"""

        new = list()
        container[name] = new
        self._parse_list_values(new)

    def _parse_list_values(self, container):
        """[ number or string or list ... ]"""

        self._tokenizer.next('[')
        token = self._tokenizer.peek('[', ']', 'VALUE')

        while token.type != ']':
            if token.type == '[':
                new = list()
                container.append(new)
                self._parse_list_values(new)
            else:
                container.append(self._tokenizer.next('VALUE').value)

            token = self._tokenizer.peek('[', ']', 'VALUE')

        self._tokenizer.next(']')

    def _parse_link(self, container, name):
        """some.path"""

        token = self._tokenizer.next('PATH')
        link = struct.Link(token.value)
        container.set(name, link, location=token)

    def _parse_plain(self, container, name):
        """number, string, bool, or None"""

        token = self._tokenizer.next('VALUE')
        container.set(name, token.value, location=token)

    def _special_extends(self, container, token):
        """Handle @extends: some.struct"""

        token = self._tokenizer.next('=', 'PATH')
        if token.value == '=':
            token = self._tokenizer.next('PATH')

        if container.container is None:
            raise errors.StructError(self,
                "@root cannot extend other structs.")

        path = token.value

        try:
            parent = container.get(path)
        except errors.StructError, ex:
            ex.location(token)
            raise

        if not isinstance(parent, struct.Struct):
            raise errors.StructError(container,
                  "@extends target must be of type Struct")

        if parent is container:
            raise errors.StructError(container,
                  "@extends target cannot be self")

        if not (path.startswith("@") or path.startswith("..")):
            raise errors.StructError(container,
                  "@extends target cannot be children of container")

        _container = container
        while _container is not None:
            if _container is parent:
                raise errors.StructError(container,
                      "@extends target cannot be parents of container")
            _container = _container.container

        container.extends(parent)

    def _extend_with_file(self, container, file_path, struct_path):
        """Parse another coil file and merge it into the tree"""

        coil_file = open(file_path)
        parent = self.__class__(coil_file, path=file_path,
                encoding=self._encoding, expand=False).prototype()

        if struct_path:
            parent = parent.get(struct_path)
            if not isinstance(parent, struct.Struct):
                raise errors.StructError(container,
                    "@file specification sub-import type must be Struct.")

        container.extends(parent, True)

    def _special_file(self, container, token):
        """Handle @file"""

        token = self._tokenizer.next('[', 'VALUE')

        if token.type == '[':
            # @file: [ "file_name" "substruct_name" ]
            file_path = self._tokenizer.next('VALUE').value
            struct_path = self._tokenizer.next('VALUE').value
            self._tokenizer.next(']')
        else:
            # @file: "file_name"
            file_path = token.value
            struct_path = ""

        file_path = container.expandvalue(file_path)
        struct_path = container.expandvalue(struct_path)

        if (not isinstance(file_path, basestring) or
                not isinstance(struct_path, basestring)):
            raise errors.CoilParseError(token, "@file value must be a string")

        if self._path and not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(self._path), file_path)

        if not os.path.isabs(file_path):
            raise errors.CoilParseError(token,
                    "Unable to find absolute path: %s" % file_path)

        try:
            self._extend_with_file(container, file_path, struct_path)
        except IOError, ex:
            raise errors.CoilParseError(token, str(ex))

    def _special_package(self, container, token):
        """Handle @package"""

        token = self._tokenizer.next('VALUE')

        value = container.expandvalue(token.value)

        if not isinstance(value, basestring):
            raise errors.CoilParseError(token,
                    "@package value must be a string")

        try:
            package, path = value.split(":", 1)
        except ValueError:
            errors.CoilParseError(token,
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
            raise errors.CoilParseError(token,
                    "Unable to find package: %s" % package)

        try:
            self._extend_with_file(container, fullpath, "")
        except IOError, ex:
            raise errors.CoilParseError(token, str(ex))

    def _special_map(self, container, token):
        if container._map is not None:
            raise errors.CoilParseError(token,
                    "Found multiple @map lists, only one is allowed")
        container._map = []
        self._parse_list_values(container._map)
