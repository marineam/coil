# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

"""Break the input into a sequence of small tokens."""

import re

from coil import errors

class Token(object):
    """Represents a single token"""

    def __init__(self, token, type_, value=None):
        """
        @param token: The L{Tokenizer} or another C{Token}.
            Used to get the current file and position in the input.
        @param type_: A string defining the type of token.
            Must be one of the types listed in L{Tokenizer.TYPES}.
        @param value: The string value of this token.
        """
        assert type_ in Tokenizer.TYPES

        # Turn numbers into numbers, True/False into bool
        if type_ == 'FLOAT':
            value = float(value)
        elif type_ == 'INTEGER':
            value = int(value)
        elif type_ == 'BOOLEAN':
            value = (value == "True")

        self.type = type_
        self.value = value
        self.path = token.path
        self.line = token.line
        self.column = token.column

    def __repr__(self):
        return "<%s %s %s (%s:%s:%s)" % (self.__class__.__name__, self.type,
                repr(self.value), self.path, self.line, self.column)

class Tokenizer(object):
    """Split input into basic tokens"""

    #: Valid Token types
    TYPES = ('{', '}', '[', ']', ':', '~', '=',
             'PATH', 'FLOAT', 'INTEGER', 'STRING', 'BOOLEAN', 'EOF')

    # Note: keys may start with - but must be followed by a letter
    KEY_REGEX = r'-?[a-zA-Z_][\w-]*'
    PATH_REGEX = r'(@|\.\.+)?%s(\.%s)*' % (KEY_REGEX, KEY_REGEX)

    PATH = re.compile(PATH_REGEX)
    FLOAT = re.compile(r'-?[0-9]+\.[0-9]+')
    INTEGER = re.compile(r'-?[0-9]+')
    BOOLEAN = re.compile(r'(True|False)')
    WHITESPACE = re.compile(r'(#.*|\s+)')

    # Strings are a bit tricky...
    # The terminating quotes are optional for ''' quotes because
    # they may span multiple lines. The rest of the voodoo is an
    # attempt to allow escaping of quotes and require \ characters
    # to always be paired with another character.
    _STR1 = re.compile(r"'''((\\.|[^\\']|''?(?!'))*)(''')?")
    _STR2 = re.compile(r'"""((\\.|[^\\"]|""?(?!"))*)(""")?')
    _STR3 = re.compile(r"'((\\.|[^\\'])*)(')")
    _STR4 = re.compile(r'"((\\.|[^\\"])*)(")')
    _STRESC = re.compile(r'\\.')

    def __init__(self, input_, path=None, encoding=None):
        """
        @param input_: An iterator over lines of input.
            Typically a C{file} object or list of strings.
        @param path: Path to input file, used for errors.
        @param encoding: Read strings using the given encoding. All
            string values will be C{unicode} objects rather than C{str}.
        """

        self.path = path
        self.line = 0
        self.column = 0
        self._input = input_
        self._buffer = ""
        self._encoding = encoding
        self._stack = []

        # We iterate over the input in both next and _parse_string
        self._next_line = self._next_line_generator().next

    def _expect(self, token, types):
        """Check that token has the correct type"""

        assert types
        for x in types:
            assert x in self.TYPES

        if token.type not in types:
            if token.type == token.value:
                unexpected = repr(token.type)
            else:
                unexpected = "%s: %s" % (token.type, repr(token.value))

            raise errors.CoilSyntaxError(token, "Unexpected %s, looking for %s" %
                    (unexpected, " ".join(types)))

    def _push(self, token):
        """Push a token back into the tokenizer"""

        assert isinstance(token, Token)
        self._stack.append(token)

    def peek(self, *types):
        """Peek at the next token but keep it in the tokenizer"""

        token = self.next(*types)
        self._push(token)
        return token

    def next(self, *types):
        """Read the input in search of the next token"""

        token = self._next()
        if types:
            self._expect(token, types)
        return token

    def _next(self):
        """Only used by self.next()"""

        if self._stack:
            return self._stack.pop()

        while True:
            if not self._buffer:
                try:
                    self._buffer = self._next_line()
                except StopIteration:
                    return Token(self, 'EOF', 'EOF')


            # Buffer should at least have a newline
            assert self._buffer

            # Skip over all whitespace and comments
            match = self.WHITESPACE.match(self._buffer)
            if match:
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
            else:
                break

        # Special characters
        for tok in ('{', '}', '[', ']', ':', '~', '='):
            if self._buffer[0] == tok:
                token =  Token(self, tok, tok)
                self._buffer = self._buffer[1:]
                self.column += 1
                return token

        # Simple tokens
        for token_type in ('FLOAT', 'INTEGER', 'BOOLEAN', 'PATH'):
            regex = getattr(self, token_type)
            match = regex.match(self._buffer)
            if match:
                token = Token(self, token_type, match.group(0))
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
                return token

        # Strings are special because they may span multiple lines
        if self._buffer[0] in ('"', "'"):
            return self._parse_string()

        # Unknown input :-(
        raise errors.CoilSyntaxError(self, "Unrecognized input: %s" % self._buffer)

    def _next_line_generator(self):
        for line in self._input:
            if not line or line[-1] != '\n':
                line = "%s\n" % line
            self.line += 1
            self.column = 1
            yield line

    def _escape_string(self, token):
        replace = {
                "\\\\": "\\",
                "\\n": "\n",
                "\\r": "\r",
                "\\t": "\t",
                "\\'": "'",
                '\\"': '"',
                }

        def do_replace(match):
            val = match.group(0)
            key = str(val)
            if key in replace:
                return replace[key]
            else:
                return val

        token.value = self._STRESC.sub(do_replace, token.value)

    def _parse_string(self):
        def decode(buf):
            # If _encoding is set all strings should 
            # be unicode instead of str
            if self._encoding:
                try:
                    return buf.decode(self._encoding)
                except UnicodeDecodeError, ex:
                    raise errors.CoilUnicodeError(self, str(ex))
            else:
                return buf

        token = Token(self, 'STRING')
        strbuf = decode(self._buffer)
        pattern = None

        # Loop until the string is terminated
        while True:
            if not pattern:
                # Find the correct string type
                for pat in (self._STR1, self._STR2, self._STR3, self._STR4):
                    match = pat.match(strbuf)
                    if match:
                        pattern = pat
                        break
            else:
                match = pattern.match(strbuf)

            if not match:
                raise errors.CoilSyntaxError(token,
                    "Invalid string: %s" % strbuf)

            if not match.group(3):
                # Read another line if string has no ending ''' or """
                try:
                    new = self._next_line()
                except StopIteration:
                    raise errors.CoilSyntaxError(token, "Unterminated string")

                strbuf += decode(new)
            else:
                token.value = match.group(1)
                break

        # Convert any escaped characters
        self._escape_string(token)

        # Fix up the column counter
        try:
            col = match.group(0).rindex('\n')
            self.column = match.end() - col
        except ValueError:
            self.column += match.end()

        # _buffer needs to be converted back to str
        self._buffer = strbuf[match.end():]
        if isinstance(self._buffer, unicode):
            self._buffer = str(self._buffer.encode(self._encoding))
        assert isinstance(self._buffer, str)

        return token
