API Overview
============

The core of the Coil API is the L{Struct} object. It is a dict-like
mapping object that knows its place in a tree and can reference items
anywhere in the tree.

Assume we have a file at /tmp/example.coil with the following contents::

    x: { y: {a: 2}
        z: "hello"
        list: [1 2 3]
    }
    sub: {
        @extends: ..x
        y.b: 3
        ~z
    }

We can then inspect the structure just like nested dict objects:

    >>> import coil
    >>> conf = coil.parse_file("/tmp/example.coil")
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
