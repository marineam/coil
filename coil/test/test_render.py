"""Test rendering to code."""

from twisted.trial import unittest
from twisted.application import service
from coil import render, struct


class ServiceA(service.Service):

    def __init__(self, x):
        self.x = x

class ServiceB(service.Service):

    def __init__(self, y):
        self.y = y


def makeMultiService(node):
    svc = service.MultiService()
    for name, value in node.iteritems():
        if name.startswith("@"): # XXX guess we need better iteration API
            continue
        subsvc = value.rendered()
        subsvc.setName(name)
        subsvc.setServiceParent(svc)
    return svc

def makeServiceA(node):
    return ServiceA(node.x)

def makeServiceB(node):
    return ServiceB(node.y)


AStruct = struct.Struct(None, [("x", 0),
                               ("@factory", "coil.test.test_render.makeServiceA")])
BStruct = struct.Struct(None, [("y", ""),
                               ("@factory", "coil.test.test_render.makeServiceB")])
MSStruct = struct.Struct(None, [("@factory", "coil.test.test_render.makeMultiService")])


class RenderTestCase(unittest.TestCase):

    def testSimple(self):
        a = render.renderStruct(struct.Struct(AStruct, [("x", 1)]))
        self.assert_(isinstance(a, ServiceA))
        self.assertEquals(a.x, 1)

    def testRenderNode(self):
        c = struct.Struct(MSStruct, [("a", AStruct), ("a2", AStruct)])
        r = render.RenderNode(c)
        self.assertIdentical(r.a, r.a)
        self.assertEquals(list(r.iterkeys()), ["@factory", "a", "a2"])
        self.assertEquals(list(r.a.iterkeys()), ["x", "@factory"])
    
    def testNesting(self):
        c = struct.Struct(MSStruct, [("a", AStruct), ("a2", AStruct)])
        root = render.renderStruct(c)
        self.assert_(isinstance(root, service.MultiService))
        self.assertEquals(root.getServiceNamed("a").x, 0)
        self.assertEquals(root.getServiceNamed("a2").x, 0)
        self.assertNotIdentical(root.getServiceNamed("a"), root.getServiceNamed("a2"))

    def testLinkToObject(self):
        c = struct.Struct(None,
                          [("anA", AStruct),
                           ("service", struct.Struct(MSStruct, [("a", struct.Link(struct.CONTAINER, "anA"))]))])
        root = render.renderStruct(c)
        self.assert_(isinstance(root.anA.rendered(), ServiceA))
        self.assertEquals(root.anA.rendered().x, 0)
        self.assertIdentical(root.anA.rendered(), root.service.rendered().getServiceNamed("a"))
