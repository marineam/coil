***************
Developer Guide
***************

API Reference
=============

.. toctree::
    :maxdepth: 2

    api
    legacy_api

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

.. _coil-022-migration:

Coil 0.2.2 Migration
====================

Coil 0.3.x differs significantly from 0.2.2. Changes include:

   - Switch to a dict-like API for :class:`~coil.struct.Struct`. The old
     behavior of accessing data via object attributes of
     :class:`~coil.struct.StructNode` makes it impossible to expand the
     API without risking new name-space conflicts with data.
   - Deprecate :class:`~coil.struct.StructNode`, the
     :class:`~coil.struct.Struct` class now knows about containment.
   - Deprecate :mod:`coil.text`, the parser has changed entirely.
   - Strict parsing of the coil text format.
   - Expand ``"${attr}"`` links within strings.
   - Expand all links (including those within strings) while loading the
     coil file rather than at run time to catch errors early.

To ease the migration of applications from 0.2.2 to 0.3.x and beyond
coil continues to provide the old interfaces and parameters to the new
to behave like 0.2.2 did. When using the legacy interfaces those
compatibility options are enabled by default. The ``coildump`` command
also includes a ``--compat=0.2.2`` option.

If you wish to maintain some compatibility with 0.2.2 but start
transitioning to the new API here are the relevant options:

   - Parser option ``permissive=True`` which can be passed to
     :class:`coil.parser.Parser`, :func:`coil.parse`, and
     :func:`coil.parse_file`. This prevents the parser from raising
     errors when parsing a block that sets/deletes the same attribute
     more than once.

   - Expansion option ``ignore_types=['strings']`` which can be passed to
     :meth:`Struct.expand <coil.struct.Struct.expand>` and the
     :class:`~coil.parser.Parser` class when ``expand=True`` is used
     (the default). This prevents coil from expanding ``"${attr}"``
     style links within strings.

   - The expansion option ``ignore_missing=True`` may also be useful as
     an alternative to ``ignore_types=['strings']``. This allows coil to
     expand links when possible and not raise an error when it cannot.

So a migration could be handled in several independent steps:

    1. Upgrade coil library from 0.2.2 to 0.3.17 or later. Things should
       just work as-is since the application will be using the legacy
       APIs (:mod:`coil.text` and :class:`~coil.struct.StructNode`).
       Note that versions of 0.3.x prior to 0.3.17 do not provide the
       compatibility options discussed above and had a number of bugs in
       :class:`~coil.struct.StructNode`.

    2. Switch to the new parser API (:class:`~coil.parser.Parser`,
       :func:`coil.parse`, and :func:`coil.parse_file`) using
       ``permissive=True`` and ``ignore_types=['strings']``.

    3. Try removing the ``permissive`` option and fix any errors now
       reported in existing coil files.

    4. If the application previously handled ``"${attr}"`` links itself
       but in a way that should be compatible with 0.3.x remove
       ``ignore_missing`` and test existing coil files to confirm
       compatibility.

       If the application's use of ``"${attr}"`` links is not quite
       compatible with 0.3.x then the following may be useful:

       .. doctest::

          >>> import coil

          First: ignore strings so all other errors can be found.
          >>> conf = coil.parse('a: 1 b: "${a} ${other}"',
          ...                   ignore_types=['strings'])

          Second: re-run expansion to handle strings bug ignore errors.
          >>> conf.expand(ignore_missing=True)

          Optionally document things coil didn't handle:
          >>> conf.unexpanded()
          set(['other'])

          Pass the config along to the old code to fill in the rest:
          >>> node = coil.struct.StructNode(conf)
          >>> # do something with node
