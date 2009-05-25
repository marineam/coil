# Copyright (c) 2008-2009 ITA Software, Inc.
# See LICENSE.txt for details.

class CoilStructError(Exception):
    """Generic error for Struct"""

    def __init__(self, struct, msg):
        self._class = struct.__class__.__name__
        self._name = struct.path()
        self.message = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return "<%s %s>: %s" % (self._class, self._name, self.message)

    def __repr__(self):
        return "%s(<%s %s>, %s)" % (self._class, self._name, repr(self.message))

class KeyMissingError(CoilStructError, KeyError):
    """The given key was not found"""

    def __init__(self, struct, key, path=None):
        if path:
            msg = "The key %s (in %s) was not found" % (repr(key), repr(path))
        else:
            msg = "The key %s was not found" % repr(key)

        CoilStructError.__init__(self, struct, msg)

class KeyTypeError(CoilStructError, TypeError):
    """The given key was not a string"""

    def __init__(self, struct, key):
        msg = "The key must be a string, got %s" % type(key)
        CoilStructError.__init__(self, struct, msg)

class KeyValueError(CoilStructError, ValueError):
    """The given key contained invalid characters"""

    def __init__(self, struct, key):
        msg = "The key %s is invalid" % repr(key)
        CoilStructError.__init__(self, struct, msg)

class CoilSyntaxError(Exception):
    def __init__(self, token, reason):
        self.path = token.path
        self.line = token.line
        self.column = token.column
        self.reason = reason

        Exception.__init__(self, "%s: %s (%s:%d:%d)" %
                (self.__class__.__name__, reason,
                 self.path, self.line, self.column))

class CoilUnicodeError(CoilSyntaxError):
    pass

class CoilDataError(CoilSyntaxError):
    pass

