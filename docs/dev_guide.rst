***************
Developer Guide
***************

Overview
========

The core of the Coil API is the :class:`~coil.struct.Struct`. It is a
dict-like mapping object that knows its place in a tree and can
reference items anywhere in the tree.

Assume we have a file named example.coil with the following contents::

    x: { y: {a: 2}
        z: "hello"
        list: [1 2 3]
    }
    sub: {
        @extends: ..x
        y.b: 3
        ~z
    }

.. Keep the following in sync with the above, I can't figure out how
    to make things reference each-other auto-magically yet.
.. testsetup:: example1

    import coil
    conf = coil.parse("""
        x: { y: {a: 2}
            z: "hello"
            list: [1 2 3]
        }
        sub: {
            @extends: ..x
            y.b: 3
            ~z
        }
        """)

We can then inspect the structure just like nested dict objects:

.. doctest:: example1

    >>> conf = coil.parse_file("example.coil") # doctest: +SKIP
    >>> conf['x']['list']
    [1, 2, 3]
    >>> conf['x']['z']
    'hello'
    >>> conf.get('x').get('z')
    'hello'
    >>> conf.keys()
    ['x', 'sub']
    >>> 'z' in conf['sub'] # we deleted this with ~z
    False
    >>> conf['x']['y']
    Struct({'a': 2})
    >>> conf['sub']['y'] # inherited from x and added 'b'
    Struct({'a': 2, 'b': 3})

Also, we can access and items based on absolute and relative paths as
we can in the text format:

.. doctest:: example1

    >>> conf['x.z']
    'hello'
    >>> conf.get("@root.x.z")
    'hello'
    >>> x = conf['x']
    >>> x.get("..sub.y.b")
    3
    >>> conf.set("sub.y.c", 4)
    >>> conf['sub']['y']
    Struct({'a': 2, 'b': 3, 'c': 4})

Helper Functions
================

.. autofunction:: coil.parse

.. autofunction:: coil.parse_file

Struct API
==========

.. automodule:: coil.struct
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:


Parser API
==========

.. automodule:: coil.parser
    :members:
    :show-inheritance:

Errors
======

.. automodule:: coil.errors
    :members:
    :show-inheritance:
