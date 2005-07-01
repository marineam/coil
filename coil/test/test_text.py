"""Test text format."""

from twisted.trial import unittest
from coil import text, struct


class TextTestCase(unittest.TestCase):

    def testListParse(self):
        s = 'x: [None 1 2.3 ["hello \\"world"] [7]]'
        self.assertEquals(text.fromString(s).get("x"),
                          [None, 1, 2.3, ['hello "world'], [7]])

    def testComments(self):
        s = "y: [12 #hello\n]"
        self.assertEquals(text.fromString(s).get("y"), [12])

    def testStruct(self):
        s = '''
struct: {
    x: 12  y: 14
    substruct: {
        a: "hello world"
        b: False
    }
}'''
        root = text.fromString(s)
        self.assertEquals(list(root.attributes()), ["struct"])
        struct = root.get("struct")
        self.assertEquals(list(struct.attributes()), ["x", "y", "substruct"])
        self.assertEquals(struct.get("x"), 12)
        substruct = struct.get("substruct")
        self.assertEquals(list(substruct.attributes()), ["a", "b"])
        self.assertEquals(substruct.get("b"), False)

    def testAttributePath(self):
        s = '''
struct: {
    sub: {a: 1 c: 2}
    sub.b: 2
    sub.c: 3
}'''
        root = text.fromString(s).get("struct")
        self.assertEquals(root.get("sub").get("a"), 1)
        self.assertEquals(root.get("sub").get("b"), 2)
        self.assertEquals(root.get("sub").get("c"), 3)
    
    def testBad(self):
        for s in [
            "struct: {",
            "struct: }",
            "a: b:",
            ":",
            "[]",
            "a: ~b",
            ]:
            self.assertRaises(text.ParseError, text.fromString, s)

        try:
            text.fromString("x: 1\n2\n")
        except text.ParseError, e:
            self.assertEquals(e.line, 2)
        else:
            raise RuntimeError

    def testDeleted(self):
        s = '''
struct: {
    a: {b: 1 x: 3}
    c: 2
    d: {b: 2}
    ~c
    ~a.b
}
~struct.d
'''
        root = text.fromString(s).get("struct")
        self.assertEquals(list(root.attributes()), ["a"])
        self.assertEquals(list(root.get("a").attributes()), ["x"])

    def testLink(self):
        s = '''
struct: {
    sub: {a: =@CONTAINER.b c2: =c c: 1}
    b: 2
    c: =@ROOT.x
}
x: "hello"
'''
        root = struct.StructNode(text.fromString(s))
        self.assertEquals(root.struct.c, "hello")
        self.assertEquals(root.struct.sub.a, 2)
        self.assertEquals(root.struct.sub.c2, 1)

    def testSimpleExtends(self):
        s = '''
bar: {
   a: 1
   b: 2
   c: {d: 7}
}

foo: {
   @extends: =@CONTAINER.bar
   a: 3
   c: {
       @extends: =@ROOT.bar.c
       e: 4
   }
   c.f: 9 # nicer way of doing it
}
'''
        foo = struct.StructNode(text.fromString(s)).foo
        self.assertEquals(foo.a, 3)
        self.assertEquals(foo.b, 2)
        self.assertEquals(foo.c.d, 7)
        self.assertEquals(foo.c.e, 4)
        self.assertEquals(foo.c.f, 9)
