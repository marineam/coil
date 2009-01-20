"""Coil: A Configuration Library."""

__version__ = "0.3.0"

from coil.parser import Parser

def parse_file(file_name):
    """Open and parse a coil file.

    Returns the root Struct.
    """
    coil = open(file_name)
    return Parser(coil, file_name).root()

def parse(string):
    """Parse a coil string.

    Returns the root Struct.
    """
    return Parser(string.splitlines()).root()
