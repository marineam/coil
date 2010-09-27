**********
Legacy API
**********

These are pieces of the coil API are deprecated pieces left over from
0.2.2. See :ref:`coil-022-migration` in the Dev Guide for more
information. New code should not use this API.

Parser
======

.. automodule:: coil.text
    :members:

Struct
======

.. autoclass:: coil.struct.StructNode
    :members:
    :undoc-members:

Errors
======

.. data:: coil.struct.StructAttributeError
    
    Alias for :exc:`coil.errors.KeyMissingError`
