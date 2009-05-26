Introduction
============

Coil is a configuration file format that is parsed into a tree of dict
like L{Struct} objects. The format supports inheritance, allowing
complicated configurations to be as compact as possible.

Design Goals
============

General design/implementation goals, some have been met, others are
still in progress.

- Support Twisted and non-Twisted reactor driven Python programs.

- Scalable to complex configurations, easily avoiding duplication.

- Orthogonal to code; code should not be required to know about the
  config system used, it should be regular Python or Twisted code.

- Minimal boilerplate.

