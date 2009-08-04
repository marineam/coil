**********
User Guide
**********

Overview
========

Coil files provide a very powerful tool for configuring large and
complex systems. Sets of values are organized into blocks called
"structs" which can refer to each other for specific values or inherit
all values. Values may be boolean, numbers, or strings. Strings may be
encoded in Unicode if the application supports it.

Text Format
===========

Data Types
----------

The basic format is a set of key, value pairs. They keys may contain:
``A-Z``, ``a-z``, ``0-9``,  ``-``, and ``_``. Values may be any of the
following:

- The null value, represented as the Python keyword ``None``.

- Boolean values, represented by ``True`` and ``False``.

- Integers, represented by simple digits such as ``12``.

- Floating point numbers such as ``3.56``.

- Strings, delimited by ``"`` and ``'`` for single line strings or
  ``"""`` and ``'''`` for single and multi line strings as in Python.

The key value pairs are represented by the syntax ``key: value`` similar
to that of Python *dict* objects except there is no comma between pairs.
White space does not mater. For example this::

    is_ok: True
    description: "This is Coil"

is equivalent to::

    is_ok: True description: "This is Coil"

Groups of these key, value pairs can be grouped into structs by using
``{ ..some data.. }``. For example::

    config-a: {
        is_ok: True
        description: "This is config a"
    }

    config-b: {
        is_ok: True
        description: "This is config b"
    }

Values may also be put inside a list using ``[ ..something.. ]``::

    things: [ 1 2.3 "a string" ]

Note that structs may not appear inside of lists but nested lists are
allowed.

Inheritance
-----------

Structs can extends other structs: this means they inherit all
attributes from that struct. Extending is done with a special
attribute, @extends, with a value that is a path to another struct.
Paths can be relative, with a prefix of ".." meaning go up one level,
"..." go up two levels, etc., or absolute, starting from the special
location @root.  In this example, y and z inherit from x and override
some of its attributes::

    x: {a: 1  b: 2}
    y: {
        @extends: ..x # relative path
        b: 3
    }
    z: {
        @extends: @root.x # absolute path
        b: 4
    }

In this example y is the same as::

    y: {a: 1 b: 3}

When inheriting from a tree of structs attributes of sub-structs may be
referenced simply by their path rather than having to inherit and modify
the individual child structs. In this example y and z both extend x, and
have identical contents::

    x: { a: {b: 1} }
    y: {
        @extends: ..x
        a.b: 3
    }
    z: {
        @extends: ..x
        a: {
            @extends: ..x.a
            b: 3
        }
    }

It is also possible to extend more than one structure, combining the
contents of two into one. In the case of conflicts the first extended
struct wins. For example, the following::

    x: { a: 1 }
    y: { a: 2 b: 3}
    z: {
        @extends: ..x
        @extends: ..y
    }

is equivalent to::

    x: { a: 1 }
    y: { a: 2 b: 3}
    z: { a: 1 b: 3}

Importing Files
---------------

Structs can import data from other files. The behavior is similar to
``@extends`` except the value is a string listing the path to another
file. If the file is relative it is assumed to be relative to the file
in which it appears, not the parsing program's current working
directory. For example, if the file "/home/joe/my.coil" wants to import
the contents of "/home/joe/test/example.coil" it could do::

    example1: { @file: "/home/joe/test/example.coil" }
    example2: { @file: "test/example.coil" }

If a specific struct is wanted rather than the whole file provide a list
of two strings that define the file name and the path::

    subexample: { @file: [ "test/example.coil" "sub.path" ] }

To ease packaging and distribution, ``@package`` may be used in place of
``@file`` to refer to a file that exists inside of a Python package
directory. The value listed is the package name and file name seperated
by a colon. For example to import "example.coil" from inside the
"awesome.library" package::

    example: { @package: "awesome.library:example.coil" }

Deletion
--------

When inheriting values from another struct with ``@extends``, ``@file``,
etc. unwanted attributes can be deleted by prefixing the name with a
'~'. So if "sub" should not contain the attribute x::

    base: {x: 1  y: 2}
    sub: {
        @extends: ..base
        ~x  # sub now has no attribute "x"
    }

References
----------

Attributes can refer to each other by name similar to a UNIX symbolic
link. This allows values to be copied between structs without extending
the entire struct. For example::

    a: 1
    b: a

is the same as::

    a: 1
    b: 1

Note that for backwards compatibility the path may be prefixed with a
'=' character: ``b: =a``.

Just as with ``@extends`` the path may be to anywhere in the tree::

    host1: "host1.somewhere.com"
    host2: "host2.somewhere.com"
    service1: { host: @root.host1 port: 1234 }
    service2: { host: ..host2 port 3456 }

References are also allowed within strings by using ${name} similar to Bash or Perl. For example::

    foo: "zomg"
    bar: "${foo}bbq"
    sub: {
        x: "foo is ${..foo}"
        y: "foo is ${@root.foo}"
    }

will turn out to be::

    foo: "zomg"
    bar: "zomgbbq"
    sub: {
        x: "foo is zomg"
        y: "foo is zomg"
    }

Config Validation
=================

Currently the core Coil library has no ability to validate files beyond
the basic syntax. Formal schema validation is planned in the future but
for now it is up to the individual applications to validate that their
config is valid.

To at least check that the syntax is correct and view how your
inheritance rules actually play out there is a simple utility called
*coildump* which will read in a coil file, expand all references, and
print it out again. It is under *bin* in the source repository.

Editor Support
==============

To make editing easier Coil includes some helpers for Emacs and Vim. For
Emacs users grab *misc/coil.el* out of the source repository. For Vim copy
the *coil.vim* files under *misc/vim/ftdetect* and *misc/vim/syntax* to
*~/.vim/ftdetect* and *~/.vim/syntax*.

