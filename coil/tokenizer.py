"""Break the input into a sequence of small tokens."""

import re

class CoilParseError(Exception):
    def __init__(self, token, reason):
        self.path = token.path
        self.line = token.line
        self.column = token.column
        self.reason = reason

        Exception.__init__(self, "%s: %s (%s:%d:%d)" %
                (self.__class__.__name__, reason,
                 self.path, self.line, self.column))

class CoilLexicalError(CoilParseError):
    pass

class CoilUnicodeError(CoilParseError):
    pass

class Token(object):
    """Represents a single token"""

    def __init__(self, tokenizer, type_=None, value=None):
        self.type = type_
        self.value = value
        self.path = tokenizer.path
        self.line = tokenizer.line
        self.column = tokenizer.column

class Tokenizer(object):

    ATOM_REGEX = r'[a-zA-Z_][\w-]*'
    ATOM = re.compile(ATOM_REGEX)

    FLOAT_REGEX = r'-?[0-9]+\.[0-9]+'
    FLOAT = re.compile(FLOAT_REGEX)
    INTEGER_REGEX = r'-?[0-9]+'
    INTEGER = re.compile(INTEGER_REGEX)

    WHITESPACE_REGEX = r'(#.*|\s+)'
    WHITESPACE = re.compile(WHITESPACE_REGEX)

    # Strings are a bit tricky...
    # The terminating quotes are optional for ''' quotes because
    # they may span multiple lines. The rest of the voodoo is an
    # attempt to allow escaping of quotes and require \ characters
    # to always be paired with another character.
    _STR1 = re.compile(r"'''((\\.|[^\\']|''?(?!'))*)(''')?")
    _STR2 = re.compile(r'"""((\\.|[^\\"]|""?(?!"))*)(""")?')
    _STR3 = re.compile(r"'((\\.|[^\\'])*)(')")
    _STR4 = re.compile(r'"((\\.|[^\\"])*)(")')

    def __init__(self, input_, path=None, encoding=None):
        self.input = input_
        self.path = path
        self.line = 0
        self.column = 0
        self._buffer = ""
        self._encoding = encoding
        self._stack = []
        self._done = False

        # We iterate over the input in both next and _parse_string
        self._next_line = self._next_line_generator().next

    def push(self, token):
        """Push a token back into the tokenizer"""

        assert isinstance(token, Token)
        self._stack.append(token)

    def peek(self):
        """Peek at the next token but keep it in the tokenizer"""

        token = self.next()
        self.push(token)
        return token

    def next(self):
        """Read the input in search of the next token"""

        while True:
            if self._stack:
                return self._stack.pop()

            if self._done:
                return Token(self)

            if not self._buffer:
                try:
                    self._buffer = self._next_line()
                except StopIteration:
                    self._done = True
                    continue

                self.line += 1
                self.column = 1

            # It should at least have a newline
            assert self._buffer

            # Skip over all whitespace and comments
            match = self.WHITESPACE.match(self._buffer)
            if match:
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
                continue

            # Special characters
            for tok in ('{', '}', '[', ']', '.', '@', ':'):
                if self._buffer[0] == tok:
                    token =  Token(self, tok, tok)
                    self._buffer = self._buffer[1:]
                    self.column += 1
                    return token

            # Basic keys
            match = self.ATOM.match(self._buffer)
            if match:
                token = Token(self, 'ATOM', match.group(0))
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
                return token

            # Floats
            match = self.FLOAT.match(self._buffer)
            if match:
                token = Token(self, 'FLOAT', float(match.group(0)))
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
                return token

            # Integers
            match = self.INTEGER.match(self._buffer)
            if match:
                token = Token(self, 'INTEGER', int(match.group(0)))
                self._buffer = self._buffer[match.end():]
                self.column += match.end()
                return token

            # Strings are special because they may span multiple lines
            if self._buffer[0] in ('"', "'"):
                return self._parse_string()

            # Unparsable!
            raise CoilLexicalError(self, "Unrecognized token: %s" %
                    self._buffer)

    def _next_line_generator(self):
        for line in self.input:
            if not line or line[-1] != '\n':
                line = "%s\n" % line
            yield line

    def _parse_string(self):
        def decode(buf):
            # If _encoding is set all strings should 
            # be unicode instead of str
            if self._encoding:
                try:
                    return buf.decode(self._encoding)
                except UnicodeDecodeError, ex:
                    raise CoilUnicodeError(self, str(ex))
            else:
                return buf

        lines = 0
        strbuf = decode(self._buffer)
        pattern = None

        for pat in (self._STR1, self._STR2, self._STR3, self._STR4):
            # Find the correct string type
            if pat.match(strbuf):
                pattern = pat
                break

        if not pattern:
            raise CoilLexicalError(self, "Invalid string: %s" % strbuf)

        while True:
            match = pattern.match(strbuf)
            if not match:
                raise CoilLexicalError(self, "Invalid string: %s" % strbuf)

            if not match.group(3):
                try:
                    new = self._next_line()
                except StopIteration:
                    self._done = True
                    raise CoilLexicalError(self, "Unterminated string")

                lines += 1
                strbuf += decode(new)
            else:
                # TODO: expand escape chars
                token = Token(self, 'STRING', match.group(1))
                self.line += lines

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
