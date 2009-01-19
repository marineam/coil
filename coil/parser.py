"""Coil Parser"""

from coil import tokenizer, struct

class SyntaxError(tokenizer.ParseError):
    pass

class Parser(object):
    """The standard coil parser"""

    def __init__(self, input, path=None, encoding=None):
        self._tokenizer = tokenizer.Tokenizer(input, path, encoding)

        # Create the root Struct and parse!
        self._root = struct.Struct()
        self._parse_struct_attributes(self._root)

    def root(self):
        return self._root

    def _expect(self, token, *types):
        if token.type is None:
            raise SyntaxError(token, "Unexpected end of input, "
                    "looking for: %s" % " ".join(types))

        if token.type not in types:
            raise SyntaxError(token, "Unexpected %s: %s, looking for %s" %
                    (token.type, repr(token.value), " ".join(types)))

    def _next(self, *types):
        token = self._tokenizer.next()
        self._expect(token, *types)
        return token

    def _peek(self, *types):
        token = self._tokenizer.peek()
        self._expect(token, *types)
        return token

    def _parse_struct(self, container=None, name=None):
        """{ ... }"""

        self._next('{')

        new = struct.Struct(container=container, name=name)
        self._parse_struct_attributes(new)

        self._next('}')

        return new

    def _parse_struct_attributes(self, new_struct):
        """attribute..."""

        while self._tokenizer.peek().type not in (None, '}'):
            self._parse_attribute(new_struct)

    def _parse_attribute(self, container):
        """name: value"""

        name = self._parse_name()
        self._next(':')
        value = self._parse_value(container, name)
        container.set(name, value)

    def _parse_name(self):
        """ATOM[.ATOM]*"""

        name = self._next('ATOM').value

        while self._tokenizer.peek().type == '.':
            self._next('.')
            name = "%s.%s" (name, self._next('ATOM').value)

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
            return self._parse_and_follow_path()
        elif token.type in ('INTEGER', 'FLOAT', 'STRING'):
            self._next('INTEGER', 'FLOAT', 'STRING')
            return token.value

    def _parse_list(self):
        """[ number or string ... ]"""

        token.next('[')
        new = []

        token = self._next(']', 'INTEGER', 'FLOAT', 'STRING')
        while True:
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
            while token.type == '.':
                next = self._next('.', 'ATOM')
                path += next.value

        elif token.type == '@':
            # Handle @root, etc
            next = self._next('ATOM')
            if next.value == "root":
                path = "@root"
            else:
                raise SyntaxError(token, "Unknown @%s, expected @root" %
                        next.value)

        while self._tokenizer.peek().type == '.':
            self._next('.')
            path = "%s.%s" % (path, self._next('ATOM'))

        try:
            return container.get(path)
        except struct.KeyMissingError:
            raise SyntaxError(token, "Path %s does not exist" % repr(path))
