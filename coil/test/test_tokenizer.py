"""Tests for coil.tokenizer."""

import unittest
from coil import tokenizer

class TokenizerTestCase(unittest.TestCase):

    def testEmpty(self):
        tok = tokenizer.Tokenizer([""])
        self.assertRaises(StopIteration, tok.next)

    def testAtom(self):
        tok = tokenizer.Tokenizer(["somekey"])
        first = tok.next()
        self.assert_(isinstance(first, tokenizer.Token))
        self.assertEquals(first.type, 'ATOM')
        self.assertEquals(first.value, "somekey")
        self.assertEquals(first.line, 1)
        self.assertEquals(first.column, 1)
        self.assertRaises(StopIteration, tok.next)

    def testString(self):
        tok = tokenizer.Tokenizer(["'string'"])
        first = tok.next()
        self.assertEquals(first.type, 'STRING')
        self.assertEquals(first.value, "string")
        self.assertEquals(first.line, 1)
        self.assertEquals(first.column, 1)
        self.assertRaises(StopIteration, tok.next)

    def testCounters(self):
        tok = tokenizer.Tokenizer(["'string' '''foo''' '' '''''' other",
                                   "'''multi line string",
                                   "it is crazy''' hi",
                                   "  bye"])
        tok.next()
        token = tok.next()
        self.assertEquals(token.line, 1)
        self.assertEquals(token.column, 10)
        token = tok.next()
        self.assertEquals(token.line, 1)
        self.assertEquals(token.column, 20)
        token = tok.next()
        self.assertEquals(token.line, 1)
        self.assertEquals(token.column, 23)
        token = tok.next() # other
        self.assertEquals(token.line, 1)
        self.assertEquals(token.column, 30)
        token = tok.next()
        self.assertEquals(token.line, 2)
        self.assertEquals(token.column, 1)
        token = tok.next() # hi
        self.assertEquals(token.line, 3)
        self.assertEquals(token.column, 16)
        token = tok.next() # bye
        self.assertEquals(token.line, 4)
        self.assertEquals(token.column, 3)
        self.assertRaises(StopIteration, tok.next)
