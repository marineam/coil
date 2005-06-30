"""Test text format."""

from twisted.trial import unittest
from coil import text


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

    def testBad(self):
        for s in [
            "struct: {",
            "struct: }",
            "a: b:",
            ":",
            "[]",
            ]:
            self.assertRaises(text.ParseError, text.fromString, s)

        try:
            text.fromString("x: 1\n2\n")
        except text.ParseError, e:
            self.assertEquals(e.line, 2)
        else:
            raise RuntimeError
