Introduction
============

Coil is a configuration file format and Python library for parsing those
config files. The format is very flexible, providing the ability to
group a set of key, value pairs in blocks, nesting these blocks,
allowing one block to inherit from another, etc. The Python library
exposes this structure as a tree of *dict* like
:class:`~coil.struct.Struct` objects which are easy to use and
manipulate. The inheritance feature allows for reasonably compact
configuration of large systems that have related components.

Design Goals
------------

General design/implementation goals, some have been met, others are
still in progress.

- Minimal boilerplate. When all you want is a set of key, value pairs
  that's all you have to use and requires less markup than other XML
  based languages.

- Reasonably readable and reliable. System administrators are want to
  run systems and do so as easily as possible. Defining configuration
  options should not require intimate knowledge of the code that reads
  the config. When that program loads the config it should validate it
  as early as possible and provide clear error messages.
  (This is still a work in progress)

- Scalable to complex configurations, easily avoiding duplication.

- Orthogonal to code; code should not be required to know about the
  config system used, it should be regular Python code.

Inspirations
------------

Why develop yet another configuration format? There are lots of options
out there including basic INI files, YAML, and more XML based formats
than you want to know about. All have there strengths and weaknesses.
INI is simple and readable but also doesn't allow nesting or inheritance
that are required for large and complex systems. XML is very popular,
has lots of tools available, and is easy to validate. But on the down
side it rather verbose and thus not particularly friendly to human
editing. YAML is on the other side with almost too little mark up,
allowing complex nested structures but everything is delimited by white
space and punctuation marks.

One inspiration is _`SmartFrog
http://www.hpl.hp.com/research/smartfrog/` see the papers section for
details), a distributed configuration system. As such, much of what it
does is outside the scope for what coil needs to be. It does have one
major idea we want: prototype-based data driven configuration. By
prototype based I mean a model similar to the way Self (maybe ECMAScript
too) object system works: there are no subclassing or instantiation,
there is only extending of other objects.

