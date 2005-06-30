"""Rendering of Struct objects to Python code."""

import sets
from twisted.python import reflect

from coil import struct


NotRendered = object()

class RenderNode(struct.StructNode):
    """Caches rendered results."""

    def __init__(self, s, container=None):
        struct.StructNode.__init__(self, s, container)
        if self._container is None:
            self._nodeCache = {}
        else:
            self._nodeCache = self._container._nodeCache
        self._nodeCache[self._struct] = self
        self._rendered = NotRendered
    
    def rendered(self):
        return self._rendered

    def containers(self):
        s = sets.Set()
        n = self._container
        while n is not None:
            s.add(n)
            n = n._container
        return s
    
    def _wrap(self, st):
        if st in self._nodeCache:
            return self._nodeCache[st]
        else:
            return self.__class__(st, self)


def renderStruct(rootStruct):
    """Render a tree of Structs."""
    root = RenderNode(rootStruct)
    stack = [("", root)]
    while stack:
        # XXX make this less stupid
        nodeName, node = stack[-1]
        waitForChildren = False
        for name, value in node.iteritems():
            if isinstance(value, RenderNode) and value.rendered() is NotRendered:
                if (name,value) in node.containers():
                    raise ValueError, "can't render recursive links: %s" % (":".join([p[0] for p in stack]),)
                stack.append((name,value))
                waitForChildren = True
        if not waitForChildren:
            stack.pop(-1)
            if node.rendered() is not NotRendered:
                continue
            try:
                factory = node.get("@factory") # XXX ick
            except struct.StructAttributeError:
                factory = lambda x: x
            else:
                factory = reflect.namedObject(factory)
            node._rendered = factory(node)
    return root.rendered()
