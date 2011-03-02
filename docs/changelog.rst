**********
Change Log
**********

Version 0.3.20 (2011-03-02)
===========================

- Properly recursively copy lists when extending a struct. This lead to
  sharing values across structs which should have been different.

Version 0.3.19 (2010-12-02)
===========================

- Fix regression in coildump -f introduced with Struct.flatten()

Version 0.3.18 (2010-11-29)
===========================

- Add new list-style Struct.sort() method.

- Move coildump's flatten code into a new Struct.flatten() method.
  This fixes some issues with coildump -f printing invalid coil.

- Add support to coildump for reading from stdin.

- Properly close input file in coil.parse_file().
  (I could have sworn that this was fixed a long time ago...)

Version 0.3.17 (2010-09-27)
===========================

- Fix broken extending-parent check added in 0.3.16

- Fix compatibility with 0.2.2:

  * Give control over what types of expansion is performed.
    This is useful to turn of the expansion of references in strings.
  * Add a "permissive" mode to the parser to ignore some errors.
    Coil 0.2.2 didn't have the multiple set/delete test.
  * Use these options when parsing via the legacy functions in text.py.
  * Expose these options in coildump.
  * Fix a number of bugs in StructNode.

- Various documentation updates/fixes.

Version 0.3.16 (2010-08-23)
===========================

- Add stricter validation of @extends to prevent circular references.

- Properly escape \r when dumping structures to text.

- Allow paths to begin with a self reference "." for compatibility with
  coil versions <= 0.2.2 which seems to have allowed it.

Version 0.3.15 (2010-03-22)
===========================

- Add new @map keyword to the coil parser for defining sequences of
  structs and mapping sequences of values into them.

Version 0.3.14 (2010-02-05)
===========================

- Add Struct.merge() method for merging two different struct trees. This
  is essentially a recursive version of Struct.update().

Version 0.3.13 (2010-01-04)
===========================

- New options to coildump:
  --block: print only part of a coil file
  --flatten: print values as "foo.bar: value" pairs rather than the
  standard "foo: { bar: value }" format.

- Fix a Python 2.4 version compatibility issue.

Version 0.3.12 (2009-11-02)
===========================

- Optimize path resolution, reducing the number of recursive calls.

Version 0.3.11 (2009-09-23)
===========================

- Some minor bug fixes and a little optimization.

Version 0.3.8 (2009-08-20)
==========================

- Fix expansion of ``"${@root.foo}"`` references in imported files.

- Extra version bump because setting the version previously to 0.3.7.pre
  screws up depending on the above fix by testing the version.

Version 0.3.7 (2009-08-20)
==========================

- Minor bug and documentation fixes

Version 0.3.6 (2009-06-10)
==========================

- Move development to http://code.google.com/p/coil/.

- Massive documentation redo, converting to sphinx and lots of updates.

- Slight performance improvement in Struct._get_path_parent()

- Improvements to the coildump script, allowing default values.

- Other minor bug fixes.

Version 0.3.5 (2009-05-06)
==========================

- Add a simple distutils setup.py script.

- Properly delay expansion of files included with @file and @package.

- Change the expansion 'ignore' parameter name to 'ignore_missing' to be
  more descriptive. Impacts calls to :meth:`Struct.expandvalue
  <coil.struct.Struct.expandvalue>`, :meth:`Struct.expanditem
  <coil.struct.Struct.expanditem>`, :meth:`Struct.expand
  <coil.struct.Struct.expand>`, and :class:`Parser
  <coil.parser.Parser>`.

Version 0.3.4 (2009-04-06)
==========================

- Add some new methods: validate_key, validate_path, and unexpanded.

- Allow limited string expansion in @file and @package arguments.  Only
  values defined in the :class:`Struct <coil.struct.Struct>` before the
  @file/@package statement are allowed in the expansion.

- Fix nested lists.

- Fix :class:`Struct.__str__ <coil.struct.Struct>` to produce valid coil
  text. (__repr__ still produces valid python code using dicts).

- Fix copying lists.

- Make :meth:`Struct.set <coil.struct.Struct.set>` public again.

- Refactor the get/set/expand methods in :class:`Struct
  <coil.struct.Struct>` to clean up a bit.

Version 0.3.3 (2009-03-18)
==========================

- Fix expansion of items inside lists

Version 0.3.2 (2009-03-17)
==========================

- Allow substituting values other than strings into strings.
  An error is still raised if the value is a list or Struct.

- Allow adding new attributes at an arbitrary tree depth.

Version 0.3.1 (2009-03-15)
==========================

- Change Struct.__getattr__ and friends to behave exactly like
  :meth:`Struct.get <coil.struct.Struct.get>`, allowing access to
  arbitrary paths.

- Fix the tokenizer and parser to allow None as a value.

- Drop expansion support from Struct.set and make it private.

- Add new :meth:`Struct.expand <coil.struct.Struct.expand>` method to
  expand all Links and in-string variables recursively over the entire
  tree.

- Default values given to any expansion methods are now only used if
  the value is missing from the tree rather than overriding them.

- Switch from the 'silent' argument to 'ignore' for all expansion
  methods and allow it to take a specific list of names that can
  be ignored.

- Allow the Parser and the parsing helper functions to pass default
  values and ignore options to :meth:`Struct.expand
  <coil.struct.Struct.expand>`.

Version 0.3.0 (2009-02-10)
==========================

This mars the beginning of a large rewrite of coil. The programming API
is changing dramatically and will continue to evolve over the 0.3.x
series. Hopefully things will be fairly solid by version 0.4.

Changes since 0.2.2:

- All inheritance, links, and string variable expansions are performed
  immediately after parsing, ensuring that broken links and other
  errors are reported as soon as possible. String variable expansion
  may also happen at run time if desired.

- The text format now allows a struct to inherit from any number of
  other structs. This allows large configurations to be broken into
  separate files and then merged back together with a set of @file
  directives.

- :class:`Struct <coil.struct.Struct>` now features a complete dict-like
  interface and understands containers, removing the need for
  :class:`StructNode <coil.struct.StructNode>`. The old StructNode class
  is still provided as a simple wrapper around Struct for backwards
  compatibility.

- Support for variable expansion within strings, for example: "${foo}"
  All relative and absolute (@root) paths are supported. This is a
  change from previous coil extensions which were more limited,
  requiring programs to change the root rather than simply allowing
  parent references.

- Easily convert between dict and Struct objects. Pass a dict as the
  'base' parameter in :class:`Struct <coil.struct.Struct>` to convert it
  to a Struct. Use :meth:`Struct.dict <coil.struct.Struct.dict>` to
  convert back to a dict.

- Struct objects may be modified at run time just like a normal dict.

- Structs get and set methods may reference any relative or absolute
  path in the tree.

- More exception types with clearer error messages to ease
  troubleshooting. This is a work in progress.
